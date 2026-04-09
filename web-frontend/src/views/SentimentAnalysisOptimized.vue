<template>
  <div class="sentiment-analysis">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header with mode selection -->
    <div class="analysis-header">
      <div class="header-left">
        <h1 class="page-title">Sentiment Analysis</h1>
        <div class="mode-selector">
          <el-radio-group v-model="analysisMode" @change="handleModeChange" size="large">
            <el-radio-button label="dictionary">
              <el-icon><Document /></el-icon>
              Dictionary Mode
            </el-radio-button>
            <el-radio-button label="hybrid">
              <el-icon><MagicStick /></el-icon>
              Hybrid Mode
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>
      
      <div class="header-right">
        <div class="model-status">
          <el-tag 
            :type="getModelStatusType()" 
            size="large"
            :aria-label="`Model status: ${getModelStatusText()}`"
          >
            <el-icon v-if="isModelLoading" class="rotating"><Loading /></el-icon>
            {{ getModelStatusText() }}
          </el-tag>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Left Panel: Single Analysis -->
        <el-col :span="8">
          <el-card shadow="hover" class="analysis-card">
            <template #header>
              <div class="card-header">
                <el-icon><EditPen /></el-icon>
                <span>Single Text Analysis</span>
              </div>
            </template>
            
            <div class="single-analysis">
              <el-form :model="singleAnalysis" label-position="top">
                <el-form-item label="Text to Analyze">
                  <el-input
                    v-model="singleAnalysis.text"
                    type="textarea"
                    :rows="6"
                    :maxlength="500"
                    show-word-limit
                    placeholder="Enter text to analyze sentiment..."
                    :aria-label="'Text input for sentiment analysis'"
                    @input="handleTextInput"
                  />
                  
                  <!-- Example text suggestions -->
                  <div class="example-suggestions">
                    <div class="suggestion-header">
                      <span class="suggestion-title">Example texts:</span>
                    </div>
                    <div class="suggestion-list">
                      <div
                        v-for="example in exampleTexts"
                        :key="example.id"
                        class="suggestion-item"
                        @click="selectExample(example)"
                        :aria-label="`Use example: ${example.text.substring(0, 30)}...`"
                      >
                        <span class="suggestion-text">{{ example.text }}</span>
                        <span class="suggestion-sentiment" :class="example.sentiment">
                          {{ example.sentiment }}
                        </span>
                      </div>
                    </div>
                  </div>
                </el-form-item>
                
                <el-form-item>
                  <el-button
                    type="primary"
                    size="large"
                    :icon="Search"
                    @click="analyzeSingleText"
                    :loading="isAnalyzing"
                    :disabled="!singleAnalysis.text.trim()"
                    :aria-label="'Analyze text sentiment'"
                    class="analyze-button"
                  >
                    Analyze Sentiment
                  </el-button>
                </el-form-item>
              </el-form>
              
              <!-- Analysis result -->
              <div v-if="singleResult" class="single-result">
                <AnalysisResultCard
                  :result="singleResult"
                  :compact="false"
                  @details="handleResultDetails"
                  @export="handleResultExport"
                />
              </div>
            </div>
          </el-card>
          
          <!-- Batch Analysis -->
          <el-card shadow="hover" class="analysis-card">
            <template #header>
              <div class="card-header">
                <el-icon><Files /></el-icon>
                <span>Batch Analysis</span>
              </div>
            </template>
            
            <div class="batch-analysis">
              <el-form :model="batchAnalysis" label-position="top">
                <el-form-item label="Upload File">
                  <el-upload
                    ref="uploadRef"
                    :auto-upload="false"
                    :on-change="handleFileChange"
                    :on-remove="handleFileRemove"
                    :file-list="batchAnalysis.files"
                    accept=".txt,.csv,.json"
                    drag
                    multiple
                    :aria-label="'Upload files for batch analysis'"
                  >
                    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                    <div class="el-upload__text">
                      Drop files here or <em>click to upload</em>
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">
                        Supports .txt, .csv, .json files
                      </div>
                    </template>
                  </el-upload>
                </el-form-item>
                
                <el-form-item v-if="batchAnalysis.files.length > 0">
                  <div class="batch-controls">
                    <el-button
                      type="primary"
                      :icon="VideoPlay"
                      @click="startBatchAnalysis"
                      :loading="isBatchAnalyzing"
                      :disabled="batchAnalysis.files.length === 0"
                      :aria-label="'Start batch analysis'"
                    >
                      Start Batch Analysis
                    </el-button>
                    
                    <el-button
                      v-if="isBatchAnalyzing"
                      type="danger"
                      :icon="VideoStop"
                      @click="cancelBatchAnalysis"
                      :aria-label="'Cancel batch analysis'"
                    >
                      Cancel
                    </el-button>
                  </div>
                </el-form-item>
                
                <!-- Batch progress -->
                <div v-if="isBatchAnalyzing" class="batch-progress">
                  <div class="progress-header">
                    <span class="progress-title">Batch Analysis Progress</span>
                    <el-tag type="info" size="small">
                      {{ batchProgress.completed }}/{{ batchProgress.total }}
                    </el-tag>
                  </div>
                  
                  <el-progress
                    :percentage="batchProgress.percentage"
                    :status="batchProgress.status"
                    :stroke-width="8"
                    :aria-label="`Batch analysis progress: ${batchProgress.percentage}%`"
                  />
                  
                  <div class="progress-info">
                    <div class="info-item">
                      <span class="info-label">Current File:</span>
                      <span class="info-value">{{ batchProgress.currentFile }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">Processing Rate:</span>
                      <span class="info-value">{{ batchProgress.rate }} files/sec</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">ETA:</span>
                      <span class="info-value">{{ batchProgress.eta }}</span>
                    </div>
                  </div>
                </div>
              </el-form>
            </div>
          </el-card>
        </el-col>
        
        <!-- Middle Panel: Real-time Streaming -->
        <el-col :span="8">
          <el-card shadow="hover" class="streaming-card">
            <template #header>
              <div class="card-header">
                <el-icon><Connection /></el-icon>
                <span>Real-time Streaming</span>
                <el-switch
                  v-model="streamingEnabled"
                  active-text="Enable"
                  size="small"
                  :aria-label="'Toggle real-time streaming'"
                />
              </div>
            </template>
            
            <div class="streaming-content">
              <StreamingStatus
                :protocol="streamingProtocol"
                :endpoint="streamingEndpoint"
                :auto-connect="streamingEnabled"
                :auto-reconnect="true"
                @connect="handleStreamConnect"
                @disconnect="handleStreamDisconnect"
                @message="handleStreamMessage"
                @error="handleStreamError"
                ref="streamingRef"
              />
              
              <!-- Stream results -->
              <div v-if="streamResults.length > 0" class="stream-results">
                <div class="results-header">
                  <span class="results-title">Recent Results</span>
                  <el-button
                    text
                    size="small"
                    @click="clearStreamResults"
                    :aria-label="'Clear stream results'"
                  >
                    Clear
                  </el-button>
                </div>
                
                <div class="results-list">
                  <AnalysisResultCard
                    v-for="result in streamResults.slice(0, 5)"
                    :key="result.id"
                    :result="result"
                    :compact="true"
                    @details="handleResultDetails"
                    @export="handleResultExport"
                  />
                </div>
              </div>
            </div>
          </el-card>
          
          <!-- Cascade Statistics -->
          <el-card shadow="hover" class="statistics-card">
            <template #header>
              <div class="card-header">
                <el-icon><PieChart /></el-icon>
                <span>Cascade Strategy Statistics</span>
              </div>
            </template>
            
            <div class="cascade-statistics">
              <div ref="cascadeChartRef" class="cascade-chart"></div>
              
              <div class="statistics-details">
                <div class="stat-item">
                  <div class="stat-icon dictionary">
                    <el-icon><Document /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ cascadeStats.dictionaryCount }}</div>
                    <div class="stat-label">Dictionary Hits</div>
                  </div>
                </div>
                
                <div class="stat-item">
                  <div class="stat-icon bert">
                    <el-icon><Cpu /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ cascadeStats.bertCount }}</div>
                    <div class="stat-label">BERT Hits</div>
                  </div>
                </div>
                
                <div class="stat-item">
                  <div class="stat-icon total">
                    <el-icon><DataAnalysis /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ cascadeStats.totalCount }}</div>
                    <div class="stat-label">Total Analyses</div>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- Right Panel: Results Table -->
        <el-col :span="8">
          <el-card shadow="hover" class="results-card">
            <template #header>
              <div class="card-header">
                <el-icon><Table /></el-icon>
                <span>Analysis Results</span>
                <div class="results-actions">
                  <el-button
                    text
                    size="small"
                    @click="refreshResults"
                    :loading="isRefreshing"
                    :aria-label="'Refresh results table'"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                  <el-dropdown @command="handleExportCommand">
                    <el-button text size="small">
                      <el-icon><Download /></el-icon>
                      Export
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="csv">Export as CSV</el-dropdown-item>
                        <el-dropdown-item command="json">Export as JSON</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </template>
            
            <div class="results-table">
              <!-- Filters -->
              <div class="table-filters">
                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-select
                      v-model="tableFilters.sentiment"
                      placeholder="Filter by sentiment"
                      clearable
                      size="small"
                      style="width: 100%"
                      :aria-label="'Filter by sentiment'"
                    >
                      <el-option label="All" value="" />
                      <el-option label="Positive" value="positive" />
                      <el-option label="Negative" value="negative" />
                      <el-option label="Neutral" value="neutral" />
                    </el-select>
                  </el-col>
                  
                  <el-col :span="12">
                    <el-select
                      v-model="tableFilters.method"
                      placeholder="Filter by method"
                      clearable
                      size="small"
                      style="width: 100%"
                      :aria-label="'Filter by analysis method'"
                    >
                      <el-option label="All" value="" />
                      <el-option label="Dictionary" value="dictionary" />
                      <el-option label="BERT" value="bert" />
                      <el-option label="Cascade" value="cascade" />
                    </el-select>
                  </el-col>
                </el-row>
                
                <div class="sort-controls">
                  <span class="sort-label">Sort by:</span>
                  <el-radio-group v-model="tableSort.field" size="small">
                    <el-radio-button label="score">Score</el-radio-button>
                    <el-radio-button label="time">Time</el-radio-button>
                    <el-radio-button label="confidence">Confidence</el-radio-button>
                  </el-radio-group>
                  <el-button
                    text
                    size="small"
                    @click="toggleSortOrder"
                    :aria-label="'Toggle sort order'"
                  >
                    <el-icon><Sort /></el-icon>
                  </el-button>
                </div>
              </div>
              
              <!-- Table -->
              <el-table
                :data="filteredResults"
                height="400"
                size="small"
                :default-sort="{ prop: tableSort.field, order: tableSort.order }"
                @sort-change="handleTableSort"
                :aria-label="'Analysis results table'"
              >
                <el-table-column prop="id" label="ID" width="80" />
                <el-table-column prop="text" label="Text" min-width="150" show-overflow-tooltip />
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
                <el-table-column prop="score" label="Score" width="80" sortable>
                  <template #default="{ row }">
                    <span :style="{ color: getScoreColor(row.sentiment) }">
                      {{ row.score.toFixed(3) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="confidence" label="Confidence" width="100" sortable>
                  <template #default="{ row }">
                    {{ Math.round(row.confidence * 100) }}%
                  </template>
                </el-table-column>
                <el-table-column prop="method" label="Method" width="100">
                  <template #default="{ row }">
                    <el-tag type="info" size="small">
                      {{ row.method }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="timestamp" label="Time" width="100" sortable>
                  <template #default="{ row }">
                    {{ formatTime(row.timestamp) }}
                  </template>
                </el-table-column>
                <el-table-column label="Actions" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      text
                      size="small"
                      @click="viewResultDetails(row)"
                      :aria-label="'View result details'"
                    >
                      <el-icon><View /></el-icon>
                    </el-button>
                    <el-button
                      text
                      size="small"
                      @click="exportResult(row)"
                      :aria-label="'Export result'"
                    >
                      <el-icon><Download /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              
              <!-- Table pagination -->
              <div class="table-pagination">
                <el-pagination
                  v-model:current-page="tablePagination.page"
                  v-model:page-size="tablePagination.size"
                  :page-sizes="[10, 20, 50, 100]"
                  :total="totalResults"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="handlePageSizeChange"
                  @current-change="handlePageChange"
                  :aria-label="'Results table pagination'"
                />
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  Document, MagicStick, EditPen, Search, Files, UploadFilled,
  VideoPlay, VideoStop, Connection, PieChart, Table, Refresh, Download,
  Sort, View, Loading, Cpu, DataAnalysis
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import AnalysisResultCard from '@/components/common/AnalysisResultCard.vue'
import StreamingStatus from '@/components/common/StreamingStatus.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface SingleAnalysis {
  text: string
}

interface BatchAnalysis {
  files: any[]
}

interface AnalysisResult {
  id: string
  text: string
  sentiment: 'positive' | 'negative' | 'neutral'
  score: number
  confidence: number
  positive: number
  negative: number
  neutral: number
  cascadeDecision?: {
    method: 'dictionary' | 'bert' | 'cascade'
    reason: string
    threshold?: number
  }
  timestamp: Date
  processingTime: number
  method: string
}

interface ExampleText {
  id: string
  text: string
  sentiment: 'positive' | 'negative' | 'neutral'
}

interface BatchProgress {
  completed: number
  total: number
  percentage: number
  status: 'success' | 'exception' | 'warning'
  currentFile: string
  rate: number
  eta: string
}

interface CascadeStats {
  dictionaryCount: number
  bertCount: number
  totalCount: number
}

// Reactive data
const analysisMode = ref<'dictionary' | 'hybrid'>('hybrid')
const isModelLoading = ref(false)
const modelError = ref<string | null>(null)

const singleAnalysis = ref<SingleAnalysis>({
  text: ''
})

const singleResult = ref<AnalysisResult | null>(null)
const isAnalyzing = ref(false)

const batchAnalysis = ref<BatchAnalysis>({
  files: []
})

const isBatchAnalyzing = ref(false)
const batchProgress = ref<BatchProgress>({
  completed: 0,
  total: 0,
  percentage: 0,
  status: 'success',
  currentFile: '',
  rate: 0,
  eta: 'N/A'
})

const streamingEnabled = ref(false)
const streamingProtocol = ref<'websocket' | 'sse'>('websocket')
const streamingEndpoint = ref('ws://localhost:8080/stream/sentiment')
const streamResults = ref<AnalysisResult[]>([])

const results = ref<AnalysisResult[]>([])
const isRefreshing = ref(false)

const tableFilters = ref({
  sentiment: '',
  method: ''
})

const tableSort = ref({
  field: 'time',
  order: 'descending'
})

const tablePagination = ref({
  page: 1,
  size: 20
})

const cascadeStats = ref<CascadeStats>({
  dictionaryCount: 0,
  bertCount: 0,
  totalCount: 0
})

// Refs
const uploadRef = ref()
const streamingRef = ref()
const cascadeChartRef = ref()

// Constants
const exampleTexts = ref<ExampleText[]>([
  {
    id: '1',
    text: 'This product is amazing! I love it so much.',
    sentiment: 'positive'
  },
  {
    id: '2',
    text: 'The service was terrible and I am very disappointed.',
    sentiment: 'negative'
  },
  {
    id: '3',
    text: 'The weather is okay today, nothing special.',
    sentiment: 'neutral'
  },
  {
    id: '4',
    text: 'Great job on the presentation! Really impressive work.',
    sentiment: 'positive'
  },
  {
    id: '5',
    text: 'I am not satisfied with the quality of this item.',
    sentiment: 'negative'
  }
])

// Computed properties
const getModelStatusText = () => {
  if (isModelLoading.value) return 'Loading...'
  if (modelError.value) return 'Error'
  if (analysisMode.value === 'hybrid') return 'BERT Ready'
  return 'Dictionary Ready'
}

const getModelStatusType = () => {
  if (isModelLoading.value) return 'warning'
  if (modelError.value) return 'danger'
  return 'success'
}

const filteredResults = computed(() => {
  let filtered = results.value

  // Apply sentiment filter
  if (tableFilters.value.sentiment) {
    filtered = filtered.filter(result => result.sentiment === tableFilters.value.sentiment)
  }

  // Apply method filter
  if (tableFilters.value.method) {
    filtered = filtered.filter(result => result.method === tableFilters.value.method)
  }

  // Apply sorting
  filtered = [...filtered].sort((a, b) => {
    const aValue = a[tableSort.value.field as keyof AnalysisResult]
    const bValue = b[tableSort.value.field as keyof AnalysisResult]
    
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return tableSort.value.order === 'ascending' ? aValue - bValue : bValue - aValue
    }
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return tableSort.value.order === 'ascending' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }
    
    return 0
  })

  // Apply pagination
  const start = (tablePagination.value.page - 1) * tablePagination.value.size
  const end = start + tablePagination.value.size
  return filtered.slice(start, end)
})

