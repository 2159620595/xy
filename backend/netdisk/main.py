# -*- coding: utf-8 -*-
"""
main.py
路由层，对应 Spring Boot 的 @RestController
只做参数接收 + 调用 Service + 返回响应，不含业务逻辑
"""
import sys, uuid, asyncio, time, os, hashlib, json, base64, re, secrets, ipaddress, hmac, subprocess

from urllib.parse import unquote, urlencode, urlsplit

from copy import deepcopy






from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from datetime import datetime
from Crypto.Cipher import AES

from Crypto.Util.Padding import pad, unpad

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import case, func, or_, text
from sqlalchemy.exc import SQLAlchemyError

from sqlalchemy.orm import Session
from pydantic import BaseModel

from app_logging import configure_logging, get_logger

from . import models
from .database import (
    SessionLocal,
    engine,
    get_db,
    ensure_database_ready,
    mark_database_ready,
    mark_database_unavailable,
    is_database_ready,
)


from .service import baidu_qr_service as QrService
from .service.baidu_device_service import BaiduDeviceService





def _patch_windows_subprocess_text_decoding() -> None:
    if sys.platform != "win32" or getattr(subprocess, "_pan_saas_text_decode_patch", False):
        return

    original_popen_init = subprocess.Popen.__init__

    def patched_popen_init(self, *args, **kwargs):
        text_mode = bool(kwargs.get("text") or kwargs.get("universal_newlines"))
        if text_mode:
            if kwargs.get("encoding") is None:
                kwargs["encoding"] = "utf-8"
            if kwargs.get("errors") is None:
                kwargs["errors"] = "replace"
        return original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = patched_popen_init
    subprocess._pan_saas_text_decode_patch = True


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    _patch_windows_subprocess_text_decoding()

# ── 日志 ──────────────────────────────────────────────────────
configure_logging()
logger = get_logger("netdisk")


# ── Redis 实例 ────────────────────────────────────────────────
# 提出来作为全局变量，因为 verify_signature 函数也需要用到
redis_client = None
local_replay_cache: dict[str, int] = {}
local_replay_cache_lock = asyncio.Lock()


# ── Pydantic 响应模型 ─────────────────────────────────────────
class QrCodeResponse(BaseModel):
    sign: str
    imgurl: str

class StatusResponse(BaseModel):
    status: str
    username: str | None = None
    msg: str | None = None
    sign: str | None = None
    imgurl: str | None = None
    region: str | None = None

class KeysResponse(BaseModel):
    status: str
    keys: list[str]
    account_id: int | None = None
    account_name: str | None = None
    region: str | None = None

class DiskAccountOut(BaseModel):
    id: int; tenant_id: str; username: str
    vip_level: str; status: int; weight: int
    avatar_url: str = ""
    cookie: str = ""
    region: str = ""
    proxy_url: str | None = None
    class Config: from_attributes = True


class CdKeyOut(BaseModel):
    id: int; tenant_id: str; key_code: str; duration: int
    status: int = 0; account_id: int | None = None
    max_uses: int = 0; use_count: int = 0; expires_at: int | None = None
    class Config: from_attributes = True

from . import task_kick_devices


ADMIN_PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
ADMIN_PASSWORD_HASH_ITERATIONS = 260000
ADMIN_LOGIN_LOCK_THRESHOLD = 5
ADMIN_LOGIN_ATTEMPT_WINDOW_MINUTES = 15
ADMIN_LOGIN_LOCK_DURATION_MINUTES = 30
ADMIN_LOGIN_SUSPICIOUS_IP_THRESHOLD = 3
ADMIN_LOGIN_RISK_FAILURE_THRESHOLD = 3
ADMIN_LOGIN_SUCCESS_IP_LOOKBACK = 5
CDKEY_VOID_GRACE_SECONDS = int(os.environ.get("CDKEY_VOID_GRACE_SECONDS", 10 * 60) or 10 * 60)


def normalize_region(value: str | None) -> str:
    return str(value or "").strip()


def get_cdkey_void_deadline(expires_at: int | None) -> int | None:
    if expires_at is None:
        return None
    return int(expires_at) + CDKEY_VOID_GRACE_SECONDS


def is_cdkey_expired(key: models.CdKey, now_ts: int | None = None) -> bool:
    deadline = get_cdkey_void_deadline(getattr(key, "expires_at", None))
    if deadline is None:
        return False
    current_ts = int(time.time()) if now_ts is None else int(now_ts)
    return current_ts > deadline


def mark_cdkey_void_if_expired(key: models.CdKey, now_ts: int | None = None) -> bool:
    if getattr(key, "status", None) == 2:
        return True
    if is_cdkey_expired(key, now_ts=now_ts):
        key.status = 2
        return True
    return False


def ensure_netdisk_schema() -> None:
    ensure_database_ready()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE disk_accounts ADD COLUMN IF NOT EXISTS region VARCHAR DEFAULT ''"))
        conn.execute(text("UPDATE disk_accounts SET region = '' WHERE region IS NULL"))
        conn.execute(text("ALTER TABLE admin_login_logs ADD COLUMN IF NOT EXISTS risk_level VARCHAR DEFAULT '正常'"))
        conn.execute(text("ALTER TABLE admin_login_logs ADD COLUMN IF NOT EXISTS risk_flags VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE admin_login_logs ADD COLUMN IF NOT EXISTS log_message VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE judian_accounts ADD COLUMN IF NOT EXISTS login_email VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE judian_accounts ADD COLUMN IF NOT EXISTS login_password TEXT DEFAULT ''"))
        conn.execute(text("ALTER TABLE judian_accounts ADD COLUMN IF NOT EXISTS user_sig TEXT DEFAULT ''"))
        conn.execute(text("ALTER TABLE judian_accounts ADD COLUMN IF NOT EXISTS diamond_quantity INTEGER DEFAULT 0"))
        conn.execute(text("ALTER TABLE judian_accounts ADD COLUMN IF NOT EXISTS diamond_quantity_updated_at VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE judian_accounts ADD COLUMN IF NOT EXISTS last_login_at VARCHAR DEFAULT ''"))
        conn.execute(text("UPDATE judian_accounts SET login_email = '' WHERE login_email IS NULL"))
        conn.execute(text("UPDATE judian_accounts SET login_password = '' WHERE login_password IS NULL"))
        conn.execute(text("UPDATE judian_accounts SET user_sig = '' WHERE user_sig IS NULL"))
        conn.execute(text("UPDATE judian_accounts SET diamond_quantity = 0 WHERE diamond_quantity IS NULL"))
        conn.execute(text("UPDATE judian_accounts SET diamond_quantity_updated_at = '' WHERE diamond_quantity_updated_at IS NULL"))
        conn.execute(text("UPDATE judian_accounts SET last_login_at = '' WHERE last_login_at IS NULL"))
    db = SessionLocal()
    try:
        backfilled_count = backfill_admin_login_messages(db)
        if backfilled_count:
            logger.info(f"已补齐 {backfilled_count} 条管理员登录日志的完整文本")
    except Exception as exc:
        db.rollback()
        logger.warning(f"补齐管理员登录日志完整文本失败: {exc}")
    finally:
        db.close()






def normalize_ip_address(value: str | None) -> str:
    candidate = str(value or "").strip().strip('"').strip("'")
    if not candidate:
        return ""
    lowered = candidate.lower()
    if lowered == "unknown":
        return ""
    if lowered in {"localhost", "::1", "0:0:0:0:0:0:0:1"}:
        return "127.0.0.1"
    if lowered.startswith("for="):
        candidate = candidate.split("=", 1)[1].strip().strip('"').strip("'")
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1:candidate.index("]")]
    if candidate.startswith("::ffff:"):
        candidate = candidate[7:]
    ipv4_with_port_match = re.fullmatch(r"(\d+\.\d+\.\d+\.\d+):(\d+)", candidate)
    if ipv4_with_port_match:
        candidate = ipv4_with_port_match.group(1)
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return ""


def extract_ip_from_header(value: str | None) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    for segment in raw_value.split(","):
        cleaned_segment = str(segment or "").strip()
        if not cleaned_segment:
            continue
        for part in cleaned_segment.split(";"):
            normalized_ip = normalize_ip_address(part)
            if normalized_ip:
                return normalized_ip
    return ""


def is_loopback_ip(value: str | None) -> bool:
    normalized_ip = normalize_ip_address(value)
    if not normalized_ip:
        return False
    try:
        return ipaddress.ip_address(normalized_ip).is_loopback
    except ValueError:
        return normalized_ip == "127.0.0.1"


def is_security_relevant_ip(value: str | None) -> bool:
    normalized_ip = normalize_ip_address(value)
    return bool(normalized_ip and not is_loopback_ip(normalized_ip))


def resolve_client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    for header_name in ("x-forwarded-for", "x-real-ip", "cf-connecting-ip", "x-client-ip", "x-forwarded", "forwarded"):
        resolved_ip = extract_ip_from_header(request.headers.get(header_name))
        if resolved_ip:
            return resolved_ip
    client = getattr(request, "client", None)
    host = getattr(client, "host", "") if client else ""
    normalized_host = normalize_ip_address(host)
    return normalized_host or str(host or "").strip()


DEFAULT_CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://woshishabi.xyz",
    "https://www.woshishabi.xyz",
]



