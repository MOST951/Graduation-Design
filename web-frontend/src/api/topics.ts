/**
 * 热点话题模块 API
 * 包含降级方案，确保前端在后端不可用时仍能正常展示
 */
import apiClient from './index';
import FallbackDataService from '@/services/fallbackDataService';

// ==================== 类型定义 ====================

/** 词语数据 */
export interface WordData {
  name: string;
  value: number;
  count: number;
  sentiment: 'positive' | 'neutral' | 'negative';
  trend: number;
  relatedWords?: string[];
}

/** 话题数据 */
export interface TopicData {
  id: number;
  name: string;
  heat: number;
  heatTrend: number;
  sentiment: 'positive' | 'neutral' | 'negative';
  sentimentScore: number;
  weiboCount: number;
  startTime: string;
  peakTime?: string;
  keywords: string[];
  summary?: string;
}

/** 热搜数据 */
export interface HotSearchData {
  rank: number;
  title: string;
  heat: number;
  heatText: string;
  category: string;
  isNew: boolean;
  isHot: boolean;
  sentiment: 'positive' | 'neutral' | 'negative';
  url?: string;
}

/** 时间序列词云数据 */
export interface TimelineWordCloud {
  time: string;
  words: WordData[];
}

/** 话题详情 */
export interface TopicDetail extends TopicData {
  description: string;
  relatedTopics: { id: number; name: string; heat: number }[];
  keyOpinions: { content: string; author: string; likes: number; sentiment: string }[];
  timeline: { time: string; event: string }[];
  sentimentDistribution: { sentiment: string; count: number; ratio: number }[];
  hourlyTrend: { hour: string; heat: number; sentiment: number }[];
}

/** 词云配置 */
export interface WordCloudConfig {
  shape: string;
  colorScheme: string;
  fontFamily: string;
  minFontSize: number;
  maxFontSize: number;
  rotationRange: [number, number];
  wordCount: number;
}

/** 分页响应 */
export interface PageResponse<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** 话题演变数据 */
export interface TopicEvolution {
  id: number;
  type: 'merge' | 'split' | 'emerge' | 'fade';
  typeLabel: string;
  time: string;
  from?: string | string[];
  to?: string | string[];
  topic?: string;
  description: string;
}

/** 传播节点 */
export interface PropagationNode {
  id: string;
  name: string;
  type: 'origin' | 'kol' | 'media' | 'user';
  typeLabel: string;
  followers: number;
  spreadCount: number;
  spreadDepth: number;
  influenceScore: number;
  sentiment: string;
  avatar?: string;
  verified?: boolean;
}

/** 传播边 */
export interface PropagationEdge {
  source: string;
  target: string;
  type: 'repost' | 'comment' | 'quote';
  weight: number;
  time: string;
}

/** 传播统计 */
export interface PropagationStats {
  totalNodes: number;
  totalEdges: number;
  maxDepth: number;
  avgSpeed: string;
  totalReach: number;
  depthDistribution: { depth: number; count: number }[];
  speedTrend: { time: string; speed: number }[];
}

/** KOL数据 */
export interface KOLData {
  id: number;
  name: string;
  avatar: string;
  followers: number;
  following: number;
  spreadCount: number;
  influenceScore: number;
  verified: boolean;
  bio?: string;
  sentiment: string;
  sentimentLabel: string;
}

/** 预测话题 */
export interface PredictedTopic {
  id: number;
  topic: string;
  predictedHeat: number;
  currentHeat: number;
  heatChange: number;
  confidence: number;
  peakTime: string;
  isNew: boolean;
  isRising: boolean;
  keyFactors: string[];
  factorDetails: { name: string; weight: number; description: string }[];
}

/** 预测准确率 */
export interface PredictionAccuracy {
  overall: number;
  top10Hit: number;
  heatError: number;
  timeError: number;
  falsePositive: number;
  dailyAccuracy: { date: string; accuracy: number }[];
}

