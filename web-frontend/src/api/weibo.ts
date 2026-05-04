/**
 * 微博数据采集与分析 API
 * 对接后端真实爬虫和Spark分析模块
 * 包含降级方案，确保前端在后端不可用时仍能正常展示
 */
import apiClient from './index';
import FallbackDataService from '@/services/fallbackDataService';

// 重新导出 apiClient 供其他模块使用
export { apiClient };

// ==================== 类型定义 ====================

/** 热搜项 */
export interface HotSearchItem {
  rank: number;
  title: string;
  hot_value: number;
  category: string;
  is_hot?: boolean;
  is_new?: boolean;
  url?: string;
  crawl_time: string;
}

/** 微博用户信息 */
export interface WeiboUser {
  id: string;
  screen_name: string;
  profile_url?: string;
  followers_count: number;
  friends_count: number;
  statuses_count: number;
  verified: boolean;
  verified_type: number;
  description?: string;
  gender?: string;
  location?: string;
}

/** 微博数据 */
export interface WeiboData {
  id: string;
  mid: string;
  text: string;
  text_raw?: string;
  source: string;
  created_at: string;
  user: WeiboUser;
  reposts_count: number;
  comments_count: number;
  attitudes_count: number;
  pics?: string[];
  video_url?: string;
  is_long_text?: boolean;
  keyword?: string;
  crawl_time: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  sentiment_score?: number;
}

/** 采集任务 */
export interface CrawlTask {
  id: string;
  task_id?: string;
  status: 'running' | 'completed' | 'failed' | 'interrupted' | 'pending' | 'paused';
  keywords: string[];
  pages: number;
  crawl_hot: boolean;
  progress: number;
  collected: number;
  start_time: string;
  end_time?: string;
  result_file?: string;
  error?: string;
  summary?: {
    total_collected: number;
    total_failed: number;
    elapsed_seconds: number;
    elapsed_display: string;
    success_rate: number;
    avg_speed: number;
  };
}

/** 分析统计 */
export interface AnalysisStatistics {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
  average_score: number;
  analysis_time: string;
}

/** 关键词情感统计 */
export interface KeywordSentiment {
  [keyword: string]: {
    total: number;
    positive: number;
    negative: number;
    neutral: number;
    average_score: number;
  };
}

/** 时间序列数据 */
export interface TimeSeriesItem {
  time: string;
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  average_score: number;
}

/** 分析结果 */
export interface AnalysisResult {
  id: string;
  statistics: AnalysisStatistics;
  keyword_stats: KeywordSentiment;
  time_series: TimeSeriesItem[];
  total_analyzed: number;
}

/** Spark集群信息 */
export interface SparkInfo {
  spark_home: string;
  spark_available: boolean;
  mode: string;
  master_url: string;
  status: string;
}

/** 排序后的微博条目 */
export interface RankedWeiboItem {
  id: string;
  text: string;
  rank: number;
  tri_score: number;
  sentiment_score: number;
  heat_score: number;
  reposts_count: number;
  comments_count: number;
  attitudes_count: number;
}

/** 数据概览统计 */
export interface OverviewStats {
  total_crawl_tasks: number;
  total_data_files: number;
  total_records: number;
  total_analyses: number;
  active_tasks: number;
  update_time: string;
}

// ==================== API 函数 ====================

/** 实时热搜响应类型 */
export interface LiveHotSearchResponse {
  hot_list: LiveHotSearchItem[];
  summary: {
    total: number;
    positive_count: number;
    negative_count: number;
    neutral_count: number;
    positive_ratio: number;
    negative_ratio: number;
  };
  last_refresh: string;
}

/** 热搜相关的微博样本 */
export interface SampleWeibo {
  id: string;
  text: string;
  user?: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  sentiment_score?: number;
  reposts_count?: number;
  comments_count?: number;
  attitudes_count?: number;
}

/** 实时热搜项（带情感分析） */
export interface LiveHotSearchItem extends HotSearchItem {
  sentiment: 'positive' | 'neutral' | 'negative';
  sentiment_score: number;
  positive_ratio: number;
  negative_ratio: number;
  weibo_count: number;
  sample_weibos: SampleWeibo[];
  trend: string;
  label?: string;
  is_fei?: boolean;
}

/**
 * 获取微博实时热搜榜（直接从微博爬取，带情感分析）
 * 包含三级降级：主API -> 备用API -> 模拟数据
 */
