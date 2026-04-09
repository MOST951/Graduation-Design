<template>
  <div class="pipeline-manager">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header -->
    <div class="manager-header">
      <div class="header-left">
        <h1 class="page-title">Pipeline Manager</h1>
        <div class="current-status">
          <el-tag
            :type="getCurrentStatusType()"
            size="large"
            :aria-label="`Current pipeline status: ${getCurrentStatusText()}`"
          >
            <el-icon v-if="isRunning" class="rotating"><Loading /></el-icon>
            {{ getCurrentStatusText() }}
          </el-tag>
        </div>
      </div>
      
      <div class="header-right">
        <div class="action-buttons">
          <el-button
            type="primary"
            size="large"
            :icon="VideoPlay"
            @click="showConfigDialog"
            :disabled="isRunning"
            :aria-label="'Start new pipeline'"
          >
            New Pipeline
          </el-button>
          
          <el-button
            v-if="currentPipeline"
            type="warning"
            size="large"
            :icon="VideoPause"
            @click="pausePipeline"
            :disabled="!canPause"
            :aria-label="'Pause current pipeline'"
          >
            Pause
          </el-button>
          
          <el-button
            v-if="currentPipeline"
            type="danger"
            size="large"
            :icon="VideoStop"
            @click="stopPipeline"
            :disabled="!canStop"
            :aria-label="'Stop current pipeline'"
          >
            Stop
          </el-button>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Left Panel: Pipeline Progress -->
        <el-col :span="12">
          <el-card shadow="hover" class="progress-card">
            <template #header>
              <div class="card-header">
                <el-icon><Operation /></el-icon>
                <span>Pipeline Progress</span>
                <div class="progress-info" v-if="currentPipeline">
                  <span class="info-item">
                    Task ID: <code>{{ currentPipeline.taskId }}</code>
                  </span>
                  <span class="info-item">
                    Started: {{ formatTime(currentPipeline.startTime) }}
                  </span>
                </div>
              </div>
            </template>
            
            <!-- Pipeline Steps -->
            <PipelineSteps
              v-if="currentPipeline"
              :stages="currentPipeline.stages"
              :can-pause="currentPipeline.executionMode === 'async'"
              :show-overall-progress="true"
              @retry-stage="handleRetryStage"
              @pause-stage="handlePauseStage"
              @resume-stage="handleResumeStage"
              @view-logs="handleViewLogs"
            />
            
            <!-- No Active Pipeline -->
            <div v-else class="no-pipeline">
              <el-empty description="No active pipeline">
                <el-button type="primary" @click="showConfigDialog">
                  Start New Pipeline
                </el-button>
              </el-empty>
            </div>
          </el-card>
        </el-col>
        
        <!-- Right Panel: History -->
        <el-col :span="12">
          <el-card shadow="hover" class="history-card">
            <template #header>
              <div class="card-header">
                <el-icon><Clock /></el-icon>
                <span>Pipeline History</span>
                <div class="history-actions">
                  <el-button
                    text
                    size="small"
                    @click="refreshHistory"
                    :loading="isRefreshingHistory"
                    :aria-label="'Refresh pipeline history'"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                  <el-button
                    text
                    size="small"
                    @click="cleanHistory"
                    :disabled="pipelineHistory.length === 0"
                    :aria-label="'Clean pipeline history'"
                  >
                    <el-icon><Delete /></el-icon>
                    Clean
                  </el-button>
                </div>
              </div>
            </template>
            
            <!-- History Table -->
            <el-table
              :data="pipelineHistory"
              height="500"
              size="small"
              :default-sort="{ prop: 'startTime', order: 'descending' }"
              @sort-change="handleHistorySort"
              :aria-label="'Pipeline history table'"
            >
              <el-table-column prop="batchId" label="Batch ID" width="120" sortable>
                <template #default="{ row }">
                  <el-button
                    text
                    type="primary"
                    @click="viewBatchDetails(row)"
                    :aria-label="`View details for batch ${row.batchId}`"
                  >
                    {{ row.batchId }}
                  </el-button>
                </template>
              </el-table-column>
              
              <el-table-column prop="startTime" label="Start Time" width="120" sortable>
                <template #default="{ row }">
                  {{ formatDateTime(row.startTime) }}
                </template>
              </el-table-column>
              
              <el-table-column prop="endTime" label="End Time" width="120" sortable>
                <template #default="{ row }">
                  {{ row.endTime ? formatDateTime(row.endTime) : 'N/A' }}
                </template>
              </el-table-column>
              
              <el-table-column prop="totalDuration" label="Duration" width="80" sortable>
                <template #default="{ row }">
                  {{ formatDuration(row.totalDuration) }}
                </template>
              </el-table-column>
              
              <el-table-column prop="status" label="Status" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="getStatusTagType(row.status)"
                    size="small"
                    :aria-label="`Status: ${row.status}`"
                  >
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <el-table-column prop="processedCount" label="Processed" width="80" sortable>
                <template #default="{ row }">
                  {{ row.processedCount?.toLocaleString() || 'N/A' }}
                </template>
              </el-table-column>
              
              <el-table-column label="Actions" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button
                    text
                    size="small"
                    @click="viewBatchDetails(row)"
                    :aria-label="'View batch details'"
                  >
                    <el-icon><View /></el-icon>
                  </el-button>
                  <el-button
                    text
                    size="small"
                    type="danger"
                    @click="deleteBatch(row)"
                    :disabled="row.status === 'running'"
                    :aria-label="'Delete batch record'"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- Configuration Dialog -->
    <PipelineConfigDialog
      v-model:visible="configDialogVisible"
      :default-config="defaultConfig"
      @confirm="handleConfigConfirm"
      @cancel="handleConfigCancel"
    />
    
    <!-- Batch Details Dialog -->
    <el-dialog
      v-model="batchDetailsVisible"
      :title="`Batch Details - ${selectedBatch?.batchId}`"
      width="800px"
      :aria-label="'Batch details dialog'"
    >
      <div v-if="selectedBatch" class="batch-details">
        <!-- Batch Summary -->
        <div class="batch-summary">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Batch ID">
              {{ selectedBatch.batchId }}
            </el-descriptions-item>
            <el-descriptions-item label="Status">
              <el-tag :type="getStatusTagType(selectedBatch.status)">
                {{ getStatusText(selectedBatch.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Start Time">
              {{ formatDateTime(selectedBatch.startTime) }}
            </el-descriptions-item>
            <el-descriptions-item label="End Time">
              {{ selectedBatch.endTime ? formatDateTime(selectedBatch.endTime) : 'N/A' }}
            </el-descriptions-item>
            <el-descriptions-item label="Duration">
              {{ formatDuration(selectedBatch.totalDuration) }}
            </el-descriptions-item>
            <el-descriptions-item label="Processed Count">
              {{ selectedBatch.processedCount?.toLocaleString() || 'N/A' }}
            </el-descriptions-item>
            <el-descriptions-item label="Execution Mode">
              {{ selectedBatch.executionMode?.toUpperCase() || 'N/A' }}
            </el-descriptions-item>
            <el-descriptions-item label="Task ID">
              <code>{{ selectedBatch.taskId || 'N/A' }}</code>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        
        <!-- Stage Details -->
        <div class="stage-details">
          <h3>Stage Details</h3>
          <el-table :data="selectedBatch.stages" size="small">
            <el-table-column prop="name" label="Stage" />
            <el-table-column prop="status" label="Status" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="processedCount" label="Processed" width="100" />
            <el-table-column prop="duration" label="Duration" width="100">
              <template #default="{ row }">
                {{ formatDuration(row.duration) }}
              </template>
            </el-table-column>
            <el-table-column prop="error" label="Error" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.error" class="error-text">{{ row.error }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
    
    <!-- Stage Logs Dialog -->
    <el-dialog
      v-model="logsDialogVisible"
      :title="`Stage Logs - ${selectedStage?.name}`"
      width="600px"
      :aria-label="'Stage logs dialog'"
    >
      <div v-if="selectedStage" class="stage-logs">
        <div class="logs-header">
          <span class="logs-info">
            Total: {{ stageLogs.length }} entries
          </span>
          <el-button text size="small" @click="clearLogs">
            Clear
          </el-button>
        </div>
        
        <div class="logs-content">
          <div
            v-for="(log, index) in stageLogs"
            :key="index"
            class="log-item"
            :class="log.level"
          >
            <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
            <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import {
  Operation, Clock, VideoPlay, VideoPause, VideoStop, Loading, Refresh, Delete,
  View
} from '@element-plus/icons-vue'
import PipelineConfigDialog from '@/components/common/PipelineConfigDialog.vue'
import PipelineSteps from '@/components/common/PipelineSteps.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface PipelineConfig {
  presetType: 'custom' | 'tech' | 'business' | 'entertainment' | 'news'
  keywordsText: string
  maxCount: number
  executionMode: 'sync' | 'async'
  timeout: number
  retryAttempts: number
  enableNotifications: boolean
  saveAsDefault: boolean
}

interface PipelineStage {
  key: string
  name: string
  description: string
  status: 'waiting' | 'running' | 'success' | 'failed' | 'paused'
  processedCount: number
  duration: number
  startTime?: Date
  endTime?: Date
  error?: string
  isRetrying?: boolean
}

interface Pipeline {
  taskId: string
  batchId: string
  config: PipelineConfig
  stages: PipelineStage[]
  startTime: Date
  endTime?: Date
  status: 'running' | 'completed' | 'failed' | 'paused' | 'cancelled'
  totalProcessed: number
  executionMode: 'sync' | 'async'
}

interface PipelineHistory {
  batchId: string
  taskId: string
  startTime: Date
  endTime?: Date
  totalDuration: number
  status: 'running' | 'completed' | 'failed' | 'paused' | 'cancelled'
  processedCount?: number
  executionMode: 'sync' | 'async'
  stages: PipelineStage[]
}

interface LogEntry {
  timestamp: Date
  level: 'info' | 'warning' | 'error'
  message: string
}

// Reactive data
const configDialogVisible = ref(false)
const batchDetailsVisible = ref(false)
const logsDialogVisible = ref(false)
const isRefreshingHistory = ref(false)
const currentPipeline = ref<Pipeline | null>(null)
const pipelineHistory = ref<PipelineHistory[]>([])
const selectedBatch = ref<PipelineHistory | null>(null)
const selectedStage = ref<PipelineStage | null>(null)
const stageLogs = ref<LogEntry[]>([])
const defaultConfig = ref<Partial<PipelineConfig>>({})
const pollingTimer = ref<NodeJS.Timeout | null>(null)

// Notification permission
const notificationPermission = ref<NotificationPermission>('default')

// Computed properties
const isRunning = computed(() => {
  return currentPipeline.value?.status === 'running'
})

const canPause = computed(() => {
  return isRunning.value && currentPipeline.value?.executionMode === 'async'
})

const canStop = computed(() => {
  return isRunning.value
})

const getCurrentStatusText = () => {
  if (!currentPipeline.value) return 'No Active Pipeline'
  return currentPipeline.value.status.charAt(0).toUpperCase() + currentPipeline.value.status.slice(1)
}

const getCurrentStatusType = () => {
  const statusMap = {
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'paused': 'info',
    'cancelled': 'info'
  }
  return statusMap[currentPipeline.value?.status as keyof typeof statusMap] || 'info'
}

// Methods
const getStatusTagType = (status: string) => {
  const typeMap = {
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'paused': 'info',
    'cancelled': 'info'
  }
  return typeMap[status as keyof typeof typeMap] || 'info'
}

const getStatusText = (status: string) => {
  const textMap = {
    'running': 'Running',
    'completed': 'Completed',
    'failed': 'Failed',
    'paused': 'Paused',
    'cancelled': 'Cancelled'
  }
  return textMap[status as keyof typeof textMap] || status
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatDateTime = (date: Date) => {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (duration: number) => {
  if (duration === 0) return '0s'
  
  const hours = Math.floor(duration / 3600)
  const minutes = Math.floor((duration % 3600) / 60)
  const seconds = Math.floor(duration % 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  } else {
    return `${seconds}s`
  }
}

const formatLogTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// Dialog management
const showConfigDialog = () => {
  configDialogVisible.value = true
}

const handleConfigConfirm = async (config: PipelineConfig) => {
  try {
    await withErrorHandling(
      async () => {
        configDialogVisible.value = false
        
        // Start pipeline
        await startPipeline(config)
      },
      'Pipeline Start',
      { showLoading: false }
    )
  } catch (error) {
    console.error('Failed to start pipeline:', error)
  }
}

const handleConfigCancel = () => {
  configDialogVisible.value = false
}

// Pipeline operations
const startPipeline = async (config: PipelineConfig) => {
  const pipeline: Pipeline = {
    taskId: `task_${Date.now()}`,
    batchId: `batch_${Date.now()}`,
    config,
    stages: createPipelineStages(),
    startTime: new Date(),
    status: 'running',
    totalProcessed: 0,
    executionMode: config.executionMode
  }
  
  currentPipeline.value = pipeline
  
  // Add to history
  const historyItem: PipelineHistory = {
    batchId: pipeline.batchId,
    taskId: pipeline.taskId,
    startTime: pipeline.startTime,
    totalDuration: 0,
    status: 'running',
    executionMode: pipeline.executionMode,
    stages: [...pipeline.stages]
  }
  
  pipelineHistory.value.unshift(historyItem)
  
  // Start simulation
  if (config.executionMode === 'async') {
    startAsyncSimulation(pipeline)
  } else {
    startSyncSimulation(pipeline)
  }
  
  ElMessage.success('Pipeline started successfully')
}

const createPipelineStages = (): PipelineStage[] => {
  return [
    {
      key: 'data_collection',
      name: 'Data Collection',
      description: 'Collect raw data from various sources',
      status: 'waiting',
      processedCount: 0,
      duration: 0
    },
    {
      key: 'data_preprocessing',
      name: 'Data Preprocessing',
      description: 'Clean and preprocess collected data',
      status: 'waiting',
      processedCount: 0,
      duration: 0
    },
    {
      key: 'sentiment_analysis',
      name: 'Sentiment Analysis',
      description: 'Analyze sentiment of preprocessed data',
      status: 'waiting',
      processedCount: 0,
      duration: 0
    },
    {
      key: 'dual_dimension_ranking',
      name: 'Dual Dimension Ranking',
      description: 'Rank data using sentiment and popularity',
      status: 'waiting',
      processedCount: 0,
      duration: 0
    },
    {
      key: 'result_storage',
      name: 'Result Storage',
      description: 'Store processed results to database',
      status: 'waiting',
      processedCount: 0,
      duration: 0
    }
  ]
}

const startAsyncSimulation = (pipeline: Pipeline) => {
  let currentStageIndex = 0
  
  const processStage = async (stageIndex: number) => {
    if (!currentPipeline.value || currentPipeline.value.status !== 'running') return
    
    const stage = pipeline.stages[stageIndex]
    stage.status = 'running'
    stage.startTime = new Date()
    stage.processedCount = 0
    
    // Simulate stage processing
    const processingTime = 3000 + Math.random() * 2000
    const interval = 100
    
    const processInterval = setInterval(() => {
      if (!currentPipeline.value || currentPipeline.value.status !== 'running') {
        clearInterval(processInterval)
        return
      }
      
      stage.processedCount += Math.floor(Math.random() * 100 + 50)
      stage.duration = (Date.now() - stage.startTime.getTime()) / 1000
      
      // Update history
      updateHistoryStage(pipeline, stageIndex, stage)
    }, interval)
    
    setTimeout(() => {
      clearInterval(processInterval)
      
      const success = Math.random() > 0.2 // 80% success rate
      
      if (success) {
        stage.status = 'success'
        stage.endTime = new Date()
        stage.processedCount = Math.floor(Math.random() * 10000 + 5000)
        stage.duration = (stage.endTime.getTime() - stage.startTime.getTime()) / 1000
        
        // Update history
        updateHistoryStage(pipeline, stageIndex, stage)
        
        // Move to next stage
        if (stageIndex < pipeline.stages.length - 1) {
          setTimeout(() => processStage(stageIndex + 1), 500)
        } else {
          completePipeline(pipeline)
        }
      } else {
        stage.status = 'failed'
        stage.endTime = new Date()
        stage.error = 'Stage processing failed due to internal error'
        stage.duration = (stage.endTime.getTime() - stage.startTime.getTime()) / 1000
        
        // Update history
        updateHistoryStage(pipeline, stageIndex, stage)
        
        failPipeline(pipeline, stage)
      }
    }, processingTime)
  }
  
  // Start first stage
  processStage(currentStageIndex)
}

const startSyncSimulation = async (pipeline: Pipeline) => {
  for (let i = 0; i < pipeline.stages.length; i++) {
    if (!currentPipeline.value || currentPipeline.value.status !== 'running') return
    
    const stage = pipeline.stages[i]
    stage.status = 'running'
    stage.startTime = new Date()
    
    // Simulate stage processing
    await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 1000))
    
    const success = Math.random() > 0.1 // 90% success rate
    
    if (success) {
      stage.status = 'success'
      stage.endTime = new Date()
      stage.processedCount = Math.floor(Math.random() * 10000 + 5000)
      stage.duration = (stage.endTime.getTime() - stage.startTime.getTime()) / 1000
      
      // Update history
      updateHistoryStage(pipeline, i, stage)
    } else {
      stage.status = 'failed'
      stage.endTime = new Date()
      stage.error = 'Stage processing failed'
      stage.duration = (stage.endTime.getTime() - stage.startTime.getTime()) / 1000
      
      // Update history
      updateHistoryStage(pipeline, i, stage)
      
      failPipeline(pipeline, stage)
      return
    }
  }
  
  completePipeline(pipeline)
}

const updateHistoryStage = (pipeline: Pipeline, stageIndex: number, stage: PipelineStage) => {
  const historyItem = pipelineHistory.value.find(item => item.batchId === pipeline.batchId)
  if (historyItem) {
    historyItem.stages[stageIndex] = { ...stage }
  }
}

const completePipeline = (pipeline: Pipeline) => {
  pipeline.status = 'completed'
  pipeline.endTime = new Date()
  pipeline.totalProcessed = pipeline.stages.reduce((sum, stage) => sum + stage.processedCount, 0)
  
  // Update history
  const historyItem = pipelineHistory.value.find(item => item.batchId === pipeline.batchId)
  if (historyItem) {
    historyItem.status = 'completed'
    historyItem.endTime = pipeline.endTime
    historyItem.totalDuration = (pipeline.endTime.getTime() - pipeline.startTime.getTime()) / 1000
    historyItem.processedCount = pipeline.totalProcessed
  }
  
  // Send notification
  sendNotification('Pipeline Completed', `Pipeline ${pipeline.batchId} completed successfully`, 'success')
  
  ElMessage.success('Pipeline completed successfully')
  
  // Clear current pipeline
  setTimeout(() => {
    currentPipeline.value = null
  }, 2000)
}

const failPipeline = (pipeline: Pipeline, failedStage: PipelineStage) => {
  pipeline.status = 'failed'
  pipeline.endTime = new Date()
  
  // Update history
  const historyItem = pipelineHistory.value.find(item => item.batchId === pipeline.batchId)
  if (historyItem) {
    historyItem.status = 'failed'
    historyItem.endTime = pipeline.endTime
    historyItem.totalDuration = (pipeline.endTime.getTime() - pipeline.startTime.getTime()) / 1000
  }
  
  // Send notification
  sendNotification('Pipeline Failed', `Pipeline ${pipeline.batchId} failed at stage: ${failedStage.name}`, 'error')
  
  ElMessage.error(`Pipeline failed at stage: ${failedStage.name}`)
  
  // Clear current pipeline
  setTimeout(() => {
    currentPipeline.value = null
  }, 2000)
}

const pausePipeline = () => {
  if (!currentPipeline.value) return
  
  currentPipeline.value.status = 'paused'
  
  // Update history
  const historyItem = pipelineHistory.value.find(item => item.batchId === currentPipeline.value.batchId)
  if (historyItem) {
    historyItem.status = 'paused'
  }
  
  ElMessage.info('Pipeline paused')
}

const stopPipeline = () => {
  if (!currentPipeline.value) return
  
  currentPipeline.value.status = 'cancelled'
  currentPipeline.value.endTime = new Date()
  
  // Update history
  const historyItem = pipelineHistory.value.find(item => item.batchId === currentPipeline.value.batchId)
  if (historyItem) {
    historyItem.status = 'cancelled'
    historyItem.endTime = currentPipeline.value.endTime
    historyItem.totalDuration = (currentPipeline.value.endTime.getTime() - currentPipeline.value.startTime.getTime()) / 1000
  }
  
  ElMessage.info('Pipeline cancelled')
  
  currentPipeline.value = null
}

// Stage operations
const handleRetryStage = async (stageIndex: number) => {
  if (!currentPipeline.value) return
  
  const stage = currentPipeline.value.stages[stageIndex]
  stage.isRetrying = true
  stage.status = 'running'
  stage.error = undefined
  
  // Update history
  updateHistoryStage(currentPipeline.value, stageIndex, stage)
  
  // Simulate retry
  setTimeout(() => {
    const success = Math.random() > 0.3 // 70% success rate on retry
    
    if (success) {
      stage.status = 'success'
      stage.endTime = new Date()
      stage.isRetrying = false
      
      // Update history
      updateHistoryStage(currentPipeline.value, stageIndex, stage)
      
      ElMessage.success(`Stage ${stage.name} retried successfully`)
    } else {
      stage.status = 'failed'
      stage.endTime = new Date()
      stage.isRetrying = false
      stage.error = 'Retry failed again'
      
      // Update history
      updateHistoryStage(currentPipeline.value, stageIndex, stage)
      
      ElMessage.error(`Stage ${stage.name} retry failed`)
    }
  }, 2000)
}

const handlePauseStage = (stageIndex: number) => {
  if (!currentPipeline.value) return
  
  const stage = currentPipeline.value.stages[stageIndex]
  stage.status = 'paused'
  
  // Update history
  updateHistoryStage(currentPipeline.value, stageIndex, stage)
  
  ElMessage.info(`Stage ${stage.name} paused`)
}

const handleResumeStage = (stageIndex: number) => {
  if (!currentPipeline.value) return
  
  const stage = currentPipeline.value.stages[stageIndex]
  stage.status = 'running'
  
  // Update history
  updateHistoryStage(currentPipeline.value, stageIndex, stage)
  
  ElMessage.info(`Stage ${stage.name} resumed`)
}

const handleViewLogs = (stageIndex: number) => {
  if (!currentPipeline.value) return
  
  selectedStage.value = currentPipeline.value.stages[stageIndex]
  stageLogs.value = generateMockLogs(selectedStage.value)
  logsDialogVisible.value = true
}

// History operations
const refreshHistory = async () => {
  isRefreshingHistory.value = true
  
  try {
    await withErrorHandling(
      async () => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success('History refreshed')
      },
      'Refresh History',
      { showLoading: false }
    )
  } finally {
    isRefreshingHistory.value = false
  }
}

const cleanHistory = async () => {
  try {
    await ElMessageBox.confirm(
      'This will keep only the last 20 pipeline records. Are you sure?',
      'Clean History',
      {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    pipelineHistory.value = pipelineHistory.value.slice(0, 20)
    ElMessage.success('History cleaned successfully')
  } catch {
    // User cancelled
  }
}

const viewBatchDetails = (batch: PipelineHistory) => {
  selectedBatch.value = batch
  batchDetailsVisible.value = true
}

const deleteBatch = async (batch: PipelineHistory) => {
  if (batch.status === 'running') {
    ElMessage.warning('Cannot delete a running pipeline')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete batch ${batch.batchId}?`,
      'Delete Batch',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    const index = pipelineHistory.value.findIndex(item => item.batchId === batch.batchId)
    if (index > -1) {
      pipelineHistory.value.splice(index, 1)
      ElMessage.success('Batch deleted successfully')
    }
  } catch {
    // User cancelled
  }
}

const handleHistorySort = ({ prop, order }: { prop: string; order: string }) => {
  pipelineHistory.value.sort((a, b) => {
    const aValue = a[prop as keyof PipelineHistory]
    const bValue = b[prop as keyof PipelineHistory]
    
    if (aValue instanceof Date && bValue instanceof Date) {
      return order === 'ascending' ? aValue.getTime() - bValue.getTime() : bValue.getTime() - aValue.getTime()
    }
    
    return 0
  })
}

// Logs
const generateMockLogs = (stage: PipelineStage): LogEntry[] => {
  const logs: LogEntry[] = []
  const now = new Date()
  
  for (let i = 0; i < 20; i++) {
    const levels: ('info' | 'warning' | 'error')[] = ['info', 'info', 'warning']
    const level = levels[Math.floor(Math.random() * levels.length)]
    
    logs.push({
      timestamp: new Date(now.getTime() - (19 - i) * 1000),
      level,
      message: `Processing item ${i + 1} - ${level === 'error' ? 'Error occurred' : level === 'warning' ? 'Warning detected' : 'Processing normally'}`
    })
  }
  
  return logs
}

const clearLogs = () => {
  stageLogs.value = []
  ElMessage.info('Logs cleared')
}

// Notifications
const sendNotification = async (title: string, body: string, type: 'success' | 'error' | 'info') => {
  if (notificationPermission.value !== 'granted') {
    return
  }
  
  try {
    const notification = new Notification(title, {
      body,
      icon: type === 'success' ? '/success-icon.png' : type === 'error' ? '/error-icon.png' : '/info-icon.png',
      tag: 'pipeline-notification'
    })
    
    // Auto-close after 5 seconds
    setTimeout(() => {
      notification.close()
    }, 5000)
  } catch (error) {
    console.error('Failed to send notification:', error)
  }
}

const requestNotificationPermission = async () => {
  if ('Notification' in window) {
    const permission = await Notification.requestPermission()
    notificationPermission.value = permission
    
    if (permission === 'granted') {
      ElMessage.success('Browser notifications enabled')
    } else {
      ElMessage.warning('Browser notifications denied')
    }
  }
}

// Lifecycle
onMounted(async () => {
  // Request notification permission
  await requestNotificationPermission()
  
  // Load initial data
  await refreshHistory()
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})

onUnmounted(() => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
})
</script>

<style scoped>
.pipeline-manager {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.manager-header {
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

.current-status {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: var(--spacing-sm);
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

.progress-info {
  display: flex;
  gap: var(--spacing-lg);
  font-size: var(--font-size-small);
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.progress-card,
.history-card {
  margin-bottom: var(--spacing-lg);
}

.no-pipeline {
  padding: var(--spacing-xl);
  text-align: center;
}

.history-actions {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.batch-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.batch-summary {
  margin-bottom: var(--spacing-lg);
}

.stage-details h3 {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.stage-logs {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border-light);
}

.logs-info {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.logs-content {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  padding: var(--spacing-sm);
}

.log-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-tiny);
  line-height: 1.4;
}

.log-time {
  color: var(--color-text-secondary);
  min-width: 60px;
}

.log-level {
  font-weight: var(--font-weight-semibold);
  min-width: 50px;
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

.log-message {
  flex: 1;
  color: var(--color-text-primary);
}

.error-text {
  color: var(--color-danger);
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
@media (max-width: 1280px) {
  .manager-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .action-buttons {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .pipeline-manager {
    padding: var(--spacing-md);
  }
  
  .manager-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .progress-info {
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: stretch;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
  
  .history-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .progress-card,
  .history-card {
    border-width: 2px;
  }
}
</style>
