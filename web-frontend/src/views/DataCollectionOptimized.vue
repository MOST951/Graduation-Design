<template>
  <div class="data-collection-optimized">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header with status -->
    <div class="collection-header">
      <div class="header-left">
        <h1 class="page-title">Data Collection</h1>
        <div class="status-indicator">
          <el-tag 
            :type="getStatusTagType()" 
            size="large"
            :aria-label="`Collection status: ${getStatusText()}`"
          >
            <el-icon v-if="isRunning" class="rotating"><Loading /></el-icon>
            {{ getStatusText() }}
          </el-tag>
        </div>
      </div>
      
      <div class="header-right">
        <div class="collection-stats">
          <span class="stat-item">
            <strong>{{ totalCollected }}</strong> collected
          </span>
          <span class="stat-item">
            <strong>{{ currentRate }}</strong> items/sec
          </span>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Left Panel: Configuration -->
        <el-col :span="8">
          <el-card shadow="hover" class="config-card">
            <template #header>
              <div class="card-header">
                <el-icon><Setting /></el-icon>
                <span>Collection Configuration</span>
              </div>
            </template>
            
            <el-form :model="config" label-position="top" size="default">
              <!-- Keywords with TagInput -->
              <el-form-item label="Keywords">
                <TagInput
                  v-model="config.keywords"
                  :placeholder="'Enter keywords, press Enter to add'"
                  :suggestions="defaultKeywords"
                  :show-suggestions="true"
                  :max-tags="10"
                  :duplicate-message="'Keyword already exists'"
                  @tag-add="handleKeywordAdd"
                  @tag-remove="handleKeywordRemove"
                />
              </el-form-item>
              
              <!-- DateTime Range Picker -->
              <el-form-item label="Time Range">
                <el-date-picker
                  v-model="config.dateRange"
                  type="datetimerange"
                  range-separator="to"
                  start-placeholder="Start time"
                  end-placeholder="End time"
                  format="YYYY-MM-DD HH:mm:ss"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  style="width: 100%"
                  :aria-label="'Select time range for data collection'"
                />
              </el-form-item>
              
              <!-- Data Sources -->
              <el-form-item label="Data Sources">
                <el-checkbox-group v-model="config.dataSources">
                  <el-checkbox 
                    v-for="source in dataSources" 
                    :key="source.value"
                    :label="source.value"
                    :aria-label="`Select ${source.label} data source`"
                  >
                    {{ source.label }}
                  </el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              
              <!-- Additional Options -->
              <el-form-item label="Hot Search">
                <el-switch 
                  v-model="config.crawlHotSearch" 
                  active-text="Crawl hot search"
                  :aria-label="'Toggle hot search crawling'"
                />
              </el-form-item>
              
              <el-form-item label="Max Count">
                <el-input-number 
                  v-model="config.maxCount" 
                  :min="100" 
                  :max="100000" 
                  :step="1000"
                  :aria-label="'Set maximum collection count'"
                />
              </el-form-item>
            </el-form>
          </el-card>
          
          <!-- Anti-Detection Settings -->
          <el-card shadow="hover" class="config-card">
            <template #header>
              <div class="card-header">
                <el-icon><Lock /></el-icon>
                <span>Anti-Detection Settings</span>
              </div>
            </template>
            
            <el-form :model="config" label-position="top" size="default">
              <el-form-item label="Request Interval (seconds)">
                <el-slider 
                  v-model="config.requestInterval" 
                  :min="1" 
                  :max="10" 
                  show-input
                  :aria-label="'Set request interval in seconds'"
                />
              </el-form-item>
              
              <el-form-item label="Proxy Pool">
                <el-switch 
                  v-model="config.useProxy" 
                  active-text="Enable proxy"
                  :aria-label="'Toggle proxy pool usage'"
                />
              </el-form-item>
              
              <el-form-item label="Random Headers">
                <el-switch 
                  v-model="config.randomHeaders" 
                  active-text="Random UA"
                  :aria-label="'Toggle random user agent headers'"
                />
              </el-form-item>
              
              <el-form-item label="Cookie Configuration">
                <el-input
                  v-model="config.cookie"
                  type="textarea"
                  :rows="3"
                  placeholder="Paste Weibo login cookies (optional)"
                  :aria-label="'Enter cookie configuration'"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
        
        <!-- Middle Panel: Progress & Statistics -->
        <el-col :span="8">
          <!-- Collection Progress -->
          <el-card shadow="hover" class="progress-card">
            <template #header>
              <div class="card-header">
                <el-icon><TrendCharts /></el-icon>
                <span>Collection Progress</span>
              </div>
            </template>
            
            <div class="progress-section">
              <el-progress
                type="dashboard"
                :percentage="progressPercentage"
                :color="progressColors"
                :width="180"
                :aria-label="`Collection progress: ${progressPercentage}%`"
              >
                <template #default="{ percentage }">
                  <span class="progress-value">{{ percentage }}%</span>
                  <span class="progress-label">Complete</span>
                </template>
              </el-progress>
              
              <div class="progress-info">
                <div class="info-item">
                  <span class="info-label">Collected:</span>
                  <span class="info-value">{{ totalCollected }} items</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Rate:</span>
                  <span class="info-value">{{ currentRate }} items/sec</span>
                </div>
                <div class="info-item">
                  <span class="info-label">ETA:</span>
                  <span class="info-value">{{ estimatedTimeRemaining }}</span>
                </div>
              </div>
            </div>
          </el-card>
          
          <!-- Control Buttons -->
          <el-card shadow="hover" class="control-card">
            <div class="control-buttons">
              <el-button-group>
                <el-button
                  type="primary"
                  :icon="VideoPlay"
                  @click="startCollection"
                  :loading="isLoading"
                  :disabled="isRunning"
                  :aria-label="'Start data collection'"
                  size="large"
                >
                  Start
                </el-button>
                <el-button
                  type="warning"
                  :icon="VideoPause"
                  @click="pauseCollection"
                  :disabled="!isRunning || isPaused"
                  :aria-label="'Pause data collection'"
                  size="large"
                >
                  Pause
                </el-button>
                <el-button
                  type="danger"
                  :icon="VideoStop"
                  @click="stopCollection"
                  :disabled="!isRunning"
                  :aria-label="'Stop data collection'"
                  size="large"
                >
                  Stop
                </el-button>
              </el-button-group>
            </div>
          </el-card>
          
          <!-- Collection Rate Chart -->
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <el-icon><DataAnalysis /></el-icon>
                <span>Collection Rate</span>
                <el-tag type="primary" size="small">{{ currentRate }} items/s</el-tag>
              </div>
            </template>
            <div ref="rateChartRef" class="chart-container"></div>
          </el-card>
          
          <!-- Deduplication Stats -->
          <el-card shadow="hover" class="dedup-card">
            <template #header>
              <div class="card-header">
                <el-icon><Filter /></el-icon>
                <span>Deduplication</span>
                <el-switch 
                  v-model="config.deduplicate" 
                  active-text="Enable"
                  size="small"
                  :aria-label="'Toggle deduplication'"
                />
              </div>
            </template>
            
            <div class="dedup-stats">
              <div class="dedup-item">
                <div class="dedup-value total">{{ dedupStats.totalFetched }}</div>
                <div class="dedup-label">Total Fetched</div>
              </div>
              <div class="dedup-item">
                <div class="dedup-value dup">{{ dedupStats.duplicates }}</div>
                <div class="dedup-label">Duplicates</div>
              </div>
              <div class="dedup-item">
                <div class="dedup-value unique">{{ dedupStats.unique }}</div>
                <div class="dedup-label">Unique</div>
              </div>
              <div class="dedup-item">
                <div class="dedup-value rate">{{ dedupStats.dedupRate }}%</div>
                <div class="dedup-label">Dedup Rate</div>
              </div>
            </div>
            
            <el-progress 
              :percentage="dedupStats.dedupRate" 
              :stroke-width="6" 
              :color="WARNING"
              class="dedup-progress"
            />
          </el-card>
        </el-col>
        
        <!-- Right Panel: Logs & History -->
        <el-col :span="8">
          <!-- Real-time Logs -->
          <el-card shadow="hover" class="log-card">
            <template #header>
              <div class="card-header">
                <el-icon><Document /></el-icon>
                <span>Real-time Logs</span>
                <el-tag :type="getLogLevelTagType()" size="small">
                  {{ logs.length }} entries
                </el-tag>
              </div>
            </template>
            
            <VirtualLogList
              :logs="logs"
              :height="400"
              :item-height="24"
              @clear="clearLogs"
              @scroll="handleLogScroll"
              ref="logListRef"
            />
          </el-card>
          
          <!-- Collection History -->
          <el-card shadow="hover" class="history-card">
            <template #header>
              <div class="card-header">
                <el-icon><Clock /></el-icon>
                <span>Collection History</span>
                <el-button
                  text
                  size="small"
                  @click="refreshHistory"
                  :loading="isHistoryLoading"
                  :aria-label="'Refresh collection history'"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </div>
            </template>
            
            <el-table
              :data="collectionHistory"
              height="300"
              size="small"
              :default-sort="{ prop: 'createdAt', order: 'descending' }"
              :aria-label="'Collection history table'"
            >
              <el-table-column 
                prop="batchId" 
                label="Batch ID" 
                width="80"
                sortable
              />
              <el-table-column 
                prop="keywords" 
                label="Keywords" 
                min-width="120"
                show-overflow-tooltip
              >
                <template #default="{ row }">
                  <el-tag 
                    v-for="keyword in row.keywords.slice(0, 2)" 
                    :key="keyword"
                    size="small"
                    class="keyword-tag"
                  >
                    {{ keyword }}
                  </el-tag>
                  <span v-if="row.keywords.length > 2" class="more-keywords">
                    +{{ row.keywords.length - 2 }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column 
                prop="createdAt" 
                label="Time" 
                width="120"
                sortable
              >
                <template #default="{ row }">
                  {{ formatDateTime(row.createdAt) }}
                </template>
              </el-table-column>
              <el-table-column 
                prop="status" 
                label="Status" 
                width="80"
              >
                <template #default="{ row }">
                  <el-tag 
                    :type="getStatusType(row.status)" 
                    size="small"
                    :aria-label="`Status: ${row.status}`"
                  >
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column 
                label="Actions" 
                width="120"
                fixed="right"
              >
                <template #default="{ row }">
                  <el-button
                    text
                    size="small"
                    @click="viewDetails(row)"
                    :aria-label="'View collection details'"
                  >
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button
                    v-if="row.status === 'failed'"
                    text
                    size="small"
                    type="warning"
                    @click="retryCollection(row)"
                    :aria-label="'Retry failed collection'"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  Setting, Lock, TrendCharts, DataAnalysis, Filter, Document, Clock,
  VideoPlay, VideoPause, VideoStop, Loading, View, Refresh
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import TagInput from '@/components/common/TagInput.vue'
import VirtualLogList from '@/components/common/VirtualLogList.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface CollectionConfig {
  keywords: string[]
  dateRange: [string, string] | null
  dataSources: string[]
  crawlHotSearch: boolean
  maxCount: number
  requestInterval: number
  useProxy: boolean
  randomHeaders: boolean
  cookie: string
  deduplicate: boolean
}

