<template>
  <div class="time-range-filter">
    <div class="filter-header">
      <el-icon><Calendar /></el-icon>
      <span class="filter-title">Time Range</span>
    </div>
    
    <div class="filter-content">
      <el-radio-group v-model="selectedRange" class="range-options" @change="handleRangeChange">
        <el-radio-button label="7d">Last 7 Days</el-radio-button>
        <el-radio-button label="30d">Last 30 Days</el-radio-button>
        <el-radio-button label="custom">Custom</el-radio-button>
      </el-radio-group>
      
      <div v-if="selectedRange === 'custom'" class="custom-range">
        <el-date-picker
          v-model="customDateRange"
          type="daterange"
          range-separator="To"
          start-placeholder="Start date"
          end-placeholder="End date"
          :shortcuts="dateShortcuts"
          :aria-label="'Custom date range selector'"
          @change="handleCustomRangeChange"
        />
      </div>
      
      <div class="range-info">
        <span class="info-label">Selected:</span>
        <span class="info-value">{{ getDisplayRange() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Calendar } from '@element-plus/icons-vue'

interface Props {
  defaultRange?: string
}

const props = withDefaults(defineProps<Props>(), {
  defaultRange: '7d'
})

const emit = defineEmits<{
  'range-change': [startDate: Date, endDate: Date]
}>()

// Reactive data
const selectedRange = ref(props.defaultRange)
const customDateRange = ref<[Date, Date] | null>(null)

// Date shortcuts
const dateShortcuts = [
  {
    text: 'Last week',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    },
  },
  {
    text: 'Last month',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    },
  },
  {
    text: 'Last 3 months',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end]
    },
  },
]

// Computed properties
const getDisplayRange = () => {
  const now = new Date()
  let startDate: Date
  let endDate: Date = now

  switch (selectedRange.value) {
    case '7d':
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      break
    case '30d':
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      break
    case 'custom':
      if (customDateRange.value) {
        startDate = customDateRange.value[0]
        endDate = customDateRange.value[1]
      } else {
        return 'Please select dates'
      }
      break
    default:
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  }

  return `${formatDate(startDate)} - ${formatDate(endDate)}`
}

// Methods
const formatDate = (date: Date) => {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const handleRangeChange = (value: string) => {
  const now = new Date()
  let startDate: Date
  let endDate: Date = now

  switch (value) {
    case '7d':
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      break
    case '30d':
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      break
    case 'custom':
      // Don't emit until custom range is selected
      return
    default:
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  }

  emit('range-change', startDate, endDate)
}

const handleCustomRangeChange = (dates: [Date, Date] | null) => {
  if (dates) {
    emit('range-change', dates[0], dates[1])
  }
}
</script>

<style scoped>
.time-range-filter {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-white);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
}

.filter-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.filter-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.filter-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.range-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.custom-range {
  display: flex;
  justify-content: center;
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

.range-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  background: var(--color-info-bg);
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-info-light);
}

.info-label {
  font-size: var(--font-size-small);
  color: var(--color-info);
  font-weight: var(--font-weight-medium);
}

.info-value {
  font-size: var(--font-size-small);
  color: var(--color-info);
  font-weight: var(--font-weight-semibold);
}

/* Responsive */
@media (max-width: 768px) {
  .time-range-filter {
    padding: var(--spacing-sm);
  }
  
  .range-options {
    justify-content: center;
  }
  
  .range-info {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-xs);
  }
}
</style>
