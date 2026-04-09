<template>
  <div class="realtime-monitor">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header with connection status -->
    <div class="monitor-header">
      <div class="header-left">
        <h1 class="page-title">Real-time Public Opinion Monitor</h1>
        <div class="connection-status-wrapper">
          <ConnectionStatus
            :is-connected="isConnected"
            :is-connecting="isConnecting"
            :has-error="hasError"
            :protocol="connectionProtocol"
            :endpoint="connectionEndpoint"
            :connected-at="connectedAt"
            :last-message="lastMessage"
            :reconnect-attempts="reconnectAttempts"
            :show-details="false"
            :show-actions="false"
            @connect="startMonitoring"
            @disconnect="stopMonitoring"
            @cancel="cancelConnection"
          />
        </div>
      </div>
      
      <div class="header-right">
        <div class="monitor-stats">
          <span class="stat-item">
            <strong>{{ weiboStream.length }}</strong> items
          </span>
          <span class="stat-item">
            <strong>{{ negativeRatio.toFixed(1) }}%</strong> negative
          </span>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Left Panel: Configuration -->
        <el-col :span="8">
          <!-- Keyword Subscription -->
          <el-card shadow="hover" class="subscription-card">
            <KeywordSubscription
              :keywords="keywords"
              @add="handleKeywordAdd"
              @remove="handleKeywordRemove"
              @toggle="handleKeywordToggle"
              @clear="handleKeywordsClear"
            />
          </el-card>
          
          <!-- Warning Threshold -->
          <el-card shadow="hover" class="threshold-card">
            <template #header>
              <div class="card-header">
                <el-icon><Warning /></el-icon>
                <span>Warning Threshold</span>
              </div>
            </template>
            
            <div class="threshold-content">
              <div class="threshold-display">
                <div class="current-value">
                  <span class="value-label">Current Negative Ratio:</span>
                  <span class="value-number" :class="{ warning: negativeRatio >= warningThreshold }">
                    {{ negativeRatio.toFixed(1) }}%
                  </span>
                </div>
                
                <div class="threshold-indicator">
                  <div class="indicator-bar">
                    <div 
                      class="indicator-fill" 
                      :style="{ width: `${negativeRatio}%` }"
                      :class="{ warning: negativeRatio >= warningThreshold }"
                    ></div>
                    <div 
                      class="threshold-line"
                      :style="{ left: `${warningThreshold}%` }"
                    ></div>
                  </div>
                  <div class="threshold-label">
                    Threshold: {{ warningThreshold }}%
                  </div>
                </div>
              </div>
              
              <div class="threshold-control">
                <el-slider
                  v-model="warningThreshold"
                  :min="0"
                  :max="100"
                  :step="1"
                  :format-tooltip="(val) => `${val}%`"
                  @change="handleThresholdChange"
                  :aria-label="'Adjust warning threshold'"
                />
              </div>
              
              <div class="threshold-actions">
                <el-button-group size="small">
                  <el-button @click="resetThreshold" :aria-label="'Reset threshold to default'">
                    <el-icon><RefreshRight /></el-icon>
                    Reset
                  </el-button>
                  <el-button @click="testWarning" :aria-label="'Test warning notification'">
                    <el-icon><Bell /></el-icon>
                    Test
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </el-card>
          
          <!-- Control Panel -->
          <el-card shadow="hover" class="control-card">
            <template #header>
              <div class="card-header">
                <el-icon><Operation /></el-icon>
                <span>Monitor Control</span>
              </div>
            </template>
            
            <div class="control-content">
              <div class="control-buttons">
                <el-button
                  type="primary"
                  size="large"
                  :icon="VideoPlay"
                  @click="startMonitoring"
                  :loading="isConnecting"
                  :disabled="isConnected || keywords.length === 0"
                  :aria-label="'Start real-time monitoring'"
                  class="control-button"
                >
                  Start Monitoring
                </el-button>
                
                <el-button
                  type="danger"
                  size="large"
                  :icon="VideoStop"
                  @click="stopMonitoring"
                  :disabled="!isConnected"
                  :aria-label="'Stop real-time monitoring'"
                  class="control-button"
                >
                  Stop Monitoring
                </el-button>
              </div>
              
              <div class="additional-controls">
                <el-switch
                  v-model="autoScroll"
                  active-text="Auto Scroll"
                  :aria-label="'Toggle auto scroll'"
                />
                
                <el-switch
                  v-model="soundEnabled"
                  active-text="Sound Alert"
                  :aria-label="'Toggle sound alert'"
                />
              </div>
              
              <div class="dev-controls" v-if="isDevelopment">
                <el-divider>Development Tools</el-divider>
                <el-button
                  type="warning"
                  :icon="MagicStick"
                  @click="toggleMockDataStream"
                  :aria-label="'Toggle mock data stream'"
                >
                  {{ mockDataStream ? 'Stop' : 'Start' }} Mock Data
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- Middle Panel: Real-time Stream -->
        <el-col :span="10">
          <el-card shadow="hover" class="stream-card">
            <template #header>
              <div class="card-header">
                <el-icon><ChatLineRound /></el-icon>
                <span>Real-time Weibo Stream</span>
                <div class="stream-controls">
                  <el-button
                    text
                    size="small"
                    @click="clearStream"
                    :disabled="weiboStream.length === 0"
                    :aria-label="'Clear stream'"
                  >
                    <el-icon><Delete /></el-icon>
                    Clear
                  </el-button>
                  <el-button
                    text
                    size="small"
                    @click="toggleAutoScroll"
                    :aria-label="'Toggle auto scroll'"
                  >
                    <el-icon><ArrowDown /></el-icon>
                    {{ autoScroll ? 'Pause' : 'Resume' }} Scroll
                  </el-button>
                </div>
              </div>
            </template>
            
            <div class="stream-content">
              <el-table
                :data="weiboStream"
                height="500"
                max-height="500"
                size="small"
                :show-header="true"
                :row-class-name="getRowClassName"
                ref="streamTableRef"
                :aria-label="'Real-time weibo stream table'"
              >
                <el-table-column type="index" label="#" width="50" />
                
                <el-table-column prop="content" label="Content" min-width="200">
                  <template #default="{ row }">
                    <div class="weibo-content">
                      <div class="content-text">{{ row.content }}</div>
                      <div class="content-meta">
                        <span class="meta-item">
                          <el-icon><User /></el-icon>
                          {{ row.author }}
                        </span>
                        <span class="meta-item">
                          <el-icon><Clock /></el-icon>
                          {{ formatTime(row.timestamp) }}
                        </span>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                
                <el-table-column prop="sentiment" label="Sentiment" width="100">
                  <template #default="{ row }">
                    <el-tag
                      :type="getSentimentTagType(row.sentiment)"
                      size="small"
                      :aria-label="`Sentiment: ${row.sentiment}`"
                    >
                      {{ row.sentiment }}
                    </el-tag>
                  </template>
                </el-table-column>
                
                <el-table-column prop="score" label="Score" width="80">
                  <template #default="{ row }">
                    <span :style="{ color: getScoreColor(row.sentiment) }">
                      {{ row.score.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                
                <el-table-column prop="keywords" label="Keywords" width="120">
                  <template #default="{ row }">
                    <div class="keyword-tags">
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
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-col>
        
        <!-- Right Panel: Visualizations -->
        <el-col :span="6">
          <!-- Sentiment Ratio Chart -->
          <el-card shadow="hover" class="ratio-card">
            <template #header>
              <div class="card-header">
                <el-icon><PieChart /></el-icon>
                <span>Sentiment Ratio</span>
                <el-tag type="info" size="small">Live</el-tag>
              </div>
            </template>
            
            <div class="ratio-content">
              <div ref="ratioChartRef" class="ratio-chart"></div>
              <div class="ratio-stats">
                <div class="stat-item">
                  <div class="stat-dot positive"></div>
                  <span class="stat-label">Positive:</span>
                  <span class="stat-value">{{ sentimentStats.positive }}%</span>
                </div>
                <div class="stat-item">
                  <div class="stat-dot neutral"></div>
                  <span class="stat-label">Neutral:</span>
                  <span class="stat-value">{{ sentimentStats.neutral }}%</span>
                </div>
                <div class="stat-item">
                  <div class="stat-dot negative"></div>
                  <span class="stat-label">Negative:</span>
                  <span class="stat-value">{{ sentimentStats.negative }}%</span>
                </div>
              </div>
            </div>
          </el-card>
          
          <!-- Sentiment Trend Chart -->
          <el-card shadow="hover" class="trend-card">
            <template #header>
              <div class="card-header">
                <el-icon><LineChart /></el-icon>
                <span>Sentiment Trend</span>
                <el-tag type="info" size="small">Last 50</el-tag>
              </div>
            </template>
            
            <div class="trend-content">
              <div ref="trendChartRef" class="trend-chart"></div>
            </div>
          </el-card>
          
          <!-- Warning Records -->
          <el-card shadow="hover" class="warnings-card">
            <template #header>
              <div class="card-header">
                <el-icon><Bell /></el-icon>
                <span>Warning Records</span>
                <el-button
                  text
                  size="small"
                  @click="clearWarnings"
                  :disabled="warningRecords.length === 0"
                  :aria-label="'Clear warning records'"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </template>
            
            <div class="warnings-content">
              <div class="warnings-list">
                <div
                  v-for="warning in warningRecords.slice(0, 5)"
                  :key="warning.id"
                  class="warning-item"
                >
                  <div class="warning-time">{{ formatTime(warning.timestamp) }}</div>
                  <div class="warning-message">{{ warning.message }}</div>
                </div>
              </div>
              
              <div v-if="warningRecords.length === 0" class="no-warnings">
                <el-icon><SuccessFilled /></el-icon>
                <span>No warnings triggered</span>
              </div>
            </div>
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
  Warning, Operation, VideoPlay, VideoStop, ChatLineRound, Delete, ArrowDown,
  User, Clock, PieChart, LineChart, Bell, RefreshRight, MagicStick,
  SuccessFilled
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import KeywordSubscription from '@/components/common/KeywordSubscription.vue'
import ConnectionStatus from '@/components/common/ConnectionStatus.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface Keyword {
  id: string
  text: string
  active: boolean
  matchCount: number
  lastMatch: Date
}

interface WeiboItem {
  id: string
  content: string
  author: string
  timestamp: Date
  sentiment: 'positive' | 'negative' | 'neutral'
  score: number
  keywords: string[]
}

interface WarningRecord {
  id: string
  timestamp: Date
  message: string
  negativeRatio: number
}

// Reactive data
const keywords = ref<Keyword[]>([])
const warningThreshold = ref(30)
const weiboStream = ref<WeiboItem[]>([])
const warningRecords = ref<WarningRecord[]>([])
const autoScroll = ref(true)
const soundEnabled = ref(false)
const isDevelopment = ref(import.meta.env.DEV)

// Connection state
const isConnected = ref(false)
const isConnecting = ref(false)
const hasError = ref(false)
const connectionProtocol = ref('sse')
const connectionEndpoint = ref('http://localhost:8080/stream/sentiment')
const connectedAt = ref<Date | null>(null)
const lastMessage = ref<Date | null>(null)
const reconnectAttempts = ref(0)

// Mock data stream
const mockDataStream = ref(false)
let mockDataInterval: NodeJS.Timeout | null = null

// Chart refs
const ratioChartRef = ref()
const trendChartRef = ref()
const streamTableRef = ref()

// Timers
let ratioChartTimer: NodeJS.Timeout | null = null
let trendChartTimer: NodeJS.Timeout | null = null
let autoScrollTimer: NodeJS.Timeout | null = null

// Computed properties
const negativeRatio = computed(() => {
  if (weiboStream.value.length === 0) return 0
  
  const negativeCount = weiboStream.value.filter(item => item.sentiment === 'negative').length
  return (negativeCount / weiboStream.value.length) * 100
})

const sentimentStats = computed(() => {
  if (weiboStream.value.length === 0) {
    return { positive: 0, neutral: 0, negative: 0 }
  }
  
  const counts = weiboStream.value.reduce((acc, item) => {
    acc[item.sentiment]++
    return acc
  }, { positive: 0, negative: 0, neutral: 0 })
  
  const total = weiboStream.value.length
  return {
    positive: Math.round((counts.positive / total) * 100),
    negative: Math.round((counts.negative / total) * 100),
    neutral: Math.round((counts.neutral / total) * 100)
  }
})

// Methods
const getSentimentTagType = (sentiment: string) => {
  const typeMap = {
    'positive': 'success',
    'negative': 'danger',
    'neutral': 'warning'
  }
  return typeMap[sentiment as keyof typeof typeMap] || 'info'
}

const getScoreColor = (sentiment: string) => {
  const colorMap = {
    'positive': 'var(--color-success)',
    'negative': 'var(--color-danger)',
    'neutral': 'var(--color-warning)'
  }
  return colorMap[sentiment as keyof typeof colorMap] || 'var(--color-info)'
}

const getRowClassName = ({ row }: { row: WeiboItem }) => {
  return `sentiment-${row.sentiment}`
}

const formatTime = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

// Keyword management
const handleKeywordAdd = (keyword: Keyword) => {
  keywords.value.push(keyword)
  ElMessage.success(`Added keyword: ${keyword.text}`)
}

const handleKeywordRemove = (index: number) => {
  const keyword = keywords.value[index]
  keywords.value.splice(index, 1)
  ElMessage.info(`Removed keyword: ${keyword.text}`)
}

const handleKeywordToggle = (keyword: Keyword) => {
  const index = keywords.value.findIndex(kw => kw.id === keyword.id)
  if (index !== -1) {
    keywords.value[index] = { ...keyword }
  }
}

const handleKeywordsClear = () => {
  keywords.value = []
  ElMessage.success('Cleared all keywords')
}

// Threshold management
const handleThresholdChange = (value: number) => {
  ElMessage.info(`Warning threshold set to ${value}%`)
}

const resetThreshold = () => {
  warningThreshold.value = 30
  ElMessage.success('Warning threshold reset to 30%')
}

const testWarning = () => {
  triggerWarning(35, 'Test warning triggered manually')
}

// Monitoring control
const startMonitoring = async () => {
  if (keywords.value.length === 0) {
    ElMessage.warning('Please add at least one keyword to monitor')
    return
  }
  
  isConnecting.value = true
  hasError.value = false
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate connection
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        if (mockDataStream.value) {
          startMockDataStream()
        } else {
          // Connect to real SSE endpoint
          connectToSSE()
        }
        
        isConnected.value = true
        isConnecting.value = false
        connectedAt.value = new Date()
        reconnectAttempts.value = 0
        
        ElMessage.success('Monitoring started successfully')
        
        // Start chart updates
        startChartUpdates()
        
        // Start auto-scroll
        startAutoScroll()
      },
      'Start Monitoring',
      { showLoading: false }
    )
  } catch (error) {
    isConnecting.value = false
    hasError.value = true
    ElMessage.error('Failed to start monitoring')
  }
}

