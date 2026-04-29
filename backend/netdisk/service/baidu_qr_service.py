# -*- coding: utf-8 -*-
import sys, uuid, time, json, random, asyncio, os, shutil

from threading import Thread, Event

import httpx
import redis.asyncio as aioredis
from loguru import logger
from sqlalchemy.orm import Session

from .. import models
from .baidu_device_service import BaiduDeviceService


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SIGN_TTL = 300
SIGN_KEY  = "sign:{}"

_redis: aioredis.Redis | None = None
_thread_store: dict[str, dict] = {}
_stop_events:  dict[str, Event] = {}
_memory_ctx_store: dict[str, dict] = {}

BROWSER_CANDIDATES = (
    os.environ.get('BAIDU_BROWSER_PATH') or os.environ.get('NETDISK_BROWSER_PATH') or '',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    'msedge.exe',
    'chrome.exe',
    'chromium',
    'chromium-browser',
    'google-chrome',
)


def set_redis(r): global _redis; _redis = r


def resolve_browser_executable() -> str | None:
    for candidate in BROWSER_CANDIDATES:
        candidate_text = str(candidate or '').strip().strip('"')
        if not candidate_text or candidate_text in {'.', '..'}:
            continue
        if os.path.isfile(candidate_text):
            return candidate_text
        resolved = shutil.which(candidate_text)
        if resolved and os.path.isfile(resolved):
            return resolved
    return None


def build_chromium_launch_kwargs(*, headless: bool, proxy: dict | None = None) -> dict:
    launch_args = ['--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage']
    if sys.platform != 'win32':
        launch_args.extend(['--no-sandbox', '--disable-setuid-sandbox'])
    launch_kwargs = {
        'headless': headless,
        'args': launch_args,
        'ignore_default_args': ['--enable-automation'],
        'chromium_sandbox': sys.platform == 'win32',
    }
    browser_executable = resolve_browser_executable()
    if browser_executable:
        launch_kwargs['executable_path'] = browser_executable
    if proxy:
        launch_kwargs['proxy'] = proxy
    return launch_kwargs


def _parse_jsonp(text):
    try: return json.loads(text[text.index("(")+1:text.rindex(")")])
    except: return {}


def _prune_memory_ctx_store():
    now = time.time()
    expired = [key for key, value in _memory_ctx_store.items() if float(value.get('_expires_at') or 0) <= now]
    for key in expired:
        _memory_ctx_store.pop(key, None)


def _memory_ctx_payload(sign):
    _prune_memory_ctx_store()
    cached = _memory_ctx_store.get(sign)
    if not cached:
        return None
    return {key: value for key, value in cached.items() if key != '_expires_at'}


async def _set_ctx(sign, ctx):
    payload = dict(ctx or {})
    payload['_expires_at'] = time.time() + SIGN_TTL
    _memory_ctx_store[sign] = payload
    _prune_memory_ctx_store()
    if _redis is None:
        return
    try:
        await _redis.setex(SIGN_KEY.format(sign), SIGN_TTL, json.dumps(ctx))
    except Exception as exc:
        logger.warning(f"[QrService] Redis set_ctx failed, fallback to memory cache: {exc}")


async def _get_ctx(sign):
    if _redis is not None:
        try:
            raw = await _redis.get(SIGN_KEY.format(sign))
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning(f"[QrService] Redis get_ctx failed, fallback to memory cache: {exc}")
    return _memory_ctx_payload(sign)


async def _del_ctx(sign):
    _memory_ctx_store.pop(sign, None)
    if _redis is None:
        return
    try:
        await _redis.delete(SIGN_KEY.format(sign))
    except Exception as exc:
        logger.warning(f"[QrService] Redis del_ctx failed, cleared memory cache only: {exc}")