def normalize_origin_value(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = urlsplit(text if "://" in text else f"https://{text}")
    except Exception:
        return ""
    scheme = str(parsed.scheme or "https").strip().lower()
    netloc = str(parsed.netloc or "").strip().lower()
    if scheme not in {"http", "https"} or not netloc:
        return ""
    return f"{scheme}://{netloc}"


def parse_origin_allowlist(value: str | None) -> list[str]:
    raw_text = str(value or "")
    if not raw_text.strip():
        return []
    normalized: list[str] = []
    for part in re.split(r"[\n,;]+", raw_text):
        origin = normalize_origin_value(part)
        if origin and origin not in normalized:
            normalized.append(origin)
    return normalized


def get_configured_cors_allowed_origins() -> list[str]:
    configured = parse_origin_allowlist(os.environ.get("CORS_ALLOW_ORIGINS", ""))
    return configured or list(DEFAULT_CORS_ALLOWED_ORIGINS)


CORS_ALLOWED_ORIGINS = get_configured_cors_allowed_origins()


def get_request_origin_candidates(request: Request | None) -> list[str]:
    if request is None:
        return []
    candidates: list[str] = []
    for header_name in ("origin", "referer"):
        origin = normalize_origin_value(request.headers.get(header_name))
        if origin and origin not in candidates:
            candidates.append(origin)
    return candidates


def is_request_from_trusted_origin(request: Request | None) -> bool:
    if request is None:
        return False
    trusted_origins = list(CORS_ALLOWED_ORIGINS)
    extra_origins = parse_origin_allowlist(os.environ.get("ADMIN_SESSION_TRUSTED_ORIGINS", ""))
    for origin in extra_origins:
        if origin not in trusted_origins:
            trusted_origins.append(origin)
    if not trusted_origins:
        return False
    return any(candidate in trusted_origins for candidate in get_request_origin_candidates(request))






def normalize_login_status(value: str | None) -> str | None:
    mapping = {
        "success": "成功",
        "ok": "成功",
        "成功": "成功",
        "failure": "失败",
        "fail": "失败",
        "error": "失败",
        "失败": "失败",
    }
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return mapping.get(normalized)


def is_admin_password_hashed(value: str | None) -> bool:
    stored_value = str(value or "").strip()
    return stored_value.startswith(f"{ADMIN_PASSWORD_HASH_PREFIX}$")


def hash_admin_password(password: str, *, salt: str | None = None, iterations: int = ADMIN_PASSWORD_HASH_ITERATIONS) -> str:
    safe_salt = str(salt or secrets.token_hex(16)).strip() or secrets.token_hex(16)
    safe_iterations = int(iterations or ADMIN_PASSWORD_HASH_ITERATIONS)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password or "").encode("utf-8"),
        safe_salt.encode("utf-8"),
        safe_iterations,
    ).hex()
    return f"{ADMIN_PASSWORD_HASH_PREFIX}${safe_iterations}${safe_salt}${digest}"


def verify_admin_password(stored_password: str | None, candidate_password: str | None) -> tuple[bool, bool]:
    stored_value = str(stored_password or "").strip()
    raw_candidate = str(candidate_password or "")
    if not stored_value:
        return False, False
    if is_admin_password_hashed(stored_value):
        try:
            _, iteration_text, salt, expected_digest = stored_value.split("$", 3)
            calculated_digest = hashlib.pbkdf2_hmac(
                "sha256",
                raw_candidate.encode("utf-8"),
                salt.encode("utf-8"),
                int(iteration_text),
            ).hex()
            return secrets.compare_digest(calculated_digest, expected_digest), False
        except Exception as exc:
            logger.warning(f"管理员密码哈希校验失败，将拒绝本次登录: {exc}")
            return False, False
    return secrets.compare_digest(stored_value, raw_candidate), True


def build_lock_message(lock_state: dict[str, int | str]) -> str:
    locked_until = int(lock_state.get("locked_until") or 0)
    remaining_minutes = int(lock_state.get("remaining_minutes") or 1)
    scope_label = str(lock_state.get("scope_label") or "账号")
    readable_time = datetime.fromtimestamp(locked_until).strftime("%Y-%m-%d %H:%M:%S") if locked_until else "稍后"
    return f"{scope_label}登录失败次数过多，已临时锁定，请于 {readable_time} 后重试（约 {remaining_minutes} 分钟）"


def format_database_unavailable_message(exc: Exception) -> str:
    raw_text = str(exc or "").strip()
    if "exceeded the data transfer quota" in raw_text.lower():
        return "Neon 数据库流量额度已超限，网盘模块暂不可用。请升级套餐或等待额度重置后重试。"
    if raw_text:
        return f"网盘数据库暂不可用：{raw_text}"
    return "网盘数据库暂不可用，请稍后重试"


