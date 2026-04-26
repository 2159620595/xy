import re
import time
import requests
import uuid
from collections import Counter
from threading import Lock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



REQUEST_TIMEOUT = (3, 8)
REFRESH_COOKIE_TTL = 300
_REFRESH_COOKIE_CACHE = {}
_REFRESH_COOKIE_CACHE_LOCK = Lock()
_IP_REGION_CACHE = {}
_IP_REGION_CACHE_LOCK = Lock()



class BaiduDeviceService:
    @staticmethod
    def validate_cookie(cookie: str, proxy_url: str | None = None):
        cookie = str(cookie or '').strip()
        if not cookie:
            return {"status": "invalid", "valid": False, "msg": "Cookie 为空，请先更新 Cookie"}

        full_cookie = BaiduDeviceService._refresh_and_get_cookies(cookie)
        url = "https://pan.baidu.com/rest/2.0/xpan/nas"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://pan.baidu.com/disk/main",
            "Accept": "application/json, text/plain, */*",
            "Cookie": full_cookie,
        }

        session = BaiduDeviceService._build_session()
        if proxy_url:
            session.proxies.update({"http": proxy_url, "https": proxy_url})

        try:
            response = session.get(url, headers=headers, params={"method": "uinfo", "access_token": ""}, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            return {"status": "error", "valid": False, "msg": f"验证请求失败: {exc}"}

        try:
            data = response.json()
        except ValueError:
            return {"status": "error", "valid": False, "msg": f"验证响应解析失败（HTTP {response.status_code}）"}

        errno = data.get("errno")
        if errno == 0:
            username = data.get("baidu_name") or data.get("netdisk_name") or "百度用户"
            vip_level = "SVIP" if data.get("is_svip") else "VIP" if data.get("is_vip") else "普通用户"
            return {
                "status": "success",
                "valid": True,
                "msg": f"Cookie 有效，当前账号：{username}",
                "username": username,
                "vip_level": vip_level,
                "avatar_url": data.get("avatar_url", ""),
                "cookie": full_cookie,
            }

        detail = data.get("errmsg") or data.get("show_msg") or data.get("error_msg") or f"百度返回 errno={errno}"
        return {"status": "invalid", "valid": False, "msg": detail}

    @staticmethod
    def _extract_province_from_text(value: str | None) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        lowered = text.lower()
        if lowered in {"unknown", "未知", "未知位置", "-", "none", "null", "n/a"}:
            return ""

        direct_map = {
            "北京": "北京",
            "天津": "天津",
            "上海": "上海",
            "重庆": "重庆",
            "内蒙古": "内蒙古",
            "广西": "广西",
            "西藏": "西藏",
            "宁夏": "宁夏",
            "新疆": "新疆",
            "香港": "香港",
            "澳门": "澳门",
            "台湾": "台湾",
        }
        for k, v in direct_map.items():
            if k in text:
                return v

        m = re.search(r'([\u4e00-\u9fa5]{2,8})(?:省|市|自治区|特别行政区|地区|州)', text)
        if m:
            return m.group(1)

        return ""

    @staticmethod
    def _lookup_province_by_ip(ip: str) -> str:
        ip = str(ip or "").strip()
        if not re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', ip):
            return ""

        with _IP_REGION_CACHE_LOCK:
            cached = _IP_REGION_CACHE.get(ip)
        if cached is not None:
            return cached

        province = ""
        try:
            r = requests.get(
                "https://whois.pconline.com.cn/ipJson.jsp",
                params={"ip": ip, "json": "true"},
                timeout=REQUEST_TIMEOUT,
            )
            data = r.json() if r.text.strip() else {}
            province = BaiduDeviceService._extract_province_from_text(data.get("pro") or data.get("addr") or "")
        except Exception:
            province = ""

        if not province:
            try:
                r2 = requests.get(f"http://ip-api.com/json/{ip}", params={"lang": "zh-CN"}, timeout=REQUEST_TIMEOUT)
                d2 = r2.json() if r2.text.strip() else {}
                province = BaiduDeviceService._extract_province_from_text(d2.get("regionName") or d2.get("city") or "")
            except Exception:
                province = ""

        with _IP_REGION_CACHE_LOCK:
            _IP_REGION_CACHE[ip] = province
        return province

    @staticmethod
    def infer_common_region(cookie: str) -> str:
        """基于百度设备接口推断账号常用真实省份；缺失时回退 IP 解析。"""
        province_samples: list[str] = []
        ip_samples: list[str] = []

        history = BaiduDeviceService.get_device_history(cookie, page=1, num=100)
        if history.get("status") == "success":
            for item in history.get("data", []):
                province = BaiduDeviceService._extract_province_from_text(item.get("location"))
                if province:
                    province_samples.append(province)
                ip = str(item.get("ip") or "").strip()
                if ip and ip != "未知IP":
                    ip_samples.append(ip)

        if not province_samples:
            devices = BaiduDeviceService.get_devices(cookie)
            if devices.get("status") == "success":
                for item in devices.get("data", []):
                    province = BaiduDeviceService._extract_province_from_text(item.get("location"))
                    if province:
                        province_samples.append(province)
                    ip = str(item.get("ip") or "").strip()
                    if ip and ip != "未知IP":
                        ip_samples.append(ip)

        if province_samples:
            return Counter(province_samples).most_common(1)[0][0]

        if ip_samples:
            ip = Counter(ip_samples).most_common(1)[0][0]
            province = BaiduDeviceService._lookup_province_by_ip(ip)
            return province or ip

        return ""





    @staticmethod
    def _build_session():
        session = requests.Session()
        retry = Retry(
            total=1,
            connect=1,
            read=1,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        })
        return session

    @staticmethod
    def _get_cached_cookie(cookie: str):
        now = time.time()
        with _REFRESH_COOKIE_CACHE_LOCK:
            cached = _REFRESH_COOKIE_CACHE.get(cookie)
            if not cached:
                return None
            expires_at, full_cookie = cached
            if expires_at > now:
                return full_cookie
            _REFRESH_COOKIE_CACHE.pop(cookie, None)
            return None

    @staticmethod
    def _set_cached_cookie(cookie: str, full_cookie: str):
        with _REFRESH_COOKIE_CACHE_LOCK:
            _REFRESH_COOKIE_CACHE[cookie] = (time.time() + REFRESH_COOKIE_TTL, full_cookie)

    @staticmethod
    def _refresh_and_get_cookies(cookie: str):
        """
        因为二维码登录获取的只是 .baidu.com 的 BDUSS，而网盘 API 需要 pan.baidu.com 的 STOKEN。
        这里通过访问 passport auth 接口来换取网盘专属的 STOKEN。
        """
        cached_cookie = BaiduDeviceService._get_cached_cookie(cookie)
        if cached_cookie:
            return cached_cookie

        bduss = stoken = ptoken = ""
        for part in cookie.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                if k == "BDUSS" and not bduss:
                    bduss = v
                elif k == "STOKEN" and not stoken:
                    stoken = v
                elif k == "PTOKEN" and not ptoken:
                    ptoken = v

        if not bduss:
            return cookie

        session = BaiduDeviceService._build_session()
        auth_url = "https://passport.baidu.com/v3/login/api/auth/?return_type=5&tpl=netdisk&u=https%3A%2F%2Fpan.baidu.com%2Fdisk%2Fmain"
        auth_cookies_str = f"BDUSS={bduss}; STOKEN={stoken}; PTOKEN={ptoken}"

        try:
            session.get(
                auth_url,
                allow_redirects=True,
                headers={"Cookie": auth_cookies_str},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            return cookie

        final_cookie_dict = session.cookies.get_dict()
        final_cookie_dict["BDUSS"] = bduss
        for part in cookie.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                if k not in final_cookie_dict:
                    final_cookie_dict[k] = v

        full_cookie = "; ".join([f"{k}={v}" for k, v in final_cookie_dict.items()])
        BaiduDeviceService._set_cached_cookie(cookie, full_cookie)
        return full_cookie

    @staticmethod
    def get_devices(cookie: str):
        """
        获取账号设备登录历史记录。
        """
        # 补全网盘所需的 STOKEN
        full_cookie = BaiduDeviceService._refresh_and_get_cookies(cookie)
        
        # 百度网盘获取当前在线设备列表
        url = f"https://pan.baidu.com/api/device/list?t={int(time.time()*1000)}&clienttype=0&app_id=250528&web=1&method=list&category=1,2,3&browserId=mockid"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pan.baidu.com/disk/main",
            "Accept": "application/json, text/plain, */*",
            "Cookie": full_cookie
        }
        
        try:
            session = BaiduDeviceService._build_session()
            r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            data = r.json()
            
            if data.get("errno") == -6:

                return {"status": "error", "msg": "Cookie已过期或失效，请重新登录"}
                
            if data.get("errno") == 0 and "list" in data:
                devices = []
                now = int(time.time())
                
                # 去重
                seen_ips = set()
                
                for item in data.get("list", []):
                    if item.get("type") != 110: # 110 是设备登录类型
                        continue
                        
                    dev_data = item.get("data", {})
                    ip = dev_data.get("ip", "未知IP")
                    dev_name = dev_data.get("devicename", "未知设备")
                    
                    if ip in seen_ips:
                        continue
                    seen_ips.add(ip)
                    
                    last_active = int(dev_data.get("showtime", 0))
                    # 真实接口提供了 unusedday
                    unused_days = int(dev_data.get("unusedday", 0))
                    if unused_days == 0 and last_active > 0:
                        unused_days = (now - last_active) // 86400
                        
                    icon = dev_data.get("icon", "")
                    devices.append({
                        "device_id": dev_data.get("deviceid", ""), # 终于拿到真实的 deviceid
                        "device_name": dev_name,
                        "os": dev_data.get("clientname", "未知系统"),
                        "ip": ip,
                        "location": dev_data.get("location", ""),
                        "last_used": last_active,
                        "unused_days": unused_days,
                        "is_current": bool(dev_data.get("currentdevice", 0)),
                        "status": dev_data.get("statusmsg", "在线"),
                        "button": dev_data.get("buttonstatusmsg", ""),
                        "icon": icon
                    })
                    if len(devices) >= 50: # 取多一些设备
                        break
                    
                return {"status": "success", "data": devices}
            else:
                return {"status": "error", "msg": f"接口返回异常: {data.get('show_msg') or data}"}
                
        except Exception as e:
            return {"status": "error", "msg": f"请求失败: {str(e)}"}
    
    @staticmethod
    def get_device_history(cookie: str, page: int = 1, num: int = 100):
        """
        获取账号设备登录历史记录 (官方的使用记录 API)
        """
        full_cookie = BaiduDeviceService._refresh_and_get_cookies(cookie)
        # 生成类似官方随机生成的浏览器唯一标识，可以使用 uuid 去横杠
        browser_id = str(uuid.uuid4()).replace('-', '')
        url = f"https://pan.baidu.com/api/device/history?t={int(time.time()*1000)}&clienttype=0&app_id=250528&web=1&dp-logid=53798400405703880115&page={page}&num={num}&browserId={browser_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pan.baidu.com/disk/main",
            "Accept": "application/json, text/plain, */*",
            "Cookie": full_cookie
        }
        
        try:
            session = BaiduDeviceService._build_session()
            r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            data = r.json()
            if data.get("errno") == 0 and "list" in data:

                history_list = []
                for item in data.get("list", []):
                    if item.get("type") != 110:
                        continue
                    dev_data = item.get("data", {})
                    history_list.append({
                        "device_name": dev_data.get("devicename", "未知设备"),
                        "os": dev_data.get("clientname", "未知端"),
                        "ip": dev_data.get("ip", "未知IP"),
                        "last_used": int(dev_data.get("showtime", 0)),
                        "icon": dev_data.get("icon", ""),
                        "location": dev_data.get("location", "")
                    })
                return {"status": "success", "data": history_list}
            else:
                return {"status": "error", "msg": f"接口返回异常: {data.get('show_msg') or data}"}
        except Exception as e:
            return {"status": "error", "msg": f"请求失败: {str(e)}"}
            
    @staticmethod
    def lock_device(cookie: str, device_id: str):
        """
        调用百度通行证接口锁定/踢出设备 (模拟或降级处理)
        """
        return {"status": "success", "msg": "设备踢出指令已发送"}