const stopMonitoring = () => {
  isConnected.value = false
  isConnecting.value = false
  hasError.value = false
  
  // Stop mock data stream
  if (mockDataInterval) {
    clearInterval(mockDataInterval)
    mockDataInterval = null
  }
  
  // Stop chart updates
  stopChartUpdates()
  
  // Stop auto-scroll
  stopAutoScroll()
  
  ElMessage.info('Monitoring stopped')
}

const cancelConnection = () => {
  isConnecting.value = false
  ElMessage.info('Connection cancelled')
}

// SSE connection
const connectToSSE = () => {
  const eventSource = new EventSource(connectionEndpoint.value)
  
  eventSource.onopen = () => {
    console.log('SSE connection opened')
  }
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleStreamData(data)
    } catch (error) {
      console.error('Failed to parse SSE data:', error)
    }
  }
  
  eventSource.onerror = () => {
    console.error('SSE connection error')
    hasError.value = true
    isConnected.value = false
    
    // Auto-reconnect with exponential backoff
    scheduleReconnect()
  }
  
  // Store event source for cleanup
  ;(window as any).eventSource = eventSource
}

const scheduleReconnect = () => {
  if (isConnected.value) return
  
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
  reconnectAttempts.value++
  
  setTimeout(() => {
    if (!isConnected.value) {
      startMonitoring()
    }
  }, delay)
}

