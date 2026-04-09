<template>
  <div class="preprocess-enhanced">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header with status -->
    <div class="preprocess-header">
      <div class="header-left">
        <h1 class="page-title">Data Preprocessing</h1>
        <div class="status-indicator">
          <el-tag 
            :type="getStatusTagType()" 
            size="large"
            :aria-label="`Processing status: ${getStatusText()}`"
          >
            <el-icon v-if="isProcessing" class="rotating"><Loading /></el-icon>
            {{ getStatusText() }}
          </el-tag>
        </div>
      </div>
      
      <div class="header-right">
        <div class="processing-stats">
          <span class="stat-item">
            <strong>{{ rawData.length }}</strong> raw
          </span>
          <span class="stat-item">
            <strong>{{ processedData.length }}</strong> processed
          </span>
          <span class="stat-item">
            <strong>{{ processingTime }}</strong> ms
          </span>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Left Panel: Data Source & Configuration -->
        <el-col :span="8">
          <!-- Data Source Selection -->
          <el-card shadow="hover" class="config-card">
            <template #header>
              <div class="card-header">
                <el-icon><DataBoard /></el-icon>
                <span>Data Source</span>
                <el-button
                  text
                  size="small"
                  @click="refreshDataSources"
                  :loading="isLoadingSources"
                  :aria-label="'Refresh data sources'"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </div>
            </template>
            
            <el-form :model="config" label-position="top" size="default">
              <el-form-item label="Data Source Type">
                <el-radio-group v-model="config.dataSource" @change="handleDataSourceChange">
                  <el-radio label="hdfs" class="source-option">
                    <div class="option-content">
                      <el-icon><FolderOpened /></el-icon>
                      <div class="option-details">
                        <div class="option-title">HDFS Raw Data</div>
                        <div class="option-desc">Read raw data from HDFS</div>
                      </div>
                    </div>
                  </el-radio>
                  <el-radio label="mysql" class="source-option">
                    <div class="option-content">
                      <el-icon><Coin /></el-icon>
                      <div class="option-details">
                        <div class="option-title">MySQL Cleaned Data</div>
                        <div class="option-desc">Read cleaned data from MySQL</div>
                      </div>
                    </div>
                  </el-radio>
                  <el-radio label="sample" class="source-option">
                    <div class="option-content">
                      <el-icon><Document /></el-icon>
                      <div class="option-details">
                        <div class="option-title">Sample Data</div>
                        <div class="option-desc">Use sample dataset</div>
                      </div>
                    </div>
                  </el-radio>
                </el-radio-group>
              </el-form-item>
              
              <!-- HDFS specific options -->
              <template v-if="config.dataSource === 'hdfs'">
                <el-form-item label="HDFS Path">
                  <el-input
                    v-model="config.hdfsPath"
                    placeholder="/user/hadoop/weibo/raw/"
                    :aria-label="'Enter HDFS path'"
                  />
                </el-form-item>
                
                <el-form-item label="File Format">
                  <el-select v-model="config.fileFormat" style="width: 100%">
                    <el-option label="JSON" value="json" />
                    <el-option label="CSV" value="csv" />
                    <el-option label="Parquet" value="parquet" />
                  </el-select>
                </el-form-item>
              </template>
              
              <!-- MySQL specific options -->
              <template v-if="config.dataSource === 'mysql'">
                <el-form-item label="Table Name">
                  <el-select v-model="config.mysqlTable" style="width: 100%">
                    <el-option label="weibo_raw_data" value="weibo_raw_data" />
                    <el-option label="weibo_temp_data" value="weibo_temp_data" />
                    <el-option label="weibo_staging" value="weibo_staging" />
                  </el-select>
                </el-form-item>
                
                <el-form-item label="Date Range">
                  <el-date-picker
                    v-model="config.dateRange"
                    type="daterange"
                    range-separator="to"
                    start-placeholder="Start date"
                    end-placeholder="End date"
                    style="width: 100%"
                  />
                </el-form-item>
              </template>
            </el-form>
          </el-card>
          
          <!-- Cleaning Steps Configuration -->
          <el-card shadow="hover" class="config-card">
            <template #header>
              <div class="card-header">
                <el-icon><Setting /></el-icon>
                <span>Cleaning Steps</span>
                <el-button
                  text
                  size="small"
                  @click="resetCleaningSteps"
                  :aria-label="'Reset cleaning steps'"
                >
                  <el-icon><RefreshRight /></el-icon>
                </el-button>
              </div>
            </template>
            
            <div class="cleaning-steps">
              <div
                v-for="step in cleaningSteps"
                :key="step.key"
                class="step-item"
                :class="{ active: config.steps.includes(step.key) }"
                @click="toggleStep(step.key)"
              >
                <div class="step-header">
                  <el-icon><component :is="step.icon" /></el-icon>
                  <span class="step-title">{{ step.title }}</span>
                  <el-switch
                    v-model="config.steps"
                    :value="step.key"
                    @click.stop
                    :aria-label="`Toggle ${step.title}`"
                  />
                </div>
                <div class="step-description">{{ step.description }}</div>
                
                <!-- Step-specific options -->
                <div v-if="config.steps.includes(step.key)" class="step-options">
                  <template v-if="step.key === 'deduplication'">
                    <el-form-item label="Similarity Threshold">
                      <el-slider
                        v-model="config.dedupThreshold"
                        :min="0.7"
                        :max="0.95"
                        :step="0.05"
                        show-input
                      />
                    </el-form-item>
                  </template>
                  
                  <template v-if="step.key === 'normalization'">
                    <el-form-item label="Normalization Method">
                      <el-radio-group v-model="config.normalizationMethod">
                        <el-radio label="lowercase">Lowercase</el-radio>
                        <el-radio label="unicode">Unicode Normalization</el-radio>
                        <el-radio label="both">Both</el-radio>
                      </el-radio-group>
                    </el-form-item>
                  </template>
                  
                  <template v-if="step.key === 'tokenization'">
                    <el-form-item label="Tokenizer">
                      <el-select v-model="config.tokenizer">
                        <el-option label="Jieba" value="jieba" />
                        <el-option label="HanLP" value="hanlp" />
                        <el-option label="Custom" value="custom" />
                      </el-select>
                    </el-form-item>
                  </template>
                  
                  <template v-if="step.key === 'stopwords'">
                    <el-form-item label="Stop Word List">
                      <el-select v-model="config.stopwordList" multiple style="width: 100%">
                        <el-option label="Chinese Common" value="zh_common" />
                        <el-option label="Weibo Specific" value="weibo" />
                        <el-option label="Domain Specific" value="domain" />
                        <el-option label="Custom" value="custom" />
                      </el-select>
                    </el-form-item>
                  </template>
                  
                  <template v-if="step.key === 'emoji'">
                    <el-form-item label="Emoji Processing">
                      <el-radio-group v-model="config.emojiProcessing">
                        <el-radio label="remove">Remove</el-radio>
                        <el-radio label="replace">Replace with text</el-radio>
                        <el-radio label="keep">Keep</el-radio>
                      </el-radio-group>
                    </el-form-item>
                  </template>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- Middle Panel: Processing & Results -->
        <el-col :span="8">
          <!-- Processing Controls -->
          <el-card shadow="hover" class="control-card">
            <div class="processing-controls">
              <el-button-group>
                <el-button
                  type="primary"
                  :icon="VideoPlay"
                  @click="startProcessing"
                  :loading="isProcessing"
                  :disabled="isProcessing || rawData.length === 0"
                  size="large"
                  :aria-label="'Start data processing'"
                >
                  Start Processing
                </el-button>
                <el-button
                  type="warning"
                  :icon="VideoPause"
                  @click="pauseProcessing"
                  :disabled="!isProcessing || isPaused"
                  size="large"
                  :aria-label="'Pause data processing'"
                >
                  Pause
                </el-button>
                <el-button
                  type="danger"
                  :icon="VideoStop"
                  @click="stopProcessing"
                  :disabled="!isProcessing"
                  size="large"
                  :aria-label="'Stop data processing'"
                >
                  Stop
                </el-button>
              </el-button-group>
            </div>
          </el-card>
          
          <!-- Processing Progress -->
          <el-card shadow="hover" class="progress-card">
            <template #header>
              <div class="card-header">
                <el-icon><TrendCharts /></el-icon>
                <span>Processing Progress</span>
                <el-tag type="primary" size="small">{{ processingProgress }}%</el-tag>
              </div>
            </template>
            
            <el-progress
              type="dashboard"
              :percentage="processingProgress"
              :color="progressColors"
              :width="160"
              :aria-label="`Processing progress: ${processingProgress}%`"
            >
              <template #default="{ percentage }">
                <span class="progress-value">{{ percentage }}%</span>
                <span class="progress-label">Complete</span>
              </template>
            </el-progress>
            
            <div class="progress-info">
              <div class="info-item">
                <span class="info-label">Current Step:</span>
                <span class="info-value">{{ currentStep }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Processed:</span>
                <span class="info-value">{{ processedData.length }}/{{ rawData.length }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Rate:</span>
                <span class="info-value">{{ processingRate }} items/sec</span>
              </div>
            </div>
          </el-card>
          
          <!-- Word Cloud -->
          <el-card shadow="hover" class="wordcloud-card">
            <WordCloud
              :words="wordFrequencyData"
              :title="'High Frequency Words (Top 20)'"
              :height="300"
              :top-count="20"
              @word-click="handleWordClick"
              @word-hover="handleWordHover"
              ref="wordCloudRef"
            />
          </el-card>
          
          <!-- Similarity Detection -->
          <el-card shadow="hover" class="similarity-card">
            <template #header>
              <div class="card-header">
                <el-icon><Connection /></el-icon>
                <span>Similarity Detection</span>
                <el-switch
                  v-model="similarityEnabled"
                  active-text="Enable"
                  size="small"
                  :aria-label="'Toggle similarity detection'"
                />
              </div>
            </template>
            
            <div v-if="similarityEnabled" class="similarity-content">
              <div class="similarity-stats">
                <div class="stat-item">
                  <div class="stat-value">{{ similarityStats.totalClusters }}</div>
                  <div class="stat-label">Clusters</div>
                </div>
                <div class="stat-item">
                  <div class="stat-value">{{ similarityStats.avgSimilarity }}%</div>
                  <div class="stat-label">Avg Similarity</div>
                </div>
                <div class="stat-item">
                  <div class="stat-value">{{ similarityStats.duplicates }}</div>
                  <div class="stat-label">Duplicates</div>
                </div>
              </div>
              
              <div class="similarity-threshold">
                <el-form-item label="Similarity Threshold">
                  <el-slider
                    v-model="similarityThreshold"
                    :min="0.5"
                    :max="0.95"
                    :step="0.05"
                    show-input
                    @change="updateSimilarityClustering"
                  />
                </el-form-item>
              </div>
              
              <div class="cluster-preview">
                <div
                  v-for="cluster in similarityClusters.slice(0, 3)"
                  :key="cluster.id"
                  class="cluster-item"
                >
                  <div class="cluster-header">
                    <span class="cluster-id">Cluster {{ cluster.id }}</span>
                    <el-tag size="small">{{ cluster.items.length }} items</el-tag>
                  </div>
                  <div class="cluster-items">
                    <span
                      v-for="item in cluster.items.slice(0, 2)"
                      :key="item.id"
                      class="cluster-item-text"
                    >
                      {{ item.text.substring(0, 20) }}...
                    </span>
                    <span v-if="cluster.items.length > 2" class="more-items">
                      +{{ cluster.items.length - 2 }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- Right Panel: Comparison & Preview -->
        <el-col :span="8">
          <!-- Before/After Comparison -->
          <el-card shadow="hover" class="comparison-card">
            <ComparisonPanel
              :items="comparisonData"
              :title="'Before/After Comparison'"
              :show-differences="showDifferences"
              @item-change="handleComparisonChange"
              ref="comparisonRef"
            />
          </el-card>
          
          <!-- Result Statistics -->
          <el-card shadow="hover" class="stats-card">
            <template #header>
              <div class="card-header">
                <el-icon><DataAnalysis /></el-icon>
                <span>Processing Statistics</span>
              </div>
            </template>
            
            <div class="statistics-grid">
              <div class="stat-card">
                <div class="stat-icon original">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ processingStats.originalCount }}</div>
                  <div class="stat-label">Original</div>
                </div>
              </div>
              
              <div class="stat-card">
                <div class="stat-icon valid">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ processingStats.validCount }}</div>
                  <div class="stat-label">Valid</div>
                </div>
              </div>
              
              <div class="stat-card">
                <div class="stat-icon duplicates">
                  <el-icon><CopyDocument /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ processingStats.duplicateCount }}</div>
                  <div class="stat-label">Duplicates</div>
                </div>
              </div>
              
              <div class="stat-card">
                <div class="stat-icon noise">
                  <el-icon><Warning /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ processingStats.noiseRate }}%</div>
                  <div class="stat-label">Noise Rate</div>
                </div>
              </div>
            </div>
          </el-card>
          
          <!-- Preview Table -->
          <el-card shadow="hover" class="preview-card">
            <template #header>
              <div class="card-header">
                <el-icon><View /></el-icon>
                <span>Result Preview</span>
                <div class="preview-actions">
                  <el-button
                    text
                    size="small"
                    @click="selectAllPreview"
                    :aria-label="'Select all items'"
                  >
                    Select All
                  </el-button>
                  <el-button
                    text
                    size="small"
                    @click="excludeSelected"
                    :disabled="selectedPreviewItems.length === 0"
                    :aria-label="'Exclude selected items'"
                  >
                    Exclude ({{ selectedPreviewItems.length }})
                  </el-button>
                </div>
              </div>
            </template>
            
            <el-table
              :data="previewData"
              height="300"
              size="small"
              @selection-change="handlePreviewSelection"
              :aria-label="'Preview table of processed data'"
            >
              <el-table-column type="selection" width="55" />
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="originalText" label="Original" min-width="150" show-overflow-tooltip />
              <el-table-column prop="processedText" label="Processed" min-width="150" show-overflow-tooltip />
              <el-table-column prop="tokens" label="Tokens" width="80" />
              <el-table-column prop="status" label="Status" width="80">
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
              <el-table-column label="Actions" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button
                    text
                    size="small"
                    @click="viewItemDetails(row)"
                    :aria-label="'View item details'"
                  >
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button
                    text
                    size="small"
                    type="danger"
                    @click="excludeItem(row)"
                    :aria-label="'Exclude this item'"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
          
          <!-- Final Actions -->
          <el-card shadow="hover" class="actions-card">
            <div class="final-actions">
              <el-button
                type="primary"
                size="large"
                :icon="Check"
                @click="processAndStore"
                :loading="isStoring"
                :disabled="processedData.length === 0"
                :aria-label="'Process and store data to database'"
                class="store-button"
              >
                One-click Clean & Store
              </el-button>
              
              <div class="action-info">
                <p class="action-description">
                  Process all data and store to <code>weibo_core_data</code> table
                </p>
                <div class="action-stats">
                  <span>{{ processedData.length }} items ready</span>
                  <span>Est. {{ estimatedStoreTime }}s</span>
                </div>
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
  DataBoard, FolderOpened, Coin, Document, Setting, RefreshRight,
  VideoPlay, VideoPause, VideoStop, Loading, TrendCharts, Connection,
  DataAnalysis, CircleCheck, CopyDocument, Warning, View, Delete, Check,
  Refresh, ArrowDown, Operation, Filter, Search, Edit
} from '@element-plus/icons-vue'
import WordCloud from '@/components/common/WordCloud.vue'
import ComparisonPanel from '@/components/common/ComparisonPanel.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface ProcessingConfig {
  dataSource: 'hdfs' | 'mysql' | 'sample'
  hdfsPath: string
  fileFormat: string
  mysqlTable: string
  dateRange: [Date, Date] | null
  steps: string[]
  dedupThreshold: number
  normalizationMethod: string
  tokenizer: string
  stopwordList: string[]
  emojiProcessing: string
}

