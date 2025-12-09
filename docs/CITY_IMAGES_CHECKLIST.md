# 热门城市图片资源清单

## 一、需要准备的图片

每个城市需要 3 种规格的图片：

| 类型 | 尺寸 | 用途 | 格式 |
|------|------|------|------|
| landmark | 1200×800 | 海报背景、大图展示 | WebP/JPG |
| poster_bg | 800×1200 | 分享海报背景（竖版） | WebP/JPG |
| thumbnail | 400×300 | 列表缩略图 | WebP |

## 二、热门城市清单 (Top 30)

### Tier 1: 一线旅游城市 (必须)

| 城市 | 地标建议 | 备注 |
|------|----------|------|
| 北京 | 故宫/天安门/长城 | 可准备多张备选 |
| 上海 | 外滩/东方明珠 | 夜景效果佳 |
| 广州 | 广州塔(小蛮腰) | |
| 深圳 | 平安金融中心/世界之窗 | |
| 杭州 | 西湖/雷峰塔 | 经典角度 |
| 成都 | 宽窄巷子/大熊猫 | |
| 重庆 | 洪崖洞/解放碑 | 夜景 |
| 西安 | 兵马俑/大雁塔/城墙 | |
| 南京 | 中山陵/夫子庙 | |
| 苏州 | 拙政园/寒山寺 | |

### Tier 2: 热门旅游城市

| 城市 | 地标建议 |
|------|----------|
| 三亚 | 天涯海角/亚龙湾 |
| 厦门 | 鼓浪屿/环岛路 |
| 青岛 | 栈桥/八大关 |
| 大理 | 洱海/崇圣寺三塔 |
| 丽江 | 古城/玉龙雪山 |
| 桂林 | 漓江/象鼻山 |
| 黄山 | 迎客松/云海 |
| 张家界 | 天门山/玻璃栈道 |
| 拉萨 | 布达拉宫 |
| 昆明 | 滇池/石林 |

### Tier 3: 其他热门目的地

| 城市 | 地标建议 |
|------|----------|
| 武汉 | 黄鹤楼/长江大桥 |
| 长沙 | 橘子洲头/岳麓山 |
| 郑州 | 少林寺 |
| 天津 | 天津之眼/五大道 |
| 哈尔滨 | 圣索菲亚教堂/冰雪大世界 |
| 沈阳 | 沈阳故宫 |
| 济南 | 趵突泉/大明湖 |
| 无锡 | 鼋头渚/灵山大佛 |
| 宁波 | 天一阁/老外滩 |
| 珠海 | 珠海渔女/长隆海洋王国 |

## 三、图片来源建议

### 方案 A: 无版权图片网站

