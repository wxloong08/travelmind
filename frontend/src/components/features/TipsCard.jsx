/**
 * 每日攻略组件
 */

import React from 'react';
import { Camera, AlertTriangle, Utensils, Navigation } from 'lucide-react';

export function TipsCard({ data }) {
  if (!data) return <div className="text-center text-gray-500">数据加载失败</div>;

  return (
    <div className="space-y-6">
      {/* 拍照点 */}
      {data.photo_spots && data.photo_spots.length > 0 && (
        <div className="animate-fadeIn">
          <h4 className="flex items-center gap-2 text-pink-400 font-bold mb-3 text-lg">
            <Camera size={20} /> 最佳出片机位
          </h4>
          <div className="grid grid-cols-1 gap-3">
            {data.photo_spots.map((spot, i) => (
              <div
                key={i}
                className="bg-white/5 border border-white/10 rounded-xl p-3 flex gap-3"
              >
                <div className="bg-pink-500/20 text-pink-400 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-xs">
                  {i + 1}
                </div>
                <div>
                  <div className="text-white font-medium">{spot.name}</div>
                  <div className="text-xs text-gray-400 mt-1">{spot.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 避坑指南 */}
      {data.warnings && data.warnings.length > 0 && (
        <div className="animate-fadeIn" style={{ animationDelay: '100ms' }}>
          <h4 className="flex items-center gap-2 text-yellow-400 font-bold mb-3 text-lg">
            <AlertTriangle size={20} /> 避坑指南
          </h4>
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 space-y-3">
            {data.warnings.map((warn, i) => (
              <div key={i} className="flex gap-2 text-sm text-gray-200">
                <AlertTriangle
                  size={14}
                  className="text-yellow-500 mt-0.5 flex-shrink-0"
                />
                <span>{warn}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 美食推荐 */}
      {data.food && data.food.length > 0 && (
        <div className="animate-fadeIn" style={{ animationDelay: '200ms' }}>
          <h4 className="flex items-center gap-2 text-orange-400 font-bold mb-3 text-lg">
            <Utensils size={20} /> 美食推荐
          </h4>
          <div className="flex flex-wrap gap-2">
            {data.food.map((f, i) => (
              <span
                key={i}
                className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-orange-200"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 交通建议 */}
      {data.transport && (
        <div className="animate-fadeIn" style={{ animationDelay: '300ms' }}>
          <h4 className="flex items-center gap-2 text-blue-400 font-bold mb-2 text-lg">
            <Navigation size={20} /> 交通建议
          </h4>
          <p className="text-sm text-gray-300 bg-blue-500/10 border border-blue-500/20 p-3 rounded-xl">
            {data.transport}
          </p>
        </div>
      )}
    </div>
  );
}

export default TipsCard;