const totalResults = computed(() => {
  let filtered = results.value

  if (tableFilters.value.sentiment) {
    filtered = filtered.filter(result => result.sentiment === tableFilters.value.sentiment)
  }

  if (tableFilters.value.method) {
    filtered = filtered.filter(result => result.method === tableFilters.value.method)
  }

  return filtered.length
})

// Methods
const handleModeChange = async () => {
  if (analysisMode.value === 'hybrid') {
    await loadBERTModel()
  } else {
    modelError.value = null
  }
}

const loadBERTModel = async () => {
  isModelLoading.value = true
  modelError.value = null

  try {
    await withErrorHandling(
      async () => {
        // Simulate BERT model loading
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        // Simulate potential error
        if (Math.random() > 0.8) {
          throw new Error('BERT model failed to load')
        }
        
        ElMessage.success('BERT model loaded successfully')
      },
      'BERT Model Loading',
      { showLoading: false }
    )
  } catch (error) {
    modelError.value = 'BERT model not available'
    
    // Auto fallback to dictionary mode
    ElNotification({
      title: 'Model Loading Failed',
      message: 'BERT model failed to load. Automatically switching to dictionary mode.',
      type: 'warning',
      duration: 5000
    })
    
    analysisMode.value = 'dictionary'
  } finally {
    isModelLoading.value = false
  }
}

