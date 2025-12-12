# ADR-002: 选择通义千问作为主要 LLM

| 属性 | 值 |
|------|-----|
| **状态** | 🟢 Accepted |
| **决策者** | [Your Name] |
| **日期** | 2024-12 |
| **相关 ADR** | ADR-001 (Agent 框架) |

## 上下文 (Context)

TravelMind 需要一个 LLM 来驱动 Agent 的推理能力，包括：

- 意图解析和槽位填充
- 行程规划和方案生成
- 多维度评估和反思
- 自然语言总结输出

关键需求：

1. **中文能力**：面向中国市场，中文理解和生成质量是首要指标
2. **成本控制**：个人项目预算有限，月成本需控制在 ¥100 以内
3. **API 稳定性**：高可用，低延迟
4. **合规性**：数据存储在国内，符合中国法规
5. **工具调用**：支持 Function Calling / Tool Use

## 考虑的备选方案 (Alternatives Considered)

### 方案 A: 通义千问 (Qwen) - 阿里云百炼平台

**模型矩阵**：
| 模型 | 输入价格 | 输出价格 | 特点 |
|------|---------|---------|------|
| qwen-turbo | ¥2/1M tokens | ¥6/1M tokens | 速度最快 |
| qwen-plus | ¥2.4/1M tokens | ¥9.6/1M tokens | 能力均衡 |
| qwen-max | ¥20/1M tokens | ¥60/1M tokens | 最强推理 |
| qwen-long | ¥0.5/1M tokens | ¥2/1M tokens | 1000万长文本 |

**优势**：
- 全球排名第七，非推理类中国大模型第一
- 新用户首开免费领 1000 万 tokens
- 主流模型各限免 100 万 tokens
- API 稳定，阿里云基础设施保障
- 支持 Function Calling
- 数据合规，服务器在国内

**劣势**：
- qwen-max 价格较高
- 复杂推理能力略逊于 GPT-4

### 方案 B: DeepSeek

**定价**：
| 模型 | 输入价格 | 输出价格 | 特点 |
|------|---------|---------|------|
| DeepSeek-V3 | ¥0.5-2/1M tokens | ¥8/1M tokens | 通用能力 |
| DeepSeek-R1 | ¥1-4/1M tokens | ¥16/1M tokens | 强推理 |

**优势**：
- 价格极具竞争力
- R1 推理模型数学和代码能力强
- 完全开源，可本地部署
- 错峰时段 (00:30-08:30) 价格降至 25-50%

**劣势**：
- 高峰期服务器可能不稳定（用户反馈）
- API 服务相对年轻，稳定性待验证
- 中文能力略逊于通义千问

### 方案 C: 智谱 GLM-4

**定价**：GLM-4-Plus 约 ¥100/1M tokens

**优势**：
- 多模态能力强
- 学术背景深厚（清华系）

**劣势**：
- 价格较高
- API 易用性不如阿里云

### 方案 D: OpenAI GPT-4 / Claude

**优势**：
- 全球顶级能力

**劣势**：
- 需要翻墙或代理
- 数据出境合规风险
- 价格昂贵（GPT-4 约 $30/1M tokens）
- 个人项目不现实

### 方案 E: 月之暗面 Kimi (Moonshot)

**优势**：
- 长文本能力强
- 代码能力优秀

**劣势**：
- API 开放程度有限
- 定价不够透明

## 决策 (Decision)

**选择通义千问 (Qwen) 作为主要 LLM，DeepSeek 作为备选。**

具体配置：

```python
# 主模型配置
LLM_CONFIG = {
    "primary": {
        "provider": "qwen",
        "model": "qwen-turbo",  # 日常使用，成本低
        "fallback_model": "qwen-plus",  # 复杂任务升级
    },
    "secondary": {
        "provider": "deepseek", 
        "model": "deepseek-chat",  # 备选方案
    }
}
```

**成本估算**：
- 假设每次完整规划消耗约 5000 tokens（输入+输出）
- 日均 20 次调用 = 10 万 tokens/天 = 300 万 tokens/月
- qwen-turbo 成本：300 万 × (¥2 + ¥6) / 100 万 ≈ ¥24/月
- 加上免费额度，实际成本可能为 **¥0-30/月**

## 后果 (Consequences)

### 正面影响

- ✅ 中文能力出色，用户体验好
- ✅ 成本极低，个人项目完全可承受
- ✅ API 稳定，阿里云 SLA 保障
- ✅ 数据合规，无出境风险
- ✅ 支持 Function Calling，与 LangGraph 工具调用兼容

### 负面影响

- ⚠️ 复杂推理能力不如 GPT-4/Claude
- ⚠️ 绑定阿里云生态

### 缓解措施

- 对于需要强推理的评估节点，可升级到 qwen-plus 或 qwen-max
- 实现 LLM Provider 抽象层，支持快速切换到其他模型
- 关键提示词进行充分测试和优化

## 实现示例

```python
# src/llm/base.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> str:
        pass

# src/llm/qwen.py
from dashscope import Generation

class QwenProvider(LLMProvider):
    def __init__(self, model: str = "qwen-turbo"):
        self.model = model
    
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> str:
        response = Generation.call(
            model=self.model,
            messages=messages,
            tools=tools,
            result_format="message"
        )
        return response.output.choices[0].message.content
```

## 参考资料

- [通义千问 API 文档](https://help.aliyun.com/zh/dashscope/)
- [DeepSeek API 文档](https://platform.deepseek.com/docs)
- [中国大模型能力排行榜](https://opencompass.org.cn/)
