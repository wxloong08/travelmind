"""
LLM Provider 抽象层

实现 Strategy Pattern，支持快速切换不同的 LLM 提供商
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Message:
    """消息数据类"""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    """工具调用数据类"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 响应数据类"""

    content: str
    tool_calls: list[ToolCall] | None = None
    usage: dict[str, int] | None = None
    model: str | None = None
    finish_reason: str | None = None


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> LLMResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具定义（OpenAI Function Calling 格式）
            tool_choice: 工具选择策略 ("auto", "none", 或指定工具)
            session_id: 会话 ID（用于追踪）

        Returns:
            LLMResponse: 包含回复内容和可能的工具调用
        """
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        生成文本嵌入向量

        Args:
            texts: 待嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        pass

    async def chat_with_retry(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """带重试的聊天请求"""
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
        )
        async def _chat() -> LLMResponse:
            return await self.chat(messages, tools)

        return await _chat()


class LLMProviderFactory:
    """LLM Provider 工厂类"""

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str) -> Any:
        """注册 Provider 装饰器"""

        def decorator(provider_cls: type[LLMProvider]) -> type[LLMProvider]:
            cls._providers[name] = provider_cls
            return provider_cls

        return decorator

    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> LLMProvider:
        """创建 Provider 实例"""
        if provider_name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {provider_name}. Available: {available}"
            )
        return cls._providers[provider_name](**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有已注册的 Provider"""
        return list(cls._providers.keys())
