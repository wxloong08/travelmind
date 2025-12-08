# ============================================================
# 修复 src/api/routes.py 中的 chat_stream 端点
# ============================================================
# 
# 找到 chat_stream 函数，将其替换为以下代码：

@router.post(
    "/chat/stream",
    tags=["Chat"],
    summary="流式对话",
)
async def chat_stream(request: ChatRequest):
    """
    流式返回对话结果

    使用 Server-Sent Events (SSE) 格式
    """
    import json
    import traceback  # 添加这行导入

    async def generate():
        try:
            logger.info("Stream started", session_id=request.session_id, message=request.message[:100])
            
            async for event in stream_travel_agent(
                user_input=request.message,
                session_id=request.session_id,
            ):
                event_type = event.get("type", "unknown")
                logger.debug("Stream event", event_type=event_type)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            # 添加详细的错误日志 - 这是关键修复
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            logger.error(
                "Stream error occurred",
                error=error_msg,
                error_type=type(e).__name__,
                traceback=error_traceback,
                session_id=request.session_id,
                message=request.message[:100],
            )
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
        finally:
            logger.info("Stream completed", session_id=request.session_id)
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )