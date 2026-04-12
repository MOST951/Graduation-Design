/**
 * 实时监控模块 API
 */
import apiClient from './index';

// ==================== 类型定义 ====================

/** 实时统计数据 */
export interface RealtimeStats {
  onlineUsers: number;
  onlineUsersTrend: number;
  newWeiboPerSecond: number;
  newWeiboTrend: number;
  sentimentScore: number;
  sentimentScoreTrend: number;
  negativeRatio: number;
  negativeRatioTrend: number;
  totalProcessed: number;
  avgLatency: number;
}

/** 实时情感分布 */
export interface RealtimeSentimentDist {
  positive: number;
  neutral: number;
  negative: number;
  timestamp: string;
}

/** 实时微博数据 */
export interface RealtimeWeibo {
  id: string;
  userId: string;
  userName: string;
  userAvatar: string;
  userVerified: boolean;
  content: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  sentimentScore: number;
  keywords: string[];
  location?: string;
  time: string;
  likes: number;
  comments: number;
  reposts: number;
}

/** 实时词云数据 */
export interface RealtimeWordCloud {
  words: { name: string; value: number; trend: number }[];
  updateTime: string;
}

/** 预警规则 */
export interface AlertRule {
  id: number;
  name: string;
  enabled: boolean;
  conditions: AlertCondition[];
  scope: {
    type: 'all' | 'topic' | 'user' | 'keyword';
    values?: string[];
  };
  timeWindow: number; // 分钟
  notifyMethods: ('site' | 'email' | 'sms' | 'webhook')[];
  webhookUrl?: string;
  silencePeriod: number; // 分钟
  level: 'high' | 'medium' | 'low';
  createdAt: string;
  updatedAt: string;
}

/** 预警条件 */
export interface AlertCondition {
  type: 'negative_ratio' | 'keyword_frequency' | 'volume_spike' | 'kol_sensitive';
  operator: '>' | '<' | '>=' | '<=' | '==';
  value: number;
  keyword?: string;
  userId?: string;
}

/** 预警事件 */
export interface AlertEvent {
  id: number;
  ruleId: number;
  ruleName: string;
  level: 'high' | 'medium' | 'low';
  status: 'pending' | 'processing' | 'resolved' | 'ignored';
  description: string;
  triggerValue: number;
  threshold: number;
  relatedWeibos?: string[];
  triggeredAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
  note?: string;
}

/** 地理分布数据 */
export interface GeoDistribution {
  region: string;
  regionCode: string;
  count: number;
  heat: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
  avgSentimentScore: number;
}

/** 地区统计 */
export interface GeoStats {
  region: string;
  totalCount: number;
  sentimentDist: { sentiment: string; count: number; ratio: number }[];
  topKeywords: { word: string; count: number }[];
  hourlyTrend: { hour: string; count: number; sentiment: number }[];
  topUsers: { name: string; count: number; influence: number }[];
}

/** 系统指标 */
export interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  networkIn: number;
  networkOut: number;
  diskUsage: number;
  processLatency: number;
  queueSize: number;
  errorRate: number;
  uptime: number;
}

/** 连接统计 */
export interface ConnectionStats {
  status: 'connected' | 'connecting' | 'disconnected';
  connectedAt?: string;
  messagesReceived: number;
  messagesSent: number;
  bytesReceived: number;
  bytesSent: number;
  reconnectCount: number;
  lastHeartbeat?: string;
}

/** WebSocket消息类型 */
export type WSMessageType = 'REAL_TIME_DATA' | 'ALERT_EVENT' | 'SYSTEM_STATUS' | 'CONTROL_COMMAND';

/** WebSocket消息 */
export interface WSMessage {
  type: WSMessageType;
  data: any;
  timestamp: string;
}

/** 分页响应 */
export interface PageResponse<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

// ==================== 1. 实时数据 API ====================

/**
 * 获取实时统计
 */
export async function getRealtimeStats(): Promise<RealtimeStats> {
  const response = await apiClient.get('/realtime/stats');
  return response.data.data;
}

/**
 * 获取实时情感分布
 */
export async function getRealtimeSentimentDist(): Promise<RealtimeSentimentDist> {
  const response = await apiClient.get('/realtime/sentiment');
  return response.data.data;
}

/**
 * 获取实时微博流
 */
export async function getRealtimeWeibos(params?: {
  sentiment?: string;
  keyword?: string;
  limit?: number;
}): Promise<RealtimeWeibo[]> {
  const response = await apiClient.get('/realtime/weibos', { params });
  return response.data.data;
}