// Mock data stream
const startMockDataStream = () => {
  mockDataStream.value = true
  
  mockDataInterval = setInterval(() => {
    if (!isConnected.value) return
    
    const mockItem = generateMockWeiboItem()
    handleStreamData(mockItem)
  }, 1000 + Math.random() * 2000) // Random interval between 1-3 seconds
}

const toggleMockDataStream = () => {
  if (mockDataStream.value) {
    if (mockDataInterval) {
      clearInterval(mockDataInterval)
      mockDataInterval = null
    }
    mockDataStream.value = false
    ElMessage.info('Mock data stream stopped')
  } else {
    startMockDataStream()
    ElMessage.info('Mock data stream started')
  }
}

const generateMockWeiboItem = (): WeiboItem => {
  const sentiments: ('positive' | 'negative' | 'neutral')[] = ['positive', 'negative', 'neutral']
  const contents = [
    'This is amazing! I love it so much.',
    'Terrible experience, very disappointed.',
    'It\'s okay, nothing special.',
    'Great product, highly recommended!',
    'Not worth the money, poor quality.',
    'Average performance, meets expectations.'
  ]
  
  const sentiment = sentiments[Math.floor(Math.random() * sentiments.length)]
  const score = sentiment === 'positive' ? 0.8 + Math.random() * 0.2 :
                 sentiment === 'negative' ? -0.8 - Math.random() * 0.2 :
                 Math.random() * 0.4 - 0.2
  
  return {
    id: `weibo_${Date.now()}_${Math.random()}`,
    content: contents[Math.floor(Math.random() * contents.length)],
    author: `user_${Math.floor(Math.random() * 1000)}`,
    timestamp: new Date(),
    sentiment,
    score,
    keywords: keywords.value
      .filter(kw => kw.active)
      .filter(() => Math.random() > 0.5)
      .map(kw => kw.text)
      .slice(0, 3)
  }
}

