# TravelMind v2.0 升级说明

## 🔗 集成关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           main.py                                    │
│  - lifespan 中调用 init_db() 和 init_redis()                         │
│  - 注册 auth_router 和 trips_router                                  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────┐
│  src/db/      │   │  src/auth/    │   │  src/cache/       │
│  - database   │   │  - jwt        │   │  - redis_client   │
│  - models     │   │  - deps       │   │  - rate_limiter   │
│  - repos      │   │  - sms        │   │  - api_cache      │
└───────────────┘   └───────────────┘   └───────────────────┘
        │                   │
        └─────────┬─────────┘
                  ▼
        ┌───────────────────┐
        │ src/api/routes/   │
        │  - auth.py        │  ← 调用 db + auth
        │  - trips.py       │  ← 调用 db + auth
        └───────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     src/graphs/nodes.py                             │
│                                                                      │
│  planning_node:                                                      │
│    1. LLM 生成结构化行程                                             │
│    2. accommodation_logic.process_itinerary_accommodation()  ← 集成点│
│    3. budget_calculator.calculate()                          ← 集成点│
│    4. 返回 travel_plan                                               │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │  src/services/            │
              │  - budget_calculator.py   │  ← 精确预算计算
              │  - accommodation_logic.py │  ← 住宿逻辑修复
              │  - trip_service.py        │  ← 行程保存
              └───────────────────────────┘
```

## ✅ 关键集成点验证

| 文件 | 集成内容 | 位置 |
|------|---------|------|
| `src/graphs/nodes.py` | `from src.services.budget_calculator import budget_calculator` | 第19行 |
| `src/graphs/nodes.py` | `from src.services.accommodation_logic import accommodation_logic` | 第20行 |
| `src/graphs/nodes.py` | `accommodation_logic.process_itinerary_accommodation()` | planning_node 中 |
| `src/graphs/nodes.py` | `budget_calculator.calculate()` | planning_node 中 |
| `src/main.py` | `from src.db.database import init_db` | 第59行 |
| `src/main.py` | `from src.api.routes import auth_router, trips_router` | 第188行 |
| `src/main.py` | `app.include_router(auth_router)` | 第189行 |

## 📋 本次升级内容

### 新增功能

| 功能 | 说明 | 状态 |
|------|------|------|
| **PostgreSQL 数据库** | 存储用户、行程、对话历史 | ✅ 完成 |
| **JWT 用户认证** | 游客模式 + 手机短信登录 | ✅ 完成 |
| **Redis 缓存** | 可选，支持优雅降级为内存缓存 | ✅ 完成 |
| **API 限流** | 用户级（10/30 次/分钟）+ 高德 3 QPS 全局限流 | ✅ 完成 |
| **行程持久化** | 刷新页面后可恢复行程 | ✅ 完成 |
| **精确预算计算** | 基于实际酒店价格和门票费用 | ✅ 完成 |
| **住宿逻辑修复** | 解决"明天继续住"矛盾 + 行李提示 | ✅ 完成 |
| **中途改口处理** | 检测目的地变化，自动清空旧数据 | ✅ 完成 |

### 修复问题

1. **预算估算不准确**：现在基于实际行程数据精确计算
2. **住宿显示矛盾**：Day 2 显示"明天继续住"但 Day 3 换酒店的问题已修复
3. **行李处理提示**：换酒店时显示行李处理建议

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，至少配置以下内容：
# - DASHSCOPE_API_KEY (必须)
# - DATABASE_URL (用户系统)
# - SECRET_KEY (JWT 密钥)
```

### 2. 启动服务

```bash
# 方式1：Docker Compose（推荐）
docker-compose up -d

# 方式2：本地开发
# 先启动 PostgreSQL
docker-compose up -d postgres

# 运行数据库迁移
alembic upgrade head

# 启动应用
make dev
```

### 3. 验证

