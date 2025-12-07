/**
 * 摄影挑战组件
 */

import React, { useState } from 'react';
import { Aperture, CheckCircle2, Circle } from 'lucide-react';

export function PhotoChallenge({ data }) {
  const [completed, setCompleted] = useState({});

  const toggleChallenge = (index) => {
    setCompleted((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  if (!data) return <div className="text-center text-gray-500">无法获取挑战任务</div>;

  const completedCount = Object.values(completed).filter(Boolean).length;
  const totalCount = data.challenges?.length || 0;

  return (
    <div className="space-y-6">
      {/* 进度 */}
      <div className="bg-gradient-to-r from-indigo-900/30 to-purple-900/30 border border-indigo-500/20 rounded-2xl p-6 text-center">
        <div className="text-4xl font-bold text-white mb-2">
          {completedCount}/{totalCount}
        </div>
        <div className="text-indigo-300 text-sm">已完成挑战</div>
        <div className="mt-4 h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
            style={{ width: `${(completedCount / totalCount) * 100}%` }}
          />
        </div>
      </div>

      {/* 挑战列表 */}
      <div className="space-y-3">
        <h4 className="text-white font-semibold flex items-center gap-2">
          <Aperture size={18} className="text-indigo-400" /> 挑战任务
        </h4>
        {data.challenges?.map((challenge, i) => {
          const isCompleted = completed[i];
          return (
            <div
              key={i}
              onClick={() => toggleChallenge(i)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                isCompleted
                  ? 'bg-green-900/10 border-green-500/30'
                  : 'bg-white/5 border-white/5 hover:bg-white/10'
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`mt-0.5 transition-colors ${
                    isCompleted ? 'text-green-500' : 'text-gray-500'
                  }`}
                >
                  {isCompleted ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                </div>
                <div className="flex-1">
                  <div
                    className={`font-medium transition-all ${
                      isCompleted ? 'text-gray-500 line-through' : 'text-white'
                    }`}
                  >
                    {challenge.title}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{challenge.desc}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PhotoChallenge;
