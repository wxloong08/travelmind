# ADR-001: AI Agent 框架选型

| 属性 | 值 |
|------|-----|
| **状态** | 🟢 Accepted |
| **决策者** | TravelMind Team |
| **日期** | 2024-12 |

## 上下文 (Context)

TravelMind 需要一个 AI Agent 框架来实现：

1. **多步骤工作流**: 旅游规划涉及意图理解 → 信息收集 → 行程规划 → 响应生成
2. **工具调用**: 集成高德地图、博查搜索等外部 API
3. **状态管理**: 跨多轮对话保持上下文
4. **可观测性**: 追踪 Agent 执行过程，便于调试

## 考虑的备选方案

### 方案 A: LangGraph (LangChain 生态)

- **优势**: 基于图的状态机，精确控制分支和循环；与 LangChain 生态深度集成；支持检查点持久化；企业级应用案例丰富
- **劣势**: 学习曲线陡峭；抽象层次多

### 方案 B: CrewAI

- **优势**: 基于角色的多 Agent 协作；学习曲线平缓；官方基准比 LangGraph 快 5.76 倍
- **劣势**: 复杂工作流控制能力不如 LangGraph

### 方案 C: AutoGen (Microsoft)

- **优势**: Human-in-the-loop 支持好
- **劣势**: 主要面向研究场景

## 决策 (Decision)

**选择 LangGraph 作为 Agent 框架。**

核心理由：

1. **企业级成熟度**: Replit、Uber、Klarna 等公司生产环境验证
2. **工作流控制**: 旅游规划需要复杂的条件分支和循环
3. **状态持久化**: 内置 checkpointer 支持会话持久化
4. **可观测性**: 与 LangSmith/Langfuse 深度集成

## 后果 (Consequences)

### 正面影响

- ✅ 工作流定义清晰，便于维护和扩展
- ✅ 状态管理规范，多轮对话稳定
- ✅ 调试追踪能力强

### 负面影响

- ⚠️ 学习成本较高
- ⚠️ 简单场景可能过度设计

## 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph vs CrewAI 对比](https://blog.langchain.dev/)
