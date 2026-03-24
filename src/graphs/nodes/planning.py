"""
行程规划节点（约束式生成 + 坐标继承）

核心策略：
1. 景点/酒店：必须从 POI 池中选择，精确匹配获取坐标
2. 餐饮活动：继承上一个活动的坐标（模拟"附近就餐"）
3. 自由活动：使用当天活动区域中心
"""

import json
from datetime import datetime
from typing import Any

import structlog

from src.config.constants import PLANNING
from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.graphs.utils.parsers import parse_trip_duration
from src.graphs.poi.validator import validate_itinerary_distances
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


# ============================================================
# 工具函数
# ============================================================


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离（公里）"""
    import math
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ============================================================
# 类型映射（后端→前端）
# ============================================================

# 后端 type → 前端 type（前端 GaodeMap.jsx 期望的值）
TYPE_MAPPING = {
    "attraction": "sight",
    "景点": "sight",
    "meal": "food",
    "food": "food",
    "餐饮": "food",
    "hotel": "hotel",
    "酒店": "hotel",
    "transport": "transport",
    "交通": "transport",
    "free": "sight",  # 自由活动当作景点
    "rest": "sight",
    "other": "sight",
}

# 中文 category → 用于匹配的 category 列表
CATEGORY_MAP = {
    "景点": ["景点", "sight", "attraction", "tourism"],
    "酒店": ["酒店", "hotel", "住宿"],
    "餐厅": ["餐厅", "food", "美食", "餐饮"],
}


def _normalize_type(act_type: str) -> str:
    """将后端 type 转换为前端期望的 type"""
    return TYPE_MAPPING.get(act_type, "sight")


def _match_category(poi_category: str, target_category: str) -> bool:
    """检查 POI category 是否匹配目标类别"""
    if not target_category:
        return True
    
    poi_cat = poi_category.strip() if poi_category else ""
    target_cat = target_category.strip()
    
    # 直接匹配
    if poi_cat == target_cat:
        return True
    
    # 通过映射匹配
    for key, aliases in CATEGORY_MAP.items():
        if target_cat in aliases or target_cat == key:
            return poi_cat in aliases or poi_cat == key
    
    return False


def _build_poi_names_list(poi_pool: dict[str, dict], category: str = None) -> str:
    """构建 POI 名称列表供 LLM 参考"""
    names = []
    for poi_id, poi in poi_pool.items():
        if category and poi.get("category") != category:
            continue
        name = poi.get("name", "")
        if name:
            names.append(name)
    return ", ".join(names[:30]) if names else "暂无数据"


def _char_jaccard_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的字符级 Jaccard 相似度"""
    if not s1 or not s2:
        return 0.0
    set1 = set(s1)
    set2 = set(s2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _exact_match_poi(name: str, poi_pool: dict[str, dict], category: str = None) -> dict | None:
    """
    智能匹配 POI 名称
    
    匹配策略（按优先级）：
    1. 精确匹配
    2. 包含关系匹配
    3. 相似度匹配（Jaccard >= 0.5）
    """
    if not name or not poi_pool:
        return None
    
    name_clean = name.strip()
    best_match = None
    best_score = 0.0
    SIMILARITY_THRESHOLD = PLANNING.POI_SIMILARITY_THRESHOLD
    
    for poi_id, poi in poi_pool.items():
        if category and not _match_category(poi.get("category", ""), category):
            continue
        
        poi_name = poi.get("name", "").strip()
        if not poi_name:
            continue
        
        # 1. 精确匹配
        if name_clean == poi_name:
            return poi
        
        # 2. 包含关系匹配
        if name_clean in poi_name or poi_name in name_clean:
            return poi
        
        # 3. 相似度匹配
        similarity = _char_jaccard_similarity(name_clean, poi_name)
        if similarity > best_score and similarity >= SIMILARITY_THRESHOLD:
            best_score = similarity
            best_match = poi
    
    return best_match


def _populate_coordinates(
    itinerary: list[dict], 
    poi_pool: dict[str, dict],
    arrival_hub: dict | None,
) -> tuple[list[dict], list[str]]:
    """
    智能填充坐标
    
    策略：
    - 景点/酒店/交通：精确匹配 POI 池
    - 餐饮：继承上一个活动坐标 + 小偏移
    - 自由活动：使用当天区域中心
    
    返回：(填充后的行程, 警告列表)
    """
    warnings = []
    
    for day in itinerary:
        day_locations = []  # 收集当天有效坐标
        prev_location = None
        
        for activity in day.get("activities", []):
            act_type = activity.get("type", "attraction")
            title = activity.get("title", "")
            
            # === 景点/酒店/交通：精确匹配 POI 池 ===
            if act_type in ("attraction", "hotel", "transport"):
                # 特殊处理 arrival hub
                if "抵达" in title or "机场" in title or "火车站" in title:
                    if arrival_hub:
                        activity["location"] = {
                            "lat": arrival_hub.get("lat"),
                            "lng": arrival_hub.get("lng"),
                        }
                        activity["poi_source"] = "arrival_hub"
                        prev_location = activity["location"]
                        day_locations.append(prev_location)
                        continue
                
                # === 通用活动模式检测（不需要精确 POI）===
                generic_patterns = [
                    ("入住", "hotel"),      # 入住酒店 → 使用住宿坐标
                    ("返回", "prev"),       # 返回市区 → 使用上一个坐标
                    ("继续游览", "prev"),   # 继续游览 → 使用上一个坐标
                    ("休整", "prev"),       # 休整 → 使用上一个坐标
                    ("自由活动", "center"), # 自由活动 → 使用当天中心
                    ("周边游览", "prev"),   # 周边游览 → 使用上一个坐标
                    ("最后游览", "prev"),   # 最后游览 → 使用上一个坐标
                ]
                
                is_generic = False
                for pattern, fallback_type in generic_patterns:
                    if pattern in title:
                        is_generic = True
                        if fallback_type == "hotel":
                            # 尝试从住宿获取坐标
                            acc = day.get("accommodation") or {}
                            if acc.get("location"):
                                activity["location"] = acc["location"].copy()
                            elif prev_location:
                                activity["location"] = prev_location.copy()
                            activity["poi_source"] = "generic_hotel"
                        elif fallback_type == "prev" and prev_location:
                            activity["location"] = prev_location.copy()
                            activity["poi_source"] = "generic_inherit"
                        elif fallback_type == "center" and day_locations:
                            avg_lat = sum(loc["lat"] for loc in day_locations) / len(day_locations)
                            avg_lng = sum(loc["lng"] for loc in day_locations) / len(day_locations)
                            activity["location"] = {"lat": avg_lat, "lng": avg_lng}
                            activity["poi_source"] = "generic_center"
                        elif prev_location:
                            activity["location"] = prev_location.copy()
                            activity["poi_source"] = "generic_fallback"
                        break
                
                if is_generic:
                    if activity.get("location"):
                        prev_location = activity["location"]
                        day_locations.append(prev_location)
                    continue  # 跳过正常 POI 匹配
                
                # 正常匹配
                matched = _exact_match_poi(title, poi_pool)
                if matched:
                    activity["location"] = {
                        "lat": matched["lat"],
                        "lng": matched["lng"],
                    }
                    activity["poi_source"] = "pool_match"
                    activity["matched_poi_name"] = matched.get("name")
                    prev_location = activity["location"]
                    day_locations.append(prev_location)
                else:
                    # 未匹配：继承上一个坐标 + 警告
                    if prev_location:
                        activity["location"] = prev_location.copy()
                        activity["poi_source"] = "inherited_fallback"
                    warnings.append(f"Day {day.get('day')}: 未找到 POI '{title}'")
            
            # === 餐饮：继承上一个位置 + 小偏移 ===
            elif act_type in ("meal", "food"):
                if prev_location:
                    activity["location"] = {
                        "lat": prev_location["lat"] + PLANNING.MEAL_COORD_OFFSET,
                        "lng": prev_location["lng"] + PLANNING.MEAL_COORD_OFFSET,
                    }
                    activity["poi_source"] = "nearby_meal"
                elif day_locations:
                    # 使用当天第一个有效位置
                    activity["location"] = day_locations[0].copy()
                    activity["poi_source"] = "day_first"
            
            # === 自由活动/其他：使用当天中心 ===
            elif act_type in ("free", "rest", "other") or not act_type:
                if day_locations:
                    # 计算当天中心
                    avg_lat = sum(loc["lat"] for loc in day_locations) / len(day_locations)
                    avg_lng = sum(loc["lng"] for loc in day_locations) / len(day_locations)
                    activity["location"] = {"lat": avg_lat, "lng": avg_lng}
                    activity["poi_source"] = "day_center"
                elif prev_location:
                    activity["location"] = prev_location.copy()
                    activity["poi_source"] = "inherited"
        
        # === 填充住宿坐标（智能选择最近酒店）===
        accommodation = day.get("accommodation")
        if accommodation:
            acc_name = accommodation.get("name", "")
            
            # 先尝试匹配 LLM 指定的酒店
            matched_hotel = _exact_match_poi(acc_name, poi_pool, category="酒店")
            
            if matched_hotel:
                accommodation["location"] = {
                    "lat": matched_hotel["lat"],
                    "lng": matched_hotel["lng"],
                }
                accommodation["poi_source"] = "pool_match"
            elif day_locations:
                # 未匹配：找距离当天活动中心最近的酒店
                center_lat = sum(loc["lat"] for loc in day_locations) / len(day_locations)
                center_lng = sum(loc["lng"] for loc in day_locations) / len(day_locations)
                
                hotels = [p for p in poi_pool.values() if p.get("category") == "酒店"]
                best_hotel = None
                min_dist = float("inf")
                
                for h in hotels:
                    if h.get("lat") and h.get("lng"):
                        dist = _haversine(center_lat, center_lng, h["lat"], h["lng"])
                        if dist < min_dist:
                            min_dist = dist
                            best_hotel = h
                
                if best_hotel:
                    accommodation["name"] = best_hotel.get("name", accommodation.get("name"))
                    accommodation["location"] = {
                        "lat": best_hotel["lat"],
                        "lng": best_hotel["lng"],
                    }
                    accommodation["price"] = f"¥{best_hotel.get('price', PLANNING.DEFAULT_HOTEL_PRICE)}/晚"
                    accommodation["poi_source"] = "nearest_hotel"
    
    # === 类型标准化（后端 → 前端）===
    # 前端 GaodeMap.jsx 期望：sight, food, hotel, transport
    for day in itinerary:
        for activity in day.get("activities", []):
            original_type = activity.get("type", "attraction")
            activity["type"] = _normalize_type(original_type)
    
    return itinerary, warnings


# ============================================================
# Prompt 构建
# ============================================================

# 预算等级 → 价格范围映射
BUDGET_PRICES = {
    "economy": (100, 200),
    "moderate": (250, 450),
    "comfortable": (400, 700),
    "luxury": (700, 1500),
}


def _build_planning_prompt(
    destination: str,
    user_days: int,
    user_nights: int,
    actual_days: int,
    actual_nights: int,
    travel_style: str,
    budget_level: str,
    min_price: int,
    max_price: int,
    must_visit_places: list,
    weather_info: dict | None,
    guide_context: str,
    attraction_names: str,
    hotel_names: str,
) -> str:
    """构建行程规划的 LLM 提示词"""
    must_visit_text = ""
    if must_visit_places:
        must_visit_text = f"""
## ⭐ 用户必去地点（必须纳入行程！）
{json.dumps(must_visit_places, ensure_ascii=False)}

**重要**：以上是用户明确提出想去的地点，必须安排在行程中，并作为核心亮点！"""

    weather_text = json.dumps(weather_info, ensure_ascii=False, indent=2) if weather_info else "暂无"
    guide_text = guide_context if guide_context else "暂无攻略信息，请根据常识规划"

    return f"""你是一个专业的旅行规划师。请基于【真实 UGC 攻略】为用户制定行程。

⚠️ 核心原则：你的规划必须参考下面的真实攻略内容，不要凭空想象！

## 📋 用户需求
- **目的地**: {destination}
- **用户表述**: {user_days}天{user_nights}晚
- **实际规划**: {actual_days}天{actual_nights}晚（含抵达日）
- **旅行风格**: {travel_style}
- **预算等级**: {budget_level} (¥{min_price}-{max_price}/晚)
{must_visit_text}

## 🛬 抵达日规则（极其重要！！！）

**用户说"{user_days}天{user_nights}晚"，但如果 Day 1 早上就有行程，需要前一天到达！**

实际行程应该是：
- **Day 0 (抵达日)**: 下午抵达{destination}，入住酒店，晚上简单逛逛
- **Day 1 - Day {user_days}**: 正式游玩
- **最后一天**: 返程，无住宿

### 抵达日（Day 0）必须包含：
1. 14:00-16:00 抵达目的地
2. 16:00-17:00 入住酒店
3. 18:00-21:00 酒店周边轻度探索/晚餐

## 🌤️ 天气信息
{weather_text}

## 📚 真实 UGC 攻略（重点参考！！！）
以下是从小红书、知乎、马蜂窝等平台搜索到的真实攻略，请从中提取：
1. 真实可行的景点顺序
2. 合理的时间安排（如故宫需要4小时、环球影城需要全天）
3. 同一区域的景点放在同一天
4. 真实的美食推荐

{guide_text}

## 📍 可选景点（建议从中选择）
{attraction_names}

## 🏨 可选酒店（建议从中选择）
{hotel_names}

## ⏰ 时间安排规则（必须遵守！）
1. **抵达日（Day 0）**：轻松安排，主要是入住和周边简单逛逛
2. **主题公园（环球影城、迪士尼等）**：必须安排全天（09:00-21:00），当天不安排其他主要景点
3. **故宫/颐和园等大型景点**：至少安排半天（4小时）
4. **日落/夕阳观景**：只能在17:00-19:00
5. **夜景/灯光秀**：只能在19:00-22:00
6. **同一天景点**：应在同一区域，避免来回折腾
7. **每天2-3个主要景点**为宜，不要走马观花
8. **返程日**：根据航班时间灵活安排，可去机场附近购物

## 🚨 地理距离约束（极其重要！违反此规则将导致行程不可行！）

**核心原则：同一天的主要景点必须在相近区域（通常 30 公里以内）！**

### 需要单独安排一整天的景点（不可与其他主要景点同天）：
- **远郊自然景观**：如长城、雪山、峡谷、湖泊等，通常距市区 50km+
- **大型主题公园**：如环球影城、迪士尼、长隆等
- **需要长途交通的景点**：车程超过 1.5 小时的景点

### 可以同天安排的景点：
- 位于同一城区/行政区的景点
- 步行或短途交通（30分钟内）可达的景点
- 同一条旅游线路上的景点

### ❌ 错误安排（绝对禁止！）：
- 远郊景点 + 市区景点（距离太远，不可能同一天）
- 相反方向的远郊景点（如上午去东边郊区，下午去西边郊区）

## 🏔️ 自然风光区特别规则（林芝/九寨沟/稻城亚丁/香格里拉等）

**这类目的地的景点分布非常广，交通时间很长！**

### 核心原则：
1. **每天只安排 1 个主要远郊景点**
2. **交通时间 2-4 小时是正常的**，不要低估
3. **去程 + 景区游览 + 返程 = 一整天**
4. **当天返回的景点，晚餐时间可能很晚（20:00+）**

### 林芝示例（每个景点需要一整天）：
| 景点 | 距市区 | 车程 | 安排建议 |
|------|--------|------|----------|
| 巴松措 | 120km | 2.5h | 早出晚归，一整天 |
| 雅鲁藏布大峡谷 | 150km | 3-4h | 一整天，可住景区附近 |
| 南迦巴瓦观景台 | 90km | 2h | 半天为主，可组合 |

### ✅ 正确安排：
- Day 1: 抵达林芝 + 市区休整（一个景点都不去）
- Day 2: 巴松措一日游（早 8:00 出发，晚 19:00 返回）
- Day 3: 雅鲁藏布大峡谷（全天，可住索松村）
- Day 4: 返程

### ❌ 错误安排（绝对禁止！）：
- 同一天安排 巴松措 + 雅鲁藏布大峡谷（距离 200km+）
- 上午市区，下午去巴松措（往返 5 小时，游玩时间不够）


## 🏨 住宿安排规则（非常重要！）
1. **住宿是为了方便第二天的行程**，不是当天的！
2. **推荐理由必须基于第二天的行程**：例如"靠近明日行程起点XX"或"方便前往长城/环球影城"
3. **最后一天不需要住宿**（返程日）
4. **主题公园**（环球影城、迪士尼等）：建议前一晚换到就近酒店，方便早起入园

## 🚗 交通安排规则（非常重要！不要瞎编时间！）

**⚠️ 交通时间必须基于实际距离估算，不要随意编造！**

### 距离-时间换算基准（城市道路）：
| 距离范围 | 预估时间 | 说明 |
|----------|----------|------|
| 0-5km | 10-20分钟 | 步行/公交/打车 |
| 5-15km | 20-40分钟 | 公交/地铁/打车 |
| 15-30km | 40-60分钟 | 地铁换乘/打车 |
| 30-60km | 1-1.5小时 | 需要专门交通 |
| 60-100km | 1.5-2小时 | 远郊，需包车/大巴 |
| 100km+ | 2-3小时+ | 远郊景区，需提前规划 |

### 🚨 远郊景点交通时间示例（绝对不要低估！）：
- **八达岭长城**（北京）：距市区 70km，车程约 2 小时
- **巴松措**（林芝）：距市区约 120km，车程约 2.5-3 小时
- **雅鲁藏布大峡谷**（林芝）：距市区约 150km，车程约 3-4 小时
- **玉龙雪山**（丽江）：距市区约 30km，车程约 40 分钟
- **九寨沟**（成都）：距成都约 400km，车程约 8 小时或飞机

### ❌ 错误示例（绝对禁止）：
- "打车 20 分钟到巴松措"（实际需要 2.5 小时！）
- "地铁 30 分钟到长城"（实际需要 2 小时！）

### 规则：
1. **如果不确定距离，宁可估长不估短**
2. **远郊景点之间不要安排在同一天**
3. **如果某天有远郊景点，其他活动必须在该景点附近**



请返回纯 JSON 格式（不要 markdown 代码块）：
{{
    "chat_response": "一段友好的回复（200-300字），包含：1. 行程亮点 2. 为什么这样安排 3. 特别提醒",
    "itinerary": [
        {{
            "day": 0,
            "title": "抵达{destination} & 入住休整",
            "activities": [
                {{"time": "14:00", "title": "抵达{destination}", "type": "transport", "desc": "根据航班/高铁时间抵达"}},
                {{"time": "16:00", "title": "入住酒店", "type": "hotel", "desc": "办理入住，稍作休息"}},
                {{"time": "18:00", "title": "晚餐", "type": "meal", "desc": "品尝当地美食"}}
            ],
            "accommodation": {{"name": "酒店名称（从可选酒店中选择）", "reason": "靠近明日行程起点"}}
        }},
        {{
            "day": 1,
            "title": "Day 1 主题（如：故宫深度游）",
            "activities": [
                {{"time": "09:00", "title": "景点名称（从可选景点中选择）", "type": "attraction", "desc": "游玩重点和tips", "transport_from_prev": {{"from": "酒店", "method": "地铁X号线", "duration": "约30分钟"}}}},
                {{"time": "12:00", "title": "午餐", "type": "meal", "desc": "推荐当地特色美食"}},
                {{"time": "14:00", "title": "下午景点", "type": "attraction", "desc": "游玩建议"}},
                {{"time": "18:00", "title": "晚餐", "type": "meal", "desc": "推荐餐厅或美食"}}
            ],
            "accommodation": {{"name": "酒店名称", "reason": "方便明日行程"}}
        }},
        {{
            "day": {user_days},
            "title": "返程 & 离开{destination}",
            "activities": [
                {{"time": "09:00", "title": "酒店周边最后游览", "type": "attraction", "desc": "自由活动或补购纪念品"}},
                {{"time": "12:00", "title": "午餐", "type": "meal", "desc": "最后一顿当地美食"}},
                {{"time": "14:00", "title": "前往机场/车站", "type": "transport", "desc": "预留充足时间"}}
            ],
            "accommodation": null
        }}
    ]
}}

🚨 重要提醒：
- **返程日（最后一天）的 accommodation 必须是 null**，因为不需要住宿！
- 不要在返程日推荐酒店！

只返回纯 JSON！"""


def _append_regenerate_context(prompt: str, previous_itinerary: list[dict]) -> str:
    """为重新生成场景追加上下文"""
    prev_summary = []
    for day in previous_itinerary[:5]:
        day_num = day.get("day", "?")
        title = day.get("title", "")
        activities = day.get("activities", [])
        activity_names = [a.get("title", "") for a in activities[:3]]
        prev_summary.append(f"Day {day_num}: {title} - {', '.join(activity_names)}")

    return prompt + f"""

## 🔄 重新生成要求
用户请求不同版本，上一版：
{chr(10).join(prev_summary)}

请尝试：调整景点顺序、替换 1-2 个景点、选择不同区域酒店"""


# ============================================================
# 响应解析
# ============================================================


def _parse_plan_response(content: str) -> dict | None:
    """解析 LLM 返回的 JSON 规划，支持 markdown 包裹和 json_repair 兜底"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse plan JSON", error=str(e))
        try:
            import json_repair
            return json_repair.repair_json(content, return_objects=True)
        except Exception:
            logger.error("JSON repair also failed")
            return None


def _build_travel_plan(
    structured_plan: dict,
    itinerary: list[dict],
    destination: str,
    budget_level: str,
    min_price: int,
    max_price: int,
    coord_warnings: list[str],
) -> dict:
    """组装最终的旅行计划数据结构"""
    return {
        "destination": destination,
        "generated_at": datetime.now().isoformat(),
        "structured": True,
        "chat_response": structured_plan.get("chat_response", ""),
        "itinerary": itinerary,
        "content": structured_plan.get("chat_response", ""),
        "budget_info": {
            "level": budget_level,
            "price_range": f"¥{min_price}-{max_price}/晚",
        },
        "coordinate_warnings": coord_warnings,
    }


def _log_coverage_stats(itinerary: list[dict], coord_warnings: list[str]) -> None:
    """记录坐标覆盖率统计"""
    total_activities = sum(len(day.get("activities", [])) for day in itinerary)
    activities_with_location = sum(
        1 for day in itinerary
        for act in day.get("activities", [])
        if act.get("location")
    )
    logger.info(
        "Plan generated with coordinate inheritance",
        days=len(itinerary),
        total_activities=total_activities,
        with_location=activities_with_location,
        coverage=f"{activities_with_location / max(1, total_activities) * 100:.0f}%",
        warnings=len(coord_warnings),
    )


# ============================================================
# 节点函数
# ============================================================


async def planning_node(state: AgentState) -> dict[str, Any]:
    """
    行程规划节点（约束式生成 + 坐标继承）

    LLM 自由生成高质量内容，后处理层智能填充坐标
    """
    logger.info("Node: planning (constrained + inheritance)")

    task_type = state.get("task_type")
    if task_type != TaskType.TRAVEL_PLANNING.value:
        return {"next_action": "respond"}

    # --- 提取状态 ---
    poi_pool = state.get("poi_pool", {})
    arrival_hub = state.get("arrival_hub")
    weather_info = state.get("weather_info")

    travel_pref = state.get("travel_preference") or {}
    destination = travel_pref.get("destination", "未知目的地")
    travel_style = travel_pref.get("travel_style", "自由行")
    must_visit_places = travel_pref.get("must_visit_places", [])
    budget_level = travel_pref.get("budget_level", "moderate")
    guide_context = travel_pref.get("guide_context", "")

    user_message = state.get("messages", [])[-1].content if state.get("messages") else ""
    trip_duration = parse_trip_duration(user_message)
    user_days = trip_duration["user_days"]
    user_nights = trip_duration["user_nights"]
    actual_days = trip_duration["actual_days"]
    actual_nights = trip_duration["actual_nights"]

    min_price, max_price = BUDGET_PRICES.get(budget_level, (250, 450))

    # --- 构建 Prompt ---
    planning_prompt = _build_planning_prompt(
        destination=destination,
        user_days=user_days,
        user_nights=user_nights,
        actual_days=actual_days,
        actual_nights=actual_nights,
        travel_style=travel_style,
        budget_level=budget_level,
        min_price=min_price,
        max_price=max_price,
        must_visit_places=must_visit_places,
        weather_info=weather_info,
        guide_context=guide_context,
        attraction_names=_build_poi_names_list(poi_pool, category="景点"),
        hotel_names=_build_poi_names_list(poi_pool, category="酒店"),
    )

    if state.get("regenerate") and state.get("previous_itinerary"):
        planning_prompt = _append_regenerate_context(planning_prompt, state["previous_itinerary"])

    # --- 调用 LLM ---
    llm = get_llm()
    messages = [
        Message(
            role="system",
            content="你是专业旅游规划师。严格按照JSON格式输出，基于真实攻略内容规划。景点名称请使用可选景点列表中的准确名称。",
        ),
        Message(role="user", content=planning_prompt),
    ]
    response = await llm.chat(messages)

    # --- 解析响应 ---
    structured_plan = _parse_plan_response(response.content)
    if not structured_plan:
        return {
            "next_action": "respond",
            "errors": ["行程规划解析失败，请重试"],
        }

    # --- 后处理：坐标填充 + 距离验证 ---
    itinerary = structured_plan.get("itinerary", [])
    itinerary, coord_warnings = _populate_coordinates(itinerary, poi_pool, arrival_hub)

    if coord_warnings:
        logger.warning("Coordinate warnings", warnings=coord_warnings[:5])

    violations = validate_itinerary_distances(itinerary, max_distance_km=PLANNING.MAX_ITINERARY_DISTANCE_KM)
    if violations:
        logger.warning("Distance violations detected", count=len(violations))

    # --- 组装结果 ---
    travel_plan = _build_travel_plan(
        structured_plan, itinerary, destination,
        budget_level, min_price, max_price, coord_warnings,
    )

    _log_coverage_stats(itinerary, coord_warnings)

    return {
        "travel_plan": travel_plan,
        "planning_phase": PlanningPhase.PLAN_GENERATED.value,
        "next_action": "route_enrich",
        "updated_at": datetime.now().isoformat(),
    }


__all__ = ["planning_node"]
