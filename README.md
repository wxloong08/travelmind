# 🧳 TravelMind

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AI 驱动的旅游规划助手** - 基于 LangGraph 的智能 Agent 应用

## ✨ 功能特性

### 核心功能
- 🗺️ **智能旅游规划** - 根据偏好制定个性化旅游攻略
- 🏨 **景点/酒店推荐** - 实时搜索目的地 POI 信息
- 📅 **行程安排** - 合理规划每日行程，考虑距离与时间
- 🌤️ **天气查询** - 获取目的地实时天气和预报
- 🔍 **实时资讯** - 搜索最新旅游攻略和新闻
- 💰 **预算仪表盘** - 基于行程数据的精确费用计算

### 用户系统
- 👤 **多用户等级** - 游客(1次/天)、免费用户(3次/天)、付费用户(20次/天)
- 📱 **手机号登录** - 短信验证码登录（支持开发模式）
- 🎫 **激活码系统** - 支持升级付费、增加次数
- 🔐 **后台管理** - 用户管理、激活码管理、使用统计

### 智能缓存
- 📚 **RAG 知识库** - 博查搜索结果自动存入向量数据库
- ⚡ **智能检索** - 相似查询优先使用本地缓存，节省 API 费用
- 📊 **LLM 可观测性** - Langfuse 集成，追踪调用和成本

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 18+（仅前端开发需要）

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/travelmind.git
cd travelmind
```

### 2. 环境配置

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 【必须】通义千问 API Key
# 获取地址: https://bailian.console.aliyun.com/
DASHSCOPE_API_KEY=sk-your-api-key

# 【推荐】高德地图 API Key  
# 获取地址: https://lbs.amap.com/
AMAP_API_KEY=your-amap-key

# 【推荐】博查搜索 API Key
# 获取地址: https://open.bochaai.com/
BOCHA_API_KEY=your-bocha-key
```

> 其他配置（数据库、JWT 等）使用 docker-compose.yml 中的默认值即可

### 3. 启动后端服务

```bash
# 构建并启动（首次约 5-10 分钟）
docker-compose up -d --build

# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 查看日志
docker-compose logs -f app
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5. 创建管理员账号

```bash
# 1. 先通过前端登录注册一个用户
# 2. 升级为管理员
docker-compose exec postgres psql -U travelmind -d travelmind -c \
  "UPDATE users SET role='admin', daily_quota=999 WHERE phone='你的手机号';"
```

### 6. 访问服务

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost:5173 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 后台管理 | http://localhost:8000/api/v1/admin/ |
| 健康检查 | http://localhost:8000/api/v1/health |

## 👥 用户系统

### 用户等级

| 等级 | 每日次数 | 获取方式 |
|-----|---------|---------|
| 游客 | 1 次 | 自动（设备指纹） |
| 免费用户 | 3 次 | 手机号注册 |
| 付费用户 | 20 次 | 激活码升级 |
| 管理员 | 无限制 | 数据库设置 |

### 激活码

```
格式: TRVL-XXXX-XXXX-XXXX

类型:
- upgrade_paid: 升级为付费用户
- add_quota: 增加额外次数
```

管理员可在后台 http://localhost:8000/api/v1/admin/ 生成激活码

## 📚 RAG 知识库

### 工作原理

```
用户搜索 → 查本地向量库 → 有3+结果? → 返回缓存（免费）
                              ↓
                            没有
                              ↓
                         调用博查 API（付费）
                              ↓
                         存入向量库
                              ↓
                         返回结果
```

### 查看 RAG 存储内容

```bash
# 进入容器
docker-compose exec app bash

# 启动 Python
python

# 查看向量库内容
>>> from src.rag import get_vector_store
>>> store = get_vector_store()
>>> collection = store._get_collection()
>>> print(f"文档数量: {collection.count()}")
>>> 
>>> # 查看文档列表
>>> results = collection.get(include=["documents", "metadatas"])
>>> for i, meta in enumerate(results["metadatas"][:5]):
...     print(f"[{i}] {meta.get('title', '无标题')[:50]}")
...     print(f"    目的地: {meta.get('destination', '-')}")
>>> 
>>> exit()
```

### RAG 数据位置

```bash
# 查看 Docker 卷
docker volume inspect travelmind_travelmind_data

# 查看容器内文件
docker-compose exec app ls -la /app/data/chroma/
```

## 🐳 Docker 命令

```bash
# 启动所有服务
docker-compose up -d

# 重新构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f app

# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 进入容器
docker-compose exec app bash
docker-compose exec postgres psql -U travelmind -d travelmind