/**
 * 获取实时词云
 */
export async function getRealtimeWordCloud(params?: {
  minutes?: number;
  limit?: number;
}): Promise<RealtimeWordCloud> {
  const response = await apiClient.get('/realtime/wordcloud', { params });
  return response.data.data;
}

/**
 * 获取历史实时数据
 */
export async function getHistoricalRealtimeData(params: {
  metric: string;
  startTime: string;
  endTime: string;
  interval?: 'minute' | 'hour' | 'day';
}): Promise<{ time: string; value: number }[]> {
  const response = await apiClient.get('/realtime/historical', { params });
  return response.data.data;
}

/**
 * 获取实时趋势数据
 */
export async function getRealtimeTrend(params?: {
  metrics?: string[];
  minutes?: number;
}): Promise<{
  timestamps: string[];
  series: { name: string; data: number[] }[];
}> {
  const response = await apiClient.get('/realtime/trend', { params });
  return response.data.data;
}

/**
 * 创建 SSE 连接获取实时数据流
 */
export function createRealtimeStream(
  onMessage: (data: RealtimeWeibo) => void,
  onError?: (error: Event) => void
): () => void {
  const eventSource = new EventSource('/api/realtime/stream');
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse SSE message:', e);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    onError?.(error);
  };
  
  return () => {
    eventSource.close();
  };
}

// ==================== 2. 预警管理 API ====================

/**
 * 获取预警规则列表
 */
export async function getAlertRules(): Promise<AlertRule[]> {
  const response = await apiClient.get('/realtime/alert/rules');
  return response.data.data;
}

/**
 * 获取单个预警规则
 */
export async function getAlertRule(id: number): Promise<AlertRule> {
  const response = await apiClient.get(`/realtime/alert/rules/${id}`);
  return response.data.data;
}

/**
 * 创建预警规则
 */
export async function createAlertRule(data: Omit<AlertRule, 'id' | 'createdAt' | 'updatedAt'>): Promise<AlertRule> {
  const response = await apiClient.post('/realtime/alert/rules', data);
  return response.data.data;
}

/**
 * 更新预警规则
 */
export async function updateAlertRule(id: number, data: Partial<AlertRule>): Promise<AlertRule> {
  const response = await apiClient.put(`/realtime/alert/rules/${id}`, data);
  return response.data.data;
}

/**
 * 删除预警规则
 */
export async function deleteAlertRule(id: number): Promise<void> {
  await apiClient.delete(`/realtime/alert/rules/${id}`);
}

/**
 * 测试预警规则
 */
export async function testAlertRule(id: number): Promise<{
  triggered: boolean;
  currentValue: number;
  threshold: number;
  message: string;
}> {
  const response = await apiClient.post(`/realtime/alert/rules/${id}/test`);
  return response.data.data;
}

/**
 * 切换预警规则状态
 */
export async function toggleAlertRule(id: number, enabled: boolean): Promise<void> {
  await apiClient.patch(`/realtime/alert/rules/${id}/toggle`, { enabled });
}

/**
 * 获取预警事件列表
 */
export async function getAlertEvents(params?: {
  page?: number;
  pageSize?: number;
  level?: string;
  status?: string;
  startTime?: string;
  endTime?: string;
}): Promise<PageResponse<AlertEvent>> {
  const response = await apiClient.get('/realtime/alert/events', { params });
  return response.data.data;
}

/**
 * 获取单个预警事件
 */
export async function getAlertEvent(id: number): Promise<AlertEvent> {
  const response = await apiClient.get(`/realtime/alert/events/${id}`);
  return response.data.data;
}

/**
 * 更新预警事件状态
 */
export async function updateAlertEvent(id: number, data: {
  status?: AlertEvent['status'];
  note?: string;
}): Promise<AlertEvent> {
  const response = await apiClient.patch(`/realtime/alert/events/${id}`, data);
  return response.data.data;
}

/**
 * 批量更新预警事件
 */
export async function batchUpdateAlertEvents(ids: number[], data: {
  status?: AlertEvent['status'];
}): Promise<void> {
  await apiClient.patch('/realtime/alert/events/batch', { ids, ...data });
}

/**
 * 获取预警统计
 */