interface CleaningStep {
  key: string
  title: string
  description: string
  icon: any
}

interface RawDataItem {
  id: string
  text: string
  metadata: Record<string, any>
}

interface ProcessedDataItem {
  id: string
  originalText: string
  processedText: string
  tokens: string[]
  metadata: Record<string, any>
  status: 'valid' | 'invalid' | 'duplicate'
}

interface WordFrequency {
  text: string
  frequency: number
  weight?: number
}

interface SimilarityCluster {
  id: number
  items: ProcessedDataItem[]
  similarity: number
}

interface ComparisonItem {
  id: string
  original: string
  processed: string
  metadata?: Record<string, any>
}

// Reactive data
const config = ref<ProcessingConfig>({
  dataSource: 'sample',
  hdfsPath: '/user/hadoop/weibo/raw/',
  fileFormat: 'json',
  mysqlTable: 'weibo_raw_data',
  dateRange: null,
  steps: ['deduplication', 'normalization', 'tokenization'],
  dedupThreshold: 0.85,
  normalizationMethod: 'lowercase',
  tokenizer: 'jieba',
  stopwordList: ['zh_common', 'weibo'],
  emojiProcessing: 'remove'
})

const rawData = ref<RawDataItem[]>([])
const processedData = ref<ProcessedDataItem[]>([])
const isProcessing = ref(false)
const isPaused = ref(false)
const isLoadingSources = ref(false)
const isStoring = ref(false)
const processingProgress = ref(0)
const processingTime = ref(0)
const processingRate = ref(0)
const currentStep = ref('')

