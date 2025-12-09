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
    PlayCircle, ExternalLink, Newspaper, TrendingUp, Sun, Moon, Umbrella, Wind, ChevronDown, Edit3,
    BrainCircuit, ChevronLeft, ChevronRight as ChevronRightIcon, XCircle, Layers
} from 'lucide-react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged, signOut, updateProfile, signInWithCustomToken } from 'firebase/auth';
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
const copyToClipboard = (text, onSuccess, onError) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => { if (onSuccess) onSuccess(); }).catch(err => { fallbackCopyTextToClipboard(text, onSuccess, onError); });
    } else { fallbackCopyTextToClipboard(text, onSuccess, onError); }
}
const fallbackCopyTextToClipboard = (text, onSuccess, onError) => {
    try {
        const textArea = document.createElement("textarea"); textArea.value = text;
        textArea.style.top = "0"; textArea.style.left = "0"; textArea.style.position = "fixed"; textArea.style.opacity = "0";
        document.body.appendChild(textArea); textArea.focus(); textArea.select();
        const successful = document.execCommand('copy'); document.body.removeChild(textArea);
        if (successful) { if (onSuccess) onSuccess(); } else { throw new Error("execCommand returned false"); }
    } catch (err) { if (onError) onError(); }
}

const safeRender = (value) => {
    if (typeof value === 'object' && value !== null) {
        return JSON.stringify(value);
    }
    return value;
};

