"""
侧边栏数据服务

提供智囊侧边栏所需的数据：
- 天气预报（5天）
- 当地资讯
- 预算计算
"""

import structlog
from typing import Any

logger = structlog.get_logger()


async def get_weather_forecast(city: str) -> dict[str, Any]:
    """
    获取城市 5 天天气预报
    """
    from src.tools import get_weather
    
    try:
        weather_data = await get_weather.ainvoke({
            "city": city,
            "forecast": True
        })
        
        if "error" in weather_data:
            return {"error": weather_data["error"]}
        
        forecasts = weather_data.get("forecasts", [])
        
        # 格式化预报数据
        formatted = []
        for f in forecasts[:5]:
            formatted.append({
                "date": f.get("date", ""),
                "week": f.get("week", ""),
                "day_weather": f.get("dayweather", "晴"),
                "night_weather": f.get("nightweather", "晴"),
                "day_temp": f.get("daytemp", ""),
                "night_temp": f.get("nighttemp", ""),
                # 天气图标映射
                "icon": _get_weather_icon(f.get("dayweather", "")),
            })
        
        return {
            "city": weather_data.get("city", city),
            "forecasts": formatted,
        }
    except Exception as e:
        logger.warning("Weather forecast failed", city=city, error=str(e))
        return {"error": str(e)}


def _get_weather_icon(weather: str) -> str:
    """根据天气文字返回图标"""
    if "雨" in weather:
        return "🌧️"
    if "雪" in weather:
        return "🌨️"
    if "阴" in weather:
        return "☁️"
    if "云" in weather:
        return "⛅"
    if "雾" in weather or "霾" in weather:
        return "🌫️"
    if "雷" in weather:
        return "⛈️"
    return "☀️"


async def get_local_news(city: str) -> list[dict[str, Any]]:
    """
    获取目的地当地资讯 - 旅游相关、安全、新鲜
    """
    from src.tools import web_search
    from datetime import datetime
    
    current_year = datetime.now().year
    
    try:
        # 优化搜索查询 - 聚焦于当前年份和旅游相关内容
        queries = [
            f"{city} 景区 开放时间 门票 {current_year}",
            f"{city} 旅游攻略 必去景点 {current_year}",
            f"{city} 美食 特色小吃 推荐",
        ]
        
        news_items = []
        
        for query in queries:
            try:
                results = await web_search.ainvoke({
                    "query": query,
                    "count": 5,
                    "freshness": "week"  # 改回一周，确保新鲜度
                })
                
                for r in results.get("results", [])[:3]:
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    url = r.get("url", "")
                    
                    # 过滤不安全或不相关的内容
                    if not _is_safe_url(url):
                        continue
                    if not _is_travel_relevant(title, snippet):
                        continue
                    
                    # 截断过长标题
                    if len(title) > 40:
                        title = title[:37] + "..."
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "source": r.get("source", ""),
                        "snippet": snippet[:100] if snippet else "",
                        "category": _categorize_news(query, title, snippet),
                    })
            except Exception as e:
                logger.warning(f"Search failed for query: {query}", error=str(e))
        
        # 去重并限制数量
        seen = set()
        unique_news = []
        for item in news_items:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique_news.append(item)
        
        return unique_news[:6]
    except Exception as e:
        logger.warning("Local news fetch failed", city=city, error=str(e))
        return []


def _is_safe_url(url: str) -> bool:
    """判断URL是否安全可信"""
    if not url:
        return False
    
    # 必须是 HTTPS
    if not url.startswith("https://"):
        return False
    
    # 排除可疑域名
    suspicious_patterns = [
        "ads.", "ad.", "tracker.", "click.",
        ".xyz", ".top", ".loan", ".work",
    ]
    url_lower = url.lower()
    for pattern in suspicious_patterns:
        if pattern in url_lower:
            return False
    
    # 优先可信来源
    trusted_domains = [
        "baidu.com", "sohu.com", "sina.com", "163.com",
        "qq.com", "ctrip.com", "mafengwo.cn", "dianping.com",
        "xiaohongshu.com", "douyin.com", "weixin.qq.com",
        "gov.cn", "china.com", "xinhua",
    ]
    for domain in trusted_domains:
        if domain in url_lower:
            return True
    
    return True  # 默认信任