/** 热搜历史 */
export interface HotSearchHistory {
  topic: string;
  records: {
    time: string;
    rank: number;
    heat: number;
    sentiment: string;
  }[];
  peakRank: number;
  peakTime: string;
  totalDuration: number;
  avgRank: number;
}

/** 预测模型配置 */
export interface PredictionModelConfig {
  model: 'arima' | 'social' | 'lstm' | 'ensemble';
  timeRange: '1h' | '6h' | '24h' | '7d';
  confidenceThreshold: number;
  features: string[];
  count: number;
}

// ==================== 词云相关 API ====================

/**
 * 获取词云数据
 */
export async function getWordCloudData(params?: {
  dateRange?: [string, string];
  source?: string;
  sentiment?: string;
  limit?: number;
}): Promise<WordData[]> {
  const response = await apiClient.get('/topics/wordcloud', { params });
  return response.data.data;
}

/**
 * 获取时间序列词云数据
 */
export async function getTimelineWordCloud(params: {
  startDate: string;
  endDate: string;
  interval: 'hour' | 'day' | 'week';
}): Promise<TimelineWordCloud[]> {
  const response = await apiClient.get('/topics/wordcloud/timeline', { params });
  return response.data.data;
}

/**
 * 获取词语详情
 */
export async function getWordDetail(word: string): Promise<{
  word: string;
  totalCount: number;
  trend: number;
  sentiment: { positive: number; neutral: number; negative: number };
  relatedWords: { word: string; correlation: number }[];
  dailyTrend: { date: string; count: number }[];
  sources: { source: string; count: number }[];
}> {
  const response = await apiClient.get(`/topics/words/${encodeURIComponent(word)}`);
  return response.data.data;
}

/**
 * 获取词语相关微博
 */
export async function getWordRelatedWeibos(word: string, params?: {
  page?: number;
  pageSize?: number;
  sentiment?: string;
}): Promise<PageResponse<{
  id: number;
  content: string;
  author: string;
  sentiment: string;
  sentimentLabel: string;
  likes: number;
  comments: number;
  reposts: number;
  time: string;
}>> {
  const response = await apiClient.get(`/topics/words/${encodeURIComponent(word)}/weibos`, { params });
  return response.data.data;
}

// ==================== 热点话题 API ====================

/**
 * 获取热点话题列表
 */
export async function getHotTopics(params?: {
  page?: number;
  pageSize?: number;
  category?: string;
  sentiment?: string;
  sortBy?: 'heat' | 'trend' | 'time';
  sortOrder?: 'asc' | 'desc';
}): Promise<PageResponse<TopicData>> {
  const response = await apiClient.get('/topics/hot', { params });
  return response.data.data;
}

/**
 * 获取话题详情
 */
export async function getTopicDetail(id: number): Promise<TopicDetail> {
  const response = await apiClient.get(`/topics/${id}`);
  return response.data.data;
}

/**
 * 获取实时热搜
 */
export async function getHotSearch(): Promise<HotSearchData[]> {
  const response = await apiClient.get('/topics/hotsearch');
  return response.data.data;
}

/**
 * 获取话题趋势
 */
export async function getTopicTrend(id: number, params?: {
  startDate?: string;
  endDate?: string;
  interval?: 'hour' | 'day';
}): Promise<{
  heatTrend: { time: string; heat: number }[];
  sentimentTrend: { time: string; positive: number; negative: number }[];
  volumeTrend: { time: string; count: number }[];
}> {
  const response = await apiClient.get(`/topics/${id}/trend`, { params });
  return response.data.data;
}

// ==================== 话题监控 API ====================

/**
 * 获取监控关键词列表
 */
export async function getMonitorKeywords(): Promise<{
  id: number;
  keyword: string;
  createdAt: string;
  alertEnabled: boolean;
  alertThreshold: number;
}[]> {
  const response = await apiClient.get('/topics/monitor/keywords');
  return response.data.data;
}

/**
 * 添加监控关键词
 */
export async function addMonitorKeyword(keyword: string, config?: {
  alertEnabled?: boolean;
  alertThreshold?: number;
}): Promise<void> {
  await apiClient.post('/topics/monitor/keywords', { keyword, ...config });
}

