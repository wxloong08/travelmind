"""
图片服务 - 严格遵循 PRD 2.4.1 优先级

优先级顺序：
1. 预设热门城市图片（本地/CDN）
2. 搜索引擎图片 API（谷歌图片搜索）
3. Unsplash API
4. AI 生成（暂不实现，成本高）
5. 默认占位图

使用方法：
    from src.services.image_service import image_service
    
    # 获取城市海报背景
    result = await image_service.get_city_image("北京", "poster_bg")
    # result = {"url": "...", "source": "preset", "city": "北京"}
    
    # 获取景点图片
    result = await image_service.get_attraction_image("故宫", "北京")
"""

import os
import structlog
import httpx
from typing import Optional, Literal

logger = structlog.get_logger()


# ============================================================
# 1. 预设热门城市图片（使用稳定的 Unsplash 直链，非 Source API）
# ============================================================

PRESET_CITY_IMAGES = {
    # ===== 一线旅游城市 =====
    "北京": {
        "landmark": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=400&h=300&fit=crop&q=80",
        "地标": "天安门/故宫",
    },
    "上海": {
        "landmark": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1538428494232-9c0d8a3ab403?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=400&h=300&fit=crop&q=80",
        "地标": "外滩/陆家嘴",
    },
    "杭州": {
        "landmark": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=400&h=300&fit=crop&q=80",
        "地标": "西湖",
    },
    "成都": {
        "landmark": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=400&h=300&fit=crop&q=80",
        "地标": "大熊猫/宽窄巷子",
    },
    "西安": {
        "landmark": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=400&h=300&fit=crop&q=80",
        "地标": "兵马俑",
    },
    "重庆": {
        "landmark": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=400&h=300&fit=crop&q=80",
        "地标": "洪崖洞",
    },
    "广州": {
        "landmark": "https://images.unsplash.com/photo-1583996607484-883ac1ed28a5?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1583996607484-883ac1ed28a5?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1583996607484-883ac1ed28a5?w=400&h=300&fit=crop&q=80",
        "地标": "广州塔",
    },
    "深圳": {
        "landmark": "https://images.unsplash.com/photo-1534274867514-d5b47ef89ed7?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1534274867514-d5b47ef89ed7?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1534274867514-d5b47ef89ed7?w=400&h=300&fit=crop&q=80",
        "地标": "深圳湾",
    },
    
    # ===== 热门旅游城市 =====
    "三亚": {
        "landmark": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=400&h=300&fit=crop&q=80",
        "地标": "亚龙湾",
    },
    "厦门": {
        "landmark": "https://images.unsplash.com/photo-1569154941061-e231b4725ef1?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1569154941061-e231b4725ef1?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1569154941061-e231b4725ef1?w=400&h=300&fit=crop&q=80",
        "地标": "鼓浪屿",
    },
    "青岛": {
        "landmark": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=400&h=300&fit=crop&q=80",
        "地标": "栈桥",
    },
    "大理": {
        "landmark": "https://images.unsplash.com/photo-1582920980795-2f97b0834c59?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1582920980795-2f97b0834c59?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1582920980795-2f97b0834c59?w=400&h=300&fit=crop&q=80",
        "地标": "洱海",
    },
    "丽江": {
        "landmark": "https://images.unsplash.com/photo-1528181304800-259b08848526?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1528181304800-259b08848526?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1528181304800-259b08848526?w=400&h=300&fit=crop&q=80",
        "地标": "古城/玉龙雪山",
    },
    "桂林": {
        "landmark": "https://images.unsplash.com/photo-1537531383496-f4749b8032cf?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1537531383496-f4749b8032cf?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1537531383496-f4749b8032cf?w=400&h=300&fit=crop&q=80",
        "地标": "漓江/象鼻山",
    },
    "黄山": {
        "landmark": "https://images.unsplash.com/photo-1513415756790-2ac1db1297d0?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1513415756790-2ac1db1297d0?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1513415756790-2ac1db1297d0?w=400&h=300&fit=crop&q=80",
        "地标": "黄山云海",
    },
    "张家界": {
        "landmark": "https://images.unsplash.com/photo-1518709414768-a88981a4515d?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1518709414768-a88981a4515d?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1518709414768-a88981a4515d?w=400&h=300&fit=crop&q=80",
        "地标": "天门山",
    },
    "拉萨": {
        "landmark": "https://images.unsplash.com/photo-1516545595035-b503f250f8ce?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1516545595035-b503f250f8ce?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1516545595035-b503f250f8ce?w=400&h=300&fit=crop&q=80",
        "地标": "布达拉宫",
    },
    "南京": {
        "landmark": "https://images.unsplash.com/photo-1599571234909-29ed5d1321d6?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1599571234909-29ed5d1321d6?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1599571234909-29ed5d1321d6?w=400&h=300&fit=crop&q=80",
        "地标": "中山陵",
    },
    "苏州": {
        "landmark": "https://images.unsplash.com/photo-1584466990297-a25c4e31d028?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1584466990297-a25c4e31d028?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584466990297-a25c4e31d028?w=400&h=300&fit=crop&q=80",
        "地标": "拙政园",
    },
    
    # ===== 国际热门城市 =====
    "东京": {
        "landmark": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=400&h=300&fit=crop&q=80",
        "地标": "东京塔/浅草寺",
    },
    "大阪": {
        "landmark": "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=400&h=300&fit=crop&q=80",
        "地标": "大阪城",
    },
    "京都": {
        "landmark": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=400&h=300&fit=crop&q=80",
        "地标": "金阁寺/伏见稻荷",
    },
    "香港": {
        "landmark": "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=400&h=300&fit=crop&q=80",
        "地标": "维多利亚港",
    },
    "新加坡": {
        "landmark": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=400&h=300&fit=crop&q=80",
        "地标": "滨海湾金沙",
    },
    "曼谷": {
        "landmark": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=400&h=300&fit=crop&q=80",
        "地标": "大皇宫",
    },
    "巴黎": {
        "landmark": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&h=300&fit=crop&q=80",
        "地标": "埃菲尔铁塔",
    },
    "伦敦": {
        "landmark": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=400&h=300&fit=crop&q=80",
        "地标": "大本钟",
    },
    "纽约": {
        "landmark": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=400&h=300&fit=crop&q=80",
        "地标": "自由女神像/时代广场",
    },
}


