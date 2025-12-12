# ADR-004: 选择 FastAPI 作为 Web 框架

| 属性 | 值 |
|------|-----|
| **状态** | 🟢 Accepted |
| **决策者** | [Your Name] |
| **日期** | 2024-12 |
| **相关 ADR** | ADR-001 (Agent 框架) |

## 上下文 (Context)

TravelMind 需要一个 Web 框架来：

1. 暴露 RESTful API 供前端调用
2. 处理 WebSocket 连接实现流式响应
3. 集成 LangGraph Agent 工作流
4. 提供自动生成的 API 文档

技术约束：
- 必须是 Python 框架（与 LangGraph 生态统一）
- 需要支持异步（Agent 调用涉及大量 I/O 等待）
- 便于本地开发和容器化部署

## 考虑的备选方案 (Alternatives Considered)

### 方案 A: FastAPI

**概述**：现代、高性能的 Python Web 框架，基于 Starlette 和 Pydantic。

**优势**：
- 原生异步支持 (`async/await`)
- 自动生成 OpenAPI (Swagger) 文档
- Pydantic 数据验证，类型安全
- 性能与 Node.js 和 Go 相当
- Netflix、Microsoft、Uber 等公司使用
- 与 LangChain/LangGraph 集成示例丰富
- 学习曲线平缓

**劣势**：
- 相对年轻（2018 年发布）
- 生态不如 Django 完善

### 方案 B: Django + Django REST Framework

**优势**：
- 成熟稳定，15+ 年历史
- "batteries included"，功能全面
- ORM 强大
- 社区庞大

**劣势**：
- 异步支持不够原生（Django 4.1 开始支持但不完善）
- 配置复杂，对于 API-only 项目过重
- 与 LangGraph 集成示例少

### 方案 C: Flask

**优势**：
- 轻量灵活
- 学习成本低
- 社区成熟

**劣势**：
- 原生不支持异步，需要 `flask[async]` 扩展
- 无内置数据验证
- 无自动 API 文档生成

### 方案 D: LangServe (LangChain 官方)

**概述**：LangChain 官方的部署方案，基于 FastAPI。

**优势**：
- 与 LangChain/LangGraph 无缝集成
- 自动生成链的 API 端点
- 内置 Playground UI

**劣势**：
- 灵活性受限，难以自定义路由逻辑
- 与业务代码耦合度高
- 更适合快速原型，不适合企业级项目

## 决策 (Decision)

**选择 FastAPI 作为 Web 框架。**

核心理由：

1. **异步原生**：LangGraph 节点涉及大量 LLM API 调用和外部服务请求，异步处理可显著提升并发性能。

2. **类型安全**：Pydantic v2 的数据验证与 LangGraph 的 `TypedDict` 状态定义天然契合。

3. **API 文档自动化**：Swagger UI 开箱即用，便于前端联调和面试演示。

4. **主流选择**：AI 应用领域 FastAPI 已成为事实标准，示例和教程丰富。

## 后果 (Consequences)

### 正面影响

- ✅ 异步性能优异，适合 I/O 密集型 Agent 应用
- ✅ 自动 API 文档，提升开发效率
- ✅ 类型安全，减少运行时错误
- ✅ 与 Langfuse 等可观测性工具集成良好

### 负面影响

- ⚠️ 无内置 ORM，需要额外引入 SQLAlchemy 或 Tortoise
- ⚠️ 认证授权需手动实现或引入 `fastapi-users`

## 实现示例

```python
# src/api/routes.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.graphs.travel_graph import travel_graph

app = FastAPI(
    title="TravelMind API",
    description="智能旅游规划与长租房助手",
    version="0.1.0"
)

class PlanRequest(BaseModel):
    user_input: str
    session_id: str | None = None

class PlanResponse(BaseModel):
    session_id: str
    result: dict
    iterations: int

@app.post("/api/v1/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """创建旅游/租房规划"""
    config = {"configurable": {"thread_id": request.session_id or uuid4().hex}}
    
    result = await travel_graph.ainvoke(
        {"user_input": request.user_input},
        config=config
    )
    
    return PlanResponse(
        session_id=config["configurable"]["thread_id"],
        result=result["final_report"],
        iterations=result["iteration_count"]
    )

@app.post("/api/v1/plan/stream")
async def create_plan_stream(request: PlanRequest):
    """流式返回规划过程"""
    async def event_generator():
        config = {"configurable": {"thread_id": request.session_id or uuid4().hex}}
        async for event in travel_graph.astream_events(
            {"user_input": request.user_input},
            config=config,
            version="v2"
        ):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangGraph + FastAPI 集成示例](https://python.useinstructor.com/concepts/fastapi/)
- [FastAPI vs Django vs Flask 性能对比](https://www.techempower.com/benchmarks/)