interface LogItem {
  timestamp: number
  level: 'info' | 'warning' | 'error'
  message: string
  details?: any
  highlighted?: boolean
}

interface CollectionHistory {
  batchId: string
  keywords: string[]
  createdAt: Date
  status: 'running' | 'completed' | 'failed' | 'paused'
  collectedCount: number
  errorCount: number
}

interface DedupStats {
  totalFetched: number
  duplicates: number
  unique: number
  dedupRate: number
}

// Reactive data
const config = ref<CollectionConfig>({
  keywords: [],
  dateRange: null,
  dataSources: ['weibo'],
  crawlHotSearch: true,
  maxCount: 1000,
  requestInterval: 2,
  useProxy: false,
  randomHeaders: true,
  cookie: '',
  deduplicate: true
})

const logs = ref<LogItem[]>([])
const collectionHistory = ref<CollectionHistory[]>([])
const isRunning = ref(false)
const isPaused = ref(false)
const isLoading = ref(false)
const isHistoryLoading = ref(false)
const totalCollected = ref(0)
const currentRate = ref(0)
const progressPercentage = ref(0)
const estimatedTimeRemaining = ref('N/A')

const dedupStats = ref<DedupStats>({
  totalFetched: 0,
  duplicates: 0,
  unique: 0,
  dedupRate: 0
})

