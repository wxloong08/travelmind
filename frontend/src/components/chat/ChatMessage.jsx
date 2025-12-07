/**
 * 聊天消息组件
 * 
 * 支持用户/AI 消息展示，Markdown 渲染，打字机效果
 */

import React from 'react';
import { User, Bot } from 'lucide-react';

// 简化的 Markdown 渲染
function EnhancedMarkdown({ text }) {
  if (typeof text !== 'string') return null;

  const lines = text.split('\n');

  return (
    <div className="space-y-2 text-gray-300 leading-relaxed text-sm">
      {lines.map((line, i) => {
        // H3 标题
        if (line.startsWith('###')) {
          return (
            <h3 key={i} className="text-lg font-bold text-blue-300 mt-4 mb-2">
              {line.replace(/^###\s+/, '')}
            </h3>
          );
        }
        // 列表项
        if (line.trim().startsWith('*') || line.trim().startsWith('-')) {
          return (
            <li key={i} className="ml-4 list-disc text-gray-300">
              {line.replace(/^[\*\-]\s+/, '')}
            </li>
          );
        }
        // 空行
        if (!line.trim()) {
          return <div key={i} className="h-2" />;
        }
        // 普通段落
        return <p key={i}>{line}</p>;
      })}
    </div>
  );
}

export function ChatMessage({ role, content, isStreaming }) {
  const isUser = role === 'user';

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* AI 头像 */}
      {!isUser && (
        <div
          className={`w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 flex items-center justify-center mr-3 shadow-lg shadow-purple-500/30 flex-shrink-0 ${
            isStreaming ? 'animate-pulse ring-2 ring-purple-500/50' : ''
          }`}
        >
          <Bot size={16} className="text-white" />
        </div>
      )}

      {/* 消息气泡 */}
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-4 backdrop-blur-md shadow-sm ${
          isUser
            ? 'bg-blue-600/90 text-white rounded-br-none'
            : 'bg-white/10 text-gray-100 border border-white/10 rounded-bl-none'
        }`}
      >
        <div className="leading-relaxed text-sm md:text-base">
          {isUser ? content : <EnhancedMarkdown text={content} />}
          {/* 打字机光标 */}
          {!isUser && isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-blue-400 animate-pulse align-middle rounded-sm" />
          )}
        </div>
      </div>

      {/* 用户头像 */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center ml-3 border border-gray-600 flex-shrink-0">
          <User size={16} className="text-gray-300" />
        </div>
      )}
    </div>
  );
}

export default ChatMessage;
