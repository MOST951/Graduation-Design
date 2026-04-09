/**
 * 统一API接口 (v2版本)
 * 
 * 整合所有核心功能的前端API调用
 * 
 * 功能：
 * 1. 数据采集接口
 * 2. 情感分析接口
 * 3. 双维度排序接口
 * 4. 统计分析接口
 * 5. 系统监控接口
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API基础配置
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v2`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// ==================== 类型定义 ====================

export interface SystemStatus {
  modules: {
    pipeline: boolean;
    spark: boolean;
    hybrid_analyzer: boolean;
    dual_dimension: boolean;
  };
  data_dir: string;
  data_files: {
    crawl_results: number;
    processed: number;
    analysis: number;
  };
  timestamp: string;
}

export interface CrawlParams {
  keywords?: string[];
  crawl_hot?: boolean;
  pages?: number;
}

export interface CrawlResult {
  total_crawled: number;
  total_cleaned: number;
  total_duplicates: number;
  total_processed: number;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  top_keywords: Array<{ word: string; count: number }>;
}

export interface SentimentAnalysisResult {
  text: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  score: number;
  confidence: number;
  label?: string;
  fusion_method?: string;
}

export interface BatchSentimentResult {
  results: SentimentAnalysisResult[];
  total: number;
}

export interface SentimentDistribution {
  distribution: {
    positive: number;
    neutral: number;
    negative: number;
    total: number;
  };
  percentage: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

export interface DualDimensionParams {
  data?: any[];
  sentiment_weight?: number;
  heat_weight?: number;
  timeliness_weight?: number;
  top_k?: number;
}

export interface RankedItem {
  id: string;
  text: string;
  sentiment_score: number;
  heat_score: number;
  dual_score: number;
  rank: number;
  user_name?: string;
  reposts_count?: number;
  comments_count?: number;
  attitudes_count?: number;
}

export interface DualDimensionResult {
  ranked_items: RankedItem[];
  total: number;
  quadrant_distribution: {
    high_sentiment_high_heat: number;
    high_sentiment_low_heat: number;
    low_sentiment_high_heat: number;
    low_sentiment_low_heat: number;
  };
  config: {
    sentiment_weight: number;
    heat_weight: number;
  };
}

export interface QuadrantAnalysis {
  distribution: {
    high_sentiment_high_heat: number;
    high_sentiment_low_heat: number;
    low_sentiment_high_heat: number;
    low_sentiment_low_heat: number;
  };
  samples: {
    high_sentiment_high_heat: RankedItem[];
    high_sentiment_low_heat: RankedItem[];
    low_sentiment_high_heat: RankedItem[];
    low_sentiment_low_heat: RankedItem[];
  };
  total: number;
}

export interface OverviewStats {
  total_weibo: number;
  total_users: number;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  top_keywords: Array<[string, number]>;
  time_range: {
    earliest: string | null;
    latest: string | null;
  };
}

export interface TrendData {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  count: number;
}

export interface HotSearchItem {
  rank: number;
  title: string;
  hot_value: number;
  category?: string;
  is_hot?: boolean;
  is_new?: boolean;
}

// ==================== API函数 ====================

/**
 * 获取系统状态
 */
export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await apiClient.get('/status');
  return response.data.data;
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{ version: string; timestamp: string }> {
  const response = await apiClient.get('/health');
  return response.data;
}

// ==================== 数据采集 ====================

/**
 * 启动数据采集
 */
export async function startCrawl(params: CrawlParams = {}): Promise<CrawlResult> {
  const response = await apiClient.post('/crawl/start', params);
  return response.data.data;
}

/**
 * 获取热搜榜
 */
export async function getHotSearch(): Promise<HotSearchItem[]> {
  const response = await apiClient.get('/crawl/hot-search');
  return response.data.data;
}

// ==================== 情感分析 ====================

/**
 * 分析单条文本情感
 */
