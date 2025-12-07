# TravelMind API 文档

> 版本: v0.1.0  
> 基础路径: `http://localhost:8000/api/v1`  
> 在线文档: `http://localhost:8000/docs` (Swagger UI)

---

## 目录

1. [概述](#概述)
2. [通用说明](#通用说明)
3. [API 端点](#api-端点)
   - [健康检查](#1-健康检查)
   - [智能对话](#2-智能对话)
   - [流式对话](#3-流式对话)
   - [POI 搜索](#4-poi-搜索)
   - [天气查询](#5-天气查询)
   - [路线规划](#6-路线规划)
   - [网络搜索](#7-网络搜索)
4. [错误处理](#错误处理)
5. [数据类型](#数据类型)
6. [前端集成示例](#前端集成示例)

---

## 概述

TravelMind 是一个 AI 驱动的旅游规划助手 API，提供以下能力：

| 功能 | 描述 |
|------|------|
| 智能对话 | 与 AI 进行多轮对话，获取旅游规划建议 |
| POI 搜索 | 搜索景点、酒店、餐厅等地点信息 |
| 天气查询 | 获取目的地实时天气和预报 |
| 路线规划 | 计算两点之间的路线和时间 |
| 网络搜索 | 搜索旅游攻略和最新资讯 |

---

## 通用说明

### 请求格式

- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 响应格式

所有响应都包含以下基础字段：

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## API 端点

### 1. 健康检查

检查服务状态和配置。

**请求**

```
GET /api/v1/health
```

**响应**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "services": {
    "llm": "configured",
    "amap": "configured",
    "search": "configured",
    "langfuse": "configured"
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 服务状态: `healthy` |
| version | string | API 版本 |
| environment | string | 运行环境: `development` / `production` |
| services | object | 各服务配置状态 |

**前端用途**: 可用于检测后端服务是否正常运行。

---

### 2. 智能对话

与 AI 进行智能对话，获取旅游规划建议。

**请求**

```
POST /api/v1/chat
```

**请求体**

```json
{
  "message": "帮我规划一个杭州三日游，预算3000元",
  "session_id": "session_abc123"
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | ✅ | 用户消息，1-10000 字符 |
| session_id | string | ❌ | 会话ID，用于多轮对话。不传则自动生成 |

**响应**

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "response": "好的，以下是为您量身定制的杭州三日游详细旅游计划：\n\n## 🌟 行程概述\n\n- **目的地**：杭州市\n- **旅行时长**：3天\n...",
  "session_id": "session_abc123",
  "task_type": "travel_planning",
  "planning_phase": "completed",
  "has_plan": true,
  "metadata": {
    "collected_pois_count": 12
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| response | string | AI 回复内容（Markdown 格式） |
| session_id | string | 会话 ID，后续对话需传回 |
| task_type | string | 任务类型: `travel_planning` / `rental_search` / `general_qa` |
| planning_phase | string | 规划阶段: `understanding` / `researching` / `planning` / `completed` |
| has_plan | boolean | 是否已生成完整旅游计划 |
| metadata | object | 额外信息 |

**前端处理建议**:
- `response` 字段为 Markdown 格式，建议使用 Markdown 渲染库显示
- 保存 `session_id` 用于后续多轮对话
- 可根据 `planning_phase` 显示进度状态

---

### 3. 流式对话

使用 Server-Sent Events (SSE) 流式返回对话结果。

**请求**

```
POST /api/v1/chat/stream
```

**请求体**

```json
{
  "message": "帮我规划一个杭州三日游",
  "session_id": "session_abc123"
}
```

**响应格式**

```
Content-Type: text/event-stream

data: {"type": "start", "session_id": "session_abc123"}

data: {"type": "token", "content": "好的"}

data: {"type": "token", "content": "，以下是"}

data: {"type": "token", "content": "为您"}

data: {"type": "end", "response": "完整回复内容..."}

data: [DONE]
```

**事件类型**

| type | 说明 |
|------|------|
| start | 开始生成 |
| token | 增量文本片段 |
| node | 当前执行的节点 |
| end | 生成完成，包含完整响应 |
| error | 发生错误 |

**前端集成示例 (JavaScript)**

```javascript
const eventSource = new EventSource('/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: '帮我规划杭州三日游' })
});

// 使用 fetch + ReadableStream
async function streamChat(message) {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        
        const event = JSON.parse(data);
        if (event.type === 'token') {
          // 追加到显示区域
          appendText(event.content);
        }
      }
    }
  }
}
```

---

### 4. POI 搜索

搜索景点、酒店、餐厅等地点信息。

**请求**

```
POST /api/v1/tools/poi/search
```

**请求体**

```json
{
  "keywords": "西湖",
  "city": "杭州",
  "poi_type": "scenic",
  "page_size": 10
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keywords | string | ✅ | 搜索关键词，1-100 字符 |
| city | string | ✅ | 城市名称，1-50 字符 |
| poi_type | string | ❌ | POI 类型，见下表 |
| page_size | integer | ❌ | 返回数量，1-20，默认 10 |

**POI 类型**

| 值 | 说明 |
|------|------|
| scenic | 景点/旅游景区 |
| hotel | 酒店/住宿 |
| restaurant | 餐厅/美食 |
| shopping | 购物/商场 |
| null | 不限类型 |

**响应**

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "query": {
    "keywords": "西湖",
    "city": "杭州"
  },
  "count": 10,
  "results": [
    {
      "name": "西湖风景名胜区",
      "address": "浙江省杭州市西湖区龙井路1号",
      "type": "风景名胜",
      "rating": 4.8,
      "cost": 0,
      "tel": "0571-87179603",
      "city": "杭州市",
      "district": "西湖区",
      "location": {
        "lng": 120.148732,
        "lat": 30.242963
      }
    },
    {
      "name": "雷峰塔",
      "address": "浙江省杭州市西湖区南山路15号",
      "type": "风景名胜",
      "rating": 4.6,
      "cost": 40,
      "tel": "0571-87982111",
      "city": "杭州市",
      "district": "西湖区",
      "location": {
        "lng": 120.149208,
        "lat": 30.231657
      }
    }
  ]
}
```

**POI 结果字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 地点名称 |
| address | string | 详细地址 |
| type | string | 地点类型 |
| rating | number | 评分 (0-5)，可能为 null |
| cost | number | 参考价格（元），可能为 null |
| tel | string | 联系电话，可能为 null |
| city | string | 所在城市 |
| district | string | 所在区县 |
| location | object | 经纬度坐标 |
| location.lng | number | 经度 |
| location.lat | number | 纬度 |

---

### 5. 天气查询

获取城市实时天气和天气预报。

**请求**

```
POST /api/v1/tools/weather
```

**请求体**

```json
{
  "city": "杭州",
  "forecast": true
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | ✅ | 城市名称，1-50 字符 |
| forecast | boolean | ❌ | 是否获取预报，默认 false |

**响应（实时天气）**

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "city": "杭州",
  "weather": "晴",
  "temperature": "18",
  "humidity": "65",
  "wind": "东北风 2级",
  "forecasts": null
}
```

**响应（含预报）**

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "city": "杭州",
  "weather": "晴",
  "temperature": "18",
  "humidity": "65",
  "wind": "东北风 2级",
  "forecasts": [
    {
      "date": "2025-12-05",
      "week": "星期五",
      "dayweather": "晴",
      "nightweather": "多云",
      "daytemp": "20",
      "nighttemp": "10",
      "daywind": "东北",
      "nightwind": "东北",
      "daypower": "≤3",
      "nightpower": "≤3"
    },
    {
      "date": "2025-12-06",
      "week": "星期六",
      "dayweather": "多云",
      "nightweather": "小雨",
      "daytemp": "18",
      "nighttemp": "12",
      "daywind": "东",
      "nightwind": "东",
      "daypower": "≤3",
      "nightpower": "≤3"
    }
  ]
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| city | string | 城市名称 |
| weather | string | 当前天气状况 |
| temperature | string | 当前温度（摄氏度） |
| humidity | string | 湿度百分比 |
| wind | string | 风向和风力 |
| forecasts | array | 未来几天天气预报（可选） |

---

### 6. 路线规划

计算两点之间的路线和预计时间。

**请求**

```
POST /api/v1/tools/route
```

**请求体**

```json
{
  "origin_lng": 120.148732,
  "origin_lat": 30.242963,
  "dest_lng": 120.149208,
  "dest_lat": 30.231657,
  "mode": "walking"
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| origin_lng | number | ✅ | 起点经度 |
| origin_lat | number | ✅ | 起点纬度 |
| dest_lng | number | ✅ | 终点经度 |
| dest_lat | number | ✅ | 终点纬度 |
| mode | string | ❌ | 出行方式，默认 `driving` |

**出行方式**

| 值 | 说明 |
|------|------|
| driving | 驾车 |
| walking | 步行 |
| transit | 公共交通 |

**响应**

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "origin": {
    "lng": 120.148732,
    "lat": 30.242963
  },
  "destination": {
    "lng": 120.149208,
    "lat": 30.231657
  },
  "mode": "walking",
  "distance_km": 1.26,
  "duration_min": 18,
  "steps": [
    {
      "instruction": "向南步行100米",
      "distance": "100米",
      "duration": "2分钟"
    },
    {
      "instruction": "左转进入南山路",
      "distance": "800米",
      "duration": "10分钟"
    }
  ]
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| origin | object | 起点坐标 |
| destination | object | 终点坐标 |
| mode | string | 出行方式 |
| distance_km | number | 距离（公里） |
| duration_min | integer | 预计时间（分钟） |
| steps | array | 导航步骤（可选） |

---

### 7. 网络搜索

搜索旅游攻略和最新资讯。

**请求**

```
POST /api/v1/tools/search
```

**请求体**

```json
{
  "query": "杭州旅游攻略 2025",
  "count": 5,
  "freshness": "month"
}
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 搜索关键词，1-200 字符 |
| count | integer | ❌ | 返回数量，1-10，默认 5 |
| freshness | string | ❌ | 时效性过滤 |

**时效性选项**

| 值 | 说明 |
|------|------|
| day | 24小时内 |
| week | 一周内 |
| month | 一个月内 |
| null | 不限 |

**响应**

```json
{
  "success": true,
  "message": "OK",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "query": "杭州旅游攻略 2025",
  "count": 5,
  "results": [
    {
      "title": "2025杭州旅游全攻略：西湖、灵隐寺、宋城一网打尽",
      "url": "https://example.com/hangzhou-guide-2025",
      "snippet": "本文为您详细介绍杭州必去景点、美食推荐、住宿建议...",
      "source": "旅游网",
      "date": "2025-12-01"
    },
    {
      "title": "杭州三日游最佳路线推荐",
      "url": "https://example.com/hangzhou-3days",
      "snippet": "第一天：西湖景区，第二天：灵隐寺+西溪湿地...",
      "source": "携程攻略",
      "date": "2025-11-28"
    }
  ]
}
```

**搜索结果字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 文章标题 |
| url | string | 文章链接 |
| snippet | string | 内容摘要 |
| source | string | 来源网站（可能为 null） |
| date | string | 发布日期（可能为 null） |

---

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "message": "Error description",
  "timestamp": "2025-12-05T15:30:00.000Z",
  "error_code": "INVALID_PARAMETER",
  "detail": "详细错误信息"
}
```

### 常见错误码

| HTTP 状态码 | 错误类型 | 说明 |
|------------|----------|------|
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在（如城市天气未找到） |
| 500 | Internal Server Error | 服务器内部错误 |

### 前端错误处理建议

```javascript
async function callApi(endpoint, data) {
  try {
    const response = await fetch(`/api/v1${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (!response.ok || !result.success) {
      throw new Error(result.detail || result.message || '请求失败');
    }
    
    return result;
  } catch (error) {
    console.error('API Error:', error);
    // 显示错误提示
    showToast(error.message);
    throw error;
  }
}
```

---

## 数据类型

### TypeScript 类型定义

```typescript
// 基础响应
interface BaseResponse {
  success: boolean;
  message: string;
  timestamp: string;
}

// 聊天请求
interface ChatRequest {
  message: string;
  session_id?: string;
}

// 聊天响应
interface ChatResponse extends BaseResponse {
  response: string;
  session_id: string;
  task_type?: 'travel_planning' | 'rental_search' | 'general_qa';
  planning_phase?: 'understanding' | 'researching' | 'planning' | 'completed';
  has_plan: boolean;
  metadata?: {
    collected_pois_count?: number;
  };
}

// POI 搜索请求
interface POISearchRequest {
  keywords: string;
  city: string;
  poi_type?: 'scenic' | 'hotel' | 'restaurant' | 'shopping';
  page_size?: number;
}

// POI 项目
interface POIItem {
  name: string;
  address: string;
  type: string;
  rating?: number;
  cost?: number;
  tel?: string;
  city?: string;
  district?: string;
  location?: {
    lng: number;
    lat: number;
  };
}

// POI 搜索响应
interface POISearchResponse extends BaseResponse {
  query: { keywords: string; city: string };
  count: number;
  results: POIItem[];
}

// 天气请求
interface WeatherRequest {
  city: string;
  forecast?: boolean;
}

// 天气预报项
interface ForecastItem {
  date: string;
  week: string;
  dayweather: string;
  nightweather: string;
  daytemp: string;
  nighttemp: string;
  daywind: string;
  nightwind: string;
  daypower: string;
  nightpower: string;
}

// 天气响应
interface WeatherResponse extends BaseResponse {
  city: string;
  weather?: string;
  temperature?: string;
  humidity?: string;
  wind?: string;
  forecasts?: ForecastItem[];
}

// 路线请求
interface RouteRequest {
  origin_lng: number;
  origin_lat: number;
  dest_lng: number;
  dest_lat: number;
  mode?: 'driving' | 'walking' | 'transit';
}

// 路线响应
interface RouteResponse extends BaseResponse {
  origin: { lng: number; lat: number };
  destination: { lng: number; lat: number };
  mode: string;
  distance_km: number;
  duration_min: number;
  steps?: Array<{
    instruction: string;
    distance: string;
    duration: string;
  }>;
}

// 网络搜索请求
interface WebSearchRequest {
  query: string;
  count?: number;
  freshness?: 'day' | 'week' | 'month';
}

// 搜索结果项
interface SearchResultItem {
  title: string;
  url: string;
  snippet: string;
  source?: string;
  date?: string;
}

// 网络搜索响应
interface WebSearchResponse extends BaseResponse {
  query: string;
  count: number;
  results: SearchResultItem[];
}

// 健康检查响应
interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
  services: {
    llm: 'configured' | 'not_configured';
    amap: 'configured' | 'not_configured';
    search: 'configured' | 'not_configured';
    langfuse: 'configured' | 'not_configured';
  };
}
```

---

## 前端集成示例

### API 封装

```typescript
// api/index.ts
const API_BASE = '/api/v1';

export const api = {
  // 健康检查
  async health(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },
  
  // 智能对话
  async chat(message: string, sessionId?: string): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    return res.json();
  },
  
  // 流式对话
  async *chatStream(message: string, sessionId?: string) {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const text = decoder.decode(value);
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          yield JSON.parse(line.slice(6));
        }
      }
    }
  },
  
  // POI 搜索
  async searchPOI(params: POISearchRequest): Promise<POISearchResponse> {
    const res = await fetch(`${API_BASE}/tools/poi/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },
  
  // 天气查询
  async getWeather(city: string, forecast = false): Promise<WeatherResponse> {
    const res = await fetch(`${API_BASE}/tools/weather`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, forecast })
    });
    return res.json();
  },
  
  // 路线规划
  async getRoute(params: RouteRequest): Promise<RouteResponse> {
    const res = await fetch(`${API_BASE}/tools/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },
  
  // 网络搜索
  async search(query: string, count = 5): Promise<WebSearchResponse> {
    const res = await fetch(`${API_BASE}/tools/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, count })
    });
    return res.json();
  }
};
```

### React 使用示例

```tsx
// components/Chat.tsx
import { useState, useRef } from 'react';
import { api } from '../api';
import ReactMarkdown from 'react-markdown';

export function Chat() {
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const sessionId = useRef<string>();
  
  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);
    
    try {
      // 流式响应
      let assistantContent = '';
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
      
      for await (const event of api.chatStream(userMessage, sessionId.current)) {
        if (event.type === 'token') {
          assistantContent += event.content;
          setMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].content = assistantContent;
            return newMessages;
          });
        } else if (event.type === 'end') {
          sessionId.current = event.session_id;
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.role === 'assistant' ? (
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            ) : (
              msg.content
            )}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="输入您的旅游规划需求..."
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? '思考中...' : '发送'}
        </button>
      </div>
    </div>
  );
}
```

---

## 附录

### CORS 配置

API 默认允许以下跨域来源：
- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

如需添加其他来源，请修改后端配置。

### 速率限制

当前版本暂无速率限制，生产环境部署时建议配置。

### 在线测试

启动服务后，访问 `http://localhost:8000/docs` 可使用 Swagger UI 在线测试所有 API。
