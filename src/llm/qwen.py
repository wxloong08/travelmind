"""
通义千问 (Qwen) LLM Provider

基于阿里云百炼平台 DashScope SDK
文档: https://help.aliyun.com/zh/dashscope/
"""

import json
import time
from typing import Any

import structlog
from dashscope import Generation, TextEmbedding
from dashscope.api_entities.dashscope_response import GenerationResponse

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
    tool_calls: list | None = None,
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


@LLMProviderFactory.register("qwen")
class QwenProvider(LLMProvider):
    """通义千问 Provider 实现"""

    def __init__(
        self,
        model: str = "qwen-turbo",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: str | None = None,
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or settings.dashscope_api_key

        if not self.api_key:
            raise ValueError(
                "DashScope API key is required. "
                "Set DASHSCOPE_API_KEY environment variable."
            )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """转换消息格式为 DashScope 格式"""
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

    def _convert_tools(
        self, tools: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]] | None:
        """转换工具定义格式"""
        if not tools:
            return None

        # DashScope 使用与 OpenAI 兼容的工具格式
        converted = []
        for tool in tools:
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", tool.get("function", {}).get("name")),
                        "description": tool.get(
                            "description", tool.get("function", {}).get("description")
                        ),
                        "parameters": tool.get(
                            "parameters", tool.get("function", {}).get("parameters", {})
                        ),
                    },
                }
            )
        return converted

    def _parse_response(self, response: GenerationResponse) -> LLMResponse:
        """解析 DashScope 响应"""
        if response.status_code != 200:
            logger.error(
                "Qwen API error",
                status_code=response.status_code,
                message=response.message,
            )
            raise Exception(f"Qwen API error: {response.message}")

        output = response.output
        
        # 处理 output 可能是字典或对象的情况
        if isinstance(output, dict):
            choices = output.get("choices", [])
        else:
            choices = getattr(output, "choices", []) or []

        if not choices:
            return LLMResponse(content="")

        choice = choices[0]
        
        # 处理 choice 可能是字典或对象的情况
        if isinstance(choice, dict):
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason")
        else:
            message = getattr(choice, "message", {}) or {}
            finish_reason = getattr(choice, "finish_reason", None)

        # 获取 content
        if isinstance(message, dict):
            content = message.get("content", "") or ""
        else:
            content = getattr(message, "content", "") or ""

        # 解析工具调用
        tool_calls = None
        try:
            # 获取 raw tool_calls - 使用最安全的方式
            raw_tool_calls = None
            if isinstance(message, dict):
                raw_tool_calls = message.get("tool_calls")
            else:
                # 对于对象，先检查是否有这个属性
                try:
                    if hasattr(message, "tool_calls"):
                        raw_tool_calls = message.tool_calls
                except (KeyError, AttributeError):
                    # DashScope SDK 可能在 __getattr__ 中抛出 KeyError
                    raw_tool_calls = None
                    
                # 如果上面失败，尝试访问 __dict__
                if raw_tool_calls is None:
                    try:
                        msg_dict = vars(message) if hasattr(message, "__dict__") else {}
                        raw_tool_calls = msg_dict.get("tool_calls")
                    except Exception:
                        pass

            if raw_tool_calls:
                tool_calls = []
                for tc in raw_tool_calls:
                    # 处理每个 tool_call
                    if isinstance(tc, dict):
                        func = tc.get("function", {})
                        call_id = tc.get("id", f"call_{len(tool_calls)}")
                        name = func.get("name", "unknown") if isinstance(func, dict) else "unknown"
                        args_raw = func.get("arguments", "{}") if isinstance(func, dict) else "{}"
                    else:
                        call_id = getattr(tc, "id", f"call_{len(tool_calls)}")
                        func = getattr(tc, "function", None)
                        if func:
                            name = getattr(func, "name", "unknown") if not isinstance(func, dict) else func.get("name", "unknown")
                            args_raw = getattr(func, "arguments", "{}") if not isinstance(func, dict) else func.get("arguments", "{}")
                        else:
                            name = "unknown"
                            args_raw = "{}"

                    # 解析 arguments
                    if isinstance(args_raw, str):
                        try:
                            args = json.loads(args_raw)
                        except json.JSONDecodeError:
                            args = {}
                    elif isinstance(args_raw, dict):
                        args = args_raw
                    else:
                        args = {}

                    tool_calls.append(
                        ToolCall(
                            id=call_id,
                            name=name,
                            arguments=args,
                        )
                    )
                    
                logger.debug("Parsed tool calls", count=len(tool_calls))
                
        except Exception as e:
            logger.warning("Failed to parse tool_calls", error=str(e), error_type=type(e).__name__)
            tool_calls = None

        # 使用量统计
        usage = None
        try:
            resp_usage = response.usage
            if resp_usage:
                if isinstance(resp_usage, dict):
                    usage = {
                        "prompt_tokens": resp_usage.get("input_tokens", 0),
                        "completion_tokens": resp_usage.get("output_tokens", 0),
                        "total_tokens": resp_usage.get("total_tokens", 0),
                    }
                else:
                    usage = {
                        "prompt_tokens": getattr(resp_usage, "input_tokens", 0),
                        "completion_tokens": getattr(resp_usage, "output_tokens", 0),
                        "total_tokens": getattr(resp_usage, "total_tokens", 0),
                    }
        except Exception:
            pass

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=self.model,
            finish_reason=finish_reason,
        )

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> LLMResponse:
        """发送聊天请求"""
        logger.debug(
            "Qwen chat request",
            model=self.model,
            message_count=len(messages),
            has_tools=bool(tools),
        )

        # 记录开始时间
        start_time = time.time()

        # 构建请求参数
        converted_messages = self._convert_messages(messages)
        request_params: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "api_key": self.api_key,
            "result_format": "message",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # 添加工具
        if tools:
            request_params["tools"] = self._convert_tools(tools)
            if tool_choice:
                request_params["tool_choice"] = tool_choice

        # 调用 API
        response = Generation.call(**request_params)
        
        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000
        
        # 调试日志：查看原始响应结构
        logger.debug(
            "Qwen raw response",
            status_code=response.status_code,
            output_type=type(response.output).__name__,
            output_keys=list(response.output.keys()) if isinstance(response.output, dict) else dir(response.output),
        )

        result = self._parse_response(response)

        # 记录到 Langfuse
        _log_to_langfuse(
            model=self.model,
            messages=converted_messages,
            output=result.content,
            usage=result.usage,
            duration_ms=duration_ms,
            session_id=session_id,
            tool_calls=[{"name": tc.name, "args": tc.arguments} for tc in result.tool_calls] if result.tool_calls else None,
        )

        logger.info(
            "Qwen chat response",
            model=self.model,
            has_content=bool(result.content),
            tool_calls_count=len(result.tool_calls) if result.tool_calls else 0,
            usage=result.usage,
            duration_ms=round(duration_ms, 2),
        )

        return result

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """生成文本嵌入向量"""
        logger.debug("Qwen embedding request", text_count=len(texts))

        # DashScope Embedding API
        response = TextEmbedding.call(
            model=settings.embedding_model,
            input=texts,
            api_key=self.api_key,
        )

        if response.status_code != 200:
            logger.error(
                "Qwen embedding error",
                status_code=response.status_code,
                message=response.message,
            )
            raise Exception(f"Qwen embedding error: {response.message}")

        embeddings = [item["embedding"] for item in response.output["embeddings"]]

        logger.info(
            "Qwen embedding response",
            text_count=len(texts),
            dimension=len(embeddings[0]) if embeddings else 0,
        )

        return embeddings


def get_llm(
    model: str | None = None,
    temperature: float | None = None,
) -> QwenProvider:
    """
    获取 LLM Provider 实例

    便捷函数，使用默认配置创建 QwenProvider
    """
    return QwenProvider(
        model=model or settings.llm_model,
        temperature=temperature or settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
