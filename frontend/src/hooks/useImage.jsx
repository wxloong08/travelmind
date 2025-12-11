/**
 * 图片 Hook - 调用后端图片服务
 * 
 * 按 PRD 2.4.1 优先级获取图片：
 * 预设 → 必应 → Unsplash → 默认
 * 
 * 使用方法：
 * ```jsx
 * // 获取城市图片
 * const { imageUrl, loading, source } = useImage('city', '北京');
 * 
 * // 获取景点图片
 * const { imageUrl, loading, source } = useImage('attraction', '故宫', '北京');
 * 
 * // 获取海报背景
 * const { imageUrl, loading, source } = useImage('poster', '上海');
 * ```
 */

import { useState, useEffect, useCallback } from 'react';

// API 基础路径 - 使用空字符串以便 Vite 代理正确处理
const API_BASE = '';

// 默认图片（当 API 不可用时使用）
const DEFAULT_IMAGES = {
    city: 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&h=600&fit=crop&q=80',
    attraction: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&q=80',
    poster: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800&h=1200&fit=crop&q=80',
    hotel: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&h=600&fit=crop&q=80',
};

// ============================================================
// 全局图片缓存 - 避免重复请求后端
// ============================================================
const imageCache = new Map();

/**
 * 生成缓存键
 */
const getCacheKey = (type, name, city = '') => `${type}:${name}:${city}`;

/**
 * 从缓存获取图片
 */
const getCachedImage = (type, name, city = '') => {
    const key = getCacheKey(type, name, city);
    return imageCache.get(key);
};

/**
 * 设置缓存
 */
const setCachedImage = (type, name, city, data) => {
    const key = getCacheKey(type, name, city);
    imageCache.set(key, data);

    // 限制缓存大小（最多 200 条）
    if (imageCache.size > 200) {
        const firstKey = imageCache.keys().next().value;
        imageCache.delete(firstKey);
    }
};


/**
 * 图片获取 Hook（带缓存）
 * 
 * @param {'city' | 'attraction' | 'poster' | 'hotel'} type - 图片类型
 * @param {string} name - 城市名或景点名
 * @param {string} [city] - 所在城市（仅 attraction 类型需要）
 * @returns {{imageUrl: string, loading: boolean, error: Error|null, source: string|null, refetch: Function}}
 */