def _evaluate_lock_scope(db: Session, column, value: str, now_ts: int) -> dict[str, int] | None:

    normalized_value = str(value or "").strip()
    if not normalized_value:
        return None
    recent_rows = (
        db.query(models.AdminLoginLog.created_at)
        .filter(
            column == normalized_value,
            models.AdminLoginLog.status == "失败",
            models.AdminLoginLog.created_at >= now_ts - ADMIN_LOGIN_LOCK_DURATION_MINUTES * 60,
        )
        .order_by(models.AdminLoginLog.created_at.desc())
        .limit(ADMIN_LOGIN_LOCK_THRESHOLD)
        .all()
    )
    if len(recent_rows) < ADMIN_LOGIN_LOCK_THRESHOLD:
        return None
    newest_ts = int(recent_rows[0].created_at or 0)
    threshold_ts = int(recent_rows[-1].created_at or 0)
    if newest_ts - threshold_ts > ADMIN_LOGIN_ATTEMPT_WINDOW_MINUTES * 60:
        return None
    locked_until = newest_ts + ADMIN_LOGIN_LOCK_DURATION_MINUTES * 60
    if locked_until <= now_ts:
        return None
    remaining_minutes = max(1, int((locked_until - now_ts + 59) // 60))
    return {
        "locked_until": locked_until,
        "remaining_minutes": remaining_minutes,
        "latest_failure_at": newest_ts,
    }


def get_admin_login_lock_state(db: Session, *, username: str, ip_address: str) -> dict[str, int | str] | None:
    now_ts = int(time.time())
    candidates: list[dict[str, int | str]] = []

    username_lock = _evaluate_lock_scope(db, models.AdminLoginLog.username, username, now_ts)
    if username_lock:
        candidates.append({"scope_label": f"账号 {username}", **username_lock})

    normalized_ip = normalize_ip_address(ip_address)
    if is_security_relevant_ip(normalized_ip):
        ip_lock = _evaluate_lock_scope(db, models.AdminLoginLog.ip_address, normalized_ip, now_ts)
        if ip_lock:
            candidates.append({"scope_label": f"IP {normalized_ip}", **ip_lock})


    if not candidates:
        return None
    return max(candidates, key=lambda item: int(item.get("locked_until") or 0))


def evaluate_admin_login_risk(db: Session, *, username: str, ip_address: str) -> tuple[str, str]:
    now_ts = int(time.time())
    risk_flags: list[str] = []
    normalized_ip = normalize_ip_address(ip_address)
    security_ip = normalized_ip if is_security_relevant_ip(normalized_ip) else ""

    recent_success_rows = (
        db.query(models.AdminLoginLog.ip_address, models.AdminLoginLog.created_at)
        .filter(models.AdminLoginLog.username == username, models.AdminLoginLog.status == "成功")
        .order_by(models.AdminLoginLog.created_at.desc())
        .limit(ADMIN_LOGIN_SUCCESS_IP_LOOKBACK)
        .all()
    )
    recent_success_ips = [
        normalized_success_ip
        for row in recent_success_rows
        for normalized_success_ip in [normalize_ip_address(row.ip_address)]
        if is_security_relevant_ip(normalized_success_ip)
    ]
    latest_success_ip = recent_success_ips[0] if recent_success_ips else ""

    latest_success_at = int(recent_success_rows[0].created_at or 0) if recent_success_rows else 0

    if normalized_ip and recent_success_ips and normalized_ip not in recent_success_ips:
        risk_flags.append("新IP登录")
        if latest_success_ip and latest_success_ip != normalized_ip and latest_success_at >= now_ts - 6 * 3600:
            risk_flags.append("短时IP切换")

    username_fail_count = int(
        db.query(func.count(models.AdminLoginLog.id))
        .filter(
            models.AdminLoginLog.username == username,
            models.AdminLoginLog.status == "失败",
            models.AdminLoginLog.created_at >= now_ts - 24 * 3600,
        )
        .scalar()
        or 0
    )
    ip_fail_count = 0
    if normalized_ip and normalized_ip != "unknown":
        ip_fail_count = int(
            db.query(func.count(models.AdminLoginLog.id))
            .filter(
                models.AdminLoginLog.ip_address == normalized_ip,
                models.AdminLoginLog.status == "失败",
                models.AdminLoginLog.created_at >= now_ts - 24 * 3600,
            )
            .scalar()
            or 0
        )
    if username_fail_count >= ADMIN_LOGIN_RISK_FAILURE_THRESHOLD or ip_fail_count >= ADMIN_LOGIN_RISK_FAILURE_THRESHOLD:
        risk_flags.append("高频失败后成功")

    deduplicated_flags = list(dict.fromkeys(flag for flag in risk_flags if flag))
    if not deduplicated_flags:
        return "正常", ""
    if "高频失败后成功" in deduplicated_flags or len(deduplicated_flags) >= 2:
        return "高危", "、".join(deduplicated_flags)
    return "关注", "、".join(deduplicated_flags)


def build_admin_login_log_message(
    *,
    login_source: str,
    username: str,
    tenant_id: str,
    status: str,
    ip_address: str,
    reason: str,
    risk_level: str,
    risk_flags: str,
) -> str:
    ip_note = "(本机回环/本地代理)" if is_loopback_ip(ip_address) else ""
    log_payload = (
        f"source={login_source} username={username or '-'} tenant_id={tenant_id} "
        f"status={status} ip={ip_address}{ip_note} reason={reason or '-'} risk={risk_level} flags={risk_flags or '-'}"
    )
    if status == "失败" or risk_level == "高危":
        return f"[admin-login] {log_payload}"
    if risk_level == "关注":
        return f"[admin-login-attention] {log_payload}"
    return f"[admin-login] {log_payload}"


def backfill_admin_login_messages(db: Session, *, limit: int = 5000) -> int:
    rows = (
        db.query(models.AdminLoginLog)
        .filter(or_(models.AdminLoginLog.log_message.is_(None), models.AdminLoginLog.log_message == ""))
        .order_by(models.AdminLoginLog.id.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        return 0
    updated_count = 0
    for row in rows:
        row.log_message = build_admin_login_log_message(
            login_source=str(row.login_source or "主后台登录").strip() or "主后台登录",
            username=str(row.username or "").strip(),
            tenant_id=str(row.tenant_id or "tenant_001").strip() or "tenant_001",
            status=str(row.status or "").strip() or "-",
            ip_address=str(row.ip_address or "unknown").strip() or "unknown",
            reason=str(row.reason or "").strip(),
            risk_level=str(row.risk_level or "正常").strip() or "正常",
            risk_flags=str(row.risk_flags or "").strip(),
        )
        updated_count += 1
    if updated_count:
        db.commit()
    return updated_count


def record_admin_login(
    db: Session,
    *,
    request: Request | None,
    username: str,
    tenant_id: str,
    status: str,
    reason: str = "",
    login_source: str = "主后台登录",
    risk_level: str = "正常",
    risk_flags: str = "",
) -> None:
    ip_address = resolve_client_ip(request) or "unknown"
    user_agent = str((request.headers.get("user-agent") if request else "") or "").strip()[:500]
    request_path = str(request.url.path if request else "/api/auth/login")
    normalized_risk_level = str(risk_level or "正常").strip() or "正常"
    normalized_risk_flags = str(risk_flags or "").strip()
    normalized_tenant_id = str(tenant_id or "tenant_001").strip() or "tenant_001"
    normalized_username = str(username or "").strip()
    normalized_reason = str(reason or "").strip()
    log_message = build_admin_login_log_message(
        login_source=login_source,
        username=normalized_username,
        tenant_id=normalized_tenant_id,
        status=status,
        ip_address=ip_address,
        reason=normalized_reason,
        risk_level=normalized_risk_level,
        risk_flags=normalized_risk_flags,
    )

    log_row = models.AdminLoginLog(
        tenant_id=normalized_tenant_id,
        username=normalized_username,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
        login_source=login_source,
        request_path=request_path,
        reason=normalized_reason,
        risk_level=normalized_risk_level,
        risk_flags=normalized_risk_flags,
        log_message=log_message,
        created_at=int(time.time()),
    )
    try:
        db.add(log_row)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning(f"管理员登录日志写入失败: {exc}")

    if status == "失败" or normalized_risk_level == "高危":
        logger.warning(log_message)
    elif normalized_risk_level == "关注":
        logger.warning(log_message)
    else:
        logger.info(log_message)




def pick_disk_account_from_pool(


    db: Session,
    *,
    tenant_id: str,
    preferred_region: str = '',
    exclude_account_id: int | None = None,
):
    load_subquery = (
        db.query(models.CdKey.account_id.label('account_id'), func.count(models.CdKey.id).label('active_key_count'))
        .filter(models.CdKey.status != 2)
        .group_by(models.CdKey.account_id)
        .subquery()
    )

    def build_query(region: str = ''):
        query = (
            db.query(models.DiskAccount)
            .outerjoin(load_subquery, models.DiskAccount.id == load_subquery.c.account_id)
            .filter(models.DiskAccount.tenant_id == tenant_id, models.DiskAccount.status == 1)
        )
        if exclude_account_id is not None:
            query = query.filter(models.DiskAccount.id != exclude_account_id)
        normalized_region = normalize_region(region)
        if normalized_region:
            query = query.filter(models.DiskAccount.region == normalized_region)
        return query.order_by(func.coalesce(load_subquery.c.active_key_count, 0).asc(), models.DiskAccount.id.asc())

    normalized_region = normalize_region(preferred_region)
    if normalized_region:
        account = build_query(normalized_region).first()
        if account is not None:
            return account, normalized_region, True
    account = build_query().first()
    return account, normalize_region(getattr(account, 'region', '')) if account is not None else '', False


# ── 生命周期 ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    redis_client = None
    try:
        redis_candidate = aioredis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        await redis_candidate.ping()
        redis_client = redis_candidate
        QrService.set_redis(redis_client)
        logger.info(f"服务启动，Redis 已连接: {redis_url}")
    except Exception as exc:
        QrService.set_redis(None)
        logger.warning(f"服务启动，Redis 不可用，已降级为内存模式: {exc}")

    try:
        models.Base.metadata.create_all(bind=engine)
        ensure_netdisk_schema()
        mark_database_ready()
        logger.info("服务启动，网盘数据库已连接")
    except SQLAlchemyError as exc:
        mark_database_unavailable(format_database_unavailable_message(exc))
        logger.error(f"服务启动，网盘数据库不可用，已跳过 netdisk 初始化: {exc}")
    except Exception as exc:
        mark_database_unavailable(format_database_unavailable_message(exc))
        logger.error(f"服务启动，网盘数据库初始化失败，已降级停用 netdisk 模块: {exc}")

    kick_task = None

    auto_kick_enabled = str(os.environ.get("ENABLE_AUTO_KICK_DEVICES", "false") or "false").strip().lower() in {"1", "true", "yes", "on"}
    if auto_kick_enabled and is_database_ready():
        logger.info("自动踢设备已启用")
        kick_task = asyncio.create_task(task_kick_devices.auto_kick_task())
    elif auto_kick_enabled:
        logger.warning("自动踢设备已跳过：网盘数据库当前不可用")
    else:
        logger.info("自动踢设备已关闭")

    try:
        yield
    finally:
        if kick_task is not None:
            kick_task.cancel()
            try:
                await kick_task
            except asyncio.CancelledError:
                pass
        if redis_client:
            await redis_client.aclose()
        logger.info("服务关闭")






app = FastAPI(lifespan=lifespan)

SIGNATURE_EXEMPT_PATHS = set()

ADMIN_AUTH_PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/cdkey/redeem",
    "/api/cdkey/switch",
    "/api/cdkey/scan_qr",
}

PLAIN_BODY_COMPATIBLE_PATHS = {
    "/api/auth/login",
}




@app.exception_handler(RequestValidationError)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import traceback
    print(f"Validation Error: {exc.errors()} | Body: {exc.body}"); logger.error(f"Validation Error: {exc.errors()} | Body: {exc.body}")
    traceback.print_exc()
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

from . import api_devices
app.include_router(api_devices.router)








# ── AES 加解密工具（与前端 crypto.js 严格对应）─────────────────

AES_KEY = os.environ.get("AES_KEY", "Bai6u$SaaS#Key16").encode("utf-8")[:16].ljust(16, b'\0')   # 16 字节
AES_IV  = os.environ.get("AES_IV", "Bai6u$SaaS#Iv_16").encode("utf-8")[:16].ljust(16, b'\0')   # 16 字节

def aes_decrypt(ciphertext_b64: str) -> bytes:
    """解密前端发来的 AES-CBC Base64 密文，返回明文 bytes"""
    raw = base64.b64decode(ciphertext_b64)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(raw), AES.block_size)

def aes_encrypt(data: bytes) -> str:
    """加密后端响应为 AES-CBC Base64 密文"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return base64.b64encode(cipher.encrypt(pad(data, AES.block_size))).decode()


def decrypt_request_payload(ciphertext_b64: str) -> bytes:
    normalized_text = str(ciphertext_b64 or "").strip()
    if not normalized_text:
        raise ValueError("请求密文为空")

    decoded_text = unquote(normalized_text)
    candidates: list[str] = []
    for candidate in (
        normalized_text,
        normalized_text.replace(" ", "+"),
        decoded_text,
        decoded_text.replace(" ", "+"),
    ):
        cleaned = str(candidate or "").strip()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return aes_decrypt(candidate)
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise ValueError("请求密文为空")


def _override_request_body(request: Request, plain_bytes: bytes) -> None:
    async def receive():
        return {"type": "http.request", "body": plain_bytes, "more_body": False}

    request._body = plain_bytes
    request._receive = receive

# ── AES 加解密工具 END ──────────────────────────────────────────


from fastapi.middleware.cors import CORSMiddleware

@app.middleware("http")
async def crypto_middleware(request: Request, call_next):
    """优先走服务端会话鉴权；旧客户端仍可通过签名协议访问。"""
    # OPTIONS 直接放行，由 CORS 中间件处理
    if request.method == "OPTIONS":
        return await call_next(request)

    # 提前记录是否需要加密响应（防止 request 被重新赋值后丢失 headers）
    need_encrypt = request.headers.get("X-Encrypted") == "1"

    if request.url.path.startswith("/api/"):
        session_payload = get_admin_session_from_request(request)
        is_public_api = request.url.path in ADMIN_AUTH_PUBLIC_PATHS
        has_signature_headers = bool(
            request.headers.get("X-Timestamp")
            and request.headers.get("X-Nonce")
            and request.headers.get("X-Signature")
        )

        if not is_public_api and session_payload is None:
            if has_signature_headers and request.url.path not in SIGNATURE_EXEMPT_PATHS:
                # 1. 兼容旧客户端：仍允许通过签名协议访问
                try:
                    await verify_signature(request)
                except HTTPException as e:
                    logger.warning(f"签名校验失败: {e.detail} | Path: {request.url.path}")
                    return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
            else:
                return JSONResponse(status_code=401, content={"detail": "登录状态已失效，请重新登录"})
        elif not is_public_api and session_payload is not None:
            try:
                enforce_admin_session_allowed_ip(request, session_payload)
            except HTTPException as e:
                logger.warning(f"管理员会话 IP 绑定校验失败: {e.detail} | Path: {request.url.path}")
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

        # 2. 如果请求头带 X-Encrypted: 1，解密请求体后替换


        if need_encrypt:
            try:
                raw_body = await request.body()
                if raw_body:
                    payload = json.loads(raw_body)
                    cipher_b64 = payload.get("d", "") if isinstance(payload, dict) else ""
                    if cipher_b64:
                        plain = decrypt_request_payload(cipher_b64)
                        plain_bytes = plain if isinstance(plain, bytes) else plain.encode("utf-8")
                        _override_request_body(request, plain_bytes)
                    elif (
                        request.url.path in PLAIN_BODY_COMPATIBLE_PATHS
                        and isinstance(payload, dict)
                        and payload.get("username") is not None
                        and payload.get("password") is not None
                    ):
                        _override_request_body(request, raw_body)
                        logger.warning(f"{request.url.path} 收到带 X-Encrypted 的明文请求体，已自动兼容处理")
            except Exception as e:
                logger.warning(f"AES 解密请求体失败: {e}")
                return JSONResponse(status_code=400, content={"detail": "请求数据解密失败"})

    # 3. 调用实际路由
    response = await call_next(request)


    # 4. 如果客户端带了 X-Encrypted: 1，则加密响应体
    if need_encrypt and response.status_code == 200:
        try:
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk
            encrypted = aes_encrypt(resp_body)
            return JSONResponse(
                content={"d": encrypted},
                status_code=200,
                headers={"X-Encrypted": "1"},
            )
        except Exception as e:
            logger.error(f"AES 加密响应体失败: {e}")
            return JSONResponse(status_code=500, content={"detail": "内部加密错误"})

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Encrypted"],
)



@app.exception_handler(Exception)
async def _global_err(req, exc):
    logger.exception(f"未捕获异常: {exc}")
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})

# ── 工具 ──────────────────────────────────────────────────────
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "SaaS_Baidu_Super_Secret_Key_2026!")
SIGNATURE_REPLAY_TTL_SECONDS = 360
ADMIN_SESSION_COOKIE_NAME = str(os.environ.get("ADMIN_SESSION_COOKIE_NAME", "pan_saas_session") or "pan_saas_session").strip() or "pan_saas_session"
ADMIN_SESSION_TTL_SECONDS = int(os.environ.get("ADMIN_SESSION_TTL_SECONDS", 12 * 60 * 60) or 12 * 60 * 60)
ADMIN_SESSION_COOKIE_SECURE = str(os.environ.get("ADMIN_SESSION_COOKIE_SECURE", "false") or "false").strip().lower() in {"1", "true", "yes", "on"}


def _urlsafe_b64encode_text(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _urlsafe_b64decode_text(value: str) -> str:
    normalized = str(value or "").strip()
    padding = "=" * (-len(normalized) % 4)
    return base64.urlsafe_b64decode(f"{normalized}{padding}".encode("ascii")).decode("utf-8")


def build_admin_session_token(*, username: str, tenant_id: str, role: str) -> str:
    now_ts = int(time.time())
    payload = {
        "sub": str(username or "").strip(),
        "tenant_id": str(tenant_id or "tenant_001").strip() or "tenant_001",
        "role": str(role or "admin").strip() or "admin",
        "iat": now_ts,
        "exp": now_ts + ADMIN_SESSION_TTL_SECONDS,
    }
    encoded_payload = _urlsafe_b64encode_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    signature = hmac.new(API_SECRET_KEY.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def parse_admin_session_token(token: str | None) -> dict[str, str | int] | None:
    raw_token = str(token or "").strip()
    if not raw_token or "." not in raw_token:
        return None
    encoded_payload, received_signature = raw_token.rsplit(".", 1)
    expected_signature = hmac.new(API_SECRET_KEY.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_signature, expected_signature):
        return None
    try:
        payload = json.loads(_urlsafe_b64decode_text(encoded_payload))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp_ts = int(payload.get("exp") or 0)
    if exp_ts <= int(time.time()):
        return None
    username = str(payload.get("sub") or "").strip()
    if not username:
        return None
    return {
        "sub": username,
        "tenant_id": str(payload.get("tenant_id") or "tenant_001").strip() or "tenant_001",
        "role": str(payload.get("role") or "admin").strip() or "admin",
        "iat": int(payload.get("iat") or 0),
        "exp": exp_ts,
    }


def get_admin_session_from_request(request: Request | None) -> dict[str, str | int] | None:
    if request is None:
        return None
    cached_session = getattr(getattr(request, "state", None), "admin_session", None)
    if cached_session is not None:
        return cached_session
    cookies = getattr(request, "cookies", None) or {}
    session_token = cookies.get(ADMIN_SESSION_COOKIE_NAME)
    session_payload = parse_admin_session_token(session_token)
    if getattr(request, "state", None) is not None:
        request.state.admin_session = session_payload
    return session_payload


def current_admin_binding_time_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_global_allowed_ip_for_username(
    db: Session,
    *,
    username: str,
    current_ip: str | None,
    request: Request | None = None,
    create_if_missing: bool = True,
    is_admin: bool = False,
) -> str:

    normalized_username = str(username or "").strip()
    if not normalized_username:
        return ""

    normalized_current_ip = normalize_ip_address(current_ip)
    user_row = db.query(models.XianyuUser).filter_by(username=normalized_username).first()
    if user_row is None:
        if not create_if_missing:
            return ""
        timestamp_text = current_admin_binding_time_text()
        user_row = models.XianyuUser(
            username=normalized_username,
            is_admin=bool(is_admin),
            created_at=timestamp_text,
            updated_at=timestamp_text,
            payload={
                "username": normalized_username,
                "is_admin": bool(is_admin),
                "created_at": timestamp_text,
                "updated_at": timestamp_text,
            },
        )
        db.add(user_row)
        db.flush()

    if bool(is_admin) and not bool(user_row.is_admin):
        user_row.is_admin = True

    allowed_ip = normalize_ip_address(getattr(user_row, "allowed_ip", ""))
    if allowed_ip and normalized_current_ip and allowed_ip != normalized_current_ip:
        if request is not None and is_request_from_trusted_origin(request):
            return allowed_ip
        raise HTTPException(status_code=403, detail="当前网络环境未被授权，请在绑定设备上登录")

    if not allowed_ip and normalized_current_ip:

        timestamp_text = current_admin_binding_time_text()
        user_row.allowed_ip = normalized_current_ip
        if not str(getattr(user_row, "created_at", "") or "").strip():
            user_row.created_at = timestamp_text
        user_row.updated_at = timestamp_text
        payload = deepcopy(user_row.payload) if isinstance(getattr(user_row, "payload", None), dict) else {}
        payload.update({
            "username": normalized_username,
            "is_admin": bool(user_row.is_admin),
            "allowed_ip": normalized_current_ip,
            "created_at": str(getattr(user_row, "created_at", "") or timestamp_text),
            "updated_at": timestamp_text,
        })
        user_row.payload = payload
        db.add(user_row)
        return normalized_current_ip

    return allowed_ip


def enforce_admin_session_allowed_ip(request: Request, session_payload: dict[str, str | int] | None = None) -> dict[str, str | int]:
    resolved_session = session_payload or get_admin_session_from_request(request)
    if resolved_session is None:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")

    state = getattr(request, "state", None)
    if state is not None and getattr(state, "admin_session_ip_verified", False):
        return resolved_session

    ensure_database_ready()
    db = SessionLocal()

    try:
        ensure_global_allowed_ip_for_username(
            db,
            username=str(resolved_session.get("sub") or "").strip(),
            current_ip=resolve_client_ip(request),
            request=request,
            create_if_missing=True,
            is_admin=str(resolved_session.get("role") or "admin").strip().lower() == "admin",
        )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.warning(f"管理员会话 IP 绑定校验失败: {exc}")
        raise HTTPException(status_code=500, detail="登录环境校验失败，请稍后重试") from exc
    finally:
        db.close()

    if state is not None:
        state.admin_session_ip_verified = True
    return resolved_session


def require_admin_session(request: Request) -> dict[str, str | int]:
    session_payload = get_admin_session_from_request(request)
    if session_payload is None:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return enforce_admin_session_allowed_ip(request, session_payload)


def set_admin_session_cookie(response: Response, *, username: str, tenant_id: str, role: str) -> None:

    response.set_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        value=build_admin_session_token(username=username, tenant_id=tenant_id, role=role),
        httponly=True,
        secure=ADMIN_SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=ADMIN_SESSION_TTL_SECONDS,
        path="/",
    )


def clear_admin_session_cookie(response: Response) -> None:
    response.delete_cookie(key=ADMIN_SESSION_COOKIE_NAME, path="/", samesite="lax")


def build_request_signature_path(request: Request) -> str:

    query_pairs = sorted(
        ((str(key), str(value)) for key, value in request.query_params.multi_items()),
        key=lambda item: (item[0], item[1]),
    )
    query_text = urlencode(query_pairs, doseq=True)
    return f"{request.url.path}?{query_text}" if query_text else request.url.path


def compute_request_body_hash(raw_body: bytes | None) -> str:
    return hashlib.sha256(raw_body or b"").hexdigest()


def build_v2_signature_payload(*, ts: str, nonce: str, method: str, request_path: str, body_hash: str) -> str:
    return "\n".join([
        str(ts or ""),
        str(nonce or ""),
        str(method or "GET").upper(),
        str(request_path or "/"),
        str(body_hash or ""),
    ])


async def ensure_nonce_not_replayed(nonce: str) -> None:
    normalized_nonce = str(nonce or "").strip()
    if not normalized_nonce:
        raise HTTPException(status_code=403, detail="非法的随机串")

    if redis_client:
        try:
            is_replayed = await redis_client.get(f"replay_nonce:{normalized_nonce}")
            if is_replayed:
                raise HTTPException(status_code=403, detail="请求已处理，请勿重复发送 (Replay attack detected)")
            await redis_client.setex(f"replay_nonce:{normalized_nonce}", SIGNATURE_REPLAY_TTL_SECONDS, "1")
            return
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Redis 连接或读取超时，改用本地内存执行防重放校验: {e}")

    now_ts = int(time.time())
    async with local_replay_cache_lock:
        expired_keys = [key for key, expires_at in local_replay_cache.items() if expires_at <= now_ts]
        for key in expired_keys:
            local_replay_cache.pop(key, None)
        existing_expires_at = int(local_replay_cache.get(normalized_nonce) or 0)
        if existing_expires_at > now_ts:
            raise HTTPException(status_code=403, detail="请求已处理，请勿重复发送 (Replay attack detected)")
        local_replay_cache[normalized_nonce] = now_ts + SIGNATURE_REPLAY_TTL_SECONDS


async def verify_signature(request: Request):

    """校验前端接口签名防爬防重放"""
    # 允许不带签名的静态资源或开放接口
    if request.url.path in ["/docs", "/openapi.json"] or not request.url.path.startswith("/api/"):
        return

    ts = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    sign = request.headers.get("X-Signature")
    signature_version = str(request.headers.get("X-Signature-Version") or "v1").strip().lower()

    if not ts or not nonce or not sign:
        raise HTTPException(status_code=403, detail="请求缺失签名头 (Missing signature)")

    try:
        req_time = int(ts)
        now_time = int(time.time() * 1000)
        # 允许前后5分钟的时间差
        if abs(now_time - req_time) > 300 * 1000:
            logger.error(f"时间戳过期: client={req_time}, server={now_time}, diff={abs(now_time - req_time)}")
            raise HTTPException(status_code=403, detail="请求已过期 (Timestamp expired)")
    except ValueError:
        raise HTTPException(status_code=403, detail="非法的时间戳")

    if signature_version == "v2":
        raw_body = await request.body()
        received_body_hash = str(request.headers.get("X-Content-SHA256") or "").strip().lower()
        expected_body_hash = compute_request_body_hash(raw_body)
        if not received_body_hash:
            raise HTTPException(status_code=403, detail="请求缺少内容摘要头")
        if not hmac.compare_digest(received_body_hash, expected_body_hash):
            raise HTTPException(status_code=403, detail="请求体摘要校验失败")

        request_path = build_request_signature_path(request)
        sign_payload = build_v2_signature_payload(
            ts=ts,
            nonce=nonce,
            method=request.method,
            request_path=request_path,
            body_hash=expected_body_hash,
        )
        expected_sign = hmac.new(
            API_SECRET_KEY.encode("utf-8"),
            sign_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sign, expected_sign):
            raise HTTPException(status_code=403, detail="签名校验失败 (Invalid signature)")
    else:
        # 兼容旧版签名算法: md5(ts + nonce + API_SECRET_KEY)
        legacy_text = f"{ts}{nonce}{API_SECRET_KEY}"
        expected_sign = hashlib.md5(legacy_text.encode('utf-8')).hexdigest()
        if sign != expected_sign:
            raise HTTPException(status_code=403, detail="签名校验失败 (Invalid signature)")

    await ensure_nonce_not_replayed(nonce)


def get_tenant(x_tenant_id: str = Header(None)) -> str:
    return x_tenant_id or "tenant_001"

# ══════════════════════════════════════════════════════════════
# 登录（使用数据库验证）
# ══════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    username = str(body.username or "").strip()
    request_tenant_id = str(request.headers.get("X-Tenant-Id") or "tenant_001").strip() or "tenant_001"
    current_ip = resolve_client_ip(request) or "unknown"

    lock_state = get_admin_login_lock_state(db, username=username, ip_address=current_ip)
    if lock_state:
        lock_message = build_lock_message(lock_state)
        record_admin_login(
            db,
            request=request,
            username=username,
            tenant_id=request_tenant_id,
            status="失败",
            reason=lock_message,
            risk_level="高危",
            risk_flags="触发登录锁定",
        )
        raise HTTPException(status_code=429, detail=lock_message)

    # 从数据库的 AdminUser 表中查询账号和密码
    user = db.query(models.AdminUser).filter_by(username=username).first()
    if not user:
        record_admin_login(
            db,
            request=request,
            username=username,
            tenant_id=request_tenant_id,
            status="失败",
            reason="用户不存在",
            risk_level="关注",
            risk_flags="未知用户尝试",
        )
        latest_lock_state = get_admin_login_lock_state(db, username=username, ip_address=current_ip)
        if latest_lock_state:
            raise HTTPException(status_code=429, detail=build_lock_message(latest_lock_state))
        raise HTTPException(status_code=401, detail="账号或密码错误")

    password_matched, needs_upgrade = verify_admin_password(user.password, body.password)
    if not password_matched:
        record_admin_login(
            db,
            request=request,
            username=username,
            tenant_id=user.tenant_id or request_tenant_id,
            status="失败",
            reason="密码错误",
            risk_level="关注",
            risk_flags="密码校验失败",
        )
        latest_lock_state = get_admin_login_lock_state(db, username=username, ip_address=current_ip)
        if latest_lock_state:
            raise HTTPException(status_code=429, detail=build_lock_message(latest_lock_state))
        raise HTTPException(status_code=401, detail="账号或密码错误")

    try:
        ensure_global_allowed_ip_for_username(
            db,
            username=user.username,
            current_ip=current_ip,
            request=request,
            create_if_missing=True,
            is_admin=str(user.role or "admin").strip().lower() == "admin",
        )

    except HTTPException as exc:
        db.rollback()
        record_admin_login(
            db,
            request=request,
            username=user.username,
            tenant_id=user.tenant_id or request_tenant_id,
            status="失败",
            reason=str(exc.detail),
            risk_level="高危",
            risk_flags="绑定设备校验失败",
        )
        raise

    if needs_upgrade:
        user.password = hash_admin_password(body.password)

    risk_level, risk_flags = evaluate_admin_login_risk(db, username=user.username, ip_address=current_ip)

    record_admin_login(
        db,
        request=request,
        username=user.username,
        tenant_id=user.tenant_id or request_tenant_id,
        status="成功",
        reason="登录成功",
        risk_level=risk_level,
        risk_flags=risk_flags,
    )
    set_admin_session_cookie(response, username=user.username, tenant_id=user.tenant_id, role=user.role)
    return {"tenant_id": user.tenant_id, "username": user.username, "role": user.role}


@app.post("/api/auth/logout")
def logout(response: Response):
    clear_admin_session_cookie(response)
    return {"status": "success"}

@app.get("/api/auth/info")
def auth_info(request: Request):
    session_payload = require_admin_session(request)
    return {
        "tenant_id": session_payload["tenant_id"],
        "username": session_payload["sub"],
        "role": session_payload["role"],
        "authenticated": True,
    }


@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    account_summary = db.query(
        func.coalesce(func.sum(case((models.DiskAccount.status == 1, 1), else_=0)), 0).label("online_count"),
        func.coalesce(func.sum(case((models.DiskAccount.status != 1, 1), else_=0)), 0).label("offline_count"),
    ).filter(
        models.DiskAccount.tenant_id == tenant_id,
    ).one()
    cdkey_summary = db.query(
        func.coalesce(func.sum(case((models.CdKey.status == 0, 1), else_=0)), 0).label("unused_keys"),
        func.coalesce(func.sum(case((models.CdKey.status == 1, 1), else_=0)), 0).label("used_keys"),
        func.coalesce(func.sum(case((models.CdKey.status == 2, 1), else_=0)), 0).label("voided_keys"),
    ).filter(
        models.CdKey.tenant_id == tenant_id,
    ).one()
    return {
        "online_count": int(account_summary.online_count or 0),
        "offline_count": int(account_summary.offline_count or 0),
        "unused_keys": int(cdkey_summary.unused_keys or 0),
        "used_keys": int(cdkey_summary.used_keys or 0),
        "voided_keys": int(cdkey_summary.voided_keys or 0),
    }


@app.get("/api/auth/login-logs")
def get_admin_login_logs(

    limit: int = Query(200, ge=1, le=500),
    status: str | None = Query(None),
    username: str | None = Query(None),
    ip_address: str | None = Query(None),
    risk_level: str | None = Query(None),
    hours: int = Query(168, ge=0, le=24 * 90),
    db: Session = Depends(get_db),
):
    now_ts = int(time.time())
    filters = []

    normalized_username = str(username or "").strip()
    if normalized_username:
        filters.append(models.AdminLoginLog.username.ilike(f"%{normalized_username}%"))

    normalized_ip = str(ip_address or "").strip()
    if normalized_ip:
        filters.append(models.AdminLoginLog.ip_address.ilike(f"%{normalized_ip}%"))

    if hours > 0:
        filters.append(models.AdminLoginLog.created_at >= now_ts - hours * 3600)

    normalized_status = normalize_login_status(status)
    normalized_risk_level = str(risk_level or "").strip()

    logs_query = db.query(models.AdminLoginLog).filter(*filters)
    if normalized_status:
        logs_query = logs_query.filter(models.AdminLoginLog.status == normalized_status)
    if normalized_risk_level:
        logs_query = logs_query.filter(models.AdminLoginLog.risk_level == normalized_risk_level)

    rows = logs_query.order_by(models.AdminLoginLog.created_at.desc(), models.AdminLoginLog.id.desc()).limit(limit).all()
    summary_row = db.query(
        func.count(models.AdminLoginLog.id).label("total_count"),
        func.coalesce(func.sum(case((models.AdminLoginLog.status == "成功", 1), else_=0)), 0).label("success_count"),
        func.coalesce(func.sum(case((models.AdminLoginLog.status == "失败", 1), else_=0)), 0).label("failed_count"),
        func.count(func.distinct(models.AdminLoginLog.ip_address)).label("unique_ip_count"),
        func.coalesce(func.sum(case((models.AdminLoginLog.risk_level == "关注", 1), else_=0)), 0).label("attention_count"),
        func.coalesce(func.sum(case((models.AdminLoginLog.risk_level == "高危", 1), else_=0)), 0).label("high_risk_count"),
    ).filter(*filters).one()

    suspicious_rows = (
        db.query(
            models.AdminLoginLog.ip_address.label("ip_address"),
            func.count(models.AdminLoginLog.id).label("fail_count"),
            func.max(models.AdminLoginLog.created_at).label("last_seen"),
        )
        .filter(*filters, models.AdminLoginLog.status == "失败")
        .group_by(models.AdminLoginLog.ip_address)
        .having(func.count(models.AdminLoginLog.id) >= ADMIN_LOGIN_SUSPICIOUS_IP_THRESHOLD)
        .order_by(func.count(models.AdminLoginLog.id).desc(), func.max(models.AdminLoginLog.created_at).desc())
        .limit(10)
        .all()
    )

    active_lock_candidates = (
        db.query(models.AdminLoginLog.username, models.AdminLoginLog.ip_address)
        .filter(
            *filters,
            models.AdminLoginLog.status == "失败",
            models.AdminLoginLog.created_at >= now_ts - ADMIN_LOGIN_LOCK_DURATION_MINUTES * 60,
            or_(models.AdminLoginLog.username != "", models.AdminLoginLog.ip_address != "unknown"),
        )
        .order_by(models.AdminLoginLog.created_at.desc())
        .limit(200)
        .all()
    )
    active_locks = []
    seen_lock_keys = set()
    lock_state_cache: dict[tuple[str, str], dict[str, int | str] | None] = {}
    for row in active_lock_candidates:
        username_value = str(row.username or "").strip()
        ip_value = str(row.ip_address or "").strip()
        cache_key = (username_value, ip_value)
        if cache_key not in lock_state_cache:
            lock_state_cache[cache_key] = get_admin_login_lock_state(db, username=username_value, ip_address=ip_value)
        lock_state = lock_state_cache[cache_key]
        if not lock_state:
            continue
        lock_key = (str(lock_state.get("scope_label") or ""), int(lock_state.get("locked_until") or 0))
        if lock_key in seen_lock_keys:
            continue
        seen_lock_keys.add(lock_key)
        active_locks.append(
            {
                "scope_label": str(lock_state.get("scope_label") or ""),
                "locked_until": int(lock_state.get("locked_until") or 0),
                "remaining_minutes": int(lock_state.get("remaining_minutes") or 0),
            }
        )
        if len(active_locks) >= 10:
            break

    return {
        "logs": [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "username": row.username,
                "status": row.status,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "login_source": row.login_source,
                "request_path": row.request_path,
                "reason": row.reason,
                "risk_level": row.risk_level,
                "risk_flags": row.risk_flags,
                "log_message": row.log_message,
                "created_at": row.created_at,

            }
            for row in rows
        ],
        "summary": {
            "total": int(summary_row.total_count or 0),
            "success": int(summary_row.success_count or 0),
            "failed": int(summary_row.failed_count or 0),
            "unique_ip_count": int(summary_row.unique_ip_count or 0),
            "attention_count": int(summary_row.attention_count or 0),
            "high_risk_count": int(summary_row.high_risk_count or 0),
            "suspicious_ip_count": len(suspicious_rows),
            "window_hours": hours,
            "lock_threshold": ADMIN_LOGIN_LOCK_THRESHOLD,
            "lock_window_minutes": ADMIN_LOGIN_ATTEMPT_WINDOW_MINUTES,
            "lock_duration_minutes": ADMIN_LOGIN_LOCK_DURATION_MINUTES,
            "top_failed_ips": [
                {
                    "ip_address": row.ip_address,
                    "fail_count": int(row.fail_count or 0),
                    "last_seen": int(row.last_seen or 0),
                }
                for row in suspicious_rows
            ],
            "active_locks": active_locks,
        },
    }




# ══════════════════════════════════════════════════════════════
# 百度二维码登录（对应 Spring Boot BaiduQrLoginController）
# ══════════════════════════════════════════════════════════════



@app.get("/api/baidu/get_qr", response_model=QrCodeResponse)
async def get_qr():
    """生成百度登录二维码。"""
    try:
        result = await QrService.generate_qr_code()
        return QrCodeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/baidu/check_status", response_model=StatusResponse)
async def check_status(
    sign: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant),
):
    """轮询扫码状态。"""
    result = await QrService.check_login_status(sign, tenant_id, db)
    return StatusResponse(**result)


# ══════════════════════════════════════════════════════════════
# 账号 & 卡密管理（对应 Spring Boot AccountController）
# ══════════════════════════════════════════════════════════════

@app.get("/api/account/assign", response_model=list[DiskAccountOut])
def get_account_list(
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """获取当前租户的网盘账号列表。避免在读接口中执行耗时的地区推断。"""
    return db.query(models.DiskAccount).filter_by(tenant_id=tenant_id).all()




@app.post("/api/cdkey/generate", response_model=KeysResponse)
def generate_keys(
    account_id: int | None = Query(None, description="绑定的网盘账号 ID"),
    region: str | None = Query(None, description="按地区自动选择账号池"),
    count: int = Query(..., ge=1, le=100, description="生成数量"),
    days:  int = Query(..., ge=1, le=3650, description="授权天数"),
    max_uses: int = Query(0, ge=0, description="最大授权次数，0=不限"),
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """为指定账号或地区账号池批量生成卡密。"""
    normalized_region = normalize_region(region)
    if account_id is not None:
        acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail="账号不存在")
    else:
        if not normalized_region:
            raise HTTPException(status_code=400, detail="请先选择绑定账户或地区账号池")
        acc, selected_region, exact_match = pick_disk_account_from_pool(db, tenant_id=tenant_id, preferred_region=normalized_region)
        if not acc:
            raise HTTPException(status_code=404, detail="当前地区账号池没有可用账号")
        normalized_region = selected_region
        if not exact_match:
            logger.warning(f"[cdkey] 地区池 {region} 无可用账号，已回退到地区 {selected_region or '未设置'} 的账号 {acc.username}")

    keys = []
    for _ in range(count):
        code = str(uuid.uuid4()).upper().replace("-", "")[:16]
        db.add(models.CdKey(tenant_id=tenant_id, key_code=code,
                            duration=days, account_id=acc.id, max_uses=max_uses))
        keys.append(code)
    db.commit()
    return KeysResponse(status="success", keys=keys, account_id=acc.id, account_name=acc.username, region=normalize_region(getattr(acc, 'region', '')))



@app.get("/api/cdkey/list", response_model=list[CdKeyOut])
def list_keys(
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """查询当前租户的卡密列表，同时批量更新超出宽限期的卡密状态。"""
    now = int(time.time())
    expired_updated = (
        db.query(models.CdKey)
        .filter(
            models.CdKey.tenant_id == tenant_id,
            models.CdKey.expires_at.isnot(None),
            models.CdKey.expires_at < now - CDKEY_VOID_GRACE_SECONDS,
            models.CdKey.status != 2,
        )
        .update({models.CdKey.status: 2}, synchronize_session=False)
    )
    if expired_updated:
        db.commit()
    return db.query(models.CdKey).filter_by(tenant_id=tenant_id).all()


@app.delete("/api/cdkey/clean_expired")
def clean_expired_keys(
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """清理/作废所有已过宽限期或已作废的卡密。"""
    now = int(time.time())
    keys = db.query(models.CdKey).filter_by(tenant_id=tenant_id).all()
    count = 0
    for key in keys:
        if key.status == 2 or is_cdkey_expired(key, now_ts=now):
            db.delete(key)
            count += 1
    db.commit()
    return {"status": "success", "msg": f"清理了 {count} 个过期/作废卡密"}


@app.delete("/api/cdkey/{key_id}")
def delete_key(
    key_id: int,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """作废指定卡密。"""
    key = db.query(models.CdKey).filter_by(id=key_id, tenant_id=tenant_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="卡密不存在")
    key.status = 2
    db.commit()
    return {"status": "success"}


@app.post("/api/cdkey/switch")
def switch_account(code: str, db: Session = Depends(get_db)):
    """自助换号：优先在同地区账号池中切换到另一个正常账号。"""
    key = db.query(models.CdKey).filter_by(key_code=code).first()
    if not key:
        raise HTTPException(status_code=404, detail="卡密不存在")
    if mark_cdkey_void_if_expired(key):
        db.commit()
        raise HTTPException(status_code=410, detail="卡密已作废")

    current_region = normalize_region(getattr(key.account, 'region', '') if key.account else '')
    new_acc, selected_region, exact_match = pick_disk_account_from_pool(
        db,
        tenant_id=key.tenant_id,
        preferred_region=current_region,
        exclude_account_id=key.account_id,
    )
    if not new_acc:
        raise HTTPException(status_code=503, detail="暂无可用账号，请联系管理员")

    key.account_id = new_acc.id
    db.commit()
    return {
        "status": "success",
        "username": new_acc.username,
        "cookie": new_acc.cookie,
        "duration": key.duration,
        "vip_level": new_acc.vip_level,
        "avatar_url": new_acc.avatar_url or "",
        "region": normalize_region(getattr(new_acc, 'region', '')),
        "region_match": bool(exact_match) if current_region else True,
        "region_message": (
            f"已优先分配同地区账号池：{selected_region}" if current_region and exact_match else
            f"同地区账号池暂时无可用账号，已回退到地区 {selected_region or '未设置'} 的账号" if current_region else
            "原账号未设置地区，已按低负载策略分配账号"
        ),
    }



@app.post("/api/cdkey/scan_qr")
async def scan_qr_for_account(code: str, sign: str, db: Session = Depends(get_db)):
    """
    用租赁账号的 Cookie 通过 Playwright 打开二维码确认页，
    点击「确认登录」按钮，完成用户浏览器的扫码登录。
    """
    import asyncio as _asyncio
    from concurrent.futures import ThreadPoolExecutor

    key = db.query(models.CdKey).filter_by(key_code=code).first()
    if not key:
        raise HTTPException(status_code=404, detail="卡密不存在")
    if mark_cdkey_void_if_expired(key):
        db.commit()
        raise HTTPException(status_code=410, detail="卡密已过期")
    if not key.account or key.account.status != 1:
        raise HTTPException(status_code=503, detail="关联账号不可用")

    cookie_str = key.account.cookie
    confirm_url = (
        f"https://wappass.baidu.com/wp/?qrlogin"
        f"&sign={sign}&cmd=login&lp=pc&tpl=netdisk&adapter=3"
    )

    def _do_confirm():
        from playwright.sync_api import sync_playwright
        from .service.proxy_service import parse_proxy_url
        
        # 解析该账号绑定的专属代理 (如未绑定则为 None)
        proxy_config = parse_proxy_url(key.account.proxy_url)
        
        with sync_playwright() as pw:
            launch_args = QrService.build_chromium_launch_kwargs(headless=True, proxy=proxy_config)
            if proxy_config:
                logger.debug(f"[scan_qr] launching browser with proxy: {proxy_config['server']}")

            browser = pw.chromium.launch(**launch_args)

            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
                viewport={"width": 390, "height": 844},
                locale="zh-CN",
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )

            logger.debug(f"[scan_qr] account: {key.account.username}, cookie_len={len(cookie_str)}")

            # 解析 Cookie 字符串并注入到 Context 中（绕过跨域和重定向丢失 headers 的问题）
            cookies = []
            for pair in cookie_str.split(';'):
                if '=' in pair:
                    k, v = pair.strip().split('=', 1)
                    cookies.append({
                        "name": k,
                        "value": v,
                        "domain": ".baidu.com",
                        "path": "/"
                    })
            ctx.add_cookies(cookies)

            # 拦截 API 响应和静态资源加速加载
            api_responses = []
            def on_response(resp):
                if any(x in resp.url for x in ["qrcode", "qrlogin", "qrconfirm", "passport"]):
                    try:
                        api_responses.append({"url": resp.url, "status": resp.status, "body": resp.text()[:300]})
                    except Exception:
                        api_responses.append({"url": resp.url, "status": resp.status})

            def on_route(route):
                req = route.request
                # 阻止图片、字体、CSS加载，极大提升渲染和加载速度
                if req.resource_type in ["image", "media", "font", "stylesheet"]:
                    route.abort()
                    return
                route.continue_()

            page = ctx.new_page()
            page.route("**/*", on_route)
            page.on("response", on_response)
            
            logger.debug(f"[scan_qr] opening confirm page: {confirm_url}")

            navigated_urls = []
            page.on("framenavigated", lambda f: navigated_urls.append(f.url) if f == page.main_frame else None)

            # 跳转到页面，只要 DOM 加载完就不再硬等
            page.goto(confirm_url, wait_until="domcontentloaded", timeout=15000)

            # 智能等待重定向或关键元素出现（替代固定死等6秒的离线策略）
            try:
                page.wait_for_function("""() => {
                    const url = window.location.href;
                    if (url.includes('insert_account') || url.includes('authwidget') || url.includes('offline=')) return true;
                    const btns = document.querySelectorAll('button, a, input[type="button"], input[type="submit"]');
                    for (let b of btns) {
                        const txt = (b.value || b.textContent || '').trim();
                        if (['确认登录', '确定', '确认', '授权登录', '登录', '同意并登录'].includes(txt)) {
                            if (b.id !== 'qrcodeWarnSure' && b.id !== 'switchAccount') return true;
                        }
                    }
                    return false;
                }""", timeout=8000)
            except Exception:
                pass

            logger.debug(f"[scan_qr] current url after wait: {page.url}")

            clicked = False

            # 情况A: insert_account 页面（需勾选协议 + 点下一步）
            if "insert_account" in page.url:
                logger.debug("[scan_qr] on insert_account page")
                try:
                    # 用 Playwright 原生 click（触发完整鼠标事件，Vue 才能响应）
                    try:
                        page.locator("button.aggreement-button").click(timeout=3000)
                        logger.debug("[scan_qr] agree button native clicked")
                    except Exception as ex:
                        logger.debug(f"[scan_qr] agree click error: {ex}")

                    # 等 Vue 响应，按钮 disable class 被移除（最多5秒）
                    try:
                        page.wait_for_selector(
                            'button.na-submit-button-new:not(.na-submit-button-disable-new)',
                            timeout=5000
                        )
                        logger.debug("[scan_qr] 下一步 button is now enabled")
                    except Exception:
                        logger.debug("[scan_qr] 下一步 still disabled after 5s, clicking anyway")

                    # 原生 click 下一步
                    try:
                        page.locator("button.na-submit-button-new").click(timeout=3000, force=True)
                        clicked = True
                        logger.debug("[scan_qr] clicked 下一步 ✓")
                    except Exception as ex:
                        logger.debug(f"[scan_qr] 下一步 click error: {ex}")

                    page.wait_for_timeout(1000)
                    logger.debug(f"[scan_qr] after next step, url={page.url}")
                except Exception as ex:
                    logger.debug(f"[scan_qr] insert_account error: {ex}")

            # 情况B: 有「确认登录」按钮的页面（正常情况或倒计时页面）
            elif "authwidget" not in page.url:
                try:
                    # 兼容 button 和 input[type="button"]（如 #qrcodeLogin-sure）
                    # 百度网盘异地扫码会有 5 秒倒计时，倒计时期间会有 value="确认登录(5S)" 且禁用。
                    # 所以要精确匹配 value="确认登录" 或者不带 Disable class 的按钮
                    page.wait_for_selector("input[value='确认登录'], button:text-is('确认登录')", timeout=10000)
                    page.evaluate("""() => {
                        const el = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]'))
                            .find(b => {
                                const txt = (b.value || b.textContent || '').trim();
                                return txt === '确认登录';
                            });
                        if (el) el.click();
                    }""")
                    clicked = True
                    logger.debug("[scan_qr] clicked 确认登录 ✓")
                except Exception as ex:
                    logger.debug(f"[scan_qr] 确认登录 not found, url={page.url}")

            # 额外检查：是否被重定向到了“身份验证”页面（即需要手机验证码拦截）
            # 这是因为百度异地登录风控触发，会强制要求号主手机接收验证码验证
            try:
                page.wait_for_function("""() => {
                    const url = window.location.href;
                    return url.includes('authwidget') || document.title.includes('身份验证') || document.title.includes('成功');
                }""", timeout=2000)
            except Exception:
                pass
            if "authwidget" in page.url or page.title() == "身份验证":
                logger.debug(f"[scan_qr] account blocked by risk control (auth_verify_type), url={page.url}")
                # 强制置为 False，让外层知道扫码其实并没有成功，需要号主人工解除风控或接收验证码
                clicked = False
                final_title = "百度安全中心-身份验证(异地风控拦截)"
            else:
                final_title = page.title()

            # 情况C: 兜底匹配其他类似文案的按钮
            if not clicked and "authwidget" not in page.url and final_title != "百度安全中心-身份验证(异地风控拦截)":
                result_js = page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]'));
                    const validBtns = btns.filter(b => b.id !== 'qrcodeWarnSure' && b.id !== 'switchAccount');
                    const btn = validBtns.find(b => {
                        const txt = (b.value || b.textContent || '').trim();
                        return ['确定','确认','确认登录','授权登录','登录','同意并登录'].includes(txt);
                    });
                    if (btn) {
                        btn.click();
                        return (btn.value || btn.textContent).trim();
                    }
                    return null;
                }""")
                if result_js:
                    clicked = True
                    logger.debug(f"[scan_qr] fallback clicked: {result_js}")

            try:
                page.wait_for_function("""() => {
                    return window.location.href.includes('authwidget') || document.title.includes('验证') || document.title.includes('成功');
                }""", timeout=1500)
            except Exception:
                pass
                
            final_url   = page.url
            if "authwidget" in page.url or page.title() == "身份验证":
                final_title = "百度安全中心-身份验证(异地风控拦截)"
                clicked = False
            else:
                final_title = page.title()
                
            logger.debug(f"[scan_qr] done url={final_url} title={final_title}")
            browser.close()
            return {"clicked": clicked, "final_url": final_url, "title": final_title, "api": api_responses}

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = await _asyncio.get_event_loop().run_in_executor(pool, _do_confirm)

        logger.info(f"[scan_qr] result={result}")
        if result.get("clicked"):
            # 记录授权成功次数
            key.use_count = (key.use_count or 0) + 1
            if key.max_uses > 0 and key.use_count >= key.max_uses:
                key.status = 2 # 次数用尽，作废
            db.commit()
            return {"status": "success", "msg": "已点击确认登录，用户浏览器应已完成登录", "use_count": key.use_count}
        elif "身份验证" in result.get("title", "") or "风控" in result.get("title", ""):
            return {"status": "failed",
                    "msg": "当前网盘账号被百度判定为异地登录风控拦截，需要号主手机接收验证码验证。请管理员先前往网页端网盘解冻或挂代理消除异地风控。"}
        else:
            return {"status": "failed",
                    "msg": f"未找到确认按钮（页面：{result.get('title', '')}），二维码可能已过期或网页发生未知重定向"}
    except Exception as e:
        logger.error(f"[scan_qr] error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/cdkey/redeem")
