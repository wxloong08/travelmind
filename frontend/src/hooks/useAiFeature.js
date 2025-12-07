/**
 * AI 功能 Hook
 * 
 * 封装各种 AI 助手功能的调用逻辑
 */

import { useCallback } from 'react';
import { assistantsApi } from '../api/client';
import useTravelStore from '../store/useTravelStore';

export function useAiFeature() {
  const {
    destination,
    weather,
    tripDays,
    itinerary,
    cache,
    setCache,
    openModal,
    setModalContent,
    setModalLoading,
    updateDayTips,
  } = useTravelStore();

  /**
   * 获取行程上下文（用于 AI 请求）
   */
  const getContext = useCallback(() => {
    if (!itinerary || itinerary.length === 0) return null;

    const activities = itinerary.flatMap((day) =>
      day.activities.map((act) => act.title)
    );
    return activities.join('、');
  }, [itinerary]);

  /**
   * 预算估算
   */
  const estimateBudget = useCallback(async (forceRefresh = false) => {
    openModal('budget', '💰 智能预算估算');

    // 检查缓存
    if (!forceRefresh && cache.budget) {
      setModalContent(cache.budget);
      return;
    }

    try {
      const result = await assistantsApi.getBudget(
        destination,
        getContext(),
        tripDays,
        `${weather.temp}, ${weather.condition}`
      );
      setCache('budget', result);
      setModalContent(result);
    } catch (error) {
      console.error('Budget estimation failed:', error);
      setModalContent({ error: '预算估算失败，请重试' });
    }
  }, [destination, weather, tripDays, cache.budget, getContext]);

  /**
   * 行李清单
   */
  const generatePacking = useCallback(async (forceRefresh = false) => {
    openModal('packing', '🎒 智能行李清单');

    if (!forceRefresh && cache.packing) {
      setModalContent(cache.packing);
      return;
    }

    try {
      const result = await assistantsApi.getPacking(
        destination,
        getContext(),
        tripDays,
        `${weather.temp}, ${weather.condition}`
      );
      setCache('packing', result);
      setModalContent(result);
    } catch (error) {
      console.error('Packing list failed:', error);
      setModalContent({ error: '行李清单生成失败，请重试' });
    }
  }, [destination, weather, tripDays, cache.packing, getContext]);

  /**
   * 氛围歌单
   */
  const generatePlaylist = useCallback(async (forceRefresh = false) => {
    openModal('playlist', '🎵 AI 氛围歌单');

    if (!forceRefresh && cache.playlist) {
      setModalContent(cache.playlist);
      return;
    }

    try {
      const result = await assistantsApi.getPlaylist(destination, getContext());
      setCache('playlist', result);
      setModalContent(result);
    } catch (error) {
      console.error('Playlist generation failed:', error);
      setModalContent({ error: '歌单生成失败，请重试' });
    }
  }, [destination, cache.playlist, getContext]);

  /**
   * 紧急助手
   */
  const generateEmergency = useCallback(async (forceRefresh = false) => {
    openModal('emergency', '🆘 智能紧急助手');

    if (!forceRefresh && cache.emergency) {
      setModalContent(cache.emergency);
      return;
    }

    try {
      const result = await assistantsApi.getEmergency(destination);
      setCache('emergency', result);
      setModalContent(result);
    } catch (error) {
      console.error('Emergency info failed:', error);
      setModalContent({ error: '紧急信息获取失败，请重试' });
    }
  }, [destination, cache.emergency]);

  /**
   * 文化锦囊
   */
  const generateCulture = useCallback(async (forceRefresh = false) => {
    openModal('culture', '🌍 本地文化锦囊');

    if (!forceRefresh && cache.culture) {
      setModalContent(cache.culture);
      return;
    }

    try {
      const result = await assistantsApi.getCulture(destination);
      setCache('culture', result);
      setModalContent(result);
    } catch (error) {
      console.error('Culture guide failed:', error);
      setModalContent({ error: '文化指南生成失败，请重试' });
    }
  }, [destination, cache.culture]);

  /**
   * 伴手礼指南
   */
  const generateSouvenirs = useCallback(async (forceRefresh = false) => {
    openModal('souvenirs', '🎁 伴手礼顾问');

    if (!forceRefresh && cache.souvenirs) {
      setModalContent(cache.souvenirs);
      return;
    }

    try {
      const result = await assistantsApi.getSouvenirs(destination);
      setCache('souvenirs', result);
      setModalContent(result);
    } catch (error) {
      console.error('Souvenir guide failed:', error);
      setModalContent({ error: '伴手礼推荐生成失败，请重试' });
    }
  }, [destination, cache.souvenirs]);

  /**
   * 摄影挑战
   */
  const generatePhotoChallenges = useCallback(async (forceRefresh = false) => {
    openModal('photo_challenge', '📸 城市摄影挑战');

    if (!forceRefresh && cache.photoChallenges) {
      setModalContent(cache.photoChallenges);
      return;
    }

    try {
      const result = await assistantsApi.getPhotoChallenges(destination);
      setCache('photoChallenges', result);
      setModalContent(result);
    } catch (error) {
      console.error('Photo challenges failed:', error);
      setModalContent({ error: '摄影挑战生成失败，请重试' });
    }
  }, [destination, cache.photoChallenges]);

  /**
   * 每日攻略
   */
  const getDayTips = useCallback(async (day, dayIndex, forceRefresh = false) => {
    openModal('tips', `${day.title} - AI 攻略`, null, { day, dayIndex });

    // 检查缓存
    if (!forceRefresh && day.cachedTips) {
      setModalContent(day.cachedTips);
      return;
    }

    try {
      const activities = day.activities.map((a) => a.title);
      const result = await assistantsApi.getDayTips(
        destination,
        day.title,
        activities
      );

      // 更新 itinerary 中的缓存
      updateDayTips(dayIndex, result);
      setModalContent(result);
    } catch (error) {
      console.error('Day tips failed:', error);
      setModalContent({ error: 'AI 攻略生成失败，请重试' });
    }
  }, [destination, updateDayTips]);

  /**
   * 旅行日记
   */
  const generateDiary = useCallback(async (day) => {
    openModal('diary', `📝 ${day.title} - 旅行日记`);

    try {
      // 日记不缓存，每次都重新生成
      const activities = day.activities.map((a) => a.title);

      // 调用专门的日记 API
      const response = await fetch(`${import.meta.env.VITE_API_BASE || '/api/v1'}/assistants/diary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination,
          day: day.day,
          day_title: day.title,
          activities,
        }),
      });

      const result = await response.json();
      setModalContent({ text: result.text });
    } catch (error) {
      console.error('Diary generation failed:', error);
      setModalContent({ error: '日记生成失败，请重试' });
    }
  }, [destination]);

  /**
   * Vlog 脚本生成
   */
  const generateVlogScript = useCallback(async (day) => {
    openModal('vlog', `🎬 ${day.title} - Vlog 脚本`);

    try {
      const activities = day.activities.map((a) => a.title);
      const result = await assistantsApi.getVlogScript(
        destination,
        day.day,
        day.title,
        activities
      );
      setModalContent(result);
    } catch (error) {
      console.error('Vlog script generation failed:', error);
      setModalContent({ error: 'Vlog 脚本生成失败，请重试' });
    }
  }, [destination]);

  /**
   * 摄影指导
   */
  const generatePhotoGuide = useCallback(async (placeName) => {
    openModal('photo_guide', `📸 ${placeName} - 摄影指导`);

    try {
      const result = await assistantsApi.getPhotoGuide(destination, placeName);
      setModalContent(result);
    } catch (error) {
      console.error('Photo guide generation failed:', error);
      setModalContent({ error: '摄影指导生成失败，请重试' });
    }
  }, [destination]);

  /**
   * 分享海报
   */
  const generatePoster = useCallback(async (forceRefresh = false) => {
    openModal('poster', '🖼️ 分享海报');

    if (!forceRefresh && cache.poster) {
      setModalContent(cache.poster);
      return;
    }

    try {
      const activities = itinerary?.flatMap((day) =>
        day.activities.map((act) => act.title)
      ) || [];
      const result = await assistantsApi.getPosterData(
        destination,
        tripDays,
        activities
      );
      setCache('poster', result);
      setModalContent(result);
    } catch (error) {
      console.error('Poster data generation failed:', error);
      setModalContent({ error: '海报数据生成失败，请重试' });
    }
  }, [destination, tripDays, itinerary, cache.poster]);

  /**
   * 重新生成当前 Modal 内容
   */
  const regenerate = useCallback((modalType, context) => {
    switch (modalType) {
      case 'budget':
        return estimateBudget(true);
      case 'packing':
        return generatePacking(true);
      case 'playlist':
        return generatePlaylist(true);
      case 'emergency':
        return generateEmergency(true);
      case 'culture':
        return generateCulture(true);
      case 'souvenirs':
        return generateSouvenirs(true);
      case 'photo_challenge':
        return generatePhotoChallenges(true);
      case 'tips':
        if (context?.day && context?.dayIndex !== undefined) {
          return getDayTips(context.day, context.dayIndex, true);
        }
        break;
      case 'diary':
        if (context?.day) {
          return generateDiary(context.day);
        }
        break;
      case 'vlog':
        if (context?.day) {
          return generateVlogScript(context.day);
        }
        break;
      case 'poster':
        return generatePoster(true);
    }
  }, [
    estimateBudget,
    generatePacking,
    generatePlaylist,
    generateEmergency,
    generateCulture,
    generateSouvenirs,
    generatePhotoChallenges,
    getDayTips,
    generateDiary,
    generateVlogScript,
    generatePoster,
  ]);

  return {
    estimateBudget,
    generatePacking,
    generatePlaylist,
    generateEmergency,
    generateCulture,
    generateSouvenirs,
    generatePhotoChallenges,
    getDayTips,
    generateDiary,
    generateVlogScript,
    generatePhotoGuide,
    generatePoster,
    regenerate,
  };
}

export default useAiFeature;

