"""
用户模型

支持手机号登录，包含用户等级和配额管理
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.db.models.trip import Trip
    from src.db.models.conversation import Conversation


class UserRole(str, Enum):
    """用户角色"""
    FREE = "free"       # 免费用户（已注册，每日3次）
    PAID = "paid"       # 付费用户（每日20次）
    ADMIN = "admin"     # 管理员（无限制）


# 默认配额配置
DEFAULT_QUOTAS = {
    UserRole.FREE: 3,   # 免费用户每日3次
    UserRole.PAID: 20,  # 付费用户每日20次
    UserRole.ADMIN: 999,  # 管理员无限制
}


class User(Base, UUIDMixin, TimestampMixin):
    """
    注册用户表
    
    支持手机号登录（后续可扩展微信登录）
    """
    __tablename__ = "users"
    
    # 登录凭证
    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=True,
        comment="手机号（唯一）",
    )
    
    # 微信登录（预留）
    wechat_openid: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=True,
        comment="微信 OpenID（预留）",
    )
    
    # 用户信息
    nickname: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="昵称",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="头像 URL",
    )
    
    # 密码（可选，用户可以选择不设置密码）
    password_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="密码哈希（bcrypt）",
    )
    
    # ============ 用户等级和配额 ============
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.FREE.value,
        comment="用户角色: free/paid/admin",
    )
    
    daily_quota: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="每日配额上限（可被管理员修改）",
    )
    
    bonus_quota: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="额外次数（用完即止，不会每日重置）",
    )
    
    # 偏好设置
    preferences: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="用户偏好设置 JSON",
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(
        default=True,
        comment="是否激活",
    )
    
    # 最后登录时间
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间",
    )
    
    # 关系
    trips: Mapped[list["Trip"]] = relationship(
        "Trip",
        back_populates="user",
        lazy="selectin",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone}, role={self.role})>"
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.nickname:
            return self.nickname
        if self.phone:
            # 脱敏手机号
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        return "用户"
    
    @property
    def is_admin(self) -> bool:
        """是否是管理员"""
        return self.role == UserRole.ADMIN.value
    
    @property
    def is_paid(self) -> bool:
        """是否是付费用户"""
        return self.role == UserRole.PAID.value
    
    def get_effective_daily_quota(self) -> int:
        """获取有效的每日配额"""
        # 如果有自定义配额，使用自定义的；否则使用角色默认值
        if self.daily_quota > 0:
            return self.daily_quota
        role = UserRole(self.role) if self.role in [r.value for r in UserRole] else UserRole.FREE
        return DEFAULT_QUOTAS.get(role, 3)
