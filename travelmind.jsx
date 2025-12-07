import React, { useState, useEffect, useRef } from 'react';
import {
    Send, MapPin, Calendar, CloudSun, Hotel,
    Coffee, Camera, Navigation, User, Bot,
    Sparkles, ChevronRight, Star, Clock, Heart,
    Backpack, X, Loader2, Lightbulb, CheckCircle2, Circle,
    Menu, LogOut, RefreshCw, Smartphone, Layout, Map as MapIcon,
    MessageSquare, UserCircle2, AlertTriangle, Utensils,
    PenLine, Save, Ticket, Info, Timer, Zap, Banknote, Share2, Copy,
    Music, Siren, Phone, Languages, Globe, BookOpen, Quote,
    Wifi, Waves, Car, Dumbbell, UtensilsCrossed, BedDouble, Check, ThumbsUp, ThumbsDown,
    ShoppingBag, Feather, Aperture, Map, Video, Mic, Image as ImageIcon, CheckSquare, Download,
    PlayCircle, ExternalLink
} from 'lucide-react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged, signOut, updateProfile } from 'firebase/auth';
import { getFirestore, doc, setDoc, getDoc } from 'firebase/firestore';

// --- Configuration ---
const apiKey = "";

// --- Firebase Configuration ---
const firebaseConfig = JSON.parse(__firebase_config || '{}');
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// --- Gemini API Helper ---
const callGemini = async (prompt, requireJson = false) => {
    try {
        const finalPrompt = requireJson
            ? `${prompt}\n\nIMPORTANT: You must return PURE VALID JSON only. Do not wrap in markdown blocks like \`\`\`json. No other text.`
            : prompt;

        const response = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{ parts: [{ text: finalPrompt }] }],
                    generationConfig: {
                        responseMimeType: requireJson ? "application/json" : "text/plain"
                    }
                })
            }
        );

        if (!response.ok) throw new Error('Gemini API Error');

        const data = await response.json();
        let text = data.candidates?.[0]?.content?.parts?.[0]?.text || "";

        // Clean up potential markdown formatting
        if (requireJson) {
            text = text.replace(/```json/g, '').replace(/```/g, '').trim();
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error("JSON Parse Failed", e);
                return null;
            }
        }

        return text;
    } catch (error) {
        console.error("Gemini Request Failed", error);
        return null;
    }
};

// --- Streaming Helper ---
const simulateStream = async (fullText, onChunk, onComplete) => {
    const chunkSize = 3;
    const delay = 20;

    let currentIndex = 0;

    const interval = setInterval(() => {
        if (currentIndex >= fullText.length) {
            clearInterval(interval);
            if (onComplete) onComplete();
            return;
        }

        const chunk = fullText.slice(currentIndex, currentIndex + chunkSize);
        onChunk(chunk);
        currentIndex += chunkSize;
    }, delay);

    return () => clearInterval(interval);
};

// --- Helper Functions ---

// Robust Copy Function with Fallback
const copyToClipboard = (text, onSuccess, onError) => {
    // Try Modern API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            if (onSuccess) onSuccess();
        }).catch(err => {
            console.warn('Clipboard API failed, trying fallback...', err);
            fallbackCopyTextToClipboard(text, onSuccess, onError);
        });
    } else {
        // Fallback for environments blocking Clipboard API
        fallbackCopyTextToClipboard(text, onSuccess, onError);
    }
}

const fallbackCopyTextToClipboard = (text, onSuccess, onError) => {
    try {
        const textArea = document.createElement("textarea");
        textArea.value = text;

        // Ensure it's not visible but part of DOM to satisfy execCommand requirements
        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);

        if (successful) {
            if (onSuccess) onSuccess();
        } else {
            throw new Error("execCommand returned false");
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        if (onError) onError();
    }
}

// --- Helper Components ---

