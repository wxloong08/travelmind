/**
 * 登录弹窗组件
 * 
 * 支持手机号验证码登录和密码登录
 * 使用 Portal 渲染到 body，确保 fixed 定位正常工作
 */

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Phone, Lock, Loader2, User, LogOut, KeyRound, MessageSquare } from 'lucide-react';
import useAuthStore from '../../store/useAuthStore';

export function LoginModal({ isOpen, onClose }) {
    const [phone, setPhone] = useState('');
    const [code, setCode] = useState('');
    const [password, setPassword] = useState('');
    const [countdown, setCountdown] = useState(0);
    const [step, setStep] = useState('phone'); // 'phone' | 'code' | 'password'
    const [loginMode, setLoginMode] = useState('sms'); // 'sms' | 'password'
    const [devCode, setDevCode] = useState(null); // 开发模式显示验证码

    const {
        isLoading,
        error,
        sendSmsCode,
        loginWithSms,
        loginWithPassword,
        clearError,
        initGuest,
    } = useAuthStore();

    // 倒计时
    useEffect(() => {
        if (countdown > 0) {
            const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [countdown]);

    // 关闭时重置状态
    useEffect(() => {
        if (!isOpen) {
            setPhone('');
            setCode('');
            setPassword('');
            setStep('phone');
            setLoginMode('sms');
            setDevCode(null);
            clearError();
        }
    }, [isOpen]);

    // 发送验证码
    const handleSendCode = async () => {
        if (!phone || phone.length !== 11) {
            alert('请输入正确的手机号');
            return;
        }

        const result = await sendSmsCode(phone);

        if (result.success) {
            setStep('code');
            setCountdown(60);
            // 开发模式下显示验证码
            if (result.code) {
                setDevCode(result.code);
            }
        } else {
            alert(result.message || '发送失败');
        }
    };

    // 验证码登录
    const handleSmsLogin = async () => {
        if (!code || code.length !== 6) {
            alert('请输入6位验证码');
            return;
        }

        const result = await loginWithSms(phone, code);

        if (result.success) {
            onClose();
        } else {
            alert(result.message || '登录失败');
        }
    };

    // 密码登录
    const handlePasswordLogin = async () => {
        if (!phone || phone.length !== 11) {
            alert('请输入正确的手机号');
            return;
        }
        if (!password || password.length < 8) {
            alert('请输入密码（至少8位）');
            return;
        }

        const result = await loginWithPassword(phone, password);

        if (result.success) {
            onClose();
        } else {
            alert(result.message || '登录失败');
        }
    };

    // 切换登录模式
    const toggleLoginMode = () => {
        setLoginMode(loginMode === 'sms' ? 'password' : 'sms');
        setStep('phone');
        setCode('');
        setPassword('');
        setDevCode(null);
        clearError();
    };

    // 游客模式
    const handleGuestMode = async () => {
        await initGuest();
        onClose();
    };

    // 键盘事件
    const handleKeyPress = (e, action) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            action();
        }
    };

    if (!isOpen) return null;

    // 使用 Portal 渲染到 body，确保 fixed 定位正常工作
    return createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
            {/* 背景遮罩 */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* 弹窗内容 */}
            <div className="relative w-full max-w-md mx-4 bg-[#1a1d2d] border border-white/10 rounded-2xl shadow-2xl animate-fadeIn">
                {/* 头部 */}
                <div className="flex items-center justify-between p-6 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <User size={20} className="text-white" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">登录 TravelMind</h2>
                            <p className="text-xs text-gray-500">保存行程，跨设备同步</p>
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
                <div className="p-6 space-y-4">
                    {/* 登录模式切换 */}
                    <div className="flex justify-center">
                        <div className="inline-flex bg-white/5 rounded-lg p-1">
                            <button
                                onClick={() => { setLoginMode('sms'); setStep('phone'); setPassword(''); setCode(''); }}
                                className={`px-4 py-1.5 rounded-md text-sm transition-colors flex items-center gap-1.5 ${loginMode === 'sms'
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                <MessageSquare size={14} />
                                验证码登录
                            </button>
                            <button
                                onClick={() => { setLoginMode('password'); setStep('phone'); setCode(''); setDevCode(null); }}
                                className={`px-4 py-1.5 rounded-md text-sm transition-colors flex items-center gap-1.5 ${loginMode === 'password'
                                    ? 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                <KeyRound size={14} />
                                密码登录
                            </button>
                        </div>
                    </div>

                    {/* 手机号输入 */}
                    <div className="space-y-2">
                        <label className="text-sm text-gray-400">手机号</label>
                        <div className="relative">
                            <Phone size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                            <input
                                type="tel"
                                value={phone}
                                onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 11))}
                                placeholder="请输入手机号"
                                disabled={step === 'code'}
                                className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
                            />
                        </div>
                    </div>

                    {/* 密码输入（密码登录模式） */}
                    {loginMode === 'password' && (
                        <div className="space-y-2 animate-fadeIn">
                            <label className="text-sm text-gray-400">密码</label>
                            <div className="relative">
                                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    onKeyPress={(e) => handleKeyPress(e, handlePasswordLogin)}
                                    placeholder="请输入密码（至少8位）"
                                    className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>
                            <p className="text-xs text-gray-500">首次登录请使用验证码登录后设置密码</p>
                        </div>
                    )}

                    {/* 验证码输入（SMS登录模式） */}
                    {loginMode === 'sms' && step === 'code' && (
                        <div className="space-y-2 animate-fadeIn">
                            <label className="text-sm text-gray-400">验证码</label>
                            <div className="relative">
                                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                <input
                                    type="text"
                                    value={code}
                                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                    onKeyPress={(e) => handleKeyPress(e, handleSmsLogin)}
                                    placeholder="请输入6位验证码"
                                    className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                                    autoFocus
                                />
                            </div>

                            {/* 开发模式显示验证码 */}
                            {devCode && (
                                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-center">
                                    <p className="text-yellow-400 text-xs">开发模式 - 验证码:</p>
                                    <p className="text-yellow-300 text-2xl font-mono font-bold tracking-widest">{devCode}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* 错误提示 */}
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                            <p className="text-red-400 text-sm">{error}</p>
                        </div>
                    )}
                </div>

                {/* 底部按钮 */}
                <div className="p-6 pt-0 space-y-3">
                    {loginMode === 'password' ? (
                        /* 密码登录模式 */
                        <button
                            onClick={handlePasswordLogin}
                            disabled={isLoading || phone.length !== 11 || password.length < 8}
                            className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <Loader2 size={18} className="animate-spin" />
                            ) : (
                                '登录'
                            )}
                        </button>
                    ) : step === 'phone' ? (
                        /* SMS模式 - 获取验证码 */
                        <button
                            onClick={handleSendCode}
                            disabled={isLoading || phone.length !== 11}
                            className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <Loader2 size={18} className="animate-spin" />
                            ) : (
                                '获取验证码'
                            )}
                        </button>
                    ) : (
                        /* SMS模式 - 登录 */
                        <>
                            <button
                                onClick={handleSmsLogin}
                                disabled={isLoading || code.length !== 6}
                                className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {isLoading ? (
                                    <Loader2 size={18} className="animate-spin" />
                                ) : (
                                    '登录'
                                )}
                            </button>

                            <button
                                onClick={handleSendCode}
                                disabled={isLoading || countdown > 0}
                                className="w-full py-2 text-gray-400 hover:text-white text-sm transition-colors disabled:cursor-not-allowed"
                            >
                                {countdown > 0 ? `重新发送 (${countdown}s)` : '重新发送验证码'}
                            </button>
                        </>
                    )}
                </div>

                {/* 分隔线和游客模式 */}
                <div className="px-6 pb-4">
                    <div className="relative flex items-center justify-center py-3">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/10"></div>
                        </div>
                        <span className="relative px-4 text-xs text-gray-500 bg-[#1a1d2d]">或者</span>
                    </div>

                    <button
                        onClick={handleGuestMode}
                        disabled={isLoading}
                        className="w-full py-3 bg-white/5 hover:bg-white/10 text-gray-300 font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        游客模式快速体验
                    </button>
                    <p className="text-xs text-gray-500 text-center mt-2">
                        游客数据仅在当前浏览器保存
                    </p>
                </div>

                {/* 底部提示 */}
                <div className="px-6 pb-6 text-center">
                    <p className="text-xs text-gray-500">
                        登录即表示同意 <span className="text-blue-400">服务条款</span> 和 <span className="text-blue-400">隐私政策</span>
                    </p>
                </div>
            </div>
        </div>,
        document.body
    );
}

