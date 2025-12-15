/**
 * 行程恢复 Hook
 * 
 * 在 App 加载时从后端恢复最新的行程，实现刷新后行程持久化
 * 
 * 重要：只在以下情况触发恢复：
 * 1. 用户是已登录用户（有 accessToken，非游客）
 * 2. 用户刷新页面后重新登录
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import useTravelStore from '../store/useTravelStore';
import useAuthStore from '../store/useAuthStore';

const API_BASE = '/api/v1';

/**
 * 从后端恢复最新行程
 * 
 * 注意：只对已登录用户（非新游客）生效
 */
export function useTripRestore() {
    const [isRestoring, setIsRestoring] = useState(false);
    const [restored, setRestored] = useState(false);
    const [error, setError] = useState(null);

    // 用于跟踪已恢复的 token，避免重复恢复同一用户
    // 但允许新用户登录后重新恢复
    const lastRestoredToken = useRef(null);

    // 从 auth store 获取状态
    const accessToken = useAuthStore((state) => state.accessToken);
    const guestToken = useAuthStore((state) => state.guestToken);
    const user = useAuthStore((state) => state.user);
    const guest = useAuthStore((state) => state.guest);
    const hasHydrated = useAuthStore((state) => state._hasHydrated);

    // 支持已登录用户和游客的恢复
    // 已登录用户：有 accessToken 和 user
    // 游客：没有 accessToken，但有 guestToken 和 guest
    // 必须等待 hydration 完成
    const isLoggedInUser = hasHydrated && !!accessToken && !!user;
    const isGuest = hasHydrated && !accessToken && !!guestToken && !!guest;
    const canRestore = isLoggedInUser || isGuest;
    const token = accessToken || guestToken;

    // 从 travel store 获取 setters
    const {
        setDestination,
        setItinerary,
        setWeather,
        setPois,
        setTripStatus,
        setMessages,
        setSessionId,
        itinerary,
    } = useTravelStore();

    /**
     * 从后端获取最新行程并恢复到 store
     */
    const restoreLatestTrip = useCallback(async () => {
        // 已有行程则不恢复
        if (itinerary && itinerary.length > 0) {
            return;
        }

        // 只对已认证用户（登录用户或游客）恢复
        if (!canRestore || !token) {
            return;
        }

        // 如果已经恢复过这个 token，跳过
        if (lastRestoredToken.current === token) {
            return;
        }

        setIsRestoring(true);
        setError(null);

        try {

            const response = await fetch(`${API_BASE}/trips/latest`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });

            if (response.status === 404) {
                // 没有历史行程，正常情况
                setRestored(true);
                return;
            }

            // 401 未授权：token 无效或过期，触发登出
            if (response.status === 401) {
                console.warn('[TripRestore] Unauthorized, logging out');
                const authStore = useAuthStore.getState();
                authStore.logout(); // 清除认证状态
                setRestored(true); // 防止无限循环
                return;
            }

            if (!response.ok) {
                throw new Error(`Failed to fetch trip: ${response.status}`);
            }

            const data = await response.json();

            // 恢复到 store
            if (data.destination) {
                setDestination(data.destination);
            }

            if (data.itinerary_data?.days) {
                setItinerary(data.itinerary_data.days);
                setTripStatus('Created');
            }

            if (data.weather_snapshot) {
                setWeather(data.weather_snapshot);
            }

            if (data.pois_snapshot && data.pois_snapshot.length > 0) {
                setPois(data.pois_snapshot);
            }

            // 恢复对话消息
            if (data.conversation?.messages && data.conversation.messages.length > 0) {
                const formattedMessages = data.conversation.messages.map(msg => ({
                    role: msg.role === 'user' ? 'user' : 'ai',
                    content: msg.content,
                    isStreaming: false,
                }));
                setMessages(formattedMessages);

                // 恢复 sessionId 用于继续对话
                if (data.conversation.session_id) {
                    setSessionId(data.conversation.session_id);
                }
            }

            // 记录已恢复的 token，避免重复恢复
            lastRestoredToken.current = token;
            setRestored(true);

        } catch (err) {
            console.error('[TripRestore] Failed to restore trip:', err);
            setError(err.message);
        } finally {
            setIsRestoring(false);
        }
    }, [canRestore, token, itinerary, setDestination, setItinerary, setWeather, setPois, setTripStatus, setMessages, setSessionId]);

    // 已认证用户（登录用户或游客）自动恢复
    useEffect(() => {
        if (canRestore && token && !restored && !isRestoring) {
            restoreLatestTrip();
        }
    }, [canRestore, token, restored, isRestoring, restoreLatestTrip]);

    return {
        isRestoring,
        restored,
        error,
        restoreLatestTrip,  // 手动触发恢复
    };
}

export default useTripRestore;
