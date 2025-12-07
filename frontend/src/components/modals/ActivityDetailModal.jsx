/**
 * 活动详情 Modal
 * 
 * 显示景点/酒店详情，支持讲故事、问路卡、评价等功能
 */

import React, { useState } from 'react';
import {
  X,
  MapPin,
  Star,
  Car,
  Loader2,
  Clock,
  Ticket,
  BookOpen,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
  Wifi,
  Dumbbell,
  UtensilsCrossed,
  BedDouble,
  Utensils,
  Share2,
  Camera,
  Sparkles,
  Info,
} from 'lucide-react';
import { assistantsApi } from '../../api/client';
import useTravelStore from '../../store/useTravelStore';

// 酒店设施图标映射
const facilityIcons = {
  wifi: Wifi,
  gym: Dumbbell,
  restaurant: UtensilsCrossed,
  pool: Wifi, // 暂用
  parking: Car,
};

export function ActivityDetailModal() {
  const { destination, detailModal, closeDetailModal, updateDetailActivity } =
    useTravelStore();

  const { isOpen, activity, path } = detailModal;

  // 本地状态
  const [activeTab, setActiveTab] = useState('overview');
  const [isGettingDirection, setIsGettingDirection] = useState(false);
  const [directionCard, setDirectionCard] = useState(null);
  const [isTellingStory, setIsTellingStory] = useState(false);
  const [story, setStory] = useState(null);
  const [isGettingReviews, setIsGettingReviews] = useState(false);
  const [reviews, setReviews] = useState(null);
  const [copied, setCopied] = useState(false);
  const [isGeneratingCaptions, setIsGeneratingCaptions] = useState(false);
  const [captions, setCaptions] = useState(null);
  const [isGettingPhotoGuide, setIsGettingPhotoGuide] = useState(false);
  const [photoGuide, setPhotoGuide] = useState(null);

  if (!isOpen || !activity) return null;

  const isHotel = activity.type === 'hotel';

  // 获取问路卡
  const handleGetDirectionCard = async () => {
    setIsGettingDirection(true);
    try {
      const result = await assistantsApi.getDirectionCard(
        destination,
        activity.title
      );
      setDirectionCard(result);
    } catch (error) {
      console.error('Direction card failed:', error);
    } finally {
      setIsGettingDirection(false);
    }
  };

  // 讲故事
  const handleTellStory = async () => {
    setIsTellingStory(true);
    try {
      const result = await assistantsApi.getStory(destination, activity.title);
      setStory(result.story);
    } catch (error) {
      console.error('Story generation failed:', error);
    } finally {
      setIsTellingStory(false);
    }
  };

  // 获取评价（模拟）
  const handleGetReviews = async () => {
    setIsGettingReviews(true);
    try {
      // 模拟评价数据（实际应该调用后端）
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setReviews({
        score: 4.8,
        total_reviews: 1240,
        pros: ['位置优越', '服务周到', '早餐丰富'],
        cons: ['房间稍小', '停车位紧张'],
        recent_reviews: [
          { user: '旅行者A', rating: 5, comment: '非常满意的入住体验！' },
          { user: '游客B', rating: 4, comment: '地理位置很好，出行方便' },
        ],
      });
    } catch (error) {
      console.error('Reviews fetch failed:', error);
    } finally {
      setIsGettingReviews(false);
    }
  };

  // 复制问路卡文本
  const handleCopy = (text) => {
    const textToCopy = text || directionCard?.local_text;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 生成发圈文案
  const handleGenerateCaptions = async () => {
    setIsGeneratingCaptions(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE || '/api/v1'}/assistants/social_captions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination,
          place_name: activity.title,
        }),
      });
      const result = await response.json();
      setCaptions(result);
    } catch (error) {
      console.error('Captions generation failed:', error);
    } finally {
      setIsGeneratingCaptions(false);
    }
  };

  // 摄影指导
  const handleGetPhotoGuide = async () => {
    setIsGettingPhotoGuide(true);
    try {
      const result = await assistantsApi.getPhotoGuide(destination, activity.title);
      setPhotoGuide(result);
    } catch (error) {
      console.error('Photo guide failed:', error);
    } finally {
      setIsGettingPhotoGuide(false);
    }
  };

  // 关闭并重置
  const handleClose = () => {
    setActiveTab('overview');
    setDirectionCard(null);
    setStory(null);
    setReviews(null);
    setCaptions(null);
    setPhotoGuide(null);
    closeDetailModal();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-[#1a1d2d] border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* 封面图 */}
        <div className="h-56 relative overflow-hidden group">
          <img
            src={
              // 优先使用 photos 数组（高德 API），其次使用 image，最后使用 Unsplash
              activity.photos?.[0] ||
              activity.image ||
              `https://source.unsplash.com/800x400/?${activity.type},travel,${encodeURIComponent(activity.title)}`
            }
            className="w-full h-full object-cover"
            alt={activity.title}
            onError={(e) => {
              // 图片加载失败时使用 Unsplash
              e.target.src = `https://source.unsplash.com/800x400/?${activity.type},travel`;
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#1a1d2d] via-transparent to-transparent" />

          {/* 酒店图片预览 */}
          {isHotel && activity.photos && activity.photos.length > 1 && (
            <div className="absolute bottom-4 right-4 flex gap-2">
              {activity.photos.slice(1, 4).map((photo, i) => (
                <div
                  key={i}
                  className="w-12 h-12 rounded-lg border-2 border-white/50 overflow-hidden bg-black/50 backdrop-blur cursor-pointer hover:border-white transition-all"
                >
                  <img
                    src={photo}
                    className="w-full h-full object-cover"
                    alt=""
                    onError={(e) => {
                      e.target.src = `https://source.unsplash.com/100x100/?hotel,interior,${i}`;
                    }}
                  />
                </div>
              ))}
              {activity.photos.length > 4 && (
                <div className="w-12 h-12 rounded-lg border-2 border-white/50 bg-black/60 backdrop-blur flex items-center justify-center text-xs text-white font-bold cursor-pointer">
                  +{activity.photos.length - 4}
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleClose}
            className="absolute top-4 right-4 bg-black/40 hover:bg-black/60 text-white p-2 rounded-full backdrop-blur-md transition-all"
          >
            <X size={20} />
          </button>
        </div>

        {/* 内容区 */}
        <div className="flex flex-col flex-1 overflow-hidden bg-[#1a1d2d]">
          {/* 标题区 */}
          <div className="px-6 pt-6 pb-2">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-white mb-1 flex items-center gap-2">
                  {activity.title}
                  {isHotel && (
                    <div className="flex text-yellow-400">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Star key={i} size={16} fill="currentColor" />
                      ))}
                    </div>
                  )}
                </h2>
                <div className="flex items-center gap-2 text-gray-400 text-sm mt-1">
                  <MapPin size={14} />
                  <span>{destination}市中心区域</span>
                  <button
                    onClick={handleGetDirectionCard}
                    disabled={isGettingDirection}
                    className="ml-2 flex items-center gap-1 text-xs bg-blue-600/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 hover:bg-blue-600/40 transition-colors disabled:opacity-50"
                  >
                    {isGettingDirection ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Car size={12} />
                    )}
                    打车/问路
                  </button>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-400">
                  {activity.time || activity.price || '--'}
                </div>
                {isHotel && (
                  <div className="text-xs text-gray-500">起/晚 (含税)</div>
                )}
              </div>
            </div>

            {/* 酒店 Tab 切换 */}
            {isHotel && (
              <div className="flex gap-6 mt-6 border-b border-white/10">
                {['overview', 'reviews', 'rooms'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`pb-3 text-sm font-medium transition-colors relative ${activeTab === tab
                      ? 'text-white'
                      : 'text-gray-500 hover:text-gray-300'
                      }`}
                  >
                    {tab === 'overview'
                      ? '概况 & 设施'
                      : tab === 'reviews'
                        ? '住客评价'
                        : '房型预订'}
                    {activeTab === tab && (
                      <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 rounded-t-full" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 滚动内容区 */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
            {/* 问路卡 */}
            {directionCard && (
              <div className="mb-6 bg-blue-600 rounded-xl p-6 text-white relative overflow-hidden shadow-lg animate-fadeIn">
                <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
                <div className="relative">
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-xs uppercase tracking-wider bg-white/20 px-2 py-1 rounded">
                      问路卡
                    </span>
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1 text-xs bg-white/20 hover:bg-white/30 px-2 py-1 rounded transition-colors"
                    >
                      {copied ? <Check size={12} /> : <Copy size={12} />}
                      {copied ? '已复制' : '复制'}
                    </button>
                  </div>
                  <div className="text-3xl font-bold mb-2">
                    {directionCard.local_text}
                  </div>
                  <div className="text-white/70 text-sm mb-1">
                    发音：{directionCard.pronunciation}
                  </div>
                  {directionCard.address && (
                    <div className="text-white/50 text-xs">
                      地址：{directionCard.address}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 概况 Tab */}
            {(activeTab === 'overview' || !isHotel) && (
              <div className="space-y-6">
                {/* 描述 */}
                <div>
                  <p className="text-gray-300 leading-relaxed">
                    {activity.desc || '暂无详细描述'}
                  </p>
                </div>

                {/* 详细信息 */}
                {activity.details && (
                  <div className="grid grid-cols-2 gap-4">
                    {activity.details.opening_hours && (
                      <div className="bg-white/5 rounded-xl p-4 flex items-center gap-3">
                        <Clock className="text-blue-400" size={20} />
                        <div>
                          <div className="text-xs text-gray-500">营业时间</div>
                          <div className="text-white font-medium">
                            {activity.details.opening_hours}
                          </div>
                        </div>
                      </div>
                    )}
                    {activity.details.ticket_price && (
                      <div className="bg-white/5 rounded-xl p-4 flex items-center gap-3">
                        <Ticket className="text-green-400" size={20} />
                        <div>
                          <div className="text-xs text-gray-500">门票价格</div>
                          <div className="text-white font-medium">
                            {activity.details.ticket_price}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 讲故事 */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="text-white font-semibold flex items-center gap-2">
                      <BookOpen size={18} className="text-purple-400" />
                      背后的故事
                    </h4>
                    {!story && (
                      <button
                        onClick={handleTellStory}
                        disabled={isTellingStory}
                        className="text-xs bg-purple-600/20 text-purple-400 px-3 py-1 rounded-full border border-purple-500/20 hover:bg-purple-600/40 transition-colors disabled:opacity-50"
                      >
                        {isTellingStory ? (
                          <span className="flex items-center gap-1">
                            <Loader2 size={12} className="animate-spin" />
                            生成中...
                          </span>
                        ) : (
                          '听故事'
                        )}
                      </button>
                    )}
                  </div>
                  {story ? (
                    <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {story}
                    </p>
                  ) : (
                    <p className="text-gray-500 text-sm">
                      点击"听故事"了解这里的历史典故...
                    </p>
                  )}
                </div>

                {/* 摄影指导 */}
                {!isHotel && (
                  <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="text-white font-semibold flex items-center gap-2">
                        <Camera size={18} className="text-pink-400" />
                        摄影指导
                      </h4>
                      {!photoGuide && (
                        <button
                          onClick={handleGetPhotoGuide}
                          disabled={isGettingPhotoGuide}
                          className="text-xs bg-pink-600/20 text-pink-400 px-3 py-1 rounded-full border border-pink-500/20 hover:bg-pink-600/40 transition-colors disabled:opacity-50"
                        >
                          {isGettingPhotoGuide ? (
                            <span className="flex items-center gap-1">
                              <Loader2 size={12} className="animate-spin" />
                              分析中...
                            </span>
                          ) : (
                            '获取建议'
                          )}
                        </button>
                      )}
                    </div>
                    {photoGuide ? (
                      <div className="bg-pink-900/20 border border-pink-500/20 rounded-xl p-4 animate-fadeIn flex gap-4">
                        <Camera size={24} className="text-pink-400 shrink-0 mt-1" />
                        <div>
                          <div className="text-sm font-bold text-white mb-1">最佳拍摄建议</div>
                          <div className="text-xs text-gray-300">⏰ {photoGuide.best_time}</div>
                          <div className="text-xs text-gray-300">📐 {photoGuide.best_angle}</div>
                          <div className="text-xs text-gray-400 mt-1 italic">{photoGuide.composition_tip}</div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-500 text-sm">
                        点击"获取建议"了解最佳拍摄时机和角度...
                      </p>
                    )}
                  </div>
                )}

                {/* 发圈文案 */}
                {!isHotel && (
                  <div className="mt-4">
                    {!captions ? (
                      <div className="flex justify-center">
                        <button
                          onClick={handleGenerateCaptions}
                          disabled={isGeneratingCaptions}
                          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white rounded-full font-medium transition-all hover:scale-105 disabled:opacity-50 text-sm"
                        >
                          {isGeneratingCaptions ? (
                            <>
                              <Loader2 size={16} className="animate-spin" />
                              正在生成...
                            </>
                          ) : (
                            <>
                              <Share2 size={16} />
                              ✨ 生成发圈文案
                            </>
                          )}
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-4 animate-fadeIn mt-6 pt-6 border-t border-white/10">
                        <h3 className="flex items-center gap-2 text-pink-400 font-bold text-sm uppercase tracking-wide">
                          <Share2 size={16} /> 朋友圈文案灵感
                        </h3>
                        <div className="grid grid-cols-1 gap-3">
                          {captions.styles?.map((style, i) => (
                            <div
                              key={i}
                              className="bg-white/5 border border-white/10 rounded-xl p-4 relative group hover:bg-white/10 transition-colors"
                            >
                              <div className="text-[10px] text-gray-500 mb-2 uppercase border border-white/10 rounded px-1.5 py-0.5 w-fit">
                                {style.name}
                              </div>
                              <p className="text-gray-200 text-sm leading-relaxed font-light">
                                {style.text}
                              </p>
                              <button
                                onClick={() => handleCopy(style.text)}
                                className="absolute top-3 right-3 p-1.5 text-gray-500 hover:text-white bg-black/20 hover:bg-blue-600 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                                title="复制文案"
                              >
                                <Copy size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 酒店设施 */}
                {isHotel && (
                  <div>
                    <h4 className="text-white font-semibold mb-3">酒店设施</h4>
                    <div className="grid grid-cols-4 gap-3">
                      {['wifi', 'gym', 'restaurant', 'parking'].map((facility) => {
                        const Icon = facilityIcons[facility] || Wifi;
                        return (
                          <div
                            key={facility}
                            className="bg-white/5 rounded-lg p-3 flex flex-col items-center gap-2"
                          >
                            <Icon size={20} className="text-blue-400" />
                            <span className="text-xs text-gray-400 capitalize">
                              {facility}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 评价 Tab */}
            {activeTab === 'reviews' && isHotel && (
              <div className="space-y-4">
                {!reviews ? (
                  <div className="text-center py-8">
                    <button
                      onClick={handleGetReviews}
                      disabled={isGettingReviews}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl transition-colors disabled:opacity-50"
                    >
                      {isGettingReviews ? (
                        <span className="flex items-center gap-2">
                          <Loader2 size={16} className="animate-spin" />
                          加载中...
                        </span>
                      ) : (
                        '加载评价'
                      )}
                    </button>
                  </div>
                ) : (
                  <>
                    {/* 评分概览 */}
                    <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-xl p-6 flex items-center gap-6">
                      <div className="text-center">
                        <div className="text-4xl font-bold text-white">
                          {reviews.score}
                        </div>
                        <div className="flex text-yellow-400 mt-1">
                          {[1, 2, 3, 4, 5].map((i) => (
                            <Star
                              key={i}
                              size={14}
                              fill={i <= Math.floor(reviews.score) ? 'currentColor' : 'none'}
                            />
                          ))}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {reviews.total_reviews} 条评价
                        </div>
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex gap-2 flex-wrap">
                          {reviews.pros.map((pro, i) => (
                            <span
                              key={i}
                              className="flex items-center gap-1 text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded"
                            >
                              <ThumbsUp size={10} /> {pro}
                            </span>
                          ))}
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          {reviews.cons.map((con, i) => (
                            <span
                              key={i}
                              className="flex items-center gap-1 text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded"
                            >
                              <ThumbsDown size={10} /> {con}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* 评价列表 */}
                    <div className="space-y-3">
                      {reviews.recent_reviews.map((review, i) => (
                        <div
                          key={i}
                          className="bg-white/5 rounded-xl p-4 border border-white/5"
                        >
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-white font-medium">
                              {review.user}
                            </span>
                            <div className="flex text-yellow-400">
                              {[1, 2, 3, 4, 5].map((j) => (
                                <Star
                                  key={j}
                                  size={12}
                                  fill={j <= review.rating ? 'currentColor' : 'none'}
                                />
                              ))}
                            </div>
                          </div>
                          <p className="text-gray-300 text-sm">
                            {review.comment}
                          </p>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 房型 Tab - 跳转 OTA 预订 */}
            {activeTab === 'rooms' && isHotel && (
              <div className="space-y-6">
                {/* 提示信息 */}
                <div className="bg-blue-900/20 border border-blue-500/20 rounded-xl p-4 text-center">
                  <p className="text-blue-300 text-sm mb-1">🏨 点击下方平台查看真实房型和价格</p>
                  <p className="text-gray-500 text-xs">跳转至第三方平台预订，享受更多优惠</p>
                </div>

                {/* OTA 跳转按钮 */}
                <div className="space-y-3">
                  {/* 携程 */}
                  <a
                    href={`https://hotels.ctrip.com/hotels/list?keyword=${encodeURIComponent(activity.title)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between bg-gradient-to-r from-blue-600/20 to-blue-500/10 border border-blue-500/30 rounded-xl p-4 hover:from-blue-600/30 hover:to-blue-500/20 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">携</div>
                      <div>
                        <div className="text-white font-semibold">携程旅行</div>
                        <div className="text-xs text-gray-400">国内领先 · 价格保障</div>
                      </div>
                    </div>
                    <div className="text-blue-400 group-hover:translate-x-1 transition-transform">→</div>
                  </a>

                  {/* 美团 */}
                  <a
                    href={`https://hotel.meituan.com/search/?keyword=${encodeURIComponent(activity.title)}&cityName=${encodeURIComponent(destination || '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between bg-gradient-to-r from-yellow-600/20 to-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 hover:from-yellow-600/30 hover:to-yellow-500/20 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-yellow-500 rounded-lg flex items-center justify-center text-white font-bold">美</div>
                      <div>
                        <div className="text-white font-semibold">美团酒店</div>
                        <div className="text-xs text-gray-400">本地生活 · 超值优惠</div>
                      </div>
                    </div>
                    <div className="text-yellow-400 group-hover:translate-x-1 transition-transform">→</div>
                  </a>

                  {/* 飞猪 */}
                  <a
                    href={`https://hotel.fliggy.com/hotel/searchresult/?searchText=${encodeURIComponent(activity.title)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between bg-gradient-to-r from-orange-600/20 to-orange-500/10 border border-orange-500/30 rounded-xl p-4 hover:from-orange-600/30 hover:to-orange-500/20 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold">飞</div>
                      <div>
                        <div className="text-white font-semibold">飞猪旅行</div>
                        <div className="text-xs text-gray-400">阿里出品 · 信用出行</div>
                      </div>
                    </div>
                    <div className="text-orange-400 group-hover:translate-x-1 transition-transform">→</div>
                  </a>
                </div>

                {/* 温馨提示 */}
                <p className="text-center text-xs text-gray-500">
                  💡 建议比较多个平台价格，选择最优惠的预订
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ActivityDetailModal;