/**
 * 用户头像按钮
 * 
 * 显示三种状态：
 * 1. 已登录用户：显示用户头像和昵称，下拉菜单
 * 2. 游客：显示"游客"文字
 * 3. 未登录：显示"登录"按钮
 */
export function UserButton() {
    const [showDropdown, setShowDropdown] = useState(false);
    const [showLoginModal, setShowLoginModal] = useState(false);
    const [showSettingsModal, setShowSettingsModal] = useState(false);

    // 直接订阅状态
    const user = useAuthStore((state) => state.user);
    const guest = useAuthStore((state) => state.guest);
    const accessToken = useAuthStore((state) => state.accessToken);
    const guestToken = useAuthStore((state) => state.guestToken);
    const logout = useAuthStore((state) => state.logout);
    const initGuest = useAuthStore((state) => state.initGuest);
    const hasHydrated = useAuthStore((state) => state._hasHydrated);

    // 计算身份状态（不阻塞渲染，hydration 完成后会自动更新）
    const isLoggedIn = !!accessToken && !!user;
    const isGuest = !accessToken && !!guestToken && !!guest;
    const isAuthenticated = isLoggedIn || isGuest;

    // 不再自动初始化游客身份
    // 用户发送消息时会触发登录流程，可选择游客模式或正式登录

    // 用于计算下拉菜单位置的 ref
    const buttonRef = React.useRef(null);
    const [dropdownPosition, setDropdownPosition] = React.useState({ top: 0, right: 0 });

    // 更新下拉菜单位置
    useEffect(() => {
        if (showDropdown && buttonRef.current) {
            const rect = buttonRef.current.getBoundingClientRect();
            setDropdownPosition({
                top: rect.bottom + 8,
                right: window.innerWidth - rect.right,
            });
        }
    }, [showDropdown]);

    // 动态导入 UserSettingsModal
    const UserSettingsModal = React.lazy(() => import('./UserSettingsModal'));

    // 已登录用户：显示头像和菜单
    if (isLoggedIn && user) {
        return (
            <>
                <div className="relative">
                    <button
                        ref={buttonRef}
                        onClick={() => setShowDropdown(!showDropdown)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
                    >
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm overflow-hidden">
                            {user.avatar_url ? (
                                <img src={user.avatar_url} alt="avatar" className="w-full h-full object-cover" />
                            ) : (
                                user.nickname?.[0] || user.phone?.slice(-4) || 'U'
                            )}
                        </div>
                        <span className="text-sm text-gray-300 hidden sm:inline">
                            {user.nickname || `${user.phone?.slice(0, 3)}****${user.phone?.slice(-4)}`}
                        </span>
                    </button>
                </div>

                {/* 使用 Portal 渲染下拉菜单到 body */}
                {showDropdown && createPortal(
                    <>
                        <div
                            className="fixed inset-0 z-[9998]"
                            onClick={() => setShowDropdown(false)}
                        />
                        <div
                            className="fixed w-48 bg-[#1a1d2d] border border-white/10 rounded-xl shadow-xl overflow-hidden z-[9999]"
                            style={{ top: dropdownPosition.top, right: dropdownPosition.right }}
                        >
                            <div className="p-3 border-b border-white/10">
                                <p className="text-sm text-white font-medium">
                                    {user.nickname || '用户'}
                                </p>
                                <p className="text-xs text-gray-500">{user.phone}</p>
                            </div>
                            <button
                                onClick={() => {
                                    setShowSettingsModal(true);
                                    setShowDropdown(false);
                                }}
                                className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-white/5 flex items-center gap-2"
                            >
                                <User size={14} />
                                用户设置
                            </button>
                            <button
                                onClick={() => {
                                    logout();
                                    setShowDropdown(false);
                                }}
                                className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-white/5 flex items-center gap-2"
                            >
                                <LogOut size={14} />
                                退出登录
                            </button>
                        </div>
                    </>,
                    document.body
                )}

                {/* 用户设置弹窗 */}
                <React.Suspense fallback={null}>
                    <UserSettingsModal
                        isOpen={showSettingsModal}
                        onClose={() => setShowSettingsModal(false)}
                    />
                </React.Suspense>
            </>
        );
    }

    // 游客：显示游客身份，点击可以升级为注册用户
    if (isGuest && guest) {
        return (
            <>
                <button
                    onClick={() => setShowLoginModal(true)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-500 to-gray-600 flex items-center justify-center text-white font-bold text-sm">
                        G
                    </div>
                    <span className="text-sm text-gray-400 hidden sm:inline">游客</span>
                </button>

                <LoginModal
                    isOpen={showLoginModal}
                    onClose={() => setShowLoginModal(false)}
                />
            </>
        );
    }

    // 未登录：显示"未登录"按钮
    return (
        <>
            <button
                onClick={() => setShowLoginModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
            >
                <User size={16} className="text-gray-400" />
                <span className="text-sm text-gray-400 hidden sm:inline">未登录</span>
            </button>

            <LoginModal
                isOpen={showLoginModal}
                onClose={() => setShowLoginModal(false)}
            />
        </>
    );
}

export default LoginModal;
