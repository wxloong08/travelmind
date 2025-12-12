"""
使用记录模型

跟踪用户/游客的每日使用次数
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.db.models.user import User
    from src.db.models.guest import Guest


class UsageRecord(Base, UUIDMixin, TimestampMixin):
    """
    使用记录表
    
    记录每次行程规划，用于统计和限流
    """
    __tablename__ = "usage_records"
    
    # 用户/游客（二选一）
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="用户 ID",
    )
    
    guest_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("guests.id"),
        nullable=True,
        index=True,
        comment="游客 ID",
    )
    
    # 使用日期（用于按日统计）
    usage_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="使用日期",
    )
    
    # 使用时间
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="使用时间",
    )
    
    # 目的地（可选，用于统计）
    destination: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="规划的目的地",
    )
    
    # 天数
    days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="规划的天数",
    )
    
    # 会话 ID
    session_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="会话 ID",
    )
    
    # 关系
    user: Mapped["User | None"] = relationship(
        "User",
        lazy="selectin",
    )
    guest: Mapped["Guest | None"] = relationship(
        "Guest",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        identity = f"user={self.user_id}" if self.user_id else f"guest={self.guest_id}"
        return f"<UsageRecord({identity}, date={self.usage_date}, dest={self.destination})>"


class DailyUsageSummary(Base, UUIDMixin):
    """
    每日使用汇总表
    
    用于快速查询当日剩余次数，避免每次都 count
    """
    __tablename__ = "daily_usage_summary"
    
    # 用户/游客（二选一）
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="用户 ID",
    )
    
    guest_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("guests.id"),
        nullable=True,
        index=True,
        comment="游客 ID",
    )
    
    # 日期
    usage_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="日期",
    )
    
    # 当日使用次数
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="当日已使用次数",
    )
    
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="最后更新时间",
    )
    
    def __repr__(self) -> str:
        identity = f"user={self.user_id}" if self.user_id else f"guest={self.guest_id}"
        return f"<DailyUsageSummary({identity}, date={self.usage_date}, count={self.usage_count})>"
