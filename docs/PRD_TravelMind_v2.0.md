# TravelMind v2.0 产品需求文档 (PRD)

## 版本信息
- **版本**: v2.0
- **日期**: 2025-12-08
- **状态**: 需求确认

---

## 一、需求概览

### 1.1 核心改进目标

| 模块 | 当前问题 | 改进目标 |
|------|----------|----------|
| 海报生成 | 天数显示错误、无背景图 | 数据同步修复、添加地标图片 |
| 住宿推荐 | 独立于行程、价格过高 | 整合进行程、基于预算筛选 |
| 交通规划 | 时间来源不明 | 基于住宿位置实际计算 |
| UI布局 | 右侧40%空间空旷 | 新增智囊侧边栏 |
| 图片展示 | 景点/酒店无图片 | 添加真实图片 |

### 1.2 优先级排序

| 优先级 | 功能 | 原因 |
|--------|------|------|
| P0 | 海报天数 Bug 修复 | 数据错误，影响用户体验 |
| P1 | 住宿整合进行程 | 核心功能缺失 |
| P1 | 交通时间真实计算 | 数据准确性 |
| P1 | 住宿预算匹配 | 推荐不合理 |
| P2 | 智囊侧边栏 | 体验提升 |
| P2 | 图片系统 | 视觉优化 |

---

## 二、功能详细设计

### 2.1 住宿与行程整合

#### 2.1.1 用户选择入口

在用户输入旅行需求后，或在设置中提供选项：

```
┌─────────────────────────────────────────────────┐
│  🏨 住宿偏好设置                                 │
├─────────────────────────────────────────────────┤
│  ○ 全程同一酒店                                  │
│    推荐住在市中心，方便往返各景点                  │
│                                                 │
│  ○ 跟随行程换酒店                                │
│    根据每天行程推荐最近的酒店，节省交通时间         │
│                                                 │
│  ● 智能推荐（默认）                              │
│    AI 根据景点距离和交通便利性自动判断             │
└─────────────────────────────────────────────────┘
```

#### 2.1.2 智能判断逻辑

```python
def should_change_hotel(current_hotel_location, next_day_attractions):
    """
    判断是否需要换酒店
    
    规则：
    1. 如果第二天第一个景点距离当前酒店 > 15km，建议换酒店
    2. 如果第二天是主题公园（环球影城、迪士尼），强烈建议住在附近
    3. 如果连续两天都在同一区域，保持同一酒店
    """
    first_attraction = next_day_attractions[0]
    distance = calculate_distance(current_hotel_location, first_attraction.location)
    
    # 主题公园特殊处理
    if is_theme_park(first_attraction):
        return {
            "should_change": True,
            "reason": "建议入住环球影城/迪士尼周边酒店，方便早入园",
            "priority": "high"
        }
    
    # 距离判断
    if distance > 15:  # km
        return {
            "should_change": True,
            "reason": f"明日首个景点距离酒店{distance}km，建议换到附近酒店",
            "priority": "medium"
        }
    
    return {"should_change": False}
```

#### 2.1.3 行程中的住宿展示

```
Day 1 故宫中轴线深度游
├── 09:00 故宫博物院
├── 14:00 景山公园  
├── 17:00 天安门广场
└── 🏨 19:30 入住：如家酒店(王府井店) ¥258/晚
              距明日首站：地铁3站，约15分钟

Day 2 北京环球影城欢乐之旅
├── ⚠️ 建议换酒店：环球影城距王府井约25km
│   推荐：环球影城大酒店 ¥899/晚（步行5分钟入园）
│   或：通州万达嘉华 ¥368/晚（地铁2站）
├── 09:00 北京环球影城（全天）
└── 🏨 21:00 入住：[用户选择的酒店]

Day 3 皇家园林之旅  
├── ⚠️ 建议换回市区酒店（明日景点在市区）
├── 09:00 颐和园
└── 🏨 18:00 入住：如家酒店(西直门店) ¥268/晚
```