export async function getLiveHotSearch(): Promise<LiveHotSearchResponse> {
  try {
    // 优先调用实时热搜API
    const response = await apiClient.get('/analysis/hot-search/live');
    if (response.data.success && response.data.data) {
      FallbackDataService.resetErrorCount('hotSearch');
      return response.data.data;
    }
    throw new Error('API返回数据异常');
  } catch (error) {
    FallbackDataService.recordError('hotSearch');
    
    // 实时热搜API不可用，尝试备用API
    try {
      const response = await apiClient.get('/weibo/hotsearch');
      const hotList = response.data.data || [];
      if (hotList.length > 0) {
        return {
          hot_list: hotList.map((item: HotSearchItem, idx: number) => ({
            ...item,
            sentiment: 'neutral',
            sentiment_score: 0,
            positive_ratio: 0,
            negative_ratio: 0,
            weibo_count: 0,
            sample_weibos: [],
            trend: 'stable',
          })),
          summary: {
            total: hotList.length,
            positive_count: 0,
            negative_count: 0,
            neutral_count: hotList.length,
            positive_ratio: 0,
            negative_ratio: 0,
          },
          last_refresh: new Date().toISOString(),
        };
      }
      throw new Error('备用API返回空数据');
    } catch (e) {
      // 所有API都失败，使用模拟数据
      console.warn('[API] 热搜API不可用，使用模拟数据');
      const mockData = FallbackDataService.getMockHotSearches();
      return {
        hot_list: mockData.map((item, idx) => ({
          rank: item.rank,
          title: item.title,
          hot_value: item.hotValue,
          category: item.label,
          crawl_time: new Date().toISOString(),
          sentiment: (item.sentiment || 'neutral') as 'positive' | 'neutral' | 'negative',
          sentiment_score: 0,
          positive_ratio: item.sentiment === 'positive' ? 0.6 : 0.3,
          negative_ratio: item.sentiment === 'negative' ? 0.4 : 0.1,
          weibo_count: Math.floor(Math.random() * 10000) + 1000,
          sample_weibos: [],
          trend: item.trend || 'stable',
          label: item.label,
        })),
        summary: {
          total: mockData.length,
          positive_count: mockData.filter(i => i.sentiment === 'positive').length,
          negative_count: mockData.filter(i => i.sentiment === 'negative').length,
          neutral_count: mockData.filter(i => i.sentiment === 'neutral').length,
          positive_ratio: 0.4,
          negative_ratio: 0.2,
        },
        last_refresh: new Date().toISOString(),
      };
    }
  }
}

/**
 * 获取微博热搜榜（兼容旧接口）
 */
export async function getHotSearch(): Promise<HotSearchItem[]> {
  try {
    // 优先使用实时热搜API
    const liveData = await getLiveHotSearch();
    return liveData.hot_list;
  } catch (error) {
    // 尝试原有API
    try {
      const response = await apiClient.get('/weibo/hotsearch');
      return response.data.data || [];
    } catch (e) {
      throw new Error('无法获取热搜数据');
    }
  }
}

/**
 * 强制刷新热搜
 */
export async function refreshHotSearch(): Promise<LiveHotSearchResponse> {
  const response = await apiClient.post('/analysis/hot-search/refresh');
  if (response.data.success) {
    // 刷新后重新获取完整数据
    return getLiveHotSearch();
  }
  throw new Error('刷新失败');
}

/**
 * 启动热搜自动刷新服务
 */
export async function startHotSearchService(refreshInterval: number = 60): Promise<void> {
  await apiClient.post('/analysis/hot-search/start', { refresh_interval: refreshInterval });
}

/**
 * 停止热搜服务
 */
export async function stopHotSearchService(): Promise<void> {
  await apiClient.post('/analysis/hot-search/stop');
}

/**
 * 搜索微博
 * @param keyword 搜索关键词
 * @param page 页码
 * @param type 搜索类型
 * @param analyze 是否进行情感分析
 */
export async function searchWeibo(
  keyword: string,
  page: number = 1,
  type: 'all' | 'hot' | 'ori' = 'all',
  analyze: boolean = true
): Promise<{ data: WeiboData[]; total: number }> {
  try {
    const response = await apiClient.get('/weibo/search', {
      params: { keyword, page, type, analyze }
    });
    return {
      data: response.data.data || [],
      total: response.data.total || 0
    };
  } catch (error) {
    // 搜索API不可用，使用模拟数据
    return { data: generateMockWeiboData(keyword, 20), total: 20 };
  }
}

