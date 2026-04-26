import time
from fastapi import APIRouter, Depends, HTTPException, Header
from .database import get_db
from sqlalchemy.orm import Session
from . import models
from .service.baidu_device_service import BaiduDeviceService

def get_tenant(x_tenant_id: str = Header(None)) -> str:
    return x_tenant_id or "tenant_001"

router = APIRouter()

@router.post("/api/account/{account_id}/validate")
def validate_account_cookie(
    account_id: int,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not acc.cookie:
        raise HTTPException(status_code=400, detail="该账号没有可验证的 Cookie")

    res = BaiduDeviceService.validate_cookie(acc.cookie, acc.proxy_url)
    status = res.get("status")
    if status == "success":
        refreshed_cookie = str(res.get("cookie") or "").strip()
        if refreshed_cookie:
            acc.cookie = refreshed_cookie
        if res.get("username"):
            acc.username = res["username"]
        if res.get("vip_level"):
            acc.vip_level = res["vip_level"]
        if res.get("avatar_url") is not None:
            acc.avatar_url = res.get("avatar_url") or ""

        # 验证成功时尝试回填常用 IP 地区（只在尚未设置时拉取）
        if not str(acc.region or "").strip():
            try:
                inferred_region = str(BaiduDeviceService.infer_common_region(acc.cookie) or "").strip()
                if inferred_region:
                    acc.region = inferred_region
            except Exception:
                pass

        acc.status = 1
        db.commit()
        return {"status": "success", "valid": True, "msg": res.get("msg") or "Cookie 有效"}


    if status == "invalid":
        acc.status = 0
        db.commit()
        return {"status": "invalid", "valid": False, "msg": res.get("msg") or "Cookie 已失效"}

    return {"status": "error", "valid": False, "msg": res.get("msg") or "验证 Cookie 时发生异常"}


@router.get("/api/account/{account_id}/devices")
def get_devices(
    account_id: int,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db)
):

    acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not acc.cookie:
        raise HTTPException(status_code=400, detail="该账号没有有效的 Cookie")
        
    res = BaiduDeviceService.get_devices(acc.cookie)
    if res["status"] != "success":
        raise HTTPException(status_code=400, detail=res.get("msg", "获取设备列表失败"))
        
    return res["data"]

@router.post("/api/account/{account_id}/devices/{device_id}/lock")
def lock_device(
    account_id: int,
    device_id: str,
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    acc = db.query(models.DiskAccount).filter_by(id=account_id, tenant_id=tenant_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
        
    res = BaiduDeviceService.lock_device(acc.cookie, device_id)
    if res["status"] != "success":
        error_msg = res.get("msg", "锁定设备失败")
        # 添加失败记录
        log = models.DeviceKickLog(
            tenant_id=acc.tenant_id,
            key_code="",
            account_name=acc.username,
            account_group="vip",
            status="失败",
            action="手动踢出设备",
            ip_address="unknown",
            device_name=device_id,
            location="未知位置",
            qr_location="",
            created_at=int(time.time()),
            error_msg=error_msg
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=400, detail=error_msg)
        
    # 添加手动踢出记录
    log = models.DeviceKickLog(
        tenant_id=acc.tenant_id,
        key_code="",
        account_name=acc.username,
        account_group="vip",
        status="成功",
        action="手动踢出设备",
        ip_address="unknown",
        device_name=device_id,
        location="未知位置",
        qr_location="",
        created_at=int(time.time()),
        error_msg=""
    )
    db.add(log)
    db.commit()
    
    return {"status": "success", "msg": "设备已成功踢出"}

@router.get("/api/device_history")
def get_device_history(
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    import concurrent.futures
    import uuid
    
    accounts = db.query(models.DiskAccount).filter_by(tenant_id=tenant_id, status=1).all()
    result_list = []
    max_workers = min(4, max(1, len(accounts)))

    
    def fetch_history(acc):
        if not acc.cookie: return []
        res = BaiduDeviceService.get_device_history(acc.cookie)
        if res["status"] != "success": return []
        logs = []
        for d in res["data"]:
            logs.append({
                "id": str(uuid.uuid4()),
                "account_id": acc.id,
                "account_name": acc.username,
                "device_name": d.get("device_name", "未知设备"),
                "location": d.get("os", "未知系统"),
                "ip_address": d.get("ip", "未知IP"),
                "created_at": d.get("last_used", int(time.time())),
                "icon": d.get("icon", ""),
            })
        return logs

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_history, acc) for acc in accounts]
        for future in concurrent.futures.as_completed(futures):

            try:
                result_list.extend(future.result())
            except Exception:
                pass
                
    result_list.sort(key=lambda x: x["created_at"], reverse=True)
    return result_list

@router.get("/api/device_logs")
def get_device_logs(
    tenant_id: str = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    import concurrent.futures
    import uuid
    
    # 1. 移除从数据库读取踢出记录的逻辑，只展示真实的在线设备
    result_list = []
    
    # 2. 查询当前系统中所有的在线账号
    accounts = db.query(models.DiskAccount).filter_by(tenant_id=tenant_id, status=1).all()
    max_workers = min(4, max(1, len(accounts)))

    
    def fetch_account_devices(acc):
        if not acc.cookie:
            return [{
                "id": str(uuid.uuid4()),
                "key_code": "",
                "account_id": acc.id,
                "device_id": "",
                "account_name": acc.username,
                "account_group": acc.vip_level,
                "status": "失败",
                "action": "查询设备",
                "ip_address": "-",
                "device_name": "-",
                "location": "-",
                "qr_location": "",
                "created_at": int(time.time()),
                "error_msg": "未绑定Cookie"
            }]
            
        res = BaiduDeviceService.get_devices(acc.cookie)
        if res["status"] != "success":
            return [{
                "id": str(uuid.uuid4()),
                "key_code": "",
                "account_id": acc.id,
                "device_id": "",
                "account_name": acc.username,
                "account_group": acc.vip_level,
                "status": "失败",
                "action": "查询设备",
                "ip_address": "-",
                "device_name": "-",
                "location": "-",
                "qr_location": "",
                "created_at": int(time.time()),
                "error_msg": res.get("msg", "查询失败")
            }]
        
        devices = res["data"]
        logs = []
        for d in devices:
            logs.append({
                "id": str(uuid.uuid4()),  # 前端渲染需要唯一 key
                "key_code": "",
                "account_id": acc.id,
                "device_id": d.get("device_id", ""),
                "account_name": acc.username,
                "account_group": acc.vip_level,
                "status": "在线",
                "action": "当前使用设备",
                "ip_address": d.get("ip", "未知IP"),
                "device_name": d.get("device_name", "未知设备"),
                "location": d.get("os", "未知系统"),
                "icon": d.get("icon", ""),
                "button": d.get("button", ""),
                "qr_location": "",
                "created_at": d.get("last_used", int(time.time())),
                "unused_days": d.get("unused_days", 0),
                "is_current": d.get("is_current", False),
                "error_msg": f"{d.get('unused_days', 0)}天未用" if d.get('unused_days', 0) > 0 else "最近使用"
            })
        return logs

    # 并发请求官方接口获取所有账号的“使用中”设备
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [executor.submit(fetch_account_devices, acc) for acc in accounts]
        for future in concurrent.futures.as_completed(futures):
            try:
                active_devices = future.result()
                result_list.extend(active_devices)
            except Exception:
                pass
                
    # 按照时间倒序排序 (让最新使用的设备和最新的踢出记录排在前面)
    result_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return result_list

