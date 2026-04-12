/**
 * 数据采集模块 API
 */
import apiClient from './index';
import type {
  TaskStatus,
  Platform,
  Keyword,
  TaskConfig,
  CollectionTask,
  TaskLog,
  ApiResponse,
  PageResponse,
  CreateTaskRequest,
  CollectedDataItem,
} from './types';

/** WebSocket 实时消息 */
export interface RealtimeMessage {
  type: 'progress' | 'data' | 'log' | 'error' | 'complete';
  taskId?: number;
  progress?: number;
  collected?: number;
  failed?: number;
  speed?: number;
  message?: string;
  data?: CollectedDataItem;
}

/** 任务列表查询参数 */
export interface TaskListParams {
  page?: number;
  pageSize?: number;
  keyword?: string;
  status?: TaskStatus | '';
  platform?: Platform | '';
  sortField?: string;
  sortOrder?: 'asc' | 'desc';
  startDate?: string;
  endDate?: string;
}

/** 任务统计 */
export interface TaskStats {
  totalCollected: number;
  totalFailed: number;
  successRate: number;
  speed: number;
  platformDistribution: { platform: string; count: number }[];
  hourlyStats: { hour: string; count: number }[];
}

/** 全局配置 */
export interface GlobalConfig {
  defaultRequestInterval: number;
  maxConcurrentTasks: number;
  proxyEnabled: boolean;
  proxyList: string[];
  userAgentRotation: boolean;
  userAgentList: string[];
  retryTimes: number;
  retryInterval: number;
  dataRetentionDays: number;
}

/** 代理测试结果 */
export interface ProxyTestResult {
  proxy: string;
  available: boolean;
  latency?: number;
  error?: string;
}

// ==================== 1. 任务管理 API ====================

/**
 * 获取任务列表
 */
export async function getTasks(params: TaskListParams = {}): Promise<PageResponse<CollectionTask>> {
  const response = await apiClient.get('/collection/tasks', { params });
  return response.data.data;
}

/**
 * 获取单个任务详情
 */
export async function getTask(id: number): Promise<CollectionTask> {
  const response = await apiClient.get(`/collection/tasks/${id}`);
  return response.data.data;
}

/**
 * 创建任务
 */
export async function createTask(data: CreateTaskRequest): Promise<CollectionTask> {
  const response = await apiClient.post('/collection/tasks', data);
  return response.data.data;
}

/**
 * 更新任务
 */
export async function updateTask(id: number, data: Partial<TaskConfig>): Promise<CollectionTask> {
  const response = await apiClient.put(`/collection/tasks/${id}`, data);
  return response.data.data;
}

/**
 * 删除任务
 */
export async function deleteTask(id: number): Promise<void> {
  await apiClient.delete(`/collection/tasks/${id}`);
}

/**
 * 批量删除任务
 */
export async function batchDeleteTasks(ids: number[]): Promise<void> {
  await apiClient.post('/collection/tasks/batch-delete', { ids });
}

/**
 * 启动任务
 */
export async function startTask(id: number): Promise<CollectionTask> {
  const response = await apiClient.post(`/collection/tasks/${id}/start`);
  return response.data.data;
}

/**
 * 停止任务
 */
export async function stopTask(id: number): Promise<CollectionTask> {
  const response = await apiClient.post(`/collection/tasks/${id}/stop`);
  return response.data.data;
}

/**
 * 暂停任务
 */
export async function pauseTask(id: number): Promise<CollectionTask> {
  const response = await apiClient.post(`/collection/tasks/${id}/pause`);
  return response.data.data;
}

/**
 * 恢复任务
 */
export async function resumeTask(id: number): Promise<CollectionTask> {
  const response = await apiClient.post(`/collection/tasks/${id}/resume`);
  return response.data.data;
}

/**
 * 重试失败任务
 */
export async function retryTask(id: number): Promise<CollectionTask> {
  const response = await apiClient.post(`/collection/tasks/${id}/retry`);
  return response.data.data;
}

// ==================== 2. 实时监控 API ====================

/** 日志查询参数 */
export interface LogQueryParams {
  page?: number;
  pageSize?: number;
  level?: 'INFO' | 'WARN' | 'ERROR' | '';
  startTime?: string;
  endTime?: string;
}

/**
 * 获取任务日志
 */
export async function getTaskLogs(id: number, params: LogQueryParams = {}): Promise<PageResponse<TaskLog>> {
  const response = await apiClient.get(`/collection/tasks/${id}/logs`, { params });
  return response.data.data;
}

/**
 * 获取任务统计
 */
export async function getTaskStats(id: number): Promise<TaskStats> {
  const response = await apiClient.get(`/collection/tasks/${id}/stats`);
  return response.data.data;
}

/**
 * 获取全局统计数据
 */
