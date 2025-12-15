/**
 * 历史行程抽屉组件
 * 
 * 从左侧滑出，显示历史行程卡片列表
 * 支持加载和删除操作
 */

import React, { useEffect } from 'react';
import { X, Plus, Trash2, MapPin, Calendar, Wallet, Loader2, History } from 'lucide-react';
import { useTripHistory } from '../../hooks';

/**
 * 格式化日期
 */
const formatDate = (dateStr) => {
    if (!dateStr) return '未知日期';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        });
    } catch {
        return dateStr;
    }
};

/**
 * 格式化预算
 */
const formatBudget = (amount) => {
    if (!amount) return null;
    return `¥${amount.toLocaleString()}`;
};

/**
 * 行程卡片组件
 */
function TripCard({ trip, onLoad, onDelete, isLoading }) {
    const handleDelete = (e) => {
        e.stopPropagation();
        if (window.confirm(`确定要删除"${trip.title}"吗？`)) {
            onDelete(trip.id);
        }
    };

    return (
        <div
            onClick={() => onLoad(trip.id)}
            className="group p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-500/30 rounded-xl cursor-pointer transition-all duration-200"
        >
            <div className="flex items-start justify-between gap-3">
                {/* 左侧：行程信息 */}
                <div className="flex-1 min-w-0">
                    {/* 主标题 */}
                    <h3 className="font-medium text-white truncate">
                        {trip.destination} {trip.days}天{trip.days - 1}晚
                    </h3>

                    {/* 副信息 */}
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            {formatDate(trip.created_at)}
                        </span>
                        {trip.estimated_budget && (
                            <span className="flex items-center gap-1">
                                <Wallet size={12} />
                                {formatBudget(trip.estimated_budget)} 估算
                            </span>
                        )}
                    </div>
                </div>

                {/* 右侧：删除按钮 */}
                <button
                    onClick={handleDelete}
                    disabled={isLoading}
                    className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                    title="删除行程"
                >
                    <Trash2 size={16} />
                </button>
            </div>
        </div>
    );
}

/**
 * 历史行程抽屉
 */
export function TripHistoryDrawer({ isOpen, onClose, onTripLoaded }) {
    const {
        trips,
        isLoading,
        error,
        total,
        fetchTrips,
        loadTrip,
        deleteTrip,
        createNewTrip,
    } = useTripHistory();

    // 打开抽屉时获取行程列表
    useEffect(() => {
        if (isOpen) {
            fetchTrips();
        }
    }, [isOpen, fetchTrips]);

    // 处理加载行程
    const handleLoadTrip = async (tripId) => {
        const success = await loadTrip(tripId);
        if (success) {
            onClose();
            onTripLoaded?.();
        }
    };

    // 处理新建行程
    const handleNewTrip = () => {
        createNewTrip();
        onClose();
        onTripLoaded?.();
    };

    if (!isOpen) return null;

    return (
        <>
            {/* 遮罩层 */}
            <div
                className="fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* 抽屉面板 */}
            <div className="fixed left-0 top-0 h-full w-80 z-[71] bg-[#0f111a] border-r border-white/10 shadow-2xl flex flex-col animate-slide-in-left">
                {/* 头部 */}
                <div className="h-16 border-b border-white/5 flex items-center justify-between px-4 bg-white/2 flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-gradient-to-tr from-purple-600 to-pink-600 shadow-lg">
                            <History size={18} className="text-white" />
                        </div>
                        <div>
                            <h2 className="font-bold text-white text-sm">历史行程</h2>
                            <p className="text-[10px] text-gray-500">{total} 个行程</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* 新建行程按钮 */}
                <div className="p-4 border-b border-white/5 flex-shrink-0">
                    <button
                        onClick={handleNewTrip}
                        className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-blue-600/20"
                    >
                        <Plus size={18} />
                        新建行程
                    </button>
                </div>

                {/* 行程列表 */}
                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                    {isLoading && trips.length === 0 ? (
                        <div className="flex items-center justify-center h-40">
                            <Loader2 size={24} className="text-blue-400 animate-spin" />
                        </div>
                    ) : error ? (
                        <div className="text-center text-red-400 py-8">
                            <p>加载失败</p>
                            <p className="text-xs mt-1">{error}</p>
                            <button
                                onClick={() => fetchTrips()}
                                className="mt-3 text-blue-400 hover:underline text-sm"
                            >
                                重试
                            </button>
                        </div>
                    ) : trips.length === 0 ? (
                        <div className="text-center text-gray-500 py-8">
                            <MapPin size={32} className="mx-auto mb-3 opacity-50" />
                            <p>暂无历史行程</p>
                            <p className="text-xs mt-1">开始规划你的第一次旅行吧！</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {trips.map((trip) => (
                                <TripCard
                                    key={trip.id}
                                    trip={trip}
                                    onLoad={handleLoadTrip}
                                    onDelete={deleteTrip}
                                    isLoading={isLoading}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* 动画样式 */}
            <style>{`
                @keyframes slide-in-left {
                    from {
                        transform: translateX(-100%);
                    }
                    to {
                        transform: translateX(0);
                    }
                }
                .animate-slide-in-left {
                    animation: slide-in-left 0.3s ease-out;
                }
            `}</style>
        </>
    );
}

export default TripHistoryDrawer;
