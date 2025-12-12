# TravelMind 用户系统升级指南

本文档说明如何启用 TravelMind 的用户系统功能，包括：
- 游客模式（每日 1 次免费使用）
- 手机号短信登录
- 行程保存和历史记录
- API 限流保护

## 📋 新增功能概览

| 功能 | 说明 | 状态 |
|------|------|------|
| PostgreSQL 数据库 | 存储用户、行程、对话 | ✅ 已实现 |
| JWT 用户认证 | 游客 + 手机号登录 | ✅ 已实现 |
| Redis 缓存 | 会话缓存 + API 限流（可选） | ✅ 已实现 |
| 行程保存 | 刷新浏览器后可恢复 | ✅ 已实现 |
| 精确预算计算 | 基于实际数据而非 LLM 估算 | ✅ 已实现 |
| 住宿逻辑修复 | 修复矛盾提示 + 行李建议 | ✅ 已实现 |
| 中途改口检测 | 自动清理旧数据 | ✅ 已实现 |
| 微信登录 | 需要企业资质 | ⏳ 预留 |

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 更新配置
cp .env.example .env
# 编辑 .env，添加以下配置：
# SECRET_KEY=your-super-secret-key（必须，可用 openssl rand -hex 32 生成）
# POSTGRES_PASSWORD=your-password（可选，默认 travelmind123）

# 2. 启动服务（API + PostgreSQL + Redis）
docker-compose up -d

# 3. 初始化数据库
docker-compose exec app alembic upgrade head

# 4. 查看日志
docker-compose logs -f app
```

### 方式二：本地开发

```bash
# 1. 安装依赖
pip install -e ".[dev]"

# 2. 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 3. 配置环境变量
export DATABASE_URL="postgresql+asyncpg://travelmind:travelmind123@localhost:5432/travelmind"
export SECRET_KEY="your-super-secret-key"
# 可选：export REDIS_URL="redis://localhost:6379/0"

# 4. 初始化数据库
make db-init

# 5. 启动开发服务器
make dev
```

## ⚙️ 配置说明

### 必须配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接 | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT 密钥（32 字符以上） | `openssl rand -hex 32` 生成 |

### 可选配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `REDIS_URL` | Redis 连接 | 空（使用内存缓存） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期 | 60 |
| `TENCENT_SMS_*` | 腾讯云短信配置 | 空（开发模式） |

### 腾讯云短信配置（可选）

如果需要实际发送短信验证码，需要配置：

```bash
TENCENT_SMS_SECRET_ID=your-secret-id
TENCENT_SMS_SECRET_KEY=your-secret-key
TENCENT_SMS_APP_ID=your-app-id
TENCENT_SMS_SIGN_NAME=TravelMind
TENCENT_SMS_TEMPLATE_ID=123456
```

**开发模式**：未配置短信时，验证码会直接返回（不实际发送），方便测试。

## 📡 新增 API

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/guest` | POST | 获取游客 Token |
| `/api/v1/auth/sms/send` | POST | 发送验证码 |
| `/api/v1/auth/sms/verify` | POST | 验证并登录 |
| `/api/v1/auth/refresh` | POST | 刷新 Token |
| `/api/v1/auth/me` | GET | 获取当前用户 |
| `/api/v1/auth/logout` | POST | 登出 |

### 行程接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/trips` | GET | 获取行程列表 |
| `/api/v1/trips/{id}` | GET | 获取行程详情 |
| `/api/v1/trips/{id}` | DELETE | 删除行程 |

## 🔐 认证流程

### 游客模式

```
1. 前端生成设备指纹（如 FingerprintJS）
2. POST /auth/guest {device_fingerprint: "xxx"}
3. 返回 {token, remaining_today: 1}
4. 每日限制 1 次完整使用
```

### 手机号登录

```
1. POST /auth/sms/send {phone: "13800138000"}
2. 返回 {success: true, message: "验证码已发送"}
   （开发模式会返回 code 字段）
3. POST /auth/sms/verify {phone: "13800138000", code: "123456"}
4. 返回 {access_token, refresh_token, user_id}
```

### Token 使用

```
Authorization: Bearer <access_token>
```

## 📊 数据库结构

```
users          # 注册用户
├── id         # UUID 主键
├── phone      # 手机号（唯一）
├── nickname   # 昵称
└── ...

guests         # 游客
├── id
├── device_fingerprint  # 设备指纹
├── daily_usage_count   # 每日使用次数
└── ...

trips          # 行程
├── id
├── user_id / guest_id  # 归属
├── title, destination, days
├── itinerary_data      # 完整行程 JSON
└── ...

conversations  # 对话
├── id
├── user_id / guest_id
├── session_id
└── trip_id    # 关联的行程

messages       # 消息
├── id
├── conversation_id
├── role, content
└── metadata
```

## 🔧 数据库迁移

```bash
# 查看迁移历史
make db-history

# 升级到最新
make db-upgrade

# 回滚一个版本
make db-downgrade

# 生成新迁移（修改模型后）
make db-migrate msg="add new column"
```

## 🧪 测试

### 测试游客模式

```bash
# 获取游客 Token
curl -X POST http://localhost:8000/api/v1/auth/guest \
  -H "Content-Type: application/json" \
  -d '{"device_fingerprint": "test-device-12345678"}'

# 使用 Token 访问 API
curl http://localhost:8000/api/v1/trips \
  -H "Authorization: Bearer <token>"
```

### 测试手机号登录（开发模式）

```bash
# 发送验证码
curl -X POST http://localhost:8000/api/v1/auth/sms/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000"}'
# 返回：{"success": true, "code": "123456", "message": "开发模式：验证码为 123456"}

# 验证并登录
curl -X POST http://localhost:8000/api/v1/auth/sms/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000", "code": "123456"}'
```

## ❓ 常见问题

### Q: 不配置数据库可以使用吗？
A: 可以，但用户系统相关功能（登录、行程保存）不可用。核心的 AI 规划功能正常工作。

### Q: Redis 是必须的吗？
A: 不是。未配置 Redis 时会自动使用内存缓存，对个人使用场景足够。

### Q: 如何查看开发模式的验证码？
A: 未配置腾讯云短信时，`/auth/sms/send` 响应会包含 `code` 字段。

### Q: 游客每日限制可以修改吗？
A: 可以修改 `src/db/models/guest.py` 中的 `DAILY_LIMIT` 常量。

## 📝 更新日志

### v0.2.0 (2024-12-11)
- 新增：PostgreSQL 数据库支持
- 新增：JWT 用户认证（游客 + 手机号）
- 新增：Redis 缓存（可选）
- 新增：行程保存和历史记录
- 新增：精确预算计算
- 修复：住宿显示逻辑矛盾
- 修复：中途改口数据不清理
