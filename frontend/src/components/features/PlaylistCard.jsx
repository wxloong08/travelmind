/**
 * 氛围歌单卡片
 */

import React from 'react';
import { Music } from 'lucide-react';

export function PlaylistCard({ data }) {
  if (!data) return <div className="text-center text-gray-500">无法获取歌单</div>;

  return (
    <div className="space-y-6">
      {/* 歌单封面 */}
      <div className="bg-gradient-to-r from-violet-900/40 to-fuchsia-900/40 border border-violet-500/20 rounded-2xl p-6 relative overflow-hidden">
        <div className="relative z-10">
          <h3 className="text-violet-200 font-bold text-lg mb-1">
            {data.vibe_title}
          </h3>
          <p className="text-gray-400 text-sm">{data.vibe_desc}</p>
        </div>
        <Music className="absolute right-4 bottom-4 text-violet-500/20 w-24 h-24 rotate-12" />
      </div>

      {/* 歌曲列表 */}
      <div className="space-y-3">
        <h4 className="text-white font-semibold flex items-center gap-2">
          <Music size={18} className="text-violet-400" /> 推荐曲目
        </h4>
        {data.songs?.map((song, i) => (
          <div
            key={i}
            className="flex items-center gap-4 p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-white/5 group"
          >
            <div className="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center text-gray-500 font-bold text-sm group-hover:text-violet-400 transition-colors">
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-200 truncate">{song.title}</div>
              <div className="text-xs text-gray-500 truncate">{song.artist}</div>
            </div>
            {song.reason && (
              <div className="text-[10px] text-gray-600 bg-black/20 px-2 py-1 rounded max-w-[120px] truncate hidden sm:block">
                {song.reason}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default PlaylistCard;