def redeem_key(code: str, db: Session = Depends(get_db)):
    """用户凭卡密换取对应账号的 Cookie。首次打开开始倒计时，超时/超次则过期。"""
    import time as _time
    key = db.query(models.CdKey).filter_by(key_code=code).first()
    if not key:
        raise HTTPException(status_code=404, detail="卡密不存在")
    if getattr(key, "status", None) == 2:
        raise HTTPException(status_code=410, detail="卡密已作废")
    if not key.account or key.account.status != 1:
        raise HTTPException(status_code=503, detail="关联账号不可用")

    now = int(_time.time())

    # 首次打开：记录过期时间
    if key.expires_at is None:
        key.expires_at = now + key.duration * 86400
        key.status = 1

    # 检查是否已超过作废宽限期
    if mark_cdkey_void_if_expired(key, now_ts=now):
        db.commit()
        raise HTTPException(status_code=410, detail="卡密已过期")

    # 检查授权次数
    if key.max_uses > 0 and (key.use_count or 0) >= key.max_uses:
        key.status = 2
        db.commit()
        raise HTTPException(status_code=410, detail=f"已超过最大授权次数（{key.max_uses}次）")

    db.commit()
    return {
        "status":     "success",
        "username":   key.account.username,
        "cookie":     key.account.cookie,
        "avatar_url": key.account.avatar_url or "",
        "vip_level":  key.account.vip_level,
        "duration":   key.duration,
        "expires_at": get_cdkey_void_deadline(key.expires_at),
        "use_count":  key.use_count,
        "max_uses":   key.max_uses,
    }


