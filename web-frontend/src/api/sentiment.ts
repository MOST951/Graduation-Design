/**
 * 情感分析模块 API
 */
import apiClient from './index';
import type {
  SentimentType,
  FineGrainedEmotion,
  AnalysisGranularity,
  SentimentAnalysisRequest,
  SentimentResult,
  ApiResponse
} from './types';

/** 分析结果统计 */
export interface AnalysisStats {
  totalCount: number;
  positiveCount: number;
  neutralCount: number;
  negativeCount: number;
  positiveRate: number;
  neutralRate: number;
  negativeRate: number;
  avgScore: number;
  avgConfidence: number;
  processTime: number;
}

/** 分析任务 */
export interface AnalysisTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  stats?: AnalysisStats;
  createdAt: string;
  completedAt?: string;
  error?: string;
}

/** 模型信息 */
export interface ModelInfo {
  id: string;
  name: string;
  type: 'bert' | 'lstm' | 'svm' | 'ensemble';
  version: string;
  accuracy: number;
  f1Score: number;
  isDefault: boolean;
  trainedAt: string;
  datasetSize: number;
  description?: string;
}

/** 训练配置 */
export interface TrainConfig {
  datasetId?: string;
  uploadFile?: File;
  trainRatio: number;
  valRatio: number;
  testRatio: number;
  batchSize: number;
  learningRate: number;
  epochs: number;
  earlyStop: boolean;
  patience?: number;
  minDelta?: number;
  useGpu: boolean;
  modelName: string;
}

/** 训练状态 */
export interface TrainingStatus {
  taskId: string;
  status: 'idle' | 'training' | 'paused' | 'completed' | 'failed';
  currentEpoch: number;
  totalEpochs: number;
  currentBatch: number;
  totalBatches: number;
  trainLoss: number;
  valLoss: number;
  trainAccuracy: number;
  valAccuracy: number;
  bestAccuracy: number;
  elapsedTime: number;
  remainingTime: number;
  gpuUsage: number;
  memoryUsage: number;
}

/** 模型评估结果 */
export interface EvaluationResult {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  auc: number;
  confusionMatrix: number[][];
  classificationReport: {
    class: string;
    precision: number;
    recall: number;
    f1: number;
    support: number;
  }[];
  rocCurve: { fpr: number; tpr: number }[];
}

/** 未标注样本 */
export interface UnlabeledSample {
  id: number;
  content: string;
  source: string;
  time: string;
  predictedSentiment?: SentimentType;
  predictedConfidence?: number;
}

/** 标注数据 */
export interface LabeledData {
  id: number;
  content: string;
  sentiment: SentimentType;
  intensity: number;
  labeledBy: string;
  labeledAt: string;
  note?: string;
}

/** 标注提交 */
export interface LabelSubmission {
  sampleId: number;
  sentiment: SentimentType;
  intensity: number;
  note?: string;
}

/** 导出格式 */
export type ExportFormat = 'json' | 'csv' | 'excel' | 'pdf';

/** 报告配置 */
export interface ReportConfig {
  title: string;
  dateRange: [string, string];
  includeCharts: boolean;
  includeSamples: boolean;
  sampleCount?: number;
  format: 'pdf' | 'html' | 'docx';
}

/** 分页响应 */
export interface PageResponse<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

// ==================== 1. 分析功能 API ====================

/**
 * 
 */
export async function analyzeSentiment(data: SentimentAnalysisRequest): Promise<AnalysisTask> {
  const response = await apiClient.post('/sentiment/analyze', data);
  return response.data.data;
}

/**
 * 获取分析任务状态
 */
export async function getAnalysisTaskStatus(taskId: string): Promise<AnalysisTask> {
  const response = await apiClient.get(`/sentiment/tasks/${taskId}`);
  return response.data.data;
}

/**
 * 获取分析结果列表
 */
