/**
 * 紧急助手组件
 */

import React from 'react';
import { AlertTriangle, Phone } from 'lucide-react';

export function EmergencyKit({ data }) {
  if (!data) return <div className="text-center text-gray-500">无法获取紧急信息</div>;

  return (
    <div className="space-y-6">
      {/* 紧急提示 */}
      <div className="bg-red-900/20 border border-red-500/30 p-4 rounded-xl flex items-start gap-3">
        <AlertTriangle className="text-red-500 flex-shrink-0 mt-1" />
        <div>
          <h4 className="text-red-400 font-bold mb-1">紧急提示</h4>
          <p className="text-gray-300 text-sm">
            {data.embassy_tip || '遇到危险请立即联系当地警方或领事馆。'}
          </p>
        </div>
      </div>

      {/* 紧急电话 */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(data.local_numbers || {}).map(([key, num], i) => (
          <div
            key={i}
            className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col items-center justify-center text-center"
          >
            <div className="text-gray-400 text-xs uppercase mb-2 tracking-wider">
              {key}
            </div>
            <div className="text-2xl font-bold text-white tracking-widest">{num}</div>
            <button className="mt-2 text-xs bg-white/10 hover:bg-green-600 hover:text-white px-3 py-1 rounded-full transition-colors flex items-center gap-1">
              <Phone size={10} /> 呼叫
            </button>
          </div>
        ))}
      </div>

      {/* SOS 求助卡 */}
      {data.sos_card && (
        <div className="border-2 border-dashed border-white/20 rounded-xl p-6 bg-white/5 mt-4 text-center relative">
          <h4 className="text-gray-400 text-xs uppercase tracking-widest mb-4">
            SOS 求助卡 (请向路人出示)
          </h4>
          <div className="text-3xl font-bold text-white mb-2">
            {data.sos_card.text_local}
          </div>
          <div className="text-gray-400 text-sm mb-1">
            {data.sos_card.pronunciation}
          </div>
          <div className="text-blue-400 text-sm font-medium">
            {data.sos_card.text_en}
          </div>
        </div>
      )}
    </div>
  );
}

export default EmergencyKit;
