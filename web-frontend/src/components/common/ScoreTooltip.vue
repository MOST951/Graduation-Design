<template>
  <el-tooltip
    :content="tooltipContent"
    placement="top"
    :show-after="500"
    :hide-after="0"
    trigger="hover"
    :aria-label="`${title} calculation formula`"
  >
    <template #content>
      <div class="score-tooltip">
        <div class="tooltip-header">
          <span class="tooltip-title">{{ title }}</span>
        </div>
        <div class="tooltip-formula">
          <div class="formula-display">{{ formula }}</div>
        </div>
        <div class="tooltip-description">
          <div class="description-title">Calculation Steps:</div>
          <div class="steps-list">
            <div
              v-for="(step, index) in steps"
              :key="index"
              class="step-item"
            >
              <span class="step-number">{{ index + 1 }}.</span>
              <span class="step-text">{{ step }}</span>
            </div>
          </div>
        </div>
        <div v-if="range" class="tooltip-range">
          <div class="range-title">Score Range:</div>
          <div class="range-value">{{ range.min }} - {{ range.max }}</div>
        </div>
        <div v-if="example" class="tooltip-example">
          <div class="example-title">Example:</div>
          <div class="example-content">{{ example }}</div>
        </div>
      </div>
    </template>
    <slot />
  </el-tooltip>
</template>

<script setup lang="ts">
interface TooltipStep {
  text: string
}

interface TooltipRange {
  min: number
  max: number
}

interface Props {
  title: string
  formula: string
  steps: TooltipStep[]
  range?: TooltipRange
  example?: string
}

defineProps<Props>()
</script>

<style scoped>
.score-tooltip {
  max-width: 400px;
  padding: var(--spacing-sm);
}

.tooltip-header {
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--color-border-light);
}

.tooltip-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-medium);
}

.tooltip-formula {
  margin-bottom: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-small);
  border: 1px solid var(--color-border-light);
}

.formula-display {
  font-family: 'Courier New', monospace;
  font-size: var(--font-size-small);
  color: var(--color-text-primary);
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-all;
}

.tooltip-description {
  margin-bottom: var(--spacing-sm);
}

.description-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-xs);
  font-size: var(--font-size-small);
  line-height: 1.4;
}

.step-number {
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary);
  min-width: 16px;
}

.step-text {
  color: var(--color-text-regular);
  flex: 1;
}

.tooltip-range {
  margin-bottom: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-info-bg);
  border-radius: var(--border-radius-small);
  border: 1px solid var(--color-info-light);
}

.range-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-info);
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.range-value {
  font-family: 'Courier New', monospace;
  font-weight: var(--font-weight-semibold);
  color: var(--color-info);
  font-size: var(--font-size-small);
}

.tooltip-example {
  padding: var(--spacing-sm);
  background: var(--color-success-bg);
  border-radius: var(--border-radius-small);
  border: 1px solid var(--color-success-light);
}

.example-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-success);
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.example-content {
  font-family: 'Courier New', monospace;
  font-size: var(--font-size-small);
  color: var(--color-success);
  line-height: 1.4;
}
</style>
