"""
游客模型

基于设备指纹识别，限制每日使用次数
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.db.models.trip import Trip
    from src.db.models.conversation import Conversation


class Guest(Base, UUIDMixin, TimestampMixin):
    """
    游客表
    
    基于设备指纹限制每日使用次数
    """
    __tablename__ = "guests"
    
    # 设备标识
    device_fingerprint: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="设备指纹（前端生成的唯一标识）",
    )
    
    # 每日使用计数
    daily_usage_count: Mapped[int] = mapped_column(
        default=0,
        comment="当日已使用次数",
    )
    last_usage_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="最后使用日期（用于重置计数）",
    )
    
    # 累计使用次数
    total_usage_count: Mapped[int] = mapped_column(
        default=0,
        comment="累计使用次数",
    )
    
    # 关系
    trips: Mapped[list["Trip"]] = relationship(
        "Trip",
        back_populates="guest",
        lazy="selectin",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="guest",
        lazy="selectin",
    )
    
    # 每日限制次数
    DAILY_LIMIT: int = 1
    
    def __repr__(self) -> str:
        return f"<Guest(id={self.id}, fingerprint={self.device_fingerprint[:8]}...)>"
    
    def can_use_today(self) -> bool:
        """检查今天是否还能使用"""
        today = date.today()
        
        # 如果是新的一天，重置计数
        if self.last_usage_date != today:
            return True
        
        return self.daily_usage_count < self.DAILY_LIMIT
    
    def increment_usage(self) -> bool:
        """
        增加使用次数
        
        Returns:
            是否成功（未超过限制）
        """
        today = date.today()
        
        # 新的一天，重置计数
        if self.last_usage_date != today:
            self.daily_usage_count = 0
            self.last_usage_date = today
        
        # 检查限制
        if self.daily_usage_count >= self.DAILY_LIMIT:
            return False
        
        self.daily_usage_count += 1
        self.total_usage_count += 1
        return True
    
    @property
    def remaining_today(self) -> int:
        """今日剩余次数"""
        today = date.today()
        
        if self.last_usage_date != today:
            return self.DAILY_LIMIT
        
        return max(0, self.DAILY_LIMIT - self.daily_usage_count)
