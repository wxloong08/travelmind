/**
 * 高德地图组件
 * 
 * 集成 @amap/amap-jsapi-loader
 * 支持 Marker 打点、Polyline 路线、信息窗口
 */

import React, { useEffect, useRef, useState } from 'react';
import AMapLoader from '@amap/amap-jsapi-loader';
import { MapPin, Loader2, Navigation } from 'lucide-react';
import useTravelStore from '../../store/useTravelStore';

// 高德地图 Key (从环境变量获取)
const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || '';
const AMAP_SECRET = import.meta.env.VITE_AMAP_SECRET || '';

// POI 类型颜色映射
const typeColors = {
  sight: '#3B82F6', // blue
  food: '#F97316', // orange
  hotel: '#8B5CF6', // purple
  transport: '#10B981', // green
  default: '#6B7280', // gray
};

// POI 类型图标
const typeIcons = {
  sight: '🏛️',
  food: '🍜',
  hotel: '🏨',
  transport: '🚃',
  default: '📍',
};

export function GaodeMap() {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const polylineRef = useRef(null);
  const infoWindowRef = useRef(null);

  const { itinerary, destination, openDetailModal } = useTravelStore();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mapReady, setMapReady] = useState(false);

  // 初始化地图
  useEffect(() => {
    if (!AMAP_KEY) {
      setError('请配置高德地图 API Key (VITE_AMAP_KEY)');
      setIsLoading(false);
      return;
    }

    let isMounted = true;

    const initMap = async () => {
      try {
        // 设置安全密钥
        if (AMAP_SECRET) {
          window._AMapSecurityConfig = {
            securityJsCode: AMAP_SECRET,
          };
        }

        // 加载高德地图
        const AMap = await AMapLoader.load({
          key: AMAP_KEY,
          version: '2.0',
          plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Geocoder'],
        });

        if (!isMounted || !mapContainerRef.current) return;

        // 创建地图实例
        const map = new AMap.Map(mapContainerRef.current, {
          zoom: 12,
          center: [120.15, 30.28], // 默认杭州
          mapStyle: 'amap://styles/dark', // 暗色主题
        });

        // 添加控件
        map.addControl(new AMap.Scale());
        map.addControl(new AMap.ToolBar({ position: 'RT' }));

        mapInstanceRef.current = map;
        setMapReady(true);
        setIsLoading(false);

        // 如果有目的地，进行地理编码
        if (destination && destination !== '未知目的地') {
          const geocoder = new AMap.Geocoder();
          geocoder.getLocation(destination, (status, result) => {
            if (status === 'complete' && result.geocodes.length) {
              const { lng, lat } = result.geocodes[0].location;
              map.setCenter([lng, lat]);
            }
          });
        }
      } catch (e) {
        console.error('Map initialization failed:', e);
        if (isMounted) {
          setError('地图加载失败，请刷新重试');
          setIsLoading(false);
        }
      }
    };

    initMap();

    return () => {
      isMounted = false;
      // 清理地图实例
      if (mapInstanceRef.current) {
        mapInstanceRef.current.destroy();
      }
    };
  }, []);

  // 更新 Markers
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current) return;

    const map = mapInstanceRef.current;
    const AMap = window.AMap;

    // 清除旧的 Markers
    markersRef.current.forEach((marker) => map.remove(marker));
    markersRef.current = [];

    // 清除旧的 Polyline
    if (polylineRef.current) {
      map.remove(polylineRef.current);
      polylineRef.current = null;
    }

    // 收集所有有坐标的活动
    const activities = [];
    itinerary.forEach((day, dayIdx) => {
      day.activities?.forEach((act, actIdx) => {
        if (act.location?.lat && act.location?.lng) {
          activities.push({
            ...act,
            dayIdx,
            actIdx,
            dayNum: day.day,
          });
        }
      });
    });

    if (activities.length === 0) return;

    // 创建 Markers
    const path = [];
    activities.forEach((act, index) => {
      const position = [act.location.lng, act.location.lat];
      path.push(position);

      const color = typeColors[act.type] || typeColors.default;
      const icon = typeIcons[act.type] || typeIcons.default;

      // 创建自定义 Marker
      const marker = new AMap.Marker({
        position,
        title: act.title,
        content: `
          <div style="
            width: 36px;
            height: 36px;
            background: ${color};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            border: 2px solid white;
            cursor: pointer;
          ">
            ${icon}
          </div>
        `,
        offset: new AMap.Pixel(-18, -18),
      });

      // 点击事件
      marker.on('click', () => {
        // 显示信息窗口
        if (infoWindowRef.current) {
          map.remove(infoWindowRef.current);
        }

        const infoWindow = new AMap.InfoWindow({
          content: `
            <div style="padding: 12px; max-width: 200px;">
              <div style="font-weight: bold; margin-bottom: 4px;">${act.title}</div>
              <div style="font-size: 12px; color: #666;">Day ${act.dayNum} · ${act.time}</div>
              <div style="font-size: 12px; color: #888; margin-top: 4px;">${act.desc || ''}</div>
            </div>
          `,
          offset: new AMap.Pixel(0, -30),
        });

        infoWindow.open(map, position);
        infoWindowRef.current = infoWindow;

        // 打开详情 Modal
        openDetailModal(act, {
          type: 'itinerary',
          dayIdx: act.dayIdx,
          actIdx: act.actIdx,
        });
      });

      map.add(marker);
      markersRef.current.push(marker);
    });

    // 创建 Polyline (路线)
    if (path.length > 1) {
      const polyline = new AMap.Polyline({
        path,
        strokeColor: '#3B82F6',
        strokeWeight: 4,
        strokeOpacity: 0.8,
        strokeStyle: 'dashed',
        strokeDasharray: [10, 5],
      });

      map.add(polyline);
      polylineRef.current = polyline;
    }

    // 自适应显示所有 Markers
    if (activities.length > 0) {
      map.setFitView(markersRef.current, false, [50, 50, 50, 50]);
    }
  }, [itinerary, mapReady, openDetailModal]);

  // 加载状态
  if (isLoading) {
    return (
      <div className="h-full min-h-[400px] bg-gray-800/50 rounded-3xl border border-white/10 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={48} className="mx-auto text-blue-500 animate-spin mb-4" />
          <p className="text-gray-400">地图加载中...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="h-full min-h-[400px] bg-gray-800/50 rounded-3xl border border-white/10 flex items-center justify-center">
        <div className="text-center p-6">
          <MapPin size={48} className="mx-auto text-red-500 mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">地图加载失败</h3>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // 无行程数据
  const hasActivitiesWithLocation = itinerary.some((day) =>
    day.activities?.some((act) => act.location?.lat && act.location?.lng)
  );

  return (
    <div className="h-full min-h-[400px] relative">
      {/* 地图容器 */}
      <div
        ref={mapContainerRef}
        className="w-full h-full min-h-[400px] rounded-3xl overflow-hidden"
      />

      {/* 无坐标数据提示 */}
      {!hasActivitiesWithLocation && mapReady && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm rounded-3xl flex items-center justify-center">
          <div className="text-center p-6">
            <Navigation size={48} className="mx-auto text-blue-500 mb-4 animate-bounce" />
            <h3 className="text-xl font-bold text-white mb-2">地图模式</h3>
            <p className="text-gray-400 text-sm">
              生成行程后，地图将显示所有景点位置和游览路线
            </p>
          </div>
        </div>
      )}

      {/* 图例 */}
      {hasActivitiesWithLocation && (
        <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur-sm rounded-xl p-3 border border-white/10">
          <div className="text-xs text-gray-400 mb-2">图例</div>
          <div className="flex gap-3">
            {Object.entries(typeColors).map(([type, color]) => {
              if (type === 'default') return null;
              return (
                <div key={type} className="flex items-center gap-1">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ background: color }}
                  />
                  <span className="text-xs text-gray-300">
                    {type === 'sight'
                      ? '景点'
                      : type === 'food'
                      ? '美食'
                      : type === 'hotel'
                      ? '酒店'
                      : '交通'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default GaodeMap;