#### 2.1.4 住宿推荐数据流

```
用户输入行程需求
       ↓
生成每日景点行程
       ↓
┌──────────────────────────────────────┐
│ 对每一天进行住宿分析：                  │
│ 1. 获取当天最后一个景点位置             │
│ 2. 获取第二天第一个景点位置             │
│ 3. 判断是否需要换酒店                  │
│ 4. 搜索目标区域酒店（基于预算）          │
│ 5. 计算交通时间                       │
└──────────────────────────────────────┘
       ↓
输出：行程 + 住宿 + 交通时间
```

---

### 2.2 住宿预算匹配

#### 2.2.1 预算等级定义

| 等级 | 每晚预算 | 酒店类型 | 关键词 |
|------|----------|----------|--------|
| 经济型 | ¥100-200 | 快捷酒店、青旅 | 如家、汉庭、7天 |
| 中等（默认） | ¥200-400 | 舒适型酒店 | 全季、亚朵、维也纳 |
| 舒适型 | ¥400-800 | 高档酒店 | 希尔顿、万豪、洲际 |
| 豪华型 | ¥800+ | 奢华酒店 | 四季、半岛、安缦 |

#### 2.2.2 预算提取逻辑

```python
def extract_budget_level(user_input, total_budget=None, days=None):
    """
    从用户输入中提取住宿预算等级
    """
    # 1. 用户明确说明
    if "经济" in user_input or "省钱" in user_input or "穷游" in user_input:
        return "economy"
    if "豪华" in user_input or "高端" in user_input or "五星" in user_input:
        return "luxury"
    
    # 2. 从总预算推算
    if total_budget and days:
        # 假设住宿占总预算的 30-40%
        accommodation_budget = total_budget * 0.35
        per_night = accommodation_budget / (days - 1)  # n天n-1晚
        
        if per_night < 200:
            return "economy"
        elif per_night < 400:
            return "moderate"  # 默认
        elif per_night < 800:
            return "comfortable"
        else:
            return "luxury"
    
    # 3. 默认中等预算
    return "moderate"
```

#### 2.2.3 攻略中的住宿提取

从搜索到的 UGC 攻略中提取住宿推荐：

```python
async def extract_hotels_from_guides(guides: list, destination: str) -> list:
    """
    从攻略中提取住宿推荐
    """
    hotel_mentions = []
    
    # 关键词匹配
    hotel_patterns = [
        r"住在(.{2,10}酒店)",
        r"推荐(.{2,10}民宿)",
        r"入住(.{2,10})",
        r"酒店推荐[：:]\s*(.+)",
        r"住宿[：:]\s*(.+)",
    ]
    
    for guide in guides:
        content = guide.get("content", "")
        for pattern in hotel_patterns:
            matches = re.findall(pattern, content)
            hotel_mentions.extend(matches)
    
    # 去重并验证（通过高德 POI 搜索确认存在）
    verified_hotels = []
    for hotel_name in set(hotel_mentions):
        poi_result = await search_poi(keywords=hotel_name, city=destination, poi_type="hotel")
        if poi_result.get("results"):
            verified_hotels.append(poi_result["results"][0])
    
    return verified_hotels
```

---

### 2.3 交通时间真实计算

#### 2.3.1 计算时机

在生成行程时，对每个景点间的交通进行实际计算：

```python
async def calculate_route_between_activities(
    from_location: tuple,  # (lng, lat)
    to_location: tuple,
    from_name: str,
    to_name: str,
) -> dict:
    """
    计算两点间的实际交通信息
    """
    # 调用高德路线规划 API
    route_result = await get_route(
        origin_lng=from_location[0],
        origin_lat=from_location[1],
        dest_lng=to_location[0],
        dest_lat=to_location[1],
        mode="transit"  # 公共交通
    )
    
    return {
        "from": from_name,
        "to": to_name,
        "distance_km": route_result["distance_km"],
        "duration_min": route_result["duration_min"],
        "route_desc": route_result.get("description", ""),  # 如"地铁1号线→换乘4号线"
        "steps": route_result.get("steps", []),
    }
```