const handleTextInput = () => {
  // Handle text input if needed
}

const selectExample = (example: ExampleText) => {
  singleAnalysis.value.text = example.text
  ElMessage.info(`Selected example: ${example.sentiment}`)
}

const analyzeSingleText = async () => {
  if (!singleAnalysis.value.text.trim()) {
    ElMessage.warning('Please enter text to analyze')
    return
  }

  isAnalyzing.value = true

  try {
    await withErrorHandling(
      async () => {
        // Simulate analysis
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        const result = await analyzeText(singleAnalysis.value.text)
        singleResult.value = result
        results.value.unshift(result)
        
        // Update cascade statistics
        updateCascadeStats(result)
        
        ElMessage.success('Analysis completed')
      },
      'Single Text Analysis',
      { showLoading: false }
    )
  } finally {
    isAnalyzing.value = false
  }
}

const analyzeText = async (text: string): Promise<AnalysisResult> => {
  // Simulate sentiment analysis
  const sentiments: ('positive' | 'negative' | 'neutral')[] = ['positive', 'negative', 'neutral']
  const sentiment = sentiments[Math.floor(Math.random() * sentiments.length)]
  
  const score = sentiment === 'positive' ? 0.8 + Math.random() * 0.2 : 
                 sentiment === 'negative' ? -0.8 - Math.random() * 0.2 : 
                 Math.random() * 0.4 - 0.2
  
  const confidence = 0.7 + Math.random() * 0.3
  
  let method: string
  let cascadeDecision
  
  if (analysisMode.value === 'dictionary') {
    method = 'dictionary'
    cascadeDecision = {
      method: 'dictionary',
      reason: 'Using dictionary directly for sentiment analysis'
    }
  } else {
    // Hybrid mode - simulate cascade decision
    const useBERT = Math.random() > 0.7
    method = useBERT ? 'bert' : 'dictionary'
    cascadeDecision = {
      method: useBERT ? 'bert' : 'dictionary',
      reason: useBERT ? 'Dictionary confidence low, using BERT' : 'Dictionary confidence sufficient',
      threshold: 0.7
    }
  }
  
  return {
    id: `analysis_${Date.now()}`,
    text,
    sentiment,
    score,
    confidence,
    positive: sentiment === 'positive' ? confidence : sentiment === 'negative' ? 0.1 : 0.3,
    negative: sentiment === 'negative' ? confidence : sentiment === 'positive' ? 0.1 : 0.3,
    neutral: sentiment === 'neutral' ? confidence : 0.2,
    cascadeDecision,
    timestamp: new Date(),
    processingTime: Math.floor(Math.random() * 500 + 100),
    method
  }
}