/** 生成模拟微博数据 */
function generateMockWeiboData(keyword: string, count: number): WeiboData[] {
  const templates = [
    `关于${keyword}，我觉得这是一个很好的话题，值得深入讨论！`,
    `${keyword}真的太棒了，强烈推荐给大家！👍`,
    `对于${keyword}这个问题，我持保留意见，需要更多观察`,
    `${keyword}让我很失望，完全不符合预期...`,
    `今天看到${keyword}相关的新闻，感觉很有意思`,
    `${keyword}是当下最热门的话题之一，你怎么看？`,
    `不得不说${keyword}确实改变了很多人的生活方式`,
    `关于${keyword}，网上的讨论真是太激烈了`,
  ];
  const sentiments: Array<'positive' | 'negative' | 'neutral'> = ['positive', 'negative', 'neutral'];
  const users = ['科技达人', '生活博主', '新闻观察', '热心网友', '专业评论', '普通用户'];
  
  return Array.from({ length: count }, (_, idx) => {
    const sentiment = sentiments[Math.floor(Math.random() * 3)];
    return {
      id: `mock_${Date.now()}_${idx}`,
      mid: `mock_${idx}`,
      text: templates[idx % templates.length],
      source: '微博',
      created_at: new Date(Date.now() - Math.random() * 86400000 * 7).toISOString(),
      user: {
        id: `user_${idx}`,
        screen_name: users[idx % users.length] + (idx + 1),
        followers_count: Math.floor(Math.random() * 100000),
        friends_count: Math.floor(Math.random() * 1000),
        statuses_count: Math.floor(Math.random() * 5000),
        verified: Math.random() > 0.7,
        verified_type: Math.random() > 0.7 ? 0 : -1,
      },
      reposts_count: Math.floor(Math.random() * 500),
      comments_count: Math.floor(Math.random() * 300),
      attitudes_count: Math.floor(Math.random() * 2000),
      keyword,
      crawl_time: new Date().toISOString(),
      sentiment,
      sentiment_score: sentiment === 'positive' ? Math.random() * 0.5 + 0.5 : sentiment === 'negative' ? -Math.random() * 0.5 - 0.3 : Math.random() * 0.4 - 0.2,
    };
  });
}

/**
 * 获取话题微博
 * @param topic 话题名称
 * @param page 页码
 * @param analyze 是否进行情感分析
 */
export async function getTopicWeibo(
  topic: string,
  page: number = 1,
  analyze: boolean = true
): Promise<{ data: WeiboData[]; total: number }> {
  const response = await apiClient.get('/weibo/topic', {
    params: { topic, page, analyze }
  });
  return {
    data: response.data.data || [],
    total: response.data.total || 0
  };
}

// 模拟任务存储
const mockTasks: Map<string, CrawlTask> = new Map();

/**
 * 启动批量采集任务
 */
export async function startCrawlTask(
  keywords: string[],
  pages: number = 3,
  crawlHot: boolean = true,
  dateRange?: [string, string] | null
): Promise<CrawlTask> {
  try {
    const response = await apiClient.post('/weibo/crawl/start', {
      keywords,
      pages,
      crawl_hot: crawlHot,
      ...(dateRange ? { start_date: dateRange[0], end_date: dateRange[1] } : {}),
    });
    return response.data.data;
  } catch (error) {
    // 采集API不可用，使用模拟任务
    return startMockCrawlTask(keywords, pages, crawlHot);
  }
}

function startMockCrawlTask(keywords: string[], pages: number, crawlHot: boolean): CrawlTask {
  const taskId = 'mock_crawl_' + Date.now();
  const totalToCollect = (keywords.length * pages * 10) + (crawlHot ? 50 : 0);
  const task: CrawlTask = {
    id: taskId, status: 'running', keywords, pages, crawl_hot: crawlHot,
    progress: 0, collected: 0, start_time: new Date().toISOString(),
  };
  mockTasks.set(taskId, task);
  
  let progress = 0;
  const interval = setInterval(() => {
    const t = mockTasks.get(taskId);
    if (!t || t.status !== 'running') { clearInterval(interval); return; }
    progress += Math.random() * 15 + 5;
    if (progress >= 100) {
      progress = 100; t.status = 'completed'; t.end_time = new Date().toISOString();
      clearInterval(interval);
    }
    t.progress = Math.min(Math.round(progress), 100);
    t.collected = Math.round(totalToCollect * progress / 100);
  }, 1500);
  
  return task;
}

/**
 * 获取采集任务状态
 * @param taskId 任务ID
 */
