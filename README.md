# 🧳 TravelMind

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AI 驱动的旅游规划助手** - 基于 LangGraph 的智能 Agent 应用

## ✨ 功能特性

- 🗺️ **智能旅游规划** - 根据偏好制定个性化旅游攻略
- 🏨 **景点/酒店推荐** - 实时搜索目的地 POI 信息
- 📅 **行程安排** - 合理规划每日行程，考虑距离与时间
- 🌤️ **天气查询** - 获取目的地实时天气和预报
- 🔍 **实时资讯** - 搜索最新旅游攻略和新闻
- 📊 **LLM 可观测性** - Langfuse 集成，追踪调用和成本

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                      FastAPI                            │
│                   (REST API Layer)                      │
├─────────────────────────────────────────────────────────┤
│                     LangGraph                           │
│              (Agent Workflow Engine)                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │Understand│→│Research │→│Planning │→│ Respond │    │
│  │  Intent │  │  Node   │  │  Node   │  │  Node   │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
├─────────────────────────────────────────────────────────┤
│                      Tools Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ 高德地图  │  │ 博查搜索  │  │  Chroma  │             │
│  │  POI API │  │ Web API  │  │ Vector DB│             │
│  └──────────┘  └──────────┘  └──────────┘             │
├─────────────────────────────────────────────────────────┤
│                    通义千问 (Qwen)                       │
│                      LLM Layer                          │
├─────────────────────────────────────────────────────────┤
│                     Langfuse                            │
│                 (LLM Observability)                     │
└─────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/travelmind.git
cd travelmind
```

### 2. 环境配置

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写必需的 API Key：

```bash
# 【必须】通义千问 API Key
# 获取地址: https://bailian.console.aliyun.com/
DASHSCOPE_API_KEY=sk-your-api-key

# 【推荐】高德地图 API Key  
# 获取地址: https://lbs.amap.com/
AMAP_API_KEY=your-amap-key

# 【可选】博查搜索 API Key
# 获取地址: https://open.bochaai.com/
BOCHA_API_KEY=your-bocha-key
```

### 3. 启动服务

```bash
docker-compose up -d
```

首次启动需要等待 1-2 分钟，Langfuse 需要执行数据库迁移。

### 4. 配置 Langfuse（首次）

1. 访问 http://localhost:3000
2. 注册账号（数据存储在本地，完全私有）
3. 创建项目
4. 进入 Settings → API Keys → 创建 API Key
5. 更新 `.env` 文件：
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-xxx
   LANGFUSE_SECRET_KEY=sk-lf-xxx
   LANGFUSE_HOST=http://langfuse:3000
   ```
6. 重新创建容器以加载新配置：
   ```bash
   docker-compose up -d --force-recreate app
   ```

### 5. 访问服务

| 服务 | 地址 |
|------|------|
| API 文档 (Swagger) | http://localhost:8000/docs |
| API 文档 (ReDoc) | http://localhost:8000/redoc |
| 健康检查 | http://localhost:8000/api/v1/health |
| Langfuse 监控 | http://localhost:3000 |

## 🐳 Docker 命令

```bash
# 启动所有服务
docker-compose up -d

# 重新构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 只看 TravelMind 日志
docker-compose logs -f app

# 重启 TravelMind（不影响 Langfuse）
docker-compose restart app

# 停止所有服务
docker-compose down

# 停止并删除数据（包括 Langfuse 数据库）
docker-compose down -v
```

## 📖 API 使用

详细 API 文档请参考 [docs/API.md](docs/API.md)

### 智能对话

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我规划一个杭州三日游，预算3000元"}'
```

### 流式对话

```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我规划一个杭州三日游"}'
```

### POI 搜索

```bash
curl -X POST "http://localhost:8000/api/v1/tools/poi/search" \
  -H "Content-Type: application/json" \
  -d '{"keywords": "西湖", "city": "杭州", "poi_type": "scenic"}'
```

### 天气查询

```bash
curl -X POST "http://localhost:8000/api/v1/tools/weather" \
  -H "Content-Type: application/json" \
  -d '{"city": "杭州", "forecast": true}'