/**
 * 删除监控关键词
 */
export async function removeMonitorKeyword(id: number): Promise<void> {
  await apiClient.delete(`/topics/monitor/keywords/${id}`);
}

/**
 * 更新监控配置
 */
export async function updateMonitorConfig(id: number, config: {
  alertEnabled?: boolean;
  alertThreshold?: number;
}): Promise<void> {
  await apiClient.put(`/topics/monitor/keywords/${id}`, config);
}

// ==================== 话题分析 API ====================

/**
 * 获取话题情感分析
 */
export async function getTopicSentiment(id: number): Promise<{
  overall: { positive: number; neutral: number; negative: number };
  timeline: { time: string; positive: number; neutral: number; negative: number }[];
  keywords: { word: string; sentiment: string; count: number }[];
}> {
  const response = await apiClient.get(`/topics/${id}/sentiment`);
  return response.data.data;
}

/**
 * 获取话题传播分析
 */
export async function getTopicSpread(id: number): Promise<{
  originCount: number;
  repostCount: number;
  spreadDepth: number;
  keyNodes: { author: string; followers: number; reposts: number }[];
  spreadPath: { from: string; to: string; count: number }[];
}> {
  const response = await apiClient.get(`/topics/${id}/spread`);
  return response.data.data;
}

/**
 * 导出话题报告
 */
export async function exportTopicReport(id: number, format: 'pdf' | 'docx' | 'html'): Promise<Blob> {
  const response = await apiClient.get(`/topics/${id}/export`, {
    params: { format },
    responseType: 'blob',
  });
  return response.data;
}

// ==================== 1. 话题发现 API ====================

/**
 * 发现热点话题
 */
export async function discoverTopics(params?: {
  dateRange?: [string, string];
  source?: string;
  category?: string;
  minHeat?: number;
  limit?: number;
}): Promise<TopicData[]> {
  const response = await apiClient.get('/topics/discover', { params });
  return response.data.data;
}

/**
 * 获取话题趋势
 */
export async function getTopicTrends(topicId: number, params?: {
  startDate?: string;
  endDate?: string;
  interval?: 'hour' | 'day' | 'week';
}): Promise<{
  heatTrend: { time: string; heat: number }[];
  sentimentTrend: { time: string; positive: number; neutral: number; negative: number }[];
  volumeTrend: { time: string; count: number }[];
  keywordTrend: { time: string; keywords: { word: string; count: number }[] }[];
}> {
  const response = await apiClient.get(`/topics/${topicId}/trends`, { params });
  return response.data.data;
}

/**
 * 分析话题演变
 */
export async function analyzeTopicEvolution(params: {
  startDate: string;
  endDate: string;
  topicIds?: number[];
}): Promise<{
  evolutions: TopicEvolution[];
  topicTimeline: { time: string; topics: { id: number; name: string; heat: number }[] }[];
  relationGraph: { nodes: { id: number; name: string }[]; edges: { source: number; target: number; weight: number }[] };
}> {
  const response = await apiClient.post('/topics/evolution/analyze', params);
  return response.data.data;
}

// ==================== 2. 词云相关 API ====================

/**
 * 生成词云数据
 */
export async function generateWordCloud(params: {
  source?: 'all' | 'weibo' | 'comment' | 'repost';
  dateRange?: [string, string];
  topicId?: number;
  sentiment?: string;
  excludeWords?: string[];
  limit?: number;
  config?: WordCloudConfig;
}): Promise<{
  words: WordData[];
  totalCount: number;
  generatedAt: string;
}> {
  const response = await apiClient.post('/topics/wordcloud/generate', params);
  return response.data.data;
}

/**
 * 获取词语趋势
 */
export async function getWordTrends(word: string, params?: {
  startDate?: string;
  endDate?: string;
  interval?: 'hour' | 'day' | 'week';
}): Promise<{
  word: string;
  trend: { time: string; count: number; heat: number }[];
  sentimentTrend: { time: string; positive: number; neutral: number; negative: number }[];
  coOccurrence: { word: string; count: number; correlation: number }[];
}> {
  const response = await apiClient.get(`/topics/words/${encodeURIComponent(word)}/trends`, { params });
  return response.data.data;
}

