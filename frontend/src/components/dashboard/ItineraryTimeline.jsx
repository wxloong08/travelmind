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
  Video,
  CheckCircle2,
  CheckSquare,
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

// 安全渲染函数：防止对象直接渲染导致 React 崩溃
const safeRender = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);
  if (typeof value === 'object') {
    // 尝试提取常见字段
    if (value.name) return value.name;
    if (value.title) return value.title;
    if (value.text) return value.text;
    // 最后 fallback 为 JSON
    try {
      return JSON.stringify(value);
    } catch {
      return '[Object]';
    }
  }
  return String(value);
};

export function ItineraryTimeline() {
  const { itinerary, openDetailModal, toggleCheckIn } = useTravelStore();
  const { getDayTips, generateDiary, generateVlogScript } = useAiFeature();

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
                <span className="text-blue-400">Day {safeRender(day.day)}</span>
                {safeRender(day.title)}
              </h3>
              <div className="text-gray-400 text-xs lg:text-sm flex items-center gap-2">
                <Calendar size={14} />
                第 {safeRender(day.day)} 天
              </div>
            </div>

            {/* 功能按钮 */}
            <div className="flex gap-2">
              <button
                onClick={() => generateVlogScript(day)}
                className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white"
                title="生成 Vlog 脚本"
              >
                <Video size={14} className="text-purple-400" />
                <span>脚本</span>
              </button>
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
              const isChecked = act.checked;
              const transport = act.transport_from_prev;

              return (
                <div key={actIdx}>
                  {/* 交通信息卡片 */}
                  {transport && (
                    <div className="flex flex-wrap items-center gap-2 py-2 px-3 mb-2 text-xs text-gray-400 bg-gray-800/50 rounded-lg border border-gray-700/50">
                      <span className="text-cyan-400">🚗</span>
                      <span className="text-gray-500">从</span>
                      <span className="text-gray-300">{safeRender(transport.from)}</span>
                      <span className="text-gray-600">→</span>
                      <span className="text-cyan-300 font-medium">{safeRender(transport.method)}</span>
                      <span className="text-yellow-400 font-mono">{safeRender(transport.duration)}</span>
                      {transport.detail && (
                        <span className="text-gray-500" title={safeRender(transport.detail)}>
                          ({safeRender(transport.detail)})
                        </span>
                      )}
                    </div>
                  )}

                  {/* 活动卡片 */}
                  <div
                    className={`bg-white/5 border border-white/10 rounded-xl p-3 lg:p-4 hover:bg-white/10 hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-900/10 hover:-translate-y-0.5 transition-all cursor-pointer group relative active:scale-[0.99] active:bg-white/5 ${isChecked ? 'opacity-60 grayscale' : ''}`}
                  >
                    {/* 打卡按钮和箭头 */}
                    <div className="absolute top-4 right-4 flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleCheckIn(dayIdx, actIdx);
                        }}
                        className={`p-1.5 rounded-full transition-colors ${isChecked ? 'text-green-400 bg-green-900/30' : 'text-gray-600 hover:text-green-400 hover:bg-green-900/20'}`}
                        title="打卡"
                      >
                        {isChecked ? <CheckSquare size={18} /> : <CheckCircle2 size={18} />}
                      </button>
                      <div className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                        <ChevronRight size={18} />
                      </div>
                    </div>

                    <div
                      className="flex items-start gap-3 lg:gap-4"
                      onClick={() => handleActivityClick(dayIdx, actIdx, act)}
                    >
                      {/* 图标 */}
                      <div className="mt-1 p-2 rounded-lg bg-gray-800 text-blue-400 group-hover:scale-110 transition-transform shrink-0">
                        <Icon size={16} />
                      </div>

                      {/* 内容 */}
                      <div className="flex-1 min-w-0 pr-10">
                        <div className="flex justify-between items-start flex-wrap gap-2">
                          <h4 className={`font-semibold text-gray-200 truncate pr-2 group-hover:text-blue-300 transition-colors ${isChecked ? 'line-through text-gray-500' : ''}`}>
                            {safeRender(act.title)}
                          </h4>
                          <span className="text-xs font-mono text-gray-500 bg-gray-800 px-2 py-0.5 rounded whitespace-nowrap">
                            {safeRender(act.time)}
                          </span>
                        </div>
                        <p className="text-xs lg:text-sm text-gray-400 mt-1 line-clamp-2">
                          {safeRender(act.desc)}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 每日住宿推荐卡片 */}
          {day.accommodation && (
            <div className="mt-4 bg-gradient-to-r from-amber-900/20 to-orange-900/20 border border-amber-500/20 rounded-xl p-4 group hover:border-amber-500/40 transition-all">
              <div className="flex items-start gap-4">
                {/* 酒店图标 */}
                <div className="p-3 rounded-xl bg-amber-500/20 text-amber-400 shrink-0">
                  <Hotel size={20} />
                </div>

                {/* 酒店信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-amber-200 flex items-center gap-2">
                      🏨 今晚入住
                      <span className="text-xs font-normal text-amber-400/70">
                        (方便明日行程)
                      </span>
                    </h4>
                    <span className="text-lg font-bold text-amber-300">
                      {safeRender(day.accommodation.price)}
                    </span>
                  </div>

                  <p className="text-white font-medium mb-1">
                    {safeRender(day.accommodation.name)}
                  </p>

                  {day.accommodation.address && (
                    <p className="text-xs text-gray-400 flex items-center gap-1 mb-2">
                      <MapPin size={12} />
                      {safeRender(day.accommodation.address)}
                    </p>
                  )}

                  {/* 智能判断是否换酒店 */}
                  {(() => {
                    // 获取下一天的酒店信息
                    const nextDay = itinerary[dayIdx + 1];
                    const currentHotel = day.accommodation?.name;
                    const nextHotel = nextDay?.accommodation?.name;
                    const isLastDay = dayIdx >= itinerary.length - 1;
                    const isSecondLastDay = dayIdx === itinerary.length - 2;

                    // 最后一天和倒数第二天不显示
                    if (isLastDay || isSecondLastDay) return null;

                    // 检查是否需要换酒店
                    const willChangeHotel = currentHotel && nextHotel &&
                      currentHotel !== nextHotel &&
                      !currentHotel.includes(nextHotel) &&
                      !nextHotel.includes(currentHotel);

                    if (willChangeHotel) {
                      return (
                        <span className="text-xs bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded-full">
                          ⚠️ 明日需换酒店
                        </span>
                      );
                    }

                    return (
                      <span className="text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded-full">
                        ✓ 明天继续住这里
                      </span>
                    );
                  })()}

                  {/* 换酒店行李提示 */}
                  {(() => {
                    const nextDay = itinerary[dayIdx + 1];
                    const currentHotel = day.accommodation?.name;
                    const nextHotel = nextDay?.accommodation?.name;
                    const willChangeHotel = currentHotel && nextHotel &&
                      currentHotel !== nextHotel &&
                      !currentHotel.includes(nextHotel) &&
                      !nextHotel.includes(currentHotel);

                    if (willChangeHotel && dayIdx < itinerary.length - 2) {
                      return (
                        <div className="mt-2 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                          <p className="text-xs text-yellow-200/80">
                            💼 <span className="font-medium">行李建议：</span>早餐后退房，可寄存酒店前台或行李柜，游玩结束后取回再前往新酒店
                          </p>
                        </div>
                      );
                    }
                    return null;
                  })()}

                  {/* 入住提示 */}
                  {day.accommodation.check_in_note && (
                    <p className="text-xs text-gray-400 mt-2 italic">
                      💡 {safeRender(day.accommodation.check_in_note)}
                    </p>
                  )}

                  {/* 推荐理由 */}
                  {day.accommodation.reason && (
                    <p className="text-xs text-amber-200/70 mt-2">
                      📍 {safeRender(day.accommodation.reason)}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default ItineraryTimeline;
