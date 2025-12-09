import { useState, useEffect } from 'react';
import {
    Map as MapIcon,
    CloudSun,
    Sun,
    Umbrella,
    Newspaper,
    TrendingUp,
    Edit3,
    RefreshCw,
    ChevronDown,
    ChevronLeft,
    XCircle,
    BrainCircuit,
    Lightbulb,
    Hotel,
    Ticket,
    Car,
    Utensils,
    ExternalLink,
} from 'lucide-react';
import useTravelStore from '../../store/useTravelStore';

const API_BASE = '/api/v1';

// === 今日路线 Widget ===
const MiniMapWidget = ({ itinerary }) => {
    const [selectedDayIdx, setSelectedDayIdx] = useState(0);
    const day = itinerary?.[selectedDayIdx];

    if (!day) {
        return (
            <div className="bg-[#1a1d2d]/60 border border-white/5 rounded-2xl p-5 h-48 flex items-center justify-center">
                <div className="text-gray-500 text-xs flex flex-col items-center gap-2">
                    <MapIcon size={24} className="opacity-50" />
                    <p>暂无行程路线</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn relative overflow-hidden group">
            {/* 标题和日期选择 */}
            <div className="flex justify-between items-center mb-4 z-10 relative">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <MapIcon size={14} className="text-blue-400" /> 今日路线
                </h4>
                {itinerary.length > 1 && (
                    <div className="relative">
                        <select
                            value={selectedDayIdx}
                            onChange={(e) => setSelectedDayIdx(Number(e.target.value))}
                            className="bg-black/30 border border-white/10 text-xs text-white rounded px-2 py-1 outline-none appearance-none pr-6 cursor-pointer hover:bg-black/50 transition-colors"
                        >
                            {itinerary.map((d, i) => (
                                <option key={i} value={i}>Day {d.day}</option>
                            ))}
                        </select>
                        <ChevronDown size={12} className="absolute right-2 top-1.5 text-gray-400 pointer-events-none" />
                    </div>
                )}
            </div>

            {/* 活动列表 */}
            <div className="space-y-0 relative z-10 pl-2">
                {day.activities?.slice(0, 4).map((act, i) => {
                    const isLast = i === Math.min(day.activities.length, 4) - 1;
                    const transport = act.transport_from_prev;
                    return (
                        <div key={i} className="flex gap-3 relative pb-4 last:pb-0">
                            {!isLast && <div className="absolute left-[9px] top-5 bottom-0 w-0.5 bg-white/10"></div>}
                            <div className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center flex-shrink-0 mt-0.5 z-10 text-[10px] text-blue-300 font-bold font-mono">
                                {i + 1}
                            </div>
                            <div className="min-w-0">
                                <div className="text-xs font-bold text-gray-200 truncate">{act.title}</div>
                                {transport && i < 3 && (
                                    <div className="text-[10px] text-gray-500 mt-0.5">
                                        ↓ {transport.duration || '约2.5km'}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
                {day.activities?.length > 4 && (
                    <div className="text-center text-[10px] text-gray-500 mt-2">
                        ...还有 {day.activities.length - 4} 个地点
                    </div>
                )}
            </div>

            {/* 背景和按钮 */}
            <div className="absolute bottom-0 right-0 w-full h-24 bg-gradient-to-t from-black/80 to-transparent z-0 pointer-events-none"></div>
            <button className="w-full mt-4 py-1.5 bg-white/5 hover:bg-white/10 border border-white/5 rounded text-xs text-blue-300 transition-colors z-10 relative">
                查看完整地图
            </button>
        </div>
    );
};

// === 天气趋势 Widget ===
const WeatherTrendWidget = ({ weatherData, destination }) => {
    const getIcon = (cond) => {
        if (!cond) return <CloudSun size={14} className="text-gray-400" />;
        if (cond.includes('雨')) return <Umbrella size={14} className="text-blue-400" />;
        if (cond.includes('雪')) return <Umbrella size={14} className="text-blue-200" />;
        if (cond.includes('晴')) return <Sun size={14} className="text-yellow-400" />;
        return <CloudSun size={14} className="text-gray-400" />;
    };

    const forecast = weatherData && weatherData.length > 0
        ? weatherData
        : [
            { day: 'Mon', temp: '--', cond: '加载中' },
            { day: 'Tue', temp: '--', cond: '...' },
            { day: 'Wed', temp: '--', cond: '...' },
            { day: 'Thu', temp: '--', cond: '...' },
            { day: 'Fri', temp: '--', cond: '...' },
        ];

    const hasBadWeather = weatherData?.some(f => f.cond?.includes('雨') || f.cond?.includes('雪'));

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <CloudSun size={14} className="text-yellow-400" /> 天气趋势
                </h4>
                <span className="text-[10px] text-gray-500">{destination || '未知'}</span>
            </div>

            <div className="space-y-3">
                {forecast.map((f, i) => (
                    <div key={i} className="flex items-center justify-between text-xs group">
                        <div className="w-8 text-gray-400">{f.day}</div>
                        <div className="flex-1 flex justify-center">{getIcon(f.cond)}</div>
                        <div className="w-12 text-right font-mono text-white">{f.temp}°C</div>
                        <div className="w-12 text-right text-gray-500 truncate">{f.cond}</div>
                    </div>
                ))}
            </div>

            {hasBadWeather && (
                <div className="mt-4 bg-blue-900/20 border border-blue-500/20 rounded p-2 flex gap-2 items-start">
                    <Lightbulb size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" />
                    <p className="text-[10px] text-blue-200 leading-relaxed">
                        未来几天可能有雨雪，建议调整户外行程或携带雨具。
                    </p>
                </div>
            )}
        </div>
    );
};

// === 当地资讯 Widget ===
const LocalNewsWidget = ({ newsData, onRefresh, isLoading }) => {
    const getTagStyle = (tag) => {
        switch (tag) {
            case '警告':
            case 'Warning':
                return 'text-red-400 bg-red-400/10';
            case '活动':
            case 'Event':
                return 'text-pink-400 bg-pink-400/10';
            default:
                return 'text-blue-400 bg-blue-400/10';
        }
    };

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <Newspaper size={14} className="text-pink-400" /> 当地资讯
                </h4>
                <button
                    onClick={onRefresh}
                    className={`text-gray-500 hover:text-white transition-colors ${isLoading ? 'animate-spin' : ''}`}
                    title="刷新"
                >
                    <RefreshCw size={12} />
                </button>
            </div>

            <div className="space-y-4">
                {newsData && newsData.length > 0 ? (
                    newsData.map((news, i) => (
                        <div key={i} className="group cursor-pointer">
                            <div className="flex justify-between items-start gap-2 mb-1">
                                <h5 className="text-xs text-gray-200 font-medium group-hover:text-blue-400 transition-colors line-clamp-1">
                                    {news.title}
                                </h5>
                            </div>
                            <div className="flex justify-between items-center">
                                <p className="text-[10px] text-gray-500 line-clamp-1">
                                    AI 实时抓取中...
                                </p>
                                <span className={`text-[9px] px-1.5 py-0.5 rounded flex-shrink-0 ${getTagStyle(news.tag)}`}>
                                    {news.tag}
                                </span>
                            </div>
                            {i < newsData.length - 1 && <div className="h-[1px] bg-white/5 mt-3"></div>}
                        </div>
                    ))
                ) : (
                    <div className="text-center text-xs text-gray-500 py-4">
                        点击刷新获取最新资讯
                    </div>
                )}
            </div>
        </div>
    );
};

// === 预算仪表盘 Widget ===
const BudgetDashboardWidget = ({ budgetData }) => {
    // 计算预算数据
    const total = budgetData?.total || 5000;
    const categories = budgetData?.categories || [
        { name: '住宿 (3晚)', amount: '¥1032', icon: Hotel, color: 'text-blue-400' },
        { name: '门票', amount: '¥860', icon: Ticket, color: 'text-yellow-400' },
        { name: '交通', amount: '¥280', icon: Car, color: 'text-cyan-400' },
        { name: '餐饮 (预估)', amount: '¥1200', icon: Utensils, color: 'text-orange-400' },
    ];

    const spent = 3372;
    const percent = total > 0 ? (spent / total) * 100 : 0;

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <TrendingUp size={14} className="text-emerald-400" /> 预算仪表盘
                </h4>
                <button className="text-gray-500 hover:text-white transition-colors">
                    <Edit3 size={12} />
                </button>
            </div>

            {/* 总预算进度 */}
            <div className="mb-4">
                <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-gray-400">总预算</span>
                    <span className="text-white font-mono font-bold">¥{total}</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-1000"
                        style={{ width: `${percent}%` }}
                    ></div>
                </div>
                <div className="flex justify-between text-[10px] mt-1.5">
                    <span className="text-emerald-400">{Math.round(percent)}% 已规划</span>
                    <span className="text-gray-500">剩余 ¥{total - spent}</span>
                </div>
            </div>

            {/* 分类支出 */}
            <div className="space-y-2">
                {[
                    { label: '住宿 (3晚)', val: '1032', icon: Hotel, color: 'text-blue-400' },
                    { label: '门票', val: '860', icon: Ticket, color: 'text-yellow-400' },
                    { label: '交通', val: '280', icon: Car, color: 'text-cyan-400' },
                    { label: '餐饮 (预估)', val: '1200', icon: Utensils, color: 'text-orange-400' },
                ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between bg-white/5 rounded px-2 py-1.5">
                        <div className="flex items-center gap-2 text-xs text-gray-300">
                            <item.icon size={10} className={item.color} /> {item.label}
                        </div>
                        <div className="text-xs font-mono text-white">¥{item.val}</div>
                    </div>
                ))}
            </div>

            <button className="w-full mt-3 text-[10px] text-gray-500 hover:text-white transition-colors text-right">
                导出费用明细 →
            </button>
        </div>
    );
};

// === 智囊助手主组件 ===
export function SmartSidebar({ isMobile, isDrawer, onClose, isCollapsed, onToggle }) {
    const { itinerary, destination, budget } = useTravelStore();
    const [sidebarInfo, setSidebarInfo] = useState({ forecast: [], news: [] });
    const [isLoading, setIsLoading] = useState(false);

    // 获取侧边栏数据
    const fetchSidebarData = async () => {
        if (!destination || destination === '未知目的地') return;

        setIsLoading(true);
        try {
            // 并行请求天气和资讯
            const [weatherRes, newsRes] = await Promise.all([
                fetch(`${API_BASE}/sidebar/weather/${encodeURIComponent(destination)}`).catch(() => null),
                fetch(`${API_BASE}/sidebar/news/${encodeURIComponent(destination)}`).catch(() => null),
            ]);

            const weatherData = weatherRes?.ok ? await weatherRes.json() : null;
            const newsData = newsRes?.ok ? await newsRes.json() : null;

            setSidebarInfo({
                forecast: weatherData?.forecast || [],
                news: newsData?.articles || [],
            });
        } catch (error) {
            console.error('Failed to fetch sidebar data:', error);
        }
        setIsLoading(false);
    };

    useEffect(() => {
        if (destination && destination !== '未知目的地') {
            fetchSidebarData();
        }
    }, [destination]);

    return (
        <div className={`flex flex-col gap-4 animate-fadeIn ${isMobile || isDrawer ? 'pb-20' : 'sticky top-4 h-[calc(100vh-8rem)] overflow-y-auto custom-scrollbar pr-2'}`}>
            {/* 移动端/抽屉标题 */}
            {(isMobile || isDrawer) && (
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        {isMobile && (
                            <button onClick={onClose} className="p-1 bg-white/10 rounded-full">
                                <ChevronLeft size={20} className="text-white" />
                            </button>
                        )}
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            <BrainCircuit size={20} className="text-blue-400" /> 智囊助手
                        </h3>
                    </div>
                    {isDrawer && (
                        <button onClick={onClose} className="p-1 bg-white/10 rounded-full hover:bg-white/20 transition-colors">
                            <XCircle size={20} className="text-gray-400 hover:text-white" />
                        </button>
                    )}
                </div>
            )}

            {/* 四个 Widget */}
            <MiniMapWidget itinerary={itinerary} />
            <WeatherTrendWidget weatherData={sidebarInfo.forecast} destination={destination} />
            <LocalNewsWidget
                newsData={sidebarInfo.news}
                onRefresh={fetchSidebarData}
                isLoading={isLoading}
            />
            <BudgetDashboardWidget budgetData={budget} />
        </div>
    );
}
