import time
from typing import Any, Callable, Dict, Optional

import cookie_manager
from fastapi import HTTPException

from api_auth import ensure_cookie_access, log_with_user
from db_manager import db_manager


def list_cookies(current_user: Dict[str, Any]) -> list[str]:
    user_cookies = db_manager.get_all_cookies(current_user["user_id"])
    return list(user_cookies.keys())


def get_cookies_details(
    current_user: Dict[str, Any],
    nickname_fetch_limiter: Dict[str, float],
    looks_like_account_id: Callable[[str], bool],
    fetch_profile: Callable[[str], tuple[str, str]],
) -> list[Dict[str, Any]]:
    user_id = current_user["user_id"]
    cookie_details_map = db_manager.get_cookie_details_by_user(user_id)
    manager = cookie_manager.manager

    result = []
    for cookie_id, cookie_details in cookie_details_map.items():
        cookie_value = cookie_details.get("value", "")
        cookie_enabled = (
            manager.get_cookie_status(cookie_id)
            if manager is not None
            else db_manager.get_cookie_status(cookie_id)
        )
        remark = cookie_details.get("remark", "") if cookie_details else ""
        xianyu_nickname = cookie_details.get("xianyu_nickname", "") if cookie_details else ""
        xianyu_avatar_url = cookie_details.get("xianyu_avatar_url", "") if cookie_details else ""
        nickname_needs_refresh = (not xianyu_nickname) or looks_like_account_id(xianyu_nickname)
        avatar_needs_refresh = not xianyu_avatar_url
        if nickname_needs_refresh or avatar_needs_refresh:
            now_ts = time.time()
            last_ts = nickname_fetch_limiter.get(cookie_id, 0.0)
            if now_ts - last_ts > 10:
                nickname_fetch_limiter[cookie_id] = now_ts
                fetched_nickname, fetched_avatar = fetch_profile(cookie_value)
                if fetched_nickname:
                    xianyu_nickname = fetched_nickname
                if fetched_avatar:
                    xianyu_avatar_url = fetched_avatar
                if fetched_nickname or fetched_avatar:
                    try:
                        db_manager.update_cookie_account_info(
                            cookie_id,
                            xianyu_nickname=fetched_nickname or None,
                            xianyu_avatar_url=fetched_avatar or None,
                        )
                    except Exception:
                        pass

        result.append(
            {
                "id": cookie_id,
                "value": cookie_value,
                "enabled": cookie_enabled,
                "auto_confirm": cookie_details.get("auto_confirm", True),
                "auto_reply_once_per_customer": cookie_details.get("auto_reply_once_per_customer", False)
                if cookie_details
                else False,
                "remark": remark,
                "pause_duration": cookie_details.get("pause_duration", 10) if cookie_details else 10,
                "username": cookie_details.get("username", "") if cookie_details else "",
                "login_password": cookie_details.get("password", "") if cookie_details else "",
                "show_browser": cookie_details.get("show_browser", False) if cookie_details else False,
                "xianyu_nickname": xianyu_nickname,
                "xianyu_avatar_url": xianyu_avatar_url,
            }
        )
    return result


