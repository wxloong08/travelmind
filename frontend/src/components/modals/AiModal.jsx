/**
 * AI 功能 Modal
 * 
 * 显示各种 AI 助手功能的结果
 */

import React from 'react';
import {
  X,
  RefreshCw,
  Loader2,
  Backpack,
  Banknote,
  Music,
  Siren,
  Globe,
  ShoppingBag,
  Aperture,
  Sparkles,
  Feather,
  Lightbulb,
} from 'lucide-react';
import useTravelStore from '../../store/useTravelStore';
import { useAiFeature } from '../../hooks';

// 功能卡片组件
import BudgetCard from '../features/BudgetCard';
import PackingList from '../features/PackingList';
import PlaylistCard from '../features/PlaylistCard';
import EmergencyKit from '../features/EmergencyKit';
import CultureGuide from '../features/CultureGuide';
import SouvenirGuide from '../features/SouvenirGuide';
import PhotoChallenge from '../features/PhotoChallenge';
import TipsCard from '../features/TipsCard';
import DiaryCard from '../features/DiaryCard';

// Modal 类型配置
const modalConfig = {
  budget: { icon: Banknote, color: 'emerald' },
  packing: { icon: Backpack, color: 'blue' },
  playlist: { icon: Music, color: 'violet' },
  emergency: { icon: Siren, color: 'red' },
  culture: { icon: Globe, color: 'blue' },
  souvenirs: { icon: ShoppingBag, color: 'pink' },
  photo_challenge: { icon: Aperture, color: 'indigo' },
  tips: { icon: Lightbulb, color: 'yellow' },
  diary: { icon: Feather, color: 'pink' },
};

export function AiModal() {
  const { modal, closeModal } = useTravelStore();
  const { regenerate } = useAiFeature();

  const { isOpen, type, title, content, isLoading, context } = modal;

  if (!isOpen) return null;

  const config = modalConfig[type] || { icon: Sparkles, color: 'blue' };
  const Icon = config.icon;

  // 渲染内容
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center py-12 gap-4">
          <Loader2 size={32} className="text-blue-500 animate-spin" />
          <p className="text-sm text-blue-300 animate-pulse">
            AI 正在为您精心定制内容...
          </p>
        </div>
      );
    }

    if (content?.error) {
      return (
        <div className="text-center text-red-400 py-8">
          <p>{content.error}</p>
        </div>
      );
    }

    switch (type) {
      case 'budget':
        return <BudgetCard data={content} />;
      case 'packing':
        return <PackingList data={content} />;
      case 'playlist':
        return <PlaylistCard data={content} />;
      case 'emergency':
        return <EmergencyKit data={content} />;
      case 'culture':
        return <CultureGuide data={content} />;
      case 'souvenirs':
        return <SouvenirGuide data={content} />;
      case 'photo_challenge':
        return <PhotoChallenge data={content} />;
      case 'tips':
        return <TipsCard data={content} />;
      case 'diary':
        return <DiaryCard data={content} />;
      default:
        return (
          <div className="text-gray-300">
            {typeof content === 'string' ? content : JSON.stringify(content)}
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-[#1a1d2d] border border-white/10 rounded-2xl w-full max-w-md md:max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-blue-900/30 to-purple-900/30">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 truncate pr-2">
            <Icon size={18} className={`text-${config.color}-400 flex-shrink-0`} />
            {title}
          </h3>
          <div className="flex items-center gap-2 flex-shrink-0">
            {!isLoading && (
              <button
                onClick={() => regenerate(type, context)}
                title="重新生成"
                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors flex items-center gap-1 text-xs"
              >
                <RefreshCw size={14} />
                <span className="hidden sm:inline">重新生成</span>
              </button>
            )}
            <button
              onClick={closeModal}
              className="text-gray-400 hover:text-white transition-colors p-1.5 hover:bg-white/10 rounded-full"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto custom-scrollbar flex-1 bg-[#131520]">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default AiModal;
