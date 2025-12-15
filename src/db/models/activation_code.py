"""
激活码模型

用于用户升级和增加配额
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class CodeType(str, Enum):
    """激活码类型"""
    UPGRADE_PAID = "upgrade_paid"    # 升级为付费用户
    ADD_QUOTA = "add_quota"          # 增加额外次数
    EXTEND_PAID = "extend_paid"      # 延长付费期限（预留）


class ActivationCode(Base, UUIDMixin, TimestampMixin):
    """
    激活码表
    
    用于：
    - 升级用户为付费用户
    - 为用户增加额外使用次数
    """
    __tablename__ = "activation_codes"
    
    # 激活码（唯一）
    code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        comment="激活码（如 TRAVEL-XXXX-XXXX）",
    )
    
    # 激活码类型
    code_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="类型: upgrade_paid/add_quota",
    )
    
    # 配额值（对于 add_quota 类型）
    quota_value: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="配额值（add_quota 类型时有效）",
    )
    
    # 备注
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注（如：送给张三的激活码）",
    )
    
    # 有效期
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间（null 表示永久有效）",
    )
    
    # 使用状态
    is_used: Mapped[bool] = mapped_column(
        default=False,
        comment="是否已使用",
    )
    
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="使用时间",
    )
    
    used_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=True,
        comment="使用者 ID",
    )
    
    # 创建者（管理员）
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=True,
        comment="创建者 ID",
    )
    
    # 关系
    used_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[used_by_id],
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<ActivationCode(code={self.code}, type={self.code_type}, used={self.is_used})>"
    
    @property
    def is_valid(self) -> bool:
        """是否有效（未使用且未过期）"""
        if self.is_used:
            return False
        if self.expires_at and datetime.now(self.expires_at.tzinfo) > self.expires_at:
            return False
        return True