const handleFileChange = (file: any) => {
  // Handle file change
}

const handleFileRemove = (file: any) => {
  // Handle file removal
}

const startBatchAnalysis = async () => {
  if (batchAnalysis.value.files.length === 0) {
    ElMessage.warning('Please upload files first')
    return
  }

  isBatchAnalyzing.value = true
  batchProgress.value = {
    completed: 0,
    total: batchAnalysis.value.files.length,
    percentage: 0,
    status: 'success',
    currentFile: '',
    rate: 0,
    eta: 'N/A'
  }

  try {
    await withErrorHandling(
      async () => {
        for (let i = 0; i < batchAnalysis.value.files.length; i++) {
          if (!isBatchAnalyzing.value) break
          
          const file = batchAnalysis.value.files[i]
          batchProgress.value.currentFile = file.name
          batchProgress.value.completed = i + 1
          batchProgress.value.percentage = Math.round(((i + 1) / batchAnalysis.value.files.length) * 100)
          batchProgress.value.rate = (i + 1) / ((Date.now() - startTime) / 1000)
          
          // Calculate ETA
          const remaining = batchAnalysis.value.files.length - (i + 1)
          const etaSeconds = remaining / batchProgress.value.rate
          batchProgress.value.eta = etaSeconds > 60 ? `${Math.round(etaSeconds / 60)}m` : `${Math.round(etaSeconds)}s`
          
          // Simulate file processing
          await new Promise(resolve => setTimeout(resolve, 1000))
          
          // Add mock results
          const mockResult = await analyzeText(`Sample text from ${file.name}`)
          results.value.unshift(mockResult)
          updateCascadeStats(mockResult)
        }
        
        ElNotification({
          title: 'Batch Analysis Completed',
          message: `Successfully analyzed ${batchProgress.value.completed} files`,
          type: 'success',
          duration: 5000
        })
      },
      'Batch Analysis',
      { showLoading: false }
    )
  } finally {
    isBatchAnalyzing.value = false
  }
}