# ============================================================
# 2. 预设热门景点图片
# ============================================================

PRESET_ATTRACTION_IMAGES = {
    # 北京景点
    "故宫": "https://images.unsplash.com/photo-1584266032559-fe1c6b1db6fa?w=800&h=600&fit=crop&q=80",
    "故宫博物院": "https://images.unsplash.com/photo-1584266032559-fe1c6b1db6fa?w=800&h=600&fit=crop&q=80",
    "天安门": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=800&h=600&fit=crop&q=80",
    "天安门广场": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=800&h=600&fit=crop&q=80",
    "长城": "https://images.unsplash.com/photo-1549893072-4bc678117f45?w=800&h=600&fit=crop&q=80",
    "八达岭长城": "https://images.unsplash.com/photo-1549893072-4bc678117f45?w=800&h=600&fit=crop&q=80",
    "颐和园": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=800&h=600&fit=crop&q=80",
    "天坛": "https://images.unsplash.com/photo-1548707309-dcebeab9ea9b?w=800&h=600&fit=crop&q=80",
    "圆明园": "https://images.unsplash.com/photo-1587381420270-9c2f80628e50?w=800&h=600&fit=crop&q=80",
    "北京环球影城": "https://images.unsplash.com/photo-1560184611-ff3e53f00e8f?w=800&h=600&fit=crop&q=80",
    "环球影城": "https://images.unsplash.com/photo-1560184611-ff3e53f00e8f?w=800&h=600&fit=crop&q=80",
    "景山公园": "https://images.unsplash.com/photo-1603095847536-a1f897cfb2b7?w=800&h=600&fit=crop&q=80",
    "王府井": "https://images.unsplash.com/photo-1591105575527-bf4ce9b8ae83?w=800&h=600&fit=crop&q=80",
    "南锣鼓巷": "https://images.unsplash.com/photo-1590117756873-2f7085e36bb2?w=800&h=600&fit=crop&q=80",
    "鸟巢": "https://images.unsplash.com/photo-1588416499323-4a3d9aee35d1?w=800&h=600&fit=crop&q=80",
    "国家博物馆": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=800&h=600&fit=crop&q=80",
    
    # 上海景点
    "外滩": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=800&h=600&fit=crop&q=80",
    "东方明珠": "https://images.unsplash.com/photo-1548919973-5cef591cdbc9?w=800&h=600&fit=crop&q=80",
    "陆家嘴": "https://images.unsplash.com/photo-1538428494232-9c0d8a3ab403?w=800&h=600&fit=crop&q=80",
    "迪士尼": "https://images.unsplash.com/photo-1533514114760-4180fbd5f8b2?w=800&h=600&fit=crop&q=80",
    "上海迪士尼": "https://images.unsplash.com/photo-1533514114760-4180fbd5f8b2?w=800&h=600&fit=crop&q=80",
    "豫园": "https://images.unsplash.com/photo-1567581750978-2a47a6cbf91d?w=800&h=600&fit=crop&q=80",
    "城隍庙": "https://images.unsplash.com/photo-1567581750978-2a47a6cbf91d?w=800&h=600&fit=crop&q=80",
    "南京路步行街": "https://images.unsplash.com/photo-1568789489449-1b86eec7d3d6?w=800&h=600&fit=crop&q=80",
    
    # 杭州景点
    "西湖": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=800&h=600&fit=crop&q=80",
    "雷峰塔": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=800&h=600&fit=crop&q=80",
    "灵隐寺": "https://images.unsplash.com/photo-1609139003551-ee40f5f73ec0?w=800&h=600&fit=crop&q=80",
    "断桥": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=800&h=600&fit=crop&q=80",
    
    # 西安景点
    "兵马俑": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&h=600&fit=crop&q=80",
    "秦始皇兵马俑": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&h=600&fit=crop&q=80",
    "大雁塔": "https://images.unsplash.com/photo-1560452992-6e4e2e6af3d3?w=800&h=600&fit=crop&q=80",
    "西安城墙": "https://images.unsplash.com/photo-1560452992-6e4e2e6af3d3?w=800&h=600&fit=crop&q=80",
    "回民街": "https://images.unsplash.com/photo-1548102268-a0e6f48a47a6?w=800&h=600&fit=crop&q=80",
    "华清池": "https://images.unsplash.com/photo-1560452992-6e4e2e6af3d3?w=800&h=600&fit=crop&q=80",
    
    # 成都景点
    "大熊猫基地": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=800&h=600&fit=crop&q=80",
    "熊猫基地": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=800&h=600&fit=crop&q=80",
    "宽窄巷子": "https://images.unsplash.com/photo-1599115706536-46dac19d7ceb?w=800&h=600&fit=crop&q=80",
    "锦里": "https://images.unsplash.com/photo-1599115706536-46dac19d7ceb?w=800&h=600&fit=crop&q=80",
    "武侯祠": "https://images.unsplash.com/photo-1599115706536-46dac19d7ceb?w=800&h=600&fit=crop&q=80",
    "都江堰": "https://images.unsplash.com/photo-1594729095896-a9b7b9ed31eb?w=800&h=600&fit=crop&q=80",
    
    # 重庆景点
    "洪崖洞": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=800&h=600&fit=crop&q=80",
    "解放碑": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=800&h=600&fit=crop&q=80",
    "磁器口": "https://images.unsplash.com/photo-1590117756873-2f7085e36bb2?w=800&h=600&fit=crop&q=80",
    "长江索道": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=800&h=600&fit=crop&q=80",
    
    # 其他热门景点
    "布达拉宫": "https://images.unsplash.com/photo-1516545595035-b503f250f8ce?w=800&h=600&fit=crop&q=80",
    "鼓浪屿": "https://images.unsplash.com/photo-1569154941061-e231b4725ef1?w=800&h=600&fit=crop&q=80",
    "洱海": "https://images.unsplash.com/photo-1582920980795-2f97b0834c59?w=800&h=600&fit=crop&q=80",
    "玉龙雪山": "https://images.unsplash.com/photo-1528181304800-259b08848526?w=800&h=600&fit=crop&q=80",
    "漓江": "https://images.unsplash.com/photo-1537531383496-f4749b8032cf?w=800&h=600&fit=crop&q=80",
}


