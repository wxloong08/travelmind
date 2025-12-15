/**
 * 认证状态管理
 * 
 * 管理用户登录状态、Token、游客身份
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const API_BASE = '/api/v1';

// 生成稳定的设备指纹（不包含时间戳，确保同一设备始终生成相同指纹）
const generateDeviceFingerprint = () => {
    // 收集稳定的设备特征
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('fingerprint', 2, 2);
    const canvasData = canvas.toDataURL();

    // 只使用稳定的特征，不包含任何时间相关的值
    const stableFeatures = [
        navigator.userAgent,
        navigator.language,
        screen.width + 'x' + screen.height,
        screen.colorDepth,
        new Date().getTimezoneOffset(),
        navigator.hardwareConcurrency || 'unknown',
        canvasData.slice(-100),  // canvas 指纹更长一些
    ].join('|');

    // 生成稳定的哈希
    let hash = 0;
    for (let i = 0; i < stableFeatures.length; i++) {
        const char = stableFeatures.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }

    // 生成第二个哈希以增加长度
    let hash2 = 5381;
    for (let i = 0; i < stableFeatures.length; i++) {
        hash2 = ((hash2 << 5) + hash2) + stableFeatures.charCodeAt(i);
    }

    // 确保指纹长度至少 16 字符：前缀 + 两个 hash
    const hashStr1 = Math.abs(hash).toString(36).padStart(8, '0');
    const hashStr2 = Math.abs(hash2).toString(36).padStart(8, '0');
    return 'tm' + hashStr1 + hashStr2;  // 2 + 8 + 8 = 18 字符，稳定不变
};

const useAuthStore = create(
    persist(
        (set, get) => ({
            // 状态
            user: null,           // 登录用户信息
            guest: null,          // 游客信息
            accessToken: null,    // 访问令牌
            refreshToken: null,   // 刷新令牌
            guestToken: null,     // 游客令牌
            isLoading: false,
            error: null,

            // 计算属性（使用函数避免 zustand persist hydration 问题）
            getIsAuthenticated: () => {
                const state = get();
                return !!(state?.accessToken || state?.guestToken);
            },
            getIsLoggedIn: () => {
                const state = get();
                return !!(state?.accessToken && state?.user);
            },
            getIsGuest: () => {
                const state = get();
                return !state?.accessToken && !!state?.guestToken;
            },
            getCurrentToken: () => {
                const state = get();
                return state?.accessToken || state?.guestToken;
            },

            // 获取当前身份类型
            getIdentityType: () => {
                const state = get();
                if (state.accessToken && state.user) return 'user';
                if (state.guestToken && state.guest) return 'guest';
                return 'anonymous';
            },

            // 获取当前身份 ID
            getIdentityId: () => {
                const state = get();
                if (state.user) return state.user.id;
                if (state.guest) return state.guest.id;
                return null;
            },

            // 初始化游客身份
            initGuest: async () => {
                const state = get();

                // 已登录用户不需要游客身份
                if (state.accessToken) return;

                // 已有有效游客 token
                if (state.guestToken && state.guest) return;

                set({ isLoading: true, error: null });

                try {
                    const fingerprint = generateDeviceFingerprint();

                    const response = await fetch(`${API_BASE}/auth/guest`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ device_fingerprint: fingerprint }),
                    });

                    if (!response.ok) {
                        throw new Error('游客初始化失败');
                    }

                    const data = await response.json();

                    set({
                        guestToken: data.token,
                        guest: {
                            id: data.guest_id,
                            fingerprint: fingerprint,
                        },
                        isLoading: false,
                    });
                } catch (error) {
                    set({ error: error.message, isLoading: false });
                }
            },

            // 发送验证码
            sendSmsCode: async (phone) => {
                set({ isLoading: true, error: null });

                try {
                    const response = await fetch(`${API_BASE}/auth/sms/send`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phone }),
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.detail || '发送验证码失败');
                    }

                    set({ isLoading: false });
                    return { success: true, message: data.message, code: data.code };
                } catch (error) {
                    set({ error: error.message, isLoading: false });
                    return { success: false, message: error.message };
                }
            },

            // 验证码登录
            loginWithSms: async (phone, code) => {
                set({ isLoading: true, error: null });

                try {
                    const state = get();
                    const body = { phone, code };

                    // 如果有游客身份，传递游客 ID 以便迁移数据
                    if (state.guest?.id) {
                        body.guest_id = state.guest.id;
                    }

                    const response = await fetch(`${API_BASE}/auth/sms/verify`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.detail || '登录失败');
                    }

                    set({
                        user: data.user,
                        accessToken: data.access_token,
                        refreshToken: data.refresh_token,
                        // 清除游客信息
                        guest: null,
                        guestToken: null,
                        isLoading: false,
                        error: null,
                    });

                    return { success: true };
                } catch (error) {
                    set({ error: error.message, isLoading: false });
                    return { success: false, message: error.message };
                }
            },

            // 密码登录
            loginWithPassword: async (phone, password) => {
                set({ isLoading: true, error: null });

                try {
                    const response = await fetch(`${API_BASE}/auth/password/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phone, password }),
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.detail || '登录失败');
                    }

                    set({
                        user: data.user,
                        accessToken: data.access_token,
                        refreshToken: data.refresh_token,
                        // 清除游客信息
                        guest: null,
                        guestToken: null,
                        isLoading: false,
                        error: null,
                    });

                    return { success: true };
                } catch (error) {
                    set({ error: error.message, isLoading: false });
                    return { success: false, message: error.message };
                }
            },

            // 刷新 Token
            refreshAccessToken: async () => {
                const state = get();

                if (!state.refreshToken) return false;

                try {
                    const response = await fetch(`${API_BASE}/auth/refresh`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ refresh_token: state.refreshToken }),
                    });

                    if (!response.ok) {
                        // Token 无效，退出登录
                        get().logout();
                        return false;
                    }

                    const data = await response.json();

                    set({
                        accessToken: data.access_token,
                        refreshToken: data.refresh_token || state.refreshToken,
                    });

                    return true;
                } catch (error) {
                    console.error('Token refresh failed:', error);
                    return false;
                }
            },

            // 登出
            logout: () => {
                set({
                    user: null,
                    accessToken: null,
                    refreshToken: null,
                    error: null,
                });

                // 重新初始化游客身份
                get().initGuest();
            },

            // 清除错误
            clearError: () => set({ error: null }),

            // Hydration 状态（用于等待 localStorage 恢复完成）
            _hasHydrated: false,
            setHasHydrated: (state) => set({ _hasHydrated: state }),
        }),
        {
            name: 'auth-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                user: state.user,
                guest: state.guest,
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
                guestToken: state.guestToken,
            }),
            onRehydrateStorage: () => (state, error) => {
                // 当 hydration 完成时调用
                state?.setHasHydrated(true);
            },
        }
    )
);

export default useAuthStore;
