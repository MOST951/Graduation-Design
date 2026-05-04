/**
 * API  TypeScript 
 */

// ====================  ====================
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
  success?: boolean;
  timestamp?: string;
}

// ====================  ====================
export interface LoginRequest {
  username: string;
  password: string;
  remember?: boolean;
}

export interface LoginResponse {
  token: string;
  refreshToken?: string;
  user: UserInfo;
  expiresIn?: number;
}

export interface UserInfo {
  id: number;
  username: string;
  email?: string;
  role: 'admin' | 'user';
  avatar?: string;
  createdAt: string;
  lastLoginAt?: string;
  isActive: boolean;
}

export interface RegisterRequest {
  username: string;
  password: string;
  confirmPassword: string;
  email?: string;
  captcha?: string;
}

// ====================  ====================
export type SentimentType = 'positive' | 'neutral' | 'negative';
export type FineGrainedEmotion = 'joy' | 'trust' | 'anticipation' | 'surprise' | 'sadness' | 'fear' | 'disgust' | 'anger';
export type AnalysisGranularity = 'binary' | 'ternary' | 'fine';

export interface SentimentAnalysisRequest {
  text?: string;
  texts?: string[];
  dataSource: 'all' | 'task' | 'custom';
  taskIds?: number[];
  dateRange?: [string, string];
  keywords?: string[];
  model: string;
  granularity: AnalysisGranularity;
  confidenceThreshold: number;
  batchSize?: number;
  useGpu?: boolean;
}

export interface SentimentResult {
  id: number;
  content: string;
  sentiment: SentimentType;
  sentimentLabel: string;
  confidence: number;
  score: number;
  intensity: number;
  emotions?: Record<FineGrainedEmotion, number>;
  keywords: string[];
  source: string;
  time: string;
  taskId?: number;
}

export interface SentimentAnalysisResponse {
  results: SentimentResult[];
  stats: {
    totalCount: number;
    positiveCount: number;
    neutralCount: number;
    negativeCount: number;
    averageConfidence: number;
    averageScore: number;
  };
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
  };
}

// ====================  ====================
export type TaskStatus = 'waiting' | 'running' | 'completed' | 'failed' | 'paused';
export type Platform = 'weibo' | 'wechat' | 'douyin' | 'zhihu' | 'xiaohongshu';

export interface Keyword {
  word: string;
  weight: number;
}

export interface TaskConfig {
  name: string;
  keywords: Keyword[];
  platforms: Platform[];
  weiboOptions?: string[];
  dateRange?: [string, string] | null;
  dataLimit: number;
  requestInterval: number;
  useProxy: boolean;
  proxyList?: string;
  rotateUserAgent: boolean;
  downloadMedia: boolean;
  enableSchedule: boolean;
  cronExpression?: string;
  maxExecutions?: number;
}

export interface CollectionTask {
  id: number;
  name: string;
  keywords: string[];
  status: TaskStatus;
  progress: number;
  collectedCount: number;
  failedCount: number;
  config: TaskConfig;
  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
  logs?: TaskLog[];
}