// Chart ref
const rateChartRef = ref<HTMLElement>()
const logListRef = ref()

// Constants
const defaultKeywords = ref([
  'AI', 'Machine Learning', 'Vue.js', 'React', 'TypeScript',
  'Python', 'JavaScript', 'Frontend', 'Backend', 'DevOps'
])

const dataSources = ref([
  { label: 'Weibo', value: 'weibo' },
  { label: 'Douyin', value: 'douyin' },
  { label: 'Kuaishou', value: 'kuaishou' }
])

const progressColors = ref([
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 }
])

// Computed properties
const getStatusText = () => {
  if (isPaused.value) return 'Paused'
  if (isRunning.value) return 'Running'
  return 'Idle'
}

const getStatusTagType = () => {
  if (isPaused.value) return 'warning'
  if (isRunning.value) return 'success'
  return 'info'
}

const getLogLevelTagType = () => {
  const errorCount = logs.value.filter(log => log.level === 'error').length
  if (errorCount > 0) return 'danger'
  const warningCount = logs.value.filter(log => log.level === 'warning').length
  if (warningCount > 0) return 'warning'
  return 'info'
}

// Methods
const startCollection = async () => {
  if (config.value.keywords.length === 0) {
    ElMessage.warning('Please add at least one keyword')
    return
  }
  
  if (!config.value.dateRange) {
    ElMessage.warning('Please select a time range')
    return
  }
  
  isLoading.value = true
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        isRunning.value = true
        isPaused.value = false
        addLog('info', 'Collection started successfully')
        addLog('info', `Keywords: ${config.value.keywords.join(', ')}`)
        addLog('info', `Time range: ${config.value.dateRange[0]} to ${config.value.dateRange[1]}`)
        
        // Start simulation
        startSimulation()
      },
      'Data Collection Start',
      { showLoading: false }
    )
  } finally {
    isLoading.value = false
  }
}

