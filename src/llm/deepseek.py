"""
DeepSeek LLM Provider

用于独立评分的 LLM Provider，使用 DeepSeek API（OpenAI 兼容）
文档: https://platform.deepseek.com/api-docs
"""

import time
from typing import Any

import structlog
from openai import AsyncOpenAI

from src.config import settings
from src.llm.base import (
    LLMProvider,
    LLMProviderFactory,
    LLMResponse,
    Message,
    ToolCall,
)

logger = structlog.get_logger()


def _log_to_langfuse(
    model: str,
    messages: list[dict],
    output: str,
    usage: dict | None,
    duration_ms: float,
    session_id: str | None = None,
):
    """记录到 Langfuse（如果已配置）"""
    try:
        from src.core.observability import log_llm_call
        log_llm_call(
            model=model,
            input_messages=messages,
            output=output,
            usage=usage,
            duration_ms=duration_ms,
            session_id=session_id,
        )
    except Exception as e:
        logger.debug("Langfuse logging failed", error=str(e))


@LLMProviderFactory.register("deepseek")
class DeepSeekProvider(LLMProvider):
    """
    DeepSeek API Provider
    
    使用 OpenAI 兼容接口，专用于评分任务
    """
    
    # DeepSeek API 基础 URL
    BASE_URL = "https://api.deepseek.com"
    
    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 2048,
        api_key: str | None = None,
    ):
        # 使用配置或默认值
        model = model or getattr(settings, "deepseek_model", "deepseek-chat")
        temperature = temperature if temperature is not None else getattr(settings, "deepseek_temperature", 0.3)
        
        super().__init__(model, temperature, max_tokens)
        
        self.api_key = api_key or getattr(settings, "deepseek_api_key", "")
        
        if not self.api_key:
            raise ValueError(
                "DeepSeek API key is required. "
                "Set DEEPSEEK_API_KEY environment variable."
            )
        
        # 创建 OpenAI 兼容客户端
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL,
        )
    
    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """转换消息格式"""
        converted = []
        for msg in messages:
            converted_msg: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.name:
                converted_msg["name"] = msg.name
            if msg.tool_call_id:
                converted_msg["tool_call_id"] = msg.tool_call_id
            converted.append(converted_msg)
        return converted
    
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> LLMResponse:
        """发送聊天请求"""
        logger.debug(
            "DeepSeek chat request",
            model=self.model,
            message_count=len(messages),
            has_tools=bool(tools),
        )
        
        start_time = time.time()
        
        # 构建请求参数
        converted_messages = self._convert_messages(messages)
        request_params: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # DeepSeek 支持工具调用
        if tools:
            request_params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.get("name", t.get("function", {}).get("name")),
                        "description": t.get("description", t.get("function", {}).get("description")),
                        "parameters": t.get("parameters", t.get("function", {}).get("parameters", {})),
                    },
                }
                for t in tools
            ]
            if tool_choice:
                request_params["tool_choice"] = tool_choice
        
        # 调用 API
        try:
            response = await self._client.chat.completions.create(**request_params)
        except Exception as e:
            logger.error("DeepSeek API error", error=str(e))
            raise
        
        duration_ms = (time.time() - start_time) * 1000
        
        # 解析响应
        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else ""
        finish_reason = choice.finish_reason if choice else None
        
        # 解析工具调用
        tool_calls = None
        if choice and choice.message and choice.message.tool_calls:
            tool_calls = []
            for tc in choice.message.tool_calls:
                import json
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        # 使用量统计
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        # 记录到 Langfuse
        _log_to_langfuse(
            model=self.model,
            messages=converted_messages,
            output=content or "",
            usage=usage,
            duration_ms=duration_ms,
            session_id=session_id,
        )
        
        logger.info(
            "DeepSeek chat response",
            model=self.model,
            has_content=bool(content),
            tool_calls_count=len(tool_calls) if tool_calls else 0,
            usage=usage,
            duration_ms=round(duration_ms, 2),
        )
        
        return LLMResponse(
            content=content or "",
            tool_calls=tool_calls,
            usage=usage,
            model=self.model,
            finish_reason=finish_reason,
        )
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        生成文本嵌入向量
        
        注意：DeepSeek 目前不提供 Embedding API，
        如需 Embedding 请使用 Qwen 的 text-embedding-v3
        """
        raise NotImplementedError(
            "DeepSeek does not provide Embedding API. "
            "Use QwenProvider.embed() instead."
        )


def get_deepseek_llm(
    model: str | None = None,
    temperature: float | None = None,
) -> DeepSeekProvider:
    """
    获取 DeepSeek Provider 实例
    
    便捷函数，用于评分任务
    """
    return DeepSeekProvider(
        model=model,
        temperature=temperature,
    )
