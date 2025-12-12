"""
对话数据访问层
"""

from sqlalchemy import select, desc, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.conversation import Conversation, Message


class ConversationRepository:
    """对话数据访问"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ========== Conversation CRUD ==========
    
    async def create_conversation(
        self,
        session_id: str,
        user_id: str | None = None,
        guest_id: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        """创建对话"""
        conversation = Conversation(
            session_id=session_id,
            user_id=user_id,
            guest_id=guest_id,
            title=title,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation
    
    async def get_conversation_by_id(self, conversation_id: str) -> Conversation | None:
        """根据 ID 获取对话"""
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_conversation_by_session(self, session_id: str) -> Conversation | None:
        """根据 session_id 获取对话"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(desc(Conversation.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_conversation(
        self,
        session_id: str,
        user_id: str | None = None,
        guest_id: str | None = None,
    ) -> tuple[Conversation, bool]:
        """获取或创建对话"""
        conversation = await self.get_conversation_by_session(session_id)
        if conversation:
            return conversation, False
        
        conversation = await self.create_conversation(
            session_id=session_id,
            user_id=user_id,
            guest_id=guest_id,
        )
        return conversation, True
    
    async def get_conversations_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """获取用户的所有对话"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status == "active")
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_conversations_by_guest(
        self,
        guest_id: str,
        limit: int = 10,
    ) -> list[Conversation]:
        """获取游客的所有对话"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.guest_id == guest_id)
            .where(Conversation.status == "active")
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def link_trip(self, conversation: Conversation, trip_id: str) -> None:
        """关联行程"""
        conversation.trip_id = trip_id
    
    async def archive_conversation(self, conversation: Conversation) -> None:
        """归档对话"""
        conversation.status = "archived"
    
    async def delete_conversation(self, conversation: Conversation) -> None:
        """删除对话（会级联删除消息）"""
        await self.session.delete(conversation)
    
    # ========== Message CRUD ==========
    
    async def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        meta_info: dict | None = None,
    ) -> Message:
        """添加消息"""
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            meta_info=meta_info,
        )
        self.session.add(message)
        
        # 更新对话消息计数
        conversation.message_count += 1
        
        await self.session.flush()
        return message
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """获取对话的消息列表"""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[Message]:
        """获取最近的消息"""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        # 按时间正序返回
        return list(reversed(messages))
    
    async def count_messages(self, conversation_id: str) -> int:
        """统计消息数量"""
        result = await self.session.execute(
            select(func.count(Message.id))
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()
    
    async def cleanup_old_messages(
        self,
        conversation_id: str,
        keep_count: int = 100,
    ) -> int:
        """清理旧消息，保留最近的 N 条"""
        # 获取要保留的消息 ID
        result = await self.session.execute(
            select(Message.id)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(keep_count)
        )
        keep_ids = [row[0] for row in result.all()]
        
        if not keep_ids:
            return 0
        
        # 删除其他消息
        delete_result = await self.session.execute(
            delete(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.id.notin_(keep_ids))
        )
        
        return delete_result.rowcount
