import asyncio
import time
from .database import SessionLocal
from . import models
from .service.baidu_device_service import BaiduDeviceService
from loguru import logger

async def auto_kick_task():
    """定时自动踢设备的后台任务。每隔15分钟运行一次。"""
    while True:
        try:
            logger.info("开始执行定时自动踢设备任务...")
            db = SessionLocal()
            try:
                # 找出所有状态正常的账号
                accounts = db.query(models.DiskAccount).filter_by(status=1).all()
                now = int(time.time())
                
                for acc in accounts:
                    if not acc.cookie:
                        continue
                        
                    res = await asyncio.to_thread(BaiduDeviceService.get_devices, acc.cookie)
                    if res["status"] != "success":
                        continue

                        
                    devices = res["data"]
                    # 踢出策略：踢出非当前设备，且未使用超过一定天数，或者非在线的
                    # 或者如果设备过多（例如超过10个），踢出最旧的
                    
                    locked_count = 0
                    for dev in devices:
                        if not dev.get("is_current") and dev.get("status") == "在线":
                            # 假设超过 5 天未使用，或者总设备数大于5就踢旧的
                            if dev.get("unused_days", 0) >= 3 or len(devices) > 5:
                                kick_res = await asyncio.to_thread(BaiduDeviceService.lock_device, acc.cookie, dev.get("device_id"))
                                
                                # 记录日志

                                log = models.DeviceKickLog(
                                    tenant_id=acc.tenant_id,
                                    key_code="",
                                    account_name=acc.username,
                                    account_group="vip",
                                    status="成功" if kick_res["status"] == "success" else "失败",
                                    action="自动踢出设备",
                                    ip_address=dev.get("ip", "unknown"),
                                    device_name=dev.get("device_name", "未知设备"),
                                    location="未知位置",
                                    qr_location="",
                                    created_at=now,
                                    error_msg=kick_res.get("msg", "")
                                )
                                db.add(log)
                                locked_count += 1
                                await asyncio.sleep(1) # 防风控
                                
                    if locked_count > 0:
                        logger.info(f"账号 {acc.username} 自动踢出了 {locked_count} 个设备")
                        
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"定时踢设备任务异常: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"auto_kick_task 外层异常: {e}")
            
        await asyncio.sleep(900) # 15分钟执行一次
