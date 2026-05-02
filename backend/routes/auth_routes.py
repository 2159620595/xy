from typing import Any, Dict, Optional

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from api_auth import create_session_for_user, delete_session_by_token
from app_logging import get_logger
from db_manager import db_manager

logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    verification_code: Optional[str] = None


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    is_admin: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    verification_code: str


class RegisterResponse(BaseModel):
    success: bool
    message: str


class SendCodeRequest(BaseModel):
    email: str
    session_id: Optional[str] = None
    type: Optional[str] = "register"


class SendCodeResponse(BaseModel):
    success: bool
    message: str


class CaptchaRequest(BaseModel):
    session_id: str


class CaptchaResponse(BaseModel):
    success: bool
    captcha_image: str
    session_id: str
    message: str


class VerifyCaptchaRequest(BaseModel):
    session_id: str
    captcha_code: str


class VerifyCaptchaResponse(BaseModel):
    success: bool
    message: str


async def login(request: LoginRequest) -> LoginResponse:
    if request.username and request.password:
        logger.info(f"【{request.username}】尝试用户名登录")
        if db_manager.verify_user_password(request.username, request.password):
            user = db_manager.get_user_by_username(request.username)
            if user:
                token = create_session_for_user(user)
                logger.info(f"【{user['username']}#{user['id']}】登录成功{'（管理员）' if user.get('is_admin') else ''}")
                return LoginResponse(
                    success=True,
                    token=token,
                    message="登录成功",
                    user_id=user["id"],
                    username=user["username"],
                    is_admin=bool(user.get("is_admin")),
                )
        logger.warning(f"【{request.username}】登录失败：用户名或密码错误")
        return LoginResponse(success=False, message="用户名或密码错误")

    if request.email and request.password:
        logger.info(f"【{request.email}】尝试邮箱密码登录")
        user = db_manager.get_user_by_email(request.email)
        if user and db_manager.verify_user_password(user["username"], request.password):
            token = create_session_for_user(user)
            logger.info(f"【{user['username']}#{user['id']}】邮箱登录成功")
            return LoginResponse(
                success=True,
                token=token,
                message="登录成功",
                user_id=user["id"],
                username=user["username"],
                is_admin=bool(user.get("is_admin")),
            )
        logger.warning(f"【{request.email}】邮箱登录失败：邮箱或密码错误")
        return LoginResponse(success=False, message="邮箱或密码错误")

    if request.email and request.verification_code:
        logger.info(f"【{request.email}】尝试邮箱验证码登录")
        if not db_manager.verify_email_code(request.email, request.verification_code, "login"):
            logger.warning(f"【{request.email}】验证码登录失败：验证码错误或已过期")
            return LoginResponse(success=False, message="验证码错误或已过期")

        user = db_manager.get_user_by_email(request.email)
        if not user:
            logger.warning(f"【{request.email}】验证码登录失败：用户不存在")
            return LoginResponse(success=False, message="用户不存在")

        token = create_session_for_user(user)
        logger.info(f"【{user['username']}#{user['id']}】验证码登录成功")
        return LoginResponse(
            success=True,
            token=token,
            message="登录成功",
            user_id=user["id"],
            username=user["username"],
            is_admin=bool(user.get("is_admin")),
        )

    return LoginResponse(success=False, message="请提供有效的登录信息")


