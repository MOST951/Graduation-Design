/**
 * 通用自动重连 composable
 * 支持 WebSocket 和 SSE (EventSource) 连接的指数退避重连
 *
 * 用法:
 *   const { status, connect, disconnect, messageCount } = useReconnectingEventSource(url, { onMessage })
 *   const { status, connect, disconnect } = useReconnectingWebSocket(url, { onMessage })
 */
import { ref, readonly, onUnmounted, type Ref } from 'vue';

// ==================== 类型定义 ====================

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface ReconnectOptions {
  /** 初始重连延迟 (ms)，默认 1000 */
  initialDelay?: number;
  /** 最大重连延迟 (ms)，默认 30000 */
  maxDelay?: number;
  /** 退避因子，默认 2 */
  backoffFactor?: number;
  /** 最大重连次数，0 表示无限，默认 0 */
  maxAttempts?: number;
  /** 达到最大次数后的冷却时间 (ms)，冷却后重置计数，默认 60000 */
  cooldownAfterMax?: number;
  /** 是否自动开始连接，默认 true */
  immediate?: boolean;
}

export interface SSEOptions extends ReconnectOptions {
  onMessage?: (data: string) => void;
  onParsedMessage?: (data: unknown) => void;
  onError?: (error: Event) => void;
  onStatusChange?: (status: ConnectionStatus) => void;
  withCredentials?: boolean;
}

export interface WSOptions extends ReconnectOptions {
  onMessage?: (data: MessageEvent) => void;
  onParsedMessage?: (data: unknown) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onStatusChange?: (status: ConnectionStatus) => void;
  protocols?: string | string[];
  /** 心跳间隔 (ms)，0 表示不发送心跳，默认 30000 */
  heartbeatInterval?: number;
  /** 心跳消息内容，默认 '{"type":"ping"}' */
  heartbeatMessage?: string;
}

// ==================== 内部工具 ====================

function calcDelay(attempt: number, initial: number, max: number, factor: number): number {
  // 指数退避 + 随机抖动 (±25%)
  const base = Math.min(initial * Math.pow(factor, attempt), max);
  const jitter = base * 0.25 * (Math.random() * 2 - 1);
  return Math.round(base + jitter);
}

// ==================== SSE ====================

export function useReconnectingEventSource(url: string | Ref<string>, options: SSEOptions = {}) {
  const {
    initialDelay = 1000,
    maxDelay = 30000,
    backoffFactor = 2,
    maxAttempts = 0,
    cooldownAfterMax = 60000,
    immediate = true,
    onMessage,
    onParsedMessage,
    onError,
    onStatusChange,
    withCredentials = false,
  } = options;

  const status = ref<ConnectionStatus>('disconnected');
  const messageCount = ref(0);
  const reconnectAttempts = ref(0);

  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let cooldownTimer: ReturnType<typeof setTimeout> | null = null;
  let intentionalClose = false;

  function getUrl(): string {
    return typeof url === 'string' ? url : url.value;
  }

  function setStatus(s: ConnectionStatus) {
    status.value = s;
    onStatusChange?.(s);
  }

  function clearTimers() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    if (cooldownTimer) { clearTimeout(cooldownTimer); cooldownTimer = null; }
  }

  function scheduleReconnect() {
    if (intentionalClose) return;
    if (maxAttempts > 0 && reconnectAttempts.value >= maxAttempts) {
      console.warn(`[SSE] 达到最大重连次数 (${maxAttempts})，${cooldownAfterMax / 1000}s 后重置`);
      setStatus('disconnected');
      cooldownTimer = setTimeout(() => {
        reconnectAttempts.value = 0;
        connect();
      }, cooldownAfterMax);
      return;
    }

    const delay = calcDelay(reconnectAttempts.value, initialDelay, maxDelay, backoffFactor);
    reconnectAttempts.value++;
    console.log(`[SSE] 重连 #${reconnectAttempts.value}，延迟 ${delay}ms`);
    setStatus('reconnecting');

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      doConnect();
    }, delay);
  }

  function doConnect() {
    close();
    setStatus('connecting');

    try {
      source = new EventSource(getUrl(), { withCredentials });

      source.onopen = () => {
        reconnectAttempts.value = 0;
        setStatus('connected');
      };

      source.onmessage = (event) => {
        messageCount.value++;
        onMessage?.(event.data);
        if (onParsedMessage) {
          try { onParsedMessage(JSON.parse(event.data)); } catch { /* ignore parse error */ }
        }
      };

      source.onerror = (event) => {
        onError?.(event);
        close();
        scheduleReconnect();
      };
    } catch (e) {
      console.error('[SSE] 连接创建失败:', e);
      scheduleReconnect();
    }
  }

  function close() {
    if (source) {
      source.close();
      source = null;
    }
  }

  function connect() {
    intentionalClose = false;
    clearTimers();
    reconnectAttempts.value = 0;
    messageCount.value = 0;
    doConnect();
  }

  function disconnect() {
    intentionalClose = true;
    clearTimers();
    close();
    setStatus('disconnected');
  }

  if (immediate) {
    connect();
  }

  onUnmounted(() => {
    disconnect();
  });

  return {
    status: readonly(status),
    messageCount: readonly(messageCount),
    reconnectAttempts: readonly(reconnectAttempts),
    connect,
    disconnect,
  };
}