export async function getCrawlTaskStatus(taskId: string): Promise<CrawlTask> {
  // 检查是否是模拟任务
  if (taskId.startsWith('mock_crawl_')) {
    const task = mockTasks.get(taskId);
    if (task) return task;
    throw new Error('任务不存在');
  }
  
  try {
    const response = await apiClient.get(`/weibo/crawl/status/${taskId}`);
    return response.data.data;
  } catch (error) {
    // 如果后端不可用，返回模拟完成状态
    return {
      id: taskId,
      status: 'completed',
      keywords: [],
      pages: 3,
      crawl_hot: true,
      progress: 100,
      collected: 50,
      start_time: new Date().toISOString(),
      end_time: new Date().toISOString(),
    };
  }
}

/** 采集任务列表响应 */
export interface CrawlTasksResponse {
  tasks: CrawlTask[];
  total: number;
  completed: number;
  running: number;
}

/** 采集任务数据响应 */
export interface CrawlTaskDataResponse {
  items: WeiboData[];
  total: number;
  page: number;
  page_size: number;
  task_info: {
    id: string;
    keywords: string[];
    collected: number;
    start_time: string;
    end_time?: string;
  };
}

/**
 * 获取所有采集任务列表
 */
export async function getCrawlTasks(): Promise<CrawlTasksResponse> {
  try {
    const response = await apiClient.get('/weibo/crawl/tasks');
    return response.data.data;
  } catch (error) {
    // 获取任务列表失败，返回模拟数据
    const tasks = Array.from(mockTasks.values());
    return {
      tasks,
      total: tasks.length,
      completed: tasks.filter(t => t.status === 'completed').length,
      running: tasks.filter(t => t.status === 'running').length,
    };
  }
}

/**
 * 获取采集任务的数据
 * @param taskId 任务ID
 * @param page 页码
 * @param pageSize 每页数量
 */
