# TravelMind Frontend

AI 智能旅行管家 - React 前端

## 技术栈

- **框架**: React 18 + Vite
- **状态管理**: Zustand
- **样式**: Tailwind CSS
- **地图**: @amap/amap-jsapi-loader (高德地图)
- **图标**: Lucide React

## 目录结构

```
src/
├── api/           # API 客户端
│   └── client.js  # 统一请求封装 + SSE 支持
├── components/
│   ├── chat/      # 聊天组件
│   ├── dashboard/ # 仪表盘组件 (行程时间轴)
│   ├── features/  # AI 功能卡片 (预算/行李/歌单等)
│   ├── map/       # 高德地图组件
│   ├── modals/    # Modal 组件
│   └── ui/        # 通用 UI 组件
├── hooks/         # 自定义 Hooks
│   ├── useStreamChat.js   # 流式聊天
│   └── useAiFeature.js    # AI 功能调用
├── store/         # Zustand 状态管理
│   └── useTravelStore.js
├── App.jsx        # 主应用
├── main.jsx       # 入口
└── index.css      # 全局样式
```

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入高德地图 Key
```

### 3. 启动开发服务器

```bash
npm run dev
```

前端运行在 http://localhost:3001，API 请求会代理到 http://localhost:8000

### 4. 构建生产版本

```bash
npm run build
```

## 功能清单

### 核心功能
- ✅ AI 对话 (SSE 流式响应)
- ✅ 行程时间轴
- ✅ 酒店/POI 推荐
- ✅ 高德地图集成 (Marker + Polyline)

### AI 助手功能
- ✅ 预算估算
- ✅ 智能行李清单
- ✅ 氛围歌单
- ✅ 紧急求助卡
- ✅ 文化锦囊
- ✅ 伴手礼指南
- ✅ 摄影挑战
- ✅ 每日攻略
- ✅ 旅行日记

### 详情功能
- ✅ 景点/酒店详情
- ✅ 讲故事
- ✅ 问路卡
- ✅ 房型预订 UI

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| VITE_API_BASE | 后端 API 地址 | 否 (默认 /api/v1) |
| VITE_AMAP_KEY | 高德地图 Web Key | 是 (地图功能) |
| VITE_AMAP_SECRET | 高德地图安全密钥 | 推荐 |

## 与后端集成

确保后端服务已启动：

```bash
# 在项目根目录
docker-compose up -d
```

后端 API 端点：
- `POST /api/v1/chat/stream` - 流式对话
- `POST /api/v1/assistants/*` - AI 助手功能
- `POST /api/v1/tools/*` - 工具调用