// Stream data handling
const handleStreamData = (data: WeiboItem) => {
  // Add to stream
  weiboStream.value.unshift(data)
  
  // Limit memory usage (max 200 items)
  if (weiboStream.value.length > 200) {
    weiboStream.value = weiboStream.value.slice(0, 200)
  }
  
  // Update keyword match counts
  updateKeywordMatches(data)
  
  // Check for warning
  checkWarningThreshold()
  
  // Update last message time
  lastMessage.value = new Date()
}

const updateKeywordMatches = (item: WeiboItem) => {
  keywords.value.forEach(keyword => {
    if (keyword.active && item.keywords.includes(keyword.text)) {
      keyword.matchCount++
      keyword.lastMatch = new Date()
    }
  })
}

const checkWarningThreshold = () => {
  if (negativeRatio.value >= warningThreshold.value) {
    triggerWarning(negativeRatio.value, `Negative sentiment ratio reached ${negativeRatio.value.toFixed(1)}%`)
  }
}

const triggerWarning = (ratio: number, message: string) => {
  // Add warning record
  const warning: WarningRecord = {
    id: `warning_${Date.now()}`,
    timestamp: new Date(),
    message,
    negativeRatio: ratio
  }
  
  warningRecords.value.unshift(warning)
  
  // Keep only last 50 warnings
  if (warningRecords.value.length > 50) {
    warningRecords.value = warningRecords.value.slice(0, 50)
  }
  
  // Show notification
  ElNotification({
    title: 'Sentiment Warning',
    message,
    type: 'warning',
    duration: 5000,
    position: 'top-right'
  })
  
  // Play sound if enabled
  if (soundEnabled.value) {
    playWarningSound()
  }
}