async def verify(user_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if user_info:
        return {
            "authenticated": True,
            "user_id": user_info["user_id"],
            "username": user_info["username"],
            "is_admin": bool(user_info.get("is_admin")),
        }
    return {"authenticated": False}


async def logout(credentials: Optional[HTTPAuthorizationCredentials]) -> Dict[str, str]:
    if credentials:
        delete_session_by_token(credentials.credentials)
    return {"message": "已登出"}


async def change_admin_password(request: ChangePasswordRequest, admin_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        username = admin_user.get("username")
        if not username:
            return {"success": False, "message": "无法获取管理员信息"}
        if not db_manager.verify_user_password(username, request.current_password):
            return {"success": False, "message": "当前密码错误"}

        success = db_manager.update_user_password(username, request.new_password)
        if success:
            db_manager.delete_user_auth_sessions(admin_user["user_id"])
            logger.info(f"【{username}#{admin_user['user_id']}】管理员密码修改成功")
            return {"success": True, "message": "密码修改成功，请重新登录"}
        return {"success": False, "message": "密码修改失败"}
    except Exception as exc:
        logger.error(f"修改管理员密码异常: {exc}")
        return {"success": False, "message": "系统错误"}


async def change_user_password(request: ChangePasswordRequest, current_user: Dict[str, Any]) -> Dict[str, Any]:
    try:
        username = current_user.get("username")
        user_id = current_user.get("user_id")
        if not username:
            return {"success": False, "message": "无法获取用户信息"}
        if not db_manager.verify_user_password(username, request.current_password):
            return {"success": False, "message": "当前密码错误"}

        success = db_manager.update_user_password(username, request.new_password)
        if success:
            db_manager.delete_user_auth_sessions(user_id)
            logger.info(f"【{username}#{user_id}】用户密码修改成功")
            return {"success": True, "message": "密码修改成功，请重新登录"}
        return {"success": False, "message": "密码修改失败"}
    except Exception as exc:
        logger.error(f"修改用户密码异常: {exc}")
        return {"success": False, "message": "系统错误"}


async def generate_captcha(request: CaptchaRequest) -> CaptchaResponse:
    try:
        captcha_text, captcha_image = db_manager.generate_captcha()
        if not captcha_image:
            return CaptchaResponse(
                success=False,
                captcha_image="",
                session_id=request.session_id,
                message="图形验证码生成失败",
            )
        if db_manager.save_captcha(request.session_id, captcha_text):
            return CaptchaResponse(
                success=True,
                captcha_image=captcha_image,
                session_id=request.session_id,
                message="图形验证码生成成功",
            )
        return CaptchaResponse(
            success=False,
            captcha_image="",
            session_id=request.session_id,
            message="图形验证码保存失败",
        )
    except Exception as exc:
        logger.error(f"生成图形验证码失败: {exc}")
        return CaptchaResponse(
            success=False,
            captcha_image="",
            session_id=request.session_id,
            message="图形验证码生成失败",
        )


async def verify_captcha(request: VerifyCaptchaRequest) -> VerifyCaptchaResponse:
    try:
        if db_manager.verify_captcha(request.session_id, request.captcha_code):
            return VerifyCaptchaResponse(success=True, message="图形验证码验证成功")
        return VerifyCaptchaResponse(success=False, message="图形验证码错误或已过期")
    except Exception as exc:
        logger.error(f"验证图形验证码失败: {exc}")
        return VerifyCaptchaResponse(success=False, message="图形验证码验证失败")


async def send_verification_code(request: SendCodeRequest) -> SendCodeResponse:
    try:
        if request.type == "register":
            if db_manager.get_user_by_email(request.email):
                return SendCodeResponse(success=False, message="该邮箱已被注册")
        elif request.type == "login":
            if not db_manager.get_user_by_email(request.email):
                return SendCodeResponse(success=False, message="该邮箱未注册")

        code = db_manager.generate_verification_code()
        if not db_manager.save_verification_code(request.email, code, request.type or "register"):
            return SendCodeResponse(success=False, message="验证码保存失败，请稍后重试")
        if await db_manager.send_verification_email(request.email, code):
            return SendCodeResponse(success=True, message="验证码已发送到您的邮箱，请查收")
        return SendCodeResponse(success=False, message="验证码发送失败，请检查邮箱地址或稍后重试")
    except Exception as exc:
        logger.error(f"发送验证码失败: {exc}")
        return SendCodeResponse(success=False, message="发送验证码失败，请稍后重试")


async def register(request: RegisterRequest) -> RegisterResponse:
    registration_enabled = db_manager.get_system_setting("registration_enabled")
    if registration_enabled != "true":
        logger.warning(f"【{request.username}】注册失败: 注册功能已关闭")
        return RegisterResponse(success=False, message="注册功能已关闭，请联系管理员")

    try:
        logger.info(f"【{request.username}】尝试注册，邮箱: {request.email}")
        if not db_manager.verify_email_code(request.email, request.verification_code):
            logger.warning(f"【{request.username}】注册失败: 验证码错误或已过期")
            return RegisterResponse(success=False, message="验证码错误或已过期")
        if db_manager.get_user_by_username(request.username):
            logger.warning(f"【{request.username}】注册失败: 用户名已存在")
            return RegisterResponse(success=False, message="用户名已存在")
        if db_manager.get_user_by_email(request.email):
            logger.warning(f"【{request.username}】注册失败: 邮箱已被注册")
            return RegisterResponse(success=False, message="该邮箱已被注册")
        if db_manager.create_user(request.username, request.email, request.password):
            logger.info(f"【{request.username}】注册成功")
            return RegisterResponse(success=True, message="注册成功，请登录")
        logger.error(f"【{request.username}】注册失败: 数据库操作失败")
        return RegisterResponse(success=False, message="注册失败，请稍后重试")
    except Exception as exc:
        logger.error(f"【{request.username}】注册异常: {exc}")
        return RegisterResponse(success=False, message="注册失败，请稍后重试")
