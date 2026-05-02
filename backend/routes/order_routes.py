from typing import Any, Dict, Optional

from fastapi import HTTPException

from api_auth import log_with_user
from db_manager import db_manager


def get_user_orders(
    cookie_id: Optional[str],
    status: Optional[str],
    keyword: Optional[str],
    page: int,
    page_size: int,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        user_id = current_user["user_id"]
        log_with_user("info", "查询用户订单信息", current_user)
        keyword = (keyword or "").strip().lower()
        normalized_status = (status or "").strip()

        user_cookies = db_manager.get_all_cookies(user_id)
        target_cookie_ids = list(user_cookies.keys())
        if cookie_id:
            target_cookie_ids = [cookie_id] if cookie_id in user_cookies else []

        paged_orders, total = db_manager.get_orders_page_by_cookie_ids(
            target_cookie_ids,
            status=normalized_status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0

        log_with_user("info", f"用户订单查询成功，共 {total} 条记录", current_user)
        return {
            "success": True,
            "data": paged_orders,
            "total": total,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size,
        }
    except Exception as exc:
        log_with_user("error", f"查询用户订单失败: {exc}", current_user)
        raise HTTPException(status_code=500, detail=f"查询订单失败: {exc}") from exc


async def fetch_user_orders(request: dict, current_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        cookie_id = (request.get("cookie_id") or "").strip()
        if not cookie_id:
            return {"success": False, "message": "缺少 cookie_id 参数"}

        user_id = current_user["user_id"]
        user_cookies = db_manager.get_all_cookies(user_id)
        if cookie_id not in user_cookies:
            raise HTTPException(status_code=403, detail="无权限访问该账号")

        cookie_details = db_manager.get_cookie_details(cookie_id)
        if not cookie_details:
            return {"success": False, "message": "账号不存在"}

        cookies_str = cookie_details.get("value") or ""
        if not cookies_str:
            return {"success": False, "message": "账号 Cookie 为空"}

        headless = not bool(cookie_details.get("show_browser"))

        try:
            from XianyuAutoAsync import XianyuLive

            live_instance = XianyuLive.get_instance(cookie_id)
            if live_instance and getattr(live_instance, "cookies_str", None):
                cookies_str = live_instance.cookies_str
        except Exception:
            pass

        from utils.order_list_fetcher import fetch_order_list_simple

        log_with_user("info", f"开始主动抓取真实订单: {cookie_id}", current_user)
        fetch_result = await fetch_order_list_simple(
            cookie_string=cookies_str,
            cookie_id=cookie_id,
            headless=headless,
        )
        if not fetch_result.get("success"):
            return {"success": False, "message": fetch_result.get("message") or "抓取订单失败"}

        fetched_orders = fetch_result.get("orders") or []
        saved_count = 0
        for order in fetched_orders:
            success = db_manager.insert_or_update_order(
                order_id=order.get("order_id"),
                item_id=order.get("item_id") or None,
                buyer_id=order.get("buyer_id") or None,
                quantity=order.get("quantity"),
                amount=order.get("amount") or None,
                order_status=order.get("status") or "unknown",
                cookie_id=cookie_id,
                is_bargain=order.get("is_bargain"),
            )
            if success:
                saved_count += 1

        log_with_user(
            "info",
            f"真实订单抓取完成: {cookie_id}, 抓取 {len(fetched_orders)} 条, 保存 {saved_count} 条",
            current_user,
        )
        return {
            "success": True,
            "message": fetch_result.get("message") or f"成功抓取 {len(fetched_orders)} 条订单",
            "fetched_count": len(fetched_orders),
            "saved_count": saved_count,
        }
    except HTTPException:
        raise
    except Exception as exc:
        log_with_user("error", f"主动抓取订单失败: {exc}", current_user)
        raise HTTPException(status_code=500, detail=f"主动抓取订单失败: {exc}") from exc


def get_order_detail(order_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        user_id = current_user["user_id"]
        log_with_user("info", f"查询订单详情: {order_id}", current_user)

        user_cookies = db_manager.get_all_cookies(user_id)
        order = db_manager.get_order_by_id(order_id)
        if order and order.get("cookie_id") in user_cookies:
            log_with_user("info", f"订单详情查询成功: {order_id}", current_user)
            return {"success": True, "data": order}

        log_with_user("warning", f"订单不存在或无权访问: {order_id}", current_user)
        raise HTTPException(status_code=404, detail="订单不存在或无权访问")
    except HTTPException:
        raise
    except Exception as exc:
        log_with_user("error", f"查询订单详情失败: {exc}", current_user)
        raise HTTPException(status_code=500, detail=f"查询订单详情失败: {exc}") from exc


def delete_order(order_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        user_id = current_user["user_id"]
        log_with_user("info", f"删除订单: {order_id}", current_user)

        user_cookies = db_manager.get_all_cookies(user_id)
        order = db_manager.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if order.get("cookie_id") not in user_cookies:
            raise HTTPException(status_code=403, detail="无权删除此订单")
        if not db_manager.delete_order(order_id):
            raise HTTPException(status_code=500, detail="删除订单失败")

        log_with_user("info", f"订单删除成功: {order_id}", current_user)
        return {"success": True, "message": "订单删除成功"}
    except HTTPException:
        raise
    except Exception as exc:
        log_with_user("error", f"删除订单失败: {exc}", current_user)
        raise HTTPException(status_code=500, detail=f"删除订单失败: {exc}") from exc