def add_cookie(item: Any, current_user: Dict[str, Any]) -> Dict[str, str]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        user_id = current_user["user_id"]
        log_with_user(
            "info",
            f"尝试添加Cookie: {item.id}, 当前用户ID: {user_id}, 用户名: {current_user.get('username', 'unknown')}",
            current_user,
        )

        existing_cookies = db_manager.get_all_cookies()
        if item.id in existing_cookies and item.id not in db_manager.get_all_cookies(user_id):
            log_with_user("warning", f"Cookie ID冲突: {item.id} 已被其他用户使用", current_user)
            raise HTTPException(status_code=400, detail="该Cookie ID已被其他用户使用")

        db_manager.save_cookie(item.id, item.value, user_id)
        cookie_manager.manager.add_cookie(item.id, item.value, user_id=user_id)
        log_with_user("info", f"Cookie添加成功: {item.id}", current_user)
        return {"msg": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        log_with_user("error", f"添加Cookie失败: {item.id} - {exc}", current_user)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def update_cookie_login_info(cid: str, update_data: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        ensure_cookie_access(cid, current_user, "操作")
        success = db_manager.update_cookie_account_info(
            cid,
            username=update_data.username,
            password=update_data.login_password,
            show_browser=update_data.show_browser,
        )
        if success:
            return {"success": True, "message": "登录信息已更新"}
        raise HTTPException(status_code=500, detail="更新登录信息失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def update_cookie(cid: str, item: Any, current_user: Dict[str, Any]) -> Dict[str, str]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        old_cookie_details = db_manager.get_cookie_details(cid)
        old_cookie_value = old_cookie_details.get("value") if old_cookie_details else None

        success = db_manager.update_cookie_account_info(cid, cookie_value=item.value)
        if not success:
            raise HTTPException(status_code=400, detail="更新Cookie失败")

        if item.value != old_cookie_value:
            cookie_manager.manager.update_cookie(cid, item.value, save_to_db=False)
        return {"msg": "updated"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def update_cookie_account_info(cid: str, info: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        old_cookie_details = db_manager.get_cookie_details(cid)
        old_cookie_value = old_cookie_details.get("value") if old_cookie_details else None
        success = db_manager.update_cookie_account_info(
            cid,
            cookie_value=info.value,
            username=info.username,
            password=info.password,
            show_browser=info.show_browser,
        )
        if not success:
            raise HTTPException(status_code=400, detail="更新账号信息失败")
        if info.value is not None and info.value != old_cookie_value:
            cookie_manager.manager.update_cookie(cid, info.value, save_to_db=False)
        return {"msg": "updated", "success": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def get_cookie_account_details(cid: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        ensure_cookie_access(cid, current_user, "操作")
        details = db_manager.get_cookie_details(cid)
        if not details:
            raise HTTPException(status_code=404, detail="账号不存在")
        return details
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def get_cookie_headinfo_debug(
    cid: str,
    current_user: Dict[str, Any],
    fetch_profile_debug: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        ensure_cookie_access(cid, current_user, "操作")
        cookie_value = db_manager.get_all_cookies(current_user["user_id"]).get(cid, "")
        result = fetch_profile_debug(cookie_value)
        result["cookie_id"] = cid
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def refresh_cookie_profile(
    cid: str,
    current_user: Dict[str, Any],
    fetch_profile: Callable[[str], tuple[str, str]],
) -> Dict[str, Any]:
    try:
        ensure_cookie_access(cid, current_user, "操作")
        cookie_value = db_manager.get_all_cookies(current_user["user_id"]).get(cid, "")
        nickname, avatar_url = fetch_profile(cookie_value)
        if not nickname and not avatar_url:
            return {"success": False, "message": "未获取到闲鱼昵称/头像", "cookie_id": cid}

        try:
            db_manager.update_cookie_account_info(
                cid,
                xianyu_nickname=nickname or None,
                xianyu_avatar_url=avatar_url or None,
            )
        except Exception:
            pass

        return {
            "success": True,
            "cookie_id": cid,
            "nickname": nickname,
            "avatar_url": avatar_url,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def update_cookie_status(cid: str, status_data: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        cookie_manager.manager.update_cookie_status(cid, status_data.enabled)
        return {"msg": "status updated", "enabled": status_data.enabled}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def remove_cookie(cid: str, current_user: Dict[str, Any]) -> Dict[str, str]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        cookie_manager.manager.remove_cookie(cid)
        return {"msg": "removed"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def update_auto_confirm(cid: str, update_data: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        success = db_manager.update_auto_confirm(cid, update_data.auto_confirm)
        if not success:
            raise HTTPException(status_code=500, detail="更新自动确认发货设置失败")
        if hasattr(cookie_manager.manager, "update_auto_confirm_setting"):
            cookie_manager.manager.update_auto_confirm_setting(cid, update_data.auto_confirm)
        return {
            "msg": "success",
            "auto_confirm": update_data.auto_confirm,
            "message": f"自动确认发货已{'开启' if update_data.auto_confirm else '关闭'}",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_auto_confirm(cid: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        auto_confirm = db_manager.get_auto_confirm(cid)
        return {
            "auto_confirm": auto_confirm,
            "message": f"自动确认发货当前{'开启' if auto_confirm else '关闭'}",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def update_cookie_remark(cid: str, update_data: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        success = db_manager.update_cookie_remark(cid, update_data.remark)
        if success:
            log_with_user("info", f"更新账号备注: {cid} -> {update_data.remark}", current_user)
            return {"message": "备注更新成功", "remark": update_data.remark}
        raise HTTPException(status_code=500, detail="备注更新失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_cookie_remark(cid: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        cookie_details = db_manager.get_cookie_details(cid)
        if cookie_details:
            return {"remark": cookie_details.get("remark", ""), "message": "获取备注成功"}
        raise HTTPException(status_code=404, detail="账号不存在")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def update_cookie_pause_duration(cid: str, update_data: Any, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        if not (0 <= update_data.pause_duration <= 60):
            raise HTTPException(status_code=400, detail="暂停时间必须在0-60分钟之间（0表示不暂停）")
        success = db_manager.update_cookie_pause_duration(cid, update_data.pause_duration)
        if success:
            log_with_user("info", f"更新账号自动回复暂停时间: {cid} -> {update_data.pause_duration}分钟", current_user)
            return {"message": "暂停时间更新成功", "pause_duration": update_data.pause_duration}
        raise HTTPException(status_code=500, detail="暂停时间更新失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_cookie_pause_duration(cid: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        pause_duration = db_manager.get_cookie_pause_duration(cid)
        return {"pause_duration": pause_duration, "message": "获取暂停时间成功"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def update_cookie_auto_reply_once_per_customer(
    cid: str, update_data: Any, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        success = db_manager.update_cookie_auto_reply_once_per_customer(cid, update_data.enabled)
        if success:
            log_with_user(
                "info",
                f"更新账号每客户只自动回复一次: {cid} -> {'开启' if update_data.enabled else '关闭'}",
                current_user,
            )
            return {"message": "每客户只自动回复一次设置更新成功", "enabled": update_data.enabled}
        raise HTTPException(status_code=500, detail="每客户只自动回复一次设置更新失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def get_cookie_auto_reply_once_per_customer(cid: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    if cookie_manager.manager is None:
        raise HTTPException(status_code=500, detail="CookieManager 未就绪")
    try:
        ensure_cookie_access(cid, current_user, "操作")
        enabled = db_manager.get_cookie_auto_reply_once_per_customer(cid)
        return {"enabled": enabled, "message": f"每客户只自动回复一次当前{'开启' if enabled else '关闭'}"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