# ============================================================
# 3. 默认占位图 - 使用 Lorem Picsum（高度可靠）
# ============================================================

DEFAULT_IMAGES = {
    # Lorem Picsum 使用 seed 确保每次返回相同图片
    "landmark": "https://picsum.photos/seed/travel-landmark/1200/800",
    "poster_bg": "https://picsum.photos/seed/travel-poster/800/1200",
    "thumbnail": "https://picsum.photos/seed/travel-thumb/400/300",
    "attraction": "https://picsum.photos/seed/travel-attraction/800/600",
    "hotel": "https://picsum.photos/seed/travel-hotel/800/600",
}


# ============================================================
# 4. 图片服务类
# ============================================================

ImageType = Literal["landmark", "poster_bg", "thumbnail", "attraction", "hotel"]


class ImageService:
    """
    图片服务 - 严格遵循 PRD 2.4.1 优先级
    
    优先级：预设 → Google Custom Search → Unsplash API → 默认
    """
    
    def __init__(self):
        # Google Custom Search API（免费 100次/天）
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        # Unsplash API
        self.unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    
    async def get_city_image(
        self, 
        city: str, 
        image_type: ImageType = "landmark"
    ) -> dict:
        """
        获取城市图片
        
        Args:
            city: 城市名称
            image_type: 图片类型 (landmark|poster_bg|thumbnail)
        
        Returns:
            {"url": str, "source": str, "city": str}
        """
        logger.info("Getting city image", city=city, type=image_type)
        
        # ===== 优先级 1: 预设高质量图片 =====
        # 热门城市使用经过验证的 Unsplash 直链
        result = self._get_preset_city_image(city, image_type)
        if result:
            logger.info("Using preset image", city=city, source="preset")
            return result
        
        # ===== 优先级 2: Google Custom Search API =====
        if self.google_api_key and self.google_search_engine_id:
            result = await self._search_google_image(f"{city} landmark travel")
            if result:
                logger.info("Using Google image", city=city, source="google")
                return {
                    "url": result,
                    "source": "google",
                    "city": city,
                }
        
        # ===== 优先级 3: Unsplash API 搜索 =====
        if self.unsplash_access_key:
            result = await self._search_unsplash_image(f"{city} landmark")
            if result:
                logger.info("Using Unsplash API image", city=city, source="unsplash")
                return {
                    "url": result,
                    "source": "unsplash",
                    "city": city,
                }
        
        # ===== 优先级 4: 默认占位图 =====
        logger.info("Using default image", city=city, source="default")
        return {
            "url": DEFAULT_IMAGES.get(image_type, DEFAULT_IMAGES["landmark"]),
            "source": "default",
            "city": city,
        }
    
    async def get_attraction_image(
        self, 
        attraction_name: str, 
        city: str = ""
    ) -> dict:
        """
        获取景点图片
        
        优先级：预设景点 → Google → Unsplash → 默认
        
        Args:
            attraction_name: 景点名称
            city: 所在城市（用于搜索）
        
        Returns:
            {"url": str, "source": str, "attraction": str}
        """
        logger.info("Getting attraction image", attraction=attraction_name, city=city)
        
        # ===== 优先级 1: 预设景点图片（Unsplash 直链）=====
        result = self._get_preset_attraction_image(attraction_name)
        if result:
            logger.info("Using preset attraction image", attraction=attraction_name)
            return result
        
        # ===== 优先级 2: Google Custom Search API =====
        if self.google_api_key and self.google_search_engine_id:
            query = f"{attraction_name} {city} landmark".strip() if city else f"{attraction_name} landmark"
            result = await self._search_google_image(query)
            if result:
                logger.info("Using Google attraction image", attraction=attraction_name)
                return {
                    "url": result,
                    "source": "google",
                    "attraction": attraction_name,
                }
        
        # ===== 优先级 3: Unsplash API 搜索 =====
        if self.unsplash_access_key:
            query = f"{attraction_name} {city}".strip() if city else attraction_name
            result = await self._search_unsplash_image(query)
            if result:
                logger.info("Using Unsplash attraction image", attraction=attraction_name)
                return {
                    "url": result,
                    "source": "unsplash",
                    "attraction": attraction_name,
                }
        
        # ===== 优先级 4: 默认占位图 =====
        logger.info("Using default attraction image", attraction=attraction_name)
        return {
            "url": DEFAULT_IMAGES["attraction"],
            "source": "default",
            "attraction": attraction_name,
        }
    
    def _get_preset_city_image(self, city: str, image_type: str) -> dict | None:
        """检查预设城市图片"""
        # 精确匹配
        if city in PRESET_CITY_IMAGES:
            data = PRESET_CITY_IMAGES[city]
            if image_type in data:
                return {
                    "url": data[image_type],
                    "source": "preset",
                    "city": city,
                    "地标": data.get("地标", ""),
                }
        
        # 模糊匹配（如"北京市" → "北京"）
        for key, data in PRESET_CITY_IMAGES.items():
            if key in city or city in key:
                if image_type in data:
                    return {
                        "url": data[image_type],
                        "source": "preset",
                        "city": key,
                        "地标": data.get("地标", ""),
                    }
        
        return None
    
    def _get_preset_attraction_image(self, attraction_name: str) -> dict | None:
        """检查预设景点图片"""
        # 精确匹配
        if attraction_name in PRESET_ATTRACTION_IMAGES:
            return {
                "url": PRESET_ATTRACTION_IMAGES[attraction_name],
                "source": "preset",
                "attraction": attraction_name,
            }
        
        # 模糊匹配
        for key, url in PRESET_ATTRACTION_IMAGES.items():
            if key in attraction_name or attraction_name in key:
                return {
                    "url": url,
                    "source": "preset",
                    "attraction": key,
                }
        
        return None
    
    async def _search_google_image(self, query: str) -> str | None:
        """
        Google Custom Search API 图片搜索
        
        免费额度：每天 100 次查询
        需要配置：GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID
        """
        if not self.google_api_key or not self.google_search_engine_id:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.google_search_engine_id,
                        "q": query,
                        "searchType": "image",
                        "num": 1,
                        "imgSize": "large",
                        "imgType": "photo",
                        "safe": "active",
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        return items[0].get("link")
        
        except Exception as e:
            logger.warning("Google image search failed", query=query, error=str(e))
        
        return None
    
    async def _search_unsplash_image(self, query: str) -> str | None:
        """Unsplash 图片搜索"""
        # 如果有 API key，使用官方 API
        if self.unsplash_access_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        "https://api.unsplash.com/search/photos",
                        headers={"Authorization": f"Client-ID {self.unsplash_access_key}"},
                        params={
                            "query": query,
                            "per_page": 1,
                            "orientation": "landscape",
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("results"):
                            return data["results"][0]["urls"]["regular"]
            
            except Exception as e:
                logger.warning("Unsplash API search failed", query=query, error=str(e))
        
        # 备选：使用 Source API（不稳定，但不需要 key）
        # 注意：这个 API 不是很稳定，建议配置正式的 API key
        try:
            # 构建 Source API URL
            keywords = query.replace(" ", ",").replace("　", ",")
            source_url = f"https://source.unsplash.com/800x600/?{keywords}"
            
            # 验证 URL 是否有效（HEAD 请求）
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.head(source_url)
                if response.status_code == 200:
                    # Source API 会重定向到实际图片
                    return str(response.url)
        
        except Exception as e:
            logger.warning("Unsplash Source API failed", query=query, error=str(e))
        
        return None


# 全局实例
image_service = ImageService()


# ============================================================
# 5. API 路由（可选，用于前端调用）
# ============================================================

def register_image_routes(app):
    """注册图片 API 路由"""
    from fastapi import APIRouter, Query
    
    router = APIRouter(prefix="/api/v1/images", tags=["images"])
    
    @router.get("/city/{city_name}")
    async def get_city_image_api(
        city_name: str,
        type: ImageType = Query(default="landmark")
    ):
        """获取城市图片"""
        return await image_service.get_city_image(city_name, type)
    
    @router.get("/attraction")
    async def get_attraction_image_api(
        name: str = Query(..., description="景点名称"),
        city: str = Query(default="", description="所在城市")
    ):
        """获取景点图片"""
        return await image_service.get_attraction_image(name, city)
    
    app.include_router(router)