/**
 * 获取相关词语
 */
export async function getRelatedWords(word: string, params?: {
  limit?: number;
  minCorrelation?: number;
}): Promise<{
  word: string;
  relatedWords: {
    word: string;
    correlation: number;
    coOccurrenceCount: number;
    sentiment: string;
  }[];
  synonyms: string[];
  antonyms: string[];
}> {
  const response = await apiClient.get(`/topics/words/${encodeURIComponent(word)}/related`, { params });
  return response.data.data;
}

// ==================== 3. 热搜榜单 API ====================

/**
 * 获取热搜榜单
 */
export async function getHotSearchList(platform: 'weibo' | 'baidu' | 'zhihu' | 'douyin' | 'all'): Promise<{
  platform: string;
  updateTime: string;
  list: HotSearchData[];
}> {
  const response = await apiClient.get('/topics/hotsearch/list', { params: { platform } });
  return response.data.data;
}

/**
 * 获取热搜历史
 */
export async function getHotSearchHistory(topic: string, params?: {
  startDate?: string;
  endDate?: string;
  platform?: string;
}): Promise<HotSearchHistory> {
  const response = await apiClient.get('/topics/hotsearch/history', { params: { topic, ...params } });
  return response.data.data;
}

/**
 * 监控热搜话题
 */
export async function monitorHotSearch(config: {
  topic: string;
  platform?: string;
  rankThreshold?: number;
  alertEnabled?: boolean;
  notifyMethods?: string[];
}): Promise<{ id: number; createdAt: string }> {
  const response = await apiClient.post('/topics/hotsearch/monitor', config);
  return response.data.data;
}

/**
 * 获取热搜监控列表
 */
export async function getHotSearchMonitors(): Promise<{
  id: number;
  topic: string;
  platform: string;
  rankThreshold: number;
  alertEnabled: boolean;
  notifyMethods: string[];
  createdAt: string;
  lastTriggered?: string;
}[]> {
  const response = await apiClient.get('/topics/hotsearch/monitors');
  return response.data.data;
}

/**
 * 删除热搜监控
 */
export async function removeHotSearchMonitor(id: number): Promise<void> {
  await apiClient.delete(`/topics/hotsearch/monitors/${id}`);
}

// ==================== 4. 传播分析 API ====================

/**
 * 分析传播路径
 */
export async function analyzePropagation(topicId: number, params?: {
  maxDepth?: number;
  minInfluence?: number;
}): Promise<{
  nodes: PropagationNode[];
  edges: PropagationEdge[];
  keyPaths: {
    path: string[];
    influence: number;
    reach: number;
    duration: string;
  }[];
}> {
  const response = await apiClient.get(`/topics/${topicId}/propagation`, { params });
  return response.data.data;
}

/**
 * 获取KOL列表
 */
export async function getKeyOpinionLeaders(topicId: number, params?: {
  page?: number;
  pageSize?: number;
  sortBy?: 'influence' | 'followers' | 'spread';
}): Promise<PageResponse<KOLData>> {
  const response = await apiClient.get(`/topics/${topicId}/kols`, { params });
  return response.data.data;
}

/**
 * 获取传播统计
 */
export async function getPropagationStats(topicId: number): Promise<PropagationStats> {
  const response = await apiClient.get(`/topics/${topicId}/propagation/stats`);
  return response.data.data;
}

/**
 * 获取传播时间线
 */
export async function getPropagationTimeline(topicId: number, params?: {
  interval?: 'minute' | 'hour' | 'day';
}): Promise<{
  timeline: {
    time: string;
    newNodes: number;
    newEdges: number;
    totalReach: number;
    topUsers: { name: string; action: string }[];
  }[];
}> {
  const response = await apiClient.get(`/topics/${topicId}/propagation/timeline`, { params });
  return response.data.data;
}

// ==================== 5. 预测功能 API ====================

/**
 * 预测热点话题
 */
