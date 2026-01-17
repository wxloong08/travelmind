"""
行程规划节点（POI 选择模式）

LLM 从 POI 池中选择景点 ID，而非自由生成文本
"""

import json
from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState, PlanningPhase, TaskType
from src.graphs.utils.parsers import parse_trip_duration
from src.graphs.poi.models import POIDistanceMatrix
from src.graphs.poi.validator import validate_itinerary_distances
from src.llm import Message
from src.llm.qwen import get_llm

logger = structlog.get_logger()


def _build_poi_table(poi_pool: dict[str, dict]) -> str:
    """构建 POI 表格供 LLM 参考"""
    if not poi_pool:
        return "暂无 POI 数据"
    
    lines = ["| ID | 名称 | 类别 | 区域 | 评分 | 价格 |"]
    lines.append("|-----|------|------|------|------|------|")
    
    for poi_id, poi in poi_pool.items():
        name = poi.get("name", "")[:15]
        category = poi.get("category", "")
        district = poi.get("district", "-")[:8] if poi.get("district") else "-"
        rating = f"{poi.get('rating', '-')}" if poi.get("rating") else "-"
        price = f"¥{poi.get('price')}" if poi.get("price") else "-"
        lines.append(f"| {poi_id[:20]} | {name} | {category} | {district} | {rating} | {price} |")
    
    return "\n".join(lines)


def _build_distance_snippet(distance_matrix: dict, limit: int = 20) -> str:
    """构建距离矩阵摘要"""
    if not distance_matrix or not distance_matrix.get("pois"):
        return "暂无距离数据"
    
    pois = distance_matrix.get("pois", {})
    cache = distance_matrix.get("cache", {})
    
    lines = ["部分 POI 间距离（公里）:"]
    count = 0
    
    for key, dist in list(cache.items())[:limit]:
        if "|" in key:
            id1, id2 = key.split("|")
            name1 = pois.get(id1, {}).get("name", id1)[:10]
            name2 = pois.get(id2, {}).get("name", id2)[:10]
            lines.append(f"- {name1} → {name2}: {dist:.1f}km")
            count += 1
    
    if count == 0:
        return "距离数据正在计算中..."
    
    return "\n".join(lines)


