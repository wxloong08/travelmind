"""
图片服务

按优先级获取城市和景点图片：
1. 预设热门城市图片
2. Unsplash API
3. 默认占位图
"""

import structlog
from typing import Optional

logger = structlog.get_logger()

# 预设热门城市图片 (使用 Unsplash 高质量免费图)
CITY_IMAGES = {
    # 国内热门城市
    "北京": {
        "landmark": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=800&q=80",  # 天安门
        "poster_bg": "https://images.unsplash.com/photo-1537002722563-44e0e5da8c5c?w=1200&q=80",  # 故宫
        "thumbnail": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=400&q=80",
    },
    "上海": {
        "landmark": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=800&q=80",  # 外滩
        "poster_bg": "https://images.unsplash.com/photo-1538428494232-9c0d8a3ab403?w=1200&q=80",  # 陆家嘴夜景
        "thumbnail": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=400&q=80",
    },
    "杭州": {
        "landmark": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=800&q=80",  # 西湖
        "poster_bg": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1598887142487-3c854d51eabb?w=400&q=80",
    },
    "成都": {
        "landmark": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=800&q=80",  # 熊猫
        "poster_bg": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1618281372631-17e14dac667b?w=400&q=80",
    },
    "西安": {
        "landmark": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&q=80",  # 兵马俑
        "poster_bg": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=400&q=80",
    },
    "重庆": {
        "landmark": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=800&q=80",  # 洪崖洞
        "poster_bg": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1576673783619-95e5f7d15dd3?w=400&q=80",
    },
    "广州": {
        "landmark": "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=800&q=80",  # 广州塔
        "poster_bg": "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=400&q=80",
    },
    "深圳": {
        "landmark": "https://images.unsplash.com/photo-1570434361343-9b3c7b3a3b1c?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1570434361343-9b3c7b3a3b1c?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1570434361343-9b3c7b3a3b1c?w=400&q=80",
    },
    "南京": {
        "landmark": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&q=80",
    },
    "苏州": {
        "landmark": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=400&q=80",
    },
    "厦门": {
        "landmark": "https://images.unsplash.com/photo-1573847103617-e9dd6b5d7b2a?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1573847103617-e9dd6b5d7b2a?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1573847103617-e9dd6b5d7b2a?w=400&q=80",
    },
    "三亚": {
        "landmark": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=400&q=80",
    },
    "丽江": {
        "landmark": "https://images.unsplash.com/photo-1544015759-8df50d06c7b6?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1544015759-8df50d06c7b6?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1544015759-8df50d06c7b6?w=400&q=80",
    },
    "大理": {
        "landmark": "https://images.unsplash.com/photo-1582921017967-79d1cb6702ee?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1582921017967-79d1cb6702ee?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1582921017967-79d1cb6702ee?w=400&q=80",
    },
    "青岛": {
        "landmark": "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?w=400&q=80",
    },
    # 境外热门城市
    "东京": {
        "landmark": "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?w=400&q=80",
    },
    "大阪": {
        "landmark": "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=400&q=80",
    },
    "首尔": {
        "landmark": "https://images.unsplash.com/photo-1619346636629-d994ae8dcd03?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1619346636629-d994ae8dcd03?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1619346636629-d994ae8dcd03?w=400&q=80",
    },
    "曼谷": {
        "landmark": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=400&q=80",
    },
    "新加坡": {
        "landmark": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=400&q=80",
    },
    "香港": {
        "landmark": "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=400&q=80",
    },
    "澳门": {
        "landmark": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?w=400&q=80",
    },
    "台北": {
        "landmark": "https://images.unsplash.com/photo-1470004914212-05527e49370b?w=800&q=80",
        "poster_bg": "https://images.unsplash.com/photo-1470004914212-05527e49370b?w=1200&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1470004914212-05527e49370b?w=400&q=80",
    },
}

# 默认占位图
DEFAULT_IMAGES = {
    "landmark": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&q=80",  # 旅行通用图
    "poster_bg": "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1200&q=80",
    "thumbnail": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400&q=80",
}


class ImageService:
    """图片服务类"""

    def __init__(self):
        self.city_images = CITY_IMAGES
        self.default_images = DEFAULT_IMAGES

    def get_city_image(
        self, city: str, image_type: str = "landmark"
    ) -> dict[str, str]:
        """
        获取城市图片
        
        Args:
            city: 城市名称
            image_type: 图片类型 (landmark/poster_bg/thumbnail)
            
        Returns:
            {"url": "图片URL", "source": "preset/unsplash/default"}
        """
        # 1. 尝试预设图片
        city_data = self.city_images.get(city)
        if city_data and image_type in city_data:
            logger.info("Image source: preset", city=city, type=image_type)
            return {
                "url": city_data[image_type],
                "source": "preset",
                "city": city,
            }
        
        # 2. 尝试模糊匹配（如"北京市" -> "北京"）
        for key in self.city_images:
            if key in city or city in key:
                city_data = self.city_images[key]
                if image_type in city_data:
                    logger.info("Image source: preset (fuzzy)", city=city, matched=key)
                    return {
                        "url": city_data[image_type],
                        "source": "preset",
                        "city": key,
                    }
        
        # 3. 返回默认图片
        logger.info("Image source: default", city=city, type=image_type)
        return {
            "url": self.default_images.get(image_type, self.default_images["landmark"]),
            "source": "default",
            "city": city,
        }

    def get_poster_background(self, destination: str) -> str:
        """获取海报背景图 URL"""
        result = self.get_city_image(destination, "poster_bg")
        return result["url"]

    def get_city_thumbnail(self, city: str) -> str:
        """获取城市缩略图 URL"""
        result = self.get_city_image(city, "thumbnail")
        return result["url"]

    def get_attraction_image(self, attraction_name: str, city: str) -> str:
        """
        获取景点图片
        
        目前使用城市图片作为默认，未来可以扩展为具体景点图片
        """
        # 目前返回城市 landmark 图片
        # TODO: 可以扩展为调用图片搜索 API 获取具体景点图片
        result = self.get_city_image(city, "landmark")
        return result["url"]


# 全局实例
image_service = ImageService()
