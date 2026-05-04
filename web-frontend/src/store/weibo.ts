/**
 * 微博数据 Store
 * 管理热搜、采集任务和数据流状态
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getLiveHotSearch,
  refreshHotSearch,
  startHotSearchService,
  stopHotSearchService,
  startCrawlTask,
  getCrawlTaskStatus,
  getCrawlTasks,
  startDataflowTask,
  getDataflowTaskStatus,
  getDataflowOverview,
  type LiveHotSearchResponse,
  type LiveHotSearchItem,
  type CrawlTask,
  type DataflowTask,
  type DataflowOverview,
} from '@/api/weibo';

/** 热搜项类型 */
export interface HotSearchItem {
  title: string;
  heat: number;
  trend: 'up' | 'down' | 'stable';
  sentiment: 'positive' | 'neutral' | 'negative';
  sentimentScore: number;
  positiveRatio: number;
  negativeRatio: number;
  isNew: boolean;
  isHot: boolean;
  isFei: boolean;
  category: string;
  label: string;
  url: string;
  weiboCount: number;
  sampleWeibos: any[];
  crawlTime: string;
}

/** 采集任务类型 */
export interface CollectionTask {
  id: string;
  keyword: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'interrupted' | 'paused';
  progress: number;
  count: number;
  startTime: string;
  endTime?: string;
  error?: string;
}