const cancelBatchAnalysis = () => {
  isBatchAnalyzing.value = false
  ElMessage.info('Batch analysis cancelled')
}

const handleStreamConnect = () => {
  ElMessage.success('Connected to streaming server')
}

const handleStreamDisconnect = () => {
  ElMessage.info('Disconnected from streaming server')
}

const handleStreamMessage = async (data: any) => {
  try {
    const result = await analyzeText(data.text || 'Stream sample text')
    streamResults.value.unshift(result)
    results.value.unshift(result)
    updateCascadeStats(result)
    
    // Keep only last 50 stream results
    if (streamResults.value.length > 50) {
      streamResults.value = streamResults.value.slice(0, 50)
    }
  } catch (error) {
    console.error('Failed to process stream message:', error)
  }
}

const handleStreamError = (error: any) => {
  ElMessage.error(`Stream error: ${error.message}`)
}

const clearStreamResults = () => {
  streamResults.value = []
  ElMessage.info('Stream results cleared')
}

const updateCascadeStats = (result: AnalysisResult) => {
  cascadeStats.value.totalCount++
  
  if (result.cascadeDecision?.method === 'dictionary') {
    cascadeStats.value.dictionaryCount++
  } else if (result.cascadeDecision?.method === 'bert') {
    cascadeStats.value.bertCount++
  }
  
  updateCascadeChart()
}