# ══════════════════════════════════════════════════════════════
# 账号操作：通过 CK 直接添加、删除 & 更新 Cookie
# ══════════════════════════════════════════════════════════════

class AddAccountRequest(BaseModel):
    cookie: str

@app.post("/api/account/add_by_cookie")
async def add_account_by_cookie(
    body: AddAccountRequest,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """直接粘贴 Cookie 添加账号，自动从百度接口拉取用户信息。"""
    import httpx as _httpx
    cookie_str = body.cookie.strip()
    bduss = next(
        (p.split("=", 1)[1].strip() for p in cookie_str.split(";")
         if p.strip().upper().startswith("BDUSS=")),
        None
    )
    if not bduss:
        raise HTTPException(status_code=400, detail="Cookie 中未找到 BDUSS，请确认复制完整")

    uinfo = {"username": "百度用户", "vip_level": "未知", "avatar_url": ""}
    try:
        async with _httpx.AsyncClient(
            headers={"Cookie": f"BDUSS={bduss}",
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True, timeout=10.0
        ) as c:
            r = await c.get("https://pan.baidu.com/rest/2.0/xpan/nas",
                            params={"method": "uinfo", "access_token": ""})
            d = r.json() if r.text.strip() else {}
            if d.get("errno") == 0:
                uinfo = {
                    "username":   d.get("baidu_name") or d.get("netdisk_name") or "百度用户",
                    "vip_level":  "SVIP" if d.get("is_svip") else "VIP" if d.get("is_vip") else "普通用户",
                    "avatar_url": d.get("avatar_url", ""),
                }
    except Exception as e:
        logger.warning(f"add_by_cookie uinfo error: {e}")

    inferred_region = ""
    try:
        inferred_region = normalize_region(BaiduDeviceService.infer_common_region(cookie_str))
    except Exception as e:
        logger.warning(f"add_by_cookie infer region error: {e}")

    acc = db.query(models.DiskAccount).filter_by(
        tenant_id=tenant_id, username=uinfo["username"]).first()
    if acc:
        acc.cookie = cookie_str; acc.status = 1
        acc.vip_level = uinfo["vip_level"]; acc.avatar_url = uinfo["avatar_url"]
        if inferred_region:
            acc.region = inferred_region
        msg = f"账号「{uinfo['username']}」Cookie 已更新"
    else:
        db.add(models.DiskAccount(
            tenant_id=tenant_id, username=uinfo["username"],
            cookie=cookie_str, status=1, weight=1,
            vip_level=uinfo["vip_level"], avatar_url=uinfo["avatar_url"],
            region=inferred_region))
        msg = f"账号「{uinfo['username']}」添加成功"
    db.commit()
    return {"status": "success", "msg": msg, "username": uinfo["username"],
            "vip_level": uinfo["vip_level"], "avatar_url": uinfo["avatar_url"], "region": inferred_region}

class UpdateAccountRequest(BaseModel):
    cookie: str | None = None
    proxy_url: str | None = None
    region: str | None = None

@app.delete("/api/account/{account_id}")
def delete_account(
    account_id: int,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """删除指定账号。"""
    acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(acc)
    db.commit()
    return {"status": "success", "msg": f"账号 {acc.username} 已删除"}


@app.put("/api/account/{account_id}/update")
def update_account(
    account_id: int,
    body: UpdateAccountRequest,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """更新指定账号的信息（Cookie 和/或 代理 IP）。"""
    acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    if body.cookie is not None:
        acc.cookie = body.cookie
        acc.status = 1
    
    if body.proxy_url is not None:
        acc.proxy_url = body.proxy_url
    if body.region is not None:
        acc.region = normalize_region(body.region)

    db.commit()
    return {"status": "success", "msg": f"账号 {acc.username} 已更新"}



# 保留原有的更新 cookie 接口，防止前端某些地方还没改过来报错
@app.put("/api/account/{account_id}/cookie")
def update_cookie(
    account_id: int,
    body: UpdateAccountRequest,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """更新指定账号的 Cookie。"""
    acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
    acc.cookie = body.cookie
    acc.status = 1
    db.commit()
    return {"status": "success", "msg": f"账号 {acc.username} Cookie 已更新"}