// Similarity detection
const similarityEnabled = ref(false)
const similarityThreshold = ref(0.85)
const similarityClusters = ref<SimilarityCluster[]>([])
const similarityStats = ref({
  totalClusters: 0,
  avgSimilarity: 0,
  duplicates: 0
})

// Word cloud data
const wordFrequencyData = ref<WordFrequency[]>([])

// Comparison data
const comparisonData = ref<ComparisonItem[]>([])
const showDifferences = ref(true)

// Preview data
const previewData = ref<ProcessedDataItem[]>([])
const selectedPreviewItems = ref<ProcessedDataItem[]>([])

// Statistics
const processingStats = ref({
  originalCount: 0,
  validCount: 0,
  duplicateCount: 0,
  noiseRate: 0
})

// Constants
const cleaningSteps = ref<CleaningStep[]>([
  {
    key: 'deduplication',
    title: 'Deduplication',
    description: 'Remove duplicate and similar content',
    icon: CopyDocument
  },
  {
    key: 'denoising',
    title: 'Denoising',
    description: 'Remove noise and irrelevant content',
    icon: Filter
  },
  {
    key: 'normalization',
    title: 'Normalization',
    description: 'Normalize text format and encoding',
    icon: Edit
  },
  {
    key: 'tokenization',
    title: 'Tokenization',
    description: 'Split text into tokens/words',
    icon: Search
  },
  {
    key: 'stopwords',
    title: 'Stop Words',
    description: 'Remove common stop words',
    icon: Operation
  },
  {
    key: 'emoji',
    title: 'Emoji Processing',
    description: 'Handle emojis and special characters',
    icon: ArrowDown
  }
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
  if (isProcessing.value) return 'Processing'
  return 'Idle'
}

const getStatusTagType = () => {
  if (isPaused.value) return 'warning'
  if (isProcessing.value) return 'success'
  return 'info'
}

const estimatedStoreTime = computed(() => {
  return Math.ceil(processedData.value.length / 100) // Rough estimate
})

// Methods
const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'valid': 'success',
    'invalid': 'danger',
    'duplicate': 'warning'
  }
  return statusMap[status] || 'info'
}

