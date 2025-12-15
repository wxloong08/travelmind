/**
 * 用户设置弹窗组件
 * 
 * 支持：
 * - 预设头像选择（男/女）
 * - 修改昵称
 * - 设置/修改密码（需短信验证，手机号自动获取）
 */

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, User, Lock, Phone, Loader2, Check, KeyRound, Eye, EyeOff } from 'lucide-react';
import useAuthStore from '../../store/useAuthStore';

const API_BASE = '/api/v1';

// 生成 DiceBear Adventurer 头像 URL
const generateDiceBearAvatar = (seed) => {
    return `https://api.dicebear.com/9.x/adventurer/svg?seed=${encodeURIComponent(seed)}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf`;
};

// 预设头像（包含预设图片和 DiceBear 示例）
const AVATAR_PRESETS = [
    { id: 'woman', url: '/avatars/woman.png', label: '女生' },
    { id: 'man', url: '/avatars/man.png', label: '男生' },
];

export function UserSettingsModal({ isOpen, onClose }) {
    const { user, accessToken } = useAuthStore();

    // 基本信息
    const [nickname, setNickname] = useState('');
    const [avatarUrl, setAvatarUrl] = useState('');

    // 密码修改
    const [showPasswordSection, setShowPasswordSection] = useState(false);
    const [fullPhone, setFullPhone] = useState(''); // 完整手机号（从后端获取）
    const [code, setCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [countdown, setCountdown] = useState(0);
    const [devCode, setDevCode] = useState(null);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    // 状态
    const [isLoading, setIsLoading] = useState(false);
    const [isFetchingPhone, setIsFetchingPhone] = useState(false);
    const [message, setMessage] = useState({ type: '', text: '' });

    // 初始化用户数据
    useEffect(() => {
        if (user && isOpen) {
            setNickname(user.nickname || '');
            setAvatarUrl(user.avatar_url || '');
        }
    }, [user, isOpen]);

    // 获取完整手机号（展开密码区域时）
    useEffect(() => {
        if (showPasswordSection && !fullPhone && accessToken) {
            fetchFullPhone();
        }
    }, [showPasswordSection]);

    const fetchFullPhone = async () => {
        setIsFetchingPhone(true);
        try {
            const response = await fetch(`${API_BASE}/auth/me/phone`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                },
            });
            if (response.ok) {
                const data = await response.json();
                setFullPhone(data.phone || '');
            }
        } catch (error) {
            console.error('Failed to fetch phone:', error);
        } finally {
            setIsFetchingPhone(false);
        }
    };

    // 倒计时
    useEffect(() => {
        if (countdown > 0) {
            const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [countdown]);

    // 关闭时重置
    useEffect(() => {
        if (!isOpen) {
            setShowPasswordSection(false);
            setCode('');
            setNewPassword('');
            setConfirmPassword('');
            setDevCode(null);
            setMessage({ type: '', text: '' });
            setFullPhone('');
        }
    }, [isOpen]);

    // 选择预设头像
    const selectPresetAvatar = (url) => {
        setAvatarUrl(url);
    };

    // 保存基本信息
    const handleSaveProfile = async () => {
        setIsLoading(true);
        setMessage({ type: '', text: '' });

        try {
            const response = await fetch(`${API_BASE}/auth/profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                },
                body: JSON.stringify({
                    nickname: nickname || null,
                    avatar_url: avatarUrl || null,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '保存失败');
            }

            // 更新本地状态
            useAuthStore.setState((state) => ({
                user: {
                    ...state.user,
                    nickname: nickname,
                    avatar_url: avatarUrl,
                },
            }));

            setMessage({ type: 'success', text: '资料保存成功！' });
        } catch (error) {
            setMessage({ type: 'error', text: error.message });
        } finally {
            setIsLoading(false);
        }
    };

    // 发送验证码
    const handleSendCode = async () => {
        if (!fullPhone || fullPhone.length !== 11) {
            setMessage({ type: 'error', text: '手机号获取失败，请刷新重试' });
            return;
        }

        setIsLoading(true);
        setMessage({ type: '', text: '' });

        try {
            const response = await fetch(`${API_BASE}/auth/sms/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: fullPhone }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '发送失败');
            }

            // 检查业务逻辑是否成功
            if (!data.success) {
                throw new Error(data.message || '发送失败');
            }

            setCountdown(60);

            // 开发模式：从 code 字段或 message 中提取验证码
            if (data.code) {
                setDevCode(data.code);
            } else if (data.message && /\d{6}/.test(data.message)) {
                // 从 message 中提取 6 位数字验证码
                const match = data.message.match(/\d{6}/);
                if (match) {
                    setDevCode(match[0]);
                }
            }

            setMessage({ type: 'success', text: '验证码已发送' });
        } catch (error) {
            setMessage({ type: 'error', text: error.message });
        } finally {
            setIsLoading(false);
        }
    };

    // 验证密码强度
    const validatePasswordStrength = (pwd) => {
        const errors = [];
        if (pwd.length < 8) errors.push('至少8位');
        // bcrypt 72字节限制
        if (new Blob([pwd]).size > 72) errors.push('密码过长');
        if (!/[a-zA-Z]/.test(pwd)) errors.push('需包含字母');
        if (!/\d/.test(pwd)) errors.push('需包含数字');
        if (!/[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;'`~]/.test(pwd)) errors.push('需包含特殊字符');
        return errors;
    };

    // Enter 键处理
    const handleKeyPress = (e, action) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            action();
        }
    };

    // 设置密码
    const handleSetPassword = async () => {
        if (!code || code.length !== 6) {
            setMessage({ type: 'error', text: '请输入6位验证码' });
            return;
        }

        const pwdErrors = validatePasswordStrength(newPassword);
        if (pwdErrors.length > 0) {
            setMessage({ type: 'error', text: `密码要求：${pwdErrors.join('、')}` });
            return;
        }

        if (newPassword !== confirmPassword) {
            setMessage({ type: 'error', text: '两次密码不一致' });
            return;
        }

        setIsLoading(true);
        setMessage({ type: '', text: '' });

        try {
            const response = await fetch(`${API_BASE}/auth/password/set`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone: fullPhone,
                    code,
                    password: newPassword,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '设置失败');
            }

            setMessage({ type: 'success', text: '密码设置成功！' });
            setShowPasswordSection(false);
            setCode('');
            setNewPassword('');
            setConfirmPassword('');
            setDevCode(null);
        } catch (error) {
            setMessage({ type: 'error', text: error.message });
        } finally {
            setIsLoading(false);
        }
    };

    // 获取密码强度提示
    const getPasswordStrengthHint = () => {
        if (!newPassword) return null;
        const errors = validatePasswordStrength(newPassword);
        if (errors.length === 0) {
            return <span className="text-green-400 text-xs">✓ 密码强度合格</span>;
        }
        return <span className="text-yellow-400 text-xs">还需：{errors.join('、')}</span>;
    };

    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
            {/* 背景遮罩 */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* 弹窗内容 */}
            <div className="relative w-full max-w-lg mx-4 bg-[#1a1d2d] border border-white/10 rounded-2xl shadow-2xl animate-fadeIn max-h-[90vh] overflow-y-auto dark-scrollbar">
                {/* 头部 */}
                <div className="flex items-center justify-between p-6 border-b border-white/10 sticky top-0 bg-[#1a1d2d] z-10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <User size={20} className="text-white" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">用户设置</h2>
                            <p className="text-xs text-gray-500">管理您的个人信息</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                    >
                        <X size={20} className="text-gray-400" />
                    </button>
                </div>

                {/* 内容 */}
                <div className="p-6 space-y-6">
                    {/* 消息提示（仅在密码设置区域未展开时显示） */}
                    {message.text && !showPasswordSection && (
                        <div className={`p-3 rounded-lg ${message.type === 'success'
                            ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                            : 'bg-red-500/10 border border-red-500/30 text-red-400'
                            }`}>
                            <p className="text-sm flex items-center gap-2">
                                {message.type === 'success' && <Check size={16} />}
                                {message.text}
                            </p>
                        </div>
                    )}

                    {/* 头像选择区域 */}
                    <div className="space-y-3">
                        <label className="text-sm text-gray-400">选择头像</label>
                        <div className="flex items-center gap-4 justify-center flex-wrap">
                            {/* 预设头像 */}
                            {AVATAR_PRESETS.map((preset) => (
                                <button
                                    key={preset.id}
                                    onClick={() => selectPresetAvatar(preset.url)}
                                    className={`relative group transition-all ${avatarUrl === preset.url
                                        ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-[#1a1d2d]'
                                        : 'hover:scale-105'
                                        }`}
                                >
                                    <img
                                        src={preset.url}
                                        alt={preset.label}
                                        className="w-16 h-16 rounded-full object-cover"
                                    />
                                    <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-gray-400 whitespace-nowrap">
                                        {preset.label}
                                    </span>
                                    {avatarUrl === preset.url && (
                                        <div className="absolute -top-1 -right-1 w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                                            <Check size={10} className="text-white" />
                                        </div>
                                    )}
                                </button>
                            ))}

                            {/* 随机头像按钮 */}
                            <button
                                onClick={() => {
                                    const seed = Math.random().toString(36).slice(2) + Date.now().toString(36);
                                    setAvatarUrl(generateDiceBearAvatar(seed));
                                }}
                                className={`relative group transition-all hover:scale-105 ${avatarUrl?.includes('dicebear.com')
                                    ? 'ring-2 ring-purple-500 ring-offset-2 ring-offset-[#1a1d2d]'
                                    : ''
                                    }`}
                            >
                                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center overflow-hidden">
                                    {avatarUrl?.includes('dicebear.com') ? (
                                        <img src={avatarUrl} alt="随机头像" className="w-full h-full" />
                                    ) : (
                                        <span className="text-white text-2xl">🎲</span>
                                    )}
                                </div>
                                <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-gray-400 whitespace-nowrap">
                                    随机
                                </span>
                                {avatarUrl?.includes('dicebear.com') && (
                                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-purple-500 rounded-full flex items-center justify-center">
                                        <Check size={10} className="text-white" />
                                    </div>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* 昵称 */}
                    <div className="space-y-2 mt-8">
                        <label className="text-sm text-gray-400">昵称</label>
                        <input
                            type="text"
                            value={nickname}
                            onChange={(e) => setNickname(e.target.value)}
                            placeholder="设置您的昵称"
                            maxLength={50}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                        />
                    </div>

                    {/* 保存按钮 */}
                    <button
                        onClick={handleSaveProfile}
                        disabled={isLoading}
                        className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {isLoading ? (
                            <Loader2 size={18} className="animate-spin" />
                        ) : (
                            '保存资料'
                        )}
                    </button>

                    {/* 分隔线 */}
                    <div className="border-t border-white/10 pt-6">
                        <button
                            onClick={() => setShowPasswordSection(!showPasswordSection)}
                            className="w-full flex items-center justify-between p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <KeyRound size={20} className="text-gray-400" />
                                <div className="text-left">
                                    <p className="text-white font-medium">密码设置</p>
                                    <p className="text-xs text-gray-500">设置或修改登录密码</p>
                                </div>
                            </div>
                            <span className={`text-gray-400 transform transition-transform ${showPasswordSection ? 'rotate-180' : ''}`}>
                                ▼
                            </span>
                        </button>
                    </div>

                    {/* 密码设置区域 */}
                    {showPasswordSection && (
                        <div className="space-y-4 animate-fadeIn">
                            {/* 密码设置区域内的消息提示 */}
                            {message.text && (
                                <div className={`p-3 rounded-lg ${message.type === 'success'
                                    ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                                    : 'bg-red-500/10 border border-red-500/30 text-red-400'
                                    }`}>
                                    <p className="text-sm flex items-center gap-2">
                                        {message.type === 'success' && <Check size={16} />}
                                        {message.text}
                                    </p>
                                </div>
                            )}
                            {/* 手机号（只读，自动获取） */}
                            <div className="space-y-2">
                                <label className="text-sm text-gray-400">验证手机号</label>
                                <div className="flex gap-2">
                                    <div className="relative flex-1">
                                        <Phone size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                        <input
                                            type="tel"
                                            value={fullPhone ? `${fullPhone.slice(0, 3)}****${fullPhone.slice(-4)}` : (isFetchingPhone ? '获取中...' : '')}
                                            readOnly
                                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-gray-400 cursor-not-allowed"
                                        />
                                    </div>
                                    <button
                                        onClick={handleSendCode}
                                        disabled={isLoading || countdown > 0 || !fullPhone}
                                        className="px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                                    >
                                        {countdown > 0 ? `${countdown}s` : '获取验证码'}
                                    </button>
                                </div>
                            </div>

                            {/* 开发模式验证码 */}
                            {devCode && (
                                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-center">
                                    <p className="text-yellow-400 text-xs">开发模式 - 验证码:</p>
                                    <p className="text-yellow-300 text-2xl font-mono font-bold tracking-widest">{devCode}</p>
                                </div>
                            )}

                            {/* 验证码 */}
                            <div className="space-y-2">
                                <label className="text-sm text-gray-400">验证码</label>
                                <input
                                    type="text"
                                    value={code}
                                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                    placeholder="请输入6位验证码"
                                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>

                            {/* 新密码 */}
                            <div className="space-y-2">
                                <label className="text-sm text-gray-400">新密码</label>
                                <div className="relative">
                                    <input
                                        type={showNewPassword ? "text" : "password"}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="至少8位，含字母+数字+特殊字符"
                                        className="w-full px-4 py-3 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowNewPassword(!showNewPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                                    >
                                        {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                                {getPasswordStrengthHint()}
                            </div>

                            {/* 确认密码 */}
                            <div className="space-y-2">
                                <label className="text-sm text-gray-400">确认密码</label>
                                <div className="relative">
                                    <input
                                        type={showConfirmPassword ? "text" : "password"}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="请再次输入新密码"
                                        className="w-full px-4 py-3 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                                    >
                                        {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                                {confirmPassword && newPassword !== confirmPassword && (
                                    <span className="text-red-400 text-xs">密码不一致</span>
                                )}
                            </div>

                            {/* 设置密码按钮 */}
                            <button
                                onClick={handleSetPassword}
                                disabled={isLoading || !code || !newPassword || !confirmPassword}
                                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {isLoading ? (
                                    <Loader2 size={18} className="animate-spin" />
                                ) : (
                                    '设置密码'
                                )}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>,
        document.body
    );
}

export default UserSettingsModal;