```

## 📁 项目结构

```
travelmind/
├── src/
│   ├── api/              # FastAPI 路由和 Schema
│   │   ├── routes.py     # API 端点定义
│   │   └── schemas.py    # Pydantic 数据模型
│   ├── config/           # 配置管理
│   │   └── settings.py   # Pydantic Settings
│   ├── core/             # 核心模块
│   │   └── observability.py  # Langfuse 集成
│   ├── graphs/           # LangGraph 工作流
│   │   ├── state.py      # 状态定义
│   │   ├── nodes.py      # 节点实现
│   │   └── travel_graph.py   # 主工作流
│   ├── llm/              # LLM Provider
│   │   ├── base.py       # 抽象基类
│   │   └── qwen.py       # 通义千问实现
│   ├── rag/              # RAG 向量检索
│   │   └── vector_store.py   # Chroma 实现
│   ├── tools/            # Agent 工具
│   │   ├── amap.py       # 高德地图 API
│   │   ├── search.py     # 博查搜索 API
│   │   └── definitions.py    # LangGraph 工具定义
│   └── main.py           # FastAPI 入口
├── tests/                # 测试文件
├── docs/                 # 文档
│   ├── API.md            # API 接口文档
│   ├── ARCHITECTURE_COMPONENTS.md
│   ├── SECURITY.md       # 安全部署指南
│   └── adr/              # 架构决策记录
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile            # Docker 镜像定义
├── pyproject.toml        # 项目配置
├── Makefile              # 常用命令
└── README.md
```

## 🧪 本地开发

如果不使用 Docker，可以本地运行：

```bash
# 安装依赖
pip install -e ".[dev]"

# 启动开发服务器
make dev

# 运行测试
make test

# 代码检查
make lint

# 代码格式化
make format
```

## 📊 Langfuse 可观测性

项目集成了 [Langfuse](https://langfuse.com/) 进行 LLM 调用追踪：

- **自托管部署**：数据完全私有，无需注册 langfuse.com
- **追踪内容**：模型调用、输入输出、Token 用量、耗时
- **成本分析**：自动计算通义千问 API 调用成本

### 版本兼容性

| 自托管 Langfuse 版本 | SDK 版本要求 |
|---------------------|-------------|
| v2.x | `langfuse>=2.0.0,<3.0.0` |
| v3.x | `langfuse>=3.0.0` |

当前项目使用 Langfuse **v2.x** 自托管版本，SDK 自动限制为 v2。

### 查看 Traces

1. 访问 http://localhost:3000
2. 进入项目 → Tracing → Traces
3. 点击具体 Trace 查看详情
4. 点击 "llm-generation" 查看输入输出

## 🔧 技术栈

| 类别 | 技术选型 | 说明 |
|------|---------|------|
| AI 框架 | LangGraph | 基于图的 Agent 工作流引擎 |
| LLM | 通义千问 (Qwen) | 阿里云百炼平台，中文优化 |
| Web 框架 | FastAPI | 高性能异步 API 框架 |
| 数据验证 | Pydantic v2 | 类型安全的数据模型 |
| 向量数据库 | Chroma | 轻量级嵌入式向量库 |
| 地图服务 | 高德地图 | POI 搜索、天气、路线规划 |
| 搜索服务 | 博查搜索 | AI 优化的中文网页搜索 |
| 可观测性 | Langfuse | LLM 调用追踪与成本分析 |
| 容器化 | Docker Compose | 一键部署（含 Langfuse） |

## 🔒 安全说明

- API Key 通过环境变量配置，不要提交到代码仓库
- 生产环境建议使用密钥管理服务（如阿里云 KMS）
- 详细安全指南请参考 [docs/SECURITY.md](docs/SECURITY.md)

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [LangChain](https://langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/) - AI 应用开发框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [通义千问](https://tongyi.aliyun.com/) - 大语言模型
- [高德开放平台](https://lbs.amap.com/) - 地图服务
- [Langfuse](https://langfuse.com/) - LLM 可观测性平台
