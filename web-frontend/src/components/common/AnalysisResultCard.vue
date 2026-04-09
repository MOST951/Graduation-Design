<template>
  <div class="analysis-result-card" :class="[`sentiment-${result.sentiment}`, { compact: compact }]">
    <div class="card-header">
      <div class="sentiment-label">
        <el-icon :class="getSentimentIcon()">
          <component :is="getSentimentIcon()" />
        </el-icon>
        <span class="sentiment-text">{{ getSentimentText() }}</span>
      </div>
      <div class="confidence-badge">
        <el-tag :type="getConfidenceType()" size="small">
          {{ Math.round(result.confidence * 100) }}% confidence
        </el-tag>
      </div>
    </div>
    
    <div class="card-content">
      <div class="score-display">
        <div class="score-value" :style="{ color: getScoreColor() }">
          {{ result.score.toFixed(3) }}
        </div>
        <div class="score-label">Score</div>
      </div>
      
      <div v-if="!compact" class="score-breakdown">
        <div class="score-item">
          <span class="score-label">Positive:</span>
          <span class="score-value positive">{{ (result.positive * 100).toFixed(1) }}%</span>
        </div>
        <div class="score-item">
          <span class="score-label">Negative:</span>
          <span class="score-value negative">{{ (result.negative * 100).toFixed(1) }}%</span>
        </div>
        <div class="score-item">
          <span class="score-label">Neutral:</span>
          <span class="score-value neutral">{{ (result.neutral * 100).toFixed(1) }}%</span>
        </div>
      </div>
      
      <div v-if="result.cascadeDecision" class="cascade-decision">
        <div class="decision-header">
          <el-icon><Operation /></el-icon>
          <span class="decision-title">Cascade Decision</span>
        </div>
        <div class="decision-content">
          <div class="decision-method">
            <span class="method-label">Method:</span>
            <el-tag :type="getMethodType()" size="small">
              {{ result.cascadeDecision.method }}
            </el-tag>
          </div>
          <div class="decision-reason">
            <span class="reason-label">Reason:</span>
            <span class="reason-text">{{ result.cascadeDecision.reason }}</span>
          </div>
          <div v-if="result.cascadeDecision.threshold" class="decision-threshold">
            <span class="threshold-label">Threshold:</span>
            <span class="threshold-value">{{ result.cascadeDecision.threshold }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="!compact" class="card-footer">
      <div class="timestamp">
        <el-icon><Clock /></el-icon>
        <span>{{ formatTime(result.timestamp) }}</span>
      </div>
      <div class="actions">
        <el-button text size="small" @click="$emit('details', result)">
          <el-icon><View /></el-icon>
          Details
        </el-button>
        <el-button text size="small" @click="$emit('export', result)">
          <el-icon><Download /></el-icon>
          Export
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Operation, Clock, View, Download, 
  Happy, Sad, Neutral, QuestionFilled
} from '@element-plus/icons-vue'

interface CascadeDecision {
  method: 'dictionary' | 'bert' | 'cascade'
  reason: string
  threshold?: number
  dictionaryScore?: number
  bertScore?: number
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
  cascadeDecision?: CascadeDecision
  timestamp: Date
  processingTime: number
}

interface Props {
  result: AnalysisResult
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false
})

const emit = defineEmits<{
  details: [result: AnalysisResult]
  export: [result: AnalysisResult]
}>()

// Computed properties
const getSentimentText = () => {
  const sentimentMap = {
    'positive': 'Positive',
    'negative': 'Negative', 
    'neutral': 'Neutral'
  }
  return sentimentMap[props.result.sentiment] || 'Unknown'
}

const getSentimentIcon = () => {
  const iconMap = {
    'positive': 'Happy',
    'negative': 'Sad',
    'neutral': 'Neutral'
  }
  return iconMap[props.result.sentiment] || 'QuestionFilled'
}

const getConfidenceType = () => {
  if (props.result.confidence >= 0.8) return 'success'
  if (props.result.confidence >= 0.6) return 'warning'
  return 'danger'
}

const getScoreColor = () => {
  if (props.result.sentiment === 'positive') return 'var(--color-success)'
  if (props.result.sentiment === 'negative') return 'var(--color-danger)'
  return 'var(--color-warning)'
}

const getMethodType = () => {
  const methodMap = {
    'dictionary': 'info',
    'bert': 'primary',
    'cascade': 'success'
  }
  return methodMap[props.result.cascadeDecision?.method] || 'info'
}

const formatTime = (timestamp: Date) => {
  return timestamp.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.analysis-result-card {
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
  transition: var(--transition-base);
  overflow: hidden;
}

.analysis-result-card:hover {
  box-shadow: var(--shadow-sm);
  transform: var(--hover-transform);
}

.analysis-result-card.sentiment-positive {
  border-left: 4px solid var(--color-success);
}

.analysis-result-card.sentiment-negative {
  border-left: 4px solid var(--color-danger);
}

.analysis-result-card.sentiment-neutral {
  border-left: 4px solid var(--color-warning);
}

.analysis-result-card.compact {
  padding: var(--spacing-sm);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-base);
  border-bottom: 1px solid var(--color-border-lighter);
}

.sentiment-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.sentiment-text {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-medium);
}

.confidence-badge {
  display: flex;
  align-items: center;
}

.card-content {
  padding: var(--spacing-base);
}

.score-display {
  text-align: center;
  margin-bottom: var(--spacing-md);
}

.score-value {
  font-size: var(--font-size-hero);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.score-label {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.score-breakdown {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
}

.score-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-small);
}

.score-label {
  color: var(--color-text-secondary);
}

.score-value.positive {
  color: var(--color-success);
}

.score-value.negative {
  color: var(--color-danger);
}

.score-value.neutral {
  color: var(--color-warning);
}

.cascade-decision {
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-small);
  padding: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.decision-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.decision-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.decision-method,
.decision-reason,
.decision-threshold {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.method-label,
.reason-label,
.threshold-label {
  color: var(--color-text-secondary);
}

.reason-text {
  color: var(--color-text-primary);
  text-align: right;
  max-width: 60%;
  word-break: break-all;
}

.threshold-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-base);
  border-top: 1px solid var(--color-border-lighter);
  background: var(--color-bg-hover);
}

.timestamp {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.actions {
  display: flex;
  gap: var(--spacing-xs);
}

/* Compact mode styles */
.analysis-result-card.compact .card-header {
  padding: var(--spacing-sm);
}

.analysis-result-card.compact .card-content {
  padding: var(--spacing-sm);
}

.analysis-result-card.compact .score-display {
  margin-bottom: var(--spacing-sm);
}

.analysis-result-card.compact .score-value {
  font-size: var(--font-size-large);
}

.analysis-result-card.compact .cascade-decision {
  margin-top: var(--spacing-xs);
}

.analysis-result-card.compact .card-footer {
  padding: var(--spacing-xs) var(--spacing-sm);
}

/* Responsive */
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .card-footer {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .actions {
    justify-content: center;
  }
  
  .score-breakdown {
    gap: var(--spacing-xxs);
  }
  
  .decision-content {
    gap: var(--spacing-xxs);
  }
  
  .decision-method,
  .decision-reason,
  .decision-threshold {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xxs);
  }
  
  .reason-text {
    max-width: 100%;
    text-align: left;
  }
}

/* Accessibility */
.analysis-result-card:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
