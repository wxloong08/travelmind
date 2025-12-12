# TravelMind Docker 本地开发指南

## 快速开始

### 1. 创建 .env 文件

```bash
cd travelmind-main
cp .env.example .env
```

### 2. 编辑 .env 文件

**最小配置（必须）**：

```bash
# 【必须】通义千问 API Key
# 获取地址: https://bailian.console.aliyun.com/
DASHSCOPE_API_KEY=sk-your-dashscope-api-key

# 【推荐】高德地图 API Key
# 获取地址: https://lbs.amap.com/
AMAP_API_KEY=your-amap-api-key

# 【推荐】博查搜索 API Key
# 获取地址: https://open.bochaai.com/
BOCHA_API_KEY=your-bocha-api-key
```

**完整配置（端到端测试）**：

```bash
# ============================================================
# 基础配置
# ============================================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_PORT=8000

# ============================================================
# 【必须】LLM 配置 - 通义千问
# ============================================================
DASHSCOPE_API_KEY=sk-your-dashscope-api-key
LLM_MODEL=qwen-turbo

# ============================================================
# 【推荐】外部 API
# ============================================================
# 高德地图（POI 搜索、天气、路线）
AMAP_API_KEY=your-amap-api-key

# 博查搜索（旅游攻略、新闻）
BOCHA_API_KEY=your-bocha-api-key

# ============================================================
# 用户系统配置
# ============================================================
# PostgreSQL 密码（Docker 内部使用）
POSTGRES_PASSWORD=travelmind123

# JWT 密钥（生产环境请用: openssl rand -hex 32）
SECRET_KEY=dev-secret-key-change-in-production

# Token 有效期（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ============================================================
# 【可选】腾讯云短信（不配置则使用开发模式）
# ============================================================
# 开发模式下验证码会直接返回，不实际发送
# TENCENT_SMS_SECRET_ID=your-secret-id
# TENCENT_SMS_SECRET_KEY=your-secret-key
# TENCENT_SMS_APP_ID=your-app-id
# TENCENT_SMS_SIGN_NAME=TravelMind
# TENCENT_SMS_TEMPLATE_ID=123456
```

### 3. 启动服务

```bash
# 构建并启动（首次需要构建，约 5-10 分钟）
docker-compose up -d --build

# 查看日志
docker-compose logs -f app

# 查看所有服务状态
docker-compose ps
```

### 4. 运行数据库迁移

```bash
# 进入容器执行迁移
docker-compose exec app alembic upgrade head
```

### 5. 创建管理员账号

```bash
# 方法1: 进入数据库容器
docker-compose exec postgres psql -U travelmind -d travelmind

# 执行 SQL（先通过 API 注册用户，然后升级为管理员）
UPDATE users SET role='admin', daily_quota=999 WHERE phone='你的手机号';
\q

# 方法2: 一行命令
docker-compose exec postgres psql -U travelmind -d travelmind -c \
  "UPDATE users SET role='admin', daily_quota=999 WHERE phone='13800138000';"
```

### 6. 验证服务

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 查看 API 文档
open http://localhost:8000/docs

# 访问后台管理
open http://localhost:8000/api/v1/admin/
```

---

## 服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                    docker-compose                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    app      │  │  postgres   │  │   redis     │         │
│  │  (FastAPI)  │  │  (数据库)   │  │  (缓存)     │         │
│  │   :8000     │  │   :5432     │  │   :6379     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

| 服务 | 端口 | 说明 |
|-----|------|------|
| app | 8000 | FastAPI 后端 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |

---

## 常用命令

### Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 重新构建并启动
docker-compose up -d --build

# 停止所有服务
docker-compose down

# 停止并删除数据卷（⚠️ 会丢失数据）
docker-compose down -v

# 查看日志
docker-compose logs -f           # 所有服务
docker-compose logs -f app       # 只看 app
docker-compose logs -f postgres  # 只看数据库

# 进入容器
docker-compose exec app bash
docker-compose exec postgres psql -U travelmind -d travelmind

# 重启单个服务
docker-compose restart app
```

