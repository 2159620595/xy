import hashlib
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app_logging import get_logger
from db_manager import db_manager

logger = get_logger(__name__)

TOKEN_EXPIRE_TIME = 24 * 60 * 60
security = HTTPBearer(auto_error=False)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def create_session_for_user(user: Dict[str, Any]) -> str:
    token = generate_token()
    expires_at = time.time() + TOKEN_EXPIRE_TIME
    db_manager.save_auth_session(hash_token(token), int(user["id"]), expires_at)
    return token


def get_session_user(session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    current_user = db_manager.get_user_by_id(int(session_data["user_id"]))
    if not current_user or not current_user.get("is_active", True):
        return None
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user.get("email"),
        "nickname": current_user.get("nickname"),
        "is_admin": bool(current_user.get("is_admin")),
        "is_active": current_user.get("is_active", True),
        "created_at": current_user.get("created_at"),
        "updated_at": current_user.get("updated_at"),
    }


def delete_session_by_token(token: str) -> None:
    if token:
        db_manager.delete_auth_session(hash_token(token))


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None

    token = credentials.credentials
    token_hash = hash_token(token)
    session_data = db_manager.get_auth_session(token_hash)
    if not session_data:
        return None

    if float(session_data.get("expires_at") or 0) <= time.time():
        db_manager.delete_auth_session(token_hash)
        return None

    current_user = get_session_user(session_data)
    if not current_user:
        db_manager.delete_auth_session(token_hash)
        return None

    return {
        "token": token,
        "user_id": current_user["id"],
        "username": current_user["username"],
        "is_admin": current_user["is_admin"],
        "session_id": session_data["id"],
        "expires_at": session_data["expires_at"],
        "user_cache": current_user,
    }


def verify_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    user_info = verify_token(credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="未授权访问")
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user_info


def require_auth(user_info: Optional[Dict[str, Any]] = Depends(verify_token)) -> Dict[str, Any]:
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return user_info


def get_current_user(user_info: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    return user_info


def get_current_user_optional(
    user_info: Optional[Dict[str, Any]] = Depends(verify_token),
) -> Optional[Dict[str, Any]]:
    return user_info


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def get_user_log_prefix(user_info: Optional[Dict[str, Any]] = None) -> str:
    if user_info:
        return f"【{user_info['username']}#{user_info['user_id']}】"
    return "【系统】"


def log_with_user(level: str, message: str, user_info: Optional[Dict[str, Any]] = None) -> None:
    full_message = f"{get_user_log_prefix(user_info)} {message}"
    normalized_level = str(level or "info").lower()
    if normalized_level == "error":
        logger.error(full_message)
    elif normalized_level == "warning":
        logger.warning(full_message)
    elif normalized_level == "debug":
        logger.debug(full_message)
    else:
        logger.info(full_message)


def can_access_cookie(cookie_id: str, current_user: Dict[str, Any]) -> bool:
    if current_user.get("is_admin"):
        return True
    user_cookies = db_manager.get_all_cookies(current_user["user_id"])
    return cookie_id in user_cookies


def ensure_cookie_access(cookie_id: str, current_user: Dict[str, Any], action: str = "访问") -> None:
    if not can_access_cookie(cookie_id, current_user):
        raise HTTPException(status_code=403, detail=f"无权限{action}该Cookie")