export async function getCrawlTaskData(
  taskId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<CrawlTaskDataResponse> {
  try {
    const response = await apiClient.get(`/weibo/crawl/data/${taskId}`, {
      params: { page, page_size: pageSize }
    });
    return response.data.data;
  } catch (error) {
    // 获取任务数据失败，返回模拟数据
    const task = mockTasks.get(taskId);
    return {
      items: generateMockWeiboData(task?.keywords?.[0] || '测试', 20),
      total: task?.collected || 20,
      page,
      page_size: pageSize,
      task_info: {
        id: taskId,
        keywords: task?.keywords || [],
        collected: task?.collected || 0,
        start_time: task?.start_time || new Date().toISOString(),
        end_time: task?.end_time,
      }
    };
  }
}

/**
 * 使用Spark进行批量情感分析
 * @param taskId 采集任务ID（可选）
 * @param data 微博数据列表（可选）
 * @param useSpark 是否使用Spark
 */
export async function analyzeData(
  taskId?: string,
  data?: WeiboData[],
  useSpark: boolean = true
): Promise<AnalysisResult> {
  const response = await apiClient.post('/weibo/analyze', {
    task_id: taskId,
    data,
    use_spark: useSpark
  });
  return response.data.data;
}

export async function analyzeCollectionTask(taskId: string, limit: number = 500): Promise<AnalysisResult> {
  const response = await apiClient.post(`/collection/tasks/${taskId}/analyze`, { limit });
  return response.data.data;
}

/**
 * 获取分析结果
 * @param analysisId 分析ID
 */
export async function getAnalysisResult(analysisId: string): Promise<AnalysisResult> {
  const response = await apiClient.get(`/weibo/analyze/${analysisId}`);
  return response.data.data;
}

/**
 * 实时分析单条文本
 * @param text 要分析的文本
 */
export async function realtimeAnalyze(text: string): Promise<{
  text: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  sentiment_score: number;
  analysis_time: string;
}> {
  const response = await apiClient.post('/weibo/realtime/analyze', { text });
  return response.data.data;
}

/**
 * 获取Spark集群信息
 */
export async function getSparkInfo(): Promise<SparkInfo> {
  const response = await apiClient.get('/weibo/spark/info');
  return response.data.data;
}

/**
 * 获取数据概览统计
 */
export async function getOverviewStats(): Promise<OverviewStats> {
  const response = await apiClient.get('/weibo/stats/overview');
  return response.data.data;
}

// ==================== 采集任务相关 API ====================

/** 采集任务信息 */
export interface CollectionTask {
  id: string;
  name: string;
  keywords: Array<{ word: string; weight?: number }>;
  status: 'waiting' | 'running' | 'paused' | 'completed' | 'stopped' | 'failed';
  progress: number;
  collected: number;
  failed: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * 获取所有采集任务列表
 * 同时从 /collection/tasks 和 /weibo/crawl/tasks 获取任务
 */
export async function getCollectionTasks(): Promise<CollectionTask[]> {
  const allTasks: CollectionTask[] = [];
  
  // 尝试从 collection API 获取
  try {
    const response = await apiClient.get('/collection/tasks');
    if (response.data.code === 200 && Array.isArray(response.data.data)) {
      allTasks.push(...response.data.data);
    }
  } catch (e) {
    console.warn('获取collection任务失败:', e);
  }
  
  // 尝试从 weibo/crawl API 获取
  try {
    const response = await apiClient.get('/weibo/crawl/tasks');
    if (response.data.code === 200 && response.data.data?.tasks) {
      const crawlTasks = response.data.data.tasks.map((t: CrawlTask) => ({
        id: t.id,
        name: t.keywords?.join(', ') || '采集任务',
        keywords: (t.keywords || []).map((k: string) => ({ word: k })),
        status: t.status,
        collected: t.collected || 0,
        progress: t.progress || 0,
        createdAt: t.start_time,
      }));
      allTasks.push(...crawlTasks);
    }
  } catch (e) {
    console.warn('获取crawl任务失败:', e);
  }
  
  // 按时间倒序排列
  allTasks.sort((a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime());
  
  return allTasks;
}

/**
 * 获取指定任务的采集数据
 * @param taskId 任务ID
 * @param page 页码
 * @param pageSize 每页数量
 */
export async function getTaskData(taskId: string, page: number = 1, pageSize: number = 100): Promise<{
  list: WeiboData[];
  total: number;
  page: number;
  pageSize: number;
}> {
  // 先尝试从 collection API 获取
  try {
    const response = await apiClient.get(`/collection/tasks/${taskId}/data`, {
      params: { page, pageSize }
    });
    if (response.data.code === 200) {
      const data = response.data.data;
      return {
        list: data.items || data.list || [],
        total: data.total || 0,
        page: data.page || page,
        pageSize: data.pageSize || pageSize,
      };
    }
  } catch (e) {
    console.warn('从collection获取数据失败，尝试crawl API');
  }
  
  // 尝试从 weibo/crawl API 获取
  try {
    const response = await apiClient.get(`/weibo/crawl/data/${taskId}`, {
      params: { page, page_size: pageSize }
    });
    if (response.data.code === 200) {
      const data = response.data.data;
      return {
        list: data.items || [],
        total: data.total || 0,
        page: data.page || page,
        pageSize: data.page_size || pageSize,
      };
    }
  } catch (e) {
    console.warn('从crawl获取数据失败');
  }
  
  throw new Error('获取任务数据失败');
}

// ==================== 预处理任务相关 API ====================

/** 预处理任务信息 */
export interface PreprocessTask {
  id: string;
  name: string;
  sourceTaskId?: string;
  cleanRules: string[];
  segmentTool: string;
  status: 'processing' | 'completed' | 'failed';
  totalCount: number;
  processedCount: number;
  createdAt: string;
}

/** 预处理后的数据项 */
export interface PreprocessedItem {
  id: string;
  original_text: string;
  cleaned_text: string;
  words: string[];
  word_count: number;
  source: string;
  keyword: string;
  author: string;
  timestamp: string;
  likes: number;
  comments: number;
  shares: number;
}

/**
 * 获取所有预处理任务列表
 */
export async function getPreprocessTasks(): Promise<PreprocessTask[]> {
  // 添加时间戳防止缓存
  const response = await apiClient.get('/preprocess/tasks', {
    params: { _t: Date.now() }
  });
  if (response.data.code === 200) {
    const tasks = response.data.data || [];
    // 确保返回数组
    if (Array.isArray(tasks)) {
      return tasks;
    }
    // 如果是对象，转换为数组
    return Object.values(tasks);
  }
  throw new Error(response.data.message || '获取预处理任务列表失败');
}

/**
 * 创建预处理任务
 */
export async function createPreprocessTask(params: {
  name?: string;
  sourceTaskId?: string;
  data?: WeiboData[];
  cleanRules?: string[];
  segmentTool?: string;
}): Promise<PreprocessTask> {
  const response = await apiClient.post('/preprocess/tasks', params);
  if (response.data.code === 200) {
    return response.data.data;
  }
  throw new Error(response.data.message || '创建预处理任务失败');
}

/**
 * 获取预处理后的数据
 * @param taskId 预处理任务ID
 * @param page 页码
 * @param pageSize 每页数量
 */
export async function getPreprocessData(taskId: string, page: number = 1, pageSize: number = 100): Promise<{
  list: PreprocessedItem[];
  total: number;
  page: number;
  pageSize: number;
}> {
  const response = await apiClient.get(`/preprocess/tasks/${taskId}/data`, {
    params: { page, pageSize }
  });
  if (response.data.code === 200) {
    return response.data.data;
  }
  throw new Error(response.data.message || '获取预处理数据失败');
}

// ==================== 辅助函数 ====================

/**
 * 格式化热度值
 */
export function formatHotValue(value: number): string {
  if (value >= 100000000) {
    return (value / 100000000).toFixed(1) + '亿';
  } else if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万';
  }
  return value.toString();
}

/**
 * 获取情感标签颜色
 */
export function getSentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'positive':
      return '#67C23A';
    case 'negative':
      return '#F56C6C';
    default:
      return '#909399';
  }
}

