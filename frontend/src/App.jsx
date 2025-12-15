/**
 * TravelMind 主应用组件
 * 
 * 整合聊天、仪表盘、地图等所有功能
 */

import React, { useRef, useEffect, useState } from 'react';
import {
  Send,
  Calendar,
  Hotel,
  Map as MapIcon,
  CloudSun,
  Sparkles,
  Menu,
  MessageSquare,
  Layout,
  Banknote,
  Backpack,
  Music,
  Siren,
  Globe,
  ShoppingBag,
  Aperture,
  Navigation,
  Star,
  Image,
  BrainCircuit,
  TrendingUp,
  History,
  Plus,
} from 'lucide-react';

import useTravelStore from './store/useTravelStore';
import useAuthStore from './store/useAuthStore';
import { useStreamChat, useAiFeature, useTripRestore } from './hooks';
import { ChatMessage } from './components/chat/ChatMessage';
import { ItineraryTimeline } from './components/dashboard/ItineraryTimeline';
import { GaodeMap } from './components/map/GaodeMap';
import { AiModal } from './components/modals/AiModal';
import { ActivityDetailModal } from './components/modals/ActivityDetailModal';
import { SmartSidebar } from './components/sidebar';
import { UserButton, LoginModal } from './components/auth';
import { TripHistoryDrawer } from './components/history';

