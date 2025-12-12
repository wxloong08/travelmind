/**
 * 认证状态管理
 * 
 * 管理用户登录状态、Token、游客身份
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const API_BASE = '/api/v1';

// 生成设备指纹（简化版，保证至少 16 字符）
const generateDeviceFingerprint = () => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('fingerprint', 2, 2);
    const canvasData = canvas.toDataURL();

    const data = [
        navigator.userAgent,
        navigator.language,
        screen.width + 'x' + screen.height,
        new Date().getTimezoneOffset(),
        canvasData.slice(-50),
    ].join('|');

    // 简单哈希
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
        const char = data.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }

    // 确保指纹长度至少 16 字符：前缀 + hash(补零到8位) + 时间戳
    const hashStr = Math.abs(hash).toString(36).padStart(8, '0');
    const timeStr = Date.now().toString(36).padStart(9, '0');
    return 'tm' + hashStr + timeStr;  // 2 + 8 + 9 = 19 字符
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

            // 计算属性
            get isAuthenticated() {
                return !!get().accessToken || !!get().guestToken;
            },
            get isLoggedIn() {
                return !!get().accessToken && !!get().user;
            },
            get isGuest() {
                return !get().accessToken && !!get().guestToken;
            },
            get currentToken() {
                return get().accessToken || get().guestToken;
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
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                guest: state.guest,
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
                guestToken: state.guestToken,
            }),
        }
    )
);

export default useAuthStore;
