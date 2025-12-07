/**
 * 行程时间轴组件
 */

import React from 'react';
import {
  Calendar,
  MapPin,
  Coffee,
  Hotel,
  ChevronRight,
  Lightbulb,
  Feather,
  Sparkles,
} from 'lucide-react';
import useTravelStore from '../../store/useTravelStore';
import { useAiFeature } from '../../hooks';

// 活动类型图标
const typeIcons = {
  sight: MapPin,
  food: Coffee,
  hotel: Hotel,
  default: MapPin,
};

export function ItineraryTimeline() {
  const { itinerary, openDetailModal } = useTravelStore();
  const { getDayTips, generateDiary } = useAiFeature();

  // 空状态
  if (!itinerary || itinerary.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <Sparkles size={48} className="mb-4 opacity-20" />
        <p>暂无行程，请在左侧告诉 AI 您的旅行计划</p>
      </div>
    );
  }

  // 点击活动
  const handleActivityClick = (dayIdx, actIdx, activity) => {
    openDetailModal(activity, {
      type: 'itinerary',
      dayIdx,
      actIdx,
    });
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {itinerary.map((day, dayIdx) => (
        <div key={dayIdx} className="relative pl-6 border-l-2 border-white/10 pb-2">
          {/* 时间轴圆点 */}
          <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-blue-500 ring-4 ring-gray-900/50" />

          {/* 日期标题 */}
          <div className="mb-6 flex justify-between items-start">
            <div>
              <h3 className="text-lg lg:text-xl font-bold text-white mb-1 flex items-center gap-2">
                <span className="text-blue-400">Day {day.day}</span>
                {day.title}
              </h3>
              <div className="text-gray-400 text-xs lg:text-sm flex items-center gap-2">
                <Calendar size={14} />
                第 {day.day} 天
              </div>
            </div>

            {/* 功能按钮 */}
            <div className="flex gap-2">
              <button
                onClick={() => generateDiary(day)}
                className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white"
                title="生成日记"
              >
                <Feather size={14} className="text-pink-400" />
                <span>日记</span>
              </button>
              <button
                onClick={() => getDayTips(day, dayIdx)}
                className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white"
              >
                <Lightbulb size={14} className="text-yellow-500" />
                <span>AI 攻略</span>
              </button>
            </div>
          </div>

          {/* 活动列表 */}
          <div className="space-y-3">
            {day.activities?.map((act, actIdx) => {
              const Icon = typeIcons[act.type] || typeIcons.default;

              return (
                <div
                  key={actIdx}
                  onClick={() => handleActivityClick(dayIdx, actIdx, act)}
                  className="bg-white/5 border border-white/10 rounded-xl p-3 lg:p-4 hover:bg-white/10 hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-900/10 hover:-translate-y-0.5 transition-all cursor-pointer group relative active:scale-[0.99] active:bg-white/5"
                >
                  {/* 箭头指示 */}
                  <div className="absolute top-4 right-4 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight size={18} />
                  </div>

                  <div className="flex items-start gap-3 lg:gap-4">
                    {/* 图标 */}
                    <div className="mt-1 p-2 rounded-lg bg-gray-800 text-blue-400 group-hover:scale-110 transition-transform shrink-0">
                      <Icon size={16} />
                    </div>

                    {/* 内容 */}
                    <div className="flex-1 min-w-0 pr-6">
                      <div className="flex justify-between items-start flex-wrap gap-2">
                        <h4 className="font-semibold text-gray-200 truncate pr-2 group-hover:text-blue-300 transition-colors">
                          {act.title}
                        </h4>
                        <span className="text-xs font-mono text-gray-500 bg-gray-800 px-2 py-0.5 rounded whitespace-nowrap">
                          {act.time}
                        </span>
                      </div>
                      <p className="text-xs lg:text-sm text-gray-400 mt-1 line-clamp-2">
                        {act.desc}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export default ItineraryTimeline;
