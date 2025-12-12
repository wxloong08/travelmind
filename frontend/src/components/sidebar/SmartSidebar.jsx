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
    const { setActiveTab } = useTravelStore();
    const day = itinerary?.[selectedDayIdx];

    // 获取活动数据（兼容不同数据结构）
    const activities = day?.activities || day?.items || day?.schedule || [];

    // 处理查看完整地图
    const handleViewMap = () => {
        setActiveTab('map');
    };

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
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            {/* 标题和日期选择 */}
            <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <MapIcon size={14} className="text-blue-400" /> 今日路线
                </h4>
                {itinerary && itinerary.length > 1 && (
                    <div className="relative">
                        <select
                            value={selectedDayIdx}
                            onChange={(e) => setSelectedDayIdx(Number(e.target.value))}
                            className="bg-black/30 border border-white/10 text-xs text-white rounded px-2 py-1 outline-none appearance-none pr-6 cursor-pointer hover:bg-black/50 transition-colors"
                        >
                            {itinerary.map((d, i) => (
                                <option key={i} value={i}>Day {d.day || i + 1}</option>
                            ))}
                        </select>
                        <ChevronDown size={12} className="absolute right-2 top-1.5 text-gray-400 pointer-events-none" />
                    </div>
                )}
            </div>

            {/* 活动列表 */}
            <div className="space-y-0 pl-2">
                {activities.length > 0 ? (
                    activities.map((act, i) => {
                        const isLast = i === activities.length - 1;
                        const transport = act.transport_from_prev || act.transport;
                        const title = act.title || act.name || act.activity || '未命名活动';
                        return (
                            <div key={i} className="flex gap-3 relative pb-3 last:pb-0">
                                {!isLast && <div className="absolute left-[9px] top-5 bottom-0 w-0.5 bg-white/10"></div>}
                                <div className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center flex-shrink-0 mt-0.5 z-10 text-[10px] text-blue-300 font-bold font-mono">
                                    {i + 1}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <div className="text-xs font-bold text-gray-200">{title}</div>
                                    {transport && (
                                        <div className="text-[10px] text-gray-500 mt-0.5">
                                            ↓ {transport.duration || '约2.5km'}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <div className="text-center text-xs text-gray-500 py-4">
                        该日暂无活动安排
                    </div>
                )}
            </div>

            {/* 查看地图按钮 */}
            <button
                onClick={handleViewMap}
                className="w-full mt-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/5 rounded text-xs text-blue-300 transition-colors"
            >
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

    if (!weatherData || weatherData.length === 0) {
        return (
            <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn flex items-center justify-center h-32">
                <div className="text-gray-500 text-xs flex flex-col items-center gap-2">
                    <CloudSun size={24} className="opacity-50" />
                    <p>暂无天气信息</p>
                </div>
            </div>
        );
    }

    const hasBadWeather = weatherData.some(f => f.cond?.includes('雨') || f.cond?.includes('雪'));

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <CloudSun size={14} className="text-yellow-400" /> 天气趋势
                </h4>
                <span className="text-[10px] text-gray-500">{destination || '未知'}</span>
            </div>

            <div className="space-y-3">
                {weatherData.map((f, i) => (
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
    // 分类名称映射和样式
    const getCategoryDisplay = (category) => {
        const categoryMap = {
            'attractions': { label: '景点', style: 'text-green-400 bg-green-400/10' },
            'events': { label: '活动', style: 'text-pink-400 bg-pink-400/10' },
            'transport': { label: '交通', style: 'text-orange-400 bg-orange-400/10' },
            'tips': { label: '攻略', style: 'text-blue-400 bg-blue-400/10' },
            'general': { label: '资讯', style: 'text-gray-400 bg-gray-400/10' },
        };
        return categoryMap[category] || categoryMap['general'];
    };

    const getTagStyle = (tag) => {
        // 兼容旧格式（中文标签）和新格式（英文分类）
        const display = getCategoryDisplay(tag);
        if (display.style !== 'text-gray-400 bg-gray-400/10') {
            return display.style;
        }

        // 旧格式兼容
        switch (tag) {
            case '警告':
            case 'Warning':
            case '交通':
                return 'text-orange-400 bg-orange-400/10';
            case '活动':
            case 'Event':
                return 'text-pink-400 bg-pink-400/10';
            case '景点':
                return 'text-green-400 bg-green-400/10';
            case '攻略':
                return 'text-blue-400 bg-blue-400/10';
            default:
                return 'text-gray-400 bg-gray-400/10';
        }
    };

    const getTagLabel = (tag) => {
        const display = getCategoryDisplay(tag);
        if (display.label !== '资讯') {
            return display.label;
        }
        return tag; // 如果是中文标签，直接返回
    };

    // 点击资讯跳转到外部链接
    const handleNewsClick = (url) => {
        if (url) {
            window.open(url, '_blank', 'noopener,noreferrer');
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
                    disabled={isLoading}
                    className={`text-gray-500 hover:text-white transition-colors ${isLoading ? 'animate-spin' : ''}`}
                    title="刷新资讯"
                >
                    <RefreshCw size={12} />
                </button>
            </div>

            <div className="space-y-3">
                {newsData && newsData.length > 0 ? (
                    newsData.map((news, i) => (
                        <div
                            key={i}
                            onClick={() => handleNewsClick(news.url)}
                            className="group cursor-pointer hover:bg-white/5 rounded-lg p-2 -mx-2 transition-colors"
                        >
                            <div className="flex justify-between items-start gap-2">
                                <h5 className="text-xs text-gray-200 font-medium group-hover:text-blue-400 transition-colors line-clamp-2 flex-1">
                                    {news.title}
                                </h5>
                                {news.url && (
                                    <ExternalLink size={10} className="text-gray-500 group-hover:text-blue-400 flex-shrink-0 mt-0.5" />
                                )}
                            </div>
                            <div className="flex justify-between items-center mt-1">
                                <span className={`text-[9px] px-1.5 py-0.5 rounded ${getTagStyle(news.tag)}`}>
                                    {getTagLabel(news.tag)}
                                </span>
                            </div>
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
const BudgetDashboardWidget = ({ budgetData, itinerary }) => {
    // 用户自定义预算状态
    const [userBudget, setUserBudget] = useState(0);

    // 基于实际行程计算精确预算
    const calculateBudget = () => {
        if (!itinerary || itinerary.length === 0) {
            return null;
        }

        let accommodationCost = 0;
        let accommodationDetails = [];
        let ticketCost = 0;
        let ticketDetails = [];
        let transportCost = 0;
        let transportDetails = [];

        const days = itinerary.length;
        const nights = Math.max(days - 1, 0);

        // 门票价格表（常见景点）
        const ticketPrices = {
            '故宫': 60, '颐和园': 30, '长城': 45, '天坛': 15,
            '环球影城': 538, '迪士尼': 475, '欢乐谷': 299,
            '博物馆': 0, '纪念馆': 0, '国家博物馆': 0,
            '鸟巢': 50, '水立方': 30, '天安门': 0, '王府井': 0,
            '南锣鼓巷': 0, '什刹海': 0, '后海': 0, '798': 0,
        };

        for (const day of itinerary) {
            // 住宿费用
            const accommodation = day.accommodation;
            if (accommodation && accommodation.price) {
                const priceStr = accommodation.price;
                const match = priceStr.match(/(\d+)/);
                if (match) {
                    const price = parseInt(match[1]);
                    accommodationCost += price;
                    accommodationDetails.push({
                        name: accommodation.name || '酒店',
                        price: price,
                    });
                }
            }

            // 门票和交通费用
            const activities = day.activities || [];
            for (const activity of activities) {
                const title = activity.title || '';
                const type = activity.type || '';

                // 跳过交通和酒店类型的活动
                if (type === 'transport' || type === 'hotel') continue;

                // 门票估算
                let ticketPrice = 0;
                for (const [keyword, price] of Object.entries(ticketPrices)) {
                    if (title.includes(keyword)) {
                        ticketPrice = price;
                        break;
                    }
                }
                // 如果没匹配到已知景点，检查是否是景点类型
                if (ticketPrice === 0 && (type === 'attraction' || type === 'sight')) {
                    // 默认估算
                    if (title.includes('公园') || title.includes('广场') || title.includes('胡同')) {
                        ticketPrice = 0; // 免费
                    } else {
                        ticketPrice = 30; // 普通景点
                    }
                }
                if (ticketPrice > 0) {
                    ticketCost += ticketPrice;
                    ticketDetails.push({ name: title, price: ticketPrice });
                }

                // 交通费用
                const transport = activity.transport_from_prev;
                if (transport) {
                    const method = transport.method || '';
                    let tCost = 0;
                    if (method.includes('地铁') || method.includes('公交')) {
                        tCost = 5;
                    } else if (method.includes('打车') || method.includes('出租') || method.includes('网约车')) {
                        tCost = 40;
                    } else if (method.includes('步行')) {
                        tCost = 0;
                    } else {
                        tCost = 10;
                    }
                    if (tCost > 0) {
                        transportCost += tCost;
                        transportDetails.push({ method, cost: tCost });
                    }
                }
            }
        }

        // 餐饮估算：每天约 150 元（早中晚）
        const foodCost = days * 150;

        // 其他费用：购物、零食等，约 50/天
        const otherCost = days * 50;

        const total = accommodationCost + ticketCost + transportCost + foodCost + otherCost;

        return {
            accommodation: {
                total: accommodationCost,
                details: accommodationDetails,
                nights: nights,
            },
            tickets: {
                total: ticketCost,
                details: ticketDetails,
            },
            transport: {
                total: transportCost,
                details: transportDetails,
            },
            food: {
                total: foodCost,
                perDay: 150,
            },
            other: {
                total: otherCost,
                perDay: 50,
            },
            grandTotal: total,
            days: days,
            nights: nights,
        };
    };

    const calculatedBudget = calculateBudget();

    // 如果没有行程数据，显示空状态
    if (!calculatedBudget) {
        return (
            <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
                <div className="flex justify-between items-center mb-4">
                    <h4 className="font-bold text-white text-sm flex items-center gap-2">
                        <TrendingUp size={14} className="text-emerald-400" /> 预算仪表盘
                    </h4>
                </div>
                <div className="text-center py-6 text-xs text-gray-500">
                    <p>暂无行程数据</p>
                    <p className="mt-1">生成行程后自动计算预算</p>
                </div>
            </div>
        );
    }

    // 总预算：用户设定 > 计算值*1.2
    const totalBudget = userBudget > 0
        ? userBudget
        : Math.ceil(calculatedBudget.grandTotal * 1.2);

    const percent = totalBudget > 0 ? (calculatedBudget.grandTotal / totalBudget) * 100 : 0;
    const remaining = totalBudget - calculatedBudget.grandTotal;
    const isOverBudget = percent > 100;

    // 编辑预算
    const handleEdit = () => {
        const input = prompt('请输入您的总预算 (CNY):', totalBudget.toString());
        if (input && !isNaN(Number(input))) {
            setUserBudget(Number(input));
        }
    };

    // 导出费用明细
    const handleExport = () => {
        const lines = [
            `=== ${calculatedBudget.days}天${calculatedBudget.nights}晚行程预算明细 ===`,
            '',
            `🏨 住宿 (${calculatedBudget.nights}晚): ¥${calculatedBudget.accommodation.total}`,
            ...calculatedBudget.accommodation.details.map(d => `   - ${d.name}: ¥${d.price}`),
            '',
            `🎫 门票: ¥${calculatedBudget.tickets.total}`,
            ...calculatedBudget.tickets.details.map(d => `   - ${d.name}: ¥${d.price}`),
            '',
            `🚇 交通: ¥${calculatedBudget.transport.total}`,
            `   (地铁/公交/打车等)`,
            '',
            `🍜 餐饮: ¥${calculatedBudget.food.total}`,
            `   (约¥${calculatedBudget.food.perDay}/天)`,
            '',
            `🛍️ 其他: ¥${calculatedBudget.other.total}`,
            `   (购物、零食等)`,
            '',
            `━━━━━━━━━━━━━━━━━━━━`,
            `预计总花费: ¥${calculatedBudget.grandTotal}`,
            `建议预算: ¥${totalBudget}`,
            `剩余空间: ¥${remaining}`,
        ];
        const text = lines.join('\n');

        navigator.clipboard.writeText(text).then(() => {
            alert('预算明细已复制到剪贴板！');
        }).catch(() => {
            alert('复制失败，请手动复制');
        });
    };

    // 分类图标
    const getCategoryIcon = (name) => {
        if (name.includes('住') || name.includes('酒店')) return <Hotel size={10} className="text-blue-400" />;
        if (name.includes('餐') || name.includes('吃') || name.includes('食')) return <Utensils size={10} className="text-orange-400" />;
        if (name.includes('交通') || name.includes('行')) return <Car size={10} className="text-cyan-400" />;
        if (name.includes('门票') || name.includes('票') || name.includes('玩')) return <Ticket size={10} className="text-yellow-400" />;
        return <TrendingUp size={10} className="text-gray-400" />;
    };

    // 构建分类数据
    const categories = [
        {
            name: `住宿 (${calculatedBudget.nights}晚)`,
            amount: calculatedBudget.accommodation.total,
            detail: calculatedBudget.accommodation.details.map(d => d.name).join('、'),
        },
        {
            name: '门票',
            amount: calculatedBudget.tickets.total,
            detail: calculatedBudget.tickets.details.length > 0
                ? calculatedBudget.tickets.details.slice(0, 3).map(d => d.name).join('、') + (calculatedBudget.tickets.details.length > 3 ? '等' : '')
                : '暂无',
        },
        {
            name: '交通',
            amount: calculatedBudget.transport.total,
            detail: '地铁/公交/打车',
        },
        {
            name: '餐饮',
            amount: calculatedBudget.food.total,
            detail: `约¥${calculatedBudget.food.perDay}/天`,
        },
        {
            name: '其他',
            amount: calculatedBudget.other.total,
            detail: '购物、零食等',
        },
    ];

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-white text-sm flex items-center gap-2">
                    <TrendingUp size={14} className="text-emerald-400" /> 预算仪表盘
                </h4>
                <button
                    onClick={handleEdit}
                    className="text-gray-500 hover:text-white transition-colors p-1 hover:bg-white/10 rounded"
                    title="修改总预算"
                >
                    <Edit3 size={12} />
                </button>
            </div>

            {/* 总预算进度 */}
            <div className="mb-4">
                <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-gray-400">总预算</span>
                    <span className="text-white font-mono font-bold">¥{totalBudget.toLocaleString()}</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                        className={`h-full rounded-full transition-all duration-1000 ${isOverBudget
                            ? 'bg-red-500'
                            : 'bg-gradient-to-r from-emerald-500 to-teal-400'
                            }`}
                        style={{ width: `${Math.min(percent, 100)}%` }}
                    ></div>
                </div>
                <div className="flex justify-between text-[10px] mt-1.5">
                    <span className={isOverBudget ? 'text-red-400' : 'text-emerald-400'}>
                        {Math.round(percent)}% 已规划
                    </span>
                    <span className="text-gray-500">
                        {remaining >= 0 ? `剩余 ¥${remaining.toLocaleString()}` : `超支 ¥${Math.abs(remaining).toLocaleString()}`}
                    </span>
                </div>
            </div>

            {/* 分类支出 */}
            <div className="space-y-2">
                {categories.map((item, i) => (
                    <div key={i} className="bg-white/5 rounded px-2 py-1.5">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-xs text-gray-300">
                                {getCategoryIcon(item.name)}
                                <span className="truncate max-w-[100px]">{item.name}</span>
                            </div>
                            <div className="text-xs font-mono text-white font-bold">¥{item.amount.toLocaleString()}</div>
                        </div>
                        {item.detail && (
                            <div className="text-[10px] text-gray-500 ml-5 truncate">{item.detail}</div>
                        )}
                    </div>
                ))}
            </div>

            {/* 总计 */}
            <div className="mt-3 pt-3 border-t border-white/10 flex justify-between items-center">
                <span className="text-xs text-gray-400">预计总花费</span>
                <span className="text-sm font-bold text-emerald-400">¥{calculatedBudget.grandTotal.toLocaleString()}</span>
            </div>

            {/* 导出按钮 */}
            <button
                onClick={handleExport}
                className="w-full mt-3 text-[10px] text-gray-500 hover:text-white transition-colors text-right flex items-center justify-end gap-1"
            >
                📋 导出费用明细 →
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
        if (!destination) return;

        setIsLoading(true);
        try {
            // 并行请求天气和资讯
            const [weatherRes, newsRes] = await Promise.all([
                fetch(`${API_BASE}/sidebar/weather/${encodeURIComponent(destination)}`).catch(() => null),
                fetch(`${API_BASE}/sidebar/news/${encodeURIComponent(destination)}`).catch(() => null),
            ]);

            const weatherData = weatherRes?.ok ? await weatherRes.json() : null;
            const newsData = newsRes?.ok ? await newsRes.json() : null;

            // 转换天气数据格式：后端返回 { forecasts: [{ date, week, day_weather, day_temp, ... }] }
            // 前端期望：[{ day, temp, cond }]
            // 星期映射
            const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
            const getWeekDay = (dateStr, fallback) => {
                // 如果已有 week 字段（如"星期一"），直接转换
                if (fallback && fallback.includes('星期')) {
                    return fallback.replace('星期', '周');
                }
                // 尝试解析日期获取星期
                if (dateStr) {
                    const date = new Date(dateStr);
                    if (!isNaN(date.getTime())) {
                        return weekDays[date.getDay()];
                    }
                }
                return fallback || '今天';
            };

            const formattedForecast = (weatherData?.forecasts || []).map((f, idx) => ({
                day: idx === 0 ? '今天' : getWeekDay(f.date, f.week),
                temp: f.day_temp || '--',
                cond: f.day_weather || '未知',
            }));

            // 转换资讯数据格式：后端返回 { news: [{ title, category, ... }] }
            // 前端期望：[{ title, tag }]
            const formattedNews = (newsData?.news || []).map((n) => ({
                title: n.title || '',
                tag: n.category === 'transport' ? '交通' :
                    n.category === 'events' ? '活动' :
                        n.category === 'attractions' ? '景点' : '资讯',
                url: n.url || '',
            }));

            setSidebarInfo({
                forecast: formattedForecast,
                news: formattedNews,
            });
        } catch (error) {
            console.error('Failed to fetch sidebar data:', error);
        }
        setIsLoading(false);
    };

    useEffect(() => {
        // 当目的地变化或行程生成后，获取天气和资讯数据
        if (destination && destination !== '未知目的地') {
            fetchSidebarData();
        }
    }, [destination, itinerary?.length > 0]);

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
            <BudgetDashboardWidget budgetData={budget} itinerary={itinerary} />
        </div>
    );
}