export async function predictHotTopics(config: PredictionModelConfig): Promise<{
  predictions: PredictedTopic[];
  modelUsed: string;
  generatedAt: string;
  nextUpdateAt: string;
}> {
  const response = await apiClient.post('/topics/predict', config);
  return response.data.data;
}

/**
 * 获取预测准确率
 */
export async function getPredictionAccuracy(params?: {
  model?: string;
  startDate?: string;
  endDate?: string;
}): Promise<PredictionAccuracy> {
  const response = await apiClient.get('/topics/predict/accuracy', { params });
  return response.data.data;
}

/**
 * 训练预测模型
 */
export async function trainPredictionModel(data: {
  modelType: 'arima' | 'social' | 'lstm' | 'ensemble';
  trainingData?: {
    startDate: string;
    endDate: string;
  };
  hyperparameters?: Record<string, any>;
}): Promise<{
  taskId: string;
  status: 'pending' | 'training' | 'completed' | 'failed';
  estimatedTime: number;
}> {
  const response = await apiClient.post('/topics/predict/train', data);
  return response.data.data;
}

/**
 * 获取模型训练状态
 */
export async function getModelTrainingStatus(taskId: string): Promise<{
  taskId: string;
  status: 'pending' | 'training' | 'completed' | 'failed';
  progress: number;
  metrics?: {
    accuracy: number;
    loss: number;
    epoch: number;
  };
  error?: string;
}> {
  const response = await apiClient.get(`/topics/predict/train/${taskId}`);
  return response.data.data;
}

/**
 * 获取可用预测模型
 */
export async function getAvailableModels(): Promise<{
  id: string;
  name: string;
  type: string;
  accuracy: number;
  trainedAt: string;
  isDefault: boolean;
}[]> {
  const response = await apiClient.get('/topics/predict/models');
  return response.data.data;
}

/**
 * 设置默认预测模型
 */
export async function setDefaultPredictionModel(modelId: string): Promise<void> {
  await apiClient.post(`/topics/predict/models/${modelId}/set-default`);
}

/**
 * 获取预测因素权重
 */
export async function getPredictionFactors(): Promise<{
  factors: {
    name: string;
    weight: number;
    description: string;
    trend: number;
  }[];
  insights: string[];
}> {
  const response = await apiClient.get('/topics/predict/factors');
  return response.data.data;
}

/**
 * 配置预测预警
 */
export async function configurePredictionAlert(config: {
  enabled: boolean;
  rankThreshold: number;
  minConfidence: number;
  frequency: 'realtime' | 'hourly' | 'daily';
  pushMethods: string[];
  webhookUrl?: string;
  keywords?: string[];
  excludeKeywords?: string[];
}): Promise<void> {
  await apiClient.post('/topics/predict/alert/config', config);
}

/**
 * 获取预测预警配置
 */
export async function getPredictionAlertConfig(): Promise<{
  enabled: boolean;
  rankThreshold: number;
  minConfidence: number;
  frequency: string;
  pushMethods: string[];
  webhookUrl?: string;
  keywords: string[];
  excludeKeywords: string[];
}> {
  const response = await apiClient.get('/topics/predict/alert/config');
  return response.data.data;
}

/**
 * 获取预警历史
 */
export async function getPredictionAlertHistory(params?: {
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
}): Promise<PageResponse<{
  id: number;
  topic: string;
  predictedRank: number;
  actualRank: number | null;
  hit: boolean;
  confidence: number;
  triggeredAt: string;
}>> {
  const response = await apiClient.get('/topics/predict/alert/history', { params });
  return response.data.data;
}

// ==================== 6. 三维度排序 API ====================

/** 三维度排序话题 */
export interface RankedTopic {
  topic_id: string | number;
  keywords: string[];
  composite_score: number;
  sentiment_avg: number;
  popularity_score: number;
  post_count: number;
  rank: number;
  name: string;
  trend: 'up' | 'stable' | 'down';
}

