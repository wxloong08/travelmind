/**
 * TravelMind API Client
 * 
 * 封装所有后端 API 调用，支持 SSE 流式响应
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

/**
 * 基础 fetch 封装
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

/**
 * SSE 流式请求生成器
 * @param {string} endpoint - API 端点
 * @param {Object} body - 请求体
 * @param {Object} headers - 额外的请求头（如 Authorization）
 */
async function* streamRequest(endpoint, body, headers = {}) {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Stream request failed: ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // 保留最后一个可能不完整的行
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();

          if (data === '[DONE]') {
            return;
          }

          try {
            yield JSON.parse(data);
          } catch (e) {
            // 忽略解析失败的数据
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============================================================
// Chat API
// ============================================================

export const chatApi = {
  /**
   * 普通对话
   */
  async send(message, sessionId = null) {
    return request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
    });
  },

  /**
   * 流式对话
   * @param {string} message - 用户消息
   * @param {string|null} sessionId - 会话 ID
   * @param {string|null} token - 认证 token（用于保存行程）
   * @param {boolean} regenerate - 是否重新生成不同版本
   * @param {Array|null} previousItinerary - 上一版行程（重新生成时传入）
   */
  stream(message, sessionId = null, token = null, regenerate = false, previousItinerary = null) {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return streamRequest('/chat/stream', {
      message,
      session_id: sessionId,
      regenerate,
      previous_itinerary: previousItinerary,
    }, headers);
  },
};

// ============================================================
// Tools API
// ============================================================

export const toolsApi = {
  /**
   * POI 搜索
   */
  async searchPOI(keywords, city, poiType = null, pageSize = 10) {
    return request('/tools/poi/search', {
      method: 'POST',
      body: JSON.stringify({
        keywords,
        city,
        poi_type: poiType,
        page_size: pageSize,
      }),
    });
  },

  /**
   * 天气查询
   */
  async getWeather(city, forecast = false) {
    return request('/tools/weather', {
      method: 'POST',
      body: JSON.stringify({ city, forecast }),
    });
  },

  /**
   * 路线规划
   */
  async getRoute(originLng, originLat, destLng, destLat, mode = 'driving') {
    return request('/tools/route', {
      method: 'POST',
      body: JSON.stringify({
        origin_lng: originLng,
        origin_lat: originLat,
        dest_lng: destLng,
        dest_lat: destLat,
        mode,
      }),
    });
  },

  /**
   * 网络搜索
   */
  async webSearch(query, count = 5, freshness = null) {
    return request('/tools/search', {
      method: 'POST',
      body: JSON.stringify({ query, count, freshness }),
    });
  },
};

// ============================================================
// AI Assistants API
// ============================================================

export const assistantsApi = {
  /**
   * 预算估算
   */
  async getBudget(destination, context = null, days = 3, weather = null) {
    return request('/assistants/budget', {
      method: 'POST',
      body: JSON.stringify({ destination, context, days, weather }),
    });
  },

  /**
   * 行李清单
   */
  async getPacking(destination, context = null, days = 3, weather = null) {
    return request('/assistants/packing', {
      method: 'POST',
      body: JSON.stringify({ destination, context, days, weather }),
    });
  },

  /**
   * 氛围歌单
   */
  async getPlaylist(destination, context = null) {
    return request('/assistants/playlist', {
      method: 'POST',
      body: JSON.stringify({ destination, context }),
    });
  },

  /**
   * 紧急助手
   */
  async getEmergency(destination) {
    return request('/assistants/emergency', {
      method: 'POST',
      body: JSON.stringify({ destination }),
    });
  },

  /**
   * 文化锦囊
   */
  async getCulture(destination) {
    return request('/assistants/culture', {
      method: 'POST',
      body: JSON.stringify({ destination }),
    });
  },

  /**
   * 伴手礼指南
   */
  async getSouvenirs(destination) {
    return request('/assistants/souvenirs', {
      method: 'POST',
      body: JSON.stringify({ destination }),
    });
  },

  /**
   * 摄影挑战
   */
  async getPhotoChallenges(destination) {
    return request('/assistants/photography', {
      method: 'POST',
      body: JSON.stringify({ destination }),
    });
  },

  /**
   * 问路卡
   */
  async getDirectionCard(destination, placeName) {
    return request('/assistants/direction_card', {
      method: 'POST',
      body: JSON.stringify({ destination, place_name: placeName }),
    });
  },

  /**
   * 景点故事
   */
  async getStory(destination, placeName) {
    return request('/assistants/story', {
      method: 'POST',
      body: JSON.stringify({ destination, place_name: placeName }),
    });
  },

  /**
   * 每日攻略
   */
  async getDayTips(destination, dayTitle, activities = []) {
    return request('/assistants/day_tips', {
      method: 'POST',
      body: JSON.stringify({
        destination,
        day_title: dayTitle,
        activities,
      }),
    });
  },

  /**
   * Vlog 脚本
   */
  async getVlogScript(destination, day, dayTitle, activities = []) {
    return request('/assistants/vlog_script', {
      method: 'POST',
      body: JSON.stringify({
        destination,
        day,
        day_title: dayTitle,
        activities,
      }),
    });
  },

  /**
   * 摄影指导
   */
  async getPhotoGuide(destination, placeName) {
    return request('/assistants/photo_guide', {
      method: 'POST',
      body: JSON.stringify({ destination, place_name: placeName }),
    });
  },

  /**
   * 海报数据
   */
  async getPosterData(destination, days, activities = []) {
    return request('/assistants/poster_data', {
      method: 'POST',
      body: JSON.stringify({ destination, days, activities }),
    });
  },
};

// ============================================================
// System API
// ============================================================

export const systemApi = {
  /**
   * 健康检查
   */
  async health() {
    return request('/health');
  },
};

// ============================================================
// Trips API (历史行程管理)
// ============================================================

export const tripsApi = {
  /**
   * 获取行程列表
   * @param {string} token - 认证 token
   * @param {number} limit - 每页数量
   * @param {number} offset - 偏移量
   */
  async list(token, limit = 20, offset = 0) {
    return request(`/trips?limit=${limit}&offset=${offset}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
  },

  /**
   * 获取行程详情
   * @param {string} token - 认证 token
   * @param {string} tripId - 行程 ID
   */
  async get(token, tripId) {
    return request(`/trips/${tripId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
  },

  /**
   * 删除行程
   * @param {string} token - 认证 token
   * @param {string} tripId - 行程 ID
   */
  async delete(token, tripId) {
    return request(`/trips/${tripId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
  },

  /**
   * 获取最新行程
   * @param {string} token - 认证 token
   */
  async getLatest(token) {
    return request('/trips/latest', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
  },

  /**
   * 检查是否有匹配的历史行程（重复检测）
   * @param {string} token - 认证 token
   * @param {string} destination - 目的地
   * @param {number} days - 天数
   */
  async match(token, destination, days) {
    return request('/trips/match', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ destination, days }),
    });
  },
};

// 导出统一的 API 对象
export const api = {
  chat: chatApi,
  tools: toolsApi,
  assistants: assistantsApi,
  system: systemApi,
  trips: tripsApi,
};

export default api;