export async function getSentimentResults(params: {
  taskId?: string;
  page?: number;
  pageSize?: number;
  sentiment?: SentimentType | '';
  confidenceMin?: number;
  confidenceMax?: number;
  keyword?: string;
  sortField?: string;
  sortOrder?: 'asc' | 'desc';
}): Promise<PageResponse<SentimentResult>> {
  const response = await apiClient.get('/sentiment/results', { params });
  return response.data.data;
}

/**
 * 获取单条分析结果详情
 */
export async function getSentimentResultDetail(id: number): Promise<SentimentResult> {
  const response = await apiClient.get(`/sentiment/results/${id}`);
  return response.data.data;
}

/**
 * 获取分析统计信息
 */
export async function getAnalysisStats(params?: {
  taskId?: string;
  dateRange?: [string, string];
}): Promise<AnalysisStats> {
  const response = await apiClient.get('/sentiment/stats', { params });
  return response.data.data;
}

/**
 * 获取实时情感数据
 */
export async function getRealTimeSentiment(): Promise<{
  recentResults: SentimentResult[];
  stats: {
    last1h: AnalysisStats;
    last24h: AnalysisStats;
  };
  trend: { time: string; positive: number; negative: number }[];
}> {
  const response = await apiClient.get('/sentiment/realtime');
  return response.data.data;
}

/**
 * 创建 WebSocket 连接获取实时分析结果
 */
export function connectRealtimeSentiment(
  onMessage: (data: any) => void,
  onError?: (error: Event) => void
): () => void {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  const port = '8081';
  
  const ws = new WebSocket(`${protocol}//${host}:${port}/api/ws/sentiment`);
  
  ws.onopen = () => {
    console.log('Sentiment WebSocket connected');
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.warn('WebSocket connection unavailable');
    onError?.(error);
  };
  
  return () => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };
}

// ==================== 2. 模型管理 API ====================

/**
 * 获取可用模型列表
 */
export async function getModels(): Promise<ModelInfo[]> {
  const response = await apiClient.get('/sentiment/models');
  return response.data.data;
}

/**
 * 获取模型详情
 */
export async function getModelDetail(id: string): Promise<ModelInfo> {
  const response = await apiClient.get(`/sentiment/models/${id}`);
  return response.data.data;
}

/**
 * 训练新模型
 */
