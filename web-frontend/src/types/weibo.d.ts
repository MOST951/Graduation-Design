/**
 * 微博数据类型定义
 */

/** 热搜项 */
export interface HotSearchItem {
  rank: number;
  title: string;
  hotValue: number;
  label: string;
  url: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  sentimentScore?: number;
  isNew?: boolean;
  isHot?: boolean;
  trend?: 'up' | 'down' | 'stable';
  crawlTime?: string;
}

/** 采集任务 */
export interface CollectionTask {
  task_id: string;
  keywords: string;
  max_posts: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  collected_count: number;
  start_time: string;
  end_time?: string;
  error_message?: string;
}

/** 数据流任务 */
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
}

/** 数据流阶段 */
export interface DataflowPhase {
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
}

/** 三维度排序话题 */
export interface RankedTopic {
  rank: number;
  name: string;
  keywords: string[];
  composite_score: number;
  sentiment_avg: number;
  popularity_score: number;
  post_count: number;
  trend: 'up' | 'down' | 'stable';
}

/** 三维度排序配置 */
export interface TriDimensionConfig {
  sentiment_weight: number;
  popularity_weight: number;
  time_decay_hours: number;
}

/** API响应通用格式 */
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

/** 连通性状态 */
export interface ConnectivityStatus {
  hotSearch: boolean;
  topics: boolean;
  sentiment: boolean;
  collection: boolean;
  lastCheck: Date | null;
}
