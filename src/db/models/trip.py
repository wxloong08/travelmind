"""
行程模型

存储用户生成的旅行计划
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.db.models.user import User
    from src.db.models.guest import Guest
    from src.db.models.conversation import Conversation


class Trip(Base, UUIDMixin, TimestampMixin):
    """
    行程表
    
    存储生成的旅行计划，支持用户和游客
    """
    __tablename__ = "trips"
    
    # 归属（用户或游客，二选一）
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="用户 ID（注册用户）",
    )
    guest_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="游客 ID",
    )
    
    # 基本信息
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="行程标题，如'北京4天3晚亲子游'",
    )
    destination: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="目的地城市",
    )
    days: Mapped[int] = mapped_column(
        nullable=False,
        comment="行程天数",
    )
    travel_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="出发日期",
    )
    
    # 预算信息
    user_budget: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="用户指定的预算（元）",
    )
    estimated_budget: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="系统估算的预算（元）",
    )
    
    # 行程数据（JSON 存储完整结构）
    itinerary_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="完整行程数据 JSON",
    )
    
    # AI 原始响应（用于调试和回溯）
    raw_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI 原始 Markdown 响应",
    )
    
    # 元数据快照
    weather_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="生成时的天气数据快照",
    )
    pois_snapshot: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="使用的 POI 数据快照",
    )
    
    # 关系
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="trips",
    )
    guest: Mapped["Guest | None"] = relationship(
        "Guest",
        back_populates="trips",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="trip",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Trip(id={self.id}, title={self.title}, destination={self.destination})>"
    
    @property
    def owner_type(self) -> str:
        """所有者类型"""
        if self.user_id:
            return "user"
        if self.guest_id:
            return "guest"
        return "unknown"
    
    @property
    def budget_summary(self) -> dict:
        """预算摘要"""
        return {
            "user_budget": self.user_budget,
            "estimated_budget": self.estimated_budget,
            "is_over_budget": (
                self.user_budget and self.estimated_budget and 
                self.estimated_budget > self.user_budget
            ),
        }