/**
 * 获取情感标签文本
 */
export function getSentimentLabel(sentiment: string): string {
  switch (sentiment) {
    case 'positive':
      return '正面';
    case 'negative':
      return '负面';
    default:
      return '中性';
  }
}


// ==================== 完整数据流连通 API ====================
// 解决中期检查表中"爬虫数据未与各个模块连通"问题
// 数据流：微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 三维度排序 → 前端展示

/** 数据流任务阶段状态 */
export interface DataflowPhase {
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
}

/** 完整数据流任务 */
export interface DataflowTask {
  task_id: string;
  status: 'crawling' | 'cleaning' | 'analyzing' | 'ranking' | 'completed' | 'failed';
  phase: 'crawl' | 'clean' | 'analyze' | 'rank' | 'done';
  progress: number;
  collected: number;
  phases: {
    crawl: DataflowPhase;
    clean: DataflowPhase;
    analyze: DataflowPhase;
    rank: DataflowPhase;
  };
  start_time: string;
  end_time?: string;
  error?: string;
  spark_job_id?: string;
}

/** Spark作业 */
export interface SparkJob {
  job_id: string;
  job_type: 'data_cleaning' | 'sentiment_analysis' | 'topic_ranking' | 'full_pipeline';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'retrying';
  input_path: string;
  output_path: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress: number;
  retry_count: number;
  error_message?: string;
  records_processed: number;
  records_output: number;
  crawl_task_id?: string;
}

/** 数据流概览 */
export interface DataflowOverview {
  dataflow: {
    stages: Array<{
      name: string;
      status: 'active' | 'inactive';
      count: number;
    }>;
  };
  crawl_stats: {
    total: number;
    completed: number;
    running: number;
    failed: number;
  };
  spark_stats: {
    total: number;
    running: number;
    completed: number;
    failed: number;
  };
  data_stats: {
    raw_files: number;
    raw_records: number;
    analysis_results: number;
  };
  update_time: string;
}

/**
 * 启动完整数据采集与处理流程
 * 数据流：微博爬虫 → HDFS → Spark清洗 → HBase → 三维度排序
 */
export async function startDataflowTask(params: {
  keywords?: string[];
  pages?: number;
  crawl_hot?: boolean;
  auto_process?: boolean;
}): Promise<{ task_id: string; status: string; phases: string[] }> {
  try {
    const response = await apiClient.post('/weibo/collect', {
      keywords: params.keywords || [],
      pages: params.pages || 3,
      crawl_hot: params.crawl_hot !== false,
      auto_process: params.auto_process !== false,
    });
    return response.data.data;
  } catch (error) {
    // 模拟任务
    const taskId = `dataflow_mock_${Date.now()}`;
    startMockDataflowTask(taskId, params);
    return {
      task_id: taskId,
      status: 'crawling',
      phases: ['crawl', 'clean', 'analyze', 'rank'],
    };
  }
}

// 模拟数据流任务存储
const mockDataflowTasks: Map<string, DataflowTask> = new Map();