export async function getGlobalStats(params: { startDate?: string; endDate?: string } = {}): Promise<{
  totalTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  totalCollected: number;
  successRate: number;
  dailyStats: { date: string; success: number; failed: number }[];
  platformStats: { platform: string; count: number }[];
  durationStats: { range: string; count: number }[];
}> {
  const response = await apiClient.get('/collection/stats', { params });
  return response.data.data;
}

/**
 * 创建 WebSocket 连接获取实时数据
 * @param taskId 任务ID，不传则获取全局实时数据
 * @param onMessage 消息回调
 * @param onError 错误回调
 * @returns 关闭连接的函数
 */
export function connectRealtimeData(
  taskId: number | null,
  onMessage: (data: RealtimeMessage) => void,
  onError?: (error: Event) => void
): () => void {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  const port = '8081';
  const path = taskId ? `/api/ws/collection/${taskId}` : '/api/ws/collection';
  
  const ws = new WebSocket(`${protocol}//${host}:${port}${path}`);
  
  ws.onopen = () => {
    console.log('WebSocket connected for realtime data');
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
    // WebSocket 连接失败时只打印一次警告，避免刷屏
    console.warn('WebSocket 连接失败 (可忽略，不影响主要功能)');
    onError?.(error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };
  
  // 返回关闭函数
  return () => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };
}

/**
 * 轮询获取实时数据（WebSocket 备选方案）
 */
export async function pollRealtimeData(taskId?: number): Promise<{
  progress: number;
  collected: number;
  failed: number;
  speed: number;
  recentLogs: TaskLog[];
  recentData: CollectedDataItem[];
}> {
  const url = taskId ? `/collection/tasks/${taskId}/realtime` : '/collection/realtime';
  const response = await apiClient.get(url);
  return response.data.data;
}

// ==================== 3. 配置管理 API ====================

/**
 * 获取爬虫全局配置
 */
export async function getConfig(): Promise<GlobalConfig> {
  const response = await apiClient.get('/collection/config');
  return response.data.data;
}

/**
 * 更新全局配置
 */
export async function updateConfig(data: Partial<GlobalConfig>): Promise<GlobalConfig> {
  const response = await apiClient.put('/collection/config', data);
  return response.data.data;
}

/**
 * 测试代理可用性
 */
export async function testProxy(proxyList: string[]): Promise<ProxyTestResult[]> {
  const response = await apiClient.post('/collection/config/test-proxy', { proxyList });
  return response.data.data;
}

/**
 * 获取可用的 User-Agent 列表
 */
export async function getUserAgents(): Promise<string[]> {
  const response = await apiClient.get('/collection/config/user-agents');
  return response.data.data;
}

/**
 * 更新 User-Agent 列表
 */
export async function updateUserAgents(userAgents: string[]): Promise<void> {
  await apiClient.put('/collection/config/user-agents', { userAgents });
}

// ==================== 4. 数据操作 API ====================

/** 导出格式 */
export type ExportFormat = 'json' | 'csv' | 'excel';

/**
 * 导出任务数据
 */
export async function exportTaskData(
  id: number,
  format: ExportFormat = 'json',
  options?: {
    fields?: string[];
    startDate?: string;
    endDate?: string;
  }
): Promise<Blob> {
  const response = await apiClient.post(
    `/collection/tasks/${id}/export`,
    { format, ...options },
    { responseType: 'blob' }
  );
  return response.data;
}

/**
 * 下载导出文件的辅助函数
 */
export function downloadExportFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * 清空任务数据
 */
export async function clearTaskData(id: number): Promise<void> {
  await apiClient.delete(`/collection/tasks/${id}/data`);
}

/**
 * 获取任务采集的数据预览
 */
export async function getTaskDataPreview(
  id: number,
  params: { page?: number; pageSize?: number } = {}
): Promise<PageResponse<CollectedDataItem>> {
  const response = await apiClient.get(`/collection/tasks/${id}/data`, { params });
  return response.data.data;
}

/**
 * 获取单条采集数据详情
 */
export async function getDataDetail(taskId: number, dataId: number): Promise<CollectedDataItem> {
  const response = await apiClient.get(`/collection/tasks/${taskId}/data/${dataId}`);
  return response.data.data;
}

export default {
  // 任务管理
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  batchDeleteTasks,
  startTask,
  stopTask,
  pauseTask,
  resumeTask,
  retryTask,
  // 实时监控
  getTaskLogs,
  getTaskStats,
  getGlobalStats,
  connectRealtimeData,
  pollRealtimeData,
  // 配置管理
  getConfig,
  updateConfig,
  testProxy,
  getUserAgents,
  updateUserAgents,
  // 数据操作
  exportTaskData,
  downloadExportFile,
  clearTaskData,
  getTaskDataPreview,
  getDataDetail,
};
