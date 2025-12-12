"""
认证 API 路由

提供:
- 游客模式
- 短信验证码登录
- Token 刷新
- 用户信息
"""

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_guest_token,
    verify_token,
    TOKEN_TYPE_REFRESH,
)
from src.auth.sms import sms_service
from src.auth.deps import (
    get_current_user,
    get_current_identity,
    CurrentIdentity,
)
from src.config import settings
from src.db.database import get_db, is_db_configured
from src.db.repositories import UserRepository, GuestRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================
# 请求/响应模型
# ============================================================

class GuestRequest(BaseModel):
    """游客请求"""
    device_fingerprint: str = Field(..., min_length=16, max_length=64, description="设备指纹")


class GuestResponse(BaseModel):
    """游客响应"""
    token: str
    guest_id: str
    remaining_today: int
    message: str


class SendSMSRequest(BaseModel):
    """发送验证码请求"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")


class SendSMSResponse(BaseModel):
    """发送验证码响应"""
    success: bool
    message: str
    # 开发模式会返回验证码
    code: str | None = None


class VerifySMSRequest(BaseModel):
    """验证短信请求"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")


class UserInfo(BaseModel):
    """用户信息"""
    id: str
    phone: str | None
    nickname: str | None
    avatar_url: str | None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    user: UserInfo | None = None
    is_new_user: bool = False


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    id: str
    phone: str | None
    nickname: str | None
    avatar_url: str | None
    is_guest: bool
    created_at: str


# ============================================================
# 游客模式
# ============================================================

@router.post(
    "/guest",
    response_model=GuestResponse,
    summary="获取游客 Token",
    description="基于设备指纹获取游客访问权限，每日限制 1 次生成行程",
)
async def get_guest_token(
    request: GuestRequest,
    db=Depends(get_db),
):
    """
    游客模式入口
    
    - 基于设备指纹识别
    - 每日限制 1 次完整使用
    """
    if not is_db_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未配置",
        )
    
    guest_repo = GuestRepository(db)
    
    # 获取或创建游客
    guest, created = await guest_repo.get_or_create(request.device_fingerprint)
    
    if created:
        logger.info("New guest created", guest_id=guest.id)
    
    # 获取剩余次数
    remaining = await guest_repo.get_remaining_usage(guest)
    
    # 生成 Token
    token = create_guest_token(guest.id)
    
    return GuestResponse(
        token=token,
        guest_id=guest.id,
        remaining_today=remaining,
        message=f"今日剩余 {remaining} 次使用机会" if remaining > 0 else "今日使用次数已用完，请明天再来或登录获取更多",
    )


# ============================================================
# 短信验证码登录
# ============================================================

@router.post(
    "/sms/send",
    response_model=SendSMSResponse,
    summary="发送短信验证码",
)
async def send_sms_code(request: SendSMSRequest):
    """
    发送短信验证码
    
    - 60 秒内不可重复发送
    - 验证码 5 分钟有效
    """
    success, message = await sms_service.send_verification_code(request.phone)
    
    response = SendSMSResponse(success=success, message=message)
    
    # 开发模式返回验证码（方便测试）
    if success and not settings.sms_enabled:
        response.code = message  # 开发模式下 message 就是验证码
        response.message = f"开发模式：验证码为 {message}"
    
    return response


@router.post(
    "/sms/verify",
    response_model=TokenResponse,
    summary="验证短信并登录",
)
async def verify_sms_and_login(
    request: VerifySMSRequest,
    db=Depends(get_db),
):
    """
    验证短信验证码并登录/注册
    
    - 验证成功后自动注册（如果是新用户）
    - 返回 Access Token 和 Refresh Token
    """
    if not is_db_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未配置",
        )
    
    # 验证验证码
    success, message = sms_service.verify_code(request.phone, request.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    
    # 获取或创建用户
    user_repo = UserRepository(db)
    user, is_new = await user_repo.get_or_create_by_phone(request.phone)
    
    if is_new:
        logger.info("New user registered", user_id=user.id, phone=request.phone[:3] + "****")
    else:
        logger.info("User logged in", user_id=user.id)
    
    # 生成 Token
    access_token = create_access_token(user.id, phone=request.phone)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=user.id,
        user=UserInfo(
            id=user.id,
            phone=request.phone[:3] + "****" + request.phone[-4:],
            nickname=user.nickname,
            avatar_url=user.avatar_url,
        ),
        is_new_user=is_new,
    )


