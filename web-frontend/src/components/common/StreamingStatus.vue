<template>
  <div class="streaming-status" :class="{ connected: isConnected, disconnected: !isConnected }">
    <div class="status-indicator">
      <div class="status-dot" :class="{ active: isConnected }"></div>
      <span class="status-text">{{ getStatusText() }}</span>
    </div>
    
    <div class="connection-info">
      <div class="info-item">
        <span class="info-label">Protocol:</span>
        <span class="info-value">{{ protocol.toUpperCase() }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Endpoint:</span>
        <span class="info-value">{{ endpoint }}</span>
      </div>
      <div v-if="isConnected" class="info-item">
        <span class="info-label">Connected:</span>
        <span class="info-value">{{ formatTime(connectedAt) }}</span>
      </div>
      <div v-if="lastMessage" class="info-item">
        <span class="info-label">Last Message:</span>
        <span class="info-value">{{ formatTime(lastMessage) }}</span>
      </div>
    </div>
    
    <div v-if="isConnected" class="stream-stats">
      <div class="stat-item">
        <span class="stat-value">{{ messageCount }}</span>
        <span class="stat-label">Messages</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ getRate() }}</span>
        <span class="stat-label">msg/sec</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ getLatency() }}</span>
        <span class="stat-label">latency</span>
      </div>
    </div>
    
    <div class="status-actions">
      <el-button
        v-if="!isConnected"
        type="primary"
        size="small"
        :loading="isConnecting"
        :aria-label="'Connect to streaming server'"
        @click="connect"
      >
        <el-icon><Connection /></el-icon>
        Connect
      </el-button>
      
      <el-button
        v-if="isConnected"
        type="danger"
        size="small"
        :aria-label="'Disconnect from streaming server'"
        @click="disconnect"
      >
        <el-icon><Close /></el-icon>
        Disconnect
      </el-button>
      
      <el-button
        text
        size="small"
        :type="autoReconnect ? 'success' : 'default'"
        :aria-label="'Toggle auto reconnect'"
        @click="toggleAutoReconnect"
      >
        <el-icon><Refresh /></el-icon>
        Auto Reconnect
      </el-button>
    </div>
    
    <!-- Error display -->
    <div v-if="error" class="error-display">
      <el-alert
        :title="error.title"
        :description="error.message"
        type="error"
        :closable="false"
        show-icon
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Close, Refresh } from '@element-plus/icons-vue'

interface StreamingError {
  title: string
  message: string
  code?: string
}

interface Props {
  protocol: 'websocket' | 'sse'
  endpoint: string
  autoConnect?: boolean
  autoReconnect?: boolean
  reconnectInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoConnect: true,
  autoReconnect: true,
  reconnectInterval: 5000
})

const emit = defineEmits<{
  connect: []
  disconnect: []
  message: [data: any]
  error: [error: StreamingError]
}>()

// Reactive data
const isConnected = ref(false)
const isConnecting = ref(false)
const autoReconnect = ref(props.autoReconnect)
const connectedAt = ref<Date | null>(null)
const lastMessage = ref<Date | null>(null)
const messageCount = ref(0)
const messageTimestamps = ref<number[]>([])
const error = ref<StreamingError | null>(null)

// WebSocket/SSE connection
let connection: WebSocket | EventSource | null = null
let reconnectTimer: NodeJS.Timeout | null = null
let messageRateTimer: NodeJS.Timeout | null = null

// Computed properties
const getStatusText = () => {
  if (isConnecting.value) return 'Connecting...'
  if (isConnected.value) return 'Connected'
  if (error.value) return 'Error'
  return 'Disconnected'
}

const getRate = () => {
  const now = Date.now()
  const recentMessages = messageTimestamps.value.filter(timestamp => now - timestamp < 10000)
  return (recentMessages.length / 10).toFixed(1)
}

