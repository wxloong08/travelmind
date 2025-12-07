/**
 * 摄影指导组件
 * 
 * 显示景点拍照建议
 */

import React from 'react';
import { Camera, Clock, Target, Lightbulb, AlertTriangle } from 'lucide-react';

export function PhotoGuideView({ data }) {
    if (!data) return <div className="text-center text-gray-500">无法获取摄影指导</div>;

    return (
        <div className="space-y-4 animate-fadeIn">
            <div className="text-center mb-4">
                <div className="inline-flex items-center justify-center p-2 bg-pink-500/20 rounded-full mb-2">
                    <Camera size={24} className="text-pink-400" />
                </div>
                <h3 className="text-xl font-bold text-white">摄影指导</h3>
            </div>

            <div className="grid gap-3">
                {/* 最佳时间 */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex gap-3">
                    <Clock className="text-yellow-400 shrink-0 mt-1" size={20} />
                    <div>
                        <div className="text-sm font-semibold text-white mb-1">最佳拍摄时间</div>
                        <div className="text-sm text-gray-400">{data.best_time}</div>
                    </div>
                </div>

                {/* 最佳角度 */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex gap-3">
                    <Target className="text-blue-400 shrink-0 mt-1" size={20} />
                    <div>
                        <div className="text-sm font-semibold text-white mb-1">推荐拍摄角度</div>
                        <div className="text-sm text-gray-400">{data.best_angle}</div>
                    </div>
                </div>

                {/* 构图建议 */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex gap-3">
                    <Lightbulb className="text-green-400 shrink-0 mt-1" size={20} />
                    <div>
                        <div className="text-sm font-semibold text-white mb-1">构图技巧</div>
                        <div className="text-sm text-gray-400">{data.composition_tip}</div>
                    </div>
                </div>

                {/* 器材建议 */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex gap-3">
                    <Camera className="text-purple-400 shrink-0 mt-1" size={20} />
                    <div>
                        <div className="text-sm font-semibold text-white mb-1">器材建议</div>
                        <div className="text-sm text-gray-400">{data.gear_tip}</div>
                    </div>
                </div>

                {/* 避免事项 */}
                <div className="bg-red-900/20 border border-red-500/20 rounded-xl p-4 flex gap-3">
                    <AlertTriangle className="text-red-400 shrink-0 mt-1" size={20} />
                    <div>
                        <div className="text-sm font-semibold text-red-300 mb-1">注意避免</div>
                        <div className="text-sm text-gray-400">{data.avoid}</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default PhotoGuideView;