```bash
# 检查 API 健康状态
curl http://localhost:8000/api/v1/health

# 查看 API 文档
open http://localhost:8000/docs
```

---

## 📁 新增文件结构

```
src/
├── auth/                      # 认证模块（新增）
│   ├── __init__.py
│   ├── jwt.py                 # JWT Token 管理
│   ├── deps.py                # FastAPI 依赖注入
│   └── sms.py                 # 腾讯云短信服务
├── db/                        # 数据库模块（新增）
│   ├── __init__.py
│   ├── database.py            # 连接管理
│   ├── models/                # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── guest.py
│   │   ├── trip.py
│   │   └── conversation.py
│   └── repositories/          # 数据访问层
│       ├── __init__.py
│       ├── user_repo.py
│       ├── guest_repo.py
│       ├── trip_repo.py
│       └── conversation_repo.py
├── cache/                     # 缓存模块（新增）
│   ├── __init__.py
│   ├── redis_client.py        # Redis 连接（支持降级）
│   ├── rate_limiter.py        # 限流器
│   └── api_cache.py           # API 结果缓存
├── api/routes/                # 路由拆分（新增）
│   ├── __init__.py
│   ├── auth.py                # 认证 API
│   └── trips.py               # 行程 API
└── services/                  # 业务服务（更新）
    ├── budget_calculator.py   # 精确预算计算（新增）
    ├── accommodation_logic.py # 住宿逻辑（新增）
    └── trip_service.py        # 行程保存服务（新增）

alembic/
└── versions/
    └── 001_initial.py         # 初始数据库迁移
```

---

## 🔐 认证流程

### 游客模式

```
POST /api/v1/auth/guest
Body: {"device_fingerprint": "xxx"}

Response: {
  "token": "eyJ...",
  "guest_id": "uuid",
  "remaining_today": 1,
  "message": "今日剩余 1 次使用机会"
}
```

### 短信登录

```
# 1. 发送验证码
POST /api/v1/auth/sms/send
Body: {"phone": "13800138000"}

# 2. 验证并登录
POST /api/v1/auth/sms/verify
Body: {"phone": "13800138000", "code": "123456"}

Response: {
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "user_id": "uuid"
}
```

---

## 📊 API 端点

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/guest` | 获取游客 Token |
| POST | `/api/v1/auth/sms/send` | 发送短信验证码 |
| POST | `/api/v1/auth/sms/verify` | 验证并登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |

### 行程

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/trips` | 获取行程列表 |
| GET | `/api/v1/trips/latest` | 获取最新行程（刷新恢复） |
| GET | `/api/v1/trips/{id}` | 获取行程详情 |
| DELETE | `/api/v1/trips/{id}` | 删除行程 |

---

## ⚙️ 环境变量

### 必须配置

```bash
DASHSCOPE_API_KEY=sk-xxx          # 通义千问 API
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db  # 数据库
SECRET_KEY=xxx                     # JWT 密钥（openssl rand -hex 32）
```

### 推荐配置

```bash
AMAP_API_KEY=xxx                   # 高德地图
REDIS_URL=redis://localhost:6379/0 # Redis（可选）
```

### 短信服务（可选）

```bash
TENCENT_SMS_SECRET_ID=xxx
TENCENT_SMS_SECRET_KEY=xxx
TENCENT_SMS_APP_ID=xxx
TENCENT_SMS_TEMPLATE_ID=xxx
```

---

## 🔄 数据库迁移

```bash
# 生成新迁移（模型变更后）
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 🧪 测试

```bash
# 运行测试
pytest

# 带覆盖率
pytest --cov=src
```

---

## 📝 注意事项

1. **首次部署**：确保执行 `alembic upgrade head` 创建数据库表
2. **短信服务**：未配置时为开发模式，验证码直接返回（不发送短信）
3. **Redis**：未配置时自动降级为内存缓存（重启会丢失）
4. **JWT 密钥**：生产环境务必使用强密钥