const handleDataSourceChange = async () => {
  isLoadingSources.value = true
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate loading data from different sources
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        if (config.value.dataSource === 'sample') {
          // Load sample data
          rawData.value = generateSampleData(1000)
        } else if (config.value.dataSource === 'hdfs') {
          // Load from HDFS
          rawData.value = await loadFromHDFS()
        } else if (config.value.dataSource === 'mysql') {
          // Load from MySQL
          rawData.value = await loadFromMySQL()
        }
        
        ElMessage.success(`Loaded ${rawData.value.length} items from ${config.value.dataSource}`)
      },
      'Data Source Loading',
      { showLoading: false }
    )
  } finally {
    isLoadingSources.value = false
  }
}

const refreshDataSources = async () => {
  await handleDataSourceChange()
}

const toggleStep = (stepKey: string) => {
  const index = config.value.steps.indexOf(stepKey)
  if (index > -1) {
    config.value.steps.splice(index, 1)
  } else {
    config.value.steps.push(stepKey)
  }
}

const resetCleaningSteps = () => {
  config.value.steps = ['deduplication', 'normalization', 'tokenization']
  ElMessage.info('Cleaning steps reset to default')
}

const startProcessing = async () => {
  if (rawData.value.length === 0) {
    ElMessage.warning('No data to process')
    return
  }
  
  if (config.value.steps.length === 0) {
    ElMessage.warning('Please select at least one cleaning step')
    return
  }
  
  isProcessing.value = true
  isPaused.value = false
  processedData.value = []
  processingProgress.value = 0
  processingTime.value = 0
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate processing steps
        const steps = config.value.steps
        let processedItems = [...rawData.value]
        
        for (let i = 0; i < steps.length; i++) {
          const step = steps[i]
          currentStep.value = step
          
          // Simulate step processing
          await new Promise(resolve => setTimeout(resolve, 2000))
          
          processedItems = await processStep(processedItems, step)
          processedData.value = processedItems
          
          processingProgress.value = Math.round(((i + 1) / steps.length) * 100)
          
          // Update statistics
          updateProcessingStats()
          
          // Update word frequency
          updateWordFrequency()
          
          // Update comparison data
          updateComparisonData()
          
          // Update preview data
          updatePreviewData()
          
          // Update similarity clustering if enabled
          if (similarityEnabled.value) {
            await updateSimilarityClustering()
          }
        }
        
        ElNotification({
          title: 'Processing Completed',
          message: `Successfully processed ${processedData.value.length} items`,
          type: 'success',
          duration: 5000
        })
      },
      'Data Processing',
      { showLoading: false }
    )
  } finally {
    isProcessing.value = false
    currentStep.value = ''
  }
}

