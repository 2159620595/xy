from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel

from judian.judian_backend import (
    app as judian_app,
    issue_judian_session,
    shutdown_judian_runtime,
    startup_judian_runtime,
)
from netdisk.main import (
    ADMIN_SESSION_COOKIE_NAME,
    ADMIN_SESSION_COOKIE_SECURE,
    ADMIN_SESSION_TTL_SECONDS,
    app as app,
    build_admin_session_token,
)

logger = logging.getLogger(__name__)
_original_lifespan = app.router.lifespan_context


class EmbeddedSessionRequest(BaseModel):
    username: str
    role: str | None = "admin"
    tenant_id: str | None = "tenant_001"


async def _run_runtime_startup(name: str, startup_coro: Any) -> None:
    try:
        await startup_coro
        logger.info("%s 运行时后台启动完成", name)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("%s 运行时后台启动失败: %s", name, exc)


@asynccontextmanager
async def combined_lifespan(app_instance: Any):
    startup_tasks: list[asyncio.Task[Any]] = []
    async with _original_lifespan(app_instance):
        startup_tasks = [
            asyncio.create_task(
                _run_runtime_startup("聚店", startup_judian_runtime()),
                name="startup-judian-runtime",
            ),
        ]
        try:
            yield
        finally:
            for task in startup_tasks:
                if task and not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await task
            await shutdown_judian_runtime()


app.router.lifespan_context = combined_lifespan


def _normalize_embedded_session_body(body: EmbeddedSessionRequest) -> tuple[str, str, str]:
    username = str(body.username or "").strip()
    role = str(body.role or "admin").strip() or "admin"
    tenant_id = str(body.tenant_id or "tenant_001").strip() or "tenant_001"
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    return username, role, tenant_id


@app.post("/api/netdisk/session")
def bootstrap_netdisk_session(body: EmbeddedSessionRequest, response: Response):
    username, role, tenant_id = _normalize_embedded_session_body(body)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        value=build_admin_session_token(username=username, tenant_id=tenant_id, role=role),
        httponly=True,
        secure=ADMIN_SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=ADMIN_SESSION_TTL_SECONDS,
        path="/",
    )
    return {
        "success": True,
        "message": "网盘会话同步成功",
        "username": username,
        "tenant_id": tenant_id,
        "role": role,
    }


@app.post("/api/judian/session")
def bootstrap_judian_session(body: EmbeddedSessionRequest, request: Request):
    username, role, _tenant_id = _normalize_embedded_session_body(body)
    payload = issue_judian_session(username=username, role=role, request=request)
    if payload is None:
        raise HTTPException(status_code=500, detail="聚点共享登录态同步失败")
    return payload


if not any(getattr(route, "path", None) == "/judian_api" for route in app.router.routes):
    app.mount("/judian_api", judian_app)