export async function getAlertStats(params?: {
  startTime?: string;
  endTime?: string;
}): Promise<{
  totalCount: number;
  pendingCount: number;
  resolvedCount: number;
  avgResolveTime: number;
  falsePositiveRate: number;
  levelDist: { level: string; count: number }[];
  dailyTrend: { date: string; count: number }[];
}> {
  const response = await apiClient.get('/realtime/alert/stats', { params });
  return response.data.data;
}

// ==================== 3. 地理数据 API ====================

/**
 * 获取地理分布数据
 */
export async function getGeoDistribution(params?: {
  mapType?: 'china' | 'world' | 'province';
  province?: string;
  metric?: 'count' | 'heat' | 'sentiment';
  startTime?: string;
  endTime?: string;
}): Promise<GeoDistribution[]> {
  const response = await apiClient.get('/realtime/geo/distribution', { params });
  return response.data.data;
}

/**
 * 获取地区统计
 */
export async function getGeoStats(region: string): Promise<GeoStats> {
  const response = await apiClient.get(`/realtime/geo/stats/${encodeURIComponent(region)}`);
  return response.data.data;
}

/**
 * 获取地区排行
 */
export async function getGeoRanking(params?: {
  metric?: 'count' | 'heat' | 'negative';
  limit?: number;
}): Promise<{
  region: string;
  value: number;
  trend: number;
}[]> {
  const response = await apiClient.get('/realtime/geo/ranking', { params });
  return response.data.data;
}

/**
 * 设置重点关注地区
 */
export async function setGeoFocus(regions: string[]): Promise<void> {
  await apiClient.post('/realtime/geo/focus', { regions });
}

/**
 * 获取重点关注地区
 */
export async function getGeoFocus(): Promise<string[]> {
  const response = await apiClient.get('/realtime/geo/focus');
  return response.data.data;
}

/**
 * 设置地区预警阈值
 */
export async function setGeoAlertThreshold(region: string, config: {
  enabled: boolean;
  negativeThreshold?: number;
  volumeThreshold?: number;
}): Promise<void> {
  await apiClient.post(`/realtime/geo/alert/${encodeURIComponent(region)}`, config);
}

// ==================== 4. 系统监控 API ====================

/**
 * 获取系统指标
 */
export async function getSystemMetrics(): Promise<SystemMetrics> {
  const response = await apiClient.get('/realtime/system/metrics');
  return response.data.data;
}

/**
 * 获取系统指标历史
 */
export async function getSystemMetricsHistory(params?: {
  metric?: string;
  minutes?: number;
}): Promise<{ time: string; value: number }[]> {
  const response = await apiClient.get('/realtime/system/metrics/history', { params });
  return response.data.data;
}

/**
 * 获取连接统计
 */
export async function getConnectionStats(): Promise<ConnectionStats> {
  const response = await apiClient.get('/realtime/system/connection');
  return response.data.data;
}

/**
 * 控制实时流
 */
export async function controlRealtimeStream(action: 'start' | 'stop' | 'restart'): Promise<{
  status: string;
  message: string;
}> {
  const response = await apiClient.post('/realtime/system/stream/control', { action });
  return response.data.data;
}

/**
 * 获取处理队列状态
 */
export async function getQueueStatus(): Promise<{
  queueName: string;
  size: number;
  processing: number;
  failed: number;
  avgProcessTime: number;
}[]> {
  const response = await apiClient.get('/realtime/system/queue');
  return response.data.data;
}

/**
 * 获取系统日志
 */
export async function getSystemLogs(params?: {
  level?: 'info' | 'warn' | 'error';
  limit?: number;
}): Promise<{
  time: string;
  level: string;
  message: string;
  source: string;
}[]> {
  const response = await apiClient.get('/realtime/system/logs', { params });
  return response.data.data;
}

// ==================== 5. WebSocket 管理 ====================

/**
 * WebSocket 连接管理类
 */
