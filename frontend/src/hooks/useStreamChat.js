/**
 * 流式聊天 Hook
 * 
 * 处理 SSE 流式响应和消息状态管理
 * 使用 simulateStream 实现打字机效果
 */

import { useCallback, useRef } from 'react';
import { chatApi } from '../api/client';
import useTravelStore from '../store/useTravelStore';
import useAuthStore from '../store/useAuthStore';

const API_BASE = '/api/v1';

/**
 * 模拟打字机效果
 * @param {string} fullText - 完整文本
 * @param {function} onChunk - 每个块的回调
 * @param {function} onComplete - 完成回调
 * @returns {function} 取消函数
 */
const simulateStream = (fullText, onChunk, onComplete) => {
  const chunkSize = 3;
  const delay = 20;
  let currentIndex = 0;
  let cancelled = false;

  const interval = setInterval(() => {
    if (cancelled || currentIndex >= fullText.length) {
      clearInterval(interval);
      if (!cancelled && onComplete) onComplete();
      return;
    }

    const chunk = fullText.slice(currentIndex, currentIndex + chunkSize);
    onChunk(chunk);
    currentIndex += chunkSize;
  }, delay);

  return () => {
    cancelled = true;
    clearInterval(interval);
  };
};

/**
 * 检查并消耗配额
 */
async function checkAndConsumeQuota(token) {
  if (!token) return { success: false, message: '未登录' };

  try {
    const response = await fetch(`${API_BASE}/auth/consume-quota`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        message: data.detail || '配额检查失败',
        quota: data,
      };
    }

    return { success: true, quota: data };
  } catch (error) {
    // 配额 API 失败时允许继续（后端可能未配置）
    return { success: true };
  }
}