#### 2.3.2 展示格式

```
Day 2 北京环球影城欢乐之旅

🏨 从 如家酒店(王府井店) 出发
   ↓ 🚇 地铁1号线→7号线→八通线，约55分钟，7.5km
   
09:00 北京环球影城
      全天游玩，建议提前购买门票
   ↓ 🚶 步行，约5分钟
   
21:00 返回酒店
```

---

### 2.4 图片系统设计

#### 2.4.1 图片来源优先级

```
热门城市（北京、上海、杭州、成都等 Top 30）
    ↓
预设高质量图片（本地存储/CDN）
    ↓ 如果没有
搜索引擎图片 API（谷歌图片搜索）
    ↓ 如果失败或无合适图片
Unsplash API
    ↓ 如果失败
AI 生成（最后手段，成本高）
    ↓ 如果都失败
默认占位图
```

#### 2.4.2 热门城市图片预设

```javascript
// frontend/src/assets/cityImages.js
export const CITY_IMAGES = {
  // 一线城市
  "北京": {
    landmark: "/images/cities/beijing-landmark.jpg",  // 天安门/故宫
    poster_bg: "/images/cities/beijing-poster.jpg",
    thumbnail: "/images/cities/beijing-thumb.jpg",
  },
  "上海": {
    landmark: "/images/cities/shanghai-landmark.jpg",  // 外滩
    poster_bg: "/images/cities/shanghai-poster.jpg",
    thumbnail: "/images/cities/shanghai-thumb.jpg",
  },
  // ... 其他热门城市
  
  // 默认
  "_default": {
    landmark: "/images/cities/default-landmark.jpg",
    poster_bg: "/images/cities/default-poster.jpg",
    thumbnail: "/images/cities/default-thumb.jpg",
  }
};

export function getCityImage(cityName, type = "landmark") {
  return CITY_IMAGES[cityName]?.[type] || CITY_IMAGES["_default"][type];
}
```

#### 2.4.3 动态图片获取（备选方案）

```python
# backend: src/services/image_service.py

async def get_destination_image(destination: str, image_type: str = "landmark") -> str:
    """
    获取目的地图片 URL
    
    优先级：预设 > 必应搜索 > Unsplash > 默认图
    """
    # 1. 检查预设图片
    preset_url = get_preset_image(destination, image_type)
    if preset_url:
        return preset_url
    
    # 2. 必应图片搜索
    try:
        bing_result = await bing_image_search(f"{destination} 地标 风景")
        if bing_result:
            return bing_result[0]["url"]
    except Exception as e:
        logger.warning(f"Bing image search failed: {e}")
    
    # 3. Unsplash
    try:
        unsplash_result = await unsplash_search(destination)
        if unsplash_result:
            return unsplash_result["urls"]["regular"]
    except Exception as e:
        logger.warning(f"Unsplash search failed: {e}")
    
    # 4. 返回默认图
    return DEFAULT_IMAGES[image_type]
```

#### 2.4.4 景点图片

景点图片优先使用高德 POI 返回的 `photos` 字段：

```python
# 在 planning_node 中
for activity in day["activities"]:
    # 搜索景点 POI 获取图片
    poi_result = await search_poi(
        keywords=activity["title"],
        city=destination,
        poi_type="tourism",
        page_size=1
    )
    if poi_result.get("results"):
        poi = poi_result["results"][0]
        activity["image"] = poi.get("photos", [None])[0]
        activity["location"] = poi.get("location")
```

---

### 2.5 智囊侧边栏 (Smart Sidebar)

#### 2.5.1 布局设计

