"""
TravelMind 认证模块

提供:
- JWT Token 管理
- 短信验证码
- 依赖注入（获取当前用户）
"""

from src.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_guest_token,
    verify_token,
    TokenPayload,
)
from src.auth.deps import (
    get_current_user,
    get_current_user_optional,
    get_current_guest,
    get_current_identity,
    CurrentIdentity,
)
from src.auth.sms import SMSService, sms_service

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "create_guest_token",
    "verify_token",
    "TokenPayload",
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "get_current_guest",
    "get_current_identity",
    "CurrentIdentity",
    # SMS
    "SMSService",
    "sms_service",
]