export interface TaskLog {
  id: number;
  taskId: number;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface CreateTaskRequest {
  name: string;
  keywords: string[];
  platforms: Platform[];
  config: Partial<TaskConfig>;
}

// ====================  ====================
export interface TriDimensionScore {
  id: number;
  content: string;
  sentimentScore: number;
  popularityScore: number;
  timelinessScore: number;
  compositeScore: number;
  rank: number;
  metadata: {
    reposts: number;
    comments: number;
    likes: number;
    publishTime: string;
    source: string;
  };
}

export interface TriDimensionConfig {
  weights: {
    sentiment: number;
    popularity: number;
    timeliness: number;
  };
  timeDecay: {
    halfLife: number;
    unit: 'hours' | 'days';
  };
  filters: {
    minScore?: number;
    dateRange?: [string, string];
    keywords?: string[];
  };
}

export interface TriDimensionResponse {
  results: TriDimensionScore[];
  config: TriDimensionConfig;
  stats: {
    totalItems: number;
    averageScore: number;
    topScore: number;
    scoreDistribution: number[];
  };
}

// ====================  ====================
export interface RealtimeStream {
  id: number;
  content: string;
  sentiment: SentimentType;
  confidence: number;
  timestamp: string;
  source: string;
  keywords: string[];
  metrics: {
    reposts?: number;
    comments?: number;
    likes?: number;
  };
}

export interface RealtimeStats {
  totalMessages: number;
  sentimentDistribution: Record<SentimentType, number>;
  averageConfidence: number;
  messagesPerMinute: number;
  topKeywords: Array<{
    keyword: string;
    count: number;
    trend: 'up' | 'down' | 'stable';
  }>;
}

export interface RealtimeSubscription {
  keywords: string[];
  threshold: {
    negativeRatio: number;
    alertCount: number;
  };
  filters: {
    platforms?: Platform[];
    minConfidence?: number;
  };
}

// ====================  ====================
export interface PipelineStep {
  id: string;
  name: string;
  status: 'waiting' | 'running' | 'success' | 'failed' | 'paused';
  progress: number;
  processedCount: number;
  totalCount: number;
  startTime?: string;
  endTime?: string;
  duration?: number;
  errorMessage?: string;
  logs?: string[];
}

export interface PipelineConfig {
  name: string;
  description?: string;
  steps: PipelineStep[];
  parameters: {
    batchSize: number;
    timeout: number;
    retryAttempts: number;
    enableNotifications: boolean;
  };
  triggers: {
    manual?: boolean;
    scheduled?: boolean;
    cronExpression?: string;
  };
}

export interface PipelineExecution {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  startTime: string;
  endTime?: string;
  duration?: number;
  steps: PipelineStep[];
  results?: {
    processedItems: number;
    successItems: number;
    failedItems: number;
    outputFiles: string[];
  };
  errorMessage?: string;
}

// ====================  ====================
export interface VisualizationData {
  sentimentDistribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  sentimentTrend: Array<{
    time: string;
    positive: number;
    neutral: number;
    negative: number;
  }>;
  wordCloud: Array<{
    text: string;
    value: number;
    category?: string;
  }>;
  hotTopics: Array<{
    keyword: string;
    count: number;
    sentiment: SentimentType;
    trend: number;
  }>;
  propagationPath: Array<{
    source: string;
    target: string;
    weight: number;
    timestamp: string;
  }>;
}

export interface VisualizationConfig {
  chartType: 'line' | 'bar' | 'pie' | 'scatter' | 'heatmap' | 'wordcloud' | 'network';
  timeRange: [string, string];
  filters: {
    keywords?: string[];
    platforms?: Platform[];
    sentimentRange?: [number, number];
  };
  displayOptions: {
    showLegend: boolean;
    showTooltip: boolean;
    animationEnabled: boolean;
    colorScheme: string;
  };
}

// ====================  ====================
export interface SystemConfig {
  spark: {
    masterUrl: string;
    appName: string;
    executorMemory: string;
    driverMemory: string;
    maxResultSize: string;
  };
  database: {
    mysql: {
      host: string;
      port: number;
      database: string;
      username: string;
      password?: string;
    };
    hbase: {
      quorum: string;
      port: number;
      master: string;
    };
  };
  logging: {
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    maxFileSize: string;
    maxFiles: number;
    enableConsole: boolean;
  };
}

export interface SystemStats {
  cpu: {
    usage: number;
    cores: number;
  };
  memory: {
    used: number;
    total: number;
    usage: number;
  };
  disk: {
    used: number;
    total: number;
    usage: number;
  };
  network: {
    bytesIn: number;
    bytesOut: number;
  };
  services: Array<{
    name: string;
    status: 'running' | 'stopped' | 'error';
    uptime?: number;
    memoryUsage?: number;
  }>;
}

// ====================  ====================
export interface DashboardMetrics {
  overview: {
    totalTasks: number;
    activeTasks: number;
    totalData: number;
    todayData: number;
  };
  sentiment: {
    positiveRatio: number;
    negativeRatio: number;
    neutralRatio: number;
    averageConfidence: number;
  };
  realtime: {
    activeStreams: number;
    messagesPerSecond: number;
    alertsCount: number;
  };
  system: {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    uptime: number;
  };
}

// ====================  ====================
export interface LogEntry {
  id: number;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  timestamp: string;
  module: string;
  userId?: number;
  ip?: string;
  userAgent?: string;
  requestId?: string;
  details?: Record<string, unknown>;
}

export interface LogFilter {
  level?: ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR')[];
  module?: string;
  dateRange?: [string, string];
  keyword?: string;
  userId?: number;
  page?: number;
  pageSize?: number;
}

// ====================  ====================
export interface ExportRequest {
  type: 'csv' | 'json' | 'excel' | 'pdf';
  data: {
    source: 'sentiment' | 'collection' | 'tri-dimension' | 'logs';
    filters?: Record<string, unknown>;
    fields?: string[];
  };
  options: {
    includeHeaders?: boolean;
    dateFormat?: string;
    encoding?: string;
  };
}

/** 通用分页响应 */
export interface PageResponse<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** 采集的数据条目 */
export interface CollectedDataItem {
  id: number;
  taskId: number;
  content: string;
  author?: string;
  publishTime?: string;
  platform: Platform;
  url?: string;
  likes?: number;
  comments?: number;
  shares?: number;
  sentiment?: 'positive' | 'neutral' | 'negative';
  sentimentScore?: number;
  collectedAt: string;
  metadata?: Record<string, unknown>;
}

export interface ExportResponse {
  downloadUrl: string;
  filename: string;
  fileSize: number;
  expiresAt: string;
}