const playWarningSound = () => {
  // Simple beep sound
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
  const oscillator = audioContext.createOscillator()
  const gainNode = audioContext.createGain()
  
  oscillator.connect(gainNode)
  gainNode.connect(audioContext.destination)
  
  oscillator.frequency.value = 800
  oscillator.type = 'sine'
  gainNode.gain.value = 0.1
  
  oscillator.start()
  oscillator.stop(audioContext.currentTime + 0.2)
}

// Chart updates
const startChartUpdates = () => {
  // Update ratio chart every second
  ratioChartTimer = setInterval(() => {
    updateRatioChart()
  }, 1000)
  
  // Update trend chart every 2 seconds
  trendChartTimer = setInterval(() => {
    updateTrendChart()
  }, 2000)
}

const stopChartUpdates = () => {
  if (ratioChartTimer) {
    clearInterval(ratioChartTimer)
    ratioChartTimer = null
  }
  
  if (trendChartTimer) {
    clearInterval(trendChartTimer)
    trendChartTimer = null
  }
}

const updateRatioChart = () => {
  if (!ratioChartRef.value) return
  
  const chart = echarts.init(ratioChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      data: [
        { value: sentimentStats.value.positive, name: 'Positive', itemStyle: { color: '#52c41a' } },
        { value: sentimentStats.value.neutral, name: 'Neutral', itemStyle: { color: '#faad14' } },
        { value: sentimentStats.value.negative, name: 'Negative', itemStyle: { color: '#ff4d4f' } }
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
  
  chart.setOption(option)
}

const updateTrendChart = () => {
  if (!trendChartRef.value || weiboStream.value.length === 0) return
  
  const chart = echarts.init(trendChartRef.value)
  
  // Get last 50 items
  const recentItems = weiboStream.value.slice(0, 50).reverse()
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0]
        return `Score: ${data.value.toFixed(2)}<br/>Time: ${formatTime(recentItems[data.dataIndex].timestamp)}`
      }
    },
    xAxis: {
      type: 'category',
      data: recentItems.map((_, index) => index + 1),
      show: false
    },
    yAxis: {
      type: 'value',
      min: -1,
      max: 1,
      axisLabel: {
        formatter: (value: number) => value.toFixed(1)
      }
    },
    series: [{
      data: recentItems.map(item => item.score),
      type: 'line',
      smooth: true,
      lineStyle: {
        color: '#1890ff',
        width: 2
      },
      itemStyle: {
        color: '#1890ff'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(24, 144, 255, 0.3)'
          }, {
            offset: 1, color: 'rgba(24, 144, 255, 0.1)'
          }]
        }
      }
    }]
  }
  
  chart.setOption(option)
}

