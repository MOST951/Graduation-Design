<template>
  <div class="system-log-viewer">
    <div class="log-header">
      <div class="header-left">
        <el-icon><Document /></el-icon>
        <span class="header-title">System Logs</span>
        <el-tag type="info" size="small">{{ filteredLogs.length }} entries</el-tag>
      </div>
      
      <div class="header-right">
        <el-button
          type="primary"
          size="small"
          :icon="Download"
          @click="exportLogs"
          :disabled="filteredLogs.length === 0"
          :aria-label="'Export filtered logs'"
        >
          Export Logs
        </el-button>
      </div>
    </div>
    
    <div class="log-filters">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-select
            v-model="selectedLevel"
            placeholder="Select log level"
            clearable
            style="width: 100%"
            @change="filterLogs"
          >
            <el-option label="All Levels" value="" />
            <el-option label="INFO" value="info" />
            <el-option label="WARN" value="warn" />
            <el-option label="ERROR" value="error" />
          </el-select>
        </el-col>
        
        <el-col :span="12">
          <el-input
            v-model="searchKeyword"
            placeholder="Search keywords..."
            clearable
            @input="filterLogs"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        
        <el-col :span="4">
          <el-button
            type="default"
            size="small"
            @click="clearFilters"
            :aria-label="'Clear all filters'"
          >
            Clear
          </el-button>
        </el-col>
      </el-row>
    </div>
    
    <div class="log-content">
      <el-table
        :data="paginatedLogs"
        height="400"
        size="small"
        :show-header="true"
        @scroll="handleScroll"
        ref="logTableRef"
        :aria-label="'System logs table'"
      >
        <el-table-column prop="timestamp" label="Time" width="180">
          <template #default="{ row }">
            <span class="timestamp">{{ formatTimestamp(row.timestamp) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="level" label="Level" width="80">
          <template #default="{ row }">
            <el-tag
              :type="getLevelTagType(row.level)"
              size="small"
              class="level-tag"
            >
              {{ row.level.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="source" label="Source" width="120">
          <template #default="{ row }">
            <span class="source">{{ row.source }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="message" label="Message" min-width="300">
          <template #default="{ row }">
            <div class="message">
              <span class="message-text">{{ row.message }}</span>
              <el-button
                v-if="row.details"
                text
                size="small"
                @click="showLogDetails(row)"
                :aria-label="'View log details'"
              >
                <el-icon><View /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- Loading indicator for infinite scroll -->
      <div v-if="isLoadingMore" class="loading-more">
        <el-icon class="rotating"><Loading /></el-icon>
        <span>Loading more logs...</span>
      </div>
      
      <!-- No more logs indicator -->
      <div v-if="!hasMoreLogs && logs.length > 0" class="no-more-logs">
        <span>No more logs to load</span>
      </div>
    </div>
    
    <!-- Log Details Dialog -->
    <el-dialog
      v-model="detailsDialogVisible"
      title="Log Details"
      width="600px"
      :aria-label="'Log details dialog'"
    >
      <div v-if="selectedLog" class="log-details">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Timestamp">
            {{ formatTimestamp(selectedLog.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="Level">
            <el-tag :type="getLevelTagType(selectedLog.level)">
              {{ selectedLog.level.toUpperCase() }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Source">
            {{ selectedLog.source }}
          </el-descriptions-item>
          <el-descriptions-item label="Message">
            {{ selectedLog.message }}
          </el-descriptions-item>
          <el-descriptions-item label="Details" v-if="selectedLog.details">
            <pre class="details-content">{{ selectedLog.details }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, Download, Search, View, Loading
} from '@element-plus/icons-vue'

interface LogEntry {
  id: string
  timestamp: Date
  level: 'info' | 'warn' | 'error'
  source: string
  message: string
  details?: string
}

// Reactive data
const logs = ref<LogEntry[]>([])
const selectedLevel = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(50)
const isLoadingMore = ref(false)
const hasMoreLogs = ref(true)
const detailsDialogVisible = ref(false)
const selectedLog = ref<LogEntry | null>(null)

// Table ref
const logTableRef = ref()

// Computed properties
const filteredLogs = computed(() => {
  let filtered = logs.value
  
  // Filter by level
  if (selectedLevel.value) {
    filtered = filtered.filter(log => log.level === selectedLevel.value)
  }
  
  // Filter by keyword
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = filtered.filter(log => 
      log.message.toLowerCase().includes(keyword) ||
      log.source.toLowerCase().includes(keyword)
    )
  }
  
  return filtered
})

const paginatedLogs = computed(() => {
  const start = 0
  const end = currentPage.value * pageSize.value
  return filteredLogs.value.slice(start, end)
})

// Methods
const getLevelTagType = (level: string) => {
  const typeMap = {
    'info': 'info',
    'warn': 'warning',
    'error': 'danger'
  }
  return typeMap[level as keyof typeof typeMap] || 'info'
}

const formatTimestamp = (timestamp: Date) => {
  return timestamp.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const filterLogs = () => {
  currentPage.value = 1
  // Reset pagination when filters change
}

const clearFilters = () => {
  selectedLevel.value = ''
  searchKeyword.value = ''
  currentPage.value = 1
}

const handleScroll = (event: any) => {
  const { scrollTop, scrollHeight, clientHeight } = event.target
  
  // Load more logs when scrolling to bottom
  if (scrollTop + clientHeight >= scrollHeight - 10 && !isLoadingMore.value && hasMoreLogs.value) {
    loadMoreLogs()
  }
}

const loadMoreLogs = async () => {
  if (isLoadingMore.value || !hasMoreLogs.value) return
  
  isLoadingMore.value = true
  
  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Generate mock logs
    const newLogs = generateMockLogs(50, logs.value.length)
    
    if (newLogs.length === 0) {
      hasMoreLogs.value = false
    } else {
      logs.value.push(...newLogs)
      currentPage.value++
    }
  } finally {
    isLoadingMore.value = false
  }
}

const generateMockLogs = (count: number, startId: number = 0): LogEntry[] => {
  const newLogs: LogEntry[] = []
  const levels: ('info' | 'warn' | 'error')[] = ['info', 'warn', 'error']
  const sources = ['Spark', 'DataCollector', 'SentimentAnalysis', 'Database', 'FileSystem', 'API']
  
  const messages = {
    info: [
      'Task completed successfully',
      'Data processing initiated',
      'Connection established',
      'Configuration loaded',
      'Service started',
      'Cache cleared successfully'
    ],
    warn: [
      'High memory usage detected',
      'Slow query performance',
      'Deprecated API usage',
      'Configuration warning',
      'Resource limit approaching',
      'Retry attempt initiated'
    ],
    error: [
      'Database connection failed',
      'Task execution failed',
      'Invalid configuration detected',
      'Service unavailable',
      'Memory allocation failed',
      'Network timeout occurred'
    ]
  }
  
  for (let i = 0; i < count; i++) {
    const level = levels[Math.floor(Math.random() * levels.length)]
    const source = sources[Math.floor(Math.random() * sources.length)]
    const levelMessages = messages[level]
    const message = levelMessages[Math.floor(Math.random() * levelMessages.length)]
    
    newLogs.push({
      id: `log_${startId + i + 1}`,
      timestamp: new Date(Date.now() - (startId + i) * 1000),
      level,
      source,
      message,
      details: level === 'error' ? `Error details for log ${startId + i + 1}: Stack trace and additional context information.` : undefined
    })
  }
  
  return newLogs
}

const showLogDetails = (log: LogEntry) => {
  selectedLog.value = log
  detailsDialogVisible.value = true
}

const exportLogs = () => {
  if (filteredLogs.value.length === 0) {
    ElMessage.warning('No logs to export')
    return
  }
  
  // Generate log content
  const logContent = filteredLogs.value.map(log => {
    const timestamp = formatTimestamp(log.timestamp)
    const level = log.level.toUpperCase().padEnd(5)
    const source = log.source.padEnd(15)
    return `[${timestamp}] ${level} ${source} ${log.message}`
  }).join('\n')
  
  // Create blob and download
  const blob = new Blob([logContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `system_logs_${new Date().toISOString().split('T')[0]}.log`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  ElMessage.success(`Exported ${filteredLogs.value.length} log entries`)
}

// Lifecycle
onMounted(async () => {
  // Load initial logs
  const initialLogs = generateMockLogs(100)
  logs.value = initialLogs
})

onUnmounted(() => {
  // Cleanup if needed
})
</script>

<style scoped>
.system-log-viewer {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.log-filters {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

.log-content {
  position: relative;
}

.timestamp {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.level-tag {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-weight: var(--font-weight-semibold);
}

.source {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-small);
  color: var(--color-text-regular);
}

.message {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
}

.message-text {
  flex: 1;
  line-height: 1.4;
  word-break: break-word;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.no-more-logs {
  text-align: center;
  padding: var(--spacing-md);
  color: var(--color-text-placeholder);
  font-size: var(--font-size-small);
  font-style: italic;
}

.log-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.details-content {
  background: var(--color-bg-hover);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-base);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-small);
  line-height: 1.4;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Animations */
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.rotating {
  animation: rotate 2s linear infinite;
}

/* Responsive */
@media (max-width: 768px) {
  .system-log-viewer {
    padding: var(--spacing-md);
  }
  
  .log-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .log-filters .el-row {
    flex-direction: column;
  }
  
  .log-filters .el-col {
    width: 100% !important;
    margin-bottom: var(--spacing-sm);
  }
  
  .message {
    flex-direction: column;
    align-items: stretch;
  }
}

/* Accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
