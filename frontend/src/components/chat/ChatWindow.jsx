/**
 * 聊天窗口组件
 * 
 * 包含消息列表和输入框
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Navigation } from 'lucide-react';
import ChatMessage from './ChatMessage';
import useTravelStore from '../../store/useTravelStore';
import { useStreamChat } from '../../hooks';

export function ChatWindow() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const { messages, isTyping } = useTravelStore();
  const { sendMessage } = useStreamChat();

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // 发送消息
  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  // 回车发送
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 头部 */}
      <div className="h-16 border-b border-white/5 flex items-center px-4 lg:px-6 bg-white/2">
        <div className="flex items-center gap-3">
          <img src="/favicon.png" alt="TravelMind" className="w-10 h-10 rounded-xl shadow-lg" />
          <div>
            <h1 className="text-lg font-bold text-white">TravelMind</h1>
            <p className="text-xs text-gray-400">AI 智能旅行管家</p>
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 custom-scrollbar">
        {messages.map((msg, idx) => (
          <ChatMessage
            key={idx}
            role={msg.role}
            content={msg.content}
            isStreaming={msg.isStreaming}
          />
        ))}

        {/* 正在输入指示器 */}
        {isTyping && (
          <ChatMessage role="ai" content="" isStreaming={true} />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="p-4 border-t border-white/5 bg-[#0f111a] lg:pb-4 pb-20">
        <div className="relative flex items-center bg-white/5 border border-white/10 rounded-2xl px-2 focus-within:border-blue-500/50 focus-within:bg-white/10 transition-all shadow-lg">
          <input
            type="text"
            className="flex-1 bg-transparent border-none text-white px-4 py-4 focus:ring-0 placeholder-gray-500 outline-none"
            placeholder="输入你的旅行计划..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSend}
            className={`p-2 rounded-xl transition-all duration-300 ${input.trim()
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-100'
                : 'bg-gray-700 text-gray-500 scale-90'
              }`}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