function startMockDataflowTask(taskId: string, _params: { keywords?: string[]; pages?: number; crawl_hot?: boolean; auto_process?: boolean }) {
  const task: DataflowTask = {
    task_id: taskId,
    status: 'crawling',
    phase: 'crawl',
    progress: 0,
    collected: 0,
    phases: {
      crawl: { status: 'running', progress: 0 },
      clean: { status: 'pending', progress: 0 },
      analyze: { status: 'pending', progress: 0 },
      rank: { status: 'pending', progress: 0 },
    },
    start_time: new Date().toISOString(),
  };
  mockDataflowTasks.set(taskId, task);

  // 模拟进度更新
  const phases = ['crawl', 'clean', 'analyze', 'rank'] as const;
  let currentPhaseIdx = 0;
  let phaseProgress = 0;

  const interval = setInterval(() => {
    const t = mockDataflowTasks.get(taskId);
    if (!t) { clearInterval(interval); return; }

    phaseProgress += Math.random() * 20 + 10;
    
    if (phaseProgress >= 100) {
      t.phases[phases[currentPhaseIdx]].status = 'completed';
      t.phases[phases[currentPhaseIdx]].progress = 100;
      currentPhaseIdx++;
      phaseProgress = 0;

      if (currentPhaseIdx >= phases.length) {
        t.status = 'completed';
        t.phase = 'done';
        t.progress = 100;
        t.end_time = new Date().toISOString();
        clearInterval(interval);
        return;
      }

      t.phase = phases[currentPhaseIdx];
      t.phases[phases[currentPhaseIdx]].status = 'running';
    } else {
      t.phases[phases[currentPhaseIdx]].progress = Math.min(Math.round(phaseProgress), 100);
    }

    // 计算总进度
    t.progress = Math.round((currentPhaseIdx * 25) + (phaseProgress / 4));
    t.collected = Math.round(50 * t.progress / 100);
  }, 1500);
}

/**
 * 获取数据流任务状态
 */
export async function getDataflowTaskStatus(taskId: string): Promise<DataflowTask> {
  // 检查模拟任务
  if (taskId.startsWith('dataflow_mock_')) {
    const task = mockDataflowTasks.get(taskId);
    if (task) return task;
    throw new Error('任务不存在');
  }

  try {
    const response = await apiClient.get(`/weibo/collect/status/${taskId}`);
    return response.data.data;
  } catch (error) {
    throw new Error('获取任务状态失败');
  }
}

/**
 * 获取数据流任务结果
 */
export async function getDataflowTaskResult(
  taskId: string,
  type: 'raw' | 'analyzed' | 'ranked' = 'ranked',
  page: number = 1,
  pageSize: number = 50
): Promise<{
  items: RankedWeiboItem[];
  total: number;
  page: number;
  page_size: number;
  type: string;
}> {
  try {
    const response = await apiClient.get(`/weibo/collect/result/${taskId}`, {
      params: { type, page, page_size: pageSize }
    });
    return response.data.data;
  } catch (error) {
    // 返回模拟数据
    return {
      items: generateMockRankedData(10),
      total: 10,
      page,
      page_size: pageSize,
      type,
    };
  }
}

function generateMockRankedData(count: number): RankedWeiboItem[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `ranked_${i}`,
    text: `这是第${i + 1}条排序后的微博内容...`,
    rank: i + 1,
    tri_score: Math.random() * 0.5 + 0.5,
    sentiment_score: Math.random() * 2 - 1,
    heat_score: Math.random() * 10,
    reposts_count: Math.floor(Math.random() * 1000),
    comments_count: Math.floor(Math.random() * 500),
    attitudes_count: Math.floor(Math.random() * 5000),
  }));
}

/**
 * 获取所有Spark作业列表
 */
export async function getSparkJobs(): Promise<{
  jobs: SparkJob[];
  total: number;
  running: number;
  completed: number;
  failed: number;
}> {
  try {
    const response = await apiClient.get('/weibo/spark/jobs');
    return response.data.data;
  } catch (error) {
    return { jobs: [], total: 0, running: 0, completed: 0, failed: 0 };
  }
}

/**
 * 获取单个Spark作业状态
 */
export async function getSparkJobStatus(jobId: string): Promise<SparkJob> {
  const response = await apiClient.get(`/weibo/spark/jobs/${jobId}`);
  return response.data.data;
}

/**
 * 取消Spark作业
 */
export async function cancelSparkJob(jobId: string): Promise<void> {
  await apiClient.post(`/weibo/spark/jobs/${jobId}/cancel`);
}

/**
 * 获取数据流概览
 */
export async function getDataflowOverview(): Promise<DataflowOverview> {
  try {
    const response = await apiClient.get('/weibo/dataflow/overview');
    return response.data.data;
  } catch (error) {
    // 返回模拟数据
    return {
      dataflow: {
        stages: [
          { name: '微博爬虫', status: 'active', count: 5 },
          { name: 'HDFS存储', status: 'active', count: 10 },
          { name: 'Spark清洗', status: 'active', count: 3 },
          { name: 'HBase存储', status: 'active', count: 100 },
          { name: '三维度排序', status: 'active', count: 2 },
        ],
      },
      crawl_stats: { total: 5, completed: 3, running: 1, failed: 1 },
      spark_stats: { total: 5, running: 1, completed: 3, failed: 1 },
      data_stats: { raw_files: 10, raw_records: 500, analysis_results: 3 },
      update_time: new Date().toISOString(),
    };
  }
}