```
┌──────────────────────────────────────────────────────────────────┐
│  TravelMind                          北京 之旅  [CREATED]        │
├──────────────┬───────────────────────────────┬───────────────────┤
│              │                               │ 🗺️ 迷你地图        │
│   聊天区域    │       行程规划                 │  [Day 1 景点标记]  │
│              │                               │                   │
│   (25%)      │       (45%)                   ├───────────────────┤
│              │                               │ 🌡️ 天气趋势        │
│              │                               │  今天 5°C 晴       │
│              │                               │  明天 3°C 多云     │
│              │                               │  后天 -1°C 小雪    │
│              │                               ├───────────────────┤
│              │                               │ 📰 当地资讯        │
│              │                               │  · 故宫周一闭馆    │
│              │                               │  · 环球影城新活动  │
│              │                               ├───────────────────┤
│              │                               │ 📊 预算仪表盘      │
│              │                               │  总预算: ¥5000    │
│              │                               │  ████████░░ 68%   │
│              │                               │  住宿: ¥1200      │
│              │                               │  门票: ¥800       │
│              │                               │  交通: ¥400       │
│              │                               │  餐饮: ¥1000      │
│              │                               │  剩余: ¥1600      │
└──────────────┴───────────────────────────────┴───────────────────┘
```

#### 2.5.2 响应式设计

| 屏幕宽度 | 布局 |
|----------|------|
| ≥ 1440px | 三栏：聊天(25%) + 行程(45%) + 侧边栏(30%) |
| 1024-1439px | 两栏：聊天+行程(100%)，侧边栏收起为图标 |
| < 1024px | 单栏：Tab 切换 |

#### 2.5.3 侧边栏组件设计

```jsx
// frontend/src/components/sidebar/SmartSidebar.jsx

const SmartSidebar = ({ destination, itinerary, budget }) => {
  return (
    <aside className="smart-sidebar">
      {/* 迷你地图 */}
      <MiniMap 
        destination={destination}
        markers={getCurrentDayMarkers(itinerary)}
      />
      
      {/* 天气趋势 */}
      <WeatherTrend 
        city={destination}
        days={5}
      />
      
      {/* 当地资讯 */}
      <LocalNews 
        city={destination}
        categories={["景点", "活动", "交通"]}
      />
      
      {/* 预算仪表盘 */}
      <BudgetDashboard 
        totalBudget={budget.total}
        breakdown={budget.breakdown}
        spent={budget.spent}
      />
    </aside>
  );
};
```

#### 2.5.4 迷你地图功能

```jsx
// frontend/src/components/sidebar/MiniMap.jsx

const MiniMap = ({ destination, markers, selectedDay }) => {
  // 功能：
  // 1. 显示当天所有景点标记
  // 2. 点击标记显示景点名称
  // 3. 显示景点间的路线
  // 4. 点击切换天数
  
  return (
    <div className="mini-map-container">
      <div className="map-header">
        <span>🗺️ 行程地图</span>
        <DaySelector 
          days={totalDays}
          selected={selectedDay}
          onChange={setSelectedDay}
        />
      </div>
      <AMapComponent
        center={destination}
        zoom={12}
        markers={markers}
        showRoute={true}
        style={{ height: '200px' }}
      />
    </div>
  );
};
```

#### 2.5.5 预算仪表盘

