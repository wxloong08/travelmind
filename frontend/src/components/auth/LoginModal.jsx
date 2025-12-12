/**
 * 登录弹窗组件
 * 
 * 支持手机号验证码登录
 */

import React, { useState, useEffect } from 'react';
import { X, Phone, Lock, Loader2, User, LogOut } from 'lucide-react';
import useAuthStore from '../../store/useAuthStore';

export function LoginModal({ isOpen, onClose }) {
    const [phone, setPhone] = useState('');
    const [code, setCode] = useState('');
    const [countdown, setCountdown] = useState(0);
    const [step, setStep] = useState('phone'); // 'phone' | 'code'
    const [devCode, setDevCode] = useState(null); // 开发模式显示验证码
    
    const {
        isLoading,
        error,
        sendSmsCode,
        loginWithSms,
        clearError,
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
            setStep('phone');
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
    
    // 登录
    const handleLogin = async () => {
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
    
    if (!isOpen) return null;
    
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
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
                    
                    {/* 验证码输入 */}
                    {step === 'code' && (
                        <div className="space-y-2 animate-fadeIn">
                            <label className="text-sm text-gray-400">验证码</label>
                            <div className="relative">
                                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                <input
                                    type="text"
                                    value={code}
                                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
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
                    {step === 'phone' ? (
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
                        <>
                            <button
                                onClick={handleLogin}
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
                
                {/* 底部提示 */}
                <div className="px-6 pb-6 text-center">
                    <p className="text-xs text-gray-500">
                        登录即表示同意 <span className="text-blue-400">服务条款</span> 和 <span className="text-blue-400">隐私政策</span>
                    </p>
                </div>
            </div>
        </div>
    );
}

/**
 * 用户头像/登录按钮组件
 */
export function UserButton() {
    const [showDropdown, setShowDropdown] = useState(false);
    const [showLoginModal, setShowLoginModal] = useState(false);
    
    const { user, isLoggedIn, logout, initGuest } = useAuthStore();
    
    // 初始化游客身份
    useEffect(() => {
        initGuest();
    }, []);
    
    if (isLoggedIn && user) {
        return (
            <>
                <div className="relative">
                    <button
                        onClick={() => setShowDropdown(!showDropdown)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
                    >
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                            {user.nickname?.[0] || user.phone?.slice(-4) || 'U'}
                        </div>
                        <span className="text-sm text-gray-300 hidden sm:inline">
                            {user.nickname || `${user.phone?.slice(0, 3)}****${user.phone?.slice(-4)}`}
                        </span>
                    </button>
                    
                    {showDropdown && (
                        <div className="absolute right-0 top-full mt-2 w-48 bg-[#1a1d2d] border border-white/10 rounded-xl shadow-xl overflow-hidden z-50">
                            <div className="p-3 border-b border-white/10">
                                <p className="text-sm text-white font-medium">
                                    {user.nickname || '用户'}
                                </p>
                                <p className="text-xs text-gray-500">{user.phone}</p>
                            </div>
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
                    )}
                </div>
                
                {/* 点击外部关闭下拉菜单 */}
                {showDropdown && (
                    <div 
                        className="fixed inset-0 z-40" 
                        onClick={() => setShowDropdown(false)}
                    />
                )}
            </>
        );
    }
    
    return (
        <>
            <button
                onClick={() => setShowLoginModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-sm font-medium rounded-lg transition-all"
            >
                <User size={16} />
                <span className="hidden sm:inline">登录</span>
            </button>
            
            <LoginModal 
                isOpen={showLoginModal}
                onClose={() => setShowLoginModal(false)}
            />
        </>
    );
}

export default LoginModal;
