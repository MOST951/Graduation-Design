<template>
  <div class="pipeline-steps">
    <el-steps
      :active="activeStep"
      :process-status="overallStatus"
      direction="vertical"
      finish-status="success"
      :aria-label="'Pipeline progress steps'"
    >
      <el-step
        v-for="(stage, index) in stages"
        :key="stage.key"
        :title="stage.name"
        :description="stage.description"
        :status="getStepStatus(stage)"
        :icon="getStepIcon(stage)"
      >
        <template #icon>
          <div class="step-icon-wrapper">
            <el-icon v-if="getStepIcon(stage)" :class="{ rotating: stage.status === 'running' }">
              <component :is="getStepIcon(stage)" />
            </el-icon>
            <span v-else class="step-number">{{ index + 1 }}</span>
          </div>
        </template>
        
        <template #title>
          <div class="step-title">
            <span>{{ stage.name }}</span>
            <el-tag
              :type="getStatusTagType(stage.status)"
              size="small"
              class="status-tag"
            >
              {{ getStatusText(stage.status) }}
            </el-tag>
          </div>
        </template>
        
        <template #description>
          <div class="step-description">
            <div class="description-text">{{ stage.description }}</div>
            <div class="step-details">
              <div class="detail-item">
                <span class="detail-label">Processed:</span>
                <span class="detail-value">{{ stage.processedCount.toLocaleString() }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Duration:</span>
                <span class="detail-value">{{ formatDuration(stage.duration) }}</span>
              </div>
              <div class="detail-item" v-if="stage.error">
                <span class="detail-label error">Error:</span>
                <span class="detail-value error">{{ stage.error }}</span>
              </div>
              <div class="detail-item" v-if="stage.startTime">
                <span class="detail-label">Started:</span>
                <span class="detail-value">{{ formatTime(stage.startTime) }}</span>
              </div>
              <div class="detail-item" v-if="stage.endTime">
                <span class="detail-label">Ended:</span>
                <span class="detail-value">{{ formatTime(stage.endTime) }}</span>
              </div>
            </div>
            
            <!-- Stage Actions -->
            <div class="step-actions" v-if="showStageActions(stage)">
              <el-button
                v-if="stage.status === 'failed'"
                type="warning"
                size="small"
                @click="$emit('retry-stage', index)"
                :loading="stage.isRetrying"
              >
                <el-icon><RefreshRight /></el-icon>
                Retry from Here
              </el-button>
              
              <el-button
                v-if="stage.status === 'running' && canPause"
                type="info"
                size="small"
                @click="$emit('pause-stage', index)"
              >
                <el-icon><VideoPause /></el-icon>
                Pause
              </el-button>
              
              <el-button
                v-if="stage.status === 'paused'"
                type="success"
                size="small"
                @click="$emit('resume-stage', index)"
              >
                <el-icon><VideoPlay /></el-icon>
                Resume
              </el-button>
              
              <el-button
                text
                size="small"
                @click="$emit('view-logs', index)"
              >
                <el-icon><Document /></el-icon>
                View Logs
              </el-button>
            </div>
          </div>
        </template>
      </el-step>
    </el-steps>
    
    <!-- Overall Progress -->
    <div class="overall-progress" v-if="showOverallProgress">
      <div class="progress-header">
        <span class="progress-title">Overall Progress</span>
        <span class="progress-percentage">{{ overallPercentage }}%</span>
      </div>
      <el-progress
        :percentage="overallPercentage"
        :status="overallStatus"
        :stroke-width="8"
      />
      <div class="progress-stats">
        <div class="stat-item">
          <span class="stat-label">Total Processed:</span>
          <span class="stat-value">{{ totalProcessed.toLocaleString() }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Total Duration:</span>
          <span class="stat-value">{{ formatDuration(totalDuration) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Current Stage:</span>
          <span class="stat-value">{{ currentStage?.name || 'N/A' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  RefreshRight, VideoPause, VideoPlay, Document, Loading, CircleCheck,
  CircleClose, Warning, Clock
} from '@element-plus/icons-vue'

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

interface Props {
  stages: PipelineStage[]
  canPause?: boolean
  showOverallProgress?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  canPause: false,
  showOverallProgress: true
})

const emit = defineEmits<{
  'retry-stage': [stageIndex: number]
  'pause-stage': [stageIndex: number]
  'resume-stage': [stageIndex: number]
  'view-logs': [stageIndex: number]
}>()

// Computed properties
const activeStep = computed(() => {
  const index = props.stages.findIndex(stage => stage.status === 'running')
  return index >= 0 ? index : -1
})

const overallStatus = computed(() => {
  if (props.stages.some(stage => stage.status === 'failed')) return 'exception'
  if (props.stages.some(stage => stage.status === 'running')) return 'warning'
  if (props.stages.every(stage => stage.status === 'success')) return 'success'
  return 'wait'
})

const overallPercentage = computed(() => {
  const totalStages = props.stages.length
  const completedStages = props.stages.filter(stage => stage.status === 'success').length
  const runningStages = props.stages.filter(stage => stage.status === 'running').length
  
  if (runningStages > 0) {
    // If running, estimate progress based on current stage
    const runningIndex = props.stages.findIndex(stage => stage.status === 'running')
    return Math.round(((runningIndex + 0.5) / totalStages) * 100)
  }
  
  return Math.round((completedStages / totalStages) * 100)
})

const totalProcessed = computed(() => {
  return props.stages.reduce((sum, stage) => sum + stage.processedCount, 0)
})

const totalDuration = computed(() => {
  return props.stages.reduce((sum, stage) => sum + stage.duration, 0)
})

const currentStage = computed(() => {
  return props.stages.find(stage => stage.status === 'running')
})

// Methods
const getStepStatus = (stage: PipelineStage) => {
  const statusMap = {
    'waiting': 'wait',
    'running': 'process',
    'success': 'finish',
    'failed': 'error',
    'paused': 'warning'
  }
  return statusMap[stage.status] as any
}

const getStepIcon = (stage: PipelineStage) => {
  const iconMap = {
    'running': 'Loading',
    'success': 'CircleCheck',
    'failed': 'CircleClose',
    'paused': 'Warning',
    'waiting': null
  }
  return iconMap[stage.status]
}

const getStatusTagType = (status: string) => {
  const typeMap = {
    'waiting': 'info',
    'running': 'warning',
    'success': 'success',
    'failed': 'danger',
    'paused': 'warning'
  }
  return typeMap[status as keyof typeof typeMap] || 'info'
}

const getStatusText = (status: string) => {
  const textMap = {
    'waiting': 'Waiting',
    'running': 'Running',
    'success': 'Completed',
    'failed': 'Failed',
    'paused': 'Paused'
  }
  return textMap[status as keyof typeof textMap] || status
}

const showStageActions = (stage: PipelineStage) => {
  return stage.status === 'failed' || 
         stage.status === 'running' || 
         stage.status === 'paused' ||
         stage.status === 'success'
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

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.step-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.step-number {
  font-weight: var(--font-weight-bold);
  color: var(--color-text-secondary);
}

.rotating {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.step-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm);
}

.status-tag {
  font-size: var(--font-size-tiny);
}

.step-description {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.description-text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
  line-height: 1.4;
}

.step-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-tiny);
}

.detail-label {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.detail-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  font-family: 'Courier New', monospace;
}

.detail-value.error {
  color: var(--color-danger);
}

.step-actions {
  display: flex;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
  flex-wrap: wrap;
}

.overall-progress {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-border-light);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.progress-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.progress-percentage {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.progress-stats {
  display: flex;
  justify-content: space-around;
  margin-top: var(--spacing-md);
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  min-width: 100px;
}

.stat-label {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.stat-value {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* Custom step styles */
:deep(.el-step__title) {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-step__description) {
  font-size: var(--font-size-small);
  color: var(--color-text-regular);
}

:deep(.el-step__icon) {
  border: 2px solid var(--color-border-light);
}

:deep(.el-step__icon.is-process) {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

:deep(.el-step__icon.is-success) {
  border-color: var(--color-success);
  background: var(--color-success);
  color: white;
}

:deep(.el-step__icon.is-error) {
  border-color: var(--color-danger);
  background: var(--color-danger);
  color: white;
}

:deep(.el-step__icon.is-warning) {
  border-color: var(--color-warning);
  background: var(--color-warning);
  color: white;
}

/* Responsive */
@media (max-width: 768px) {
  .step-title {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }
  
  .step-actions {
    justify-content: center;
  }
  
  .progress-header {
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: stretch;
  }
  
  .progress-stats {
    flex-direction: column;
    align-items: stretch;
  }
  
  .stat-item {
    flex-direction: row;
    justify-content: space-between;
  }
}

/* Accessibility */
.step-actions:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