export class RealtimeWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private initialDelay = 1000;
  private maxDelay = 30000;
  private cooldownAfterMax = 60000;
  private heartbeatInterval: number | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private cooldownTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;
  private messageQueue: WSMessage[] = [];
  private listeners: Map<WSMessageType, ((data: any) => void)[]> = new Map();
  private statusListeners: ((status: ConnectionStats['status']) => void)[] = [];
  
  public status: ConnectionStats['status'] = 'disconnected';
  public stats = {
    messagesReceived: 0,
    messagesSent: 0,
    bytesReceived: 0,
    bytesSent: 0,
    reconnectCount: 0,
  };

  constructor(url?: string) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    this.url = url || `${protocol}//${host}:8081/api/ws/realtime`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    
    this.intentionalClose = false;
    this.reconnectAttempts = 0;
    this.clearTimers();
    this.doConnect();
  }

  private doConnect(): void {
    this.setStatus('connecting');
    
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      console.error('[WS] 连接创建失败:', e);
      this.scheduleReconnect();
      return;
    }
    
    this.ws.onopen = () => {
      console.log('[WS] 已连接');
      this.setStatus('connected');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.flushMessageQueue();
    };
    
    this.ws.onmessage = (event) => {
      this.stats.messagesReceived++;
      this.stats.bytesReceived += event.data.length;
      
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.notifyListeners(message.type, message.data);
      } catch (e) {
        console.error('[WS] 消息解析失败:', e);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('[WS] 连接错误:', error);
    };
    
    this.ws.onclose = () => {
      console.log('[WS] 连接关闭');
      this.stopHeartbeat();
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      } else {
        this.setStatus('disconnected');
      }
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.clearTimers();
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  send(type: WSMessageType, data: any): void {
    const message: WSMessage = { type, data, timestamp: new Date().toISOString() };
    
    if (this.ws?.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify(message);
      this.ws.send(payload);
      this.stats.messagesSent++;
      this.stats.bytesSent += payload.length;
    } else {
      this.messageQueue.push(message);
    }
  }

  on(type: WSMessageType, callback: (data: any) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(callback);
    
    return () => {
      const callbacks = this.listeners.get(type);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) callbacks.splice(index, 1);
      }
    };
  }

  onStatusChange(callback: (status: ConnectionStats['status']) => void): () => void {
    this.statusListeners.push(callback);
    return () => {
      const index = this.statusListeners.indexOf(callback);
      if (index > -1) this.statusListeners.splice(index, 1);
    };
  }

  private setStatus(status: ConnectionStats['status']): void {
    this.status = status;
    this.statusListeners.forEach(cb => cb(status));
  }

  private notifyListeners(type: WSMessageType, data: any): void {
    this.listeners.get(type)?.forEach(cb => cb(data));
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      this.send('CONTROL_COMMAND', { action: 'heartbeat' });
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private clearTimers(): void {
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.cooldownTimer) { clearTimeout(this.cooldownTimer); this.cooldownTimer = null; }
  }

  private scheduleReconnect(): void {
    if (this.intentionalClose) return;

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn(`[WS] 达到最大重连次数 (${this.maxReconnectAttempts})，${this.cooldownAfterMax / 1000}s 后重试`);
      this.setStatus('disconnected');
      this.cooldownTimer = setTimeout(() => {
        this.reconnectAttempts = 0;
        this.doConnect();
      }, this.cooldownAfterMax);
      return;
    }
    
    // 指数退避 + 随机抖动
    const base = Math.min(this.initialDelay * Math.pow(2, this.reconnectAttempts), this.maxDelay);
    const jitter = base * 0.25 * (Math.random() * 2 - 1);
    const delay = Math.round(base + jitter);
    
    this.reconnectAttempts++;
    this.stats.reconnectCount++;
    console.log(`[WS] 重连 #${this.reconnectAttempts}/${this.maxReconnectAttempts}，延迟 ${delay}ms`);
    this.setStatus('connecting');
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.doConnect();
    }, delay);
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!;
      this.send(message.type, message.data);
    }
  }
}

// 全局 WebSocket 实例
export const realtimeWS = new RealtimeWebSocket();

export default {
  // 实时数据
  getRealtimeStats,
  getRealtimeSentimentDist,
  getRealtimeWeibos,
  getRealtimeWordCloud,
  getHistoricalRealtimeData,
  getRealtimeTrend,
  createRealtimeStream,
  
  // 预警管理
  getAlertRules,
  getAlertRule,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  testAlertRule,
  toggleAlertRule,
  getAlertEvents,
  getAlertEvent,
  updateAlertEvent,
  batchUpdateAlertEvents,
  getAlertStats,
  
  // 地理数据
  getGeoDistribution,
  getGeoStats,
  getGeoRanking,
  setGeoFocus,
  getGeoFocus,
  setGeoAlertThreshold,
  
  // 系统监控
  getSystemMetrics,
  getSystemMetricsHistory,
  getConnectionStats,
  controlRealtimeStream,
  getQueueStatus,
  getSystemLogs,
  
  // WebSocket
  realtimeWS,
  RealtimeWebSocket,
};