const pauseProcessing = () => {
  isPaused.value = true
  ElMessage.info('Processing paused')
}

const stopProcessing = () => {
  isProcessing.value = false
  isPaused.value = false
  processingProgress.value = 0
  currentStep.value = ''
  ElMessage.info('Processing stopped')
}

const processStep = async (items: any[], step: string): Promise<any[]> => {
  // Simulate different processing steps
  switch (step) {
    case 'deduplication':
      return items.filter((item, index) => {
        // Simple deduplication based on text similarity
        return items.findIndex(other => 
          other.text === item.text && other.id !== item.id
        ) === index
      })
    
    case 'denoising':
      return items.map(item => ({
        ...item,
        text: item.text.replace(/[^\w\s\u4e00-\u9fff]/g, '') // Remove non-word chars
      }))
    
    case 'normalization':
      return items.map(item => ({
        ...item,
        text: config.value.normalizationMethod === 'lowercase' 
          ? item.text.toLowerCase()
          : item.text
      }))
    
    case 'tokenization':
      return items.map(item => ({
        ...item,
        tokens: item.text.split(/\s+/).filter(token => token.length > 0)
      }))
    
    case 'stopwords':
      return items.map(item => ({
        ...item,
        tokens: item.tokens?.filter(token => 
          !['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'].includes(token.toLowerCase())
        ) || []
      }))
    
    case 'emoji':
      return items.map(item => ({
        ...item,
        text: config.value.emojiProcessing === 'remove' 
          ? item.text.replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]/g, '')
          : item.text
      }))
    
    default:
      return items
  }
}