const pauseCollection = async () => {
  try {
    await withErrorHandling(
      async () => {
        isPaused.value = true
        addLog('info', 'Collection paused')
      },
      'Collection Pause',
      { showLoading: false }
    )
  } catch (error) {
    console.error('Failed to pause collection:', error)
  }
}

const stopCollection = async () => {
  try {
    await withErrorHandling(
      async () => {
        isRunning.value = false
        isPaused.value = false
        addLog('info', 'Collection stopped')
        
        // Show success notification
        ElNotification({
          title: 'Collection Completed',
          message: `Successfully collected ${totalCollected.value} items`,
          type: 'success',
          duration: 5000
        })
        
        // Refresh history
        await refreshHistory()
      },
      'Collection Stop',
      { showLoading: false }
    )
  } catch (error) {
    console.error('Failed to stop collection:', error)
  }
}

const addLog = (level: 'info' | 'warning' | 'error', message: string, details?: any) => {
  const log: LogItem = {
    timestamp: Date.now(),
    level,
    message,
    details,
    highlighted: level === 'error'
  }
  
  logs.value.unshift(log)
  
  // Keep only last 1000 logs
  if (logs.value.length > 1000) {
    logs.value = logs.value.slice(0, 1000)
  }
  
  // Announce errors for accessibility
  if (level === 'error') {
    AccessibilityHelper.announce(`Error: ${message}`, 'assertive')
  }
}

const clearLogs = () => {
  logs.value = []
  addLog('info', 'Logs cleared')
}

const handleLogScroll = (scrollTop: number) => {
  // Handle scroll if needed
}

const handleKeywordAdd = (keyword: string) => {
  addLog('info', `Keyword added: ${keyword}`)
}

const handleKeywordRemove = (keyword: string, index: number) => {
  addLog('info', `Keyword removed: ${keyword}`)
}

const refreshHistory = async () => {
  isHistoryLoading.value = true
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Generate mock history
        collectionHistory.value = [
          {
            batchId: 'B001',
            keywords: ['AI', 'Machine Learning'],
            createdAt: new Date(Date.now() - 86400000),
            status: 'completed',
            collectedCount: 1250,
            errorCount: 0
          },
          {
            batchId: 'B002',
            keywords: ['Vue.js', 'React'],
            createdAt: new Date(Date.now() - 172800000),
            status: 'failed',
            collectedCount: 890,
            errorCount: 45
          },
          {
            batchId: 'B003',
            keywords: ['Python', 'JavaScript'],
            createdAt: new Date(Date.now() - 259200000),
            status: 'completed',
            collectedCount: 2100,
            errorCount: 12
          }
        ]
      },
      'Refresh Collection History',
      { showLoading: false }
    )
  } finally {
    isHistoryLoading.value = false
  }
}

const viewDetails = (record: CollectionHistory) => {
  ElMessage.info(`Viewing details for batch ${record.batchId}`)
  // Implement detail view logic
}

const retryCollection = async (record: CollectionHistory) => {
  try {
    await withErrorHandling(
      async () => {
        // Load failed collection config
        config.value.keywords = [...record.keywords]
        addLog('info', `Retrying collection for batch ${record.batchId}`)
        
        // Start collection
        await startCollection()
      },
      'Retry Collection',
      { showLoading: false }
    )
  } catch (error) {
    console.error('Failed to retry collection:', error)
  }
}

const formatDateTime = (date: Date) => {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'running': 'success',
    'completed': 'success',
    'failed': 'danger',
    'paused': 'warning'
  }
  return statusMap[status] || 'info'
}

// Simulation
let simulationInterval: NodeJS.Timeout | null = null

