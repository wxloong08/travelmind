/**
 * Vlog 脚本视图组件
 * 
 * 显示 AI 生成的 Vlog 拍摄脚本
 */

import React from 'react';
import { Video } from 'lucide-react';

export function VlogScriptView({ data }) {
    if (!data) return <div className="text-center text-gray-500">无法获取 Vlog 脚本</div>;

    return (
        <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-4">
                <div className="inline-flex items-center justify-center p-2 bg-purple-500/20 rounded-full mb-2">
                    <Video size={24} className="text-purple-400" />
                </div>
                <h3 className="text-xl font-bold text-white">Vlog 拍摄脚本</h3>
                <p className="text-sm text-gray-400">{data.title}</p>
            </div>

            <div className="space-y-4">
                {data.shots?.map((shot, i) => (
                    <div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4">
                        <div className="flex justify-between mb-2">
                            <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">
                                Shot {i + 1} • {shot.duration}
                            </span>
                            <span className="text-xs text-gray-500">{shot.angle}</span>
                        </div>
                        <p className="text-white font-medium mb-1">{shot.action}</p>
                        <p className="text-sm text-gray-400 italic">"{shot.audio}"</p>
                    </div>
                ))}
            </div>

            <div className="bg-purple-900/20 border border-purple-500/20 p-4 rounded-xl">
                <h4 className="text-sm font-bold text-purple-300 mb-1">🎵 配乐建议</h4>
                <p className="text-sm text-gray-300">{data.bgm}</p>
            </div>
        </div>
    );
}

export default VlogScriptView;