export function useStreamChat() {
  const {
    sessionId,
    setSessionId,
    addMessage,
    appendToLastMessage,
    updateLastMessage,
    setIsTyping,
    setDestination,
    setTripStatus,
    setWeather,
    setItinerary,
    setPois,
    setActiveTab,
    setMobileView,
    clearCache,
  } = useTravelStore();

  // 用于取消正在进行的流式输出
  const cancelStreamRef = useRef(null);

  /**
   * 从用户消息中提取目的地和天数
   * @param {string} message - 用户消息
   * @returns {Object|null} { destination, days } 或 null
   */
  const extractTripParams = (message) => {
    // 常见城市列表
    const cities = [
      '北京', '上海', '广州', '深圳', '杭州', '成都', '重庆', '西安', '南京', '苏州',
      '三亚', '厦门', '青岛', '大理', '丽江', '香格里拉', '西双版纳', '桂林', '张家界',
      '黄山', '九寨沟', '长沙', '武汉', '天津', '哈尔滨', '沈阳', '昆明', '贵阳', '拉萨'
    ];

    // 提取目的地
    let destination = null;
    for (const city of cities) {
      if (message.includes(city)) {
        destination = city;
        break;
      }
    }

    // 提取天数 - 匹配 "X天" 或 "X日"
    let days = null;
    const daysMatch = message.match(/(\d+)\s*[天日]/);
    if (daysMatch) {
      days = parseInt(daysMatch[1], 10);
    }

    // 如果没有天数，尝试匹配 "X晚" 并推算
    if (!days) {
      const nightsMatch = message.match(/(\d+)\s*晚/);
      if (nightsMatch) {
        days = parseInt(nightsMatch[1], 10) + 1; // N晚通常对应N+1天
      }
    }

    if (destination && days) {
      return { destination, days };
    }
    return null;
  };

  /**
   * 检测是否是重新生成请求
   * @param {string} message - 用户消息
   * @returns {boolean}
   */
  const isRegenerateRequest = (message) => {
    const regenerateKeywords = [
      '重新生成', '再生成', '再来一次', '换一个版本', '重新规划', '换个方案',
      '重新做', '不满意', '换一版', '再做一个', '重来', '重做'
    ];
    return regenerateKeywords.some(kw => message.includes(kw));
  };

  /**
   * 加载匹配的历史行程到界面
   * @param {Object} tripData - 匹配的行程数据
   */
  const loadMatchedTrip = (tripData) => {
    // 更新目的地
    if (tripData.destination) {
      setDestination(tripData.destination);
    }

    // 更新行程
    // itinerary_data 可能是直接的数组，或者包含 .days 属性
    const itineraryDays = Array.isArray(tripData.itinerary_data)
      ? tripData.itinerary_data
      : tripData.itinerary_data?.days || tripData.itinerary_data;

    if (itineraryDays && itineraryDays.length > 0) {
      setItinerary(itineraryDays);
      clearCache();
      setActiveTab('itinerary');

      // 移动端自动切换
      if (window.innerWidth < 1024) {
        setMobileView('dashboard');
      }
    }

    // 更新天气
    if (tripData.weather_snapshot) {
      setWeather(tripData.weather_snapshot);
    }

    // 更新 POI
    if (tripData.pois_snapshot && tripData.pois_snapshot.length > 0) {
      setPois(tripData.pois_snapshot);
    }

    // 更新会话 ID（如果有对话历史）
    if (tripData.conversation?.session_id) {
      setSessionId(tripData.conversation.session_id);
    }

    setTripStatus('Created');
  };

  /**
   * 发送消息并处理流式响应
   * 支持重复检测和重新生成不同版本
   */
  const sendMessage = useCallback(async (message) => {
    if (!message.trim()) return;

    // 取消之前的流式输出
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }

    // 获取当前 token 和状态
    const authState = useAuthStore.getState();
    const token = authState.accessToken || authState.guestToken;
    const travelState = useTravelStore.getState();
    const currentItinerary = travelState.itinerary;

    // ========== 重复检测和重新生成逻辑 ==========

    // 1. 检测是否是重新生成请求
    const isRegenerate = isRegenerateRequest(message);

    // 2. 提取目的地和天数
    const tripParams = extractTripParams(message);

    // 3. 如果不是重新生成请求，且有目的地+天数，检查是否有匹配的历史行程
    if (!isRegenerate && tripParams && token) {
      try {
        const { tripsApi } = await import('../api/client');
        const matchResult = await tripsApi.match(token, tripParams.destination, tripParams.days);

        if (matchResult.matched && matchResult.trip) {
          // 找到匹配的历史行程，直接加载
          addMessage({ role: 'user', content: message, isStreaming: false });

          // 显示友好提示
          const loadingMessage = `✨ 找到您之前规划的${tripParams.destination}${tripParams.days}天行程！正在为您加载...`;
          addMessage({ role: 'ai', content: '', isStreaming: true });

          // 打字机效果显示提示
          await new Promise((resolve) => {
            cancelStreamRef.current = simulateStream(
              loadingMessage,
              (chunk) => appendToLastMessage(chunk),
              () => {
                cancelStreamRef.current = null;
                resolve();
              }
            );
          });

          updateLastMessage({ isStreaming: false });

          // 加载历史行程数据
          loadMatchedTrip(matchResult.trip);

          // 完成
          setIsTyping(false);
          return;
        }
      } catch (error) {
        // 匹配 API 失败时继续正常流程
        console.warn('Trip match API failed, continuing with normal flow:', error);
      }
    }

    // ========== 正常流程：检查配额并发送请求 ==========

    // 检查并消耗配额
    const quotaResult = await checkAndConsumeQuota(token);
    if (!quotaResult.success) {
      // 配额不足，显示友好提示
      const isGuest = authState.isGuest;
      const tipMessage = isGuest
        ? '😊 今日免费体验次数已用完，请登录获取更多次数~'
        : '💡 今日使用次数已用完，明天再来或使用激活码增加次数';

      addMessage({ role: 'user', content: message, isStreaming: false });
      addMessage({
        role: 'ai',
        content: tipMessage,
        isStreaming: false
      });
      return;
    }

    // 添加用户消息
    addMessage({ role: 'user', content: message, isStreaming: false });
    setIsTyping(true);

    // 添加空的 AI 消息（用于流式填充）
    addMessage({ role: 'ai', content: '', isStreaming: true });

    try {
      let finalData = null;
      let fullContent = '';

      // 确定是否是重新生成以及上一版行程
      const shouldRegenerate = isRegenerate && currentItinerary && currentItinerary.length > 0;
      const previousItinerary = shouldRegenerate ? currentItinerary : null;

      // 使用流式 API（传递 token、regenerate 标志和上一版行程）
      for await (const event of chatApi.stream(
        message,
        sessionId,
        token,
        shouldRegenerate,
        previousItinerary
      )) {
        if (event.type === 'start') {
          // 流开始
          if (event.session_id) {
            setSessionId(event.session_id);
          }
        } else if (event.type === 'token') {
          // 收到 token，保存完整内容用于打字机效果
          fullContent = event.content || '';
        } else if (event.type === 'end') {
          // 流结束，收到完整数据
          finalData = event;
        } else if (event.error) {
          // 错误
          updateLastMessage({
            content: '抱歉，出了点问题，请重试。',
            isStreaming: false,
          });
          setIsTyping(false);
          return;
        }
      }

      // 如果有内容，使用打字机效果显示
      if (fullContent) {
        await new Promise((resolve) => {
          cancelStreamRef.current = simulateStream(
            fullContent,
            (chunk) => {
              appendToLastMessage(chunk);
            },
            () => {
              cancelStreamRef.current = null;
              resolve();
            }
          );
        });
      }

      // 处理最终数据
      if (finalData) {
        updateLastMessage({ isStreaming: false });

        // 更新行程数据
        if (finalData.destination_detected) {
          setDestination(finalData.destination_detected);
        }
        if (finalData.status_update) {
          setTripStatus(finalData.status_update);
        }
        if (finalData.weather_forecast) {
          setWeather(finalData.weather_forecast);
        }

        // 更新行程
        if (finalData.itinerary && finalData.itinerary.length > 0) {
          setItinerary(finalData.itinerary);
          clearCache(); // 清除旧的缓存
          setActiveTab('itinerary');

          // 移动端自动切换到 dashboard
          if (window.innerWidth < 1024) {
            setMobileView('dashboard');
          }
        }

        // 更新 POI
        if (finalData.pois && finalData.pois.length > 0) {
          setPois(finalData.pois);
        }
      }
    } catch (error) {
      updateLastMessage({
        content: '网络开小差了，请重试一下。',
        isStreaming: false,
      });
    } finally {
      setIsTyping(false);
    }
  }, [sessionId]);

  /**
   * 非流式发送（备用）
   */
  const sendMessageSync = useCallback(async (message) => {
    if (!message.trim()) return;

    addMessage({ role: 'user', content: message, isStreaming: false });
    setIsTyping(true);

    try {
      const response = await chatApi.send(message, sessionId);

      if (response.session_id) {
        setSessionId(response.session_id);
      }

      addMessage({
        role: 'ai',
        content: response.response,
        isStreaming: false,
      });

      // 处理元数据
      if (response.metadata?.destination_detected) {
        setDestination(response.metadata.destination_detected);
      }
    } catch (error) {
      addMessage({
        role: 'ai',
        content: '抱歉，出了点问题，请重试。',
        isStreaming: false,
      });
    } finally {
      setIsTyping(false);
    }
  }, [sessionId]);

  return {
    sendMessage,
    sendMessageSync,
  };
}

export default useStreamChat;

