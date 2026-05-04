/**
 * 热点话题模块 Store
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getWordCloudData,
  getTimelineWordCloud,
  getWordDetail,
  getWordRelatedWeibos,
  getHotTopics,
  getTopicDetail,
  getHotSearch,
  getTopicTrend,
  getMonitorKeywords,
  addMonitorKeyword,
  removeMonitorKeyword,
  updateMonitorConfig,
  getRankedTopics,
  getTriDimensionConfig,
  updateTriDimensionConfig,
  type WordData,
  type TopicData,
  type TopicDetail,
  type HotSearchData,
  type TimelineWordCloud,
  type RankedTopic,
  type TriDimensionConfig,
} from '@/api/topics';

export const useTopicsStore = defineStore('topics', () => {
  // ==================== State ====================
  
  /** 词云数据 */
  const wordCloudData = ref<WordData[]>([]);
  
  /** 时间序列词云 */
  const timelineWordCloud = ref<TimelineWordCloud[]>([]);
  
  /** 热点话题列表 */
  const hotTopics = ref<TopicData[]>([]);
  
  /** 话题总数 */
  const totalTopics = ref(0);
  
  /** 当前话题详情 */
  const currentTopic = ref<TopicDetail | null>(null);
  
  /** 实时热搜 */
  const hotSearch = ref<HotSearchData[]>([]);
  
  /** 监控关键词 */
  const monitorKeywords = ref<{ id: number; keyword: string; alertEnabled: boolean; alertThreshold: number }[]>([]);
  
  /** 三维度排序话题 */
  const rankedTopics = ref<RankedTopic[]>([]);
  
  /** 三维度排序配置 */
  const triDimensionConfig = ref<TriDimensionConfig>({
    sentiment_weight: 0.6,
    popularity_weight: 0.4,
    time_decay_hours: 24,
  });
  
  /** 选中的词语 */
  const selectedWord = ref<string | null>(null);
  
  /** 词语详情 */
  const wordDetail = ref<any>(null);
  
  /** 加载状态 */
  const isLoading = ref(false);
  const isLoadingWordCloud = ref(false);
  const isLoadingTopics = ref(false);
  const isLoadingHotSearch = ref(false);
  const isLoadingRankedTopics = ref(false);
  const isSavingConfig = ref(false);

  // ==================== Getters ====================
  
  /** 按热度排序的话题 */
  const topicsByHeat = computed(() => 
    [...hotTopics.value].sort((a, b) => b.heat - a.heat)
  );
  
  /** 按趋势排序的话题 */
  const topicsByTrend = computed(() => 
    [...hotTopics.value].sort((a, b) => b.heatTrend - a.heatTrend)
  );
  
  /** 正面话题 */
  const positiveTopics = computed(() => 
    hotTopics.value.filter(t => t.sentiment === 'positive')
  );
  
  /** 负面话题 */
  const negativeTopics = computed(() => 
    hotTopics.value.filter(t => t.sentiment === 'negative')
  );
  
  /** 热搜前10 */
  const topHotSearch = computed(() => 
    hotSearch.value.slice(0, 10)
  );
  
  /** 词云统计 */
  const wordCloudStats = computed(() => {
    const total = wordCloudData.value.length;
    const positive = wordCloudData.value.filter(w => w.sentiment === 'positive').length;
    const negative = wordCloudData.value.filter(w => w.sentiment === 'negative').length;
    const neutral = total - positive - negative;
    const totalValue = wordCloudData.value.reduce((sum, w) => sum + w.value, 0);
    const avgValue = total > 0 ? Math.round(totalValue / total) : 0;
    
    return { total, positive, negative, neutral, totalValue, avgValue };
  });
  
  /** 三维度排序Top5 */
  const topRankedTopics = computed(() => rankedTopics.value.slice(0, 5));
  
  /** 正面排序话题 */
  const positiveRankedTopics = computed(() => 
    rankedTopics.value.filter(t => t.sentiment_avg > 0.3)
  );
  
  /** 负面排序话题 */
  const negativeRankedTopics = computed(() => 
    rankedTopics.value.filter(t => t.sentiment_avg < -0.3)
  );

  // ==================== Actions ====================
  
  /**
   * 获取词云数据
   */
  async function fetchWordCloudData(params?: {
    dateRange?: [string, string];
    source?: string;
    sentiment?: string;
    limit?: number;
  }) {
    isLoadingWordCloud.value = true;
    try {
      wordCloudData.value = await getWordCloudData(params);
    } catch (error) {
      console.error('获取词云数据失败:', error);
      throw error;
    } finally {
      isLoadingWordCloud.value = false;
    }
  }
  
  /**
   * 获取时间序列词云
   */
  async function fetchTimelineWordCloud(params: {
    startDate: string;
    endDate: string;
    interval: 'hour' | 'day' | 'week';
  }) {
    isLoadingWordCloud.value = true;
    try {
      timelineWordCloud.value = await getTimelineWordCloud(params);
    } catch (error) {
      console.error('获取时间序列词云失败:', error);
      throw error;
    } finally {
      isLoadingWordCloud.value = false;
    }
  }
  
  /**
   * 获取词语详情
   */
  async function fetchWordDetail(word: string) {
    isLoading.value = true;
    try {
      selectedWord.value = word;
      wordDetail.value = await getWordDetail(word);
    } catch (error) {
      console.error('获取词语详情失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 获取词语相关微博
   */
  async function fetchWordRelatedWeibos(word: string, params?: {
    page?: number;
    pageSize?: number;
    sentiment?: string;
  }) {
    try {
      return await getWordRelatedWeibos(word, params);
    } catch (error) {
      console.error('获取相关微博失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取热点话题列表
   */
  async function fetchHotTopics(params?: {
    page?: number;
    pageSize?: number;
    category?: string;
    sentiment?: string;
    sortBy?: 'heat' | 'trend' | 'time';
    sortOrder?: 'asc' | 'desc';
  }) {
    isLoadingTopics.value = true;
    try {
      const response = await getHotTopics(params);
      hotTopics.value = response.list;
      totalTopics.value = response.total;
      return response;
    } catch (error) {
      console.error('获取热点话题失败:', error);
      throw error;
    } finally {
      isLoadingTopics.value = false;
    }
  }
  
  /**
   * 获取话题详情
   */
  async function fetchTopicDetail(id: number) {
    isLoading.value = true;
    try {
      currentTopic.value = await getTopicDetail(id);
      return currentTopic.value;
    } catch (error) {
      console.error('获取话题详情失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 获取实时热搜
   */
  async function fetchHotSearch() {
    isLoadingHotSearch.value = true;
    try {
      hotSearch.value = await getHotSearch();
    } catch (error) {
      console.error('获取热搜失败:', error);
      throw error;
    } finally {
      isLoadingHotSearch.value = false;
    }
  }
  
  /**
   * 获取话题趋势
   */
  async function fetchTopicTrend(id: number, params?: {
    startDate?: string;
    endDate?: string;
    interval?: 'hour' | 'day';
  }) {
    try {
      return await getTopicTrend(id, params);
    } catch (error) {
      console.error('获取话题趋势失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取监控关键词
   */
  async function fetchMonitorKeywords() {
    try {
      monitorKeywords.value = await getMonitorKeywords();
    } catch (error) {
      console.error('获取监控关键词失败:', error);
      throw error;
    }
  }
  
  /**
   * 添加监控关键词
   */
  async function addKeywordToMonitor(keyword: string, config?: {
    alertEnabled?: boolean;
    alertThreshold?: number;
  }) {
    try {
      await addMonitorKeyword(keyword, config);
      await fetchMonitorKeywords();
    } catch (error) {
      console.error('添加监控关键词失败:', error);
      throw error;
    }
  }
  
  /**
   * 删除监控关键词
   */
  async function removeKeywordFromMonitor(id: number) {
    try {
      await removeMonitorKeyword(id);
      monitorKeywords.value = monitorKeywords.value.filter(k => k.id !== id);
    } catch (error) {
      console.error('删除监控关键词失败:', error);
      throw error;
    }
  }
  
  /**
   * 更新监控配置
   */
  async function updateKeywordMonitorConfig(id: number, config: {
    alertEnabled?: boolean;
    alertThreshold?: number;
  }) {
    try {
      await updateMonitorConfig(id, config);
      const keyword = monitorKeywords.value.find(k => k.id === id);
      if (keyword) {
        Object.assign(keyword, config);
      }
    } catch (error) {
      console.error('更新监控配置失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取三维度排序话题
   */
  async function fetchRankedTopics() {
    isLoadingRankedTopics.value = true;
    try {
      rankedTopics.value = await getRankedTopics();
      return rankedTopics.value;
    } catch (error) {
      console.error('获取三维度排序话题失败:', error);
      throw error;
    } finally {
      isLoadingRankedTopics.value = false;
    }
  }
  
  /**
   * 获取三维度排序配置
   */
  async function fetchTriDimensionConfig() {
    try {
      const config = await getTriDimensionConfig();
      triDimensionConfig.value = config;
      return config;
    } catch (error) {
      console.warn('获取三维度配置失败，使用默认值:', error);
      // 使用默认配置
      return triDimensionConfig.value;
    }
  }
  
  /**
   * 更新三维度排序配置
   */
  async function saveTriDimensionConfig(config: Partial<TriDimensionConfig>) {
    isSavingConfig.value = true;
    try {
      const updatedConfig = await updateTriDimensionConfig(config);
      triDimensionConfig.value = updatedConfig;
      // 配置更新后重新获取排序结果
      await fetchRankedTopics();
      return updatedConfig;
    } catch (error) {
      console.error('更新三维度配置失败:', error);
      throw error;
    } finally {
      isSavingConfig.value = false;
    }
  }
  
  /**
   * 选择词语
   */
  function selectWord(word: string | null) {
    selectedWord.value = word;
    if (word) {
      fetchWordDetail(word);
    } else {
      wordDetail.value = null;
    }
  }
  
  /**
   * 清除选择
   */
  function clearSelection() {
    selectedWord.value = null;
    wordDetail.value = null;
    currentTopic.value = null;
  }
  
  /**
   * 重置 Store
   */
  function $reset() {
    wordCloudData.value = [];
    timelineWordCloud.value = [];
    hotTopics.value = [];
    totalTopics.value = 0;
    currentTopic.value = null;
    hotSearch.value = [];
    monitorKeywords.value = [];
    rankedTopics.value = [];
    triDimensionConfig.value = {
      sentiment_weight: 0.6,
      popularity_weight: 0.4,
      time_decay_hours: 24,
    };
    selectedWord.value = null;
    wordDetail.value = null;
    isLoading.value = false;
    isLoadingWordCloud.value = false;
    isLoadingTopics.value = false;
    isLoadingHotSearch.value = false;
    isLoadingRankedTopics.value = false;
    isSavingConfig.value = false;
  }

  return {
    // State
    wordCloudData,
    timelineWordCloud,
    hotTopics,
    totalTopics,
    currentTopic,
    hotSearch,
    monitorKeywords,
    rankedTopics,
    triDimensionConfig,
    selectedWord,
    wordDetail,
    isLoading,
    isLoadingWordCloud,
    isLoadingTopics,
    isLoadingHotSearch,
    isLoadingRankedTopics,
    isSavingConfig,
    
    // Getters
    topicsByHeat,
    topicsByTrend,
    positiveTopics,
    negativeTopics,
    topHotSearch,
    wordCloudStats,
    topRankedTopics,
    positiveRankedTopics,
    negativeRankedTopics,
    
    // Actions
    fetchWordCloudData,
    fetchTimelineWordCloud,
    fetchWordDetail,
    fetchWordRelatedWeibos,
    fetchHotTopics,
    fetchTopicDetail,
    fetchHotSearch,
    fetchTopicTrend,
    fetchMonitorKeywords,
    addKeywordToMonitor,
    removeKeywordFromMonitor,
    updateKeywordMonitorConfig,
    fetchRankedTopics,
    fetchTriDimensionConfig,
    saveTriDimensionConfig,
    selectWord,
    clearSelection,
    $reset,
  };
});
