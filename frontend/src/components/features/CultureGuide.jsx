/**
 * 文化锦囊组件
 */

import React from 'react';
import { Globe, Languages, X, CheckCircle2 } from 'lucide-react';

export function CultureGuide({ data }) {
  if (!data) return <div className="text-center text-gray-500">无法获取文化信息</div>;

  return (
    <div className="space-y-6">
      {/* 禁忌 & 礼仪 */}
      <div className="space-y-3 animate-fadeIn">
        <h4 className="text-white font-semibold flex items-center gap-2">
          <Globe size={18} className="text-blue-400" /> 社交禁忌 & 礼仪
        </h4>
        <div className="grid grid-cols-1 gap-3">
          {data.taboos?.map((taboo, i) => (
            <div
              key={i}
              className="bg-red-900/10 border border-red-500/20 p-3 rounded-xl flex gap-3 items-start"
            >
              <div className="bg-red-500/20 text-red-400 p-1 rounded-full mt-0.5">
                <X size={12} />
              </div>
              <p className="text-sm text-gray-300">{taboo}</p>
            </div>
          ))}
          {data.etiquette && (
            <div className="bg-green-900/10 border border-green-500/20 p-3 rounded-xl flex gap-3 items-start">
              <div className="bg-green-500/20 text-green-400 p-1 rounded-full mt-0.5">
                <CheckCircle2 size={12} />
              </div>
              <p className="text-sm text-gray-300">{data.etiquette}</p>
            </div>
          )}
        </div>
      </div>

      {/* 地道话术 */}
      <div className="space-y-3 animate-fadeIn" style={{ animationDelay: '100ms' }}>
        <h4 className="text-white font-semibold flex items-center gap-2">
          <Languages size={18} className="text-yellow-400" /> 地道话术
        </h4>
        <div className="grid grid-cols-1 gap-2">
          {data.phrases?.map((p, i) => (
            <div
              key={i}
              className="bg-white/5 border border-white/5 rounded-xl p-3 flex justify-between items-center"
            >
              <div>
                <div className="text-white font-bold">{p.local}</div>
                <div className="text-xs text-gray-500">{p.pronunciation}</div>
              </div>
              <div className="text-sm text-gray-300 text-right">{p.meaning}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default CultureGuide;