| 网站 | 说明 | 中国城市覆盖 |
|------|------|-------------|
| [Unsplash](https://unsplash.com) | 免费高质量 | ⭐⭐⭐ |
| [Pexels](https://pexels.com) | 免费 | ⭐⭐⭐ |
| [Pixabay](https://pixabay.com) | 免费 | ⭐⭐⭐⭐ |
| [500px](https://500px.com) | 需付费 | ⭐⭐⭐⭐⭐ |

### 方案 B: AI 生成

使用 Midjourney / DALL-E / Stable Diffusion 生成：

```
Prompt 示例：
"The Forbidden City in Beijing, aerial view, golden rooftops, 
blue sky, professional photography, high resolution, 8k"

"West Lake in Hangzhou, misty morning, traditional Chinese boats, 
willow trees, peaceful atmosphere, landscape photography"
```

**优点**: 无版权问题、可定制风格
**缺点**: 可能不够真实、成本较高

### 方案 C: 购买授权

| 平台 | 价格 | 说明 |
|------|------|------|
| 视觉中国 | ¥50-200/张 | 国内首选 |
| Getty Images | $50-300/张 | 质量最高 |
| Shutterstock | $10-50/张 | 性价比高 |

## 四、图片处理规范

### 4.1 尺寸裁剪

```javascript
// 图片尺寸配置
const IMAGE_SIZES = {
  landmark: { width: 1200, height: 800, fit: 'cover' },
  poster_bg: { width: 800, height: 1200, fit: 'cover' },
  thumbnail: { width: 400, height: 300, fit: 'cover' },
};
```

### 4.2 压缩要求

| 规格 | 文件大小 | 格式 |
|------|----------|------|
| landmark | < 200KB | WebP (优先) / JPG |
| poster_bg | < 150KB | WebP (优先) / JPG |
| thumbnail | < 50KB | WebP |

### 4.3 处理脚本

```bash
# 使用 ImageMagick 批量处理
convert input.jpg -resize 1200x800^ -gravity center -extent 1200x800 \
  -quality 85 -strip output_landmark.webp

convert input.jpg -resize 800x1200^ -gravity center -extent 800x1200 \
  -quality 85 -strip output_poster.webp

convert input.jpg -resize 400x300^ -gravity center -extent 400x300 \
  -quality 80 -strip output_thumb.webp
```

## 五、存储方案

### 方案 A: 本地存储 (开发/小规模)

```
frontend/
└── public/
    └── images/
        └── cities/
            ├── beijing/
            │   ├── landmark.webp
            │   ├── poster_bg.webp
            │   └── thumbnail.webp
            ├── shanghai/
            │   ├── landmark.webp
            │   ├── poster_bg.webp
            │   └── thumbnail.webp
            └── ...
```

### 方案 B: 阿里云 OSS (生产推荐)

```
https://travelmind-assets.oss-cn-hangzhou.aliyuncs.com/cities/beijing/landmark.webp
```

**优点**:
- CDN 加速
- 按量付费
- 自动压缩

**配置**:
```javascript
// frontend/src/config/assets.js
export const ASSET_BASE_URL = import.meta.env.PROD 
  ? 'https://travelmind-assets.oss-cn-hangzhou.aliyuncs.com'
  : '/images';
```

## 六、代码实现

### 6.1 图片配置文件

```javascript
// frontend/src/assets/cityImages.js

const CITIES = {
  "北京": {
    landmark: "beijing/landmark.webp",
    poster_bg: "beijing/poster_bg.webp", 
    thumbnail: "beijing/thumbnail.webp",
    credit: "Photo by xxx on Unsplash",  // 版权信息
  },
  "上海": {
    landmark: "shanghai/landmark.webp",
    poster_bg: "shanghai/poster_bg.webp",
    thumbnail: "shanghai/thumbnail.webp",
  },
  // ... 其他城市
};

const DEFAULT = {
  landmark: "default/landmark.webp",
  poster_bg: "default/poster_bg.webp",
  thumbnail: "default/thumbnail.webp",
};

export function getCityImage(cityName, type = 'landmark') {
  const baseUrl = import.meta.env.VITE_ASSET_BASE || '/images/cities';
  const city = CITIES[cityName] || DEFAULT;
  return `${baseUrl}/${city[type]}`;
}

export function getCityImageWithFallback(cityName, type = 'landmark') {
  return {
    src: getCityImage(cityName, type),
    fallback: getCityImage('_default', type),
  };
}
```

### 6.2 图片组件

```jsx
// frontend/src/components/ui/CityImage.jsx

import { useState } from 'react';
import { getCityImageWithFallback } from '@/assets/cityImages';

export function CityImage({ city, type = 'landmark', className, alt }) {
  const [error, setError] = useState(false);
  const { src, fallback } = getCityImageWithFallback(city, type);
  
  return (
    <img
      src={error ? fallback : src}
      alt={alt || `${city} ${type}`}
      className={className}
      onError={() => setError(true)}
      loading="lazy"
    />
  );
}
```

## 七、任务清单

### Phase 1: 收集图片 (1-2天)

- [ ] 从 Unsplash/Pexels 下载 Tier 1 城市图片
- [ ] 筛选质量合格的图片
- [ ] 记录版权/来源信息

### Phase 2: 处理图片 (1天)

- [ ] 批量裁剪为 3 种规格
- [ ] 压缩优化
- [ ] 转换为 WebP 格式

### Phase 3: 上传存储 (0.5天)

- [ ] 开发环境: 放入 public/images
- [ ] 生产环境: 上传到 OSS

### Phase 4: 代码集成 (0.5天)

- [ ] 创建配置文件
- [ ] 海报组件使用图片
- [ ] 行程卡片使用缩略图

---

## 八、备选动态方案

如果静态图片无法覆盖所有城市，使用动态获取：

```python
# backend: src/services/image_service.py

async def get_city_image_dynamic(city: str, type: str) -> str:
    """动态获取城市图片"""
    
    # 1. 检查缓存
    cache_key = f"city_image:{city}:{type}"
    cached = await redis.get(cache_key)
    if cached:
        return cached
    
    # 2. 必应图片搜索
    try:
        query = f"{city} 地标 风景 高清"
        result = await bing_image_search(query, count=1, safe_search=True)
        if result:
            url = result[0]["contentUrl"]
            await redis.set(cache_key, url, ex=86400 * 7)  # 缓存7天
            return url
    except Exception as e:
        logger.warning(f"Bing image search failed for {city}: {e}")
    
    # 3. Unsplash API
    try:
        result = await unsplash_search(city)
        if result:
            url = result["urls"]["regular"]
            await redis.set(cache_key, url, ex=86400 * 7)
            return url
    except Exception as e:
        logger.warning(f"Unsplash search failed for {city}: {e}")
    
    # 4. 返回默认图
    return DEFAULT_IMAGES[type]
```

---

*图片资源清单结束*