const updateProcessingStats = () => {
  processingStats.value = {
    originalCount: rawData.value.length,
    validCount: processedData.value.length,
    duplicateCount: rawData.value.length - processedData.value.length,
    noiseRate: Math.round(((rawData.value.length - processedData.value.length) / rawData.value.length) * 100)
  }
}

const updateWordFrequency = () => {
  const wordMap = new Map<string, number>()
  
  processedData.value.forEach(item => {
    if (item.tokens) {
      item.tokens.forEach(token => {
        wordMap.set(token, (wordMap.get(token) || 0) + 1)
      })
    }
  })
  
  wordFrequencyData.value = Array.from(wordMap.entries())
    .map(([text, frequency]) => ({ text, frequency }))
    .sort((a, b) => b.frequency - a.frequency)
    .slice(0, 20)
}

const updateComparisonData = () => {
  comparisonData.value = processedData.value.slice(0, 10).map(item => ({
    id: item.id,
    original: item.originalText || item.text,
    processed: item.processedText || item.text
  }))
}

const updatePreviewData = () => {
  previewData.value = processedData.value.slice(0, 50).map(item => ({
    ...item,
    originalText: item.originalText || item.text,
    processedText: item.processedText || item.text,
    status: 'valid'
  }))
}

const updateSimilarityClustering = async () => {
  if (!similarityEnabled.value) return
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate SimHash clustering
        const clusters: SimilarityCluster[] = []
        const processed = new Set<string>()
        
        processedData.value.forEach((item, index) => {
          if (processed.has(item.id)) return
          
          const cluster: SimilarityCluster = {
            id: clusters.length + 1,
            items: [item],
            similarity: 1.0
          }
          
          // Find similar items
          processedData.value.forEach((otherItem, otherIndex) => {
            if (index !== otherIndex && !processed.has(otherItem.id)) {
              const similarity = calculateSimilarity(item, otherItem)
              if (similarity >= similarityThreshold.value) {
                cluster.items.push(otherItem)
                processed.add(otherItem.id)
              }
            }
          })
          
          clusters.push(cluster)
          processed.add(item.id)
        })
        
        similarityClusters.value = clusters
        
        // Update statistics
        similarityStats.value = {
          totalClusters: clusters.length,
          avgSimilarity: Math.round(clusters.reduce((sum, cluster) => sum + cluster.similarity, 0) / clusters.length),
          duplicates: clusters.reduce((sum, cluster) => sum + cluster.items.length - 1, 0)
        }
      },
      'Similarity Clustering',
      { showLoading: false }
    )
  } catch (error) {
    console.error('Failed to update similarity clustering:', error)
  }
}

