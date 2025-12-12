# TravelMind 用户系统升级 + RAG 知识库

## 更新日期: 2024-12-12

---

## 概述

本次更新实现了三个主要功能：
1. **用户等级和配额系统** - 免费用户/付费用户/管理员
2. **简易后台管理系统** - 用户管理、激活码管理、统计
3. **RAG 知识库集成** - 博查搜索结果缓存，减少 API 调用

---

## 1. 用户等级系统

### 用户类型

| 用户类型 | 每日配额 | 说明 |
|---------|---------|------|
| 游客 | 1 次/天 | 设备指纹识别，无需注册 |
| 免费用户 | 3 次/天 | 手机号注册登录 |
| 付费用户 | 20 次/天 | 通过激活码升级 |
| 管理员 | 无限制 | 可管理用户和激活码 |

### 数据库字段

```sql
-- users 表新增字段
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN daily_quota INTEGER DEFAULT 3;
ALTER TABLE users ADD COLUMN bonus_quota INTEGER DEFAULT 0;
```

### 配额计算规则

```
可用次数 = 每日配额 + 额外次数 - 今日已用

优先消耗每日配额，超出部分消耗额外次数
每日配额 00:00 重置，额外次数用完即止
```

---

## 2. 激活码系统

### 激活码类型

| 类型 | 代码 | 效果 |
|-----|------|------|
| 升级付费 | `upgrade_paid` | 用户升级为付费用户，每日配额变为 20 |
| 增加次数 | `add_quota` | 增加 N 次额外使用机会 |

### 激活码格式

```
TRVL-XXXX-XXXX-XXXX
例如: TRVL-A1B2-C3D4-E5F6
```

### 使用流程

1. 管理员在后台生成激活码
2. 用户在前端输入激活码
3. 系统验证并应用效果

---

## 3. 后台管理系统

### 访问地址

```
http://localhost:8000/api/v1/admin/
```

### 功能列表

#### 用户管理
- 查看用户列表（支持搜索）
- 修改用户角色（free/paid/admin）
- 修改每日配额
- 增加临时次数（bonus_quota）
- 禁用/启用用户

#### 激活码管理
- 生成激活码（支持批量）
- 查看激活码列表
- 查看使用记录
- 删除未使用的激活码

#### 统计面板
- 注册用户数
- 付费用户数
- 游客数
- 今日使用次数
- 本周使用次数

---

## 4. RAG 知识库

### 工作流程

```
用户请求规划
    ↓
搜索本地向量库（Chroma）
    ↓
结果数量 >= 3 ?
    ├── 是 → 返回缓存结果
    └── 否 → 调用博查 API
              ↓
         存储结果到向量库
              ↓
         返回 API 结果
```

### 存储内容

| 内容类型 | 来源 | 存储时机 |
|---------|------|---------|
| 搜索摘要 | 博查 API | 每次 API 调用后 |
| 完整攻略 | 网页抓取 | 抓取高质量来源后 |

### 相似度配置

```python
# src/services/knowledge_service.py
SIMILARITY_THRESHOLD = 0.75  # 相似度阈值
MIN_RESULTS = 3              # 最少需要的结果数
```

### 节省效果

假设场景：
- 用户 A 规划 "北京4天3晚亲子游"
- 用户 B 规划 "北京5天4晚亲子游"

由于查询相似，用户 B 可以直接使用用户 A 的缓存结果，节省博查 API 调用。

---

## 5. 新增文件

### 数据库模型

| 文件 | 说明 |
|------|------|
| `src/db/models/activation_code.py` | 激活码模型 |
| `src/db/models/usage.py` | 使用记录模型 |

### 服务层

| 文件 | 说明 |
|------|------|
| `src/services/quota_service.py` | 配额管理服务 |
| `src/services/knowledge_service.py` | RAG 知识库服务 |

### API 路由

| 文件 | 说明 |
|------|------|
| `src/api/routes/admin.py` | 后台管理 API + 页面 |

### 数据库迁移

| 文件 | 说明 |
|------|------|
| `alembic/versions/002_user_quota.py` | 添加配额字段和新表 |

---

## 6. 修改文件

| 文件 | 修改内容 |
|------|---------|
| `src/db/models/user.py` | 添加 role、daily_quota、bonus_quota 字段 |
| `src/db/models/__init__.py` | 导出新模型 |
| `src/api/routes/__init__.py` | 导出 admin_router |
| `src/main.py` | 注册 admin 路由 |
| `src/graphs/nodes.py` | _search_web 集成 RAG |

---

## 7. 部署步骤

### 1. 运行数据库迁移

```bash
cd travelmind-main
alembic upgrade head
```

### 2. 创建管理员账号

```bash
# 方法1：直接 SQL
psql -U postgres -d travelmind -c "
  INSERT INTO users (id, phone, role, daily_quota)
  VALUES (gen_random_uuid(), '13800138000', 'admin', 999);
"

# 方法2：先注册再修改
# 1. 手机号登录注册
# 2. 修改数据库: UPDATE users SET role='admin' WHERE phone='13800138000';
```

### 3. 验证后台

1. 访问 `http://localhost:8000/api/v1/admin/`
2. 使用管理员手机号登录
3. 验证功能正常

---

## 8. API 变更

### 新增端点

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/admin/` | GET | 后台管理页面 |
| `/admin/users` | GET | 用户列表 |
| `/admin/users/{id}` | GET | 用户详情 |
| `/admin/users/{id}` | PUT | 更新用户 |
| `/admin/users/{id}/add-bonus` | POST | 增加临时次数 |
| `/admin/codes` | GET | 激活码列表 |
| `/admin/codes` | POST | 生成激活码 |
| `/admin/codes/{id}` | DELETE | 删除激活码 |
| `/admin/stats` | GET | 统计信息 |

### 权限要求

所有 `/admin/*` 端点需要管理员权限（role='admin'）

---

## 9. 前端集成（待实现）

### 激活码输入

```javascript
// 调用 API 使用激活码
const response = await fetch('/api/v1/auth/activate', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code: 'TRVL-XXXX-XXXX-XXXX' }),
});
```

### 配额显示

```javascript
// 获取当前配额信息
const response = await fetch('/api/v1/auth/quota', {
    headers: { 'Authorization': `Bearer ${token}` },
});
const { daily_quota, bonus_quota, used_today, remaining_today } = await response.json();
```

---

## 10. 测试建议

### 配额测试

1. 创建免费用户，验证每日 3 次限制
2. 使用激活码升级为付费用户，验证每日 20 次
3. 管理员增加临时次数，验证 bonus 生效
4. 第二天验证配额重置

### RAG 测试

1. 第一次搜索 "北京亲子游"，观察博查 API 调用
2. 第二次搜索类似内容，验证使用缓存
3. 检查 Chroma 数据目录是否有数据

### 后台测试

1. 管理员登录后台
2. 查看用户列表
3. 修改用户角色
4. 生成激活码
5. 查看统计信息
