"""
Langfuse 可观测性集成

提供 LLM 调用追踪、成本分析等功能

使用 Langfuse SDK v2 (兼容自托管 Langfuse v2.x)
"""

from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger()


# ============================================================
# Langfuse SDK 初始化
# ============================================================

LANGFUSE_AVAILABLE = False
_langfuse_client = None

def _init_langfuse():
    """初始化 Langfuse 客户端"""
    global LANGFUSE_AVAILABLE, _langfuse_client
    
    if not settings.langfuse_enabled:
        logger.info("Langfuse not enabled (missing configuration)")
        return
    
    try:
        from langfuse import Langfuse
        
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        
        LANGFUSE_AVAILABLE = True
        logger.info(
            "Langfuse SDK initialized successfully",
            host=settings.langfuse_host,
        )
        
    except ImportError as e:
        logger.warning("Langfuse SDK not installed", error=str(e))
    except Exception as e:
        logger.error("Failed to initialize Langfuse", error=str(e), error_type=type(e).__name__)


# 模块加载时初始化
_init_langfuse()


# ============================================================
# 公共 API
# ============================================================

def get_langfuse_client():
    """获取 Langfuse 客户端"""
    return _langfuse_client


def log_llm_call(
    model: str,
    input_messages: list[dict[str, Any]],
    output: str,
    usage: dict[str, int] | None = None,
    duration_ms: float | None = None,
    session_id: str | None = None,
):
    """
    记录 LLM 调用到 Langfuse
    
    Args:
        model: 模型名称
        input_messages: 输入消息列表
        output: 输出内容
        usage: token 使用量 {"prompt_tokens": x, "completion_tokens": y, "total_tokens": z}
        duration_ms: 调用耗时（毫秒）
        session_id: 会话 ID
    """
    if not LANGFUSE_AVAILABLE or not _langfuse_client:
        logger.debug("Langfuse not available, skipping log")
        return

    try:
        # 提取第一条用户消息作为 trace 的 input
        trace_input = None
        for msg in input_messages:
            if msg.get("role") == "user":
                trace_input = msg.get("content", "")[:500]  # 截断避免太长
                break
        
        # 截断 output 用于 trace 显示
        trace_output = output[:500] if output else None
        
        # 创建 trace（带 input/output 摘要）
        trace = _langfuse_client.trace(
            name="travelmind-chat",
            session_id=session_id,
            input=trace_input,
            output=trace_output,
            metadata={
                "duration_ms": duration_ms,
            },
        )
        
        # 构建 usage 对象（Langfuse v2 格式）
        langfuse_usage = None
        if usage:
            langfuse_usage = {
                "input": usage.get("prompt_tokens"),
                "output": usage.get("completion_tokens"),
                "total": usage.get("total_tokens"),
                "unit": "TOKENS",
            }
        
        # 在 trace 下创建 generation（完整数据）
        trace.generation(
            name="llm-generation",
            model=model,
            input=input_messages,
            output=output,
            usage=langfuse_usage,
            metadata={
                "provider": "dashscope",
            },
        )
        
        # 确保数据发送到服务器
        _langfuse_client.flush()
        
        logger.info(
            "LLM call logged to Langfuse",
            model=model,
            session_id=session_id,
            has_usage=bool(usage),
        )
        
    except Exception as e:
        logger.error(
            "Failed to log to Langfuse",
            error=str(e),
            error_type=type(e).__name__,
        )


def flush():
    """确保所有数据发送到 Langfuse"""
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as e:
            logger.error("Failed to flush Langfuse", error=str(e))
