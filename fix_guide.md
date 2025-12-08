# TravelMind 流式响应错误诊断与修复指南

## 问题现象

1. 意图分析成功执行（Langfuse Trace 显示 task_type: "travel_planning"）
2. HTTP 请求返回 200 OK
3. 前端显示错误消息："抱歉，出了点问题，请重试。"
4. 后端日志只有一个 warning（Page fetch failed 403）

## 问题根因

工作流在执行过程中（research 或 planning 节点）发生了未记录的异常：

```
understand_intent (成功) -> research (可能出错) -> planning (可能出错) -> respond
```

异常被 `routes.py` 的 `generate()` 函数捕获后发送为 `{'error': str(e)}`，
前端检测到 `event.error` 后显示错误消息。

## 诊断步骤

### 步骤 1：应用日志增强补丁

#### 1.1 修改 src/api/routes.py

在文件顶部添加：
```python
import traceback
```

找到 `chat_stream` 函数，修改 `generate()` 内的异常处理：

```python
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
        # 关键修复：添加详细的错误日志
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        logger.error(
            "Stream error occurred",
            error=error_msg,
            error_type=type(e).__name__,
            traceback=error_traceback,
            session_id=request.session_id,
        )
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
    finally:
        logger.info("Stream completed", session_id=request.session_id)
        yield "data: [DONE]\n\n"
```

#### 1.2 修改 src/graphs/travel_graph.py

在 `stream_travel_agent` 函数开头添加：
```python
import traceback
```

在工作流执行周围添加 try-except：

```python
try:
    async for event in travel_graph.astream(state_with_message, config=config):
        for node_name, node_output in event.items():
            logger.info("Stream node executed", node=node_name)  # 改为 info 级别
            # ... 原有代码 ...
            
except Exception as e:
    logger.error(
        "Workflow execution failed",
        error=str(e),
        error_type=type(e).__name__,
        traceback=traceback.format_exc(),
        session_id=actual_session_id,
    )
    raise
```

### 步骤 2：重新测试并查看日志

应用补丁后，重新发送请求：
```
帮我规划北京4天3晚的亲子游，想去环球影城
```

查看后端日志，应该能看到类似以下输出：

```
INFO: Stream started session_id=xxx message="帮我规划北京4天3晚的亲子游..."
INFO: Stream node executed node="understand_intent"
INFO: Stream node executed node="research"
ERROR: Workflow execution failed error="xxx" traceback="..."
ERROR: Stream error occurred error="xxx" traceback="..."
INFO: Stream completed session_id=xxx
```

### 步骤 3：根据错误信息修复

常见错误及修复：

#### 错误 1：JSON 解析错误
```
json.JSONDecodeError: Expecting value: line 1 column 1
```
**原因**：LLM 返回的内容不是有效 JSON
**修复**：在 `planning_node` 中添加更健壮的 JSON 解析

#### 错误 2：KeyError
```
KeyError: 'results'
```
**原因**：API 返回的数据结构与预期不符
**修复**：使用 `.get()` 方法安全访问字典键

#### 错误 3：httpx 超时
```
httpx.ReadTimeout: timed out
```
**原因**：外部 API 请求超时
**修复**：增加超时时间或添加重试逻辑

## 可能的根本原因

基于日志分析，最可能的原因是：

1. **博查搜索 API 返回异常数据**
   - `_search_web` 函数返回 None 或格式错误的数据
   - 检查 `src/tools/definitions.py` 中的 `web_search` 工具

2. **planning_node JSON 解析失败**
   - LLM 返回的规划内容不是有效 JSON
   - 检查 `planning_node` 中的 `json.loads()` 调用

3. **LangGraph 状态传递问题**
   - 状态在节点之间传递时出现类型错误
   - 检查 `AgentState` 的类型定义

## 快速修复建议

如果暂时无法定位具体问题，可以在 `research_node` 和 `planning_node` 中添加全局异常处理：

```python
async def research_node(state: AgentState) -> dict[str, Any]:
    try:
        # 原有代码
        ...
    except Exception as e:
        logger.error("research_node failed", error=str(e), traceback=traceback.format_exc())
        # 返回安全的默认值，让工作流继续
        return {
            "next_action": "respond",
            "updated_at": datetime.now().isoformat(),
        }
```

这样即使 research 失败，工作流也能继续到 respond 节点，向用户返回一个友好的错误提示。

## 联系支持

如果以上步骤无法解决问题，请提供：
1. 完整的后端日志（应用补丁后）
2. 具体的错误堆栈信息
3. 请求的完整内容