export function useImage(type, name, city = '') {
    const [imageUrl, setImageUrl] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [source, setSource] = useState(null);

    const fetchImage = useCallback(async () => {
        if (!name) {
            setLoading(false);
            return;
        }

        // ===== 优先检查缓存 =====
        const cached = getCachedImage(type, name, city);
        if (cached) {
            setImageUrl(cached.url);
            setSource(cached.source);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            let endpoint;

            switch (type) {
                case 'city':
                    endpoint = `${API_BASE}/api/v1/images/city/${encodeURIComponent(name)}?type=landmark`;
                    break;
                case 'poster':
                    endpoint = `${API_BASE}/api/v1/images/city/${encodeURIComponent(name)}?type=poster_bg`;
                    break;
                case 'attraction':
                    endpoint = `${API_BASE}/api/v1/images/attraction?name=${encodeURIComponent(name)}&city=${encodeURIComponent(city)}`;
                    break;
                case 'hotel':
                    // 酒店暂时用默认图
                    const hotelData = { url: DEFAULT_IMAGES.hotel, source: 'default' };
                    setCachedImage(type, name, city, hotelData);
                    setImageUrl(hotelData.url);
                    setSource(hotelData.source);
                    setLoading(false);
                    return;
                default:
                    throw new Error(`Unknown image type: ${type}`);
            }

            const response = await fetch(endpoint);

            if (response.ok) {
                const data = await response.json();
                // 缓存结果
                setCachedImage(type, name, city, data);
                setImageUrl(data.url);
                setSource(data.source);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (err) {
            console.error(`Failed to fetch ${type} image for ${name}:`, err);
            setError(err);
            // 使用默认图并缓存
            const fallbackData = { url: DEFAULT_IMAGES[type] || DEFAULT_IMAGES.city, source: 'default' };
            setCachedImage(type, name, city, fallbackData);
            setImageUrl(fallbackData.url);
            setSource(fallbackData.source);
        } finally {
            setLoading(false);
        }
    }, [type, name, city]);

    useEffect(() => {
        fetchImage();
    }, [fetchImage]);

    return { imageUrl, loading, error, source, refetch: fetchImage };
}


/**
 * 景点图片组件
 * 
 * 使用方法：
 * ```jsx
 * <AttractionImage 
 *   name="故宫" 
 *   city="北京" 
 *   className="w-full h-40 rounded-lg"
 * />
 * ```
 */
export function AttractionImage({
    name,
    city = '',
    className = '',
    fallbackClassName = '',
    showSource = false
}) {
    const { imageUrl, loading, error, source } = useImage('attraction', name, city);
    const [imgError, setImgError] = useState(false);

    if (loading) {
        return (
            <div className={`animate-pulse bg-gray-700/50 ${className}`}>
                <div className="w-full h-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-gray-500 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
                    </svg>
                </div>
            </div>
        );
    }

    if (imgError || !imageUrl) {
        return (
            <div className={`bg-gradient-to-br from-gray-700 to-gray-800 ${fallbackClassName || className}`}>
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                </div>
            </div>
        );
    }

    return (
        <div className={`relative overflow-hidden ${className}`}>
            <img
                src={imageUrl}
                alt={name}
                className="w-full h-full object-cover"
                onError={() => setImgError(true)}
                loading="lazy"
            />
            {showSource && source && source !== 'default' && (
                <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/50 rounded text-[10px] text-white/60">
                    {source === 'preset' ? '精选' : source}
                </div>
            )}
        </div>
    );
}


/**
 * 城市图片组件
 */
export function CityImage({
    city,
    type = 'landmark',
    className = '',
    showSource = false
}) {
    const imageType = type === 'poster' ? 'poster' : 'city';
    const { imageUrl, loading, source } = useImage(imageType, city);
    const [imgError, setImgError] = useState(false);

    if (loading) {
        return (
            <div className={`animate-pulse bg-gray-700/50 ${className}`} />
        );
    }

    if (imgError || !imageUrl) {
        return (
            <div className={`bg-gradient-to-br from-indigo-600 to-purple-700 ${className}`} />
        );
    }

    return (
        <div className={`relative overflow-hidden ${className}`}>
            <img
                src={imageUrl}
                alt={city}
                className="w-full h-full object-cover"
                onError={() => setImgError(true)}
                loading="lazy"
            />
            {showSource && source && (
                <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/50 rounded text-[10px] text-white/60">
                    {source === 'preset' ? '精选' : source}
                </div>
            )}
        </div>
    );
}


/**
 * 预加载图片
 * 
 * @param {string} url - 图片 URL
 * @returns {Promise<void>}
 */
export function preloadImage(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve();
        img.onerror = reject;
        img.src = url;
    });
}


/**
 * 批量获取景点图片
 * 
 * @param {Array<{name: string, city?: string}>} attractions - 景点列表
 * @returns {Promise<Map<string, string>>} - 景点名到图片 URL 的映射
 */
export async function batchFetchAttractionImages(attractions, city = '') {
    const imageMap = new Map();

    await Promise.all(
        attractions.map(async (attr) => {
            const name = typeof attr === 'string' ? attr : attr.name;
            const attrCity = (typeof attr === 'object' && attr.city) || city;

            try {
                const response = await fetch(
                    `${API_BASE}/api/v1/images/attraction?name=${encodeURIComponent(name)}&city=${encodeURIComponent(attrCity)}`
                );

                if (response.ok) {
                    const data = await response.json();
                    imageMap.set(name, data.url);
                }
            } catch (err) {
                console.error(`Failed to fetch image for ${name}:`, err);
                imageMap.set(name, DEFAULT_IMAGES.attraction);
            }
        })
    );

    return imageMap;
}


export default useImage;