# ── 浏览器线程：整个登录流程在同一个 Playwright context 内完成 ──
def _browser_login_thread(sign: str, gid: str, store: dict, stop: Event):
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**build_chromium_launch_kwargs(headless=True))

            ctx = browser.new_context(
                user_agent=DEFAULT_UA, locale="zh-CN",
                viewport={"width": 1280, "height": 800},
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                "window.chrome={runtime:{}};"
            )
            page = ctx.new_page()

            # 拦截 getqrcode 拿 sign & imgurl
            qr = {}
            def on_resp(r):
                try:
                    if "getqrcode" in r.url:
                        d = _parse_jsonp(r.text())
                        if d.get("sign"): qr.update(d)
                except: pass
            page.on("response", on_resp)

            page.goto("https://www.baidu.com/", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(500)
            page.goto(f"https://passport.baidu.com/v2/?login&tpl=netdisk&gid={gid}",
                      wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            actual_sign = qr.get("sign", "")
            img_url = qr.get("imgurl", "")
            if not actual_sign:
                store["error"] = "getqrcode failed"
                store["ready"] = True
                browser.close()
                return

            img_url = img_url.replace("\\", "")
            if not img_url.startswith("http"): img_url = f"https://{img_url}"

            store["actual_sign"] = actual_sign
            store["imgurl"]      = img_url
            store["ready"]       = True
            logger.info(f"[browser] QR ready sign={actual_sign[:8]}")

            # 等 BDUSS cookie 出现（页面 JS 扫码确认后自动写入），每秒检查一次，最多 90 秒
            for _ in range(90):
                if stop.is_set(): break
                time.sleep(1)
                cookies = ctx.cookies()
                bduss = next((c["value"] for c in cookies if c["name"] == "BDUSS"), None)
                if bduss:
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                    store["bduss"]      = bduss
                    store["cookie_str"] = cookie_str
                    store["done"]       = "success"
                    logger.info(f"[browser] login ok BDUSS captured url={page.url}")
                    browser.close()
                    return

            store["done"] = "timeout"
            logger.warning(f"[browser] timeout waiting for BDUSS")
            browser.close()
    except Exception as e:
        store["error"] = str(e)
        store["done"]  = f"error:{e}"
        logger.error(f"[browser] thread error: {e}")


# ── 对外方法 ────────────────────────────────────────────────
async def generate_qr_code() -> dict:
    gid  = str(uuid.uuid4()).upper()
    sign = f"pending_{gid}"
    logger.info(f"[QrService] generateQrCode GID={gid}")

    store = {"ready": False, "actual_sign": "", "imgurl": "",
             "bduss": None, "cookie_str": None, "done": None}
    stop  = Event()
    _thread_store[sign] = store
    _stop_events[sign]  = stop

    Thread(target=_browser_login_thread, args=(sign, gid, store, stop), daemon=True).start()

    # 等浏览器打开并拿到二维码（最多 20 秒）
    for _ in range(40):
        await asyncio.sleep(0.5)
        if store.get("ready"): break
    else:
        stop.set()
        raise ValueError("浏览器启动超时")

    if store.get("error"):
        raise ValueError(store["error"])

    actual  = store["actual_sign"]
    img_url = store["imgurl"]
    logger.debug(f"[QrService] actual_sign={actual!r} imgurl={img_url!r}")

    if not actual:
        raise ValueError("二维码 sign 为空，请重试")
    if not img_url:
        raise ValueError("二维码图片地址为空，请重试")

    _thread_store[actual] = store
    _stop_events[actual]  = stop
    _thread_store.pop(sign, None)
    _stop_events.pop(sign, None)

    await _set_ctx(actual, {"gid": gid})

    logger.info(f"[QrService] generateQrCode ok sign={actual[:8]}...")

    return {"sign": actual, "imgurl": img_url}


async def check_login_status(sign: str, tenant_id: str, db: Session) -> dict:
    store = _thread_store.get(sign)
    if not store:
        # sign 可能已经完成并被清理，或者是旧的 sign
        return {"status": "pending"}

    done = store.get("done")

    if not done:
        return {"status": "pending"}

    # 清理
    _stop_events.get(sign, Event()).set()
    _thread_store.pop(sign, None)
    _stop_events.pop(sign, None)
    await _del_ctx(sign)

    if done != "success":
        return {"status": "failed", "msg": f"{done}，请重新扫码"}

    cookie_str = store["cookie_str"]
    bduss      = store["bduss"]

    # 获取用户信息：百度网盘 PCS 官方接口，只需 BDUSS 即可
    uinfo = {"username": "百度用户", "vip_level": "未知"}
    try:
        async with httpx.AsyncClient(
            headers={"Cookie": f"BDUSS={bduss}", "User-Agent": DEFAULT_UA},
            follow_redirects=True, timeout=10.0
        ) as c:
            r = await c.get("https://pan.baidu.com/rest/2.0/xpan/nas",
                            params={"method": "uinfo", "access_token": ""})
            logger.debug(f"[QrService] xpan/nas uinfo={r.status_code} body={r.text[:300]}")
            d = r.json() if r.text.strip() else {}
            if d.get("errno") == 0:
                uinfo = {
                    "username":   d.get("baidu_name") or d.get("netdisk_name") or "百度用户",
                    "vip_level":  "SVIP" if d.get("is_svip") else
                                  "VIP"  if d.get("is_vip")  else "普通用户",
                    "avatar_url": d.get("avatar_url", ""),
                }
            else:
                # 降级：直接从 passport 拿账号名
                r2 = await c.get("https://passport.baidu.com/center/api/login",
                                 headers={"Referer": "https://passport.baidu.com/center"})
                logger.debug(f"[QrService] passport center={r2.status_code} body={r2.text[:300]}")
                d2 = r2.json() if r2.text.strip() else {}
                name = d2.get("data", {}).get("username") or d2.get("username", "")
                if name:
                    uinfo["username"] = name
    except Exception as e:
        logger.warning(f"[QrService] uinfo error: {e}")

    inferred_region = ""
    try:
        inferred_region = str(BaiduDeviceService.infer_common_region(cookie_str) or "").strip()
    except Exception as e:
        logger.warning(f"[QrService] infer region error: {e}")

    # 入库
    acc = db.query(models.DiskAccount).filter_by(
        tenant_id=tenant_id, username=uinfo["username"]).first()
    if acc:
        acc.cookie=cookie_str; acc.status=1; acc.vip_level=uinfo["vip_level"]; acc.avatar_url=uinfo.get("avatar_url","")
        if inferred_region:
            acc.region = inferred_region
    else:
        db.add(models.DiskAccount(tenant_id=tenant_id, username=uinfo["username"],
                                  cookie=cookie_str, status=1, weight=1,
                                  vip_level=uinfo["vip_level"], avatar_url=uinfo.get("avatar_url",""),
                                  region=inferred_region))
    db.commit()
    logger.info(f"[QrService] saved user={uinfo['username']} tenant={tenant_id} region={inferred_region or '未识别'}")
    return {"status": "success", "username": uinfo["username"], "region": inferred_region}