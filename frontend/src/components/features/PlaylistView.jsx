/**
 * 增强版歌单视图组件
 * 
 * 支持复制歌单和跳转QQ音乐/网易云搜索
 */

import React, { useState } from 'react';
import { Music, Copy, CheckCircle2 } from 'lucide-react';

// 复制到剪贴板（带降级）
const copyToClipboard = (text, onSuccess, onError) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(onSuccess).catch(() => {
            fallbackCopy(text, onSuccess, onError);
        });
    } else {
        fallbackCopy(text, onSuccess, onError);
    }
};

const fallbackCopy = (text, onSuccess, onError) => {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        if (successful) onSuccess?.();
        else throw new Error('execCommand failed');
    } catch (err) {
        console.error('Copy failed', err);
        onError?.();
    }
};

export function PlaylistView({ data }) {
    const [copied, setCopied] = useState(false);

    if (!data) return <div className="text-center text-gray-500">无法获取歌单</div>;

    const handleCopyPlaylist = () => {
        const text = data.songs?.map((s) => `${s.title} ${s.artist}`).join('\n') || '';
        copyToClipboard(
            text,
            () => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            },
            () => alert('复制失败，请手动选择文本复制')
        );
    };

    const openMusicSearch = (service, song) => {
        const query = encodeURIComponent(`${song.title} ${song.artist}`);
        let url = '';
        if (service === 'netease') url = `https://music.163.com/#/search/m/?s=${query}`;
        if (service === 'qq') url = `https://y.qq.com/n/ryqq/search?w=${query}`;
        window.open(url, '_blank');
    };

    return (
        <div className="space-y-6">
            {/* 氛围卡片 */}
            <div className="bg-gradient-to-r from-violet-900/40 to-fuchsia-900/40 border border-violet-500/20 rounded-2xl p-6 relative overflow-hidden">
                <div className="relative z-10">
                    <h3 className="text-violet-200 font-bold text-lg mb-1">{data.vibe_title}</h3>
                    <p className="text-gray-400 text-sm">{data.vibe_desc}</p>
                    <button
                        onClick={handleCopyPlaylist}
                        className="mt-4 flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/10 px-3 py-1.5 rounded-lg text-xs text-white transition-all"
                    >
                        {copied ? (
                            <CheckCircle2 size={12} className="text-green-400" />
                        ) : (
                            <Copy size={12} />
                        )}
                        {copied ? '已复制导入文本' : '复制歌单 (可导入App)'}
                    </button>
                </div>
                <Music className="absolute right-4 bottom-4 text-violet-500/20 w-24 h-24 rotate-12" />
            </div>

            {/* 歌曲列表 */}
            <div className="space-y-3">
                <div className="flex justify-between items-center px-1">
                    <h4 className="text-white font-semibold flex items-center gap-2">
                        <Music size={18} className="text-violet-400" /> 推荐曲目
                    </h4>
                </div>
                {data.songs?.map((song, i) => (
                    <div
                        key={i}
                        className="flex items-center gap-3 p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-white/5 group"
                    >
                        <div className="w-8 h-8 bg-gray-800 rounded-lg flex items-center justify-center text-gray-500 font-bold text-xs group-hover:text-violet-400 transition-colors shrink-0">
                            {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-200 truncate text-sm">{song.title}</div>
                            <div className="text-xs text-gray-500 truncate">{song.artist}</div>
                        </div>

                        {/* 音乐平台跳转 */}
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
                提示：点击"复制歌单"后，可在音乐App中选择"导入外部歌单"
            </div>
        </div>
    );
}

export default PlaylistView;
