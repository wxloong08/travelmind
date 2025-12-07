/**
 * 伴手礼指南组件
 */

import React from 'react';
import { ShoppingBag, AlertTriangle, X } from 'lucide-react';

export function SouvenirGuide({ data }) {
  if (!data) return <div className="text-center text-gray-500">无法获取购物建议</div>;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 必买推荐 */}
      <div className="space-y-3">
        <h4 className="text-white font-semibold flex items-center gap-2">
          <ShoppingBag size={18} className="text-pink-400" /> 必买伴手礼
        </h4>
        <div className="grid grid-cols-1 gap-3">
          {data.must_buy?.map((item, i) => (
            <div
              key={i}
              className="bg-white/5 border border-white/5 rounded-xl p-3 flex justify-between items-center"
            >
              <div>
                <div className="text-white font-bold">{item.name}</div>
                <div className="text-xs text-gray-400">{item.desc}</div>
              </div>
              <div className="bg-pink-500/10 text-pink-400 text-xs px-2 py-1 rounded">
                推荐
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 避坑指南 */}
      {data.avoid && data.avoid.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-white font-semibold flex items-center gap-2">
            <AlertTriangle size={18} className="text-red-400" /> 避坑指南 (不推荐)
          </h4>
          <div className="grid grid-cols-1 gap-2">
            {data.avoid.map((item, i) => (
              <div
                key={i}
                className="bg-red-900/10 border border-red-500/20 p-3 rounded-xl text-gray-300 text-sm flex gap-2"
              >
                <X size={16} className="text-red-400 mt-0.5 shrink-0" />
                {item}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SouvenirGuide;
