"""
Redis 会话存储

用于 LangGraph 会话状态持久化
生产环境必需，确保服务重启后会话不丢失
"""

import json
from datetime import datetime, timedelta
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger()

# Redis 客户端（延迟初始化）
_redis_client = None


def get_redis_client():
    """获取 Redis 客户端"""
    global _redis_client

    if _redis_client is None:
        if not settings.redis_url:
            logger.warning("Redis URL not configured, session persistence disabled")
            return None

        try:
            import redis

            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 测试连接
            _redis_client.ping()
            logger.info("Redis connected", url=settings.redis_url.split("@")[-1])
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            return None

    return _redis_client


class RedisSessionStore:
    """
    Redis 会话存储

    用途：
    1. 存储多轮对话的会话状态
    2. 缓存 LLM 响应，减少重复调用
    3. 存储用户偏好设置
    """

    def __init__(self, prefix: str = "travelmind"):
        self.prefix = prefix
        self.client = get_redis_client()
        self.default_ttl = timedelta(hours=24)  # 会话默认保存 24 小时

    def _key(self, key_type: str, key_id: str) -> str:
        """生成 Redis key"""
        return f"{self.prefix}:{key_type}:{key_id}"

    # ============================================================
    # 会话状态管理
    # ============================================================

    async def save_session(
        self,
        session_id: str,
        state: dict[str, Any],
        ttl: timedelta | None = None,
    ) -> bool:
        """
        保存会话状态

        Args:
            session_id: 会话 ID
            state: 会话状态字典
            ttl: 过期时间

        Returns:
            是否保存成功
        """
        if not self.client:
            return False

        try:
            key = self._key("session", session_id)
            # 序列化状态（处理不可序列化的对象）
            serialized = self._serialize_state(state)
            self.client.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(serialized, ensure_ascii=False),
            )
            logger.debug("Session saved", session_id=session_id)
            return True
        except Exception as e:
            logger.error("Failed to save session", session_id=session_id, error=str(e))
            return False

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
        """
        加载会话状态

        Args:
            session_id: 会话 ID

        Returns:
            会话状态或 None
        """
        if not self.client:
            return None

        try:
            key = self._key("session", session_id)
            data = self.client.get(key)
            if data:
                logger.debug("Session loaded", session_id=session_id)
                return json.loads(data)
            return None
        except Exception as e:
            logger.error("Failed to load session", session_id=session_id, error=str(e))
            return None

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if not self.client:
            return False

        try:
            key = self._key("session", session_id)
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error("Failed to delete session", error=str(e))
            return False

    async def extend_session(self, session_id: str, ttl: timedelta | None = None) -> bool:
        """延长会话过期时间"""
        if not self.client:
            return False

        try:
            key = self._key("session", session_id)
            self.client.expire(key, ttl or self.default_ttl)
            return True
        except Exception as e:
            logger.error("Failed to extend session", error=str(e))
            return False

    # ============================================================
    # LLM 响应缓存
    # ============================================================

    async def cache_llm_response(
        self,
        cache_key: str,
        response: str,
        ttl: timedelta = timedelta(hours=1),
    ) -> bool:
        """
        缓存 LLM 响应

        用于缓存相同问题的回答，减少 API 调用成本
        """
        if not self.client:
            return False

        try:
            key = self._key("llm_cache", cache_key)
            self.client.setex(key, ttl, response)
            return True
        except Exception as e:
            logger.error("Failed to cache LLM response", error=str(e))
            return False

    async def get_cached_response(self, cache_key: str) -> str | None:
        """获取缓存的 LLM 响应"""
        if not self.client:
            return None

        try:
            key = self._key("llm_cache", cache_key)
            return self.client.get(key)
        except Exception as e:
            logger.error("Failed to get cached response", error=str(e))
            return None

    # ============================================================
    # 用户偏好存储
    # ============================================================

    async def save_user_preference(
        self,
        user_id: str,
        preferences: dict[str, Any],
    ) -> bool:
        """保存用户偏好"""
        if not self.client:
            return False

        try:
            key = self._key("user_pref", user_id)
            self.client.set(key, json.dumps(preferences, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error("Failed to save user preference", error=str(e))
            return False

    async def get_user_preference(self, user_id: str) -> dict[str, Any] | None:
        """获取用户偏好"""
        if not self.client:
            return None

        try:
            key = self._key("user_pref", user_id)
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error("Failed to get user preference", error=str(e))
            return None

    # ============================================================
    # 辅助方法
    # ============================================================

    def _serialize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """序列化状态，处理不可 JSON 序列化的对象"""
        serialized = {}
        for key, value in state.items():
            if key == "messages":
                # 特殊处理 LangChain 消息对象
                serialized[key] = [
                    {
                        "type": type(msg).__name__,
                        "content": msg.content if hasattr(msg, "content") else str(msg),
                    }
                    for msg in value
                ]
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif hasattr(value, "__dict__"):
                serialized[key] = value.__dict__
            else:
                try:
                    json.dumps(value)
                    serialized[key] = value
                except (TypeError, ValueError):
                    serialized[key] = str(value)
        return serialized

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        if not self.client:
            return {"status": "disabled", "reason": "Redis not configured"}

        try:
            self.client.ping()
            info = self.client.info("memory")
            return {
                "status": "healthy",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": self.client.info("clients").get("connected_clients"),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# 全局实例
_session_store: RedisSessionStore | None = None


def get_session_store() -> RedisSessionStore:
    """获取会话存储单例"""
    global _session_store
    if _session_store is None:
        _session_store = RedisSessionStore()
    return _session_store