const getLatency = () => {
  // Simulate latency calculation
  return isConnected.value ? `${Math.floor(Math.random() * 50 + 10)}ms` : 'N/A'
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// Methods
const connect = async () => {
  if (isConnected.value || isConnecting.value) return
  
  isConnecting.value = true
  error.value = null
  
  try {
    if (props.protocol === 'websocket') {
      await connectWebSocket()
    } else {
      await connectSSE()
    }
  } catch (err) {
    handleError({
      title: 'Connection Failed',
      message: `Failed to connect to ${props.endpoint}`,
      code: 'CONN_ERROR'
    })
  } finally {
    isConnecting.value = false
  }
}

const disconnect = () => {
  if (connection) {
    if (props.protocol === 'websocket') {
      (connection as WebSocket).close()
    } else {
      (connection as EventSource).close()
    }
    connection = null
  }
  
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  
  isConnected.value = false
  connectedAt.value = null
  emit('disconnect')
}

const connectWebSocket = () => {
  return new Promise<void>((resolve, reject) => {
    try {
      const ws = new WebSocket(props.endpoint)
      connection = ws
      
      ws.onopen = () => {
        isConnected.value = true
        connectedAt.value = new Date()
        messageCount.value = 0
        messageTimestamps.value = []
        emit('connect')
        resolve()
      }
      
      ws.onmessage = (event) => {
        handleMessage(event.data)
      }
      
      ws.onclose = () => {
        handleDisconnect()
      }
      
      ws.onerror = () => {
        handleError({
          title: 'WebSocket Error',
          message: 'WebSocket connection error',
          code: 'WS_ERROR'
        })
        reject(new Error('WebSocket error'))
      }
    } catch (err) {
      reject(err)
    }
  })
}

const connectSSE = () => {
  return new Promise<void>((resolve, reject) => {
    try {
      const eventSource = new EventSource(props.endpoint)
      connection = eventSource
      
      eventSource.onopen = () => {
        isConnected.value = true
        connectedAt.value = new Date()
        messageCount.value = 0
        messageTimestamps.value = []
        emit('connect')
        resolve()
      }
      
      eventSource.onmessage = (event) => {
        handleMessage(event.data)
      }
      
      eventSource.onerror = () => {
        handleError({
          title: 'SSE Error',
          message: 'Server-Sent Events connection error',
          code: 'SSE_ERROR'
        })
        reject(new Error('SSE error'))
      }
    } catch (err) {
      reject(err)
    }
  })
}

const handleMessage = (data: string) => {
  try {
    const parsedData = JSON.parse(data)
    lastMessage.value = new Date()
    messageCount.value++
    messageTimestamps.value.push(Date.now())
    
    // Keep only last 100 timestamps for rate calculation
    if (messageTimestamps.value.length > 100) {
      messageTimestamps.value = messageTimestamps.value.slice(-100)
    }
    
    emit('message', parsedData)
  } catch (err) {
    console.error('Failed to parse message:', err)
  }
}

const handleDisconnect = () => {
  isConnected.value = false
  connection = null
  
  if (autoReconnect.value && !error.value) {
    scheduleReconnect()
  }
  
  emit('disconnect')
}

const handleError = (err: StreamingError) => {
  error.value = err
  isConnected.value = false
  connection = null
  
  emit('error', err)
  
  if (autoReconnect.value) {
    scheduleReconnect()
  }
}

const scheduleReconnect = () => {
  if (reconnectTimer) return
  
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connect()
  }, props.reconnectInterval)
}

const toggleAutoReconnect = () => {
  autoReconnect.value = !autoReconnect.value
  
  if (!autoReconnect.value && reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  
  ElMessage.info(`Auto reconnect ${autoReconnect.value ? 'enabled' : 'disabled'}`)
}

// Lifecycle
onMounted(() => {
  if (props.autoConnect) {
    connect()
  }
  
  // Start message rate calculation timer
  messageRateTimer = setInterval(() => {
    // Clean old timestamps
    const now = Date.now()
    messageTimestamps.value = messageTimestamps.value.filter(timestamp => now - timestamp < 10000)
  }, 5000)
})

onUnmounted(() => {
  disconnect()
  
  if (messageRateTimer) {
    clearInterval(messageRateTimer)
  }
})

// Expose methods
defineExpose({
  connect,
  disconnect,
  isConnected: computed(() => isConnected.value),
  messageCount: computed(() => messageCount.value)
})
</script>

<style scoped>
.streaming-status {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-base);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
}

.streaming-status.connected {
  border-color: var(--color-success);
}

.streaming-status.disconnected {
  border-color: var(--color-danger);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--border-radius-circle);
  background: var(--color-danger);
  transition: var(--transition-fast);
}

.status-dot.active {
  background: var(--color-success);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-text {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.connection-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-small);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-small);
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.stream-stats {
  display: flex;
  justify-content: space-around;
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-small);
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.stat-label {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.status-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.error-display {
  margin-top: var(--spacing-sm);
}

/* Responsive */
@media (max-width: 768px) {
  .streaming-status {
    padding: var(--spacing-sm);
  }
  
  .connection-info {
    grid-template-columns: 1fr;
    gap: var(--spacing-xs);
  }
  
  .stream-stats {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  
  .stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .stat-value {
    font-size: var(--font-size-medium);
  }
  
  .status-actions {
    justify-content: center;
  }
}

/* Accessibility */
.streaming-status:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
