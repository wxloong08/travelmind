/**
 * 预算估算卡片
 */

import React from 'react';
import { Banknote, Sparkles, Zap } from 'lucide-react';

export function BudgetCard({ data }) {
  if (!data) return <div className="text-center text-gray-500">无法获取预算数据</div>;

  return (
    <div className="space-y-6">
      {/* 总预算 */}
      <div className="bg-gradient-to-r from-emerald-900/30 to-teal-900/30 border border-emerald-500/20 rounded-2xl p-6 text-center">
        <h3 className="text-gray-400 text-sm mb-1 uppercase tracking-wider">
          预估总花费 (不含大交通)
        </h3>
        <div className="text-4xl font-bold text-white text-shadow-lg">
          {data.total_range}
        </div>
        <div className="text-emerald-400 text-xs mt-2 flex items-center justify-center gap-1">
          <Sparkles size={12} /> 基于当前目的地物价估算
        </div>
      </div>

      {/* 费用明细 */}
      <div className="space-y-3">
        <h4 className="text-white font-semibold flex items-center gap-2">
          <Banknote size={18} className="text-emerald-400" /> 费用明细
        </h4>
        {data.categories?.map((cat, i) => (
          <div
            key={i}
            className="bg-white/5 border border-white/5 rounded-xl p-4 flex justify-between items-center"
          >
            <div>
              <div className="text-gray-200 font-medium">{cat.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{cat.desc}</div>
            </div>
            <div className="text-emerald-300 font-mono font-bold">{cat.amount}</div>
          </div>
        ))}
      </div>

      {/* 省钱贴士 */}
      {data.saving_tip && (
        <div className="bg-blue-900/10 border border-blue-500/10 p-4 rounded-xl">
          <h4 className="text-blue-300 font-bold mb-2 flex items-center gap-2 text-sm">
            <Zap size={14} /> 省钱小妙招
          </h4>
          <p className="text-sm text-gray-300 leading-relaxed">{data.saving_tip}</p>
        </div>
      )}
    </div>
  );
}

export default BudgetCard;