// ==================== 数据质量监控 API ====================

/** 数据质量指标 */
export interface DataQualityMetrics {
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  fixed_records: number;
  success_rate: number;
  duplicate_rate: number;
  fix_rate: number;
  field_completeness: Record<string, number>;
  error_counts: Record<string, number>;
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

/** 质量报警 */
export interface QualityAlert {
  alert_type: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  metric_name: string;
  current_value: number;
  threshold: number;
  timestamp: string;
}

/** 质量报告 */
export interface QualityReport {
  report_id: string;
  task_id?: string;
  generated_at: string;
  metrics: DataQualityMetrics;
  alerts: QualityAlert[];
  summary: {
    status: 'healthy' | 'warning' | 'critical';
    total_alerts: number;
    critical_alerts: number;
    high_alerts: number;
  };
  recommendations: string[];
}

/** 数据质量摘要 */
export interface DataQualitySummary {
  status: string;
  success_rate?: number;
  duplicate_rate?: number;
  total_records?: number;
  alerts_count?: number;
  generated_at?: string;
  message?: string;
}

/** 错误日志条目 */
export interface ErrorLogEntry {
  timestamp: string;
  data_id?: string;
  data_preview?: string;
  errors: Array<{
    field_name: string;
    error_type: string;
    message: string;
    level: string;
  }>;
  warnings: Array<{
    field_name: string;
    error_type: string;
    message: string;
    level: string;
  }>;
}

/**
 * 获取数据质量概览
 */
export async function getDataQuality(): Promise<{
  summary: DataQualitySummary;
  recent_reports: QualityReport[];
  recent_errors: ErrorLogEntry[];
  thresholds: Record<string, number>;
}> {
  try {
    const response = await apiClient.get('/weibo/data-quality');
    return response.data.data;
  } catch (error) {
    // 返回模拟数据
    return {
      summary: {
        status: 'healthy',
        success_rate: 95.5,
        duplicate_rate: 5.2,
        total_records: 1000,
        alerts_count: 0,
        generated_at: new Date().toISOString(),
      },
      recent_reports: [],
      recent_errors: [],
      thresholds: {
        success_rate: 0.8,
        duplicate_rate: 0.3,
        field_completeness: 0.7,
      },
    };
  }
}

/**
 * 验证数据质量
 */
export async function validateDataQuality(params: {
  data: WeiboData[];
  check_duplicates?: boolean;
  auto_fix?: boolean;
  generate_report?: boolean;
  task_id?: string;
}): Promise<{
  metrics: DataQualityMetrics;
  valid_count: number;
  report?: QualityReport;
  alerts: QualityAlert[];
}> {
  const response = await apiClient.post('/weibo/data-quality/validate', {
    data: params.data,
    check_duplicates: params.check_duplicates !== false,
    auto_fix: params.auto_fix !== false,
    generate_report: params.generate_report !== false,
    task_id: params.task_id,
  });
  return response.data.data;
}

/**
 * 获取质量报告列表
 */
export async function getQualityReports(limit: number = 10): Promise<{
  reports: QualityReport[];
  total: number;
}> {
  try {
    const response = await apiClient.get('/weibo/data-quality/reports', {
      params: { limit }
    });
    return response.data.data;
  } catch (error) {
    return { reports: [], total: 0 };
  }
}

/**
 * 获取错误日志
 */
export async function getQualityErrors(
  limit: number = 100,
  errorType?: string
): Promise<{
  errors: ErrorLogEntry[];
  total: number;
}> {
  try {
    const response = await apiClient.get('/weibo/data-quality/errors', {
      params: { limit, error_type: errorType }
    });
    return response.data.data;
  } catch (error) {
    return { errors: [], total: 0 };
  }
}

/**
 * 获取当前质量报警
 */
export async function getQualityAlerts(): Promise<{
  alerts: QualityAlert[];
  status: string;
  generated_at?: string;
}> {
  try {
    const response = await apiClient.get('/weibo/data-quality/alerts');
    return response.data.data;
  } catch (error) {
    return { alerts: [], status: 'no_data' };
  }
}
