# TravelMind 项目分析报告

## 1. 项目数据流（现有）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              前端（React + Zustand）                     │
│                                                                          │
│  用户输入 → sendMessage() → chatApi.stream("/chat/stream")              │
│                                      │                                   │
│                                      ↓                                   │
│            ┌─────────────────────────────────────────┐                  │
│            │ SSE 事件流:                              │                  │
│            │ - start: {session_id}                   │                  │
│            │ - token: {content}                      │                  │
│            │ - end: {itinerary, pois, weather, ...}  │                  │
│            └─────────────────────────────────────────┘                  │
│                                      │                                   │
│                                      ↓                                   │
│            setItinerary(itinerary)  ← 存储在内存，刷新丢失              │
│            setPois(pois)                                                 │
│            setWeather(weather)                                           │
│                                                                          │
│  localStorage 只保存: {destination, sessionId}                          │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                              后端（FastAPI）                             │
│                                                                          │
│  /chat/stream → stream_travel_agent() → LangGraph 工作流                │
│                                              │                           │
│        ┌─────────────────────────────────────┼─────────────────────────┐│
│        │                                     ↓                          ││
│        │ understand_intent_node → research_node → planning_node        ││
│        │                                     ↓                          ││
│        │                              respond_node                      ││
│        │                                     │                          ││
│        │                    返回: travel_plan, itinerary, ...          ││
│        └────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  checkpointer（MemorySaver/RedisSaver）:                                │
│  - 存储对话状态（messages, travel_preference 等）                        │
│  - 不存储生成的 itinerary                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. 当前问题

| 问题 | 原因 | 影响 |
|------|------|------|
| 刷新页面行程丢失 | `itinerary` 只在前端内存，不持久化 | 用户体验差 |
| 无法区分用户 | 没有用户系统 | 无法保存用户偏好 |
| 会话依赖 session_id | LangGraph checkpointer 只存对话状态 | 行程数据无法恢复 |

## 3. 现有的预算计算

有**两套预算系统**：

### 3.1 LLM 估算 (`/assistants/budget`)
- 文件: `src/services/assistants.py` → `estimate_budget()`
- 功能: 根据目的地和天数，LLM 给出粗略范围（如 "3000-5000 元"）
- 前端调用: `assistantsApi.getBudget()`

### 3.2 规则计算 (`/sidebar/budget`)
- 文件: `src/services/sidebar.py` → `calculate_budget_breakdown()`
- 功能: 基于 `itinerary` 数据计算精确预算
- 前端调用: **前端自行计算**（因为有 `itinerary` 数据）

## 4. 现有的住宿逻辑

### 后端处理（planning_node）
- 第 1038-1078 行: 填充真实酒店数据
- 根据 `stay_same_tomorrow` 判断是否换酒店

### 前端处理（ItineraryTimeline.jsx）
- 第 233-264 行: 智能判断是否换酒店
- 第 266-288 行: 显示行李处理提示

**结论**: 住宿逻辑已在前端完整实现，后端只提供数据。

## 5. 我创建的代码评估

| 文件/模块 | 评估 | 决定 |
|----------|------|------|
| `src/db/` | ✅ 合理，需要数据库存储行程 | 保留 |
| `src/db/models/` | ✅ 模型设计合理 | 保留 |
| `src/db/repositories/` | ✅ Repository 模式合理 | 保留 |
| `src/auth/jwt.py` | ✅ JWT 实现标准 | 保留 |
| `src/auth/deps.py` | ✅ FastAPI 依赖合理 | 保留 |
| `src/auth/sms.py` | ✅ 短信服务合理 | 保留 |
| `src/cache/` | ✅ Redis + 内存降级合理 | 保留 |
| `src/api/routes/auth.py` | ✅ 认证 API 合理 | 保留 |
| `src/api/routes/trips.py` | ✅ 行程 API 合理 | 保留 |
| `src/services/budget_calculator.py` | ❌ 与 sidebar.py 重复 | **删除** |
| `src/services/accommodation_logic.py` | ❌ 与前端重复 | **删除** |
| `src/services/trip_service.py` | ⚠️ 概念合理但集成方式错误 | 修改 |
| `nodes.py` 中的集成 | ❌ 不应该修改核心工作流 | **已撤销** |