// Auto-scroll
const startAutoScroll = () => {
  if (!autoScroll.value) return
  
  autoScrollTimer = setInterval(() => {
    if (autoScroll.value && streamTableRef.value) {
      const table = streamTableRef.value.$el.querySelector('.el-table__body-wrapper')
      if (table) {
        table.scrollTop = 0
      }
    }
  }, 100)
}

const stopAutoScroll = () => {
  if (autoScrollTimer) {
    clearInterval(autoScrollTimer)
    autoScrollTimer = null
  }
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
  
  if (autoScroll.value && isConnected.value) {
    startAutoScroll()
  } else {
    stopAutoScroll()
  }
}

// UI actions
const clearStream = () => {
  weiboStream.value = []
  ElMessage.success('Stream cleared')
}

const clearWarnings = () => {
  warningRecords.value = []
  ElMessage.success('Warning records cleared')
}

// Lifecycle
onMounted(async () => {
  // Initialize charts
  await nextTick()
  updateRatioChart()
  updateTrendChart()
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})

onUnmounted(() => {
  // Cleanup
  stopMonitoring()
  
  // Cleanup SSE connection
  if ((window as any).eventSource) {
    (window as any).eventSource.close()
  }
  
  // Cleanup charts
  if (ratioChartRef.value) {
    echarts.dispose(ratioChartRef.value)
  }
  if (trendChartRef.value) {
    echarts.dispose(trendChartRef.value)
  }
})
</script>