export async function trainModel(config: TrainConfig): Promise<{ taskId: string }> {
  const formData = new FormData();
  
  if (config.uploadFile) {
    formData.append('file', config.uploadFile);
  }
  
  // 添加其他配置参数
  Object.entries(config).forEach(([key, value]) => {
    if (key !== 'uploadFile' && value !== undefined) {
      formData.append(key, String(value));
    }
  });
  
  const response = await apiClient.post('/sentiment/models/train', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data.data;
}

/**
 * 获取训练状态
 */
export async function getTrainingStatus(taskId: string): Promise<TrainingStatus> {
  const response = await apiClient.get(`/sentiment/models/train/${taskId}/status`);
  return response.data.data;
}

/**
 * 暂停训练
 */
export async function pauseTraining(taskId: string): Promise<void> {
  await apiClient.post(`/sentiment/models/train/${taskId}/pause`);
}

/**
 * 恢复训练
 */
export async function resumeTraining(taskId: string): Promise<void> {
  await apiClient.post(`/sentiment/models/train/${taskId}/resume`);
}

/**
 * 停止训练
 */
export async function stopTraining(taskId: string): Promise<void> {
  await apiClient.post(`/sentiment/models/train/${taskId}/stop`);
}

/**
 * 评估模型性能
 */
export async function evaluateModel(id: string, testDatasetId?: string): Promise<EvaluationResult> {
  const response = await apiClient.post(`/sentiment/models/${id}/evaluate`, { testDatasetId });
  return response.data.data;
}

/**
 * 删除模型
 */
export async function deleteModel(id: string): Promise<void> {
  await apiClient.delete(`/sentiment/models/${id}`);
}

/**
 * 设为默认模型
 */
export async function setDefaultModel(id: string): Promise<void> {
  await apiClient.post(`/sentiment/models/${id}/set-default`);
}

/**
 * 下载模型
 */
export async function downloadModel(id: string): Promise<Blob> {
  const response = await apiClient.get(`/sentiment/models/${id}/download`, {
    responseType: 'blob',
  });
  return response.data;
}

// ==================== 3. 数据标注 API ====================

/**
 * 获取未标注样本
 */
export async function getUnlabeledSamples(count: number = 20): Promise<UnlabeledSample[]> {
  const response = await apiClient.get('/sentiment/labeling/unlabeled', { params: { count } });
  return response.data.data;
}

/**
 * 提交单条标注
 */
export async function submitLabel(data: LabelSubmission): Promise<void> {
  await apiClient.post('/sentiment/labeling/submit', data);
}

/**
 * 批量提交标注
 */
export async function submitLabels(data: LabelSubmission[]): Promise<{ success: number; failed: number }> {
  const response = await apiClient.post('/sentiment/labeling/batch-submit', { labels: data });
  return response.data.data;
}

/**
 * 跳过样本
 */
export async function skipSample(sampleId: number): Promise<void> {
  await apiClient.post(`/sentiment/labeling/skip/${sampleId}`);
}

/**
 * 获取已标注数据
 */
export async function getLabeledData(params?: {
  page?: number;
  pageSize?: number;
  sentiment?: SentimentType | '';
  labeledBy?: string;
  startDate?: string;
  endDate?: string;
}): Promise<PageResponse<LabeledData>> {
  const response = await apiClient.get('/sentiment/labeling/labeled', { params });
  return response.data.data;
}

/**
 * 获取标注统计
 */
export async function getLabelingStats(): Promise<{
  totalLabeled: number;
  totalUnlabeled: number;
  labeledToday: number;
  distribution: { sentiment: string; count: number }[];
  recentActivity: { date: string; count: number }[];
}> {
  const response = await apiClient.get('/sentiment/labeling/stats');
  return response.data.data;
}

/**
 * 导出标注数据
 */
export async function exportLabeledData(format: 'json' | 'csv'): Promise<Blob> {
  const response = await apiClient.get('/sentiment/labeling/export', {
    params: { format },
    responseType: 'blob',
  });
  return response.data;
}

/**
 * 导入标注数据
 */
export async function importLabeledData(file: File): Promise<{ imported: number; skipped: number }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/sentiment/labeling/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data.data;
}

// ==================== 4. 结果导出 API ====================

/**
 * 导出分析结果
 */
export async function exportResults(
  format: ExportFormat,
  params?: {
    taskId?: string;
    sentiment?: SentimentType | '';
    dateRange?: [string, string];
    fields?: string[];
  }
): Promise<Blob> {
  const response = await apiClient.post('/sentiment/export', { format, ...params }, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * 生成分析报告
 */
export async function generateReport(config: ReportConfig): Promise<Blob> {
  const response = await apiClient.post('/sentiment/report', config, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * 获取报告模板列表
 */
export async function getReportTemplates(): Promise<{
  id: string;
  name: string;
  description: string;
  preview: string;
}[]> {
  const response = await apiClient.get('/sentiment/report/templates');
  return response.data.data;
}

/**
 * 下载文件辅助函数
 */
export function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default {
  // 分析功能
  analyzeSentiment,
  getAnalysisTaskStatus,
  getSentimentResults,
  getSentimentResultDetail,
  getAnalysisStats,
  getRealTimeSentiment,
  connectRealtimeSentiment,
  // 模型管理
  getModels,
  getModelDetail,
  trainModel,
  getTrainingStatus,
  pauseTraining,
  resumeTraining,
  stopTraining,
  evaluateModel,
  deleteModel,
  setDefaultModel,
  downloadModel,
  // 数据标注
  getUnlabeledSamples,
  submitLabel,
  submitLabels,
  skipSample,
  getLabeledData,
  getLabelingStats,
  exportLabeledData,
  importLabeledData,
  // 结果导出
  exportResults,
  generateReport,
  getReportTemplates,
  downloadFile,
};
