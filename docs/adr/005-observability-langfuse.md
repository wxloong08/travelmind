# ADR-005: 选择 Langfuse 作为可观测性方案

| 属性 | 值 |
|------|-----|
| **状态** | 🟢 Accepted |
| **决策者** | [Your Name] |
| **日期** | 2024-12 |
| **相关 ADR** | ADR-001 (Agent 框架) |

## 上下文 (Context)

LLM 应用的可观测性与传统 Web 应用有显著差异，需要追踪：

| 维度 | 传统应用 | LLM 应用 |
|------|---------|---------|
| 请求追踪 | HTTP 请求/响应 | 多轮 LLM 调用链 |
| 成本监控 | 服务器资源 | **Token 消耗** |
| 延迟分析 | 接口响应时间 | 各节点执行时间 |
| 质量评估 | 功能正确性 | **输出质量、幻觉检测** |
| 调试信息 | 日志、堆栈 | **Prompt、中间推理过程** |

TravelMind 基于 LangGraph 构建，一次用户请求可能涉及：
- 5-10 次 LLM 调用
- 3-5 次外部 API 调用
- 最多 3 次评估-优化迭代

**需求**：
1. 追踪完整的 Agent 执行链路
2. 监控每个节点的 Token 消耗和耗时
3. 记录 Prompt 和响应，便于调试
4. 支持自托管，数据不出境
5. 成本可控（个人项目）

## 考虑的备选方案 (Alternatives Considered)

### 方案 A: Langfuse

**概述**：开源 LLM 可观测性平台，专为 LangChain/LangGraph 设计。

**优势**：
- 完全开源 (Apache 2.0)，可自托管
- 基于 OpenTelemetry，框架无关
- 与 LangChain/LangGraph 深度集成
- 详细的 Trace 视图：Prompt、Completion、Token 计数、延迟
- 成本分析仪表盘
- 云服务 Hobby 层免费（5000 traces/月）

**劣势**：
- 自托管需要额外运维
- 部分高级功能（评估、实验）仅限付费版

**定价**：
| 方案 | 价格 | Traces |
|------|------|--------|
| 自托管 | 免费 | 无限制 |
| Hobby | 免费 | 5000/月 |
| Pro | $29/月起 | 50000/月 |

### 方案 B: LangSmith (LangChain 官方)

**概述**：LangChain 官方的追踪和评估平台。

**优势**：
- 与 LangChain/LangGraph 无缝集成
- 功能完善：追踪、评估、Playground、Hub
- 团队协作功能强

**劣势**：
- **不开源**，无法自托管
- 免费层限制严格（5000 traces/月）
- 数据存储在美国，合规风险
- 付费版 $39/seat/月起

### 方案 C: OpenTelemetry + Jaeger/Grafana

**概述**：通用的分布式追踪方案。

**优势**：
- 行业标准，生态完善
- 完全开源，自托管灵活
- 与现有基础设施集成

**劣势**：
- 不是为 LLM 应用设计，缺少 Token 计数、Prompt 记录等特性
- 需要大量自定义开发
- 学习和配置成本高

### 方案 D: 自建日志系统

**概述**：使用 Python logging + ELK/Loki。

**优势**：
- 完全控制
- 无额外依赖

**劣势**：
- 开发成本极高
- 缺乏可视化
- 不适合个人项目

## 决策 (Decision)

**选择 Langfuse 作为可观测性方案。**

**部署策略**：
1. **开发阶段**：使用 Langfuse Cloud 免费层（5000 traces/月）
2. **生产阶段**：Docker 自托管（数据合规）

核心理由：

1. **开源可自托管**：数据留在国内，符合合规要求
2. **LLM 原生**：Token 计数、成本分析、Prompt 记录开箱即用
3. **LangGraph 深度集成**：一行代码启用追踪
4. **成本友好**：个人项目使用免费层或自托管

## 后果 (Consequences)

### 正面影响

- ✅ 完整的 Agent 执行链路可视化
- ✅ Token 消耗和成本一目了然
- ✅ Prompt 调试效率大幅提升
- ✅ 面试展示时可直接打开 Dashboard 演示

### 负面影响

- ⚠️ 自托管需要 Docker 环境
- ⚠️ 云服务免费层有限额

## 实现示例

```python
# src/core/observability.py
import os
from langfuse.callback import CallbackHandler

def get_langfuse_handler(session_id: str | None = None) -> CallbackHandler:
    """获取 Langfuse 回调处理器"""
    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        session_id=session_id,
        # 可选：添加用户标识
        user_id=os.getenv("USER_ID"),
    )

# src/graphs/travel_graph.py
from src.core.observability import get_langfuse_handler

async def run_with_tracing(user_input: str, session_id: str):
    """带追踪的执行"""
    handler = get_langfuse_handler(session_id)
    
    config = {
        "configurable": {"thread_id": session_id},
        "callbacks": [handler]  # 注入 Langfuse 回调
    }
    
    result = await travel_graph.ainvoke(
        {"user_input": user_input},
        config=config
    )
    
    # 手动刷新确保数据上传
    handler.flush()
    
    return result
```

### 自托管 Docker Compose

```yaml
# docker-compose.langfuse.yml
version: "3.8"

services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/langfuse
      - NEXTAUTH_SECRET=your-secret-key
      - NEXTAUTH_URL=http://localhost:3000
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=langfuse
    volumes:
      - langfuse_data:/var/lib/postgresql/data

volumes:
  langfuse_data:
```

## 参考资料

- [Langfuse 官方文档](https://langfuse.com/docs)
- [Langfuse + LangGraph 集成指南](https://langfuse.com/docs/integrations/langchain)
- [LLM 可观测性最佳实践](https://langfuse.com/blog)