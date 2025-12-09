/**
 * 分享海报组件
 * 
 * 使用 HTML2Canvas 生成可下载的行程海报
 * 支持目的地地标背景图
 */

import React, { useRef, useState, useEffect } from 'react';
import { Sparkles, Navigation, Download, Loader2, Image as ImageIcon } from 'lucide-react';

// 预设城市背景图 - 使用 Unsplash Source 直接访问（更好的 CORS 支持）
const CITY_BACKGROUNDS = {
    "北京": "https://source.unsplash.com/800x1200/?beijing,forbidden-city",
    "上海": "https://source.unsplash.com/800x1200/?shanghai,bund",
    "杭州": "https://source.unsplash.com/800x1200/?hangzhou,west-lake",
    "成都": "https://source.unsplash.com/800x1200/?chengdu,panda",
    "西安": "https://source.unsplash.com/800x1200/?xian,terracotta-warriors",
    "重庆": "https://source.unsplash.com/800x1200/?chongqing,hongyadong",
    "广州": "https://source.unsplash.com/800x1200/?guangzhou,canton-tower",
    "三亚": "https://source.unsplash.com/800x1200/?sanya,beach",
    "丽江": "https://source.unsplash.com/800x1200/?lijiang,ancient-town",
    "东京": "https://source.unsplash.com/800x1200/?tokyo,japan",
    "香港": "https://source.unsplash.com/800x1200/?hongkong,skyline",
    "新加坡": "https://source.unsplash.com/800x1200/?singapore,marina-bay",
};

const DEFAULT_BACKGROUND = "https://source.unsplash.com/800x1200/?travel,landscape";

export function PosterView({ data }) {
    const posterRef = useRef(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [backgroundUrl, setBackgroundUrl] = useState(null);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [loadError, setLoadError] = useState(false);

    // 获取背景图 URL
    useEffect(() => {
        if (data?.destination) {
            // 尝试精确匹配
            let url = CITY_BACKGROUNDS[data.destination];

            // 尝试模糊匹配
            if (!url) {
                for (const [city, imgUrl] of Object.entries(CITY_BACKGROUNDS)) {
                    if (data.destination.includes(city) || city.includes(data.destination)) {
                        url = imgUrl;
                        break;
                    }
                }
            }

            setBackgroundUrl(url || DEFAULT_BACKGROUND);
            setImageLoaded(false);
            setLoadError(false);
        }
    }, [data?.destination]);

    // 预加载图片
    useEffect(() => {
        if (backgroundUrl) {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                setImageLoaded(true);
                setLoadError(false);
            };
            img.onerror = () => {
                setLoadError(true);
                setImageLoaded(true); // 仍然设置为 loaded 以显示渐变背景
            };
            img.src = backgroundUrl;
        }
    }, [backgroundUrl]);

    if (!data) return <div className="text-center text-gray-500">无法获取海报数据</div>;

    const handleDownload = async () => {
        setIsGenerating(true);
        try {
            // 动态加载 html2canvas
            if (!window.html2canvas) {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }

            const canvas = await window.html2canvas(posterRef.current, {
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#312e81', // 备用背景色
                scale: 2, // 高清
                logging: false,
            });

            const link = document.createElement('a');
            link.download = `TravelMind-${data.destination}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        } catch (error) {
            console.error('Poster generation failed', error);
            alert('海报生成失败，请稍后重试');
        }
        setIsGenerating(false);
    };

    // 根据图片加载状态决定背景样式
    const getBackgroundStyle = () => {
        if (imageLoaded && !loadError && backgroundUrl) {
            return {
                backgroundImage: `linear-gradient(to bottom, rgba(30, 27, 75, 0.6), rgba(88, 28, 135, 0.85)), url(${backgroundUrl})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
            };
        }
        // 默认渐变背景
        return {
            background: 'linear-gradient(to bottom right, #312e81, #6b21a8)',
        };
    };

    return (
        <div className="flex flex-col items-center animate-fadeIn gap-4">
            {/* 海报容器 */}
            <div
                ref={posterRef}
                className="w-full max-w-sm border border-white/20 rounded-2xl overflow-hidden shadow-2xl relative aspect-[3/4] flex flex-col"
                style={getBackgroundStyle()}
            >
                {/* 装饰元素 */}
                <div className="absolute top-0 right-0 p-4 opacity-20">
                    <Sparkles size={100} className="text-white" />
                </div>

                {/* 内容区域 */}
                <div className="relative z-10 flex-1 flex flex-col justify-between p-6">
                    <div>
                        <h2 className="text-3xl font-black text-white tracking-tight mb-1 drop-shadow-lg">
                            {data.destination}
                        </h2>
                        <p className="text-indigo-200 text-sm uppercase tracking-widest drop-shadow">
                            {data.days}
                        </p>
                    </div>

                    <div className="space-y-4 my-6">
                        {data.highlights?.map((h, i) => (
                            <div key={i} className="flex items-center gap-3">
                                <div className="w-1.5 h-1.5 bg-white rounded-full shadow-lg"></div>
                                <span className="text-white text-lg font-light drop-shadow">{h}</span>
                            </div>
                        ))}
                    </div>

                    <div className="mt-auto">
                        <div className="flex items-end justify-between">
                            <div>
                                <p className="text-xs text-indigo-300 mb-1">Generated by</p>
                                <div className="flex items-center gap-1.5">
                                    <div className="bg-white p-1 rounded-md">
                                        <Navigation size={12} className="text-indigo-900" />
                                    </div>
                                    <span className="font-bold text-white drop-shadow">TravelMind</span>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-xs text-indigo-300 mb-1">Budget Est.</p>
                                <p className="text-xl font-bold text-white drop-shadow-lg">{data.budget}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 图片加载状态指示 */}
                {!imageLoaded && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                        <Loader2 size={24} className="text-white animate-spin" />
                    </div>
                )}
            </div>

            {/* 下载按钮 */}
            <button
                onClick={handleDownload}
                disabled={isGenerating}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-full font-bold shadow-lg shadow-blue-600/30 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {isGenerating ? (
                    <Loader2 size={18} className="animate-spin" />
                ) : (
                    <Download size={18} />
                )}
                {isGenerating ? '正在渲染...' : '保存海报到相册'}
            </button>
            <p className="text-center text-xs text-gray-500">
                使用 HTML2Canvas 技术生成
            </p>
        </div>
    );
}

export default PosterView;
