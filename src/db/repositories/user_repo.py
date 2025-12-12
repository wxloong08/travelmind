"""
用户数据访问层
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User


class UserRepository:
    """用户数据访问"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        phone: str | None = None,
        nickname: str | None = None,
        wechat_openid: str | None = None,
    ) -> User:
        """创建用户"""
        user = User(
            phone=phone,
            nickname=nickname,
            wechat_openid=wechat_openid,
            last_login_at=datetime.utcnow(),
        )
        self.session.add(user)
        await self.session.flush()
        return user
    
    async def get_by_id(self, user_id: str) -> User | None:
        """根据 ID 获取用户"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, phone: str) -> User | None:
        """根据手机号获取用户"""
        result = await self.session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()
    
    async def get_by_wechat_openid(self, openid: str) -> User | None:
        """根据微信 OpenID 获取用户"""
        result = await self.session.execute(
            select(User).where(User.wechat_openid == openid)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_by_phone(self, phone: str) -> tuple[User, bool]:
        """
        根据手机号获取或创建用户
        
        Returns:
            (user, created): 用户对象和是否新创建
        """
        user = await self.get_by_phone(phone)
        if user:
            # 更新最后登录时间
            user.last_login_at = datetime.utcnow()
            return user, False
        
        user = await self.create(phone=phone)
        return user, True
    
    async def update_last_login(self, user: User) -> None:
        """更新最后登录时间"""
        user.last_login_at = datetime.utcnow()
    
    async def update_preferences(self, user: User, preferences: dict) -> None:
        """更新用户偏好"""
        if user.preferences:
            user.preferences.update(preferences)
        else:
            user.preferences = preferences
    
    async def update_profile(
        self,
        user: User,
        nickname: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """更新用户资料"""
        if nickname is not None:
            user.nickname = nickname
        if avatar_url is not None:
            user.avatar_url = avatar_url