```jsx
// frontend/src/components/sidebar/BudgetDashboard.jsx

const BudgetDashboard = ({ totalBudget, breakdown, actualSpent }) => {
  const categories = [
    { key: "accommodation", label: "住宿", icon: "🏨", color: "#4F46E5" },
    { key: "tickets", label: "门票", icon: "🎫", color: "#10B981" },
    { key: "transport", label: "交通", icon: "🚇", color: "#F59E0B" },
    { key: "food", label: "餐饮", icon: "🍜", color: "#EF4444" },
    { key: "shopping", label: "购物", icon: "🛍️", color: "#8B5CF6" },
  ];
  
  const totalEstimated = Object.values(breakdown).reduce((a, b) => a + b, 0);
  const percentage = Math.round((totalEstimated / totalBudget) * 100);
  
  return (
    <div className="budget-dashboard">
      <div className="budget-header">
        <span>📊 预算仪表盘</span>
        <span className="total">总预算: ¥{totalBudget}</span>
      </div>
      
      {/* 进度条 */}
      <div className="budget-progress">
        <div 
          className="progress-bar"
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
        <span>{percentage}%</span>
      </div>
      
      {/* 分类明细 */}
      <div className="budget-breakdown">
        {categories.map(cat => (
          <div key={cat.key} className="budget-item">
            <span>{cat.icon} {cat.label}</span>
            <span>¥{breakdown[cat.key] || 0}</span>
          </div>
        ))}
      </div>
      
      {/* 剩余预算 */}
      <div className="budget-remaining">
        剩余: ¥{totalBudget - totalEstimated}
      </div>
    </div>
  );
};
```

#### 2.5.6 当地资讯获取

```python
# backend: src/services/local_news.py

async def get_local_news(city: str) -> list:
    """
    获取目的地实时资讯
    """
    queries = [
        f"{city} 景点 最新消息",
        f"{city} 旅游 活动",
        f"{city} 交通 管制",
    ]
    
    news_items = []
    for query in queries:
        results = await web_search(query=query, count=3, freshness="week")
        for r in results.get("results", []):
            news_items.append({
                "title": r["title"][:30] + "..." if len(r["title"]) > 30 else r["title"],
                "url": r["url"],
                "source": r.get("source", ""),
                "date": r.get("date", ""),
            })
    
    # 去重并限制数量
    seen = set()
    unique_news = []
    for item in news_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique_news.append(item)
    
    return unique_news[:5]
```

---

### 2.6 海报修复

#### 2.6.1 数据同步修复

```jsx
// 确保海报组件使用正确的数据源

const SharePoster = ({ itinerary, destination, travelStyle, budget }) => {
  // 从 itinerary 计算实际天数
  const actualDays = itinerary?.length || 0;
  const actualNights = actualDays > 0 ? actualDays - 1 : 0;
  
  // 提取主要景点（每天第一个）
  const highlights = itinerary?.map(day => 
    day.activities?.[0]?.title
  ).filter(Boolean).slice(0, 3);
  
  return (
    <div className="poster" style={{ backgroundImage: `url(${getCityImage(destination, 'poster_bg')})` }}>
      <h1>{destination}</h1>
      <p>{actualDays}天{actualNights}晚 {travelStyle || '深度游'}</p>
      
      <ul>
        {highlights.map((h, i) => <li key={i}>{h}</li>)}
      </ul>
      
      <footer>
        <span>Generated by TravelMind</span>
        <span>Budget Est. ¥{budget}</span>
      </footer>
    </div>
  );
};
```

#### 2.6.2 海报背景图

使用目的地地标图片作为背景：

```jsx
const posterStyle = {
  backgroundImage: `
    linear-gradient(
      to bottom,
      rgba(88, 28, 135, 0.8),
      rgba(88, 28, 135, 0.95)
    ),
    url(${getCityImage(destination, 'poster_bg')})
  `,
  backgroundSize: 'cover',
  backgroundPosition: 'center',
};
```

---

## 三、API 变更

### 3.1 新增接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/destinations/{city}/image` | GET | 获取城市图片 |
| `/api/v1/destinations/{city}/news` | GET | 获取当地资讯 |
| `/api/v1/routes/calculate` | POST | 计算两点间路线 |

### 3.2 修改接口

| 接口 | 变更 |
|------|------|
| `/api/v1/chat/stream` | 响应增加 `accommodation` 字段 |
| `/api/v1/assistants/budget` | 增加分类明细 |

