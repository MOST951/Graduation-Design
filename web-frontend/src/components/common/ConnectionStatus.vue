<template>
  <div class="connection-status" :class="{ connected: isConnected, connecting: isConnecting, error: hasError }">
    <div class="status-indicator">
      <div class="status-dot" :class="{ active: isConnected, connecting: isConnecting }"></div>
      <span class="status-text">{{ getStatusText() }}</span>
    </div>
    
    <div v-if="showDetails" class="connection-info">
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
      <div v-if="reconnectAttempts > 0" class="info-item">
        <span class="info-label">Reconnect Attempts:</span>
        <span class="info-value">{{ reconnectAttempts }}</span>
      </div>
    </div>
    
    <div v-if="showActions" class="status-actions">
      <el-button
        v-if="!isConnected && !isConnecting"
        type="primary"
        size="small"
        :loading="isConnecting"
        :aria-label="'Connect to server'"
        @click="connect"
      >
        <el-icon><Connection /></el-icon>
        Connect
      </el-button>
      
      <el-button
        v-if="isConnected"
        type="danger"
        size="small"
        :aria-label="'Disconnect from server'"
        @click="disconnect"
      >
        <el-icon><Close /></el-icon>
        Disconnect
      </el-button>
      
      <el-button
        v-if="isConnecting || hasError"
        type="warning"
        size="small"
        :aria-label="'Cancel connection'"
        @click="cancelConnection"
      >
        <el-icon><Close /></el-icon>
        Cancel
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Connection, Close } from '@element-plus/icons-vue'

interface Props {
  isConnected: boolean
  isConnecting: boolean
  hasError: boolean
  protocol: string
  endpoint: string
  connectedAt?: Date
  lastMessage?: Date
  reconnectAttempts?: number
  showDetails?: boolean
  showActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  reconnectAttempts: 0,
  showDetails: true,
  showActions: true
})

const emit = defineEmits<{
  connect: []
  disconnect: []
  cancel: []
}>()

// Computed properties
const getStatusText = () => {
  if (props.isConnecting) return 'Connecting...'
  if (props.isConnected) return 'Connected'
  if (props.hasError) return 'Connection Error'
  return 'Disconnected'
}

// Methods
const connect = () => {
  emit('connect')
}

const disconnect = () => {
  emit('disconnect')
}

const cancelConnection = () => {
  emit('cancel')
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.connection-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
  transition: var(--transition-fast);
}

.connection-status.connected {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.connection-status.connecting {
  border-color: var(--color-warning);
  background: var(--color-warning-bg);
}

.connection-status.error {
  border-color: var(--color-danger);
  background: var(--color-danger-bg);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--border-radius-circle);
  background: var(--color-danger);
  transition: var(--transition-fast);
}

.status-dot.active {
  background: var(--color-success);
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.connecting {
  background: var(--color-warning);
  animation: blink 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes blink {
  0%, 50%, 100% {
    opacity: 1;
  }
  25%, 75% {
    opacity: 0.3;
  }
}

.status-text {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-size: var(--font-size-small);
}

.connection-info {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-tiny);
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.status-actions {
  display: flex;
  gap: var(--spacing-xs);
  margin-left: auto;
}

/* Responsive */
@media (max-width: 768px) {
  .connection-status {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }
  
  .connection-info {
    justify-content: center;
    gap: var(--spacing-sm);
  }
  
  .status-actions {
    justify-content: center;
    margin-left: 0;
  }
}

/* Accessibility */
.connection-status:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