# 停止服务
docker-compose down

# 停止并删除数据（⚠️ 会丢失所有数据）
docker-compose down -v
```

## 📖 API 文档

详细 API 文档请参考 [docs/API.md](docs/API.md)

### 流式对话

```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "帮我规划一个北京三日亲子游", "session_id": "test"}'
```

### 获取配额信息

```bash
curl "http://localhost:8000/api/v1/auth/quota" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 使用激活码

```bash
curl -X POST "http://localhost:8000/api/v1/auth/activate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"code": "TRVL-XXXX-XXXX-XXXX"}'
```

## 🏗️ 系统架构

### POI-Based 工作流

```mermaid
graph TD
    A[用户输入] --> B[understand_intent]
    B --> C[research_node]
    
    subgraph "Research Phase 并行"
        C --> D1[搜索景点 POI<br/>带坐标]
        C --> D2[搜索酒店 POI<br/>带坐标]
        C --> D3[搜索餐厅 POI<br/>带坐标]
        C --> D4[获取天气]
        C --> D5[推断交通枢纽<br/>机场/车站坐标]
    end
    
    D1 & D2 & D3 & D4 & D5 --> E[构建 POI 距离矩阵]
    E --> F[planning_node<br/>LLM 从 POI 池选择]
    F --> G[本地距离验证<br/>Haversine]
    G -->|通过| H[respond]
    G -->|超标| I[智能调整]
    I --> F
```

### 核心设计原则

| 原则 | 说明 |
|-----|------|
| **POI 选择制** | LLM 从 POI 池中选择，而非自由生成文本 |
| **坐标前置** | Research 阶段并行获取所有 POI 坐标 |
| **本地验证** | 距离检查使用 Haversine 公式，减少 API 调用 |
| **Default & Refine** | 智能默认值 + 用户可调整 |

## 📁 项目结构

```
travelmind/
├── src/
│   ├── api/              # FastAPI 路由
│   │   ├── routes/       # 拆分的路由模块
│   │   │   ├── auth.py   # 认证相关
│   │   │   ├── admin.py  # 后台管理
│   │   │   └── trips.py  # 行程管理
│   │   └── schemas.py    # Pydantic 数据模型
│   ├── auth/             # 认证模块
│   ├── db/               # 数据库模块
│   │   ├── models/       # SQLAlchemy 模型
│   │   └── repositories/ # 数据访问层
│   ├── services/         # 业务服务
│   │   ├── quota_service.py      # 配额管理
│   │   ├── knowledge_service.py  # RAG 知识库
│   │   └── trip_service.py       # 行程服务
│   ├── graphs/           # LangGraph 工作流
│   │   ├── nodes/        # 节点模块（模块化）
│   │   │   ├── intent.py     # 意图理解节点
│   │   │   ├── research.py   # 信息收集节点
│   │   │   ├── planning.py   # 行程规划节点
│   │   │   ├── respond.py    # 响应生成节点
│   │   │   ├── evaluate.py   # 评估检查节点
│   │   │   └── reflect.py    # 反思优化节点
│   │   ├── poi/          # POI 模块
│   │   │   ├── models.py     # EnhancedPOI 数据结构
│   │   │   └── validator.py  # 距离验证器
│   │   ├── utils/        # 工具函数
│   │   │   ├── prompts.py    # Prompt 模板
│   │   │   └── parsers.py    # 解析函数
│   │   ├── state.py      # AgentState 定义
│   │   └── travel_graph.py   # 工作流图定义
│   ├── rag/              # RAG 向量检索
│   ├── tools/            # Agent 工具
│   └── main.py           # FastAPI 入口
├── frontend/             # React 前端
├── alembic/              # 数据库迁移
├── docs/                 # 文档
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 🔧 技术栈

| 类别 | 技术选型 | 说明 |
|------|---------|------|
| 前端 | React + Vite | 现代前端构建 |
| 状态管理 | Zustand | 轻量级状态管理 |
| 地图 | 高德地图 JS API | 地图展示和路线 |
| AI 框架 | LangGraph | 基于图的 Agent 工作流 |
| LLM | 通义千问 (Qwen) | 阿里云百炼平台 |
| Web 框架 | FastAPI | 高性能异步 API |
| 数据库 | PostgreSQL | 用户和行程存储 |
| 缓存 | Redis | API 缓存和限流 |
| 向量数据库 | Chroma | RAG 知识库 |
| 搜索服务 | 博查搜索 | AI 优化的中文搜索 |

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。