### 3.3 响应格式变更

```json
{
  "type": "end",
  "itinerary": [
    {
      "day": 1,
      "title": "故宫中轴线深度游",
      "activities": [...],
      "accommodation": {
        "name": "如家酒店(王府井店)",
        "price": "¥258/晚",
        "location": {"lng": 116.41, "lat": 39.91},
        "distance_to_next": "3.2km",
        "transport_to_next": "地铁3站，约15分钟",
        "should_change_tomorrow": false
      },
      "transport_from_hotel": {
        "from": "昨晚住宿",
        "to": "故宫博物院",
        "duration": "15分钟",
        "description": "地铁1号线，天安门东站"
      }
    }
  ],
  "budget_breakdown": {
    "accommodation": 1200,
    "tickets": 800,
    "transport": 400,
    "food": 1000,
    "total_estimated": 3400
  }
}
```

---

## 四、数据模型

### 4.1 住宿推荐模型

```python
class AccommodationRecommendation(BaseModel):
    """住宿推荐"""
    name: str
    price_per_night: int
    total_price: int
    rating: float
    location: Location
    address: str
    distance_to_first_attraction: float  # km
    transport_to_first_attraction: str
    tags: list[str]
    image_url: str | None
    booking_links: dict[str, str]  # {"高德": "url", "携程": "url"}
    
    # 推荐原因
    recommendation_reason: str  # "距离环球影城步行5分钟"
    is_from_guide: bool  # 是否来自攻略推荐


class DayAccommodation(BaseModel):
    """每日住宿安排"""
    check_in_time: str
    hotel: AccommodationRecommendation
    should_change_next_day: bool
    change_reason: str | None  # "明日景点在通州，建议换到环球影城附近"
    alternative_hotels: list[AccommodationRecommendation]
```

### 4.2 交通信息模型

```python
class TransportInfo(BaseModel):
    """交通信息"""
    from_name: str
    to_name: str
    from_location: Location
    to_location: Location
    distance_km: float
    duration_min: int
    mode: str  # "transit", "walking", "driving"
    description: str  # "地铁1号线→换乘7号线"
    steps: list[dict] | None
```

---

## 五、实现计划

### Phase 1: Bug 修复 (1-2天)
- [ ] 修复海报天数显示错误
- [ ] 确保数据从 itinerary 正确传递到海报组件

### Phase 2: 住宿整合 (3-5天)
- [ ] 后端：住宿推荐逻辑（预算匹配、区域推荐）
- [ ] 后端：交通时间计算接口
- [ ] 前端：行程中展示住宿
- [ ] 前端：住宿偏好设置

### Phase 3: 智囊侧边栏 (3-5天)
- [ ] 前端：侧边栏布局和响应式
- [ ] 前端：迷你地图组件
- [ ] 前端：天气趋势组件
- [ ] 后端：当地资讯接口
- [ ] 前端：预算仪表盘

### Phase 4: 图片系统 (2-3天)
- [ ] 收集/生成热门城市图片
- [ ] 后端：图片获取服务
- [ ] 前端：海报背景图
- [ ] 前端：景点图片展示

---

## 六、验收标准

### 6.1 海报
- [ ] 天数与实际行程一致
- [ ] 显示目的地地标背景图
- [ ] 正确显示旅行风格和预算

### 6.2 住宿
- [ ] 每天结束时显示住宿推荐
- [ ] 价格在用户预算范围内
- [ ] 提示是否需要换酒店及原因
- [ ] 可以点击跳转预订链接

### 6.3 交通
- [ ] 显示"从XX出发"
- [ ] 时间基于高德 API 计算
- [ ] 显示具体路线（如"地铁1号线"）

### 6.4 侧边栏
- [ ] 宽屏显示，窄屏收起
- [ ] 地图标记当天景点
- [ ] 天气显示未来3-5天
- [ ] 预算实时更新

---

*文档结束*
