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
   * 发送消息并处理流式响应
   */
  const sendMessage = useCallback(async (message) => {
    if (!message.trim()) return;

    // 取消之前的流式输出
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }

    // 获取当前 token
    const authState = useAuthStore.getState();
    const token = authState.accessToken || authState.guestToken;

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

      // 使用流式 API
      for await (const event of chatApi.stream(message, sessionId)) {
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