export const useWeiboStore = defineStore('weibo', () => {
  // ==================== State ====================
  
  /** 热搜列表 */
  const hotSearches = ref<HotSearchItem[]>([]);
  
  /** 热搜统计摘要 */
  const hotSearchSummary = ref<any>({});
  
  /** 最后刷新时间 */
  const lastRefreshTime = ref<string>('');
  
  /** 热搜服务状态 */
  const hotSearchServiceRunning = ref(false);
  
  /** 采集任务列表 */
  const collectionTasks = ref<CollectionTask[]>([]);
  
  /** 当前数据流任务ID */
  const dataflowTaskId = ref<string>('');
  
  /** 数据流任务状态 */
  const dataflowTask = ref<DataflowTask | null>(null);
  
  /** 数据流概览 */
  const dataflowOverview = ref<DataflowOverview | null>(null);
  
  /** 加载状态 */
  const isLoading = ref(false);
  const isRefreshing = ref(false);
  
  /** 错误信息 */
  const error = ref<string | null>(null);

  // ==================== Getters ====================
  
  /** 热搜数量 */
  const hotSearchCount = computed(() => hotSearches.value.length);
  
  /** 正面热搜 */
  const positiveHotSearches = computed(() => 
    hotSearches.value.filter(h => h.sentiment === 'positive')
  );
  
  /** 负面热搜 */
  const negativeHotSearches = computed(() => 
    hotSearches.value.filter(h => h.sentiment === 'negative')
  );
  
  /** 新上榜热搜 */
  const newHotSearches = computed(() => 
    hotSearches.value.filter(h => h.isNew)
  );
  
  /** 运行中的任务 */
  const runningTasks = computed(() => 
    collectionTasks.value.filter(t => t.status === 'running')
  );
  
  /** 是否有任务在运行 */
  const hasRunningTask = computed(() => runningTasks.value.length > 0);
  
  /** 词云数据（从热搜生成） */
  const wordcloudDataFromHotSearch = computed(() => {
    const data: { name: string; value: number }[] = [];
    hotSearches.value.forEach((item, index) => {
      // 分词处理热搜标题
      const words = item.title.split(/[\s,，、]+/);
      words.forEach((word: string) => {
        if (word.length >= 2) {
          data.push({
            name: word,
            value: Math.max(1000, item.heat / 100 - index * 500),
          });
        }
      });
      // 添加完整标题
      data.push({
        name: item.title,
        value: Math.max(5000, item.heat / 50),
      });
    });
    return data;
  });

  // ==================== Actions ====================
  
  /**
   * 获取实时热搜
   */
  async function fetchHotSearch() {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response: LiveHotSearchResponse = await getLiveHotSearch();
      
      // 转换数据格式
      hotSearches.value = response.hot_list.map((item: LiveHotSearchItem) => ({
        title: item.title,
        heat: item.hot_value,
        trend: item.trend === 'rising' || item.trend === 'new' ? 'up' : 
               item.trend === 'falling' ? 'down' : 'stable',
        sentiment: (item.sentiment || 'neutral') as 'positive' | 'neutral' | 'negative',
        sentimentScore: item.sentiment_score || 0,
        positiveRatio: item.positive_ratio || 0,
        negativeRatio: item.negative_ratio || 0,
        isNew: item.is_new || item.trend === 'new',
        isHot: item.is_hot || false,
        isFei: item.is_fei || false,
        category: item.category || '',
        label: item.label || '',
        url: item.url || '',
        weiboCount: item.weibo_count || 0,
        sampleWeibos: item.sample_weibos || [],
        crawlTime: item.crawl_time,
      }));
      
      hotSearchSummary.value = response.summary;
      lastRefreshTime.value = response.last_refresh;
      
      return hotSearches.value;
    } catch (err: any) {
      error.value = err.message || '获取热搜失败';
      console.error('获取热搜失败:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 强制刷新热搜（重新爬取）
   */
  async function forceRefreshHotSearch() {
    isRefreshing.value = true;
    error.value = null;
    
    try {
      await refreshHotSearch();
      await fetchHotSearch();
    } catch (err: any) {
      error.value = err.message || '刷新热搜失败';
      console.error('刷新热搜失败:', err);
      throw err;
    } finally {
      isRefreshing.value = false;
    }
  }
  
  /**
   * 启动热搜服务
   */
  async function startHotSearch(interval: number = 60) {
    try {
      await startHotSearchService(interval);
      hotSearchServiceRunning.value = true;
    } catch (err: any) {
      console.warn('启动热搜服务失败:', err);
    }
  }
  
  /**
   * 停止热搜服务
   */
  async function stopHotSearch() {
    try {
      await stopHotSearchService();
      hotSearchServiceRunning.value = false;
    } catch (err: any) {
      console.warn('停止热搜服务失败:', err);
    }
  }
  
  /**
   * 启动采集任务
   */
  async function startCollection(params: {
    keywords: string[];
    pages?: number;
    crawlHot?: boolean;
    dateRange?: [string, string] | null;
  }) {
    try {
      const result = await startCrawlTask(params.keywords, params.pages || 3, params.crawlHot || false, params.dateRange);
      
      // 兼容后端返回的 id 或 task_id 字段
      const taskId = result.task_id || result.id;
      
      const task: CollectionTask = {
        id: taskId,
        keyword: params.keywords.join(', '),
        status: 'running',
        progress: 0,
        count: 0,
        startTime: new Date().toISOString(),
      };
      
      collectionTasks.value.unshift(task);
      return { ...result, task_id: taskId };
    } catch (err: any) {
      error.value = err.message || '启动采集任务失败';
      throw err;
    }
  }
  
  /**
   * 获取采集任务状态
   */
  async function getTaskStatus(taskId: string) {
    try {
      const status = await getCrawlTaskStatus(taskId);
      
      // 更新任务列表中的状态
      const taskIndex = collectionTasks.value.findIndex(t => t.id === taskId);
      if (taskIndex !== -1) {
        collectionTasks.value[taskIndex] = {
          ...collectionTasks.value[taskIndex],
          status: status.status,
          progress: status.progress || 0,
          count: status.collected_count || 0,
          endTime: status.status === 'completed' ? new Date().toISOString() : undefined,
          error: status.error,
        };
      }
      
      return status;
    } catch (err: any) {
      console.error('获取任务状态失败:', err);
      throw err;
    }
  }
  
  /**
   * 启动数据流任务（完整流水线）
   */
  async function startDataflow(params: {
    keywords: string[];
    pages?: number;
    crawlHot?: boolean;
    autoProcess?: boolean;
  }) {
    try {
      const result = await startDataflowTask({
        keywords: params.keywords,
        pages: params.pages || 3,
        crawl_hot: params.crawlHot || false,
        auto_process: params.autoProcess !== false,
      });
      
      dataflowTaskId.value = result.task_id;
      return result;
    } catch (err: any) {
      error.value = err.message || '启动数据流任务失败';
      throw err;
    }
  }
  
  /**
   * 获取数据流任务状态
   */
  async function getDataflowStatus(taskId?: string) {
    const id = taskId || dataflowTaskId.value;
    if (!id) return null;
    
    try {
      const status = await getDataflowTaskStatus(id);
      dataflowTask.value = status;
      return status;
    } catch (err: any) {
      console.error('获取数据流状态失败:', err);
      throw err;
    }
  }
  
  /**
   * 获取数据流概览
   */
  async function fetchDataflowOverview() {
    try {
      const overview = await getDataflowOverview();
      dataflowOverview.value = overview;
      return overview;
    } catch (err: any) {
      console.error('获取数据流概览失败:', err);
      throw err;
    }
  }
  
  // ==================== 任务轮询（store级别，切换页面不中断） ====================
  
  let _pollTimer: ReturnType<typeof setInterval> | null = null;
  let _dataflowPollTimer: ReturnType<typeof setInterval> | null = null;
  
  /**
   * 启动采集任务轮询（在store层面运行，不受组件生命周期影响）
   */
  function startTaskPolling(taskId: string) {
    stopTaskPolling();
    _pollTimer = setInterval(async () => {
      try {
        const status = await getCrawlTaskStatus(taskId);
        const idx = collectionTasks.value.findIndex(t => t.id === taskId);
        if (idx !== -1) {
          collectionTasks.value[idx] = {
            ...collectionTasks.value[idx],
            status: status.status as CollectionTask['status'],
            progress: status.progress || 0,
            count: status.collected || 0,
            endTime: status.end_time || undefined,
            error: status.error || undefined,
          };
        }
        if (status.status === 'completed' || status.status === 'failed') {
          stopTaskPolling();
        }
      } catch {
        // 静默处理
      }
    }, 2000);
  }
  
  function stopTaskPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
  }
  
  /**
   * 启动数据流轮询
   */
  function startDataflowPolling() {
    stopDataflowPolling();
    _dataflowPollTimer = setInterval(async () => {
      try {
        const status = await getDataflowTaskStatus(dataflowTaskId.value);
        dataflowTask.value = status;
        if (status.status === 'completed' || status.status === 'failed') {
          stopDataflowPolling();
        }
      } catch {
        // 静默处理
      }
    }, 2000);
  }
  
  function stopDataflowPolling() {
    if (_dataflowPollTimer) { clearInterval(_dataflowPollTimer); _dataflowPollTimer = null; }
  }
  
  /**
   * 从后端加载历史任务列表（登录后调用，上次登录的数据仍在）
   */
  async function loadTaskHistory() {
    try {
      const resp = await getCrawlTasks();
      const remoteTasks = resp.tasks || [];
      
      // 合并到本地任务列表（以后端为准，避免重复）
      const localIds = new Set(collectionTasks.value.map(t => t.id));
      for (const rt of remoteTasks) {
        if (!localIds.has(rt.id)) {
          collectionTasks.value.push({
            id: rt.id,
            keyword: (rt.keywords || []).join(', '),
            status: rt.status as CollectionTask['status'],
            progress: rt.progress || 0,
            count: rt.collected || 0,
            startTime: rt.start_time || '',
            endTime: rt.end_time || undefined,
            error: rt.error || undefined,
          });
        }
      }
      
      // 如果有正在运行的任务，自动恢复轮询
      const running = collectionTasks.value.find(t => t.status === 'running');
      if (running) {
        startTaskPolling(running.id);
      }
    } catch {
      // 后端不可用时静默处理
    }
  }
  
  /**
   * 清除错误
   */
  function clearError() {
    error.value = null;
  }
  
  /**
   * 重置Store
   */
  function $reset() {
    stopTaskPolling();
    stopDataflowPolling();
    hotSearches.value = [];
    hotSearchSummary.value = {};
    lastRefreshTime.value = '';
    hotSearchServiceRunning.value = false;
    collectionTasks.value = [];
    dataflowTaskId.value = '';
    dataflowTask.value = null;
    dataflowOverview.value = null;
    isLoading.value = false;
    isRefreshing.value = false;
    error.value = null;
  }

  return {
    // State
    hotSearches,
    hotSearchSummary,
    lastRefreshTime,
    hotSearchServiceRunning,
    collectionTasks,
    dataflowTaskId,
    dataflowTask,
    dataflowOverview,
    isLoading,
    isRefreshing,
    error,
    
    // Getters
    hotSearchCount,
    positiveHotSearches,
    negativeHotSearches,
    newHotSearches,
    runningTasks,
    hasRunningTask,
    wordcloudDataFromHotSearch,
    
    // Actions
    fetchHotSearch,
    forceRefreshHotSearch,
    startHotSearch,
    stopHotSearch,
    startCollection,
    getTaskStatus,
    startDataflow,
    getDataflowStatus,
    fetchDataflowOverview,
    loadTaskHistory,
    startTaskPolling,
    stopTaskPolling,
    startDataflowPolling,
    stopDataflowPolling,
    clearError,
    $reset,
  };
});