# ============================================================
# Token 刷新
# ============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新 Access Token",
)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db=Depends(get_db),
):
    """
    使用 Refresh Token 获取新的 Access Token
    """
    # 验证 Refresh Token
    payload = verify_token(request.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的 Refresh Token",
        )
    
    # 查询用户
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.sub)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    # 生成新的 Token
    access_token = create_access_token(user.id, phone=user.phone)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=user.id,
        user=UserInfo(
            id=user.id,
            phone=user.phone[:3] + "****" + user.phone[-4:] if user.phone else None,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
        ),
    )


# ============================================================
# 用户信息
# ============================================================

@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="获取当前用户信息",
)
async def get_current_user_info(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
):
    """
    获取当前登录用户或游客的信息
    """
    if identity.user:
        return UserInfoResponse(
            id=identity.user.id,
            phone=identity.user.phone[:3] + "****" + identity.user.phone[-4:] if identity.user.phone else None,
            nickname=identity.user.nickname,
            avatar_url=identity.user.avatar_url,
            is_guest=False,
            created_at=identity.user.created_at.isoformat(),
        )
    
    if identity.guest:
        return UserInfoResponse(
            id=identity.guest.id,
            phone=None,
            nickname="游客",
            avatar_url=None,
            is_guest=True,
            created_at=identity.guest.created_at.isoformat(),
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未登录",
    )


@router.post(
    "/logout",
    summary="登出",
)
async def logout():
    """
    登出
    
    客户端应该删除本地存储的 Token
    """
    # JWT 是无状态的，服务端不需要做任何事情
    # 如果需要黑名单功能，可以将 Token 加入 Redis 黑名单
    return {"message": "登出成功"}


# ============================================================
# 激活码和配额
# ============================================================

class ActivateCodeRequest(BaseModel):
    """激活码请求"""
    code: str = Field(..., min_length=10, max_length=32, description="激活码")


class QuotaInfoResponse(BaseModel):
    """配额信息响应"""
    daily_quota: int
    bonus_quota: int
    used_today: int
    remaining_today: int
    remaining_daily: int
    remaining_bonus: int
    role: str
    is_unlimited: bool = False


@router.post(
    "/activate",
    summary="使用激活码",
)
async def activate_code(
    request: ActivateCodeRequest,
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    db=Depends(get_db),
):
    """
    使用激活码升级账户或增加次数
    
    - 需要已登录的用户（不支持游客）
    - 激活码只能使用一次
    """
    if not identity.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再使用激活码",
        )
    
    from src.services.quota_service import QuotaService
    
    quota_service = QuotaService(db)
    success, message = await quota_service.use_activation_code(
        user_id=identity.user.id,
        code=request.code,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    
    # 返回更新后的配额信息
    quota_info = await quota_service.get_user_quota_info(identity.user)
    
    return {
        "message": message,
        "quota": quota_info,
    }


@router.get(
    "/quota",
    response_model=QuotaInfoResponse,
    summary="获取配额信息",
)
async def get_quota_info(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    db=Depends(get_db),
):
    """
    获取当前用户/游客的配额信息
    """
    from src.services.quota_service import QuotaService
    
    quota_service = QuotaService(db)
    
    if identity.user:
        quota_info = await quota_service.get_user_quota_info(identity.user)
    elif identity.guest:
        quota_info = await quota_service.get_guest_quota_info(identity.guest)
        # 游客额外字段
        quota_info["role"] = "guest"
        quota_info["remaining_daily"] = quota_info["remaining_today"]
        quota_info["remaining_bonus"] = 0
        quota_info["is_unlimited"] = False
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    
    return QuotaInfoResponse(**quota_info)


@router.post(
    "/consume-quota",
    summary="消耗配额",
    description="在发送聊天消息前调用，检查并消耗一次配额",
)
async def consume_quota(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
    db=Depends(get_db),
):
    """
    消耗一次配额
    
    - 成功：返回剩余配额信息
    - 失败：返回 402 或 403 错误
    """
    from src.services.quota_service import QuotaService
    
    quota_service = QuotaService(db)
    
    # 获取用户或游客 ID
    user_id = identity.user.id if identity.user else None
    guest_id = identity.guest.id if identity.guest else None
    
    if not user_id and not guest_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    
    # 检查并消耗配额
    success, message, quota_info = await quota_service.check_and_consume(
        user_id=user_id,
        guest_id=guest_id,
    )
    
    if not success:
        # 配额不足
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=message,
        )
    
    logger.info(
        "Quota consumed",
        user_id=user_id,
        guest_id=guest_id,
        remaining=quota_info.get("remaining_today"),
    )
    
    return {
        "success": True,
        "message": message,
        "remaining_today": quota_info.get("remaining_today", 0),
        "is_guest": bool(guest_id),
    }

