/**
 * TravelMind 全局状态管理
 * 
 * 使用 Zustand 管理应用状态
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

/**
 * 旅行状态 Store
 */
export const useTravelStore = create(
  devtools(
    persist(
      (set, get) => ({
        // ============================================================
        // 基础状态
        // ============================================================

        // 目的地
        destination: '未知目的地',
        setDestination: (destination) => set({ destination }),

        // 旅行状态
        tripStatus: '', // Planning | Created
        setTripStatus: (status) => set({ tripStatus: status }),

        // 天气信息
        weather: { temp: '--', condition: '未知' },
        setWeather: (weather) => set({ weather }),

        // 旅行天数
        tripDays: 3,
        setTripDays: (days) => set({ tripDays: days }),

        // ============================================================
        // 聊天状态
        // ============================================================

        messages: [
          {
            role: 'ai',
            content: '你好！我是 TravelMind，你的智能行程管家。\n\n请告诉我你想去哪里，玩几天？\n例如："帮我规划一个北京4天3晚的亲子游，想去环球影城"',
            isStreaming: false,
          },
        ],
        sessionId: null,
        isTyping: false,

        addMessage: (message) => set((state) => ({
          messages: [...state.messages, message],
        })),

        updateLastMessage: (updates) => set((state) => {
          const messages = [...state.messages];
          const lastIndex = messages.length - 1;
          if (lastIndex >= 0) {
            messages[lastIndex] = { ...messages[lastIndex], ...updates };
          }
          return { messages };
        }),

        appendToLastMessage: (text) => set((state) => {
          const messages = [...state.messages];
          const lastIndex = messages.length - 1;
          if (lastIndex >= 0 && messages[lastIndex].role === 'ai') {
            messages[lastIndex] = {
              ...messages[lastIndex],
              content: messages[lastIndex].content + text,
            };
          }
          return { messages };
        }),

        setSessionId: (sessionId) => set({ sessionId }),
        setIsTyping: (isTyping) => set({ isTyping }),

        clearChat: () => set({
          messages: [
            {
              role: 'ai',
              content: '你好！我是 TravelMind，你的智能行程管家。\n\n请告诉我你想去哪里？',
              isStreaming: false,
            },
          ],
          sessionId: null,
        }),

        // ============================================================
        // 行程数据
        // ============================================================

        itinerary: [],
        setItinerary: (itinerary) => set({ itinerary }),

        updateDayTips: (dayIndex, tips) => set((state) => {
          const itinerary = [...state.itinerary];
          if (itinerary[dayIndex]) {
            itinerary[dayIndex] = { ...itinerary[dayIndex], cachedTips: tips };
          }
          return { itinerary };
        }),

        // 打卡功能
        toggleCheckIn: (dayIdx, actIdx) => set((state) => {
          const itinerary = [...state.itinerary];
          if (itinerary[dayIdx]?.activities?.[actIdx]) {
            itinerary[dayIdx].activities[actIdx] = {
              ...itinerary[dayIdx].activities[actIdx],
              checked: !itinerary[dayIdx].activities[actIdx].checked,
            };
          }
          return { itinerary };
        }),

        // POI 数据（酒店推荐等）
        pois: [],
        setPois: (pois) => set({ pois }),

        // 预算数据（用于侧边栏显示）
        budget: null,
        setBudget: (budget) => set({ budget }),

        // ============================================================
        // AI 功能缓存
        // ============================================================

        // 缓存各种 AI 功能的结果，避免重复请求
        cache: {
          budget: null,
          packing: null,
          playlist: null,
          emergency: null,
          culture: null,
          souvenirs: null,
          photoChallenges: null,
        },

        setCache: (key, data) => set((state) => ({
          cache: { ...state.cache, [key]: data },
        })),

        getCache: (key) => get().cache[key],

        clearCache: () => set({
          cache: {
            budget: null,
            packing: null,
            playlist: null,
            emergency: null,
            culture: null,
            souvenirs: null,
            photoChallenges: null,
          },
          budget: null, // 同时清除侧边栏预算
        }),

        // ============================================================
        // UI 状态
        // ============================================================

        // 当前激活的 Tab
        activeTab: 'itinerary', // itinerary | pois | map
        setActiveTab: (tab) => set({ activeTab: tab }),

        // 移动端视图
        mobileView: 'chat', // chat | dashboard
        setMobileView: (view) => set({ mobileView: view }),

        // Modal 状态
        modal: {
          isOpen: false,
          type: null, // budget | packing | playlist | emergency | culture | souvenirs | photo_challenge | tips | diary
          title: '',
          content: null,
          isLoading: false,
          context: null, // 额外上下文，如当前日期
        },

        openModal: (type, title, content = null, context = null) => set({
          modal: {
            isOpen: true,
            type,
            title,
            content,
            isLoading: !content,
            context,
          },
        }),

        setModalContent: (content) => set((state) => ({
          modal: { ...state.modal, content, isLoading: false },
        })),

        setModalLoading: (isLoading) => set((state) => ({
          modal: { ...state.modal, isLoading },
        })),

        closeModal: () => set((state) => ({
          modal: { ...state.modal, isOpen: false },
        })),

        // 活动详情 Modal
        detailModal: {
          isOpen: false,
          activity: null,
          path: null, // { type: 'itinerary' | 'poi', dayIdx?, actIdx?, index? }
        },

        openDetailModal: (activity, path) => set({
          detailModal: { isOpen: true, activity, path },
        }),

        updateDetailActivity: (updates) => set((state) => ({
          detailModal: {
            ...state.detailModal,
            activity: { ...state.detailModal.activity, ...updates },
          },
        })),

        closeDetailModal: () => set({
          detailModal: { isOpen: false, activity: null, path: null },
        }),

        // ============================================================
        // 重置
        // ============================================================

        resetTrip: () => set({
          destination: '',
          tripStatus: '',
          weather: null,
          itinerary: [],
          pois: [],
          budget: null, // 清除预算
          cache: {
            budget: null,
            packing: null,
            playlist: null,
            emergency: null,
            culture: null,
            souvenirs: null,
            photoChallenges: null,
          },
        }),
      }),
      {
        name: 'travelmind-storage-v2',
        partialize: (state) => ({
          // 只持久化部分状态
          destination: state.destination,
          sessionId: state.sessionId,
        }),
      }
    ),
    { name: 'TravelMind' }
  )
);

export default useTravelStore;