function App() {
  const [input, setInput] = useState('');
  const [showSidebarDrawer, setShowSidebarDrawer] = useState(false);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const messagesEndRef = useRef(null);

  // 全局状态
  const {
    destination,
    tripStatus,
    weather,
    messages,
    isTyping,
    activeTab,
    setActiveTab,
    mobileView,
    setMobileView,
    itinerary,
    pois,
    openDetailModal,
  } = useTravelStore();

  // Hooks
  const { sendMessage } = useStreamChat();
  const {
    estimateBudget,
    generatePacking,
    generatePlaylist,
    generateEmergency,
    generateCulture,
    generateSouvenirs,
    generatePhotoChallenges,
    getDayTips,
    generateDiary,
    generatePoster,
  } = useAiFeature();

  // 刷新后从后端恢复行程
  useTripRestore();

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages, isTyping]);

  // 认证状态
  const accessToken = useAuthStore((state) => state.accessToken);
  const guestToken = useAuthStore((state) => state.guestToken);
  const isAuthenticated = !!accessToken || !!guestToken;

  // 发送消息（需要先登录）
  const handleSend = () => {
    if (!input.trim()) return;

    // 未认证时弹出登录框
    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }

    sendMessage(input);
    setInput('');
  };

  // 点击行程活动
  const handleActivityClick = (dayIdx, actIdx, activity) => {
    openDetailModal(activity, { type: 'itinerary', dayIdx, actIdx });
  };

  // 点击 POI
  const handlePoiClick = (index, poi) => {
    const activity = {
      ...poi,
      title: poi.name,
      desc: poi.desc || `评分: ${poi.rating} | 标签: ${poi.tags?.join(', ')}`,
      time: poi.price || '价格待定',
      type: 'hotel',
    };
    openDetailModal(activity, { type: 'poi', index });
  };

  const hasItinerary = itinerary.length > 0;

  return (
    <div className="flex h-screen w-full bg-[#0f111a] text-gray-200 font-sans overflow-hidden">
      {/* Modals */}
      <AiModal />
      <ActivityDetailModal />

      {/* 历史行程抽屉 */}
      <TripHistoryDrawer
        isOpen={showHistoryDrawer}
        onClose={() => setShowHistoryDrawer(false)}
        onTripLoaded={() => console.log('[App] Trip loaded from history')}
      />

      {/* 登录弹窗（发送消息时触发） */}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
      />

      {/* 移动端底部导航 */}
      <div className="fixed bottom-0 left-0 right-0 lg:hidden z-40 bg-[#0f111a]/95 backdrop-blur-lg border-t border-white/5 px-4 py-2 flex justify-around items-center safe-area-bottom">
        <button onClick={() => setMobileView('chat')} className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${mobileView === 'chat' ? 'text-blue-400' : 'text-gray-500'}`}>
          <MessageSquare size={20} />
          <span className="text-[10px]">对话</span>
        </button>
        <button onClick={() => setMobileView('dashboard')} className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${mobileView === 'dashboard' ? 'text-blue-400' : 'text-gray-500'}`}>
          <Layout size={20} />
          <span className="text-[10px]">行程</span>
        </button>
        <button onClick={() => setMobileView('sidebar')} className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-all ${mobileView === 'sidebar' ? 'text-blue-400' : 'text-gray-500'}`}>
          <BrainCircuit size={20} />
          <span className="text-[10px]">智囊</span>
        </button>
      </div>

      {/* Sidebar Overlay for LG/Mobile screens (Drawer) */}
      {(showSidebarDrawer || (mobileView === 'sidebar')) && (
        <div className={`fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm ${mobileView === 'sidebar' ? 'flex' : 'hidden lg:flex xl:hidden'}`} onClick={() => { setShowSidebarDrawer(false); if (mobileView === 'sidebar') setMobileView('dashboard'); }}>
          <div className={`absolute right-0 top-0 h-full bg-[#0f111a] border-l border-white/10 shadow-2xl p-4 overflow-y-auto transition-all duration-300 ${mobileView === 'sidebar' ? 'w-full' : 'w-80'}`} onClick={e => e.stopPropagation()}>
            <SmartSidebar
              destination={destination}
              itinerary={itinerary}
              isDrawer={true}
              isMobile={mobileView === 'sidebar'}
              onClose={() => { setShowSidebarDrawer(false); if (mobileView === 'sidebar') setMobileView('dashboard'); }}
            />
          </div>
        </div>
      )}

      {/* 左侧聊天区 */}
      <div className={`${mobileView === 'chat' ? 'flex' : 'hidden lg:flex'} w-full lg:w-[280px] xl:w-[320px] 2xl:w-[25%] flex-col border-r border-white/5 bg-gradient-to-b from-[#12141f] to-[#0f111a] relative z-20 flex-shrink-0 transition-all duration-300`}>
        {/* 聊天头部 */}
        <div className="h-16 border-b border-white/5 flex items-center justify-between px-4 lg:px-6 bg-white/2 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <img src="/favicon.png" alt="TravelMind" className="w-10 h-10 rounded-xl shadow-lg" />
            <div>
              <h1 className="font-bold text-white text-sm lg:text-base">TravelMind</h1>
              <p className="text-[10px] lg:text-xs text-gray-500">AI 智能旅行管家</p>
            </div>
          </div>

          {/* 右侧操作按钮组 */}
          <div className="flex items-center gap-2">
            {/* 历史按钮 */}
            <button
              onClick={() => setShowHistoryDrawer(true)}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              title="历史行程"
            >
              <History size={18} />
            </button>
            {/* 新建按钮 */}
            <button
              onClick={() => {
                useTravelStore.getState().resetTrip();
                useTravelStore.getState().clearChat();
              }}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              title="新建行程"
            >
              <Plus size={18} />
            </button>
            {/* 登录按钮 */}
            <UserButton />
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
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
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

      {/* 中间仪表盘 (自适应宽度) */}
      <div className={`${mobileView === 'dashboard' ? 'flex' : 'hidden lg:flex'} flex-1 flex-col relative z-10 bg-gradient-to-br from-[#131620] to-[#0b0c12] min-w-0 pb-20 lg:pb-0 w-full`}>
        {/* 仪表盘头部 */}
        <div className="h-16 border-b border-white/5 flex items-center justify-between px-4 lg:px-8 bg-white/2">
          <div className="flex items-center gap-3 lg:gap-4 overflow-hidden">
            <h2 className="text-white font-semibold whitespace-nowrap">
              {destination ? `${destination} 之旅` : "TravelMind"}
            </h2>
            {tripStatus && (
              <span
                className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${tripStatus === 'Created'
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20'
                  : 'bg-blue-500/20 text-blue-400 border-blue-500/20'
                  }`}
              >
                {tripStatus}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 lg:gap-4">
            {/* AI 功能按钮 */}
            {hasItinerary && (
              <>
                {/* Desktop */}
                <div className="hidden xl:flex items-center gap-2">
                  <FeatureButton icon={Banknote} label="预算" color="emerald" onClick={() => estimateBudget()} />
                  <FeatureButton icon={Backpack} label="行李" color="blue" onClick={() => generatePacking()} />
                  <FeatureButton icon={Music} label="歌单" color="violet" onClick={() => generatePlaylist()} />
                  <FeatureButton icon={Siren} label="求助" color="red" onClick={() => generateEmergency()} />
                  <FeatureButton icon={Globe} label="文化" color="cyan" onClick={() => generateCulture()} />
                  <FeatureButton icon={ShoppingBag} label="好物" color="pink" onClick={() => generateSouvenirs()} />
                  <FeatureButton icon={Aperture} label="挑战" color="indigo" onClick={() => generatePhotoChallenges()} />
                  <FeatureButton icon={Image} label="海报" color="purple" onClick={() => generatePoster()} />
                </div>

                {/* Mobile */}
                <div className="xl:hidden flex items-center gap-2">
                  <IconButton icon={Image} color="purple" onClick={() => generatePoster()} />
                  <IconButton icon={Aperture} color="indigo" onClick={() => generatePhotoChallenges()} />
                  <IconButton icon={ShoppingBag} color="pink" onClick={() => generateSouvenirs()} />
                  <IconButton icon={Globe} color="cyan" onClick={() => generateCulture()} />
                  <IconButton icon={Music} color="violet" onClick={() => generatePlaylist()} />
                  <IconButton icon={Siren} color="red" onClick={() => generateEmergency()} />
                  <IconButton icon={Banknote} color="emerald" onClick={() => estimateBudget()} />
                  <IconButton icon={Backpack} color="blue" onClick={() => generatePacking()} />
                </div>
              </>
            )}

            {/* 天气 */}
            <div className="h-6 w-[1px] bg-white/10 mx-1 lg:mx-2 hidden sm:block" />
            {weather && (
              <div className="flex items-center gap-2 lg:gap-3 bg-white/5 px-3 py-1.5 rounded-full border border-white/10 backdrop-blur-md">
                <CloudSun
                  size={18}
                  className={weather.condition?.includes('雨') ? 'text-gray-400' : 'text-yellow-400'}
                />
                <div>
                  <div className="text-xs lg:text-sm font-bold text-white">{weather.temp}</div>
                  <div className="text-[10px] text-gray-400 hidden sm:block">
                    {destination}, {weather.condition}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Tab 切换 */}
        <div className="px-4 lg:px-8 pt-4 lg:pt-6 pb-2 overflow-x-auto no-scrollbar">
          <div className="flex gap-1 bg-white/5 p-1 rounded-xl w-fit border border-white/5 mx-auto lg:mx-0">
            {[
              { id: 'itinerary', icon: Calendar, label: '行程规划' },
              { id: 'pois', icon: Hotel, label: '推荐住宿' },
              { id: 'map', icon: MapIcon, label: '地图模式' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 lg:px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
              >
                <tab.icon size={16} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar">
          {/* 行程 Tab */}
          {activeTab === 'itinerary' && (
            <div className="w-full h-full mx-auto lg:mx-0">
              {!hasItinerary ? (
                <div className="flex flex-col items-center justify-center h-64 text-gray-500 border-2 border-dashed border-white/10 rounded-2xl">
                  <Sparkles size={32} className="mb-3 opacity-30" />
                  <p className="text-sm">告诉我你想去哪，我来为你规划</p>
                </div>
              ) : (
                <ItineraryTimeline
                  days={itinerary}
                  onGetTips={getDayTips}
                  onActivityClick={handleActivityClick}
                  onGetDiary={generateDiary}
                />
              )}
            </div>
          )}

          {/* POI Tab */}
          {activeTab === 'pois' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
              {pois.length > 0 ? (
                pois.map((poi, idx) => {
                  // 判断是否为真正的酒店
                  const poiType = (poi.type || '').toLowerCase();
                  const poiTags = (poi.tags || []).join(' ').toLowerCase();
                  const isHotel = poiType.includes('酒店') || poiType.includes('宾馆') ||
                    poiTags.includes('酒店') || poiTags.includes('住宿');
                  const isRestaurant = poiType.includes('餐') || poiType.includes('饭店') ||
                    poiTags.includes('餐饮') || poiTags.includes('美食');

                  // 跳转函数
                  const openExternal = (platform) => {
                    const query = encodeURIComponent(`${poi.name} ${destination}`);
                    let url = '';
                    if (platform === 'amap') url = `https://m.amap.com/search/mapview/keywords=${query}`;
                    if (platform === 'douyin') url = `https://www.douyin.com/search/${query}`;
                    if (platform === 'xiaohongshu') url = `https://www.xiaohongshu.com/search_result?keyword=${query}`;
                    if (platform === 'ctrip') url = `https://hotels.ctrip.com/hotels/list?countryId=1&city=${destination}&keyword=${encodeURIComponent(poi.name)}`;
                    if (platform === 'meituan') url = `https://i.meituan.com/awp/h5/hotel/search.html?q=${query}`;
                    window.open(url, '_blank');
                  };

                  return (
                    <div
                      key={idx}
                      className="group relative overflow-hidden rounded-2xl bg-gray-800 border border-white/10 shadow-xl hover:shadow-2xl hover:shadow-blue-500/10 transition-all duration-300 flex flex-col"
                    >
                      <div className="h-32 bg-gray-700 relative overflow-hidden">
                        <img
                          src={
                            poi.photos?.[0] ||
                            poi.image ||
                            `https://source.unsplash.com/600x400/?hotel,${encodeURIComponent(poi.name || 'travel')}`
                          }
                          onError={(e) => {
                            e.target.src =
                              'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=600&q=80';
                          }}
                          alt={poi.name}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                        />
                        <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm px-2 py-1 rounded-lg flex items-center gap-1 text-xs font-bold text-yellow-400">
                          <Star size={12} fill="currentColor" /> {poi.rating || '4.5'}
                        </div>
                        {/* 类型标签 */}
                        {isRestaurant && (
                          <div className="absolute top-2 left-2 bg-orange-500/80 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] font-bold text-white">
                            餐饮
                          </div>
                        )}
                      </div>
                      <div className="p-4 flex-1 flex flex-col">
                        <h3 className="font-bold text-white truncate">{poi.name}</h3>
                        <div className="flex items-center justify-between mt-2 mb-3">
                          <span className="text-blue-400 font-mono font-bold">
                            {poi.price || '暂无报价'}
                          </span>
                          <div className="flex gap-1 flex-wrap justify-end">
                            {poi.tags?.slice(0, 2).map((tag, i) => (
                              <span
                                key={i}
                                className="text-[10px] bg-white/10 text-gray-300 px-1.5 py-0.5 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* 根据类型显示不同的跳转按钮 */}
                        {isHotel && !isRestaurant ? (
                          <div className="flex gap-2 mt-auto">
                            <button
                              onClick={() => openExternal('ctrip')}
                              className="flex-1 bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white py-2 rounded-lg text-[10px] font-medium transition-colors border border-blue-500/30"
                            >
                              携程
                            </button>
                            <button
                              onClick={() => openExternal('meituan')}
                              className="flex-1 bg-yellow-600/20 hover:bg-yellow-600 text-yellow-400 hover:text-white py-2 rounded-lg text-[10px] font-medium transition-colors border border-yellow-500/30"
                            >
                              美团
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-2 mt-auto">
                            <button
                              onClick={() => openExternal('amap')}
                              className="flex-1 bg-green-600/20 hover:bg-green-600 text-green-400 hover:text-white py-2 rounded-lg text-[10px] font-medium transition-colors border border-green-500/30"
                            >
                              高德
                            </button>
                            <button
                              onClick={() => openExternal('douyin')}
                              className="flex-1 bg-pink-600/20 hover:bg-pink-600 text-pink-400 hover:text-white py-2 rounded-lg text-[10px] font-medium transition-colors border border-pink-500/30"
                            >
                              抖音
                            </button>
                            <button
                              onClick={() => openExternal('xiaohongshu')}
                              className="flex-1 bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white py-2 rounded-lg text-[10px] font-medium transition-colors border border-red-500/30"
                            >
                              小红书
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="col-span-3 text-center text-gray-500 py-10">
                  <Hotel size={48} className="mx-auto mb-4 opacity-20" />
                  <p>暂无推荐，请先规划行程</p>
                </div>
              )}
            </div>
          )}

          {/* 地图 Tab */}
          {activeTab === 'map' && <GaodeMap />}
        </div>
      </div>



      {/* 右侧侧边栏 - XL显示完整，LG显示折叠条 */}

      {/* 1. XL Screen: Full Sidebar */}
      <div className="hidden xl:flex w-[320px] 2xl:w-[15%] flex-col border-l border-white/5 relative z-10 bg-[#0f111a]/80 backdrop-blur-sm flex-shrink-0">
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          <SmartSidebar itinerary={itinerary} destination={destination} />
        </div>
      </div>

      {/* 2. LG Screen: Collapsed Toolbar */}
      <div className="hidden lg:flex xl:hidden w-12 flex-col items-center py-4 border-l border-white/5 bg-[#0f111a]">
        <div className="space-y-4">
          <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white transition-colors" title="智囊助手">
            <BrainCircuit size={20} />
          </button>
          <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white transition-colors" title="地图">
            <MapIcon size={20} />
          </button>
          <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white transition-colors" title="天气">
            <CloudSun size={20} />
          </button>
          <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white transition-colors" title="预算">
            <TrendingUp size={20} />
          </button>
        </div>
      </div>
    </div >
  );
}

// 功能按钮组件
function FeatureButton({ icon: Icon, label, color, onClick }) {
  const colorClasses = {
    emerald: 'from-emerald-500/20 to-teal-500/20 hover:from-emerald-500/30 hover:to-teal-500/30 border-emerald-500/30 text-emerald-400',
    blue: 'from-blue-500/20 to-purple-500/20 hover:from-blue-500/30 hover:to-purple-500/30 border-blue-500/30 text-blue-400',
    violet: 'from-violet-500/20 to-fuchsia-500/20 hover:from-violet-500/30 hover:to-fuchsia-500/30 border-violet-500/30 text-violet-400',
    red: 'from-red-500/20 to-orange-500/20 hover:from-red-500/30 hover:to-orange-500/30 border-red-500/30 text-red-400',
    cyan: 'from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border-cyan-500/30 text-cyan-400',
    pink: 'from-pink-500/20 to-rose-500/20 hover:from-pink-500/30 hover:to-rose-500/30 border-pink-500/30 text-pink-400',
    indigo: 'from-indigo-500/20 to-purple-500/20 hover:from-indigo-500/30 hover:to-purple-500/30 border-indigo-500/30 text-indigo-400',
  };

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r ${colorClasses[color]} border rounded-full text-xs lg:text-sm font-medium transition-all hover:scale-105 whitespace-nowrap`}
    >
      <Icon size={14} className="lg:w-4 lg:h-4" />
      <span>{label}</span>
    </button>
  );
}

// 图标按钮组件 (移动端)
function IconButton({ icon: Icon, color, onClick }) {
  const colorClasses = {
    emerald: 'text-emerald-400',
    blue: 'text-blue-400',
    violet: 'text-violet-400',
    red: 'text-red-400',
    cyan: 'text-cyan-400',
    pink: 'text-pink-400',
    indigo: 'text-indigo-400',
  };

  return (
    <button
      onClick={onClick}
      className={`p-2 bg-white/5 hover:bg-white/10 rounded-full ${colorClasses[color]} border border-white/5`}
    >
      <Icon size={16} />
    </button>
  );
}

export default App;
