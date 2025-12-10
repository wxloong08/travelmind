/**
 * 分享海报组件 - 后端生成版
 * 
 * 调用后端 API 使用 Playwright 生成海报图片
 */

import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
    Sparkles,
    Download,
    Loader2,
    Calendar,
    MapPin,
    Wallet
} from 'lucide-react';


/**
 * 从行程数据中提取亮点
 */
function extractHighlights(itinerary) {
    if (!itinerary || !Array.isArray(itinerary)) return [];

    const highlights = [];

    for (const day of itinerary) {
        if (day.day_type === 'arrival' || day.day_type === 'departure') continue;

        for (const activity of (day.activities || [])) {
            if (activity.type === 'attraction' ||
                (!activity.type && !activity.title?.includes('酒店') && !activity.title?.includes('入住'))) {
                highlights.push(activity.title);
            }
        }
    }

    return [...new Set(highlights)].slice(0, 4);
}


/**
 * 计算天数和晚数
 */
function calculateTripDuration(data) {
    const itinerary = data?.itinerary || [];

    if (itinerary.length > 0) {
        const totalDays = itinerary.length;
        const nights = Math.max(0, totalDays - 1);
        return { totalDays, nights };
    }

    let totalDays = 0;
    let nights = 0;

    if (typeof data?.days === 'number') {
        totalDays = data.days;
        nights = Math.max(0, totalDays - 1);
    } else if (typeof data?.days === 'string') {
        const daysMatch = data.days.match(/(\d+)\s*天/);
        const nightsMatch = data.days.match(/(\d+)\s*晚/);

        if (daysMatch) totalDays = parseInt(daysMatch[1], 10);
        if (nightsMatch) nights = parseInt(nightsMatch[1], 10);
        else nights = Math.max(0, totalDays - 1);
    }

    return { totalDays, nights };
}


export function PosterView({ data }) {
    const [posterUrl, setPosterUrl] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState(null);

    // 计算天数
    const duration = calculateTripDuration(data);
    const highlights = extractHighlights(data?.itinerary);

    // 格式化预算
    const formatBudget = (budget) => {
        if (!budget) return '';
        if (typeof budget === 'number') return `¥${budget.toLocaleString()}`;
        return String(budget).startsWith('¥') ? budget : `¥${budget}`;
    };

    // 生成海报
    const generatePoster = useCallback(async () => {
        if (!data?.destination) return;

        setIsGenerating(true);
        setError(null);
        setPosterUrl(null);

        try {
            const response = await fetch('/api/v1/poster/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    destination: data.destination,
                    days: duration.totalDays,
                    nights: duration.nights,
                    budget: formatBudget(data.budget),
                    highlights: highlights,
                    travel_style: data.travelStyle || '',
                    background_url: '',
                    image_source: ''
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // 获取图片 blob
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            setPosterUrl(url);
        } catch (err) {
            console.error('生成海报失败:', err);
            setError(err.message);
        } finally {
            setIsGenerating(false);
        }
    }, [data, duration, highlights]);

    // 首次加载自动生成
    useEffect(() => {
        if (data?.destination && !posterUrl && !isGenerating) {
            generatePoster();
        }
    }, [data?.destination]);

    // 下载海报
    const handleDownload = () => {
        if (!posterUrl) return;

        const link = document.createElement('a');
        link.href = posterUrl;
        link.download = `${data?.destination || '旅行'}行程海报.png`;
        link.click();
    };

    // 清理 blob URL
    useEffect(() => {
        return () => {
            if (posterUrl) {
                URL.revokeObjectURL(posterUrl);
            }
        };
    }, [posterUrl]);

    return (
        <div className="flex flex-col gap-4">
            {/* 海报预览区域 */}
            <div className="relative w-full aspect-[3/4] rounded-xl overflow-hidden shadow-2xl bg-gray-900">
                {/* 加载中 */}
                {isGenerating && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-white">
                        <Loader2 className="w-12 h-12 animate-spin text-amber-400 mb-4" />
                        <p className="text-gray-400">正在生成海报...</p>
                        <p className="text-xs text-gray-600 mt-2">首次生成可能需要几秒钟</p>
                    </div>
                )}

                {/* 错误状态 */}
                {error && !isGenerating && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-white p-6">
                        <div className="text-red-400 mb-4">生成失败</div>
                        <p className="text-gray-500 text-sm text-center mb-4">{error}</p>
                        <button
                            onClick={generatePoster}
                            className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 text-amber-400 rounded-lg hover:bg-amber-500/30 transition-colors"
                        >
                            <RefreshCw className="w-4 h-4" />
                            重试
                        </button>
                    </div>
                )}

                {/* 海报图片 */}
                {posterUrl && !isGenerating && (
                    <img
                        src={posterUrl}
                        alt="旅行海报"
                        className="w-full h-full object-contain"
                    />
                )}

                {/* 初始状态 */}
                {!posterUrl && !isGenerating && !error && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-indigo-600 to-purple-700 text-white p-6">
                        <Sparkles className="w-12 h-12 text-amber-400 mb-4" />
                        <h3 className="text-2xl font-bold mb-2">{data?.destination}</h3>
                        <div className="flex items-center gap-4 text-white/80 mb-6">
                            <span className="flex items-center gap-1">
                                <Calendar className="w-4 h-4" />
                                {duration.totalDays}天{duration.nights}晚
                            </span>
                            {data?.budget && (
                                <span className="flex items-center gap-1">
                                    <Wallet className="w-4 h-4" />
                                    {formatBudget(data.budget)}
                                </span>
                            )}
                        </div>
                        <button
                            onClick={generatePoster}
                            className="flex items-center gap-2 px-6 py-3 bg-amber-500 text-white rounded-xl font-medium hover:bg-amber-600 transition-colors"
                        >
                            <Sparkles className="w-5 h-5" />
                            生成海报
                        </button>
                    </div>
                )}
            </div>

            {/* 下载按钮 */}
            <button
                onClick={handleDownload}
                disabled={!posterUrl || isGenerating}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-medium transition-all hover:shadow-lg hover:shadow-amber-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Download className="w-5 h-5" />
                下载海报
            </button>
        </div>
    );
}

export default PosterView;