const EnhancedMarkdown = ({ text }) => {
    if (typeof text !== 'string') return null; // Safety check
    const lines = text.split('\n');
    return (
        <div className="space-y-2 text-gray-300 leading-relaxed text-sm">
            {lines.map((line, i) => {
                if (line.startsWith('###')) return <h3 key={i} className="text-lg font-bold text-blue-300 mt-4 mb-2">{line.replace(/^###\s+/, '')}</h3>;
                if (line.trim().startsWith('*') || line.trim().startsWith('-')) return <li key={i} className="ml-4 list-disc text-gray-300">{line.replace(/^[\*\-]\s+/, '')}</li>;
                if (!line.trim()) return <div key={i} className="h-2" />;
                return <p key={i}>{line}</p>;
            })}
        </div>
    );
};

const ChatMessage = ({ role, content, isStreaming }) => {
    const isUser = role === 'user';
    return (
        <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
            {!isUser && (
                <div className={`w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 flex items-center justify-center mr-3 shadow-lg shadow-purple-500/30 flex-shrink-0 ${isStreaming ? 'animate-pulse ring-2 ring-purple-500/50' : ''}`}>
                    <Bot size={16} className="text-white" />
                </div>
            )}
            <div className={`max-w-[85%] rounded-2xl px-5 py-4 backdrop-blur-md shadow-sm ${isUser
                ? 'bg-blue-600/90 text-white rounded-br-none'
                : 'bg-white/10 text-gray-100 border border-white/10 rounded-bl-none'
                }`}>
                <div className="leading-relaxed text-sm md:text-base">
                    {isUser ? content : <EnhancedMarkdown text={content} />}
                    {!isUser && isStreaming && (
                        <span className="inline-block w-2 h-4 ml-1 bg-blue-400 animate-pulse align-middle rounded-sm"></span>
                    )}
                </div>
            </div>
            {isUser && (
                <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center ml-3 border border-gray-600 flex-shrink-0">
                    <User size={16} className="text-gray-300" />
                </div>
            )}
        </div>
    );
};

// --- Sub-View Components ---

const PlaylistView = ({ data }) => {
    const [copied, setCopied] = useState(false);

    if (!data) return <div className="text-center text-gray-500">无法获取歌单</div>;

    const handleCopyPlaylist = () => {
        // Format suitable for import in most music apps: "Title Artist"
        const text = data.songs.map(s => `${s.title} ${s.artist}`).join('\n');

        copyToClipboard(text, () => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }, () => {
            alert("复制失败，请手动选择文本复制");
        });
    };

    const openMusicSearch = (service, song) => {
        const query = encodeURIComponent(`${song.title} ${song.artist}`);
        let url = "";
        // Web versions of searches
        if (service === 'netease') url = `https://music.163.com/#/search/m/?s=${query}`;
        if (service === 'qq') url = `https://y.qq.com/n/ryqq/search?w=${query}`;
        window.open(url, '_blank');
    };

    return (
        <div className="space-y-6">
            <div className="bg-gradient-to-r from-violet-900/40 to-fuchsia-900/40 border border-violet-500/20 rounded-2xl p-6 relative overflow-hidden">
                <div className="relative z-10">
                    <h3 className="text-violet-200 font-bold text-lg mb-1">{data.vibe_title}</h3>
                    <p className="text-gray-400 text-sm">{data.vibe_desc}</p>
                    <button
                        onClick={handleCopyPlaylist}
                        className="mt-4 flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/10 px-3 py-1.5 rounded-lg text-xs text-white transition-all"
                    >
                        {copied ? <CheckCircle2 size={12} className="text-green-400" /> : <Copy size={12} />}
                        {copied ? "已复制导入文本" : "复制歌单 (可导入App)"}
                    </button>
                </div>
                <Music className="absolute right-4 bottom-4 text-violet-500/20 w-24 h-24 rotate-12" />
            </div>

            <div className="space-y-3">
                <div className="flex justify-between items-center px-1">
                    <h4 className="text-white font-semibold flex items-center gap-2"><Music size={18} className="text-violet-400" /> 推荐曲目</h4>
                </div>
                {data.songs.map((song, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-white/5 group">
                        <div className="w-8 h-8 bg-gray-800 rounded-lg flex items-center justify-center text-gray-500 font-bold text-xs group-hover:text-violet-400 transition-colors shrink-0">
                            {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-200 truncate text-sm">{song.title}</div>
                            <div className="text-xs text-gray-500 truncate">{song.artist}</div>
                        </div>

                        {/* Music Actions */}
                        <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                            <button
                                onClick={() => openMusicSearch('netease', song)}
                                className="px-2 py-1 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded text-[10px] border border-red-500/30 transition-colors font-medium"
                                title="网易云搜"
                            >
                                网易
                            </button>
                            <button
                                onClick={() => openMusicSearch('qq', song)}
                                className="px-2 py-1 bg-green-600/20 hover:bg-green-600/40 text-green-400 rounded text-[10px] border border-green-500/30 transition-colors font-medium"
                                title="QQ音乐搜"
                            >
                                QQ
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="text-[10px] text-gray-500 text-center mt-2">
                提示：点击“复制歌单”后，可在音乐App中选择“导入外部歌单”
            </div>
        </div>
    );
};

const BudgetView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">无法获取预算数据</div>;
    return (
        <div className="space-y-6">
            <div className="bg-gradient-to-r from-emerald-900/30 to-teal-900/30 border border-emerald-500/20 rounded-2xl p-6 text-center">
                <h3 className="text-gray-400 text-sm mb-1 uppercase tracking-wider">预估总花费 (不含大交通)</h3><div className="text-4xl font-bold text-white text-shadow-lg">{data.total_range}</div><div className="text-emerald-400 text-xs mt-2 flex items-center justify-center gap-1"><Sparkles size={12} /> 基于当前目的地物价估算</div>
            </div>
            <div className="space-y-3"><h4 className="text-white font-semibold flex items-center gap-2"><Banknote size={18} className="text-emerald-400" /> 费用明细</h4>{data.categories.map((cat, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 flex justify-between items-center"><div><div className="text-gray-200 font-medium">{cat.name}</div><div className="text-xs text-gray-500 mt-0.5">{cat.desc}</div></div><div className="text-emerald-300 font-mono font-bold">{cat.amount}</div></div>))}</div>
            <div className="bg-blue-900/10 border border-blue-500/10 p-4 rounded-xl"><h4 className="text-blue-300 font-bold mb-2 flex items-center gap-2 text-sm"><Zap size={14} /> 省钱小妙招</h4><p className="text-sm text-gray-300 leading-relaxed">{data.saving_tip}</p></div>
        </div>
    );
};

const EmergencyView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">无法获取紧急信息</div>;
    return (<div className="space-y-6"><div className="bg-red-900/20 border border-red-500/30 p-4 rounded-xl flex items-start gap-3"><AlertTriangle className="text-red-500 flex-shrink-0 mt-1" /><div><h4 className="text-red-400 font-bold mb-1">紧急提示</h4><p className="text-gray-300 text-sm">{data.embassy_tip || "遇到危险请立即联系当地警方或领事馆。"}</p></div></div><div className="grid grid-cols-2 gap-4">{Object.entries(data.local_numbers || {}).map(([key, num], i) => (<div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col items-center justify-center text-center"><div className="text-gray-400 text-xs uppercase mb-2 tracking-wider">{key}</div><div className="text-2xl font-bold text-white tracking-widest">{num}</div><button className="mt-2 text-xs bg-white/10 hover:bg-green-600 hover:text-white px-3 py-1 rounded-full transition-colors flex items-center gap-1"><Phone size={10} /> 呼叫</button></div>))}</div>{data.sos_card && (<div className="border-2 border-dashed border-white/20 rounded-xl p-6 bg-white/5 mt-4 text-center relative"><h4 className="text-gray-400 text-xs uppercase tracking-widest mb-4">SOS 求助卡 (请向路人出示)</h4><div className="text-3xl font-bold text-white mb-2">{data.sos_card.text_local}</div><div className="text-gray-400 text-sm mb-1">{data.sos_card.pronunciation}</div><div className="text-blue-400 text-sm font-medium">{data.sos_card.text_en}</div></div>)}</div>);
};
const CultureView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">无法获取文化信息</div>;
    return (<div className="space-y-6"><div className="space-y-3 animate-fadeIn"><h4 className="text-white font-semibold flex items-center gap-2"><Globe size={18} className="text-blue-400" /> 社交禁忌 & 礼仪</h4><div className="grid grid-cols-1 gap-3">{data.taboos.map((taboo, i) => (<div key={i} className="bg-red-900/10 border border-red-500/20 p-3 rounded-xl flex gap-3 items-start"><div className="bg-red-500/20 text-red-400 p-1 rounded-full mt-0.5"><X size={12} /></div><p className="text-sm text-gray-300">{taboo}</p></div>))}{data.etiquette && (<div className="bg-green-900/10 border border-green-500/20 p-3 rounded-xl flex gap-3 items-start"><div className="bg-green-500/20 text-green-400 p-1 rounded-full mt-0.5"><CheckCircle2 size={12} /></div><p className="text-sm text-gray-300">{data.etiquette}</p></div>)}</div></div><div className="space-y-3 animate-fadeIn" style={{ animationDelay: '100ms' }}><h4 className="text-white font-semibold flex items-center gap-2"><Languages size={18} className="text-yellow-400" /> 地道话术</h4><div className="grid grid-cols-1 gap-2">{data.phrases.map((p, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-3 flex justify-between items-center"><div><div className="text-white font-bold">{p.local}</div><div className="text-xs text-gray-500">{p.pronunciation}</div></div><div className="text-sm text-gray-300 text-right">{p.meaning}</div></div>))}</div></div></div>);
};
const SouvenirView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">无法获取购物建议</div>;
    return (<div className="space-y-6 animate-fadeIn"><div className="space-y-3"><h4 className="text-white font-semibold flex items-center gap-2"><ShoppingBag size={18} className="text-pink-400" /> 必买伴手礼</h4><div className="grid grid-cols-1 gap-3">{data.must_buy.map((item, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-3 flex justify-between items-center"><div><div className="text-white font-bold">{item.name}</div><div className="text-xs text-gray-400">{item.desc}</div></div><div className="bg-pink-500/10 text-pink-400 text-xs px-2 py-1 rounded">推荐</div></div>))}</div></div>{data.avoid && data.avoid.length > 0 && (<div className="space-y-3"><h4 className="text-white font-semibold flex items-center gap-2"><AlertTriangle size={18} className="text-red-400" /> 避坑指南 (不推荐)</h4><div className="grid grid-cols-1 gap-2">{data.avoid.map((item, i) => (<div key={i} className="bg-red-900/10 border border-red-500/20 p-3 rounded-xl text-gray-300 text-sm flex gap-2"><X size={16} className="text-red-400 mt-0.5 shrink-0" /> {item}</div>))}</div></div>)}</div>);
};
const PhotoChallengeView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">无法获取挑战任务</div>;
    return (
        <div className="space-y-6 animate-fadeIn">
            <div className="bg-indigo-900/20 border border-indigo-500/20 p-4 rounded-xl mb-4 text-center"><h4 className="text-indigo-300 font-bold mb-1 flex items-center justify-center gap-2 text-lg"><Aperture size={20} /> 城市探索者挑战</h4><p className="text-xs text-gray-400">用镜头捕捉城市的灵魂</p></div>
            <div className="grid grid-cols-1 gap-4">{data.challenges.map((c, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 flex gap-4 items-center group hover:bg-white/10 transition-all"><div className="w-12 h-12 rounded-full bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-xl font-bold border border-indigo-500/30 group-hover:scale-110 transition-transform">{i + 1}</div><div><div className="font-bold text-white text-lg mb-1">{c.title}</div><div className="text-sm text-gray-400">{c.desc}</div></div></div>))}</div>
        </div>
    );
};

const SocialCaptionsView = ({ captions }) => {
    const handleCopy = (text) => {
        copyToClipboard(text, () => {
            alert("文案已复制！");
        });
    };

    return (
        <div className="space-y-4 animate-fadeIn mt-6 pt-6 border-t border-white/10">
            <h3 className="flex items-center gap-2 text-pink-400 font-bold text-sm uppercase tracking-wide">
                <Share2 size={16} /> 朋友圈文案灵感
            </h3>
            <div className="grid grid-cols-1 gap-3">
                {captions.styles.map((style, i) => (
                    <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 relative group hover:bg-white/10 transition-colors">
                        <div className="text-[10px] text-gray-500 mb-2 uppercase border border-white/10 rounded px-1.5 py-0.5 w-fit">{style.name}</div>
                        <p className="text-gray-200 text-sm leading-relaxed font-light">{style.text}</p>
                        <button
                            onClick={() => handleCopy(style.text)}
                            className="absolute top-3 right-3 p-1.5 text-gray-500 hover:text-white bg-black/20 hover:bg-blue-600 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                            title="复制文案"
                        >
                            <Copy size={14} />
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

// --- Vlog Script View ---
const VlogScriptView = ({ data }) => {
    return (
        <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-4">
                <div className="inline-flex items-center justify-center p-2 bg-purple-500/20 rounded-full mb-2">
                    <Video size={24} className="text-purple-400" />
                </div>
                <h3 className="text-xl font-bold text-white">Vlog 拍摄脚本</h3>
                <p className="text-sm text-gray-400">{data.title}</p>
            </div>
            <div className="space-y-4">
                {data.shots.map((shot, i) => (
                    <div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4">
                        <div className="flex justify-between mb-2">
                            <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">Shot {i + 1} • {shot.duration}</span>
                            <span className="text-xs text-gray-500">{shot.angle}</span>
                        </div>
                        <p className="text-white font-medium mb-1">{shot.action}</p>
                        <p className="text-sm text-gray-400 italic">"{shot.audio}"</p>
                    </div>
                ))}
            </div>
            <div className="bg-purple-900/20 border border-purple-500/20 p-4 rounded-xl">
                <h4 className="text-sm font-bold text-purple-300 mb-1">配乐建议</h4>
                <p className="text-sm text-gray-300">{data.bgm}</p>
            </div>
        </div>
    );
};

// --- Share Poster View (Updated with Real HTML2Canvas) ---
const PosterView = ({ data }) => {
    const posterRef = useRef(null);
    const [isGenerating, setIsGenerating] = useState(false);

    const handleDownload = async () => {
        setIsGenerating(true);
        try {
            // Dynamically load html2canvas if not present
            if (!window.html2canvas) {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }

            const canvas = await window.html2canvas(posterRef.current, {
                useCORS: true,
                backgroundColor: null,
                scale: 2 // High res
            });

            const link = document.createElement('a');
            link.download = `TravelMind-${data.destination}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        } catch (error) {
            console.error("Poster generation failed", error);
            alert("海报生成失败，请稍后重试");
        }
        setIsGenerating(false);
    };

    return (
        <div className="flex flex-col items-center animate-fadeIn gap-4">
            {/* Poster Container */}
            <div ref={posterRef} className="w-full max-w-sm bg-gradient-to-br from-indigo-900 to-purple-900 border border-white/20 rounded-2xl overflow-hidden shadow-2xl relative aspect-[3/4] p-6 flex flex-col">
                <div className="absolute top-0 right-0 p-4 opacity-20">
                    <Sparkles size={100} className="text-white" />
                </div>
                <div className="relative z-10 flex-1 flex flex-col justify-between">
                    <div>
                        <h2 className="text-3xl font-black text-white tracking-tight mb-1">{data.destination}</h2>
                        <p className="text-indigo-200 text-sm uppercase tracking-widest">{data.days}</p>
                    </div>

                    <div className="space-y-4 my-6">
                        {data.highlights.map((h, i) => (
                            <div key={i} className="flex items-center gap-3">
                                <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                                <span className="text-white text-lg font-light">{h}</span>
                            </div>
                        ))}
                    </div>

                    <div className="mt-auto">
                        <div className="flex items-end justify-between">
                            <div>
                                <p className="text-xs text-indigo-300 mb-1">Generated by</p>
                                <div className="flex items-center gap-1.5">
                                    <div className="bg-white p-1 rounded-md"><Navigation size={12} className="text-indigo-900" /></div>
                                    <span className="font-bold text-white">TravelMind</span>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-xs text-indigo-300 mb-1">Budget Est.</p>
                                <p className="text-xl font-bold text-white">{data.budget}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <button
                onClick={handleDownload}
                disabled={isGenerating}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-full font-bold shadow-lg shadow-blue-600/30 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <Download size={18} />}
                {isGenerating ? "正在渲染..." : "保存海报到相册"}
            </button>
            <p className="text-center text-xs text-gray-500">使用 HTML2Canvas 技术生成</p>
        </div>
    );
};

// --- Activity Detail Modal ---

const ActivityDetailModal = ({ isOpen, onClose, activity, onSave, onEnrich, isEnriching, destination }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState(activity || {});
    const [activeTab, setActiveTab] = useState('overview');

    const [captions, setCaptions] = useState(null);
    const [story, setStory] = useState(null);
    const [reviews, setReviews] = useState(null);
    const [dishes, setDishes] = useState(null);
    const [directionCard, setDirectionCard] = useState(null);
    const [photoGuide, setPhotoGuide] = useState(null); // New: Photo Guide

    // Decoupled Loading States
    const [isGeneratingCaptions, setIsGeneratingCaptions] = useState(false);
    const [isTellingStory, setIsTellingStory] = useState(false);
    const [isRecommendingFood, setIsRecommendingFood] = useState(false);
    const [isGettingReviews, setIsGettingReviews] = useState(false);
    const [isGettingDirection, setIsGettingDirection] = useState(false);
    const [isGettingPhotoGuide, setIsGettingPhotoGuide] = useState(false);

    const prevTitleRef = useRef(null);

    useEffect(() => {
        if (activity) {
            if (activity.title !== prevTitleRef.current) {
                setFormData(activity);
                setIsEditing(false);
                setCaptions(null);
                setStory(null);
                setReviews(null);
                setDishes(null);
                setDirectionCard(null);
                setPhotoGuide(null);
                setActiveTab('overview');
                prevTitleRef.current = activity.title;
            } else {
                setFormData(prev => ({ ...prev, ...activity }));
            }
        }
    }, [activity]);

    if (!isOpen || !activity) return null;

    const isHotel = activity.type === 'hotel';
    const isFood = activity.type === 'food';

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSave = () => {
        onSave(formData);
        setIsEditing(false);
    };

    const handleGenerateCaptions = async () => {
        setIsGeneratingCaptions(true);
        const prompt = `Generate 3 distinct social media captions (Chinese) for "${activity.title}". Return JSON: { "styles": [{ "name": "文艺风", "text": "..." }, ...] }`;
        const data = await callGemini(prompt, true);
        setCaptions(data);
        setIsGeneratingCaptions(false);
    };

    const handleTellStory = async () => {
        setIsTellingStory(true);
        const prompt = `Tell a short, fascinating legend or anecdote about "${activity.title}". Target: Tourists. Language: Chinese. Length: <150 words. Return text string.`;
        const text = await callGemini(prompt, false);
        setStory(text);
        setIsTellingStory(false);
    };

    const handleRecommendDishes = async () => {
        setIsRecommendingFood(true);
        const prompt = `What to order at "${activity.title}" in ${destination}? Return JSON: { "dishes": [{"name": "Dish", "desc": "Taste"}], "ordering_tip": "Tip" }`;
        const data = await callGemini(prompt, true);
        setDishes(data);
        setIsRecommendingFood(false);
    };

    const handleGenerateReviews = async () => {
        setIsGettingReviews(true);
        const prompt = `Generate realistic reviews for hotel "${activity.title}". Return JSON: { "score": 4.8, "total_reviews": 1240, "pros": ["Clean"], "cons": ["Small"], "recent_reviews": [{"user": "A", "rating": 5, "comment": "Good"}] }`;
        const data = await callGemini(prompt, true);
        setReviews(data);
        setIsGettingReviews(false);
    };

    const handleGetDirectionCard = async () => {
        setIsGettingDirection(true);
        const prompt = `I need to go to "${activity.title}" in ${destination}. Translate "Please take me to [Place]" into local language. Return JSON: { "local_text": "...", "pronunciation": "...", "address": "..." }`;
        const data = await callGemini(prompt, true);
        setDirectionCard(data);
        setIsGettingDirection(false);
    };

    // New: Photo Guide
    const handleGetPhotoGuide = async () => {
        setIsGettingPhotoGuide(true);
        const prompt = `
      Provide photography advice for "${activity.title}". 
      Return JSON: { "best_time": "e.g. Sunset", "best_angle": "e.g. From the bridge", "composition_tip": "..." }
    `;
        const data = await callGemini(prompt, true);
        setPhotoGuide(data);
        setIsGettingPhotoGuide(false);
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
            <div className="bg-[#1a1d2d] border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Cover Image */}
                <div className="h-56 relative overflow-hidden group">
                    <img src={activity.image || `https://source.unsplash.com/800x400/?${activity.type},travel,${activity.title}`} className="w-full h-full object-cover" alt={activity.title} />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#1a1d2d] via-transparent to-transparent"></div>
                    {isHotel && (<div className="absolute bottom-4 right-4 flex gap-2">{[1, 2, 3].map(i => (<div key={i} className="w-12 h-12 rounded-lg border-2 border-white/50 overflow-hidden bg-black/50 backdrop-blur cursor-pointer hover:border-white transition-all"><img src={`https://source.unsplash.com/100x100/?hotel,interior,${i}`} className="w-full h-full object-cover" /></div>))}<div className="w-12 h-12 rounded-lg border-2 border-white/50 bg-black/60 backdrop-blur flex items-center justify-center text-xs text-white font-bold cursor-pointer">+24</div></div>)}
                    <button onClick={onClose} className="absolute top-4 right-4 bg-black/40 hover:bg-black/60 text-white p-2 rounded-full backdrop-blur-md transition-all"><X size={20} /></button>
                </div>

                {/* Content Body */}
                <div className="flex flex-col flex-1 overflow-hidden bg-[#1a1d2d]">
                    <div className="px-6 pt-6 pb-2">
                        <div className="flex justify-between items-start">
                            <div>
                                <h2 className="text-2xl font-bold text-white mb-1 flex items-center gap-2">{formData.title} {isHotel && <div className="flex text-yellow-400"><Star size={16} fill="currentColor" /><Star size={16} fill="currentColor" /><Star size={16} fill="currentColor" /><Star size={16} fill="currentColor" /><Star size={16} fill="currentColor" /></div>}</h2>
                                <div className="flex items-center gap-2 text-gray-400 text-sm mt-1">
                                    <MapPin size={14} /> <span>{destination}市中心区域</span>
                                    <button onClick={handleGetDirectionCard} disabled={isGettingDirection} className="ml-2 flex items-center gap-1 text-xs bg-blue-600/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 hover:bg-blue-600/40 transition-colors disabled:opacity-50">
                                        {isGettingDirection ? <Loader2 size={12} className="animate-spin" /> : <Car size={12} />} 打车/问路
                                    </button>
                                </div>
                            </div>
                            <div className="text-right"><div className="text-2xl font-bold text-blue-400">{formData.price || formData.time}</div>{isHotel && <div className="text-xs text-gray-500">起/晚 (含税)</div>}</div>
                        </div>
                        {isHotel && (<div className="flex gap-6 mt-6 border-b border-white/10">{['overview', 'reviews', 'rooms'].map(tab => (<button key={tab} onClick={() => setActiveTab(tab)} className={`pb-3 text-sm font-medium transition-colors relative ${activeTab === tab ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>{tab === 'overview' ? '概况 & 设施' : tab === 'reviews' ? '住客评价' : '房型预订'}{activeTab === tab && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 rounded-t-full"></div>}</button>))}</div>)}
                    </div>

                    <div className="flex-1 overflow-y-auto custom-scrollbar p-6">

                        {/* Direction Card Overlay */}
                        {directionCard && (
                            <div className="mb-6 bg-blue-600 rounded-xl p-6 text-white relative overflow-hidden shadow-lg animate-fadeIn">
                                <div className="absolute top-0 right-0 p-4 opacity-10"><Map size={120} /></div>
                                <h3 className="text-xs uppercase tracking-widest opacity-80 mb-4">请带我去 / Please take me to</h3>
                                <div className="text-3xl font-bold mb-2">{directionCard.local_text}</div>
                                <div className="text-lg opacity-80 mb-4">{activity.title}</div>
                                <div className="bg-black/20 rounded-lg p-3 text-sm flex gap-3">
                                    <MapPin size={16} className="shrink-0 mt-0.5" />
                                    <div>
                                        <div>{directionCard.address}</div>
                                        <div className="opacity-60 text-xs mt-1">发音: {directionCard.pronunciation}</div>
                                    </div>
                                </div>
                                <button onClick={() => setDirectionCard(null)} className="absolute top-2 right-2 p-1 hover:bg-white/20 rounded"><X size={16} /></button>
                            </div>
                        )}

                        {activeTab === 'overview' && (
                            <div className="space-y-6 animate-fadeIn">
                                {isHotel && (<div><h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">热门设施</h3><div className="grid grid-cols-4 gap-4">{[{ icon: Wifi, label: "免费WiFi" }, { icon: Waves, label: "游泳池" }, { icon: Car, label: "免费停车" }, { icon: Dumbbell, label: "健身房" }, { icon: UtensilsCrossed, label: "餐厅" }, { icon: Coffee, label: "咖啡厅" }].map((fac, i) => (<div key={i} className="flex flex-col items-center gap-2 p-3 bg-white/5 rounded-xl border border-white/5"><fac.icon size={20} className="text-gray-300" /><span className="text-xs text-gray-400">{fac.label}</span></div>))}</div></div>)}
                                <div><h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">简介</h3><p className="text-gray-300 leading-relaxed text-sm">{activity.desc}</p></div>

                                {/* --- Dynamic AI Feature Block --- */}
                                {!isHotel && (
                                    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 rounded-2xl p-1 border border-blue-500/20">
                                        <div className="bg-[#1a1d2d]/80 backdrop-blur rounded-xl p-5">
                                            {/* Header */}
                                            <div className="flex justify-between items-center mb-4">
                                                <h3 className="flex items-center gap-2 text-blue-300 font-bold"><Sparkles size={18} />
                                                    {isFood ? "美食推荐" : "景点百科"}
                                                </h3>
                                                <div className="flex gap-2">
                                                    {/* Buttons */}
                                                    {!activity.details && !isEnriching && (
                                                        <button onClick={onEnrich} className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"><Info size={14} /> 详情</button>
                                                    )}

                                                    {!isFood && !story && !isTellingStory && (
                                                        <button onClick={handleTellStory} className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/80 hover:bg-amber-500 text-white rounded-lg transition-colors"><BookOpen size={14} /> 讲故事</button>
                                                    )}

                                                    {!isFood && !photoGuide && !isGettingPhotoGuide && (
                                                        <button onClick={handleGetPhotoGuide} className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-pink-600/80 hover:bg-pink-500 text-white rounded-lg transition-colors"><Camera size={14} /> 摄影指导</button>
                                                    )}

                                                    {isFood && !dishes && !isRecommendingFood && (
                                                        <button onClick={handleRecommendDishes} className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-orange-600/80 hover:bg-orange-500 text-white rounded-lg transition-colors"><Utensils size={14} /> 必点菜</button>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Content Display Area */}
                                            <div className="space-y-4">
                                                {/* 1. Details Section */}
                                                {isEnriching ? (
                                                    <div className="flex items-center gap-2 text-blue-400 text-xs py-2"><Loader2 size={14} className="animate-spin" /> 正在查询详情...</div>
                                                ) : activity.details && (
                                                    <div className="grid grid-cols-2 gap-4 animate-fadeIn border-b border-white/5 pb-4 last:border-0 last:pb-0">
                                                        <div className="bg-white/5 p-3 rounded-lg"><div className="text-xs text-gray-500 mb-1">开放时间</div><div className="text-sm text-gray-200">{activity.details.opening_hours}</div></div>
                                                        <div className="bg-white/5 p-3 rounded-lg"><div className="text-xs text-gray-500 mb-1">门票/价格</div><div className="text-sm text-gray-200">{activity.details.ticket_price}</div></div>
                                                    </div>
                                                )}

                                                {/* 2. Story Section */}
                                                {isTellingStory ? (
                                                    <div className="flex items-center gap-2 text-amber-400 text-xs py-2"><Loader2 size={14} className="animate-spin" /> 正在生成故事...</div>
                                                ) : story && (
                                                    <div className="bg-amber-900/20 border border-amber-500/20 rounded-xl p-4 animate-fadeIn border-b border-white/5 last:border-0">
                                                        <Quote className="text-amber-500/40 w-6 h-6 mb-2" />
                                                        <p className="text-gray-200 text-sm leading-relaxed italic">{story}</p>
                                                    </div>
                                                )}

                                                {/* 3. Photo Guide Section */}
                                                {isGettingPhotoGuide ? (
                                                    <div className="flex items-center gap-2 text-pink-400 text-xs py-2"><Loader2 size={14} className="animate-spin" /> 正在分析摄影机位...</div>
                                                ) : photoGuide && (
                                                    <div className="bg-pink-900/20 border border-pink-500/20 rounded-xl p-4 animate-fadeIn flex gap-4">
                                                        <Camera size={24} className="text-pink-400 shrink-0 mt-1" />
                                                        <div>
                                                            <div className="text-sm font-bold text-white mb-1">最佳拍摄建议</div>
                                                            <div className="text-xs text-gray-300">⏰ {photoGuide.best_time}</div>
                                                            <div className="text-xs text-gray-300">📐 {photoGuide.best_angle}</div>
                                                            <div className="text-xs text-gray-400 mt-1 italic">{photoGuide.composition_tip}</div>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* 4. Food Section */}
                                                {isRecommendingFood ? (
                                                    <div className="flex items-center gap-2 text-orange-400 text-xs py-2"><Loader2 size={14} className="animate-spin" /> 正在推荐菜品...</div>
                                                ) : dishes && (
                                                    <div className="animate-fadeIn space-y-3">
                                                        {dishes.dishes.map((d, i) => (
                                                            <div key={i} className="flex gap-3 items-start bg-white/5 p-3 rounded-lg">
                                                                <div className="bg-orange-500/20 text-orange-400 w-6 h-6 rounded flex items-center justify-center text-xs font-bold shrink-0">{i + 1}</div>
                                                                <div><div className="text-sm font-bold text-white">{d.name}</div><div className="text-xs text-gray-400">{d.desc}</div></div>
                                                            </div>
                                                        ))}
                                                        <div className="text-xs text-orange-300 mt-2 flex items-center gap-1"><Zap size={12} /> {dishes.ordering_tip}</div>
                                                    </div>
                                                )}

                                                {/* Empty State */}
                                                {!activity.details && !story && !dishes && !photoGuide && !isEnriching && !isTellingStory && !isRecommendingFood && !isGettingPhotoGuide && (
                                                    <div className="text-center py-4 text-gray-500 text-xs">点击上方按钮，获取更多智能信息</div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* ... Reviews & Rooms Tabs (kept same) ... */}
                        {activeTab === 'rooms' && (<div className="space-y-4 animate-fadeIn">{[{ name: "豪华大床房", size: "35㎡", bed: "1张特大床", price: "¥899", tags: ["含早", "免费取消"] }, { name: "行政双床房", size: "42㎡", bed: "2张单人床", price: "¥1099", tags: ["含早", "行政礼遇"] }, { name: "全景套房", size: "60㎡", bed: "1张特大床", price: "¥1899", tags: ["含早", "湖景", "延迟退房"] }].map((room, i) => (<div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 flex gap-4"><div className="w-24 h-24 bg-gray-800 rounded-lg flex-shrink-0 overflow-hidden"><img src={`https://source.unsplash.com/200x200/?hotel,room,${i}`} className="w-full h-full object-cover" /></div><div className="flex-1"><div className="flex justify-between items-start"><h4 className="font-bold text-white text-lg">{room.name}</h4><div className="text-right"><div className="text-xl font-bold text-blue-400">{room.price}</div><button className="mt-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors">预订</button></div></div><div className="text-sm text-gray-400 flex items-center gap-3 mt-1"><span>{room.size}</span> <span className="w-1 h-1 bg-gray-600 rounded-full"></span> <span className="flex items-center gap-1"><BedDouble size={14} /> {room.bed}</span></div><div className="flex gap-2 mt-3">{room.tags.map(tag => <span key={tag} className="text-xs text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">{tag}</span>)}</div></div></div>))}</div>)}
                        {activeTab === 'reviews' && (<div className="space-y-6 animate-fadeIn">{!reviews ? (<div className="text-center py-10"><div className="mb-4 text-gray-400 text-sm">想知道大家怎么评价这家酒店？<br />让 AI 为您汇总全网真实口碑。</div><button onClick={handleGenerateReviews} disabled={isGettingReviews} className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 rounded-full text-white font-medium flex items-center gap-2 mx-auto hover:scale-105 transition-transform">{isGettingReviews ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />} 生成口碑总结</button></div>) : (<><div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl"><div className="text-center px-4 border-r border-white/10"><div className="text-3xl font-bold text-white">{reviews.score}</div><div className="text-xs text-gray-400">/ 5.0</div></div><div className="flex-1"><div className="flex gap-2 mb-2"><div className="bg-green-500/10 text-green-400 px-2 py-1 rounded text-xs border border-green-500/20 flex items-center gap-1"><ThumbsUp size={12} /> 优点：{reviews.pros.join('、')}</div></div><div className="flex gap-2"><div className="bg-red-500/10 text-red-400 px-2 py-1 rounded text-xs border border-red-500/20 flex items-center gap-1"><ThumbsDown size={12} /> 缺点：{reviews.cons.join('、')}</div></div></div></div><div className="space-y-4">{reviews.recent_reviews.map((r, i) => (<div key={i} className="border-b border-white/5 pb-4 last:border-0"><div className="flex justify-between items-center mb-1"><div className="font-bold text-gray-300 text-sm">{r.user}</div><div className="flex text-yellow-500 text-xs">{"★".repeat(r.rating)}</div></div><p className="text-gray-400 text-sm">{r.comment}</p></div>))}</div></>)}</div>)}
                    </div>

                    {!isHotel && !captions && (<div className="p-4 border-t border-white/10 flex justify-center"><button onClick={handleGenerateCaptions} disabled={isGeneratingCaptions} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white rounded-full font-medium transition-all hover:scale-105 disabled:opacity-50 text-sm">{isGeneratingCaptions ? <Loader2 size={16} className="animate-spin" /> : <Share2 size={16} />}{isGeneratingCaptions ? "正在生成..." : "✨ 生成发圈文案"}</button></div>)}
                    {captions && (<div className="p-4 border-t border-white/10 max-h-48 overflow-y-auto"><SocialCaptionsView captions={captions} /></div>)}
                </div>
            </div>
        </div>
    );
};

// ... ItineraryTimeline, TipsView, PackingList kept same ...
const ItineraryTimeline = ({ days, onGetTips, onActivityClick, onGetDiary, onToggleCheckIn, onGenerateVlog }) => {
    if (!days || days.length === 0) return <div className="flex flex-col items-center justify-center py-20 text-gray-500"><Sparkles size={48} className="mb-4 opacity-20" /><p>暂无行程，请在左侧告诉 AI 您的旅行计划</p></div>;
    return (
        <div className="space-y-8 animate-fadeIn">
            {days.map((day, dayIdx) => (
                <div key={dayIdx} className="relative pl-6 border-l-2 border-white/10 pb-2">
                    <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-blue-500 ring-4 ring-gray-900/50"></div>
                    <div className="mb-6 flex justify-between items-start">
                        <div><h3 className="text-lg lg:text-xl font-bold text-white mb-1 flex items-center gap-2"><span className="text-blue-400">Day {day.day}</span> {day.title}</h3><div className="text-gray-400 text-xs lg:text-sm flex items-center gap-2"><Calendar size={14} /> 第 {day.day} 天</div></div>
                        <div className="flex gap-2">
                            <button onClick={() => onGenerateVlog(day)} className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white" title="生成 Vlog 脚本"><Video size={14} className="text-purple-400" /><span>脚本</span></button>
                            <button onClick={() => onGetDiary(day)} className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white" title="生成日记"><Feather size={14} className="text-pink-400" /><span>日记</span></button>
                            <button onClick={() => onGetTips(day)} className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white"><Lightbulb size={14} className="text-yellow-500" /><span>AI 攻略</span></button>
                        </div>
                    </div>
                    <div className="space-y-3">
                        {day.activities.map((act, actIdx) => {
                            const isChecked = act.checked;
                            return (
                                <div key={actIdx} className={`bg-white/5 border border-white/10 rounded-xl p-3 lg:p-4 hover:bg-white/10 hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-900/10 hover:-translate-y-0.5 transition-all cursor-pointer group relative active:scale-[0.99] active:bg-white/5 ${isChecked ? 'opacity-60 grayscale' : ''}`}>
                                    <div className="absolute top-4 right-4 flex gap-2">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onToggleCheckIn(dayIdx, actIdx); }}
                                            className={`p-1.5 rounded-full transition-colors ${isChecked ? 'text-green-400 bg-green-900/30' : 'text-gray-600 hover:text-green-400 hover:bg-green-900/20'}`}
                                            title="打卡"
                                        >
                                            {isChecked ? <CheckSquare size={18} /> : <CheckCircle2 size={18} />}
                                        </button>
                                        <div className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"><ChevronRight size={18} /></div>
                                    </div>
                                    <div className="flex items-start gap-3 lg:gap-4" onClick={() => onActivityClick(dayIdx, actIdx, act)}>
                                        <div className="mt-1 p-2 rounded-lg bg-gray-800 text-blue-400 group-hover:scale-110 transition-transform shrink-0">{act.type === 'food' ? <Coffee size={16} /> : act.type === 'hotel' ? <Hotel size={16} /> : <MapPin size={16} />}</div>
                                        <div className="flex-1 min-w-0 pr-10">
                                            <div className="flex justify-between items-start flex-wrap gap-2">
                                                <h4 className={`font-semibold text-gray-200 truncate pr-2 group-hover:text-blue-300 transition-colors ${isChecked ? 'line-through text-gray-500' : ''}`}>{act.title}</h4>
                                                <span className="text-xs font-mono text-gray-500 bg-gray-800 px-2 py-0.5 rounded whitespace-nowrap">{act.time}</span>
                                            </div>
                                            <p className="text-xs lg:text-sm text-gray-400 mt-1 line-clamp-2">{act.desc}</p>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
};

const TipsView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">数据加载失败</div>;
    return (
        <div className="space-y-6">
            {data.photo_spots && data.photo_spots.length > 0 && (<div className="animate-fadeIn"><h4 className="flex items-center gap-2 text-pink-400 font-bold mb-3 text-lg"><Camera size={20} /> 最佳出片机位</h4><div className="grid grid-cols-1 gap-3">{data.photo_spots.map((spot, i) => (<div key={i} className="bg-white/5 border border-white/10 rounded-xl p-3 flex gap-3"><div className="bg-pink-500/20 text-pink-400 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-xs">{i + 1}</div><div><div className="text-white font-medium">{spot.name}</div><div className="text-xs text-gray-400 mt-1">{spot.desc}</div></div></div>))}</div></div>)}
            {data.warnings && data.warnings.length > 0 && (<div className="animate-fadeIn" style={{ animationDelay: '100ms' }}><h4 className="flex items-center gap-2 text-yellow-400 font-bold mb-3 text-lg"><AlertTriangle size={20} /> 避坑指南</h4><div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 space-y-3">{data.warnings.map((warn, i) => (<div key={i} className="flex gap-2 text-sm text-gray-200"><AlertTriangle size={14} className="text-yellow-500 mt-0.5 flex-shrink-0" /><span>{warn}</span></div>))}</div></div>)}
            {data.food && data.food.length > 0 && (<div className="animate-fadeIn" style={{ animationDelay: '200ms' }}><h4 className="flex items-center gap-2 text-orange-400 font-bold mb-3 text-lg"><Utensils size={20} /> 美食推荐</h4><div className="flex flex-wrap gap-2">{data.food.map((f, i) => (<span key={i} className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-orange-200">{f}</span>))}</div></div>)}
            {data.transport && (<div className="animate-fadeIn" style={{ animationDelay: '300ms' }}><h4 className="flex items-center gap-2 text-blue-400 font-bold mb-2 text-lg"><Navigation size={20} /> 交通建议</h4><p className="text-sm text-gray-300 bg-blue-500/10 border border-blue-500/20 p-3 rounded-xl">{data.transport}</p></div>)}
        </div>
    );
};
const PackingList = ({ data }) => {
    const [checkedItems, setCheckedItems] = useState({});
    const toggleItem = (catIdx, itemIdx) => { const key = `${catIdx}-${itemIdx}`; setCheckedItems(prev => ({ ...prev, [key]: !prev[key] })); };
    if (!data || !data.categories) return <div className="text-gray-400 text-center">数据解析失败</div>;
    return (
        <div className="space-y-6">
            {data.special_tips && (<div className="bg-blue-900/20 border border-blue-500/20 p-4 rounded-xl mb-4"><h4 className="text-blue-300 font-bold mb-2 flex items-center gap-2"><Sparkles size={16} /> AI 特别提醒</h4><EnhancedMarkdown text={data.special_tips} /></div>)}
            {data.categories.map((cat, catIdx) => (
                <div key={catIdx} className="animate-fadeIn" style={{ animationDelay: `${catIdx * 100}ms` }}><h4 className="text-white font-semibold mb-3 border-l-4 border-purple-500 pl-3">{cat.name}</h4><div className="grid grid-cols-1 gap-3">{cat.items.map((item, itemIdx) => { const isChecked = checkedItems[`${catIdx}-${itemIdx}`]; return (<div key={itemIdx} onClick={() => toggleItem(catIdx, itemIdx)} className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${isChecked ? 'bg-green-900/10 border-green-500/30' : 'bg-white/5 border-white/5 hover:bg-white/10'}`}><div className={`mt-0.5 transition-colors ${isChecked ? 'text-green-500' : 'text-gray-500'}`}>{isChecked ? <CheckCircle2 size={20} /> : <Circle size={20} />}</div><div className="flex-1"><div className={`font-medium text-sm transition-all ${isChecked ? 'text-gray-500 line-through' : 'text-gray-200'}`}>{item.name}</div>{item.reason && (<div className="text-xs text-gray-500 mt-1">{item.reason}</div>)}</div></div>); })}</div></div>
            ))}
        </div>
    );
};

// --- Gemini Modal Updated to support Budget, Playlist, Emergency, Culture, Souvenirs, Diary, Photo Challenge, Vlog, Poster ---
const GeminiModal = ({ isOpen, onClose, title, content, contentType, isLoading, onRegenerate }) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
            <div className="bg-[#1a1d2d] border border-white/10 rounded-2xl w-full max-w-md md:max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
                <div className="p-4 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-blue-900/30 to-purple-900/30"><h3 className="text-lg font-bold text-white flex items-center gap-2 truncate pr-2">
                    {contentType === 'packing' ? <Backpack size={18} className="text-emerald-400 flex-shrink-0" /> :
                        contentType === 'budget' ? <Banknote size={18} className="text-emerald-400 flex-shrink-0" /> :
                            contentType === 'playlist' ? <Music size={18} className="text-violet-400 flex-shrink-0" /> :
                                contentType === 'emergency' ? <Siren size={18} className="text-red-500 flex-shrink-0" /> :
                                    contentType === 'culture' ? <Globe size={18} className="text-blue-400 flex-shrink-0" /> :
                                        contentType === 'souvenirs' ? <ShoppingBag size={18} className="text-pink-400 flex-shrink-0" /> :
                                            contentType === 'diary' ? <Feather size={18} className="text-white flex-shrink-0" /> :
                                                contentType === 'photo_challenge' ? <Aperture size={18} className="text-indigo-400 flex-shrink-0" /> :
                                                    contentType === 'vlog' ? <Video size={18} className="text-purple-400 flex-shrink-0" /> :
                                                        contentType === 'poster' ? <ImageIcon size={18} className="text-indigo-400 flex-shrink-0" /> :
                                                            <Sparkles size={18} className="text-blue-400 flex-shrink-0" />}{title}</h3><div className="flex items-center gap-2 flex-shrink-0">{!isLoading && (<button onClick={onRegenerate} title="重新生成" className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors flex items-center gap-1 text-xs"><RefreshCw size={14} /><span className="hidden sm:inline">重新生成</span></button>)}<button onClick={onClose} className="text-gray-400 hover:text-white transition-colors p-1.5 hover:bg-white/10 rounded-full"><X size={20} /></button></div></div>
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1 bg-[#131520]">
                    {isLoading ? (<div className="flex flex-col items-center justify-center py-12 gap-4"><Loader2 size={32} className="text-blue-500 animate-spin" /><p className="text-sm text-blue-300 animate-pulse">AI 正在为您精心定制内容...</p></div>) : (
                        <>
                            {contentType === 'packing' ? <PackingList data={content} /> :
                                contentType === 'tips' ? <TipsView data={content} /> :
                                    contentType === 'budget' ? <BudgetView data={content} /> :
                                        contentType === 'playlist' ? <PlaylistView data={content} /> :
                                            contentType === 'emergency' ? <EmergencyView data={content} /> :
                                                contentType === 'culture' ? <CultureView data={content} /> :
                                                    contentType === 'souvenirs' ? <SouvenirView data={content} /> :
                                                        contentType === 'photo_challenge' ? <PhotoChallengeView data={content} /> :
                                                            contentType === 'vlog' ? <VlogScriptView data={content} /> :
                                                                contentType === 'poster' ? <PosterView data={content} /> :
                                                                    <EnhancedMarkdown text={content} />}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- Main App Component ---

export default function TravelMindApp() {
    const [user, setUser] = useState(null);
    const [loadingAuth, setLoadingAuth] = useState(true);

    // App Data State
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([
        { role: 'ai', content: '你好！我是 TravelMind。你的智能行程管家。\n\n请告诉我你想去哪里，玩几天？\n例如："帮我规划一个北京4天3晚的亲子游，想去环球影城"', isStreaming: false }
    ]);
    const [isTyping, setIsTyping] = useState(false);

    const [activeTab, setActiveTab] = useState('itinerary');
    const [mobileView, setMobileView] = useState('chat');

    const [itineraryData, setItineraryData] = useState([]);
    const [poiData, setPoiData] = useState([]);
    const [destination, setDestination] = useState("未知目的地");
    const [tripStatus, setTripStatus] = useState("Planning");
    const [weather, setWeather] = useState({ temp: "--", condition: "未知" });

    // Cache State
    const [packingListData, setPackingListData] = useState(null);
    const [budgetData, setBudgetData] = useState(null);
    const [playlistData, setPlaylistData] = useState(null);
    const [emergencyData, setEmergencyData] = useState(null);
    const [cultureData, setCultureData] = useState(null);
    const [souvenirData, setSouvenirData] = useState(null);
    const [photoChallengeData, setPhotoChallengeData] = useState(null);
    const [posterData, setPosterData] = useState(null);

    // Modals State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalTitle, setModalTitle] = useState('');
    const [modalContent, setModalContent] = useState(null);
    const [modalContentType, setModalContentType] = useState('text');
    const [isGeminiLoading, setIsGeminiLoading] = useState(false);
    const [currentDayForTip, setCurrentDayForTip] = useState(null);

    // Activity Detail State
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [selectedActivity, setSelectedActivity] = useState(null);
    const [selectedActivityPath, setSelectedActivityPath] = useState(null); // { type: 'itinerary' | 'poi', dayIdx/index, actIdx }
    const [isActivityEnriching, setIsActivityEnriching] = useState(false);

    // Voice Interaction State
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);

    const messagesEndRef = useRef(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
            setUser(currentUser);
            setLoadingAuth(false);
        });
        return () => unsubscribe();
    }, []);

    const handleLogin = async () => {
        try {
            setLoadingAuth(true);
            await signInAnonymously(auth);
        } catch (error) {
            console.error("Login failed", error);
            setLoadingAuth(false);
        }
    };

    const handleLogout = async () => await signOut(auth);
    const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

    // Auto scroll logic for streaming
    useEffect(scrollToBottom, [messages, isTyping]);

    const handleSend = async () => {
        if (!input.trim()) return;
        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg, isStreaming: false }]);
        setIsTyping(true);

        const prompt = `
      User Request: "${userMsg}"
      Current Context: Destination is ${destination}.
      
      You are an expert travel agent "TravelMind". 
      
      **CRITICAL INSTRUCTION ON MISSING INFO:**
      - If the user DOES NOT specify a date, assume "next weekend" or "the coming optimal travel season" for that city.
      - If the user DOES NOT specify a budget, assume "Moderate/Comfortable" level.
      - **IMPORTANT:** In your "chat_response", explicitly mention these assumptions. (e.g., "I've planned this for next week assuming clear weather...", "Selected comfortable hotels for you...").
      
      Please provide a response in JSON format containing:
      1. "chat_response": A friendly, natural text response (Chinese). Explain your assumptions here if any.
      2. "destination_detected": The city name if detected (e.g. "杭州"), else keep null.
      3. "status_update": "Created" if a valid plan is generated, else "Planning".
      4. "weather_forecast": { "temp": "e.g. 20°C", "condition": "e.g. Sunny" } estimated based on the assumed date.
      5. "itinerary": An array of objects for a travel plan. Format: [{day: 1, title: "Theme", activities: [{time: "09:00", title: "Place", type: "sight/food", desc: "Short desc", checked: false}]}].
      6. "pois": An array of recommended hotels/places based on the assumed budget. Format: [{name: "Name", type: "hotel", price: "Price", tags: ["Tag1"], rating: 4.8}].
    `;

        const data = await callGemini(prompt, true);
        setIsTyping(false);

        if (data) {
            const chatText = data.chat_response || "收到！";
            setMessages(prev => [...prev, { role: 'ai', content: "", isStreaming: true }]);

            simulateStream(chatText, (chunk) => {
                setMessages(prev => {
                    const last = prev[prev.length - 1];
                    if (last.role === 'ai' && last.isStreaming) {
                        const newContent = last.content + chunk;
                        return [...prev.slice(0, -1), { ...last, content: newContent }];
                    }
                    return prev;
                });
            }, () => {
                setMessages(prev => {
                    const last = prev[prev.length - 1];
                    return [...prev.slice(0, -1), { ...last, isStreaming: false }];
                });

                if (data.destination_detected) setDestination(data.destination_detected);
                if (data.status_update) setTripStatus(data.status_update);
                if (data.weather_forecast) setWeather(data.weather_forecast);

                if (data.itinerary && data.itinerary.length > 0) {
                    setItineraryData(data.itinerary);
                    setPackingListData(null);
                    setBudgetData(null);
                    setPlaylistData(null);
                    setEmergencyData(null);
                    setCultureData(null);
                    setSouvenirData(null);
                    setPhotoChallengeData(null);
                    setPosterData(null);
                    setActiveTab('itinerary');
                    if (window.innerWidth < 1024) setMobileView('dashboard');
                }
                if (data.pois && data.pois.length > 0) setPoiData(data.pois);
            });

        } else {
            setMessages(prev => [...prev, { role: 'ai', content: "网络开小差了，请重试一下。", isStreaming: false }]);
        }
    };

    // --- Features Handlers ---

    const handleGetDayTips = async (day, forceRegenerate = false) => {
        setCurrentDayForTip(day);
        setModalTitle(`${day.title} - AI 攻略`);
        setModalContentType('tips');
        setIsModalOpen(true);

        if (!forceRegenerate && day.cachedTips) {
            setModalContent(day.cachedTips);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Target: ${destination} - ${day.title}.
      Activities: ${day.activities.map(a => a.title).join(', ')}.
      Return JSON tips (Chinese): { "photo_spots": [{"name":"", "desc":""}], "warnings": [], "food": [], "transport": "" }
    `;
        const data = await callGemini(prompt, true);

        if (data) {
            const updatedItinerary = itineraryData.map(d => d.day === day.day ? { ...d, cachedTips: data } : d);
            setItineraryData(updatedItinerary);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("AI 攻略生成失败，请稍后重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleGeneratePackingList = async (forceRegenerate = false) => {
        setModalTitle("🎒 智能行李清单");
        setModalContentType('packing');
        setIsModalOpen(true);

        if (!forceRegenerate && packingListData) {
            setModalContent(packingListData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Create smart packing list for ${destination} trip. Status: ${weather.condition}, ${weather.temp}.
      Context: ${itineraryData.map(d => d.activities.map(a => a.title).join(', ')).join(', ')}.
      Return JSON: { "special_tips": "", "categories": [{ "name": "", "items": [{ "name": "", "reason": "" }] }] }
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setPackingListData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("生成失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleEstimateBudget = async (forceRegenerate = false) => {
        setModalTitle("💰 智能预算估算");
        setModalContentType('budget');
        setIsModalOpen(true);

        if (!forceRegenerate && budgetData) {
            setModalContent(budgetData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Estimate budget for trip to ${destination}.
      Itinerary: ${itineraryData.map(d => d.activities.map(a => a.title).join(', ')).join(', ')}.
      Return JSON: { "total_range": "e.g. 2000-3000 RMB", "categories": [{ "name": "餐饮", "amount": "e.g. 800", "desc": "Based on average restaurant prices" }], "saving_tip": "One useful tip to save money in ${destination}" }
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setBudgetData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("预算估算失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleGeneratePlaylist = async (forceRegenerate = false) => {
        setModalTitle("🎵 AI 氛围歌单");
        setModalContentType('playlist');
        setIsModalOpen(true);

        if (!forceRegenerate && playlistData) {
            setModalContent(playlistData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Create a playlist of 5 songs that fit the vibe of a trip to ${destination}.
      Context: ${itineraryData.length > 0 ? itineraryData[0].title : 'General Trip'}.
      Return JSON: { 
        "vibe_title": "Short poetic title (e.g. 漫步京都小巷)", 
        "vibe_desc": "One sentence description of the mood",
        "songs": [{ "title": "", "artist": "", "reason": "Why it fits" }] 
      }
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setPlaylistData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("歌单生成失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleGenerateEmergency = async (forceRegenerate = false) => {
        setModalTitle("🆘 智能紧急助手");
        setModalContentType('emergency');
        setIsModalOpen(true);

        if (!forceRegenerate && emergencyData) {
            setModalContent(emergencyData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Provide emergency info for a tourist in ${destination}.
      Return JSON: { 
        "local_numbers": { "警方": "110", "急救": "120" }, 
        "sos_card": { "text_local": "Help me (in local language)", "text_en": "I need help, please call police", "pronunciation": "Pronunciation guide" }, 
        "embassy_tip": "General safety advice for tourists in this city (in Chinese)." 
      }
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setEmergencyData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("紧急信息获取失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleGenerateCulture = async (forceRegenerate = false) => {
        setModalTitle("🌍 本地文化锦囊");
        setModalContentType('culture');
        setIsModalOpen(true);

        if (!forceRegenerate && cultureData) {
            setModalContent(cultureData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      You are a local expert for ${destination}. Provide a cultural guide in JSON:
      {
        "taboos": ["Don't do X", "Avoid Y"],
        "etiquette": "Tipping or bowing advice",
        "phrases": [
          {"local": "Hello/Thanks in dialect/language", "pronunciation": "Phonetic", "meaning": "Meaning"}
        ]
      }
      Keep it practical and fun.
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setCultureData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("文化指南生成失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleGenerateSouvenirs = async (forceRegenerate = false) => {
        setModalTitle("🎁 伴手礼顾问");
        setModalContentType('souvenirs');
        setIsModalOpen(true);

        if (!forceRegenerate && souvenirData) {
            setModalContent(souvenirData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Recommend authentic souvenirs for ${destination}.
      Return JSON:
      {
        "must_buy": [{"name": "Item Name", "desc": "Why it's good"}],
        "avoid": ["Tourist Trap Item 1", "Item 2"]
      }
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setSouvenirData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("生成失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    const handleGeneratePhotoChallenge = async (forceRegenerate = false) => {
        setModalTitle("📸 城市摄影挑战");
        setModalContentType('photo_challenge');
        setIsModalOpen(true);

        if (!forceRegenerate && photoChallengeData) {
            setModalContent(photoChallengeData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Generate 5 creative photo scavenger hunt tasks for a tourist in ${destination}. 
      Return JSON: { "challenges": [{"title": "e.g. Red Lantern", "desc": "Find a..."}] }
    `;

        const data = await callGemini(prompt, true);
        if (data) {
            setPhotoChallengeData(data);
            setModalContent(data);
        } else {
            setModalContentType('text');
            setModalContent("生成失败，请重试。");
        }
        setIsGeminiLoading(false);
    };

    // --- NEW: Vlog Generator ---
    const handleGenerateVlog = async (day) => {
        setModalTitle(`🎬 ${day.title} - Vlog 脚本`);
        setModalContentType('vlog');
        setIsModalOpen(true);
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Create a Vlog shooting script for Day ${day.day} in ${destination}.
      Activities: ${day.activities.map(a => a.title).join(', ')}.
      Return JSON: { "title": "Catchy Vlog Title", "shots": [{"action": "Selfie at entrance", "angle": "Wide shot", "duration": "3s", "audio": "Voiceover: We arrived!"}], "bgm": "Upbeat pop" }
    `;
        const data = await callGemini(prompt, true);
        setModalContent(data);
        setIsGeminiLoading(false);
    };

    // --- NEW: Poster Generator ---
    const handleGeneratePoster = async (forceRegenerate = false) => {
        setModalTitle("🖼️ 分享海报预览");
        setModalContentType('poster');
        setIsModalOpen(true);

        if (!forceRegenerate && posterData) {
            setModalContent(posterData);
            return;
        }
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Summarize trip to ${destination} for a poster.
      Return JSON: { "destination": "${destination}", "days": "4 DAYS 3 NIGHTS", "highlights": ["Highlight 1", "Highlight 2", "Highlight 3"], "budget": "¥2500" }
    `;
        const data = await callGemini(prompt, true);
        if (data) {
            setPosterData(data);
            setModalContent(data);
        }
        setIsGeminiLoading(false);
    };

    const handleGenerateDiary = async (day) => {
        setModalTitle(`📝 ${day.title} - 旅行日记`);
        setModalContentType('diary');
        setIsModalOpen(true);
        setModalContent(null);
        setIsGeminiLoading(true);

        const prompt = `
      Write a first-person travel diary entry for Day ${day.day} in ${destination}.
      Activities: ${day.activities.map(a => a.title).join(', ')}.
      Tone: Emotional, vivid, and personal (in Chinese).
      Format: Markdown.
    `;
        const text = await callGemini(prompt, false);
        setModalContent(text);
        setIsGeminiLoading(false);
    };

    const handleRegenerate = () => {
        if (modalContentType === 'packing') handleGeneratePackingList(true);
        else if (modalContentType === 'tips' && currentDayForTip) handleGetDayTips(currentDayForTip, true);
        else if (modalContentType === 'budget') handleEstimateBudget(true);
        else if (modalContentType === 'playlist') handleGeneratePlaylist(true);
        else if (modalContentType === 'emergency') handleGenerateEmergency(true);
        else if (modalContentType === 'culture') handleGenerateCulture(true);
        else if (modalContentType === 'souvenirs') handleGenerateSouvenirs(true);
        else if (modalContentType === 'photo_challenge') handleGeneratePhotoChallenge(true);
        else if (modalContentType === 'diary') handleGenerateDiary(currentDayForTip);
        else if (modalContentType === 'vlog') handleGenerateVlog(currentDayForTip);
        else if (modalContentType === 'poster') handleGeneratePoster(true);
    };

    // --- Activity Detail Handlers ---
    const handleActivityClick = (dayIdx, actIdx, activity) => {
        setSelectedActivityPath({ type: 'itinerary', dayIdx, actIdx });
        setSelectedActivity(activity);
        setDetailModalOpen(true);
    };

    const handlePoiClick = (index, poi) => {
        setSelectedActivityPath({ type: 'poi', index });
        setSelectedActivity({
            ...poi,
            title: poi.name,
            desc: poi.desc || `评分: ${poi.rating} | 标签: ${poi.tags?.join(', ')}`,
            time: poi.price || "价格待定",
            type: 'hotel'
        });
        setDetailModalOpen(true);
    };

    const handleToggleCheckIn = (dayIdx, actIdx) => {
        const newItinerary = [...itineraryData];
        newItinerary[dayIdx].activities[actIdx].checked = !newItinerary[dayIdx].activities[actIdx].checked;
        setItineraryData(newItinerary);
    };

    const handleUpdateActivity = (updatedActivity) => {
        if (selectedActivityPath.type === 'itinerary') {
            const { dayIdx, actIdx } = selectedActivityPath;
            const newItinerary = [...itineraryData];
            newItinerary[dayIdx].activities[actIdx] = updatedActivity;
            setItineraryData(newItinerary);
        } else if (selectedActivityPath.type === 'poi') {
            const { index } = selectedActivityPath;
            const newPois = [...poiData];
            newPois[index] = {
                ...updatedActivity,
                name: updatedActivity.title,
                price: updatedActivity.time
            };
            setPoiData(newPois);
        }
        setSelectedActivity(updatedActivity);
    };

    const handleEnrichActivity = async () => {
        setIsActivityEnriching(true);
        const prompt = `
      Tell me about "${selectedActivity.title}" in ${destination}.
      Return a JSON object with: { "intro": "A compelling 3-sentence introduction (in Chinese).", "opening_hours": "e.g. 09:00 - 17:00", "ticket_price": "Approximate price (e.g. 50 RMB)" }
    `;
        const details = await callGemini(prompt, true);
        setIsActivityEnriching(false);
        if (details) {
            const updatedActivity = { ...selectedActivity, details };
            handleUpdateActivity(updatedActivity);
        }
    };

    // --- Voice Interaction (REAL Web Speech API Implementation) ---
    const handleVoiceInput = () => {
        // Stop if already listening
        if (isListening) {
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
            setIsListening(false);
            return;
        }

        // Check browser support
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert("抱歉，您的浏览器不支持语音识别功能，请尝试 Chrome 或 Edge 浏览器。");
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.lang = 'zh-CN'; // Set to Chinese
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            setIsListening(true);
        };

        recognition.onend = () => {
            setIsListening(false);
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            setIsListening(false);
            if (event.error === 'not-allowed') {
                alert("请允许麦克风权限以使用语音功能。");
            }
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript) {
                setInput(transcript);
                // Optional: Auto-send after voice input
                // handleSend(); 
            }
        };

        recognitionRef.current = recognition;
        recognition.start();
    };

    // --- Render ---

    if (loadingAuth) return <div className="flex h-screen items-center justify-center bg-[#0f111a]"><Loader2 className="animate-spin text-blue-500" size={48} /></div>;

    if (!user) return (
        <div className="flex h-screen w-full relative overflow-hidden bg-[#0f111a] items-center justify-center">
            <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/20 rounded-full blur-[120px]"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-blue-900/20 rounded-full blur-[120px]"></div>
            <div className="relative z-10 w-full max-w-md p-8 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl mx-4">
                <div className="text-center mb-8">
                    <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-blue-600 to-purple-600 mb-4 shadow-lg shadow-blue-500/30"><Navigation size={32} className="text-white" /></div>
                    <h1 className="text-3xl font-bold text-white mb-2">TravelMind</h1><p className="text-gray-400">您的 AI 智能旅行规划管家</p>
                </div>
                <button onClick={handleLogin} className="w-full py-3.5 px-4 bg-white text-black font-bold rounded-xl hover:bg-gray-100 transition-all transform hover:scale-[1.02] flex items-center justify-center gap-2"><UserCircle2 size={20} /> 立即开始 (访客模式)</button>
                <p className="mt-6 text-center text-xs text-gray-500">点击即代表同意服务条款与隐私协议</p>
            </div>
        </div>
    );

    return (
        <div className="flex h-screen w-full bg-[#0f111a] text-gray-200 font-sans overflow-hidden">

            {/* Modals */}
            <GeminiModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={modalTitle} content={modalContent} contentType={modalContentType} isLoading={isGeminiLoading} onRegenerate={handleRegenerate} />

            <ActivityDetailModal
                isOpen={detailModalOpen}
                onClose={() => setDetailModalOpen(false)}
                activity={selectedActivity}
                onSave={handleUpdateActivity}
                onEnrich={handleEnrichActivity}
                isEnriching={isActivityEnriching}
                destination={destination}
            />

            {/* Background */}
            <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-blue-900/10 rounded-full blur-[120px]"></div>
            </div>

            {/* Mobile Nav */}
            <div className="lg:hidden fixed bottom-0 left-0 w-full h-16 bg-[#131520] border-t border-white/10 z-50 flex justify-around items-center px-2 safe-area-bottom">
                <button onClick={() => setMobileView('chat')} className={`flex flex-col items-center p-2 rounded-lg transition-colors ${mobileView === 'chat' ? 'text-blue-400' : 'text-gray-500'}`}><MessageSquare size={20} /><span className="text-[10px] mt-1">聊天</span></button>
                <button onClick={() => setMobileView('dashboard')} className={`flex flex-col items-center p-2 rounded-lg transition-colors ${mobileView === 'dashboard' ? 'text-blue-400' : 'text-gray-500'}`}><Layout size={20} /><span className="text-[10px] mt-1">行程</span></button>
            </div>

            {/* Left Chat */}
            <div className={`${mobileView === 'dashboard' ? 'hidden lg:flex' : 'flex'} w-full lg:w-[40%] flex-col border-r border-white/5 relative z-10 bg-[#0f111a]/50 backdrop-blur-sm transition-all`}>
                <div className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-white/5 backdrop-blur-md">
                    <div className="flex items-center gap-2"><div className="bg-gradient-to-br from-blue-500 to-purple-600 p-1.5 rounded-lg"><Navigation size={18} className="text-white" /></div><span className="font-bold text-lg tracking-tight text-white">TravelMind</span></div>
                    <div className="flex items-center gap-3"><div className="text-xs text-right hidden sm:block"><div className="text-white font-medium">Guest User</div><div className="text-gray-500">在线</div></div><button onClick={handleLogout} className="p-2 hover:bg-red-500/10 hover:text-red-400 text-gray-400 rounded-full transition-colors"><LogOut size={18} /></button></div>
                </div>
                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar pb-24 lg:pb-4">
                    {messages.map((msg, i) => <ChatMessage key={i} {...msg} />)}
                    {isTyping && <ChatMessage role="ai" content="" isTyping={true} isStreaming={true} />}
                    <div ref={messagesEndRef} />
                </div>
                <div className="p-4 border-t border-white/5 bg-[#0f111a] lg:pb-4 pb-20">
                    <div className="relative flex items-center bg-white/5 border border-white/10 rounded-2xl px-2 focus-within:border-blue-500/50 focus-within:bg-white/10 transition-all shadow-lg">
                        <button onClick={handleVoiceInput} className={`p-2 mr-2 rounded-full transition-all ${isListening ? 'bg-red-500/20 text-red-500 animate-pulse' : 'text-gray-400 hover:text-white'}`} title={isListening ? "点击停止" : "点击说话"}>
                            <Mic size={20} />
                        </button>
                        <input type="text" className="flex-1 bg-transparent border-none text-white px-2 py-4 focus:ring-0 placeholder-gray-500 outline-none" placeholder={isListening ? "正在聆听..." : "输入你的旅行计划..."} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} />
                        <button onClick={handleSend} className={`p-2 rounded-xl transition-all duration-300 ${input.trim() ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-100' : 'bg-gray-700 text-gray-500 scale-90'}`}><Send size={18} /></button>
                    </div>
                </div>
            </div>

            {/* Right Dashboard */}
            <div className={`${mobileView === 'chat' ? 'hidden lg:flex' : 'flex'} flex-1 flex-col relative z-10 bg-gradient-to-br from-[#131620] to-[#0b0c12] lg:pb-0 pb-16`}>
                <div className="h-16 border-b border-white/5 flex items-center justify-between px-4 lg:px-8 bg-white/2">
                    <div className="flex items-center gap-3 lg:gap-4 overflow-hidden">
                        <h2 className="text-white font-semibold whitespace-nowrap">{destination} 之旅</h2>
                        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${tripStatus === 'Created' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20' : 'bg-blue-500/20 text-blue-400 border-blue-500/20'}`}>{tripStatus}</span>
                    </div>
                    <div className="flex items-center gap-2 lg:gap-4">
                        {itineraryData.length > 0 && (
                            <>
                                {/* Desktop Buttons */}
                                <div className="hidden xl:flex items-center gap-2">
                                    <button onClick={() => handleEstimateBudget(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 hover:from-emerald-500/30 hover:to-teal-500/30 border border-emerald-500/30 rounded-full text-xs lg:text-sm font-medium text-emerald-400 transition-all hover:scale-105 whitespace-nowrap"><Banknote size={14} className="lg:w-4 lg:h-4" /><span>预算</span></button>
                                    <button onClick={() => handleGeneratePackingList(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-blue-500/20 to-purple-500/20 hover:from-blue-500/30 hover:to-purple-500/30 border border-blue-500/30 rounded-full text-xs lg:text-sm font-medium text-blue-400 transition-all hover:scale-105 whitespace-nowrap"><Backpack size={14} className="lg:w-4 lg:h-4" /><span>行李</span></button>
                                    <button onClick={() => handleGeneratePlaylist(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 hover:from-violet-500/30 hover:to-fuchsia-500/30 border border-violet-500/30 rounded-full text-xs lg:text-sm font-medium text-violet-400 transition-all hover:scale-105 whitespace-nowrap"><Music size={14} className="lg:w-4 lg:h-4" /><span>歌单</span></button>
                                    <button onClick={() => handleGenerateEmergency(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-red-500/20 to-orange-500/20 hover:from-red-500/30 hover:to-orange-500/30 border border-red-500/30 rounded-full text-xs lg:text-sm font-medium text-red-400 transition-all hover:scale-105 whitespace-nowrap"><Siren size={14} className="lg:w-4 lg:h-4" /><span>求助</span></button>
                                    <button onClick={() => handleGenerateCulture(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 border border-cyan-500/30 rounded-full text-xs lg:text-sm font-medium text-cyan-400 transition-all hover:scale-105 whitespace-nowrap"><Globe size={14} className="lg:w-4 lg:h-4" /><span>文化</span></button>
                                    <button onClick={() => handleGenerateSouvenirs(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-pink-500/20 to-rose-500/20 hover:from-pink-500/30 hover:to-rose-500/30 border border-pink-500/30 rounded-full text-xs lg:text-sm font-medium text-pink-400 transition-all hover:scale-105 whitespace-nowrap"><ShoppingBag size={14} className="lg:w-4 lg:h-4" /><span>好物</span></button>
                                    <button onClick={() => handleGeneratePhotoChallenge(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 hover:from-indigo-500/30 hover:to-purple-500/30 border border-indigo-500/30 rounded-full text-xs lg:text-sm font-medium text-indigo-400 transition-all hover:scale-105 whitespace-nowrap"><Aperture size={14} className="lg:w-4 lg:h-4" /><span>挑战</span></button>
                                    <button onClick={() => handleGeneratePoster(false)} className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-indigo-500/20 to-sky-500/20 hover:from-indigo-500/30 hover:to-sky-500/30 border border-indigo-500/30 rounded-full text-xs lg:text-sm font-medium text-sky-400 transition-all hover:scale-105 whitespace-nowrap"><ImageIcon size={14} className="lg:w-4 lg:h-4" /><span>海报</span></button>
                                </div>

                                {/* Mobile/Tablet Compact Menu */}
                                <div className="xl:hidden flex items-center gap-2">
                                    <button onClick={() => handleGeneratePhotoChallenge(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-indigo-400 border border-white/5"><Aperture size={16} /></button>
                                    <button onClick={() => handleGenerateSouvenirs(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-pink-400 border border-white/5"><ShoppingBag size={16} /></button>
                                    <button onClick={() => handleGenerateCulture(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-cyan-400 border border-white/5"><Globe size={16} /></button>
                                    <button onClick={() => handleGeneratePlaylist(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-violet-400 border border-white/5"><Music size={16} /></button>
                                    <button onClick={() => handleGenerateEmergency(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-red-400 border border-white/5"><Siren size={16} /></button>
                                    <button onClick={() => handleEstimateBudget(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-emerald-400 border border-white/5"><Banknote size={16} /></button>
                                    <button onClick={() => handleGeneratePackingList(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-blue-400 border border-white/5"><Backpack size={16} /></button>
                                    <button onClick={() => handleGeneratePoster(false)} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-sky-400 border border-white/5"><ImageIcon size={16} /></button>
                                </div>
                            </>
                        )}
                        <div className="h-6 w-[1px] bg-white/10 mx-1 lg:mx-2 hidden sm:block"></div>
                        <div className="flex items-center gap-2 lg:gap-3 bg-white/5 px-3 py-1.5 rounded-full border border-white/10 backdrop-blur-md">{weather.condition.includes('雨') ? <CloudSun size={18} className="text-gray-400" /> : <CloudSun size={18} className="text-yellow-400" />}<div><div className="text-xs lg:text-sm font-bold text-white">{weather.temp}</div><div className="text-[10px] text-gray-400 hidden sm:block">{destination}, {weather.condition}</div></div></div>
                    </div>
                </div>

                <div className="px-4 lg:px-8 pt-4 lg:pt-6 pb-2 overflow-x-auto no-scrollbar">
                    <div className="flex gap-1 bg-white/5 p-1 rounded-xl w-fit border border-white/5 mx-auto lg:mx-0">
                        {[{ id: 'itinerary', icon: Calendar, label: '行程规划' }, { id: 'pois', icon: Hotel, label: '推荐住宿' }, { id: 'map', icon: MapIcon, label: '地图模式' }].map(tab => (
                            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-3 lg:px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}><tab.icon size={16} />{tab.label}</button>
                        ))}
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar">
                    {activeTab === 'itinerary' && (
                        <div className="max-w-3xl mx-auto lg:mx-0">
                            {itineraryData.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-gray-500 border-2 border-dashed border-white/10 rounded-2xl"><Sparkles size={32} className="mb-3 opacity-30" /><p className="text-sm">告诉我你想去哪，我来为你规划</p></div>
                            ) : (
                                <ItineraryTimeline days={itineraryData} onGetTips={handleGetDayTips} onActivityClick={handleActivityClick} onGetDiary={handleGenerateDiary} onToggleCheckIn={handleToggleCheckIn} onGenerateVlog={handleGenerateVlog} />
                            )}
                        </div>
                    )}
                    {activeTab === 'pois' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
                            {poiData.length > 0 ? poiData.map((poi, idx) => (
                                <div key={idx} className="group relative overflow-hidden rounded-2xl bg-gray-800 border border-white/10 shadow-xl hover:shadow-2xl hover:shadow-blue-500/10 transition-all duration-300 flex flex-col">
                                    <div className="h-32 bg-gray-700 relative overflow-hidden"><img src={poi.image || `https://source.unsplash.com/600x400/?hotel,${poi.type}`} onError={(e) => { e.target.src = "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=600&q=80" }} alt={poi.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" /><div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm px-2 py-1 rounded-lg flex items-center gap-1 text-xs font-bold text-yellow-400"><Star size={12} fill="currentColor" /> {poi.rating || "4.5"}</div></div>
                                    <div className="p-4 flex-1 flex flex-col"><h3 className="font-bold text-white truncate">{poi.name}</h3><div className="flex items-center justify-between mt-2 mb-3"><span className="text-blue-400 font-mono font-bold">{poi.price || "暂无报价"}</span><div className="flex gap-1 flex-wrap justify-end">{poi.tags && poi.tags.map((tag, i) => (<span key={i} className="text-[10px] bg-white/10 text-gray-300 px-1.5 py-0.5 rounded">{tag}</span>))}</div></div><button onClick={() => handlePoiClick(idx, poi)} className="w-full mt-auto bg-white/5 hover:bg-blue-600 hover:text-white text-gray-300 py-2 rounded-lg text-xs font-medium transition-colors border border-white/10">查看详情</button></div>
                                </div>
                            )) : <div className="col-span-3 text-center text-gray-500 py-10"><Hotel size={48} className="mx-auto mb-4 opacity-20" /><p>暂无推荐，请先规划行程</p></div>}
                        </div>
                    )}
                    {activeTab === 'map' && (
                        <div className="h-full min-h-[400px] bg-gray-800/50 rounded-3xl border border-white/10 flex items-center justify-center relative overflow-hidden group">
                            <div className="absolute inset-0 bg-[url('https://api.mapbox.com/styles/v1/mapbox/dark-v10/static/120.15,30.28,11,0/800x600?access_token=pk.xxx')] bg-cover opacity-50 grayscale group-hover:grayscale-0 transition-all duration-700"></div>
                            <div className="relative z-10 text-center p-6 bg-black/40 backdrop-blur-md rounded-2xl border border-white/10"><MapIcon size={48} className="mx-auto text-blue-500 mb-4 animate-bounce" /><h3 className="text-xl font-bold text-white">地图模式预览</h3><p className="text-gray-400 mt-2 text-sm">实际开发中，这里将集成 React-AMap (高德地图)</p></div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}