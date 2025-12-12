"""
JWT Token 管理

提供:
- Access Token: 短期有效，用于 API 认证
- Refresh Token: 长期有效，用于刷新 Access Token
- Guest Token: 游客标识
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import settings

logger = structlog.get_logger()

# 算法
ALGORITHM = "HS256"

# Token 类型
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_GUEST = "guest"


class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str                    # 主题（用户 ID 或游客 ID）
    type: str                   # Token 类型
    exp: datetime               # 过期时间
    iat: datetime               # 签发时间
    
    # 可选字段
    phone: str | None = None    # 手机号（脱敏）
    is_guest: bool = False      # 是否游客


def _get_secret_key() -> str:
    """获取密钥"""
    if not settings.secret_key:
        raise ValueError(
            "SECRET_KEY not configured. "
            "Please set SECRET_KEY in your .env file."
        )
    return settings.secret_key


def create_access_token(
    user_id: str,
    phone: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建 Access Token
    
    Args:
        user_id: 用户 ID
        phone: 手机号（可选，用于显示）
        expires_delta: 自定义过期时间
    
    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_ACCESS,
        "exp": expire,
        "iat": now,
        "phone": phone[:3] + "****" + phone[-4:] if phone else None,
        "is_guest": False,
    }
    
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建 Refresh Token
    
    Args:
        user_id: 用户 ID
        expires_delta: 自定义过期时间（默认 7 天）
    
    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=7)
    
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_REFRESH,
        "exp": expire,
        "iat": now,
        "is_guest": False,
    }
    
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def create_guest_token(
    guest_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建 Guest Token
    
    Args:
        guest_id: 游客 ID
        expires_delta: 自定义过期时间（默认 24 小时）
    
    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=24)
    
    payload = {
        "sub": guest_id,
        "type": TOKEN_TYPE_GUEST,
        "exp": expire,
        "iat": now,
        "is_guest": True,
    }
    
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def verify_token(token: str, expected_type: str | None = None) -> TokenPayload | None:
    """
    验证 Token
    
    Args:
        token: JWT Token 字符串
        expected_type: 期望的 Token 类型（可选）
    
    Returns:
        TokenPayload 或 None（验证失败）
    """
    try:
        payload = jwt.decode(
            token,
            _get_secret_key(),
            algorithms=[ALGORITHM],
        )
        
        # 检查类型
        token_type = payload.get("type")
        if expected_type and token_type != expected_type:
            logger.warning(
                "Token type mismatch",
                expected=expected_type,
                actual=token_type,
            )
            return None
        
        return TokenPayload(
            sub=payload["sub"],
            type=payload["type"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            phone=payload.get("phone"),
            is_guest=payload.get("is_guest", False),
        )
        
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error during token verification", error=str(e))
        return None


def decode_token_unsafe(token: str) -> dict[str, Any] | None:
    """
    解码 Token（不验证签名）
    
    仅用于调试或获取过期 Token 的信息
    """
    try:
        return jwt.decode(
            token,
            _get_secret_key(),
            algorithms=[ALGORITHM],
            options={"verify_signature": False, "verify_exp": False},
        )
    except Exception:
        return None