def _is_travel_relevant(title: str, snippet: str) -> bool:
    """判断内容是否与旅游相关"""
    text = (title + " " + snippet).lower()
    
    # 排除无关内容
    exclude_keywords = ["招聘", "房价", "楼盘", "股票", "政策", "会议", "领导", "政府"]
    for kw in exclude_keywords:
        if kw in text:
            return False
    
    # 包含旅游相关关键词
    travel_keywords = ["景点", "景区", "旅游", "游玩", "门票", "攻略", "打卡", 
                       "酒店", "美食", "特色", "推荐", "必去", "网红", "体验"]
    for kw in travel_keywords:
        if kw in text:
            return True
    
    return True  # 默认保留


def _categorize_news(query: str, title: str, snippet: str = "") -> str:
    """分类资讯类型"""
    text = title + " " + snippet
    
    # 景点相关
    if any(kw in text for kw in ["景点", "景区", "打卡", "网红", "必去"]):
        return "attractions"
    
    # 活动/节庆
    if any(kw in text for kw in ["活动", "节庆", "文化节", "演出", "展览"]):
        return "events"
    
    # 交通
    if any(kw in text for kw in ["交通", "地铁", "公交", "机场", "高铁"]):
        return "transport"
    
    # 攻略
    if any(kw in text for kw in ["攻略", "推荐", "注意事项", "小贴士"]):
        return "tips"
    
    return "general"


def calculate_budget_breakdown(itinerary: list, destination: str) -> dict[str, Any]:
    """
    从行程数据计算预算分解
    """
    accommodation_cost = 0
    ticket_cost = 0
    transport_cost = 0
    food_cost = 0
    
    days = len(itinerary) if itinerary else 3
    nights = max(days - 1, 1)
    
    for day in itinerary:
        # 住宿费用
        accommodation = day.get("accommodation", {})
        if accommodation:
            price_str = accommodation.get("price", "")
            # 从 "¥320起" 提取数字
            if price_str:
                import re
                match = re.search(r"(\d+)", price_str)
                if match:
                    accommodation_cost += int(match.group(1))
        
        # 门票费用（从活动描述中估算）
        for activity in day.get("activities", []):
            title = activity.get("title", "")
            desc = activity.get("desc", "")
            
            # 常见景点门票估算
            if any(kw in title for kw in ["故宫", "颐和园", "长城", "天坛"]):
                ticket_cost += 60
            elif any(kw in title for kw in ["环球影城", "迪士尼", "欢乐谷"]):
                ticket_cost += 500
            elif any(kw in title for kw in ["博物馆", "纪念馆"]):
                ticket_cost += 20
            elif any(kw in title for kw in ["公园", "广场"]):
                ticket_cost += 10
            else:
                ticket_cost += 30  # 默认估算
            
            # 交通费用
            transport = activity.get("transport_from_prev", {})
            if transport:
                method = transport.get("method", "")
                if "地铁" in method or "公交" in method:
                    transport_cost += 5
                elif "打车" in method or "出租" in method:
                    transport_cost += 50
                else:
                    transport_cost += 3
    
    # 餐饮估算：每天每人 100-150 元
    food_cost = days * 120
    
    total = accommodation_cost + ticket_cost + transport_cost + food_cost
    
    return {
        "breakdown": {
            "accommodation": accommodation_cost,
            "tickets": ticket_cost,
            "transport": transport_cost,
            "food": food_cost,
        },
        "total_estimated": total,
        "per_day": round(total / days) if days > 0 else 0,
        "nights": nights,
        "days": days,
    }
