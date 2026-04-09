/**
 * 实时监控模块 Store
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getRealtimeStats,
  getRealtimeSentimentDist,
  getRealtimeWeibos,
  getRealtimeWordCloud,
  getRealtimeTrend,
  getAlertRules,
  getAlertEvents,
  updateAlertEvent,
  getGeoDistribution,
  getSystemMetrics,
  realtimeWS,
  type RealtimeStats,
  type RealtimeSentimentDist,
  type RealtimeWeibo,
  type RealtimeWordCloud,
  type AlertRule,
  type AlertEvent,
  type GeoDistribution,
  type SystemMetrics,
  type ConnectionStats,
} from '@/api/realtime';

export const useRealtimeStore = defineStore('realtime', () => {
  // ==================== State ====================
  
  /** 实时统计 */
  const stats = ref<RealtimeStats | null>(null);
  
  /** 实时情感分布 */
  const sentimentDist = ref<RealtimeSentimentDist | null>(null);
  
  /** 实时微博列表 */
  const weibos = ref<RealtimeWeibo[]>([]);
  
  /** 实时词云 */
  const wordCloud = ref<RealtimeWordCloud | null>(null);
  
  /** 实时趋势数据 */
  const trendData = ref<{ timestamps: string[]; series: { name: string; data: number[] }[] } | null>(null);
  
  /** 预警规则 */
  const alertRules = ref<AlertRule[]>([]);
  
  /** 预警事件 */
  const alertEvents = ref<AlertEvent[]>([]);
  const alertEventsTotal = ref(0);
  
  /** 地理分布 */
  const geoDistribution = ref<GeoDistribution[]>([]);
  
  /** 系统指标 */
  const systemMetrics = ref<SystemMetrics | null>(null);
  
  /** 连接状态 */
  const connectionStatus = ref<ConnectionStats['status']>('disconnected');
  const connectionStats = ref({
    messagesReceived: 0,
    messagesSent: 0,
    bytesReceived: 0,
    bytesSent: 0,
    reconnectCount: 0,
  });
  
  /** 微博流控制 */
  const streamPaused = ref(false);
  const streamFilter = ref({
    sentiment: '' as string,
    keyword: '' as string,
  });
  
  /** 加载状态 */
  const isLoading = ref(false);
  const isLoadingWeibos = ref(false);
  const isLoadingAlerts = ref(false);
  
  /** 刷新定时器 */
  let refreshTimer: number | null = null;
  let weiboRefreshTimer: number | null = null;

  // ==================== Getters ====================
  
  /** 未处理预警数 */
  const pendingAlertCount = computed(() => 
    alertEvents.value.filter(e => e.status === 'pending').length
  );
  
  /** 高级别预警数 */
  const highLevelAlertCount = computed(() => 
    alertEvents.value.filter(e => e.level === 'high' && e.status === 'pending').length
  );
  
  /** 正面微博 */
  const positiveWeibos = computed(() => 
    weibos.value.filter(w => w.sentiment === 'positive')
  );
  
  /** 负面微博 */
  const negativeWeibos = computed(() => 
    weibos.value.filter(w => w.sentiment === 'negative')
  );
  
  /** 筛选后的微博 */
  const filteredWeibos = computed(() => {
    let result = [...weibos.value];
    if (streamFilter.value.sentiment) {
      result = result.filter(w => w.sentiment === streamFilter.value.sentiment);
    }
    if (streamFilter.value.keyword) {
      const kw = streamFilter.value.keyword.toLowerCase();
      result = result.filter(w => w.content.toLowerCase().includes(kw));
    }
    return result;
  });
  
  /** 是否已连接 */
  const isConnected = computed(() => connectionStatus.value === 'connected');
  
  /** 负面舆情是否超阈值 */
  const isNegativeAlert = computed(() => 
    stats.value ? stats.value.negativeRatio > 25 : false
  );

  // ==================== Actions ====================
  
  /**
   * 获取实时统计
   */
  async function fetchStats() {
    try {
      stats.value = await getRealtimeStats();
    } catch (error) {
      console.error('获取实时统计失败:', error);
    }
  }
  
  /**
   * 获取实时情感分布
   */
  async function fetchSentimentDist() {
    try {
      sentimentDist.value = await getRealtimeSentimentDist();
    } catch (error) {
      console.error('获取情感分布失败:', error);
    }
  }
  
  /**
   * 获取实时微博
   */
  async function fetchWeibos(params?: { sentiment?: string; keyword?: string; limit?: number }) {
    isLoadingWeibos.value = true;
    try {
      const newWeibos = await getRealtimeWeibos(params);
      if (streamPaused.value) return;
      
      // 合并新微博，去重
      const existingIds = new Set(weibos.value.map(w => w.id));
      const uniqueNew = newWeibos.filter(w => !existingIds.has(w.id));
      weibos.value = [...uniqueNew, ...weibos.value].slice(0, 100); // 保留最新100条
    } catch (error) {
      console.error('获取实时微博失败:', error);
    } finally {
      isLoadingWeibos.value = false;
    }
  }
  
  /**
   * 获取实时词云
   */
  async function fetchWordCloud(params?: { minutes?: number; limit?: number }) {
    try {
      wordCloud.value = await getRealtimeWordCloud(params);
    } catch (error) {
      console.error('获取词云失败:', error);
    }
  }
  
  /**
   * 获取实时趋势
   */
  async function fetchTrend(params?: { metrics?: string[]; minutes?: number }) {
    try {
      trendData.value = await getRealtimeTrend(params);
    } catch (error) {
      console.error('获取趋势数据失败:', error);
    }
  }
  
  /**
   * 获取预警规则
   */
  async function fetchAlertRules() {
    try {
      alertRules.value = await getAlertRules();
    } catch (error) {
      console.error('获取预警规则失败:', error);
    }
  }
  
  /**
   * 获取预警事件
   */
  async function fetchAlertEvents(params?: {
    page?: number;
    pageSize?: number;
    level?: string;
    status?: string;
  }) {
    isLoadingAlerts.value = true;
    try {
      const response = await getAlertEvents(params);
      alertEvents.value = response.list;
      alertEventsTotal.value = response.total;
      return response;
    } catch (error) {
      console.error('获取预警事件失败:', error);
      throw error;
    } finally {
      isLoadingAlerts.value = false;
    }
  }
  
  /**
   * 更新预警事件状态
   */
  async function updateEventStatus(id: number, data: { status?: AlertEvent['status']; note?: string }) {
    try {
      const updated = await updateAlertEvent(id, data);
      const index = alertEvents.value.findIndex(e => e.id === id);
      if (index > -1) {
        alertEvents.value[index] = updated;
      }
      return updated;
    } catch (error) {
      console.error('更新预警事件失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取地理分布
   */
  async function fetchGeoDistribution(params?: {
    mapType?: 'china' | 'world' | 'province';
    province?: string;
    metric?: 'count' | 'heat' | 'sentiment';
  }) {
    try {
      geoDistribution.value = await getGeoDistribution(params);
    } catch (error) {
      console.error('获取地理分布失败:', error);
    }
  }
  
  /**
   * 获取系统指标
   */
  async function fetchSystemMetrics() {
    try {
      systemMetrics.value = await getSystemMetrics();
    } catch (error) {
      console.error('获取系统指标失败:', error);
    }
  }
  
  /**
   * 开始自动刷新
   */
  function startAutoRefresh(interval = 5000) {
    stopAutoRefresh();
    
    // 立即获取一次
    fetchStats();
    fetchSentimentDist();
    fetchWordCloud();
    
    // 定时刷新
    refreshTimer = window.setInterval(() => {
      fetchStats();
      fetchSentimentDist();
      fetchWordCloud();
    }, interval);
    
    // 微博流更频繁刷新
    weiboRefreshTimer = window.setInterval(() => {
      if (!streamPaused.value) {
        fetchWeibos({ limit: 10 });
      }
    }, 3000);
  }
  
  /**
   * 停止自动刷新
   */
  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
    if (weiboRefreshTimer) {
      clearInterval(weiboRefreshTimer);
      weiboRefreshTimer = null;
    }
  }
  
  /**
   * 暂停/继续微博流
   */
  function toggleStreamPause() {
    streamPaused.value = !streamPaused.value;
  }
  
  /**
   * 设置微博流筛选
   */
  function setStreamFilter(filter: { sentiment?: string; keyword?: string }) {
    if (filter.sentiment !== undefined) streamFilter.value.sentiment = filter.sentiment;
    if (filter.keyword !== undefined) streamFilter.value.keyword = filter.keyword;
  }
  
  /**
   * 清空微博列表
   */
  function clearWeibos() {
    weibos.value = [];
  }
  
  /**
   * 连接 WebSocket
   */
  function connectWebSocket() {
    realtimeWS.connect();
    
    // 监听状态变化
    realtimeWS.onStatusChange((status) => {
      connectionStatus.value = status;
    });
    
    // 监听实时数据
    realtimeWS.on('REAL_TIME_DATA', (data) => {
      if (data.type === 'weibo' && !streamPaused.value) {
        weibos.value = [data.data, ...weibos.value].slice(0, 100);
      } else if (data.type === 'stats') {
        stats.value = data.data;
      }
    });
    
    // 监听预警事件
    realtimeWS.on('ALERT_EVENT', (data) => {
      alertEvents.value = [data, ...alertEvents.value];
    });
    
    // 更新连接统计
    const updateStats = () => {
      connectionStats.value = { ...realtimeWS.stats };
    };
    setInterval(updateStats, 1000);
  }
  
  /**
   * 断开 WebSocket
   */
  function disconnectWebSocket() {
    realtimeWS.disconnect();
  }
  
  /**
   * 初始化
   */
  async function initialize() {
    isLoading.value = true;
    try {
      await Promise.all([
        fetchStats(),
        fetchSentimentDist(),
        fetchWeibos({ limit: 20 }),
        fetchWordCloud(),
        fetchAlertRules(),
        fetchAlertEvents({ pageSize: 10 }),
        fetchGeoDistribution(),
        fetchSystemMetrics(),
      ]);
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 重置 Store
   */
  function $reset() {
    stopAutoRefresh();
    disconnectWebSocket();
    
    stats.value = null;
    sentimentDist.value = null;
    weibos.value = [];
    wordCloud.value = null;
    trendData.value = null;
    alertRules.value = [];
    alertEvents.value = [];
    alertEventsTotal.value = 0;
    geoDistribution.value = [];
    systemMetrics.value = null;
    connectionStatus.value = 'disconnected';
    streamPaused.value = false;
    streamFilter.value = { sentiment: '', keyword: '' };
    isLoading.value = false;
  }

  return {
    // State
    stats,
    sentimentDist,
    weibos,
    wordCloud,
    trendData,
    alertRules,
    alertEvents,
    alertEventsTotal,
    geoDistribution,
    systemMetrics,
    connectionStatus,
    connectionStats,
    streamPaused,
    streamFilter,
    isLoading,
    isLoadingWeibos,
    isLoadingAlerts,
    
    // Getters
    pendingAlertCount,
    highLevelAlertCount,
    positiveWeibos,
    negativeWeibos,
    filteredWeibos,
    isConnected,
    isNegativeAlert,
    
    // Actions
    fetchStats,
    fetchSentimentDist,
    fetchWeibos,
    fetchWordCloud,
    fetchTrend,
    fetchAlertRules,
    fetchAlertEvents,
    updateEventStatus,
    fetchGeoDistribution,
    fetchSystemMetrics,
    startAutoRefresh,
    stopAutoRefresh,
    toggleStreamPause,
    setStreamFilter,
    clearWeibos,
    connectWebSocket,
    disconnectWebSocket,
    initialize,
    $reset,
  };
});