// --- Basic UI Components ---
const EnhancedMarkdown = ({ text }) => {
    if (typeof text !== 'string') return null;
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
            {!isUser && (<div className={`w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 flex items-center justify-center mr-3 shadow-lg shadow-purple-500/30 flex-shrink-0 ${isStreaming ? 'animate-pulse ring-2 ring-purple-500/50' : ''}`}><Bot size={16} className="text-white" /></div>)}
            <div className={`max-w-[85%] rounded-2xl px-5 py-4 backdrop-blur-md shadow-sm ${isUser ? 'bg-blue-600/90 text-white rounded-br-none' : 'bg-white/10 text-gray-100 border border-white/10 rounded-bl-none'}`}>
                <div className="leading-relaxed text-sm md:text-base">{isUser ? content : <EnhancedMarkdown text={content} />}{!isUser && isStreaming && (<span className="inline-block w-2 h-4 ml-1 bg-blue-400 animate-pulse align-middle rounded-sm"></span>)}</div>
            </div>
            {isUser && (<div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center ml-3 border border-gray-600 flex-shrink-0"><User size={16} className="text-gray-300" /></div>)}
        </div>
    );
};

// --- REAL MAP IMPLEMENTATION (Leaflet) ---
const RealMap = ({ itinerary, destination }) => {
    const mapContainerRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const [isMapReady, setIsMapReady] = useState(false);

    // Mock Coordinates for robustness if AI fails to return them
    const CITY_COORDS = {
        "北京": [39.9042, 116.4074],
        "上海": [31.2304, 121.4737],
        "东京": [35.6762, 139.6503],
        "大阪": [34.6937, 135.5023],
        "三亚": [18.2528, 109.5119],
        "成都": [30.5728, 104.0668],
        "杭州": [30.2741, 120.1551],
        "未知目的地": [39.9042, 116.4074]
    };

    useEffect(() => {
        // Dynamically load Leaflet CSS and JS using cdnjs for better stability
        const loadLeaflet = async () => {
            if (window.L && typeof window.L.map === 'function') {
                setIsMapReady(true);
                return;
            }

            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
            document.head.appendChild(link);

            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
                script.onload = () => {
                    // Slight delay to ensure window.L is fully populated
                    setTimeout(() => {
                        if (window.L && typeof window.L.map === 'function') {
                            resolve();
                        } else {
                            reject(new Error("Leaflet failed to initialize correctly"));
                        }
                    }, 100);
                };
                script.onerror = reject;
                document.head.appendChild(script);
            });
            setIsMapReady(true);
        };

        loadLeaflet().catch(err => console.error("Leaflet load error", err));
    }, []);

    useEffect(() => {
        if (isMapReady && mapContainerRef.current && !mapInstanceRef.current && window.L && typeof window.L.map === 'function') {
            const defaultCenter = CITY_COORDS[destination] || CITY_COORDS["北京"];
            const map = window.L.map(mapContainerRef.current).setView(defaultCenter, 11);

            // Dark Mode Tiles
            window.L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
                maxZoom: 19
            }).addTo(map);

            mapInstanceRef.current = map;
        }

        // Update markers when itinerary changes
        if (isMapReady && mapInstanceRef.current && itinerary.length > 0 && window.L) {
            const map = mapInstanceRef.current;

            // Clear existing layers (except tiles)
            map.eachLayer((layer) => {
                if (layer instanceof window.L.Marker || layer instanceof window.L.Polyline) {
                    map.removeLayer(layer);
                }
            });

            // Add markers
            const points = [];
            itinerary.forEach((day, dIdx) => {
                day.activities.forEach((act, aIdx) => {
                    // Try to use AI coords, or fuzzy offset from city center
                    const cityCenter = CITY_COORDS[destination] || CITY_COORDS["北京"];
                    // Create a pseudo-random offset if no coords to simulate spread
                    const offsetLat = (Math.random() - 0.5) * 0.1;
                    const offsetLng = (Math.random() - 0.5) * 0.1;
                    const lat = act.lat || (cityCenter[0] + offsetLat);
                    const lng = act.lng || (cityCenter[1] + offsetLng);

                    if (lat && lng) {
                        points.push([lat, lng]);
                        const color = dIdx % 2 === 0 ? '#3b82f6' : '#10b981'; // Blue or Green based on day

                        // Custom Dot Icon
                        const icon = window.L.divIcon({
                            className: 'custom-div-icon',
                            html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>`,
                            iconSize: [12, 12],
                            iconAnchor: [6, 6]
                        });

                        window.L.marker([lat, lng], { icon })
                            .addTo(map)
                            .bindPopup(`<b>Day ${day.day}</b><br>${act.title}`);
                    }
                });
            });

            // Draw line connecting points
            if (points.length > 1) {
                window.L.polyline(points, { color: '#6366f1', weight: 3, opacity: 0.7, dashArray: '5, 10' }).addTo(map);
                map.fitBounds(window.L.latLngBounds(points).pad(0.2));
            }
        }
    }, [isMapReady, itinerary, destination]);

    return (
        <div className="h-full w-full rounded-3xl overflow-hidden border border-white/10 relative group">
            {!isMapReady && <div className="absolute inset-0 flex items-center justify-center bg-gray-900"><Loader2 className="animate-spin text-blue-500" /></div>}
            <div ref={mapContainerRef} className="w-full h-full z-0" style={{ minHeight: '400px' }}></div>
            {/* Overlay Controls */}
            <div className="absolute bottom-4 right-4 z-[400] flex flex-col gap-2">
                <div className="bg-black/60 backdrop-blur px-3 py-1.5 rounded-lg text-xs text-white border border-white/10 flex items-center gap-2">
                    <Layers size={14} />
                    <span>OpenStreetMap</span>
                </div>
            </div>
        </div>
    );
};

// --- Feature Views ---
const TipsView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">数据加载失败</div>;
    return (
        <div className="space-y-6">
            {data.photo_spots && data.photo_spots.length > 0 && (<div className="animate-fadeIn"><h4 className="flex items-center gap-2 text-pink-400 font-bold mb-3 text-lg"><Camera size={20} /> 最佳出片机位</h4><div className="grid grid-cols-1 gap-3">{data.photo_spots.map((spot, i) => (<div key={i} className="bg-white/5 border border-white/10 rounded-xl p-3 flex gap-3"><div className="bg-pink-500/20 text-pink-400 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-xs">{i + 1}</div><div><div className="text-white font-medium">{safeRender(spot.name)}</div><div className="text-xs text-gray-400 mt-1">{safeRender(spot.desc)}</div></div></div>))}</div></div>)}
            {data.warnings && data.warnings.length > 0 && (<div className="animate-fadeIn" style={{ animationDelay: '100ms' }}><h4 className="flex items-center gap-2 text-yellow-400 font-bold mb-3 text-lg"><AlertTriangle size={20} /> 避坑指南</h4><div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 space-y-3">{data.warnings.map((warn, i) => (<div key={i} className="flex gap-2 text-sm text-gray-200"><AlertTriangle size={14} className="text-yellow-500 mt-0.5 flex-shrink-0" /><span>{safeRender(warn)}</span></div>))}</div></div>)}
            {data.food && data.food.length > 0 && (<div className="animate-fadeIn" style={{ animationDelay: '200ms' }}><h4 className="flex items-center gap-2 text-orange-400 font-bold mb-3 text-lg"><Utensils size={20} /> 美食推荐</h4><div className="flex flex-wrap gap-2">{data.food.map((f, i) => (<span key={i} className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-orange-200">{safeRender(f)}</span>))}</div></div>)}
            {data.transport && (<div className="animate-fadeIn" style={{ animationDelay: '300ms' }}><h4 className="flex items-center gap-2 text-blue-400 font-bold mb-2 text-lg"><Navigation size={20} /> 交通建议</h4><p className="text-sm text-gray-300 bg-blue-500/10 border border-blue-500/20 p-3 rounded-xl">{safeRender(data.transport)}</p></div>)}
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
            {data.categories && data.categories.map((cat, catIdx) => (
                <div key={catIdx} className="animate-fadeIn" style={{ animationDelay: `${catIdx * 100}ms` }}><h4 className="text-white font-semibold mb-3 border-l-4 border-purple-500 pl-3">{safeRender(cat.name)}</h4><div className="grid grid-cols-1 gap-3">{cat.items && cat.items.map((item, itemIdx) => { const isChecked = checkedItems[`${catIdx}-${itemIdx}`]; return (<div key={itemIdx} onClick={() => toggleItem(catIdx, itemIdx)} className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${isChecked ? 'bg-green-900/10 border-green-500/30' : 'bg-white/5 border-white/5 hover:bg-white/10'}`}><div className={`mt-0.5 transition-colors ${isChecked ? 'text-green-500' : 'text-gray-500'}`}>{isChecked ? <CheckCircle2 size={20} /> : <Circle size={20} />}</div><div className="flex-1"><div className={`font-medium text-sm transition-all ${isChecked ? 'text-gray-500 line-through' : 'text-gray-200'}`}>{safeRender(item.name)}</div>{item.reason && (<div className="text-xs text-gray-500 mt-1">{safeRender(item.reason)}</div>)}</div></div>); })}</div></div>
            ))}
        </div>
    );
};
const PlaylistView = ({ data }) => {
    const [copied, setCopied] = useState(false);
    if (!data) return <div className="text-center text-gray-500">无法获取歌单</div>;
    const handleCopyPlaylist = () => { if (data.songs) { const text = data.songs.map(s => `${s.title} ${s.artist}`).join('\n'); copyToClipboard(text, () => { setCopied(true); setTimeout(() => setCopied(false), 2000); }, () => { alert("复制失败"); }); } };
    const openMusicSearch = (service, song) => { const query = encodeURIComponent(`${song.title} ${song.artist}`); let url = ""; if (service === 'netease') url = `https://music.163.com/#/search/m/?s=${query}`; if (service === 'qq') url = `https://y.qq.com/n/ryqq/search?w=${query}`; window.open(url, '_blank'); };
    return (
        <div className="space-y-6"><div className="bg-gradient-to-r from-violet-900/40 to-fuchsia-900/40 border border-violet-500/20 rounded-2xl p-6 relative overflow-hidden"><div className="relative z-10"><h3 className="text-violet-200 font-bold text-lg mb-1">{safeRender(data.vibe_title)}</h3><p className="text-gray-400 text-sm">{safeRender(data.vibe_desc)}</p><button onClick={handleCopyPlaylist} className="mt-4 flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/10 px-3 py-1.5 rounded-lg text-xs text-white transition-all">{copied ? <CheckCircle2 size={12} className="text-green-400" /> : <Copy size={12} />}{copied ? "已复制" : "复制歌单"}</button></div><Music className="absolute right-4 bottom-4 text-violet-500/20 w-24 h-24 rotate-12" /></div><div className="space-y-3">{data.songs && data.songs.map((song, i) => (<div key={i} className="flex items-center gap-3 p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-white/5 group"><div className="w-8 h-8 bg-gray-800 rounded-lg flex items-center justify-center text-gray-500 font-bold text-xs group-hover:text-violet-400 transition-colors shrink-0">{i + 1}</div><div className="flex-1 min-w-0"><div className="font-medium text-gray-200 truncate text-sm">{safeRender(song.title)}</div><div className="text-xs text-gray-500 truncate">{safeRender(song.artist)}</div></div><div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity"><button onClick={() => openMusicSearch('netease', song)} className="px-2 py-1 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded text-[10px] border border-red-500/30 font-medium">网易</button><button onClick={() => openMusicSearch('qq', song)} className="px-2 py-1 bg-green-600/20 hover:bg-green-600/40 text-green-400 rounded text-[10px] border border-green-500/30 font-medium">QQ</button></div></div>))}</div></div>
    );
};
const BudgetView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-500">无法获取预算数据</div>;
    return (
        <div className="space-y-6">
            <div className="bg-gradient-to-r from-emerald-900/30 to-teal-900/30 border border-emerald-500/20 rounded-2xl p-6 text-center"><h3 className="text-gray-400 text-sm mb-1 uppercase tracking-wider">预估总花费</h3><div className="text-4xl font-bold text-white text-shadow-lg">{safeRender(data.total_range)}</div></div>
            {data.categories && data.categories.length > 0 && (
                <div className="space-y-3"><h4 className="text-white font-semibold flex items-center gap-2"><Banknote size={18} className="text-emerald-400" /> 费用明细</h4>{data.categories.map((cat, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 flex justify-between items-center"><div><div className="text-gray-200 font-medium">{safeRender(cat.name)}</div><div className="text-xs text-gray-500 mt-0.5">{safeRender(cat.desc)}</div></div><div className="text-emerald-300 font-mono font-bold">{safeRender(cat.amount)}</div></div>))}</div>
            )}
            <div className="bg-blue-900/10 border border-blue-500/10 p-4 rounded-xl"><h4 className="text-blue-300 font-bold mb-2 flex items-center gap-2 text-sm"><Zap size={14} /> 省钱小妙招</h4><p className="text-sm text-gray-300 leading-relaxed">{safeRender(data.saving_tip)}</p></div>
        </div>
    );
};
const EmergencyView = ({ data }) => (<div className="space-y-6"><div className="bg-red-900/20 border border-red-500/30 p-4 rounded-xl flex items-start gap-3"><AlertTriangle className="text-red-500 flex-shrink-0 mt-1" /><div><h4 className="text-red-400 font-bold mb-1">紧急提示</h4><p className="text-gray-300 text-sm">{safeRender(data.embassy_tip)}</p></div></div><div className="grid grid-cols-2 gap-4">{data.local_numbers && Object.entries(data.local_numbers).map(([key, num], i) => (<div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col items-center justify-center text-center"><div className="text-gray-400 text-xs uppercase mb-2 tracking-wider">{safeRender(key)}</div><div className="text-2xl font-bold text-white tracking-widest">{safeRender(num)}</div><button className="mt-2 text-xs bg-white/10 hover:bg-green-600 hover:text-white px-3 py-1 rounded-full flex items-center gap-1"><Phone size={10} /> 呼叫</button></div>))}</div></div>);
const CultureView = ({ data }) => (<div className="space-y-6"><div className="space-y-3"><h4 className="text-white font-semibold flex items-center gap-2"><Globe size={18} className="text-blue-400" /> 社交禁忌 & 礼仪</h4><div className="grid grid-cols-1 gap-3">{data.taboos && data.taboos.map((taboo, i) => (<div key={i} className="bg-red-900/10 border border-red-500/20 p-3 rounded-xl flex gap-3 items-start"><X size={12} className="text-red-400 mt-0.5" /><p className="text-sm text-gray-300">{safeRender(taboo)}</p></div>))}</div></div></div>);
const SouvenirView = ({ data }) => (<div className="space-y-6"><div className="space-y-3"><h4 className="text-white font-semibold flex items-center gap-2"><ShoppingBag size={18} className="text-pink-400" /> 必买伴手礼</h4><div className="grid grid-cols-1 gap-3">{data.must_buy && data.must_buy.map((item, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-3 flex justify-between items-center"><div><div className="text-white font-bold">{safeRender(item.name)}</div><div className="text-xs text-gray-400">{safeRender(item.desc)}</div></div><div className="bg-pink-500/10 text-pink-400 text-xs px-2 py-1 rounded">推荐</div></div>))}</div></div></div>);
const PhotoChallengeView = ({ data }) => (<div className="space-y-6"><div className="bg-indigo-900/20 border border-indigo-500/20 p-4 rounded-xl mb-4 text-center"><h4 className="text-indigo-300 font-bold mb-1 flex items-center justify-center gap-2 text-lg"><Aperture size={20} /> 城市探索者挑战</h4></div><div className="grid grid-cols-1 gap-4">{data.challenges && data.challenges.map((c, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 flex gap-4 items-center"><div className="w-12 h-12 rounded-full bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-xl font-bold border border-indigo-500/30">{i + 1}</div><div><div className="font-bold text-white text-lg mb-1">{safeRender(c.title)}</div><div className="text-sm text-gray-400">{safeRender(c.desc)}</div></div></div>))}</div></div>);
const VlogScriptView = ({ data }) => (<div className="space-y-6"><div className="text-center mb-4"><h3 className="text-xl font-bold text-white">Vlog 脚本</h3><p className="text-sm text-gray-400">{safeRender(data.title)}</p></div><div className="space-y-4">{data.shots && data.shots.map((shot, i) => (<div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4"><div className="flex justify-between mb-2"><span className="text-xs font-bold text-purple-400 uppercase">Shot {i + 1} • {safeRender(shot.duration)}</span><span className="text-xs text-gray-500">{safeRender(shot.angle)}</span></div><p className="text-white font-medium mb-1">{safeRender(shot.action)}</p></div>))}</div></div>);
const PosterView = ({ data }) => { const posterRef = useRef(null); const handleDownload = async () => { if (!window.html2canvas) { await new Promise((resolve) => { const script = document.createElement('script'); script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'; script.onload = resolve; document.head.appendChild(script); }); } const canvas = await window.html2canvas(posterRef.current, { useCORS: true, backgroundColor: null, scale: 2 }); const link = document.createElement('a'); link.download = `poster.png`; link.href = canvas.toDataURL('image/png'); link.click(); }; return (<div className="flex flex-col items-center gap-4"><div ref={posterRef} className="w-full max-w-sm bg-gradient-to-br from-indigo-900 to-purple-900 border border-white/20 rounded-2xl p-6 relative aspect-[3/4] flex flex-col"><h2 className="text-3xl font-black text-white mb-1">{safeRender(data.destination)}</h2><div className="space-y-4 my-6 flex-1">{data.highlights && data.highlights.map((h, i) => (<div key={i} className="flex items-center gap-3"><div className="w-1.5 h-1.5 bg-white rounded-full"></div><span className="text-white text-lg font-light">{safeRender(h)}</span></div>))}</div><div className="mt-auto flex justify-between items-end"><div className="text-white font-bold">TravelMind</div><div className="text-xl font-bold text-white">{safeRender(data.budget)}</div></div></div><button onClick={handleDownload} className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-full font-bold shadow-lg transition-all hover:scale-105"><Download size={18} /> 保存海报</button></div>); };

const GeminiModal = ({ isOpen, onClose, title, content, contentType, isLoading, onRegenerate }) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
            <div className="bg-[#1a1d2d] border border-white/10 rounded-2xl w-full max-w-md md:max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
                <div className="p-4 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-blue-900/30 to-purple-900/30"><h3 className="text-lg font-bold text-white flex items-center gap-2 truncate pr-2">{title}</h3><div className="flex items-center gap-2 flex-shrink-0">{!isLoading && (<button onClick={onRegenerate} title="重新生成" className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors flex items-center gap-1 text-xs"><RefreshCw size={14} /><span className="hidden sm:inline">重新生成</span></button>)}<button onClick={onClose} className="text-gray-400 hover:text-white transition-colors p-1.5 hover:bg-white/10 rounded-full"><X size={20} /></button></div></div>
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1 bg-[#131520]">
                    {isLoading ? (<div className="flex flex-col items-center justify-center py-12 gap-4"><Loader2 size={32} className="text-blue-500 animate-spin" /><p className="text-sm text-blue-300 animate-pulse">AI 正在为您精心定制内容...</p></div>) : (
                        <>
                            {contentType === 'packing' ? <PackingList data={content} /> : contentType === 'tips' ? <TipsView data={content} /> : contentType === 'budget' ? <BudgetView data={content} /> : contentType === 'playlist' ? <PlaylistView data={content} /> : contentType === 'emergency' ? <EmergencyView data={content} /> : contentType === 'culture' ? <CultureView data={content} /> : contentType === 'souvenirs' ? <SouvenirView data={content} /> : contentType === 'photo_challenge' ? <PhotoChallengeView data={content} /> : contentType === 'vlog' ? <VlogScriptView data={content} /> : contentType === 'poster' ? <PosterView data={content} /> : <EnhancedMarkdown text={typeof content === 'string' ? content : JSON.stringify(content)} />}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- Smart Sidebar Widgets ---

const MiniMapWidget = ({ itinerary }) => {
    const [selectedDayIdx, setSelectedDayIdx] = useState(0);
    const day = itinerary && itinerary.length > 0 ? itinerary[selectedDayIdx] : null;

    if (!day) return (
        <div className="bg-[#1a1d2d]/60 border border-white/5 rounded-2xl p-5 h-48 flex items-center justify-center">
            <div className="text-gray-500 text-xs flex flex-col items-center gap-2"><MapIcon size={24} className="opacity-50" /><p>暂无行程路线</p></div>
        </div>
    );

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn relative overflow-hidden group">
            <div className="flex justify-between items-center mb-4 z-10 relative">
                <h4 className="font-bold text-white text-sm flex items-center gap-2"><MapIcon size={14} className="text-blue-400" /> 今日路线</h4>
                {itinerary.length > 1 && (
                    <div className="relative">
                        <select value={selectedDayIdx} onChange={(e) => setSelectedDayIdx(Number(e.target.value))} className="bg-black/30 border border-white/10 text-xs text-white rounded px-2 py-1 outline-none appearance-none pr-6 cursor-pointer hover:bg-black/50 transition-colors">
                            {itinerary.map((d, i) => <option key={i} value={i}>Day {d.day}</option>)}
                        </select>
                        <ChevronDown size={12} className="absolute right-2 top-1.5 text-gray-400 pointer-events-none" />
                    </div>
                )}
            </div>
            <div className="space-y-0 relative z-10 pl-2">
                {day.activities.slice(0, 4).map((act, i) => {
                    const isLast = i === Math.min(day.activities.length, 4) - 1;
                    return (
                        <div key={i} className="flex gap-3 relative pb-4 last:pb-0">
                            {!isLast && <div className="absolute left-[9px] top-5 bottom-0 w-0.5 bg-white/10"></div>}
                            <div className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center flex-shrink-0 mt-0.5 z-10 text-[10px] text-blue-300 font-bold font-mono">{i + 1}</div>
                            <div className="min-w-0"><div className="text-xs font-bold text-gray-200 truncate">{safeRender(act.title)}</div>{i < 3 && <div className="text-[10px] text-gray-500 mt-0.5">↓ 约2.5km</div>}</div>
                        </div>
                    );
                })}
                {day.activities.length > 4 && <div className="text-center text-[10px] text-gray-500 mt-2">...还有 {day.activities.length - 4} 个地点</div>}
            </div>
            <div className="absolute bottom-0 right-0 w-full h-24 bg-gradient-to-t from-black/80 to-transparent z-0 pointer-events-none"></div>
            <div className="absolute inset-0 bg-[url('https://api.mapbox.com/styles/v1/mapbox/dark-v10/static/116.40,39.90,12,0/300x400?access_token=pk.xxx')] bg-cover opacity-10 z-0 mix-blend-overlay"></div>
            <button className="w-full mt-4 py-1.5 bg-white/5 hover:bg-white/10 border border-white/5 rounded text-xs text-blue-300 transition-colors z-10 relative">查看完整地图</button>
        </div>
    );
};

const WeatherTrendWidget = ({ weatherData, destination }) => {
    const getIcon = (cond) => {
        if (!cond) return <CloudSun size={14} className="text-gray-400" />;
        if (cond.includes('雨')) return <Umbrella size={14} className="text-blue-400" />;
        if (cond.includes('雪')) return <Umbrella size={14} className="text-blue-200" />;
        if (cond.includes('晴')) return <Sun size={14} className="text-yellow-400" />;
        return <CloudSun size={14} className="text-gray-400" />;
    };
    const forecast = weatherData && weatherData.length > 0 ? weatherData : [{ day: "今天", temp: "--", cond: "加载中" }, { day: "明天", temp: "--", cond: "..." }];
    const hasBadWeather = weatherData && weatherData.some(f => f.cond && (f.cond.includes("雨") || f.cond.includes("雪")));

    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4"><h4 className="font-bold text-white text-sm flex items-center gap-2"><CloudSun size={14} className="text-yellow-400" /> 天气趋势</h4><span className="text-[10px] text-gray-500">{safeRender(destination) || "未知"}</span></div>
            <div className="space-y-3">{forecast.map((f, i) => (<div key={i} className="flex items-center justify-between text-xs group"><div className="w-8 text-gray-400">{safeRender(f.day)}</div><div className="flex-1 flex justify-center">{getIcon(f.cond)}</div><div className="w-12 text-right font-mono text-white">{safeRender(f.temp)}°C</div><div className="w-12 text-right text-gray-500 truncate">{safeRender(f.cond)}</div></div>))}</div>
            {hasBadWeather && (<div className="mt-4 bg-blue-900/20 border border-blue-500/20 rounded p-2 flex gap-2 items-start"><Lightbulb size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" /><p className="text-[10px] text-blue-200 leading-relaxed">未来几天可能有雨雪，建议调整户外行程。</p></div>)}
        </div>
    );
};

const LocalNewsWidget = ({ newsData, onRefresh, isLoading }) => (
    <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
        <div className="flex justify-between items-center mb-4"><h4 className="font-bold text-white text-sm flex items-center gap-2"><Newspaper size={14} className="text-pink-400" /> 当地资讯</h4><button onClick={onRefresh} className={`text-gray-500 hover:text-white transition-colors ${isLoading ? 'animate-spin' : ''}`} title="刷新"><RefreshCw size={12} /></button></div>
        <div className="space-y-4">
            {newsData && newsData.length > 0 ? newsData.map((news, i) => (<div key={i} className="group cursor-pointer"><div className="flex justify-between items-start gap-2 mb-1"><h5 className="text-xs text-gray-200 font-medium group-hover:text-blue-400 transition-colors line-clamp-1">{safeRender(news.title)}</h5></div><div className="flex justify-between items-center"><p className="text-[10px] text-gray-500 line-clamp-1">AI 实时抓取中...</p><span className={`text-[9px] px-1.5 py-0.5 rounded flex-shrink-0 ${news.tag === '警告' ? 'text-red-400 bg-red-400/10' : 'text-blue-400 bg-blue-400/10'}`}>{safeRender(news.tag)}</span></div>{i < newsData.length - 1 && <div className="h-[1px] bg-white/5 mt-3"></div>}</div>)) : <div className="text-center text-xs text-gray-500 py-4">点击刷新获取最新资讯</div>}
        </div>
    </div>
);

const BudgetDashboardWidget = ({ budgetData }) => {
    const total = budgetData ? 5000 : 0; const spent = budgetData ? 3372 : 0; const percent = total > 0 ? (spent / total) * 100 : 0;
    return (
        <div className="bg-[#1a1d2d]/90 border border-white/10 rounded-2xl p-4 animate-fadeIn">
            <div className="flex justify-between items-center mb-4"><h4 className="font-bold text-white text-sm flex items-center gap-2"><TrendingUp size={14} className="text-emerald-400" /> 预算仪表盘</h4><button className="text-gray-500 hover:text-white transition-colors"><Edit3 size={12} /></button></div>
            <div className="mb-4"><div className="flex justify-between text-xs mb-1.5"><span className="text-gray-400">总预算</span><span className="text-white font-mono font-bold">¥{total}</span></div><div className="h-2 bg-gray-700 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-1000" style={{ width: `${percent}%` }}></div></div><div className="flex justify-between text-[10px] mt-1.5"><span className="text-emerald-400">{Math.round(percent)}% 已规划</span><span className="text-gray-500">剩余 ¥{total - spent}</span></div></div>
            <div className="space-y-2">
                {[{ label: "住宿 (3晚)", val: "1032", icon: Hotel, color: "text-blue-400" }, { label: "门票", val: "860", icon: Ticket, color: "text-yellow-400" }, { label: "交通", val: "280", icon: Car, color: "text-cyan-400" }, { label: "餐饮 (预估)", val: "1200", icon: Utensils, color: "text-orange-400" }].map((item, i) => (<div key={i} className="flex items-center justify-between bg-white/5 rounded px-2 py-1.5"><div className="flex items-center gap-2 text-xs text-gray-300"><item.icon size={10} className={item.color} /> {item.label}</div><div className="text-xs font-mono text-white">¥{item.val}</div></div>))}
            </div>
            <button className="w-full mt-3 text-[10px] text-gray-500 hover:text-white transition-colors text-right">导出费用明细 →</button>
        </div>
    );
};

// --- Smart Sidebar & Layout Controller ---
const SmartSidebar = ({ destination, itinerary, budget, sidebarInfo, onRefreshSidebar, isSidebarLoading, isMobile, isDrawer, onClose }) => {
    return (
        <div className={`flex flex-col gap-4 animate-fadeIn ${isMobile || isDrawer ? 'pb-20' : 'sticky top-4 h-[calc(100vh-8rem)] overflow-y-auto custom-scrollbar pr-2'}`}>
            {(isMobile || isDrawer) && (
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        {isMobile && <button onClick={onClose} className="p-1 bg-white/10 rounded-full"><ChevronLeft size={20} className="text-white" /></button>}
                        <h3 className="text-lg font-bold text-white flex items-center gap-2"><BrainCircuit size={20} className="text-blue-400" /> 智囊助手</h3>
                    </div>
                    {isDrawer && <button onClick={onClose} className="p-1 bg-white/10 rounded-full hover:bg-white/20 transition-colors"><XCircle size={20} className="text-gray-400 hover:text-white" /></button>}
                </div>
            )}
            <MiniMapWidget itinerary={itinerary} />
            <WeatherTrendWidget weatherData={sidebarInfo?.forecast} destination={destination} />
            <LocalNewsWidget newsData={sidebarInfo?.news} onRefresh={() => onRefreshSidebar(destination)} isLoading={isSidebarLoading} />
            <BudgetDashboardWidget budgetData={budget} />
        </div>
    );
};

// --- ActivityDetailModal ---
const ActivityDetailModal = ({ isOpen, onClose, activity, destination }) => {
    const [formData, setFormData] = useState(activity || {});
    const [isGeneratingCaptions, setIsGeneratingCaptions] = useState(false);
    const [captions, setCaptions] = useState(null);
    const [story, setStory] = useState(null);
    const [reviews, setReviews] = useState(null);
    const [dishes, setDishes] = useState(null);
    const [directionCard, setDirectionCard] = useState(null);
    const [photoGuide, setPhotoGuide] = useState(null);
    const [isTellingStory, setIsTellingStory] = useState(false);
    const [isRecommendingFood, setIsRecommendingFood] = useState(false);
    const [isGettingReviews, setIsGettingReviews] = useState(false);
    const [isGettingDirection, setIsGettingDirection] = useState(false);
    const [isGettingPhotoGuide, setIsGettingPhotoGuide] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => { if (activity) setFormData(activity); }, [activity]);
    if (!isOpen || !activity) return null;

    const handleGenerateCaptions = async () => { setIsGeneratingCaptions(true); const data = await callGemini(`Generate 3 captions for ${activity.title}`, true); setCaptions(data); setIsGeneratingCaptions(false); };
    const handleTellStory = async () => { setIsTellingStory(true); const text = await callGemini(`Story about ${activity.title}`, false); setStory(text); setIsTellingStory(false); };
    const handleRecommendDishes = async () => { setIsRecommendingFood(true); const data = await callGemini(`Food at ${activity.title}`, true); setDishes(data); setIsRecommendingFood(false); };
    const handleGetDirectionCard = async () => { setIsGettingDirection(true); const data = await callGemini(`Directions to ${activity.title}`, true); setDirectionCard(data); setIsGettingDirection(false); };
    const handleGetPhotoGuide = async () => { setIsGettingPhotoGuide(true); const data = await callGemini(`Photo guide for ${activity.title}`, true); setPhotoGuide(data); setIsGettingPhotoGuide(false); };
    const handleGenerateReviews = async () => { setIsGettingReviews(true); const data = await callGemini(`Reviews for ${activity.title}`, true); setReviews(data); setIsGettingReviews(false); };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
            <div className="bg-[#1a1d2d] border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="h-56 relative overflow-hidden group"><img src={activity.image_url || `https://source.unsplash.com/800x400/?${activity.image_keyword || activity.type}`} className="w-full h-full object-cover" alt={activity.title} /><div className="absolute inset-0 bg-gradient-to-t from-[#1a1d2d] via-transparent to-transparent"></div><button onClick={onClose} className="absolute top-4 right-4 bg-black/40 hover:bg-black/60 text-white p-2 rounded-full backdrop-blur-md transition-all"><X size={20} /></button></div>
                <div className="flex flex-col flex-1 overflow-hidden bg-[#1a1d2d]"><div className="px-6 pt-6 pb-2"><div className="flex justify-between items-start"><div><h2 className="text-2xl font-bold text-white mb-1 flex items-center gap-2">{safeRender(formData.title)}</h2><div className="flex items-center gap-2 text-gray-400 text-sm mt-1"><MapPin size={14} /> <span>{safeRender(destination)}</span></div></div></div></div><div className="flex-1 p-6 text-gray-300 text-sm">{safeRender(typeof activity.desc === 'string' ? activity.desc : JSON.stringify(activity.desc))}</div></div>
            </div>
        </div>
    );
};

// --- Itinerary Timeline ---
const ItineraryTimeline = ({ days, onGetTips, onActivityClick, onGetDiary, onToggleCheckIn, onGenerateVlog }) => {
    if (!days || days.length === 0) return <div className="flex flex-col items-center justify-center py-20 text-gray-500"><Sparkles size={48} className="mb-4 opacity-20" /><p>暂无行程，请在左侧告诉 AI 您的旅行计划</p></div>;
    return (
        <div className="space-y-8 animate-fadeIn">
            {days.map((day, dayIdx) => (
                <div key={dayIdx} className="relative pl-6 border-l-2 border-white/10 pb-2">
                    <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-blue-500 ring-4 ring-gray-900/50"></div>
                    <div className="mb-6 flex justify-between items-start"><div><h3 className="text-lg lg:text-xl font-bold text-white mb-1 flex items-center gap-2"><span className="text-blue-400">Day {day.day}</span> {safeRender(day.title)}</h3></div><div className="flex gap-2"><button onClick={() => onGenerateVlog(day)} className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white"><Video size={14} className="text-purple-400" /><span>脚本</span></button><button onClick={() => onGetTips(day)} className="group flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-xs font-medium text-gray-300 hover:text-white"><Lightbulb size={14} className="text-yellow-500" /><span>AI 攻略</span></button></div></div>
                    <div className="space-y-6">{day.activities.map((act, actIdx) => { const isChecked = act.checked; const isHotelReturn = act.type === 'hotel' || act.title.includes('酒店') || act.title.includes('入住'); return (<div key={actIdx} onClick={() => onActivityClick(dayIdx, actIdx, act)} className={`group relative flex gap-4 ${isHotelReturn ? 'opacity-80' : ''}`}>{!isHotelReturn && (<div className="w-24 h-24 sm:w-32 sm:h-32 flex-shrink-0 rounded-xl overflow-hidden bg-gray-800 border border-white/10 relative"><img src={`https://source.unsplash.com/300x300/?${act.image_keyword || act.title},travel`} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" alt={act.title} /><div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div></div>)}<div className={`flex-1 bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-all cursor-pointer ${isHotelReturn ? 'bg-blue-900/10 border-blue-500/20' : ''}`}><div className="flex justify-between items-start mb-2"><div className="flex items-center gap-2"><span className={`text-xs font-mono px-1.5 py-0.5 rounded ${isHotelReturn ? 'bg-blue-500/20 text-blue-300' : 'bg-gray-700 text-gray-300'}`}>{safeRender(act.time)}</span><h4 className={`font-bold text-white ${isChecked ? 'line-through text-gray-500' : ''}`}>{safeRender(act.title)}</h4></div><button onClick={(e) => { e.stopPropagation(); onToggleCheckIn(dayIdx, actIdx); }} className={`p-1 rounded-full transition-colors ${isChecked ? 'text-green-400' : 'text-gray-600 hover:text-white'}`}>{isChecked ? <CheckSquare size={16} /> : <CheckCircle2 size={16} />}</button></div><p className="text-sm text-gray-400 leading-relaxed line-clamp-2">{safeRender(act.desc)}</p>{isHotelReturn && <div className="mt-2 text-xs text-blue-400 flex items-center gap-1"><Hotel size={12} /> 住宿安排</div>}</div></div>); })}</div>
                </div>
            ))}
        </div>
    );
};

// --- Main App Component ---

export default function TravelMindApp() {
    const [user, setUser] = useState(null);
    const [loadingAuth, setLoadingAuth] = useState(true);
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([{ role: 'ai', content: '你好！我是 TravelMind。你的智能行程管家。\n\n请告诉我你想去哪里，玩几天？\n例如："帮我规划一个北京4天3晚的亲子游，想去环球影城"', isStreaming: false }]);
    const [isTyping, setIsTyping] = useState(false);
    const [activeTab, setActiveTab] = useState('itinerary');
    const [mobileView, setMobileView] = useState('chat'); // 'chat' | 'dashboard' | 'sidebar'
    const [showSidebarDrawer, setShowSidebarDrawer] = useState(false); // For Tablet/LG Screens

    // Core Data & Modals State
    const [itineraryData, setItineraryData] = useState([]);
    const [poiData, setPoiData] = useState([]);
    const [destination, setDestination] = useState("未知目的地");
    const [tripStatus, setTripStatus] = useState("Planning");
    const [weather, setWeather] = useState({ temp: "--", condition: "未知" });
    const [sidebarInfo, setSidebarInfo] = useState({ forecast: [], news: [] });
    const [isSidebarLoading, setIsSidebarLoading] = useState(false);

    const [packingListData, setPackingListData] = useState(null);
    const [budgetData, setBudgetData] = useState(null);
    const [playlistData, setPlaylistData] = useState(null);
    const [emergencyData, setEmergencyData] = useState(null);
    const [cultureData, setCultureData] = useState(null);
    const [souvenirData, setSouvenirData] = useState(null);
    const [photoChallengeData, setPhotoChallengeData] = useState(null);
    const [posterData, setPosterData] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalTitle, setModalTitle] = useState('');
    const [modalContent, setModalContent] = useState(null);
    const [modalContentType, setModalContentType] = useState('text');
    const [isGeminiLoading, setIsGeminiLoading] = useState(false);
    const [currentDayForTip, setCurrentDayForTip] = useState(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [selectedActivity, setSelectedActivity] = useState(null);
    const [selectedActivityPath, setSelectedActivityPath] = useState(null);
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);
    const messagesEndRef = useRef(null);

    useEffect(() => { const initAuth = async () => { setLoadingAuth(true); try { if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) { await signInWithCustomToken(auth, __initial_auth_token); } else { await signInAnonymously(auth); } } catch (error) { console.error("Auth failed", error); setLoadingAuth(false); } }; initAuth(); const unsubscribe = onAuthStateChanged(auth, (currentUser) => { setUser(currentUser); setLoadingAuth(false); }); return () => unsubscribe(); }, []);
    useEffect(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, isTyping]);

    const updateSidebarInfo = async (dest) => {
        if (!dest || dest === "未知目的地") return;
        setIsSidebarLoading(true);
        const prompt = `
            You are a local travel expert for "${dest}". 
            Task: Generate real-time travel dashboard data.
            Return ONLY JSON with this structure:
            {
                "forecast": [
                    {"day": "Mon", "temp": 22, "cond": "Sunny"},
                    {"day": "Tue", "temp": 20, "cond": "Cloudy"},
                    {"day": "Wed", "temp": 18, "cond": "Rain"},
                    {"day": "Thu", "temp": 21, "cond": "Sunny"},
                    {"day": "Fri", "temp": 23, "cond": "Cloudy"}
                ],
                "news": [
                    {"title": "Breaking travel news/event for ${dest} (max 15 chars)", "tag": "Event"},
                    {"title": "Important safety or transport warning (max 15 chars)", "tag": "Warning"},
                    {"title": "Useful local tip (max 15 chars)", "tag": "Info"}
                ]
            }
            Make sure the weather is realistic for the current season in ${dest}.
        `;
        const data = await callGemini(prompt, true);
        if (data) { setSidebarInfo(data); }
        setIsSidebarLoading(false);
    };

    const handleSend = async () => {
        if (!input.trim()) return;
        const userMsg = input; setInput(''); setMessages(prev => [...prev, { role: 'user', content: userMsg, isStreaming: false }]); setIsTyping(true);
        const prompt = `User Request: "${userMsg}"\nCurrent Context: Destination is ${destination}.\nYou are "TravelMind". MANDATORY PLANNING RULES:\n1. BUDGET: Moderate/Economy (300-600 CNY/night).\n2. ACCOMMODATION: Explicitly include "Check-in" or "Return to hotel" each day. Recommend SPECIFIC hotel names.\n3. TRANSPORT: State START point for travel times.\n4. IMAGES: Provide short English "image_keyword".\n5. COORDINATES: Provide lat/lng for each activity if possible, e.g., "lat": 39.9, "lng": 116.4.\nReturn JSON:\n{"chat_response": "...", "destination_detected": "...", "status_update": "Created", "weather_forecast": {"temp": "20°C", "condition": "Sunny"}, "itinerary": [{"day": 1, "title": "Theme", "activities": [{"time": "09:00", "title": "Place", "type": "sight", "desc": "...", "image_keyword": "...", "lat": 39.9, "lng": 116.4}]}], "pois": [{"name": "Hotel", "type": "hotel", "price": "¥450", "tags": [], "rating": 4.6}]}`;
        const data = await callGemini(prompt, true); setIsTyping(false);
        if (data) {
            const chatText = data.chat_response || "收到！"; setMessages(prev => [...prev, { role: 'ai', content: "", isStreaming: true }]); simulateStream(chatText, (chunk) => { setMessages(prev => { const last = prev[prev.length - 1]; if (last.role === 'ai' && last.isStreaming) { return [...prev.slice(0, -1), { ...last, content: last.content + chunk }]; } return prev; }); }, () => { setMessages(prev => { const last = prev[prev.length - 1]; return [...prev.slice(0, -1), { ...last, isStreaming: false }]; }); if (data.destination_detected) { setDestination(data.destination_detected); updateSidebarInfo(data.destination_detected); } if (data.status_update) setTripStatus(data.status_update); if (data.weather_forecast) setWeather(data.weather_forecast); if (data.itinerary && data.itinerary.length > 0) { setItineraryData(data.itinerary); setActiveTab('itinerary'); } if (data.pois && data.pois.length > 0) setPoiData(data.pois); });
        } else { setMessages(prev => [...prev, { role: 'ai', content: "网络开小差了，请重试一下。", isStreaming: false }]); }
    };

    const handleGetDayTips = async (day) => { setCurrentDayForTip(day); setModalTitle(`${day.title} - AI 攻略`); setModalContentType('tips'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Tips for ${day.title} in ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGeneratePackingList = async () => { setModalTitle("🎒 智能行李清单"); setModalContentType('packing'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Packing list for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleEstimateBudget = async () => { setModalTitle("💰 智能预算估算"); setModalContentType('budget'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Budget for ${destination}`, true); if (data) { setBudgetData(data); setModalContent(data); } setIsGeminiLoading(false); };
    const handleGeneratePlaylist = async () => { setModalTitle("🎵 AI 氛围歌单"); setModalContentType('playlist'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Playlist for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGenerateEmergency = async () => { setModalTitle("🆘 智能紧急助手"); setModalContentType('emergency'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Emergency info for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGenerateCulture = async () => { setModalTitle("🌍 本地文化锦囊"); setModalContentType('culture'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Culture guide for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGenerateSouvenirs = async () => { setModalTitle("🎁 伴手礼顾问"); setModalContentType('souvenirs'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Souvenirs for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGeneratePhotoChallenge = async () => { setModalTitle("📸 城市摄影挑战"); setModalContentType('photo_challenge'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Photo challenges for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGenerateVlog = async (day) => { setModalTitle(`🎬 ${day.title} - Vlog 脚本`); setModalContentType('vlog'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Vlog script for ${day.title}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };
    const handleGenerateDiary = async (day) => { setModalTitle(`📝 ${day.title} - 旅行日记`); setModalContentType('diary'); setIsModalOpen(true); setModalContent(null); setIsGeminiLoading(true); const prompt = `Write a first-person travel diary entry for Day ${day.day} in ${destination}. Activities: ${day.activities.map(a => a.title).join(', ')}. Tone: Emotional, vivid, and personal (in Chinese). Format: Markdown.`; const text = await callGemini(prompt, false); setModalContent(text); setIsGeminiLoading(false); };
    const handleGeneratePoster = async () => { setModalTitle("🖼️ 分享海报预览"); setModalContentType('poster'); setIsModalOpen(true); setIsGeminiLoading(true); const data = await callGemini(`Poster content for ${destination}`, true); if (data) setModalContent(data); setIsGeminiLoading(false); };

    const handleLogin = async () => { setLoadingAuth(true); try { if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) { await signInWithCustomToken(auth, __initial_auth_token); } else { await signInAnonymously(auth); } } catch (error) { console.error("Login failed", error); setLoadingAuth(false); } };
    const handleLogout = async () => await signOut(auth);
    const handleVoiceInput = () => { if (isListening) { recognitionRef.current?.stop(); setIsListening(false); return; } const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SpeechRecognition) { alert("浏览器不支持"); return; } const recognition = new SpeechRecognition(); recognition.lang = 'zh-CN'; recognition.onstart = () => setIsListening(true); recognition.onend = () => setIsListening(false); recognition.onresult = (e) => setInput(e.results[0][0].transcript); recognitionRef.current = recognition; recognition.start(); };
    const handleActivityClick = (dayIdx, actIdx, act) => { setSelectedActivityPath({ type: 'itinerary', dayIdx, actIdx }); setSelectedActivity(act); setDetailModalOpen(true); };
    const handleToggleCheckIn = (dayIdx, actIdx) => { const newData = [...itineraryData]; newData[dayIdx].activities[actIdx].checked = !newData[dayIdx].activities[actIdx].checked; setItineraryData(newData); };
    const handleRegenerate = () => { if (modalContentType === 'packing') handleGeneratePackingList(); else if (modalContentType === 'tips' && currentDayForTip) handleGetDayTips(currentDayForTip); else if (modalContentType === 'budget') handleEstimateBudget(); else if (modalContentType === 'playlist') handleGeneratePlaylist(); else if (modalContentType === 'emergency') handleGenerateEmergency(); else if (modalContentType === 'culture') handleGenerateCulture(); else if (modalContentType === 'souvenirs') handleGenerateSouvenirs(); else if (modalContentType === 'photo_challenge') handleGeneratePhotoChallenge(); else if (modalContentType === 'vlog' && currentDayForTip) handleGenerateVlog(currentDayForTip); else if (modalContentType === 'diary' && currentDayForTip) handleGenerateDiary(currentDayForTip); else if (modalContentType === 'poster') handleGeneratePoster(); };

    if (loadingAuth) return <div className="flex h-screen items-center justify-center bg-[#0f111a]"><Loader2 className="animate-spin text-blue-500" size={48} /></div>;
    if (!user) return <div className="flex h-screen w-full items-center justify-center bg-[#0f111a] text-white"><button onClick={handleLogin} className="px-6 py-3 bg-blue-600 rounded-xl font-bold hover:bg-blue-700">立即体验 TravelMind</button></div>;

    return (
        <div className="flex h-screen w-full bg-[#0f111a] text-gray-200 font-sans overflow-hidden">
            <GeminiModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={modalTitle} content={modalContent} contentType={modalContentType} isLoading={isGeminiLoading} onRegenerate={handleRegenerate} />
            <ActivityDetailModal isOpen={detailModalOpen} onClose={() => setDetailModalOpen(false)} activity={selectedActivity} destination={destination} />

            {/* Background */}
            <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden z-0"><div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px]"></div><div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-blue-900/10 rounded-full blur-[120px]"></div></div>

            {/* Mobile Nav - UPDATED with 3 Tabs */}
            <div className="lg:hidden fixed bottom-0 left-0 w-full h-16 bg-[#131520] border-t border-white/10 z-50 flex justify-around items-center px-2 safe-area-bottom">
                <button onClick={() => setMobileView('chat')} className={`flex flex-col items-center p-2 ${mobileView === 'chat' ? 'text-blue-400' : 'text-gray-500'}`}><MessageSquare size={20} /><span className="text-[10px] mt-1">聊天</span></button>
                <button onClick={() => setMobileView('dashboard')} className={`flex flex-col items-center p-2 ${mobileView === 'dashboard' ? 'text-blue-400' : 'text-gray-500'}`}><Layout size={20} /><span className="text-[10px] mt-1">行程</span></button>
                <button onClick={() => setMobileView('sidebar')} className={`flex flex-col items-center p-2 ${mobileView === 'sidebar' ? 'text-blue-400' : 'text-gray-500'}`}><BrainCircuit size={20} /><span className="text-[10px] mt-1">智囊</span></button>
            </div>

            {/* Sidebar Overlay for LG screens (Drawer) */}
            {showSidebarDrawer && (
                <div className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm lg:flex xl:hidden" onClick={() => setShowSidebarDrawer(false)}>
                    <div className="absolute right-0 top-0 h-full w-80 bg-[#0f111a] border-l border-white/10 shadow-2xl p-4 overflow-y-auto" onClick={e => e.stopPropagation()}>
                        <SmartSidebar destination={destination} weather={weather} itinerary={itineraryData} budget={budgetData} sidebarInfo={sidebarInfo} onRefreshSidebar={updateSidebarInfo} isSidebarLoading={isSidebarLoading} isDrawer={true} onClose={() => setShowSidebarDrawer(false)} />
                    </div>
                </div>
            )}

            {/* Layout Container */}
            <div className="flex w-full h-full">

                {/* 1. Left Chat Column (Fixed Width on Large Screens) */}
                <div className={`${mobileView === 'chat' ? 'flex' : 'hidden lg:flex'} w-full lg:w-[280px] xl:w-[320px] flex-col border-r border-white/5 relative z-10 bg-[#0f111a]/50 backdrop-blur-sm flex-shrink-0 transition-all duration-300`}>
                    <div className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-white/5 backdrop-blur-md"><div className="flex items-center gap-2"><div className="bg-gradient-to-br from-blue-500 to-purple-600 p-1.5 rounded-lg"><Navigation size={18} className="text-white" /></div><span className="font-bold text-lg tracking-tight text-white">TravelMind</span></div><button onClick={handleLogout} className="p-2 hover:bg-red-500/10 hover:text-red-400 text-gray-400 rounded-full"><LogOut size={18} /></button></div>
                    <div className="flex-1 overflow-y-auto p-4 custom-scrollbar pb-24 lg:pb-4">{messages.map((msg, i) => <ChatMessage key={i} {...msg} />)}{isTyping && <ChatMessage role="ai" content="" isTyping={true} isStreaming={true} />}<div ref={messagesEndRef} /></div>
                    <div className="p-4 border-t border-white/5 bg-[#0f111a] lg:pb-4 pb-20"><div className="relative flex items-center bg-white/5 border border-white/10 rounded-2xl px-2 focus-within:border-blue-500/50 transition-all"><button onClick={handleVoiceInput} className={`p-2 mr-2 rounded-full ${isListening ? 'bg-red-500/20 text-red-500 animate-pulse' : 'text-gray-400 hover:text-white'}`}><Mic size={20} /></button><input type="text" className="flex-1 bg-transparent border-none text-white px-2 py-4 focus:ring-0 placeholder-gray-500 outline-none" placeholder={isListening ? "正在聆听..." : "输入你的旅行计划..."} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} /><button onClick={handleSend} className={`p-2 rounded-xl transition-all ${input.trim() ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-500'}`}><Send size={18} /></button></div></div>
                </div>

                {/* 2. Middle Dashboard Column (Fluid) */}
                <div className={`${mobileView === 'dashboard' ? 'flex' : 'hidden lg:flex'} flex-1 flex-col relative z-10 bg-gradient-to-br from-[#131620] to-[#0b0c12] min-w-0 pb-16 lg:pb-0`}>
                    <div className="h-16 border-b border-white/5 flex items-center justify-between px-4 lg:px-8 bg-white/2 flex-shrink-0">
                        <div className="flex items-center gap-3"><h2 className="text-white font-semibold">{safeRender(destination)} 之旅</h2><span className="text-[10px] uppercase px-2 py-0.5 rounded-full border bg-emerald-500/20 text-emerald-400 border-emerald-500/20">{safeRender(tripStatus)}</span></div>
                        {/* Top Icons Menu - Only visible on XL screens where sidebar is expanded, or as quick actions */}
                        <div className="hidden xl:flex items-center gap-2">
                            {[{ icon: Banknote, action: handleEstimateBudget, color: "emerald", label: "预算" }, { icon: Backpack, action: handleGeneratePackingList, color: "blue", label: "行李" }, { icon: Music, action: handleGeneratePlaylist, color: "violet", label: "歌单" }, { icon: Siren, action: handleGenerateEmergency, color: "red", label: "求助" }, { icon: ImageIcon, action: handleGeneratePoster, color: "sky", label: "海报" }].map((btn, i) => (
                                <button key={i} onClick={() => btn.action()} className={`flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-${btn.color}-500/20 to-${btn.color}-600/20 hover:from-${btn.color}-500/30 hover:to-${btn.color}-600/30 border border-${btn.color}-500/30 rounded-full text-xs lg:text-sm font-medium text-${btn.color}-400 transition-all hover:scale-105 whitespace-nowrap`}><btn.icon size={14} /><span>{btn.label}</span></button>
                            ))}
                        </div>

                        {/* Mobile/Tablet Compact Menu (Restored & Updated) */}
                        <div className="hidden md:flex xl:hidden items-center gap-2">
                            {[
                                { icon: Banknote, action: handleEstimateBudget, color: "emerald", label: "预算" },
                                { icon: Backpack, action: handleGeneratePackingList, color: "blue", label: "行李" },
                                { icon: Music, action: handleGeneratePlaylist, color: "violet", label: "歌单" },
                                { icon: Siren, action: handleGenerateEmergency, color: "red", label: "求助" },
                                { icon: ImageIcon, action: handleGeneratePoster, color: "sky", label: "海报" }
                            ].map((btn, i) => (
                                <button key={i} onClick={() => btn.action()} className={`p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-${btn.color}-400 transition-all hover:scale-105`} title={btn.label}>
                                    <btn.icon size={16} />
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar">
                        <div className="max-w-5xl mx-auto">
                            <div className="flex gap-1 bg-white/5 p-1 rounded-xl w-fit border border-white/5 mb-6">
                                {[{ id: 'itinerary', icon: Calendar, label: '行程' }, { id: 'pois', icon: Hotel, label: '住宿' }, { id: 'map', icon: MapIcon, label: '地图' }].map(tab => (
                                    <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-3 lg:px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}><tab.icon size={16} />{tab.label}</button>
                                ))}
                            </div>

                            {activeTab === 'itinerary' && <ItineraryTimeline days={itineraryData} onGetTips={handleGetDayTips} onActivityClick={handleActivityClick} onGetDiary={handleGenerateDiary} onToggleCheckIn={handleToggleCheckIn} onGenerateVlog={handleGenerateVlog} />}
                            {activeTab === 'pois' && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {poiData.length > 0 ? poiData.map((poi, idx) => (<div key={idx} className="group relative overflow-hidden rounded-2xl bg-gray-800 border border-white/10 shadow-xl hover:shadow-2xl transition-all duration-300 flex flex-col"><div className="h-40 bg-gray-700 relative overflow-hidden"><img src={`https://source.unsplash.com/600x400/?hotel,${poi.type},interior`} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" alt={poi.name} /><div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm px-2 py-1 rounded-lg flex items-center gap-1 text-xs font-bold text-yellow-400"><Star size={12} fill="currentColor" /> {poi.rating || "4.5"}</div></div><div className="p-4 flex-1 flex flex-col"><h3 className="font-bold text-white truncate">{poi.name}</h3><div className="flex items-center justify-between mt-2 mb-3"><span className="text-blue-400 font-mono font-bold">{poi.price || "¥350起"}</span><div className="flex gap-1 flex-wrap justify-end">{poi.tags && poi.tags.map((tag, i) => (<span key={i} className="text-[10px] bg-white/10 text-gray-300 px-1.5 py-0.5 rounded">{tag}</span>))}</div></div><button className="w-full mt-auto bg-white/5 hover:bg-blue-600 hover:text-white text-gray-300 py-2 rounded-lg text-xs font-medium transition-colors border border-white/10">查看详情</button></div></div>)) : <div className="text-center text-gray-500 py-10"><Hotel size={48} className="mx-auto mb-4 opacity-20" /><p>AI 正在根据您的预算搜索高性价比住宿...</p></div>}
                                </div>
                            )}
                            {activeTab === 'map' && <div className="h-[500px] bg-gray-800/50 rounded-3xl border border-white/10 flex items-center justify-center relative overflow-hidden group"><RealMap itinerary={itineraryData} destination={destination} /></div>}
                        </div>
                    </div>
                </div>

                {/* 3. Right Sidebar Column (Fixed Width on XL, Collapsed on LG, Full on Mobile) */}
                <div className={`${mobileView === 'sidebar' ? 'flex fixed inset-0 z-50 bg-[#0f111a]' : 'hidden xl:flex'} w-full xl:w-[320px] flex-col border-l border-white/5 relative z-10 bg-[#0f111a]/80 backdrop-blur-sm flex-shrink-0`}>
                    <div className="flex-1 overflow-y-auto p-4 custom-scrollbar pb-20 xl:pb-4">
                        <SmartSidebar destination={destination} weather={weather} itinerary={itineraryData} budget={budgetData} sidebarInfo={sidebarInfo} onRefreshSidebar={updateSidebarInfo} isSidebarLoading={isSidebarLoading} isMobile={mobileView === 'sidebar'} onClose={() => setMobileView('dashboard')} />
                    </div>
                </div>

                {/* LG Screen Sidebar Toggle (Collapsed State - NOW FUNCTIONAL) */}
                <div className="hidden lg:flex xl:hidden w-12 flex-col items-center py-4 border-l border-white/5 bg-[#0f111a]">
                    <div className="space-y-4">
                        <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white" title="地图"><MapIcon size={20} /></button>
                        <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white" title="天气"><CloudSun size={20} /></button>
                        <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white" title="资讯"><Newspaper size={20} /></button>
                        <button onClick={() => setShowSidebarDrawer(true)} className="p-2 bg-white/5 rounded-lg text-gray-400 hover:text-white" title="预算"><TrendingUp size={20} /></button>
                    </div>
                </div>

            </div>
        </div>
    );
}