// ==================== WebSocket ====================

export function useReconnectingWebSocket(url: string | Ref<string>, options: WSOptions = {}) {
  const {
    initialDelay = 1000,
    maxDelay = 30000,
    backoffFactor = 2,
    maxAttempts = 0,
    cooldownAfterMax = 60000,
    immediate = true,
    onMessage,
    onParsedMessage,
    onError,
    onOpen,
    onClose,
    onStatusChange,
    protocols,
    heartbeatInterval = 30000,
    heartbeatMessage = '{"type":"ping"}',
  } = options;

  const status = ref<ConnectionStatus>('disconnected');
  const messageCount = ref(0);
  const reconnectAttempts = ref(0);

  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let cooldownTimer: ReturnType<typeof setTimeout> | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let intentionalClose = false;

  function getUrl(): string {
    return typeof url === 'string' ? url : url.value;
  }

  function setStatus(s: ConnectionStatus) {
    status.value = s;
    onStatusChange?.(s);
  }

  function clearTimers() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    if (cooldownTimer) { clearTimeout(cooldownTimer); cooldownTimer = null; }
    stopHeartbeat();
  }

  function startHeartbeat() {
    if (heartbeatInterval <= 0) return;
    heartbeatTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(heartbeatMessage);
      }
    }, heartbeatInterval);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
  }

  function scheduleReconnect() {
    if (intentionalClose) return;
    if (maxAttempts > 0 && reconnectAttempts.value >= maxAttempts) {
      console.warn(`[WS] 达到最大重连次数 (${maxAttempts})，${cooldownAfterMax / 1000}s 后重置`);
      setStatus('disconnected');
      cooldownTimer = setTimeout(() => {
        reconnectAttempts.value = 0;
        connect();
      }, cooldownAfterMax);
      return;
    }

    const delay = calcDelay(reconnectAttempts.value, initialDelay, maxDelay, backoffFactor);
    reconnectAttempts.value++;
    console.log(`[WS] 重连 #${reconnectAttempts.value}，延迟 ${delay}ms`);
    setStatus('reconnecting');

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      doConnect();
    }, delay);
  }

  function doConnect() {
    closeWs();
    setStatus('connecting');

    try {
      ws = protocols ? new WebSocket(getUrl(), protocols) : new WebSocket(getUrl());

      ws.onopen = () => {
        reconnectAttempts.value = 0;
        setStatus('connected');
        startHeartbeat();
        onOpen?.();
      };

      ws.onmessage = (event) => {
        messageCount.value++;
        onMessage?.(event);
        if (onParsedMessage) {
          try { onParsedMessage(JSON.parse(event.data)); } catch { /* ignore */ }
        }
      };

      ws.onerror = (event) => {
        onError?.(event);
      };

      ws.onclose = (event) => {
        stopHeartbeat();
        onClose?.(event);
        if (!intentionalClose) {
          scheduleReconnect();
        } else {
          setStatus('disconnected');
        }
      };
    } catch (e) {
      console.error('[WS] 连接创建失败:', e);
      scheduleReconnect();
    }
  }

  function closeWs() {
    if (ws) {
      ws.onclose = null; // prevent triggering reconnect
      ws.close();
      ws = null;
    }
  }

  function send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data);
    } else {
      console.warn('[WS] 发送失败: 连接未就绪');
    }
  }

  function connect() {
    intentionalClose = false;
    clearTimers();
    reconnectAttempts.value = 0;
    messageCount.value = 0;
    doConnect();
  }

  function disconnect() {
    intentionalClose = true;
    clearTimers();
    closeWs();
    setStatus('disconnected');
  }

  if (immediate) {
    connect();
  }

  onUnmounted(() => {
    disconnect();
  });

  return {
    status: readonly(status),
    messageCount: readonly(messageCount),
    reconnectAttempts: readonly(reconnectAttempts),
    connect,
    disconnect,
    send,
  };
}