const calculateSimilarity = (item1: ProcessedDataItem, item2: ProcessedDataItem): number => {
  // Simple similarity calculation (can be enhanced with SimHash)
  const text1 = item1.processedText || item1.text
  const text2 = item2.processedText || item2.text
  
  const words1 = text1.toLowerCase().split(/\s+/)
  const words2 = text2.toLowerCase().split(/\s+/)
  
  const commonWords = words1.filter(word => words2.includes(word))
  const totalWords = new Set([...words1, ...words2]).size
  
  return totalWords > 0 ? commonWords.length / totalWords : 0
}

const handleWordClick = (word: WordFrequency) => {
  // Highlight word in comparison panel
  ElMessage.info(`Selected word: ${word.text} (${word.frequency} occurrences)`)
  
  // Update comparison to highlight selected word
  if (comparisonRef.value) {
    // This would need to be implemented in the ComparisonPanel component
    comparisonRef.value.highlightWord(word.text)
  }
}

const handleWordHover = (word: WordFrequency) => {
  // Handle word hover if needed
}

const handleComparisonChange = (item: ComparisonItem, index: number) => {
  // Handle comparison change
}

const handlePreviewSelection = (selection: ProcessedDataItem[]) => {
  selectedPreviewItems.value = selection
}

const selectAllPreview = () => {
  selectedPreviewItems.value = [...previewData.value]
}

const excludeSelected = () => {
  const selectedIds = new Set(selectedPreviewItems.value.map(item => item.id))
  previewData.value = previewData.value.filter(item => !selectedIds.has(item.id))
  selectedPreviewItems.value = []
  ElMessage.success(`Excluded ${selectedIds.size} items`)
}

const excludeItem = (item: ProcessedDataItem) => {
  previewData.value = previewData.value.filter(p => p.id !== item.id)
  ElMessage.success(`Excluded item ${item.id}`)
}

const viewItemDetails = (item: ProcessedDataItem) => {
  ElMessage.info(`Viewing details for item ${item.id}`)
  // Implement detail view logic
}

const processAndStore = async () => {
  if (processedData.value.length === 0) {
    ElMessage.warning('No processed data to store')
    return
  }
  
  isStoring.value = true
  
  try {
    await withErrorHandling(
      async () => {
        // Simulate database storage
        await new Promise(resolve => setTimeout(resolve, 3000))
        
        ElNotification({
          title: 'Data Stored Successfully',
          message: `${processedData.value.length} items stored to weibo_core_data table`,
          type: 'success',
          duration: 5000
        })
        
        // Clear processed data after successful storage
        processedData.value = []
        processingStats.value = {
          originalCount: 0,
          validCount: 0,
          duplicateCount: 0,
          noiseRate: 0
        }
      },
      'Data Storage',
      { showLoading: false }
    )
  } finally {
    isStoring.value = false
  }
}

