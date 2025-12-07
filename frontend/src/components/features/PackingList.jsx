/**
 * 行李清单组件
 */

import React, { useState } from 'react';
import { CheckCircle2, Circle, Sparkles } from 'lucide-react';

export function PackingList({ data }) {
  const [checkedItems, setCheckedItems] = useState({});

  const toggleItem = (catIdx, itemIdx) => {
    const key = `${catIdx}-${itemIdx}`;
    setCheckedItems((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!data || !data.categories) {
    return <div className="text-gray-400 text-center">数据解析失败</div>;
  }

  return (
    <div className="space-y-6">
      {/* 特别提醒 */}
      {data.special_tips && (
        <div className="bg-blue-900/20 border border-blue-500/20 p-4 rounded-xl mb-4">
          <h4 className="text-blue-300 font-bold mb-2 flex items-center gap-2">
            <Sparkles size={16} /> AI 特别提醒
          </h4>
          <p className="text-sm text-gray-300 leading-relaxed">{data.special_tips}</p>
        </div>
      )}

      {/* 分类列表 */}
      {data.categories.map((cat, catIdx) => (
        <div
          key={catIdx}
          className="animate-fadeIn"
          style={{ animationDelay: `${catIdx * 100}ms` }}
        >
          <h4 className="text-white font-semibold mb-3 border-l-4 border-purple-500 pl-3">
            {cat.name}
          </h4>
          <div className="grid grid-cols-1 gap-3">
            {cat.items?.map((item, itemIdx) => {
              const isChecked = checkedItems[`${catIdx}-${itemIdx}`];
              return (
                <div
                  key={itemIdx}
                  onClick={() => toggleItem(catIdx, itemIdx)}
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                    isChecked
                      ? 'bg-green-900/10 border-green-500/30'
                      : 'bg-white/5 border-white/5 hover:bg-white/10'
                  }`}
                >
                  <div
                    className={`mt-0.5 transition-colors ${
                      isChecked ? 'text-green-500' : 'text-gray-500'
                    }`}
                  >
                    {isChecked ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                  </div>
                  <div className="flex-1">
                    <div
                      className={`font-medium text-sm transition-all ${
                        isChecked ? 'text-gray-500 line-through' : 'text-gray-200'
                      }`}
                    >
                      {item.name}
                    </div>
                    {item.reason && (
                      <div className="text-xs text-gray-500 mt-1">{item.reason}</div>
                    )}
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

export default PackingList;
