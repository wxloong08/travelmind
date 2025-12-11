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
import random
import structlog
import httpx
from typing import Optional, Literal

logger = structlog.get_logger()


# ============================================================
# 1. 预设热门城市图片（使用稳定的 Unsplash 直链，非 Source API）
# ============================================================

PRESET_CITY_IMAGES = {
    "北京": {
        "landmark": "https://images.unsplash.com/photo-1616918129099-077a09f0716c?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1616918129099-077a09f0716c?w=1200&h=1800&fit=crop&q=90",
            "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/30836815/pexels-photo-30836815.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1616918129099-077a09f0716c?w=600&h=400&fit=crop&q=90",
        "地标": "天安门/长城/故宫/天坛",
    },
    "上海": {
        "landmark": "https://images.unsplash.com/photo-1548919973-5cef591cdbc9?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1548919973-5cef591cdbc9?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/7994514/pexels-photo-7994514.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1548919973-5cef591cdbc9?w=600&h=400&fit=crop&q=90",
        "地标": "外滩/陆家嘴/东方明珠/上海塔",
    },
    "杭州": {
        "landmark": "https://images.unsplash.com/photo-1639923193576-250cf967da51?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1639923193576-250cf967da51?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1639923193576-250cf967da51?w=600&h=400&fit=crop&q=90",
        "地标": "西湖/雷峰塔",
    },
    "成都": {
        "landmark": "https://images.unsplash.com/photo-1527118732049-c88155f2107c?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1527118732049-c88155f2107c?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1527118732049-c88155f2107c?w=600&h=400&fit=crop&q=90",
        "地标": "大熊猫/宽窄巷子/锦里",
    },
    "西安": {
        "landmark": "https://images.unsplash.com/photo-1527922751658-fdc12370761e?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1527922751658-fdc12370761e?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1527922751658-fdc12370761e?w=600&h=400&fit=crop&q=90",
        "地标": "兵马俑/大雁塔",
    },
    "重庆": {
        "landmark": "https://images.unsplash.com/photo-1676901976028-6a6589da1364?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1676901976028-6a6589da1364?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/14062542/pexels-photo-14062542.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1676901976028-6a6589da1364?w=600&h=400&fit=crop&q=90",
        "地标": "洪崖洞/解放碑/长江索道",
    },
    "广州": {
        "landmark": "https://images.unsplash.com/photo-1656531231697-4084cb4b91f3?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1656531231697-4084cb4b91f3?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1656531231697-4084cb4b91f3?w=600&h=400&fit=crop&q=90",
        "地标": "广州塔/珠江新城",
    },
    "深圳": {
        "landmark": "https://images.unsplash.com/photo-1661178581714-a344b67c8691?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1661178581714-a344b67c8691?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1661178581714-a344b67c8691?w=600&h=400&fit=crop&q=90",
        "地标": "深圳湾",
    },
    "厦门": {
        "landmark": "https://images.pexels.com/photos/2192854/pexels-photo-2192854.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1280&fit=crop",
        "poster_bg": [
            "https://images.pexels.com/photos/2192854/pexels-photo-2192854.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/20265634/pexels-photo-20265634.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.pexels.com/photos/2192854/pexels-photo-2192854.jpeg?auto=compress&cs=tinysrgb&w=600&h=400&fit=crop",
        "地标": "鼓浪屿/厦门大学",
    },
    "青岛": {
        "landmark": "https://images.unsplash.com/photo-1739436598532-f22747099b6f?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1739436598532-f22747099b6f?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1739436598532-f22747099b6f?w=600&h=400&fit=crop&q=90",
        "地标": "栈桥",
    },
    "大理": {
        "landmark": "https://images.unsplash.com/photo-1678278949517-1e7888e810cc?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1678278949517-1e7888e810cc?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/14321306/pexels-photo-14321306.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/14592485/pexels-photo-14592485.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1678278949517-1e7888e810cc?w=600&h=400&fit=crop&q=90",
        "地标": "洱海/大理古城/崇圣寺三塔",
    },
    "丽江": {
        "landmark": "https://images.pexels.com/photos/8936979/pexels-photo-8936979.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1280&fit=crop",
        "poster_bg": [
            "https://images.pexels.com/photos/8936979/pexels-photo-8936979.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/2408632/pexels-photo-2408632.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.pexels.com/photos/8936979/pexels-photo-8936979.jpeg?auto=compress&cs=tinysrgb&w=600&h=400&fit=crop",
        "地标": "古城/玉龙雪山",
    },
    "桂林": {
        "landmark": "https://images.unsplash.com/photo-1588423886412-914102b72f96?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1588423886412-914102b72f96?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/20370740/pexels-photo-20370740.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/2161929/pexels-photo-2161929.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1588423886412-914102b72f96?w=600&h=400&fit=crop&q=90",
        "地标": "漓江/象鼻山/龙脊梯田",
    },
    "黄山": {
        "landmark": "https://images.unsplash.com/photo-1591116446368-2078ad1c0fea?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1591116446368-2078ad1c0fea?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1591116446368-2078ad1c0fea?w=600&h=400&fit=crop&q=90",
        "地标": "黄山云海",
    },
    "张家界": {
        "landmark": "https://images.unsplash.com/photo-1738579945323-8c78c9a1a27f?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1738579945323-8c78c9a1a27f?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/6139687/pexels-photo-6139687.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/29073775/pexels-photo-29073775.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/34683513/pexels-photo-34683513.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1738579945323-8c78c9a1a27f?w=600&h=400&fit=crop&q=90",
        "地标": "天门山/武陵源/张家界国家森林公园/张家界大峡谷",
    },
    "拉萨": {
        "landmark": "https://images.unsplash.com/photo-1701913997567-746dd137eff6?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": [
            "https://images.unsplash.com/photo-1701913997567-746dd137eff6?w=1200&h=1800&fit=crop&q=90",
            "https://images.pexels.com/photos/16154562/pexels-photo-16154562.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.unsplash.com/photo-1701913997567-746dd137eff6?w=600&h=400&fit=crop&q=90",
        "地标": "布达拉宫/大昭寺",
    },
    "南京": {
        "landmark": "https://images.pexels.com/photos/11792973/pexels-photo-11792973.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1280&fit=crop",
        "poster_bg": [
            "https://images.pexels.com/photos/11792973/pexels-photo-11792973.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/35022548/pexels-photo-35022548.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/35132919/pexels-photo-35132919.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/20848052/pexels-photo-20848052.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
            "https://images.pexels.com/photos/19042554/pexels-photo-19042554.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1800&fit=crop",
        ],
        "thumbnail": "https://images.pexels.com/photos/11792973/pexels-photo-11792973.jpeg?auto=compress&cs=tinysrgb&w=600&h=400&fit=crop",
        "地标": "中山陵/玄武湖/夫子庙/明孝陵/栖霞寺",
    },
    "苏州": {
        "landmark": "https://images.unsplash.com/photo-1692193793062-8e13784f326b?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1692193793062-8e13784f326b?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1692193793062-8e13784f326b?w=600&h=400&fit=crop&q=90",
        "地标": "拙政园/留园",
    },
    "香港": {
        "landmark": "https://images.unsplash.com/photo-1690070767302-86a0f719a36f?w=1920&h=1280&fit=crop&q=90",
        "poster_bg": "https://images.unsplash.com/photo-1690070767302-86a0f719a36f?w=1200&h=1800&fit=crop&q=90",
        "thumbnail": "https://images.unsplash.com/photo-1690070767302-86a0f719a36f?w=600&h=400&fit=crop&q=90",
        "地标": "维多利亚港/香港迪士尼",
    },
    # ===== 国际热门城市 =====
    "东京": {
        "landmark": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=400&h=300&fit=crop&q=80",
        "地标": "东京塔/浅草寺/上野公园/东京迪士尼",
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
        "地标": "金阁寺/伏见稻荷大社/清水寺/岚山",
    },
    "新加坡": {
        "landmark": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=400&h=300&fit=crop&q=80",
        "地标": "滨海湾金沙/新加坡动物园/新加坡植物园",
    },
    "曼谷": {
        "landmark": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=400&h=300&fit=crop&q=80",
        "地标": "大皇宫/曼谷夜景/暹罗广场",
    },
    "巴黎": {
        "landmark": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1200&h=800&fit=crop&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&h=1200&fit=crop&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&h=300&fit=crop&q=80",
        "地标": "埃菲尔铁塔/巴黎圣母院/卢浮宫",
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
        "地标": "自由女神像/时代广场/帝国大厦",
    },
}


# ============================================================
# 2. 预设热门景点图片
# ============================================================

PRESET_ATTRACTION_IMAGES = {
    # 北京景点
    "故宫": "https://images.unsplash.com/photo-1757510181446-9bae2ff1a70f?w=1920&h=1280&fit=crop&q=90",
    "故宫博物院": "https://images.pexels.com/photos/34449585/pexels-photo-34449585.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1280&fit=crop",
    "天安门": "https://images.unsplash.com/photo-1595445428220-95c9429c6005?w=1920&h=1280&fit=crop&q=90",
    "天安门广场": "https://images.unsplash.com/photo-1595445428220-95c9429c6005?w=1920&h=1280&fit=crop&q=90",
    "长城": "https://images.unsplash.com/photo-1509195070461-b99ef33ceb67?w=1920&h=1280&fit=crop&q=90",
    "八达岭长城": "https://images.unsplash.com/photo-1509195070461-b99ef33ceb67?w=1920&h=1280&fit=crop&q=90",
    "颐和园": "https://images.unsplash.com/photo-1669382485231-ef86d9fa986f?w=1920&h=1280&fit=crop&q=90",
    "天坛": "https://images.unsplash.com/photo-1584872589930-e99fe5bf4408?w=1920&h=1280&fit=crop&q=90",
    "圆明园": "https://images.unsplash.com/photo-1660531076440-f92c01c325d0?w=1920&h=1280&fit=crop&q=90",
    "北京环球影城": "https://images.pexels.com/photos/34042832/pexels-photo-34042832.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1280&fit=crop",
    "环球影城": "https://images.pexels.com/photos/34042832/pexels-photo-34042832.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1280&fit=crop",
    "景山公园": "https://images.unsplash.com/photo-1628001204260-c5df3cc58f02?w=1920&h=1280&fit=crop&q=90",
    "南锣鼓巷": "https://images.unsplash.com/photo-1683820251709-08259527a456?w=1920&h=1280&fit=crop&q=90",
    "鸟巢": "https://images.unsplash.com/photo-1708962817931-cfc91e2830a3?w=1920&h=1280&fit=crop&q=90",
    
    # 上海景点
    "外滩": "https://images.unsplash.com/photo-1695633537524-d1d5d070ff9a?w=1920&h=1280&fit=crop&q=90",
    "东方明珠": "https://images.unsplash.com/photo-1714902926881-5cf4044dfd72?w=1920&h=1280&fit=crop&q=90",
    "陆家嘴": "https://images.unsplash.com/photo-1635832543205-63a3f4875cfb?w=1920&h=1280&fit=crop&q=90",
    "迪士尼": "https://images.unsplash.com/photo-1725627238535-add439c94292?w=1920&h=1280&fit=crop&q=90",
    "上海迪士尼": "https://images.unsplash.com/photo-1725627238535-add439c94292?w=1920&h=1280&fit=crop&q=90",
    "豫园": "https://images.unsplash.com/photo-1707235459783-c609f5efd679?w=1920&h=1280&fit=crop&q=90",
    
    # 杭州景点
    "西湖": "https://images.unsplash.com/photo-1711700320048-76fb7bed9232?w=1920&h=1280&fit=crop&q=90",
    "雷峰塔": "https://images.unsplash.com/photo-1696513778713-6f00226ba810?w=1920&h=1280&fit=crop&q=90",
    "灵隐寺": "https://images.unsplash.com/photo-1753365001548-6e802da329e6?w=1920&h=1280&fit=crop&q=90",
    
    # 西安景点
    "兵马俑": "https://images.unsplash.com/photo-1648726444582-6d108b5d13dc?w=1920&h=1280&fit=crop&q=90",
    "秦始皇兵马俑": "https://images.unsplash.com/photo-1648726444582-6d108b5d13dc?w=1920&h=1280&fit=crop&q=90",
    "大雁塔": "https://images.unsplash.com/photo-1715473057495-47e412c32bbc?w=1920&h=1280&fit=crop&q=90",
    "西安城墙": "https://images.unsplash.com/photo-1569685794205-a8fc87049f5d?w=1920&h=1280&fit=crop&q=90",
    
    # 成都景点
    "宽窄巷子": "https://images.unsplash.com/photo-1627209011444-a920214c51d5?w=1920&h=1280&fit=crop&q=90",
    
    # 重庆景点
    "洪崖洞": "https://images.unsplash.com/photo-1691407302480-bad30ab53e07?w=1920&h=1280&fit=crop&q=90",
    
    # 其他热门景点
    "布达拉宫": "https://images.unsplash.com/photo-1701913997555-ecbdce49c9b9?w=1920&h=1280&fit=crop&q=90",
    "洱海": "https://images.unsplash.com/photo-1645157668565-45afc90a3ed2?w=1920&h=1280&fit=crop&q=90",
    "玉龙雪山": "https://images.unsplash.com/photo-1571897110146-94b06d59632e?w=1920&h=1280&fit=crop&q=90",
    "漓江": "https://images.unsplash.com/photo-1588423886412-914102b72f96?w=1920&h=1280&fit=crop&q=90",
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
        
        # 注意：跳过预设景点图片，因为很多 Unsplash URL 已失效
        # 直接使用 API 搜索确保图片与景点相关
        
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
        """检查预设城市图片，支持随机选择"""
        
        def get_image_url(data, img_type):
            """从预设数据获取图片 URL，支持列表随机选择"""
            value = data.get(img_type)
            if value is None:
                return None
            # 如果是列表，随机选择一个
            if isinstance(value, list):
                return random.choice(value)
            return value
        
        # 精确匹配
        if city in PRESET_CITY_IMAGES:
            data = PRESET_CITY_IMAGES[city]
            url = get_image_url(data, image_type)
            if url:
                return {
                    "url": url,
                    "source": "preset",
                    "city": city,
                    "地标": data.get("地标", ""),
                }
        
        # 模糊匹配（如"北京市" → "北京"）
        for key, data in PRESET_CITY_IMAGES.items():
            if key in city or city in key:
                url = get_image_url(data, image_type)
                if url:
                    return {
                        "url": url,
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