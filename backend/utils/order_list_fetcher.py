"""
闲鱼订单列表抓取工具
基于 Playwright 访问卖家订单页，并尝试从真实接口响应中提取订单列表。
"""

import asyncio
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Response, async_playwright


if sys.platform.startswith("linux") or os.getenv("DOCKER_ENV"):
    try:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    except Exception as exc:
        logger.warning(f"设置事件循环策略失败: {exc}")


class OrderListFetcher:
    """抓取闲鱼卖家订单列表的轻量工具。"""

    CANDIDATE_URLS = [
        "https://www.goofish.com/",
        "https://www.goofish.com/order/all?role=seller",
        "https://www.goofish.com/order?role=seller",
        "https://www.goofish.com/order-list?role=seller",
        "https://www.goofish.com/trade/order_list?role=seller",
    ]

    API_HINTS = ("h5api.m.goofish.com", "mtop", "order", "trade")

    def __init__(self, cookie_string: str, cookie_id: str, headless: bool = True):
        self.cookie_string = cookie_string
        self.cookie_id = cookie_id
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.orders_by_id: Dict[str, Dict[str, Any]] = {}

    async def init_browser(self) -> bool:
        """初始化浏览器和页面。"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                ],
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1440, "height": 960},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
            )
            await self._set_cookies()
            self.page = await self.context.new_page()
            self.page.on("response", lambda response: asyncio.create_task(self._handle_response(response)))
            return True
        except Exception as exc:
            logger.error(f"【{self.cookie_id}】初始化订单列表抓取浏览器失败: {exc}")
            return False

    async def _set_cookies(self):
        cookies: List[Dict[str, Any]] = []
        for cookie_pair in self.cookie_string.split("; "):
            if "=" not in cookie_pair:
                continue
            name, value = cookie_pair.split("=", 1)
            cookies.append(
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".goofish.com",
                    "path": "/",
                }
            )
        if cookies and self.context:
            await self.context.add_cookies(cookies)

    async def _handle_response(self, response: Response):
        """监听网络响应，尝试从真实接口中抽取订单数据。"""
        try:
            url = response.url.lower()
            if response.status != 200:
                return
            if not all(hint in url for hint in ("goofish", "order")) and not (
                "trade" in url and any(hint in url for hint in self.API_HINTS)
            ):
                return

            content_type = (response.headers.get("content-type") or "").lower()
            if "json" not in content_type and "javascript" not in content_type:
                return

            payload = await response.json()
            parsed_orders = self._extract_orders_from_payload(payload)
            if not parsed_orders:
                return

            for order in parsed_orders:
                self.orders_by_id[order["order_id"]] = order

            logger.info(
                f"【{self.cookie_id}】从响应提取到 {len(parsed_orders)} 条订单，累计 {len(self.orders_by_id)} 条: {response.url}"
            )
        except Exception:
            # 页面接口变化较频繁，单次解析失败不影响整体抓取流程
            return

    def _extract_orders_from_payload(self, payload: Any) -> List[Dict[str, Any]]:
        orders: List[Dict[str, Any]] = []
        seen_order_ids = set()

        def visit(value: Any):
            if isinstance(value, dict):
                parsed = self._parse_order_candidate(value)
                if parsed and parsed["order_id"] not in seen_order_ids:
                    seen_order_ids.add(parsed["order_id"])
                    orders.append(parsed)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(payload)
        return orders

    def _parse_order_candidate(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        order_id = self._normalize_id(
            self._find_first(data, ("orderId", "bizOrderId", "order_id", "id"))
        )
        if not order_id:
            return None

        item_id = self._normalize_id(self._find_first(data, ("itemId", "item_id", "itemBizId", "bizItemId")))
        buyer_id = self._normalize_id(
            self._find_first(
                data,
                ("buyerId", "buyer_id", "buyerUserId", "userId", "user_id", "buyerNick"),
            )
        )
        amount = self._extract_amount(
            self._find_first(
                data,
                ("amount", "payAmount", "actualFee", "realPayFee", "price", "totalFee", "payment"),
            )
        )
        quantity = self._extract_quantity(
            self._find_first(data, ("num", "quantity", "buyAmount", "count"))
        )
        status = self._normalize_status(
            self._find_first(
                data,
                (
                    "orderStatus",
                    "status",
                    "statusDesc",
                    "statusText",
                    "tradeStatus",
                    "bizOrderStatus",
                ),
            )
        )
        is_bargain = self._extract_bargain_flag(data)

        if not any([item_id, buyer_id, amount, status != "unknown"]):
            return None

        return {
            "order_id": order_id,
            "item_id": item_id,
            "buyer_id": buyer_id,
            "quantity": quantity,
            "amount": amount,
            "status": status,
            "is_bargain": is_bargain,
        }

    def _find_first(self, data: Any, keys: Iterable[str]) -> Any:
        key_set = {key.lower() for key in keys}

        def walk(value: Any) -> Any:
            if isinstance(value, dict):
                for current_key, current_value in value.items():
                    if str(current_key).lower() in key_set:
                        if current_value not in (None, "", [], {}):
                            return current_value
                for current_value in value.values():
                    found = walk(current_value)
                    if found not in (None, "", [], {}):
                        return found
            elif isinstance(value, list):
                for item in value:
                    found = walk(item)
                    if found not in (None, "", [], {}):
                        return found
            return None

        return walk(data)

    def _normalize_id(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            candidate = str(int(value))
        else:
            candidate = str(value).strip()

        match = re.search(r"\d{10,}", candidate)
        if match:
            return match.group(0)

        if candidate and len(candidate) >= 6 and not candidate.startswith("{"):
            return candidate
        return ""

    def _extract_amount(self, value: Any) -> Optional[str]:
        if value in (None, "", [], {}):
            return None
        if isinstance(value, (int, float)):
            return f"{value:.2f}"

        text = str(value).strip()
        match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
        return match.group(1) if match else text or None

    def _extract_quantity(self, value: Any) -> int:
        if value in (None, "", [], {}):
            return 1
        if isinstance(value, (int, float)):
            return max(1, int(value))

        text = str(value).strip()
        match = re.search(r"(\d+)", text)
        if not match:
            return 1
        return max(1, int(match.group(1)))

    def _normalize_status(self, value: Any) -> str:
        if value in (None, "", [], {}):
            return "unknown"

        text = str(value).strip().lower()
        if any(keyword in text for keyword in ("退款撤销", "refund_cancelled")):
            return "refund_cancelled"
        if any(keyword in text for keyword in ("退款", "售后", "refunding", "refund")):
            return "refunding"
        if any(keyword in text for keyword in ("交易成功", "已完成", "completed", "finish", "success")):
            return "completed"
        if any(keyword in text for keyword in ("已发货", "待收货", "shipped", "consign")):
            return "shipped"
        if any(keyword in text for keyword in ("待发货", "已付款", "paid", "pending_ship", "buyer_paid")):
            return "pending_ship"
        if any(keyword in text for keyword in ("关闭", "取消", "cancel", "closed")):
            return "cancelled"
        if any(keyword in text for keyword in ("处理中", "待付款", "processing", "created")):
            return "processing"
        return "unknown"

    def _extract_bargain_flag(self, data: Dict[str, Any]) -> bool:
        text = str(data)
        return any(keyword in text for keyword in ("小刀", "讲价", "bargain", "haggle"))

    async def _maybe_click_order_tabs(self):
        if not self.page:
            return

        for label in ("已卖出", "待发货", "订单", "交易"):
            try:
                locator = self.page.get_by_text(label, exact=False).first
                if await locator.count() > 0:
                    await locator.click(timeout=1500)
                    await self.page.wait_for_timeout(1200)
            except Exception:
                continue

    async def fetch_orders(self, max_wait_ms: int = 8000) -> Dict[str, Any]:
        """抓取订单列表并返回结构化结果。"""
        if not await self.init_browser():
            return {"success": False, "message": "浏览器初始化失败", "orders": []}

        try:
            for url in self.CANDIDATE_URLS:
                if not self.page:
                    break
                try:
                    logger.info(f"【{self.cookie_id}】尝试抓取订单页: {url}")
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await self.page.wait_for_timeout(1800)
                    await self._maybe_click_order_tabs()
                    await self.page.mouse.wheel(0, 1600)
                    await self.page.wait_for_timeout(1200)
                    if self.orders_by_id:
                        break
                except Exception as exc:
                    logger.warning(f"【{self.cookie_id}】访问订单候选页失败 {url}: {exc}")

            if not self.orders_by_id and self.page:
                await self.page.wait_for_timeout(max_wait_ms)

            orders = list(self.orders_by_id.values())
            return {
                "success": True,
                "message": f"成功抓取 {len(orders)} 条真实订单" if orders else "未抓取到订单数据，请确认账号已登录且订单页结构未变化",
                "orders": orders,
            }
        except Exception as exc:
            logger.error(f"【{self.cookie_id}】抓取订单列表异常: {exc}")
            return {"success": False, "message": f"抓取订单列表失败: {exc}", "orders": []}
        finally:
            await self.close()

    async def close(self):
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception as exc:
            logger.warning(f"【{self.cookie_id}】关闭订单列表抓取浏览器失败: {exc}")


async def fetch_order_list_simple(cookie_string: str, cookie_id: str, headless: bool = True) -> Dict[str, Any]:
    fetcher = OrderListFetcher(cookie_string=cookie_string, cookie_id=cookie_id, headless=headless)
    return await fetcher.fetch_orders()
