"""
SQLAlchemy 数据模型

包含:
- User: 注册用户
- Guest: 游客
- Trip: 行程
- Conversation: 对话
- Message: 消息
- ActivationCode: 激活码
- UsageRecord: 使用记录
- DailyUsageSummary: 每日使用汇总
"""

from src.db.models.base import Base
from src.db.models.user import User, UserRole, DEFAULT_QUOTAS
from src.db.models.guest import Guest
from src.db.models.trip import Trip
from src.db.models.conversation import Conversation, Message
from src.db.models.activation_code import ActivationCode, CodeType
from src.db.models.usage import UsageRecord, DailyUsageSummary

__all__ = [
    "Base",
    "User",
    "UserRole",
    "DEFAULT_QUOTAS",
    "Guest",
    "Trip",
    "Conversation",
    "Message",
    "ActivationCode",
    "CodeType",
    "UsageRecord",
    "DailyUsageSummary",
]
