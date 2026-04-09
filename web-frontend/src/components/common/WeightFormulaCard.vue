<template>
  <div class="weight-formula-card">
    <div class="formula-header">
      <el-icon><Operation /></el-icon>
      <span class="formula-title">Weight Formula</span>
    </div>
    
    <div class="formula-display">
      <div class="formula-main">
        <span class="formula-label">Composite Score =</span>
        <div class="formula-terms">
          <div class="term" :class="{ active: weights.sentiment > 0 }">
            <span class="weight">w<sub>1</sub></span>
            <span class="operator">×</span>
            <span class="component">Sentiment</span>
            <span class="value">({{ weights.sentiment.toFixed(2) }})</span>
          </div>
          
          <div class="term" :class="{ active: weights.popularity > 0 }">
            <span class="operator">+</span>
            <span class="weight">w<sub>2</sub></span>
            <span class="operator">×</span>
            <span class="component">Popularity</span>
            <span class="value">({{ weights.popularity.toFixed(2) }})</span>
          </div>
          
          <div class="term" :class="{ active: weights.timeliness > 0 }">
            <span class="operator">+</span>
            <span class="weight">w<sub>3</sub></span>
            <span class="operator">×</span>
            <span class="component">Timeliness</span>
            <span class="value">({{ weights.timeliness.toFixed(2) }})</span>
          </div>
        </div>
      </div>
      
      <div class="formula-constraints">
        <div class="constraint-item">
          <span class="constraint-label">Sum of weights:</span>
          <span class="constraint-value" :class="{ valid: isValidSum }">
            {{ totalSum.toFixed(2) }}
          </span>
          <span class="constraint-target">= 1.0</span>
        </div>
        
        <div class="constraint-item">
          <span class="constraint-label">Valid range:</span>
          <span class="constraint-value">0.0 - 1.0</span>
        </div>
      </div>
    </div>
    
    <div class="formula-description">
      <div class="description-title">Component Descriptions:</div>
      <div class="description-list">
        <div class="description-item">
          <span class="component-label">w<sub>1</sub> (Sentiment):</span>
          <span class="component-desc">Normalized sentiment intensity score</span>
        </div>
        <div class="description-item">
          <span class="component-label">w<sub>2</sub> (Popularity):</span>
          <span class="component-desc">Interaction popularity score (reposts, comments, likes)</span>
        </div>
        <div class="description-item">
          <span class="component-label">w<sub>3</sub> (Timeliness):</span>
          <span class="component-desc">Time decay factor based on publish time</span>
        </div>
      </div>
    </div>
    
    <div class="formula-actions">
      <el-button-group size="small">
        <el-button :aria-label="'Reset weights to default'" @click="resetWeights">
          <el-icon><RefreshRight /></el-icon>
          Reset
        </el-button>
        <el-button :aria-label="'Equalize all weights'" @click="equalizeWeights">
          <el-icon><Balance /></el-icon>
          Equalize
        </el-button>
        <el-button :aria-label="'Optimize weights for best results'" @click="optimizeWeights">
          <el-icon><MagicStick /></el-icon>
          Optimize
        </el-button>
      </el-button-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Operation, RefreshRight, Balance, MagicStick
} from '@element-plus/icons-vue'

interface Weights {
  sentiment: number
  popularity: number
  timeliness: number
}

interface Props {
  weights: Weights
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:weights': [weights: Weights]
  'reset': []
  'equalize': []
  'optimize': []
}>()

// Computed properties
const totalSum = computed(() => {
  return props.weights.sentiment + props.weights.popularity + props.weights.timeliness
})

const isValidSum = computed(() => {
  return Math.abs(totalSum.value - 1.0) < 0.01
})

// Methods
const resetWeights = () => {
  const defaultWeights: Weights = {
    sentiment: 0.4,
    popularity: 0.4,
    timeliness: 0.2
  }
  emit('update:weights', defaultWeights)
  emit('reset')
  ElMessage.success('Weights reset to default values')
}

const equalizeWeights = () => {
  const equalWeights: Weights = {
    sentiment: 0.33,
    popularity: 0.33,
    timeliness: 0.34
  }
  emit('update:weights', equalWeights)
  emit('equalize')
  ElMessage.success('Weights equalized')
}

const optimizeWeights = () => {
  // Simulate optimization based on historical data
  const optimizedWeights: Weights = {
    sentiment: 0.45,
    popularity: 0.35,
    timeliness: 0.20
  }
  emit('update:weights', optimizedWeights)
  emit('optimize')
  ElMessage.success('Weights optimized based on historical performance')
}
</script>

<style scoped>
.weight-formula-card {
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
  padding: var(--spacing-lg);
  transition: var(--transition-base);
}

.weight-formula-card:hover {
  box-shadow: var(--shadow-sm);
}

.formula-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.formula-title {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.formula-display {
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.formula-main {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.formula-label {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.formula-terms {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-sm);
}

.term {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius-small);
  background: var(--color-bg-white);
  border: 1px solid var(--color-border-light);
  transition: var(--transition-fast);
}

.term.active {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
}

.weight {
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
  font-family: 'Times New Roman', serif;
}

.weight sub {
  font-size: 0.7em;
  vertical-align: sub;
}

.operator {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.component {
  color: var(--color-text-regular);
  font-weight: var(--font-weight-medium);
}

.value {
  color: var(--color-success);
  font-weight: var(--font-weight-semibold);
  font-family: 'Courier New', monospace;
}

.formula-constraints {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  background: var(--color-bg-white);
  border-radius: var(--border-radius-small);
  border: 1px solid var(--color-border-light);
}

.constraint-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.constraint-label {
  color: var(--color-text-secondary);
}

.constraint-value {
  font-weight: var(--font-weight-semibold);
  font-family: 'Courier New', monospace;
}

.constraint-value.valid {
  color: var(--color-success);
}

.constraint-value:not(.valid) {
  color: var(--color-danger);
}

.constraint-target {
  color: var(--color-text-secondary);
}

.formula-description {
  margin-bottom: var(--spacing-md);
}

.description-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.description-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.description-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  font-size: var(--font-size-small);
  line-height: 1.4;
}

.component-label {
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary);
  font-family: 'Times New Roman', serif;
  white-space: nowrap;
}

.component-label sub {
  font-size: 0.7em;
  vertical-align: sub;
}

.component-desc {
  color: var(--color-text-secondary);
  flex: 1;
}

.formula-actions {
  display: flex;
  justify-content: center;
}

/* Responsive */
@media (max-width: 768px) {
  .formula-terms {
    flex-direction: column;
    align-items: stretch;
  }
  
  .term {
    justify-content: center;
  }
  
  .formula-constraints {
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: stretch;
  }
  
  .constraint-item {
    justify-content: space-between;
  }
  
  .description-item {
    flex-direction: column;
    gap: var(--spacing-xxs);
  }
  
  .formula-actions .el-button-group {
    display: flex;
    flex-direction: column;
    width: 100%;
  }
  
  .formula-actions .el-button {
    width: 100%;
  }
}

/* Accessibility */
.weight-formula-card:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