const startSimulation = () => {
  let progress = 0
  let collected = 0
  let rate = 0
  
  simulationInterval = setInterval(() => {
    if (!isRunning.value || isPaused.value) return
    
    // Update progress
    progress += Math.random() * 2
    if (progress > 100) progress = 100
    
    progressPercentage.value = Math.round(progress)
    
    // Update collected count
    const increment = Math.floor(Math.random() * 15 + 5)
    collected += increment
    totalCollected.value = collected
    
    // Update rate
    rate = Math.floor(Math.random() * 10 + 5)
    currentRate.value = rate
    
    // Update dedup stats
    dedupStats.value.totalFetched = collected
    dedupStats.value.duplicates = Math.floor(collected * 0.15)
    dedupStats.value.unique = collected - dedupStats.value.duplicates
    dedupStats.value.dedupRate = Math.round((dedupStats.value.duplicates / collected) * 100)
    
    // Add random logs
    if (Math.random() > 0.8) {
      const logTypes = ['info', 'info', 'warning']
      const messages = [
        `Fetching data for ${config.value.keywords[Math.floor(Math.random() * config.value.keywords.length)]}`,
        `Processing batch ${Math.floor(Math.random() * 100)}`,
        'Rate limit reached, slowing down',
        'Proxy rotation successful',
        'Cookie validation passed'
      ]
      
      addLog(
        logTypes[Math.floor(Math.random() * logTypes.length)] as 'info' | 'warning',
        messages[Math.floor(Math.random() * messages.length)]
      )
    }
    
    // Check for completion
    if (progress >= 100) {
      stopCollection()
    }
    
    // Update ETA
    if (progress > 0 && progress < 100) {
      const remaining = (100 - progress) / (progress / (collected / rate))
      estimatedTimeRemaining.value = `${Math.round(remaining)}s`
    }
  }, 1000)
}

// Chart initialization
const initRateChart = () => {
  if (!rateChartRef.value) return
  
  const chart = echarts.init(rateChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c} items/s'
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 10 }, (_, i) => `${i}s ago`),
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10
      }
    },
    series: [{
      data: Array.from({ length: 10 }, () => Math.floor(Math.random() * 20 + 5)),
      type: 'line',
      smooth: true,
      areaStyle: {
        color: 'rgba(22, 93, 255, 0.2)'
      },
      lineStyle: {
        color: '#165DFF'
      },
      itemStyle: {
        color: '#165DFF'
      }
    }]
  }
  
  chart.setOption(option)
  
  // Handle resize
  const handleResize = () => chart.resize()
  window.addEventListener('resize', handleResize)
  
  // Cleanup
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    chart.dispose()
  })
}

// Lifecycle
onMounted(async () => {
  // Initialize chart
  nextTick(() => {
    initRateChart()
  })
  
  // Load initial data
  await refreshHistory()
  
  // Add initial log
  addLog('info', 'Data collection module initialized')
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})

onUnmounted(() => {
  if (simulationInterval) {
    clearInterval(simulationInterval)
  }
})
</script>

<style scoped>
.data-collection-optimized {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.collection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-extra-large);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.status-indicator {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.collection-stats {
  display: flex;
  gap: var(--spacing-lg);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.stat-item strong {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.main-content {
  margin-top: var(--spacing-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-semibold);
}

.config-card,
.progress-card,
.control-card,
.chart-card,
.dedup-card,
.log-card,
.history-card {
  margin-bottom: var(--spacing-lg);
}

.progress-section {
  text-align: center;
}

.progress-value {
  display: block;
  font-size: var(--font-size-extra-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.progress-label {
  display: block;
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.progress-info {
  margin-top: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-small);
}

.info-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.info-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.control-buttons {
  display: flex;
  justify-content: center;
}

.chart-container {
  height: 200px;
}

.dedup-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.dedup-item {
  text-align: center;
}

.dedup-value {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-xs);
}

.dedup-value.total {
  color: var(--color-info);
}

.dedup-value.dup {
  color: var(--color-warning);
}

.dedup-value.unique {
  color: var(--color-success);
}

.dedup-value.rate {
  color: var(--color-primary);
}

.dedup-label {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.dedup-progress {
  margin-top: var(--spacing-md);
}

.keyword-tag {
  margin-right: var(--spacing-xxs);
}

.more-keywords {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
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

/* Responsive design */
@media (max-width: 1280px) {
  .collection-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .data-collection-optimized {
    padding: var(--spacing-md);
  }
  
  .collection-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .collection-stats {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .dedup-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .control-buttons .el-button-group {
    display: flex;
    flex-direction: column;
    width: 100%;
  }
  
  .control-buttons .el-button {
    width: 100%;
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .collection-header,
  .config-card,
  .progress-card,
  .control-card,
  .chart-card,
  .dedup-card,
  .log-card,
  .history-card {
    border-width: 2px;
  }
}
</style>
