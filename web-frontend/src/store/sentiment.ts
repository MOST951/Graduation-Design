/**
 * 情感分析 Store
 * 管理情感分析结果、模型状态和统计数据
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  analyzeSentiment,
  getAnalysisTaskStatus,
  getSentimentResults,
  getAnalysisStats,
  getRealTimeSentiment,
  getModels,
  getModelDetail,
  trainModel,
  getTrainingStatus,
  setDefaultModel,
  type AnalysisRequest,
  type AnalysisTask,
  type SentimentResult,
  type AnalysisStats,
  type ModelInfo,
  type TrainingStatus,
  type SentimentType,
} from '@/api/sentiment';

export const useSentimentStore = defineStore('sentiment', () => {
  // ==================== State ====================
  
  /** 分析结果列表 */
  const analysisResults = ref<SentimentResult[]>([]);
  
  /** 分析结果总数 */
  const analysisResultsTotal = ref(0);
  
  /** 当前分析任务 */
  const currentTask = ref<AnalysisTask | null>(null);
  
  /** 分析统计 */
  const analysisStats = ref<AnalysisStats | null>(null);
  
  /** 实时情感数据 */
  const realtimeSentiment = ref<{
    recentResults: SentimentResult[];
    stats: { last1h: AnalysisStats; last24h: AnalysisStats };
    trend: { time: string; positive: number; negative: number }[];
  } | null>(null);
  
  /** 模型列表 */
  const models = ref<ModelInfo[]>([]);
  
  /** 当前选中的模型 */
  const selectedModel = ref<ModelInfo | null>(null);
  
  /** 训练状态 */
  const trainingStatus = ref<TrainingStatus | null>(null);
  
  /** 情感分布 */
  const sentimentDistribution = ref<{
    positive: number;
    neutral: number;
    negative: number;
  }>({ positive: 0, neutral: 0, negative: 0 });
  
  /** 加载状态 */
  const isLoading = ref(false);
  const isAnalyzing = ref(false);
  const isTraining = ref(false);
  
  /** 错误信息 */
  const error = ref<string | null>(null);

  // ==================== Getters ====================
  
  /** 默认模型 */
  const defaultModel = computed(() => 
    models.value.find(m => m.isDefault) || models.value[0]
  );
  
  /** 正面结果 */
  const positiveResults = computed(() => 
    analysisResults.value.filter(r => r.sentiment === 'positive')
  );
  
  /** 负面结果 */
  const negativeResults = computed(() => 
    analysisResults.value.filter(r => r.sentiment === 'negative')
  );
  
  /** 中性结果 */
  const neutralResults = computed(() => 
    analysisResults.value.filter(r => r.sentiment === 'neutral')
  );
  
  /** 正面比例 */
  const positiveRatio = computed(() => {
    const total = analysisResults.value.length;
    return total > 0 ? (positiveResults.value.length / total) * 100 : 0;
  });
  
  /** 负面比例 */
  const negativeRatio = computed(() => {
    const total = analysisResults.value.length;
    return total > 0 ? (negativeResults.value.length / total) * 100 : 0;
  });
  
  /** 平均置信度 */
  const avgConfidence = computed(() => {
    if (analysisResults.value.length === 0) return 0;
    const sum = analysisResults.value.reduce((acc, r) => acc + r.confidence, 0);
    return sum / analysisResults.value.length;
  });
  
  /** 是否有任务在运行 */
  const hasRunningTask = computed(() => 
    currentTask.value?.status === 'processing' || currentTask.value?.status === 'pending'
  );

  // ==================== Actions ====================
  
  /**
   * 执行情感分析
   */
  async function analyze(request: AnalysisRequest) {
    isAnalyzing.value = true;
    error.value = null;
    
    try {
      const task = await analyzeSentiment(request);
      currentTask.value = task;
      return task;
    } catch (err: any) {
      error.value = err.message || '分析失败';
      throw err;
    } finally {
      isAnalyzing.value = false;
    }
  }
  
  /**
   * 获取分析任务状态
   */
  async function getTaskStatus(taskId: string) {
    try {
      const task = await getAnalysisTaskStatus(taskId);
      currentTask.value = task;
      
      // 如果任务完成，更新统计
      if (task.status === 'completed' && task.stats) {
        analysisStats.value = task.stats;
      }
      
      return task;
    } catch (err: any) {
      console.error('获取任务状态失败:', err);
      throw err;
    }
  }
  
  /**
   * 获取分析结果列表
   */
  async function fetchResults(params: {
    taskId?: string;
    page?: number;
    pageSize?: number;
    sentiment?: SentimentType | '';
    keyword?: string;
  } = {}) {
    isLoading.value = true;
    
    try {
      const response = await getSentimentResults(params);
      analysisResults.value = response.list;
      analysisResultsTotal.value = response.total;
      
      // 更新情感分布
      updateDistribution();
      
      return response;
    } catch (err: any) {
      error.value = err.message || '获取结果失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 获取分析统计
   */
  async function fetchStats(params?: { taskId?: string; dateRange?: [string, string] }) {
    try {
      const stats = await getAnalysisStats(params);
      analysisStats.value = stats;
      return stats;
    } catch (err: any) {
      console.error('获取统计失败:', err);
      throw err;
    }
  }
  
  /**
   * 获取实时情感数据
   */
  async function fetchRealtimeSentiment() {
    try {
      const data = await getRealTimeSentiment();
      realtimeSentiment.value = data;
      return data;
    } catch (err: any) {
      console.error('获取实时数据失败:', err);
      throw err;
    }
  }
  
  /**
   * 获取模型列表
   */
  async function fetchModels() {
    try {
      const list = await getModels();
      models.value = list;
      
      // 设置默认选中的模型
      if (!selectedModel.value && list.length > 0) {
        selectedModel.value = list.find(m => m.isDefault) || list[0];
      }
      
      return list;
    } catch (err: any) {
      console.error('获取模型列表失败:', err);
      throw err;
    }
  }
  
  /**
   * 获取模型详情
   */
  async function fetchModelDetail(modelId: string) {
    try {
      const model = await getModelDetail(modelId);
      selectedModel.value = model;
      return model;
    } catch (err: any) {
      console.error('获取模型详情失败:', err);
      throw err;
    }
  }
  
  /**
   * 训练新模型
   */
  async function startTraining(config: any) {
    isTraining.value = true;
    error.value = null;
    
    try {
      const result = await trainModel(config);
      return result;
    } catch (err: any) {
      error.value = err.message || '训练失败';
      throw err;
    } finally {
      isTraining.value = false;
    }
  }
  
  /**
   * 获取训练状态
   */
  async function fetchTrainingStatus(taskId: string) {
    try {
      const status = await getTrainingStatus(taskId);
      trainingStatus.value = status;
      return status;
    } catch (err: any) {
      console.error('获取训练状态失败:', err);
      throw err;
    }
  }
  
  /**
   * 设置默认模型
   */
  async function setAsDefaultModel(modelId: string) {
    try {
      await setDefaultModel(modelId);
      
      // 更新本地状态
      models.value.forEach(m => {
        m.isDefault = m.id === modelId;
      });
      
      // 更新选中的模型
      const model = models.value.find(m => m.id === modelId);
      if (model) {
        selectedModel.value = model;
      }
    } catch (err: any) {
      error.value = err.message || '设置默认模型失败';
      throw err;
    }
  }
  
  /**
   * 更新情感分布
   */
  function updateDistribution() {
    const total = analysisResults.value.length;
    if (total === 0) {
      sentimentDistribution.value = { positive: 0, neutral: 0, negative: 0 };
      return;
    }
    
    sentimentDistribution.value = {
      positive: positiveResults.value.length,
      neutral: neutralResults.value.length,
      negative: negativeResults.value.length,
    };
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
    analysisResults.value = [];
    analysisResultsTotal.value = 0;
    currentTask.value = null;
    analysisStats.value = null;
    realtimeSentiment.value = null;
    models.value = [];
    selectedModel.value = null;
    trainingStatus.value = null;
    sentimentDistribution.value = { positive: 0, neutral: 0, negative: 0 };
    isLoading.value = false;
    isAnalyzing.value = false;
    isTraining.value = false;
    error.value = null;
  }

  return {
    // State
    analysisResults,
    analysisResultsTotal,
    currentTask,
    analysisStats,
    realtimeSentiment,
    models,
    selectedModel,
    trainingStatus,
    sentimentDistribution,
    isLoading,
    isAnalyzing,
    isTraining,
    error,
    
    // Getters
    defaultModel,
    positiveResults,
    negativeResults,
    neutralResults,
    positiveRatio,
    negativeRatio,
    avgConfidence,
    hasRunningTask,
    
    // Actions
    analyze,
    getTaskStatus,
    fetchResults,
    fetchStats,
    fetchRealtimeSentiment,
    fetchModels,
    fetchModelDetail,
    startTraining,
    fetchTrainingStatus,
    setAsDefaultModel,
    updateDistribution,
    clearError,
    $reset,
  };
});