// Helper functions
const generateSampleData = (count: number): RawDataItem[] => {
  const samples = [
    'AI is transforming the world with machine learning',
    'Vue.js is a progressive JavaScript framework',
    'Python is great for data science and AI',
    'Machine learning algorithms are getting better',
    'Data preprocessing is crucial for ML models',
    'Natural language processing is fascinating',
    'Deep learning requires large datasets',
    'Cloud computing enables scalable solutions',
    'Blockchain technology is revolutionizing finance',
    'Internet of Things connects everything'
  ]
  
  return Array.from({ length: count }, (_, i) => ({
    id: `sample_${i + 1}`,
    text: samples[i % samples.length] + ` #${i}`,
    metadata: {
      source: 'sample',
      createdAt: new Date(Date.now() - Math.random() * 86400000 * 7),
      length: samples[i % samples.length].length
    }
  }))
}

const loadFromHDFS = async (): Promise<RawDataItem[]> => {
  // Simulate HDFS loading
  return generateSampleData(5000)
}

const loadFromMySQL = async (): Promise<RawDataItem[]> => {
  // Simulate MySQL loading
  return generateSampleData(2000)
}

// Lifecycle
onMounted(async () => {
  // Load initial sample data
  await handleDataSourceChange()
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})
</script>

<style scoped>
.preprocess-enhanced {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.preprocess-header {
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

.processing-stats {
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
.control-card,
.progress-card,
.wordcloud-card,
.similarity-card,
.comparison-card,
.stats-card,
.preview-card,
.actions-card {
  margin-bottom: var(--spacing-lg);
}

.source-option {
  display: block;
  width: 100%;
  margin-bottom: var(--spacing-sm);
}

.option-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  transition: var(--transition-fast);
}

.option-content:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}

.option-details {
  flex: 1;
}

.option-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.option-desc {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.cleaning-steps {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.step-item {
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  padding: var(--spacing-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.step-item:hover {
  border-color: var(--color-primary);
}

.step-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-xs);
}

.step-title {
  flex: 1;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.step-description {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
}

.step-options {
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-border-lighter);
}

.processing-controls {
  display: flex;
  justify-content: center;
  padding: var(--spacing-lg);
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

.similarity-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.similarity-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-sm);
}

.similarity-stats .stat-item {
  text-align: center;
}

.stat-value {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.stat-label {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.cluster-preview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.cluster-item {
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  padding: var(--spacing-sm);
}

.cluster-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.cluster-id {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.cluster-items {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.cluster-item-text {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
  background: var(--color-bg-hover);
  padding: 2px 6px;
  border-radius: var(--border-radius-xs);
}

.more-items {
  font-size: var(--font-size-tiny);
  color: var(--color-info);
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--border-radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.original {
  background: var(--color-info);
}

.stat-icon.valid {
  background: var(--color-success);
}

.stat-icon.duplicates {
  background: var(--color-warning);
}

.stat-icon.noise {
  background: var(--color-danger);
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

.preview-actions {
  display: flex;
  gap: var(--spacing-xs);
}

.final-actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.store-button {
  width: 100%;
}

.action-info {
  text-align: center;
}

.action-description {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-xs) 0;
}

.action-stats {
  display: flex;
  justify-content: center;
  gap: var(--spacing-lg);
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
  .preprocess-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .statistics-grid {
    grid-template-columns: 1fr;
  }
  
  .similarity-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .preprocess-enhanced {
    padding: var(--spacing-md);
  }
  
  .preprocess-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .processing-stats {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .processing-controls .el-button-group {
    display: flex;
    flex-direction: column;
    width: 100%;
  }
  
  .processing-controls .el-button {
    width: 100%;
  }
  
  .final-actions {
    gap: var(--spacing-sm);
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .config-card,
  .control-card,
  .progress-card,
  .wordcloud-card,
  .similarity-card,
  .comparison-card,
  .stats-card,
  .preview-card,
  .actions-card {
    border-width: 2px;
  }
}
</style>
