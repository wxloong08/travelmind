/**
 * 旅行日记组件
 */

import React from 'react';
import { Feather, Quote } from 'lucide-react';

export function DiaryCard({ data }) {
  // 处理各种可能的数据格式
  if (!data) return <div className="text-center text-gray-500">日记生成失败</div>;

  // 兼容不同的数据格式
  let text = '';
  if (typeof data === 'string') {
    text = data;
  } else if (data.text) {
    text = data.text;
  } else if (data.story) {
    text = data.story;
  } else if (data.error) {
    return <div className="text-center text-red-400">{data.error}</div>;
  }

  // 如果还是空的，显示加载中或错误
  if (!text || text.trim() === '') {
    return <div className="text-center text-gray-500">正在生成日记...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-br from-pink-900/20 to-purple-900/20 border border-pink-500/20 rounded-2xl p-6 relative overflow-hidden">
        {/* 装饰性引号 */}
        <Quote className="absolute top-4 left-4 w-12 h-12 text-pink-500/10" />
        <Quote className="absolute bottom-4 right-4 w-12 h-12 text-pink-500/10 rotate-180" />

        {/* 日记内容 */}
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-4">
            <Feather size={20} className="text-pink-400" />
            <span className="text-pink-400 font-semibold">旅行手记</span>
          </div>

          {/* 使用 prose 样式渲染 Markdown 风格内容 */}
          <div
            className="text-gray-200 leading-relaxed text-sm prose prose-invert prose-sm max-w-none
                       prose-headings:text-pink-300 prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                       prose-p:my-2 prose-strong:text-pink-200"
            style={{ whiteSpace: 'pre-wrap' }}
          >
            {text}
          </div>
        </div>
      </div>

      {/* 分享提示 */}
      <div className="text-center text-xs text-gray-500">
        ✨ AI 为您生成的专属旅行回忆
      </div>
    </div>
  );
}

export default DiaryCard;