export async function analyzeSentiment(
  text: string,
  options: {
    method?: 'lexicon' | 'bert' | 'hybrid';
    context?: Record<string, any>;
  } = {}
): Promise<SentimentAnalysisResult> {
  const response = await apiClient.post('/sentiment/analyze', {
    text,
    method: options.method || 'hybrid',
    context: options.context,
  });
  return response.data.data;
}

/**
 * 批量分析文本情感
 */
export async function analyzeSentimentBatch(
  texts: string[],
  method: 'lexicon' | 'bert' | 'hybrid' = 'hybrid'
): Promise<BatchSentimentResult> {
  const response = await apiClient.post('/sentiment/analyze', {
    texts,
    method,
  });
  return response.data.data;
}

/**
 * 获取情感分布
 */
export async function getSentimentDistribution(): Promise<SentimentDistribution> {
  const response = await apiClient.get('/sentiment/distribution');
  return response.data.data;
}

// ==================== 双维度排序 ====================

/**
 * 执行双维度排序
 */
export async function rankDualDimension(
  params: DualDimensionParams = {}
): Promise<DualDimensionResult> {
  const response = await apiClient.post('/ranking/dual-dimension', params);
  return response.data.data;
}

/**
 * 获取四象限分析
 */
export async function getQuadrantAnalysis(): Promise<QuadrantAnalysis> {
  const response = await apiClient.get('/ranking/quadrant-analysis');
  return response.data.data;
}

// ==================== 统计分析 ====================

/**
 * 获取数据概览统计
 */
export async function getOverviewStats(): Promise<OverviewStats> {
  const response = await apiClient.get('/stats/overview');
  return response.data.data;
}

/**
 * 获取情感趋势
 */
export async function getSentimentTrend(days: number = 7): Promise<TrendData[]> {
  const response = await apiClient.get('/stats/trend', {
    params: { days },
  });
  return response.data.data;
}

// ==================== 缓存优化 ====================

// 简单的内存缓存
const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 60000; // 1分钟缓存

function getCached<T>(key: string): T | null {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data as T;
  }
  return null;
}

function setCache(key: string, data: any): void {
  cache.set(key, { data, timestamp: Date.now() });
}

/**
 * 获取系统状态（带缓存）
 */
export async function getSystemStatusCached(): Promise<SystemStatus> {
  const cacheKey = 'system_status';
  const cached = getCached<SystemStatus>(cacheKey);
  if (cached) return cached;
  
  const data = await getSystemStatus();
  setCache(cacheKey, data);
  return data;
}

/**
 * 获取概览统计（带缓存）
 */
export async function getOverviewStatsCached(): Promise<OverviewStats> {
  const cacheKey = 'overview_stats';
  const cached = getCached<OverviewStats>(cacheKey);
  if (cached) return cached;
  
  const data = await getOverviewStats();
  setCache(cacheKey, data);
  return data;
}

/**
 * 获取情感分布（带缓存）
 */
export async function getSentimentDistributionCached(): Promise<SentimentDistribution> {
  const cacheKey = 'sentiment_dist';
  const cached = getCached<SentimentDistribution>(cacheKey);
  if (cached) return cached;
  
  const data = await getSentimentDistribution();
  setCache(cacheKey, data);
  return data;
}

/**
 * 清除缓存
 */
export function clearCache(): void {
  cache.clear();
}

// ==================== 导出默认对象 ====================

export default {
  // 系统状态
  getSystemStatus,
  getSystemStatusCached,
  healthCheck,
  
  // 数据采集
  startCrawl,
  getHotSearch,
  
  // 情感分析
  analyzeSentiment,
  analyzeSentimentBatch,
  getSentimentDistribution,
  getSentimentDistributionCached,
  
  // 双维度排序
  rankDualDimension,
  getQuadrantAnalysis,
  
  // 统计分析
  getOverviewStats,
  getOverviewStatsCached,
  getSentimentTrend,
  
  // 缓存管理
  clearCache,
};