### 数据库操作

```bash
# 运行迁移
docker-compose exec app alembic upgrade head

# 查看迁移历史
docker-compose exec app alembic history

# 回滚迁移
docker-compose exec app alembic downgrade -1

# 连接数据库
docker-compose exec postgres psql -U travelmind -d travelmind

# 常用 SQL
\dt                    # 查看所有表
SELECT * FROM users;   # 查看用户
SELECT * FROM activation_codes;  # 查看激活码
\q                     # 退出
```

---

## 端到端测试流程

### 1. 启动前端（另开终端）

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 2. 测试用户流程

1. **游客模式**
   - 打开 http://localhost:5173
   - 输入 "帮我规划北京3天亲子游"
   - 观察行程生成（游客每天只能用 1 次）

2. **注册登录**
   - 点击右上角"登录"
   - 输入手机号，获取验证码
   - 开发模式下验证码会显示在页面上
   - 登录后变为免费用户（每天 3 次）

3. **使用激活码**
   - 管理员后台生成激活码
   - 用户输入激活码升级为付费用户

4. **后台管理**
   - 访问 http://localhost:8000/api/v1/admin/
   - 用管理员账号登录
   - 查看用户列表、生成激活码、查看统计

### 3. 测试 API

```bash
# 游客初始化
curl -X POST http://localhost:8000/api/v1/auth/guest/init \
  -H "Content-Type: application/json" \
  -d '{"device_fingerprint": "test-device-123"}'

# 发送验证码
curl -X POST http://localhost:8000/api/v1/auth/sms/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000"}'

# 验证码登录（开发模式返回的 code）
curl -X POST http://localhost:8000/api/v1/auth/sms/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000", "code": "123456"}'

# 获取配额信息
curl http://localhost:8000/api/v1/auth/quota \
  -H "Authorization: Bearer YOUR_TOKEN"

# 生成行程
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "帮我规划北京3天亲子游", "session_id": "test-session"}'
```

---

## 故障排除

### 1. 容器启动失败

```bash
# 查看详细日志
docker-compose logs app

# 常见问题:
# - DASHSCOPE_API_KEY 未配置
# - 端口被占用（8000, 5432, 6379）
```

### 2. 数据库连接失败

```bash
# 检查 postgres 是否启动
docker-compose ps postgres

# 检查连接
docker-compose exec postgres pg_isready -U travelmind
```

### 3. 迁移失败

```bash
# 查看当前迁移状态
docker-compose exec app alembic current

# 手动修复（回滚后重新执行）
docker-compose exec app alembic downgrade base
docker-compose exec app alembic upgrade head
```

### 4. 清理重来

```bash
# 停止并删除所有容器和数据
docker-compose down -v

# 删除构建缓存
docker system prune -a

# 重新开始
docker-compose up -d --build
docker-compose exec app alembic upgrade head
```

---

## 环境变量说明

| 变量 | 必须 | 默认值 | 说明 |
|-----|------|--------|------|
| `DASHSCOPE_API_KEY` | ✅ | - | 通义千问 API Key |
| `AMAP_API_KEY` | 推荐 | - | 高德地图 API Key |
| `BOCHA_API_KEY` | 推荐 | - | 博查搜索 API Key |
| `POSTGRES_PASSWORD` | - | travelmind123 | 数据库密码 |
| `SECRET_KEY` | - | dev-secret... | JWT 密钥 |
| `DEBUG` | - | true | 调试模式 |
| `LOG_LEVEL` | - | INFO | 日志级别 |
| `TENCENT_SMS_*` | - | - | 短信服务（不配置则开发模式） |

---

## 下一步

1. **前端开发**：`cd frontend && npm run dev`
2. **API 文档**：http://localhost:8000/docs
3. **后台管理**：http://localhost:8000/api/v1/admin/
4. **可观测性**：`docker-compose --profile observability up -d`（启用 Langfuse）