<template>
  <div class="virtual-log-list">
    <div class="log-controls">
      <div class="control-left">
        <el-button 
          text 
          size="small" 
          :disabled="logs.length === 0"
          aria-label="Clear logs"
          @click="clearLogs"
        >
          <el-icon><Delete /></el-icon>
          Clear
        </el-button>
        <el-switch
          v-model="autoScroll"
          active-text="Auto-scroll"
          size="small"
          aria-label="Auto-scroll toggle"
        />
      </div>
      <div class="control-right">
        <el-select
          v-model="logLevel"
          size="small"
          style="width: 120px"
          aria-label="Filter by log level"
        >
          <el-option label="All" value="all" />
          <el-option label="Info" value="info" />
          <el-option label="Warning" value="warning" />
          <el-option label="Error" value="error" />
        </el-select>
        <el-button
          text
          size="small"
          aria-label="Scroll to bottom"
          @click="scrollToBottom"
        >
          <el-icon><ArrowDown /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div 
      ref="scrollContainer"
      class="log-container"
      :style="{ height: height + 'px' }"
      @scroll="handleScroll"
    >
      <div class="log-content">
        <div
          v-for="(log, index) in visibleLogs"
          :key="`${log.timestamp}-${index}`"
          class="log-item"
          :class="[log.level, { highlighted: log.highlighted }]"
          :style="{ height: itemHeight + 'px' }"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-level" :class="log.level">[{{ log.level.toUpperCase() }}]</span>
          <span class="log-message">{{ log.message }}</span>
          <span v-if="log.details" class="log-details" @click="toggleDetails(index)">
            <el-icon><View /></el-icon>
          </span>
        </div>
        
        <!-- Expanded details -->
        <div
          v-for="(log, index) in visibleLogs"
          v-show="expandedItems.has(index)"
          :key="`details-${log.timestamp}-${index}`"
          class="log-details-content"
        >
          <pre>{{ JSON.stringify(log.details, null, 2) }}</pre>
        </div>
      </div>
    </div>
    
    <div class="log-footer">
      <span class="log-stats">
        Total: {{ logs.length }} | 
        Shown: {{ visibleLogs.length }} | 
        Errors: {{ errorCount }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { Delete, ArrowDown, View } from '@element-plus/icons-vue'

interface LogItem {
  timestamp: number
  level: 'info' | 'warning' | 'error'
  message: string
  details?: any
  highlighted?: boolean
}

interface Props {
  logs: LogItem[]
  height?: number
  itemHeight?: number
  bufferSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 300,
  itemHeight: 24,
  bufferSize: 5
})

const emit = defineEmits<{
  clear: []
  scroll: [scrollTop: number]
}>()

// Reactive data
const scrollContainer = ref<HTMLElement>()
const scrollTop = ref(0)
const autoScroll = ref(true)
const logLevel = ref('all')
const expandedItems = ref(new Set<number>())

// Computed properties
const filteredLogs = computed(() => {
  if (logLevel.value === 'all') return props.logs
  return props.logs.filter(log => log.level === logLevel.value)
})

const visibleLogs = computed(() => {
  const containerHeight = props.height
  const itemHeight = props.itemHeight
  const startIdx = Math.floor(scrollTop.value / itemHeight)
  const visibleCount = Math.ceil(containerHeight / itemHeight)
  
  const startIndex = Math.max(0, startIdx - props.bufferSize)
  const endIndex = Math.min(filteredLogs.value.length, startIdx + visibleCount + props.bufferSize)
  
  return filteredLogs.value.slice(startIndex, endIndex)
})

const errorCount = computed(() => {
  return props.logs.filter(log => log.level === 'error').length
})

const startIndex = computed(() => {
  return Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.bufferSize)
})

// Methods
const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement
  scrollTop.value = target.scrollTop
  emit('scroll', scrollTop.value)
  
  // Check if user scrolled away from bottom
  if (scrollContainer.value) {
    const { scrollHeight, clientHeight, scrollTop } = scrollContainer.value
    const isAtBottom = scrollHeight - clientHeight - scrollTop < 50
    if (!isAtBottom && autoScroll.value) {
      autoScroll.value = false
    }
  }
}

const scrollToBottom = () => {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    autoScroll.value = true
  }
}

const clearLogs = () => {
  emit('clear')
  expandedItems.value.clear()
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const toggleDetails = (index: number) => {
  if (expandedItems.value.has(index)) {
    expandedItems.value.delete(index)
  } else {
    expandedItems.value.add(index)
  }
}

// Auto-scroll when new logs are added
watch(() => props.logs.length, async () => {
  if (autoScroll.value && scrollContainer.value) {
    await nextTick()
    scrollToBottom()
  }
})

// Auto-scroll when filter changes
watch(logLevel, async () => {
  await nextTick()
  if (autoScroll.value) {
    scrollToBottom()
  }
})

// Lifecycle
onMounted(() => {
  // Initial scroll to bottom
  if (autoScroll.value && scrollContainer.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})

// Expose methods for parent component
defineExpose({
  scrollToBottom,
  clearLogs,
  toggleAutoScroll: () => { autoScroll.value = !autoScroll.value }
})
</script>

<style scoped>
.virtual-log-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
}

.log-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-base);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-hover);
}

.control-left,
.control-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.log-container {
  flex: 1;
  overflow-y: auto;
  position: relative;
}

.log-content {
  position: relative;
}

.log-item {
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-base);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-small);
  line-height: var(--item-height);
  border-bottom: 1px solid var(--color-border-extra-light);
  transition: var(--transition-fast);
  gap: var(--spacing-sm);
}

.log-item:hover {
  background: var(--color-bg-hover);
}

.log-item.highlighted {
  background: var(--color-warning-bg);
  animation: highlight 2s ease-out;
}

.log-item.info .log-level {
  color: var(--color-info);
}

.log-item.warning .log-level {
  color: var(--color-warning);
}

.log-item.error .log-level {
  color: var(--color-danger);
}

.log-time {
  color: var(--color-text-secondary);
  font-size: var(--font-size-tiny);
  min-width: 60px;
}

.log-level {
  font-weight: var(--font-weight-semibold);
  min-width: 50px;
}

.log-message {
  flex: 1;
  color: var(--color-text-primary);
  word-break: break-all;
}

.log-details {
  cursor: pointer;
  color: var(--color-info);
  opacity: 0.7;
  transition: var(--transition-fast);
}

.log-details:hover {
  opacity: 1;
}

.log-details-content {
  background: var(--color-bg-hover);
  border-left: 3px solid var(--color-info);
  padding: var(--spacing-sm) var(--spacing-base);
  margin: 0 var(--spacing-base);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}

.log-footer {
  padding: var(--spacing-xs) var(--spacing-base);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-hover);
}

.log-stats {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

@keyframes highlight {
  0% {
    background: var(--color-warning-bg);
  }
  100% {
    background: transparent;
  }
}

/* Scrollbar styling */
.log-container::-webkit-scrollbar {
  width: 6px;
}

.log-container::-webkit-scrollbar-track {
  background: transparent;
}

.log-container::-webkit-scrollbar-thumb {
  background: var(--color-border-base);
  border-radius: var(--border-radius-round);
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-placeholder);
}

/* Responsive */
@media (max-width: 768px) {
  .log-controls {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .control-left,
  .control-right {
    justify-content: center;
  }
  
  .log-item {
    padding: 0 var(--spacing-sm);
    font-size: var(--font-size-tiny);
  }
  
  .log-time {
    min-width: 50px;
  }
  
  .log-level {
    min-width: 40px;
  }
}
</style>
