"""
对话和消息模型

存储用户的对话历史
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.db.models.user import User
    from src.db.models.guest import Guest
    from src.db.models.trip import Trip


class Conversation(Base, UUIDMixin, TimestampMixin):
    """
    对话表
    
    一个对话可以包含多条消息，可能关联一个行程
    """
    __tablename__ = "conversations"
    
    # 归属
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="用户 ID",
    )
    guest_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="游客 ID",
    )
    
    # 前端会话标识
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="前端 session 标识",
    )
    
    # 关联行程
    trip_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("trips.id", ondelete="SET NULL"),
        nullable=True,
        comment="生成的行程 ID",
    )
    
    # 对话信息
    title: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="对话标题（自动生成）",
    )
    message_count: Mapped[int] = mapped_column(
        default=0,
        comment="消息数量",
    )
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        comment="状态: active, archived",
    )
    
    # 关系
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="conversations",
    )
    guest: Mapped["Guest | None"] = relationship(
        "Guest",
        back_populates="conversations",
    )
    trip: Mapped["Trip | None"] = relationship(
        "Trip",
        back_populates="conversations",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        lazy="selectin",
        order_by="Message.created_at",
    )
    
    # 每用户消息限制
    MAX_MESSAGES_PER_USER: int = 100
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, session={self.session_id[:8]}...)>"


class Message(Base, UUIDMixin, TimestampMixin):
    """
    消息表
    
    存储对话中的每条消息
    """
    __tablename__ = "messages"
    
    # 所属对话
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="对话 ID",
    )
    
    # 消息内容
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="角色: user, assistant, system",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )
    
    # 元数据（注意：不能使用 'metadata' 作为字段名，这是 SQLAlchemy 保留字）
    meta_info: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="元数据 JSON: task_type, tokens 等",
    )
    
    # 关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Message(id={self.id}, role={self.role}, content='{content_preview}')>"