const updateCascadeChart = () => {
  if (!cascadeChartRef.value) return
  
  const chart = echarts.init(cascadeChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [{
      name: 'Cascade Strategy',
      type: 'pie',
      radius: '50%',
      data: [
        { value: cascadeStats.value.dictionaryCount, name: 'Dictionary' },
        { value: cascadeStats.value.bertCount, name: 'BERT' }
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
  
  // Handle resize
  const handleResize = () => chart.resize()
  window.addEventListener('resize', handleResize)
}

const refreshResults = async () => {
  isRefreshing.value = true
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate refresh
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success('Results refreshed')
      },
      'Refresh Results',
      { showLoading: false }
    )
  } finally {
    isRefreshing.value = false
  }
}

const handleExportCommand = async (command: 'csv' | 'json') => {
  try {
    await withErrorHandling(
      async () => {
        const data = filteredResults.value
        
        if (command === 'csv') {
          exportToCSV(data)
        } else {
          exportToJSON(data)
        }
      },
      'Export Results',
      { showLoading: false }
    )
  } catch (error) {
    console.error('Export failed:', error)
  }
}

const exportToCSV = (data: AnalysisResult[]) => {
  const headers = ['ID', 'Text', 'Sentiment', 'Score', 'Confidence', 'Method', 'Timestamp']
  const csvContent = [
    headers.join(','),
    ...data.map(row => [
      row.id,
      `"${row.text.replace(/"/g, '""')}"`,
      row.sentiment,
      row.score,
      row.confidence,
      row.method,
      row.timestamp.toISOString()
    ].join(','))
  ].join('\n')
  
  downloadFile(csvContent, 'sentiment_analysis_results.csv', 'text/csv')
}

const exportToJSON = (data: AnalysisResult[]) => {
  const jsonContent = JSON.stringify(data, null, 2)
  downloadFile(jsonContent, 'sentiment_analysis_results.json', 'application/json')
}

const downloadFile = (content: string, filename: string, contentType: string) => {
  const blob = new Blob([content], { type: contentType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  ElMessage.success(`Exported ${filename}`)
}

const handleTableSort = ({ prop, order }: { prop: string; order: string }) => {
  tableSort.value.field = prop
  tableSort.value.order = order
}

const toggleSortOrder = () => {
  tableSort.value.order = tableSort.value.order === 'ascending' ? 'descending' : 'ascending'
}

const handlePageSizeChange = (size: number) => {
  tablePagination.value.size = size
  tablePagination.value.page = 1
}

const handlePageChange = (page: number) => {
  tablePagination.value.page = page
}

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

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleResultDetails = (result: AnalysisResult) => {
  ElMessage.info(`Viewing details for result ${result.id}`)
  // Implement detail view logic
}

const handleResultExport = (result: AnalysisResult) => {
  exportToJSON([result])
}

const viewResultDetails = (result: AnalysisResult) => {
  handleResultDetails(result)
}

const exportResult = (result: AnalysisResult) => {
  handleResultExport(result)
}

// Lifecycle
onMounted(async () => {
  // Load initial data
  await refreshResults()
  
  // Initialize cascade chart
  nextTick(() => {
    updateCascadeChart()
  })
  
  // Load BERT model if in hybrid mode
  if (analysisMode.value === 'hybrid') {
    await loadBERTModel()
  }
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})
</script>

<style scoped>
.sentiment-analysis {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.analysis-header {
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

.mode-selector {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.model-status {
  display: flex;
  align-items: center;
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

.analysis-card,
.streaming-card,
.statistics-card,
.results-card {
  margin-bottom: var(--spacing-lg);
}

.single-analysis {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.example-suggestions {
  margin-top: var(--spacing-sm);
}

.suggestion-header {
  margin-bottom: var(--spacing-xs);
}

.suggestion-title {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-small);
  cursor: pointer;
  transition: var(--transition-fast);
}

.suggestion-item:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
}

.suggestion-text {
  flex: 1;
  font-size: var(--font-size-small);
  color: var(--color-text-primary);
  margin-right: var(--spacing-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggestion-sentiment {
  font-size: var(--font-size-tiny);
  font-weight: var(--font-weight-medium);
  padding: 2px 6px;
  border-radius: var(--border-radius-xs);
}

.suggestion-sentiment.positive {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.suggestion-sentiment.negative {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.suggestion-sentiment.neutral {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.analyze-button {
  width: 100%;
}

.single-result {
  margin-top: var(--spacing-md);
}

.batch-analysis {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.batch-controls {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: center;
}

.batch-progress {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.progress-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.progress-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
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

.streaming-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.stream-results {
  margin-top: var(--spacing-md);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.results-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.cascade-statistics {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.cascade-chart {
  height: 200px;
}

.statistics-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--border-radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.dictionary {
  background: var(--color-info);
}

.stat-icon.bert {
  background: var(--color-primary);
}

.stat-icon.total {
  background: var(--color-success);
}

.stat-content {
  flex: 1;
}

.stat-content .stat-value {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.stat-content .stat-label {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.results-table {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.table-filters {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.sort-label {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.results-actions {
  display: flex;
  gap: var(--spacing-xs);
}

.table-pagination {
  margin-top: var(--spacing-md);
  display: flex;
  justify-content: center;
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
  .analysis-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .mode-selector {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .sentiment-analysis {
    padding: var(--spacing-md);
  }
  
  .analysis-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .mode-selector .el-radio-group {
    display: flex;
    flex-direction: column;
    width: 100%;
  }
  
  .batch-controls {
    flex-direction: column;
  }
  
  .batch-controls .el-button {
    width: 100%;
  }
  
  .progress-info {
    grid-template-columns: 1fr;
  }
  
  .statistics-details {
    gap: var(--spacing-xs);
  }
  
  .sort-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .results-actions {
    justify-content: center;
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .analysis-card,
  .streaming-card,
  .statistics-card,
  .results-card {
    border-width: 2px;
  }
}
</style>