/** 后端返回的原始话题数据（字段名可能与前端不同） */
interface RawRankedTopicItem {
  topic_id?: string | number;
  keyword?: string;
  name?: string;
  keywords?: string[];
  composite_score?: number;
  sentiment_score?: number;
  sentiment_avg?: number;
  popularity_score?: number;
  weibo_count?: number;
  post_count?: number;
  rank?: number;
  trend?: 'up' | 'stable' | 'down';
}

/** 三维度配置 */
export interface TriDimensionConfig {
  sentiment_weight: number;
  popularity_weight: number;
  time_decay_hours: number;
}

/**
 * 获取三维度排序后的热点话题
 * GET /api/topics/ranked
 * 包含降级方案
 */
export async function getRankedTopics(): Promise<RankedTopic[]> {
  try {
    const response = await apiClient.get('/topics/ranked');
    FallbackDataService.resetErrorCount('rankedTopics');
    // 后端返回格式: { code: 200, data: { topics: [...] } }
    const topics = response.data?.data?.topics || response.data?.topics || response.data || [];
    return topics.map((item: RawRankedTopicItem, idx: number) => ({
      topic_id: item.topic_id || `topic_${idx}`,
      name: item.keyword || item.name || '',
      keywords: item.keywords || [item.keyword].filter(Boolean),
      composite_score: item.composite_score || 0,
      sentiment_avg: item.sentiment_score || item.sentiment_avg || 0,
      popularity_score: item.popularity_score || 0,
      post_count: item.weibo_count || item.post_count || 0,
      rank: item.rank || idx + 1,
      trend: item.trend || 'stable',
    }));
  } catch (error) {
    FallbackDataService.recordError('rankedTopics');
    console.warn('[API] 三维度排序API不可用，使用模拟数据');
    
    // 使用模拟数据
    const mockData = FallbackDataService.getMockRankedTopics();
    return mockData.map((item, idx) => ({
      topic_id: item.topic_id,
      name: item.name,
      keywords: item.keywords,
      composite_score: item.composite_score,
      sentiment_avg: item.sentiment_avg,
      popularity_score: item.popularity_score,
      post_count: item.post_count,
      rank: idx + 1,
      trend: item.trend,
    }));
  }
}

/**
 * 获取三维度排序配置
 * GET /api/topics/tri-dimension/config
 * 包含降级方案
 */
export async function getTriDimensionConfig(): Promise<TriDimensionConfig> {
  try {
    const response = await apiClient.get('/topics/tri-dimension/config');
    return response.data.data;
  } catch (error) {
    console.warn('[API] 三维度配置API不可用，使用默认配置');
    return FallbackDataService.getMockTriDimensionConfig();
  }
}

/**
 * 更新三维度排序配置
 * POST /api/topics/tri-dimension/config
 */
export async function updateTriDimensionConfig(config: Partial<TriDimensionConfig>): Promise<TriDimensionConfig> {
  const response = await apiClient.post('/topics/tri-dimension/config', config);
  return response.data.data;
}

export default {
  // 基础 API
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
  getTopicSentiment,
  getTopicSpread,
  exportTopicReport,
  
  // 1. 话题发现
  discoverTopics,
  getTopicTrends,
  analyzeTopicEvolution,
  
  // 2. 词云相关
  generateWordCloud,
  getWordTrends,
  getRelatedWords,
  
  // 3. 热搜榜单
  getHotSearchList,
  getHotSearchHistory,
  monitorHotSearch,
  getHotSearchMonitors,
  removeHotSearchMonitor,
  
  // 4. 传播分析
  analyzePropagation,
  getKeyOpinionLeaders,
  getPropagationStats,
  getPropagationTimeline,
  
  // 5. 预测功能
  predictHotTopics,
  getPredictionAccuracy,
  trainPredictionModel,
  getModelTrainingStatus,
  getAvailableModels,
  setDefaultPredictionModel,
  getPredictionFactors,
  configurePredictionAlert,
  getPredictionAlertConfig,
  getPredictionAlertHistory,
  
  // 6. 三维度排序
  getRankedTopics,
  getTriDimensionConfig,
  updateTriDimensionConfig,
};
