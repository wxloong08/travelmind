/**
 * 行程历史管理 Hook
 * 
 * 用于历史行程抽屉：获取列表、加载选中行程、删除行程、新建行程
 */

import { useState, useCallback } from 'react';
import { tripsApi } from '../api/client';
import useTravelStore from '../store/useTravelStore';
import useAuthStore from '../store/useAuthStore';

/**
 * 行程历史管理
 */
export function useTripHistory() {
    const [trips, setTrips] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [total, setTotal] = useState(0);

    // 从 auth store 获取 token（支持登录用户和游客）
    const accessToken = useAuthStore((state) => state.accessToken);
    const guestToken = useAuthStore((state) => state.guestToken);
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
        clearChat,
        resetTrip,
        clearCache,
    } = useTravelStore();

    /**
     * 获取行程列表
     */
    const fetchTrips = useCallback(async (limit = 20, offset = 0) => {
        if (!token) {
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const data = await tripsApi.list(token, limit, offset);
            setTrips(data.trips || []);
            setTotal(data.total || 0);

        } catch (err) {
            console.error('[TripHistory] Failed to fetch trips:', err);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [token]);

    /**
     * 加载选中的行程
     * @param {string} tripId - 行程 ID
     */
    const loadTrip = useCallback(async (tripId) => {
        if (!token) return;

        setIsLoading(true);
        setError(null);

        try {
            const data = await tripsApi.get(token, tripId);


            // 恢复行程数据到 store
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

            // 恢复对话消息（重要：先清除旧对话，再恢复新对话）
            if (data.conversation?.messages && data.conversation.messages.length > 0) {
                const formattedMessages = data.conversation.messages.map(msg => ({
                    role: msg.role === 'user' ? 'user' : 'ai',
                    content: msg.content,
                    isStreaming: false,
                }));
                setMessages(formattedMessages);

                if (data.conversation.session_id) {
                    setSessionId(data.conversation.session_id);
                }
            } else {
                // 如果没有对话历史，设置默认欢迎消息并重置 sessionId
                setMessages([
                    {
                        role: 'ai',
                        content: `已加载${data.destination || ''}行程。有什么需要我帮您调整的吗？`,
                        isStreaming: false,
                    },
                ]);
                setSessionId(null);
            }

            // 清除缓存，因为切换了行程
            clearCache();


            return true;
        } catch (err) {
            console.error('[TripHistory] Failed to load trip:', err);
            setError(err.message);
            return false;
        } finally {
            setIsLoading(false);
        }
    }, [token, setDestination, setItinerary, setWeather, setPois, setTripStatus, setMessages, setSessionId, clearCache]);

    /**
     * 删除行程
     * @param {string} tripId - 行程 ID
     */
    const deleteTrip = useCallback(async (tripId) => {
        if (!token) return false;

        setIsLoading(true);
        setError(null);

        try {
            await tripsApi.delete(token, tripId);
            // 从本地列表中移除
            setTrips(prev => prev.filter(t => t.id !== tripId));
            setTotal(prev => prev - 1);

            return true;
        } catch (err) {
            console.error('[TripHistory] Failed to delete trip:', err);
            setError(err.message);
            return false;
        } finally {
            setIsLoading(false);
        }
    }, [token]);

    /**
     * 创建新行程（清空当前状态）
     */
    const createNewTrip = useCallback(() => {
        resetTrip();
        clearChat();
        clearCache();

    }, [resetTrip, clearChat, clearCache]);

    return {
        trips,
        isLoading,
        error,
        total,
        fetchTrips,
        loadTrip,
        deleteTrip,
        createNewTrip,
    };
}

export default useTripHistory;