## 6. 正确的集成方案

### 6.1 保存行程（不修改 planning_node）

**方案**: 在 API 层面保存，不修改 LangGraph 工作流

```python
# src/api/routes.py - 修改 chat_stream 函数

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    identity: CurrentIdentity = Depends(get_current_identity_optional),  # 可选认证
):
    async def generate():
        trip_id = None
        
        async for event in stream_travel_agent(...):
            yield f"data: {json.dumps(event)}\n\n"
            
            # 在 end 事件时保存行程
            if event.get("type") == "end" and event.get("itinerary"):
                trip_id = await save_trip_to_db(
                    event, 
                    user_id=identity.user.id if identity.is_registered else None,
                    guest_id=identity.guest.id if identity.is_guest else None,
                )
                # 将 trip_id 添加到响应
                yield f"data: {json.dumps({'type': 'saved', 'trip_id': trip_id})}\n\n"
```

### 6.2 恢复行程

**方案**: 添加新 API，前端启动时调用

```python
# src/api/routes/trips.py

@router.get("/trips/latest")
async def get_latest_trip(identity: CurrentIdentity = Depends(require_auth)):
    """获取最新行程，用于刷新后恢复"""
    ...
```

前端修改:
```javascript
// App.jsx 或 main.jsx
useEffect(() => {
    // 启动时尝试恢复行程
    const token = localStorage.getItem('token');
    if (token) {
        fetch('/api/v1/trips/latest', { headers: { Authorization: `Bearer ${token}` }})
            .then(res => res.json())
            .then(data => {
                if (data.itinerary) {
                    setItinerary(data.itinerary);
                }
            });
    }
}, []);
```

### 6.3 认证流程

```
┌──────────────────────────────────────────────────────────┐
│                        游客模式                           │
├──────────────────────────────────────────────────────────┤
│ 1. 前端生成设备指纹                                       │
│ 2. 调用 POST /auth/guest                                 │
│ 3. 获取 guest_token                                      │
│ 4. 后续请求携带 Authorization: Bearer {guest_token}       │
│ 5. 行程绑定到 guest_id                                   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                       登录模式                            │
├──────────────────────────────────────────────────────────┤
│ 1. 用户输入手机号                                         │
│ 2. 调用 POST /auth/sms/send 发送验证码                   │
│ 3. 调用 POST /auth/sms/verify 验证并登录                 │
│ 4. 获取 access_token + refresh_token                     │
│ 5. 后续请求携带 Authorization: Bearer {access_token}      │
│ 6. 行程绑定到 user_id                                    │
│ 7. 游客行程可迁移到用户账号                               │
└──────────────────────────────────────────────────────────┘
```

## 7. 安全性评估

| 方面 | 当前实现 | 评估 | 建议 |
|------|---------|------|------|
| JWT 密钥 | 从环境变量读取 | ✅ 正确 | 生产环境使用强密钥 |
| 密码存储 | 无密码（短信验证） | ✅ 安全 | - |
| Token 过期 | access_token 60分钟 | ✅ 合理 | - |
| 短信验证码 | 5分钟过期，60秒发送间隔 | ✅ 合理 | 添加每日发送次数限制 |
| API 限流 | 游客10次/分钟，用户30次/分钟 | ✅ 合理 | - |
| SQL 注入 | SQLAlchemy ORM | ✅ 安全 | - |
| XSS | 前端 React 自动转义 | ✅ 安全 | - |

## 8. 下一步行动

1. **删除冗余代码**：
   - `src/services/budget_calculator.py`
   - `src/services/accommodation_logic.py`

2. **修改 API 集成**：
   - 在 `/chat/stream` 中添加保存逻辑（而非 planning_node）
   - 保持原有工作流不变

3. **更新前端**：
   - 添加登录/注册页面
   - 添加 Token 管理
   - 启动时恢复行程

4. **端到端测试**：
   - 完整流程测试（注册 → 对话 → 生成行程 → 刷新 → 恢复）
   - 游客模式测试
   - 边界情况测试