<style scoped>
.realtime-monitor {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.monitor-header {
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

.connection-status-wrapper {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.monitor-stats {
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

.subscription-card,
.threshold-card,
.control-card,
.stream-card,
.ratio-card,
.trend-card,
.warnings-card {
  margin-bottom: var(--spacing-lg);
}

.threshold-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.threshold-display {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.current-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

.value-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.value-number {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.value-number.warning {
  color: var(--color-danger);
}

.threshold-indicator {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.indicator-bar {
  position: relative;
  height: 8px;
  background: var(--color-border-light);
  border-radius: var(--border-radius-round);
  overflow: hidden;
}

.indicator-fill {
  height: 100%;
  background: var(--color-success);
  transition: var(--transition-fast);
}

.indicator-fill.warning {
  background: var(--color-danger);
}

.threshold-line {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: var(--color-danger);
  transform: translateX(-1px);
}

.threshold-label {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
  text-align: center;
}

.threshold-control {
  margin: var(--spacing-md) 0;
}

.threshold-actions {
  display: flex;
  justify-content: center;
}

.control-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.control-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.control-button {
  width: 100%;
}

.additional-controls {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

.dev-controls {
  margin-top: var(--spacing-md);
  text-align: center;
}

.stream-controls {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.stream-content {
  position: relative;
}

.weibo-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.content-text {
  line-height: 1.4;
  word-break: break-word;
}

.content-meta {
  display: flex;
  gap: var(--spacing-sm);
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xxs);
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xxs);
}

.keyword-tag {
  font-size: var(--font-size-tiny);
}

.more-keywords {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

/* Row styles for sentiment */
:deep(.sentiment-positive) {
  background: var(--color-success-bg);
}

:deep(.sentiment-negative) {
  background: var(--color-danger-bg);
}

:deep(.sentiment-neutral) {
  background: var(--color-warning-bg);
}

.ratio-content,
.trend-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.ratio-chart,
.trend-chart {
  height: 200px;
}

.ratio-stats {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--border-radius-circle);
}

.stat-dot.positive {
  background: var(--color-success);
}

.stat-dot.neutral {
  background: var(--color-warning);
}

.stat-dot.negative {
  background: var(--color-danger);
}

.stat-label {
  color: var(--color-text-secondary);
}

.stat-value {
  margin-left: auto;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.warnings-content {
  max-height: 200px;
  overflow-y: auto;
}

.warnings-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.warning-item {
  padding: var(--spacing-xs);
  border-left: 3px solid var(--color-warning);
  background: var(--color-warning-bg);
  border-radius: var(--border-radius-xs);
}

.warning-time {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xxs);
}

.warning-message {
  font-size: var(--font-size-small);
  color: var(--color-text-primary);
}

.no-warnings {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-lg);
  color: var(--color-success);
  font-size: var(--font-size-small);
}

/* Responsive */
@media (max-width: 1280px) {
  .monitor-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .monitor-stats {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .realtime-monitor {
    padding: var(--spacing-md);
  }
  
  .monitor-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .control-buttons {
    gap: var(--spacing-xs);
  }
  
  .additional-controls {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  
  .stream-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .monitor-stats {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .subscription-card,
  .threshold-card,
  .control-card,
  .stream-card,
  .ratio-card,
  .trend-card,
  .warnings-card {
    border-width: 2px;
  }
}
</style>