def _haversine(lat1, lon1, lat2, lon2):
    """计算两点间距离（km）"""
    import math
    R = 6371  # 地球半径
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def planning_node(state: AgentState) -> dict[str, Any]:
    """
    行程规划节点（POI 选择模式）

    LLM 从 POI 池中选择，确保每个活动都有真实坐标
    """
    logger.info("Node: planning (POI-based)")

    task_type = state.get("task_type")
    if task_type != TaskType.TRAVEL_PLANNING.value:
        return {"next_action": "respond"}

    llm = get_llm()

    # 获取 POI 池和距离矩阵
    poi_pool = state.get("poi_pool", {})
    distance_matrix = state.get("distance_matrix", {})
    arrival_hub = state.get("arrival_hub")
    weather_info = state.get("weather_info")
    
    travel_pref = state.get("travel_preference") or {}
    destination = travel_pref.get("destination", "未知目的地")
    travel_style = travel_pref.get("travel_style", "自由行")
    must_visit_places = travel_pref.get("must_visit_places", [])
    days = travel_pref.get("days", 3)
    budget_level = travel_pref.get("budget_level", "moderate")
    guide_context = travel_pref.get("guide_context", "")

    # 解析行程时长
    user_message = state.get("messages", [])[-1].content if state.get("messages") else ""
    trip_duration = parse_trip_duration(user_message)
    user_days = trip_duration["user_days"]
    user_nights = trip_duration["user_nights"]
    actual_days = trip_duration["actual_days"]
    actual_nights = trip_duration["actual_nights"]

    # 构建 POI 表格
    poi_table = _build_poi_table(poi_pool)
    distance_snippet = _build_distance_snippet(distance_matrix)

    # 必去景点强调
    must_visit_text = ""
    if must_visit_places:
        must_visit_text = f"""
## ⭐ 用户必去地点
{json.dumps(must_visit_places, ensure_ascii=False)}
请确保这些地点出现在行程中！
"""

    # ========== POI 选择模式 Prompt ==========
    planning_prompt = f"""你是专业旅游规划师。请从下方 POI 池中**选择**景点组合成合理的行程。

## ⚠️ 关键规则（必须遵守）
1. **地理集中**：每天活动必须在同一区域（距离 < 15km），绝不跨区！
2. **必须安排餐饮**：每天必须有午餐（12:00-13:00）和晚餐（18:00-19:00）
3. **合理时间安排**：
   - 景点游玩时间 2-3 小时
   - 用餐时间 1 小时
   - 每天行程不超过 8 小时（9:00-21:00）
4. **只选核心热门景点**：优先选择评分高、知名度高的景点
5. **避免远郊景点**：如果某个景点距离其他景点 > 30km，不要选择它

## 用户需求
- 目的地: {destination}
- 行程: {user_days}天{user_nights}晚（实际 {actual_days} 天含抵达日）
- 风格: {travel_style}
- 预算: {budget_level}
{must_visit_text}

## POI 池（请从中选择）
{poi_table}

## 距离参考
{distance_snippet}

## 天气
{json.dumps(weather_info, ensure_ascii=False, indent=2) if weather_info else "暂无"}

## 🔥 真实攻略参考（重要！请参考以下真实旅行者的行程推荐）
{guide_context if guide_context else "暂无攻略，请根据目的地常识规划经典景点"}

## ❓ 信息缺失处理
如果你发现**缺少关键信息**（如某个必去景点的门票价格、开放时间，或者该地区是否有合适的酒店），无法完成规划，请设置 "needs_more_info": true，并在 "missing_info_query" 中提出具体问题。
系统会去搜索该问题，然后重新回来让你规划。
**注意**：不要滥用此功能！仅在**缺少该信息就无法规划**时使用。如果只是缺少一些非关键细节（如餐厅具体菜单），请使用常识推断或留空。

---

请返回纯 JSON（不要 markdown）：
{{
    "needs_more_info": false,
    "missing_info_query": "",
    "chat_response": "友好回复（150-200字），简要介绍行程亮点和特色",
    "itinerary": [
        {{
            "day": 0,
            "title": "抵达{destination}",
            "activities": [
                {{"poi_id": "arrival_hub", "time": "14:00", "title": "抵达{destination}", "type": "transport", "desc": "办理入住休整"}},
                {{"poi_id": "RESTAURANT_ID", "time": "18:00", "title": "晚餐", "type": "meal", "desc": "品尝当地特色"}}
            ],
            "accommodation": {{"poi_id": "HOTEL_ID", "name": "酒店名", "price": "¥300/晚", "reason": "位置便利"}}
        }},
        {{
            "day": 1,
            "title": "Day 1 主题（XX区游玩）",
            "activities": [
                {{"poi_id": "ATTRACTION_1", "time": "09:00", "title": "上午景点", "type": "attraction", "desc": "游玩重点"}},
                {{"poi_id": "RESTAURANT_ID", "time": "12:00", "title": "午餐", "type": "meal", "desc": "休息用餐"}},
                {{"poi_id": "ATTRACTION_2", "time": "14:00", "title": "下午景点", "type": "attraction", "desc": "游玩重点"}},
                {{"poi_id": "RESTAURANT_ID", "time": "18:00", "title": "晚餐", "type": "meal", "desc": "当地美食"}}
            ],
            "accommodation": {{"poi_id": "HOTEL_ID", "name": "酒店名", "price": "¥300/晚", "reason": "靠近明日景点"}}
        }}
    ]
}}

⚠️ 必须遵守：
- 每天必须有午餐（12:00）和晚餐（18:00）两个 meal 类型活动
- 从 POI 池选择餐厅的 poi_id，如果池中没有合适的，使用 "generic_lunch" 或 "generic_dinner"
- 抵达日（Day 0）只安排入住和晚餐，不安排景点
- 每天的景点必须在同一区域（参考距离表）

只返回 JSON！"""

    # 重新生成逻辑
    regenerate = state.get("regenerate", False)
    previous_itinerary = state.get("previous_itinerary")
    
    if regenerate and previous_itinerary:
        prev_summary = []
        for day in previous_itinerary[:5]:
            day_num = day.get("day", "?")
            activities = day.get("activities", [])
            activity_names = [a.get("title", "")[:15] for a in activities[:3]]
            prev_summary.append(f"Day {day_num}: {', '.join(activity_names)}")
        
        planning_prompt += f"""

## 🔄 重新生成
用户请求不同版本，上一版：
{chr(10).join(prev_summary)}

请尝试：调整景点顺序、替换 1-2 个景点、选择不同区域酒店"""

    messages = [
        Message(
            role="system",
            content="你是专业旅游规划师。严格按 JSON 输出，只使用 POI 池中的景点。"
        ),
        Message(role="user", content=planning_prompt),
    ]

    response = await llm.chat(messages)

    # 解析响应
    structured_plan = None
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        structured_plan = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse POI-based plan", error=str(e))
        # 回退到 legacy planning
        from src.graphs.nodes_legacy import planning_node as legacy_planning
        return await legacy_planning(state)

    # ========== Fallback 检查 ==========
    supplementary_count = state.get("supplementary_search_count", 0)
    if structured_plan.get("needs_more_info") and supplementary_count < 1:
        query = structured_plan.get("missing_info_query", "")
        if query:
            logger.info("Planning requires more info", query=query)
            return {
                "next_action": "supplementary_search", 
                "fallback_query": query,
                # 保持 phase 不变（或者退回 RESEARCH？）这里保持 PLAN_GENERATED 之前的状态
                "planning_phase": PlanningPhase.PLANNING.value 
            }

    # ========== 后处理：验证距离并填充坐标 ==========
    itinerary = structured_plan.get("itinerary", [])
    
    # 为每个活动填充坐标
    for day in itinerary:
        for activity in day.get("activities", []):
            poi_id = activity.get("poi_id")
            if poi_id and poi_id in poi_pool:
                poi_data = poi_pool[poi_id]
                activity["location"] = {
                    "lat": poi_data.get("lat"),
                    "lng": poi_data.get("lng"),
                }
                # 如果没有 title，使用 POI 名称
                if not activity.get("title"):
                    activity["title"] = poi_data.get("name", "")
        
        # 填充住宿价格（从 POI 池中获取）
        accommodation = day.get("accommodation")
        if accommodation:
            poi_id = accommodation.get("poi_id")
            if poi_id and poi_id in poi_pool:
                poi_data = poi_pool[poi_id]
                # 如果没有价格，从 POI 数据中填充
                if not accommodation.get("price") and poi_data.get("price"):
                    accommodation["price"] = f"¥{poi_data['price']}/晚"
                # 如果没有名称，从 POI 数据中填充
                if not accommodation.get("name") and poi_data.get("name"):
                    accommodation["name"] = poi_data["name"]
            # 如果仍然没有价格，设置默认值
            if not accommodation.get("price"):
                # 根据预算等级设置默认价格
                default_prices = {
                    "budget": "¥150/晚",
                    "moderate": "¥300/晚",
                    "luxury": "¥800/晚",
                }
                accommodation["price"] = default_prices.get(budget_level, "¥300/晚")

        # 智能酒店重新分配：找到真正离第二天活动最近的酒店
        # 如果是最后一天，不需要住宿，但这里为了逻辑完整也可以算
        if accommodation and day.get("activities"):
            # 获取当天（或第二天）的活动重心
            # 策略：住宿是为了方便 *第二天* 的行程。
            # 但简单起见，且为了避免跨天索引越界，我们尽量选靠近 *当天结束地点* 或 *第二天开始地点* 的酒店。
            # 这里采用：选靠近 *当天最后活动* 的酒店，方便回酒店。或者选靠近 *当天大部分活动* 的位置。
            
            # 计算当天活动的重心
            act_lats = [a["location"]["lat"] for a in day["activities"] if a.get("location")]
            act_lngs = [a["location"]["lng"] for a in day["activities"] if a.get("location")]
            
            if act_lats and act_lngs:
                center_lat = sum(act_lats) / len(act_lats)
                center_lng = sum(act_lngs) / len(act_lngs)
                
                # 在 POI 池中找酒店
                hotels = [p for p in poi_pool.values() if p.get("category") == "hotel"]
                best_hotel = None
                min_dist = 99999
                
                for h in hotels:
                    if not h.get("lat") or not h.get("lng"):
                        continue
                    dist = _haversine(center_lat, center_lng, h["lat"], h["lng"])
                    if dist < min_dist:
                        min_dist = dist
                        best_hotel = h
                
                # 如果找到了更近的酒店（且距离差异显著，比如 < 5km vs > 10km），替换它
                # 但要注意 LLM 可能有自己的理由。这里我们强制优化"地理位置"。
                if best_hotel:
                     accommodation["poi_id"] = best_hotel.get("id") # 假设 id 在 values 里，其实 poi_pool key 就是 id
                     accommodation["name"] = best_hotel.get("name")
                     accommodation["price"] = f"¥{best_hotel.get('price', 300)}/晚"
                     accommodation["location"] = {"lat": best_hotel["lat"], "lng": best_hotel["lng"]}
    
    # 本地距离验证
    violations = validate_itinerary_distances(itinerary, max_distance_km=50.0)
    
    if violations:
        logger.warning("Distance violations detected", count=len(violations), violations=violations[:3])
        # 可以选择触发反思，这里先记录
        structured_plan["distance_warnings"] = violations

    # 构建旅游计划
    travel_plan = {
        "destination": destination,
        "generated_at": datetime.now().isoformat(),
        "structured": True,
        "poi_based": True,  # 标记为 POI 模式生成
        "chat_response": structured_plan.get("chat_response", ""),
        "itinerary": itinerary,
        "content": structured_plan.get("chat_response", ""),
        "budget_info": {
            "level": budget_level,
        },
    }

    updates = {
        "travel_plan": travel_plan,
        "planning_phase": PlanningPhase.PLAN_GENERATED.value,
        "next_action": "route_enrich",
        "updated_at": datetime.now().isoformat(),
    }

    logger.info(
        "POI-based plan generated",
        days=len(itinerary),
        distance_violations=len(violations) if violations else 0,
    )

    return updates


__all__ = ["planning_node"]
