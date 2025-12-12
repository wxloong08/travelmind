"""
认证依赖注入

提供 FastAPI 依赖函数，用于获取当前用户/游客
"""

from dataclasses import dataclass
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.jwt import verify_token, TOKEN_TYPE_ACCESS, TOKEN_TYPE_GUEST
from src.db.database import get_db, is_db_configured
from src.db.models import User, Guest

logger = structlog.get_logger()

# Bearer Token 认证
security = HTTPBearer(auto_error=False)


@dataclass
class CurrentIdentity:
    """
    当前身份
    
    可能是注册用户或游客
    """
    user: User | None = None
    guest: Guest | None = None
    
    @property
    def is_authenticated(self) -> bool:
        """是否已认证（包括游客）"""
        return self.user is not None or self.guest is not None
    
    @property
    def is_registered(self) -> bool:
        """是否注册用户"""
        return self.user is not None
    
    @property
    def is_guest(self) -> bool:
        """是否游客"""
        return self.guest is not None and self.user is None
    
    @property
    def id(self) -> str | None:
        """身份 ID"""
        if self.user:
            return self.user.id
        if self.guest:
            return self.guest.id
        return None
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.user:
            return self.user.display_name
        if self.guest:
            return "游客"
        return "匿名"


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db=Depends(get_db),
) -> User:
    """
    获取当前登录用户（必须）
    
    如果未登录或 Token 无效，抛出 401 错误
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 Token
    payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 查询用户
    from src.db.repositories import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.sub)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    
    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db=Depends(get_db),
) -> User | None:
    """
    获取当前登录用户（可选）
    
    如果未登录返回 None，不抛出错误
    """
    if not credentials:
        return None
    
    # 验证 Token
    payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
    if not payload:
        return None
    
    # 查询用户
    from src.db.repositories import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.sub)
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_guest(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db=Depends(get_db),
) -> Guest | None:
    """
    获取当前游客
    
    如果不是游客 Token 返回 None
    """
    if not credentials:
        return None
    
    # 验证 Token
    payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_GUEST)
    if not payload:
        return None
    
    # 查询游客
    from src.db.repositories import GuestRepository
    guest_repo = GuestRepository(db)
    guest = await guest_repo.get_by_id(payload.sub)
    
    return guest


async def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db=Depends(get_db),
) -> CurrentIdentity:
    """
    获取当前身份（用户或游客）
    
    这是最常用的依赖，同时支持注册用户和游客
    """
    identity = CurrentIdentity()
    
    if not credentials:
        return identity
    
    # 先尝试验证为用户 Token
    payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
    if payload:
        from src.db.repositories import UserRepository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(payload.sub)
        if user and user.is_active:
            identity.user = user
            return identity
    
    # 再尝试验证为游客 Token
    payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_GUEST)
    if payload:
        from src.db.repositories import GuestRepository
        guest_repo = GuestRepository(db)
        guest = await guest_repo.get_by_id(payload.sub)
        if guest:
            identity.guest = guest
            return identity
    
    return identity


async def require_auth(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
) -> CurrentIdentity:
    """
    要求已认证（用户或游客）
    
    如果未认证抛出 401 错误
    """
    if not identity.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录或以游客身份访问",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return identity


async def require_user(
    identity: Annotated[CurrentIdentity, Depends(get_current_identity)],
) -> User:
    """
    要求注册用户
    
    游客不允许访问，抛出 403 错误
    """
    if not identity.is_registered:
        if identity.is_guest:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此功能需要登录，游客无法访问",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return identity.user
