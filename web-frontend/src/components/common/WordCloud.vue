<template>
  <div class="word-cloud-container">
    <div class="cloud-header">
      <h3 class="cloud-title">{{ title }}</h3>
      <div class="cloud-controls">
        <el-select
          v-model="selectedMetric"
          size="small"
          style="width: 120px"
          @change="updateMetric"
        >
          <el-option label="Frequency" value="frequency" />
          <el-option label="Weight" value="weight" />
          <el-option label="Score" value="score" />
        </el-select>
        <el-button
          text
          size="small"
          :loading="isLoading"
          :aria-label="'Refresh word cloud'"
          @click="refreshCloud"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="cloud-content">
      <div 
        ref="cloudContainer"
        class="word-cloud"
        :style="{ height: height + 'px' }"
        :aria-label="'Word cloud showing ' + words.length + ' words'"
      >
        <div
          v-for="(word, index) in displayWords"
          :key="word.text"
          class="word-item"
          :class="{ highlighted: word.highlighted }"
          :style="getWordStyle(word, index)"
          :aria-label="`Word: ${word.text}, frequency: ${word.frequency}`"
          @click="handleWordClick(word)"
          @mouseenter="handleWordHover(word)"
          @mouseleave="handleWordLeave(word)"
        >
          {{ word.text }}
        </div>
      </div>
    </div>
    
    <div class="cloud-footer">
      <div class="word-stats">
        <span class="stat-item">
          Total: <strong>{{ words.length }}</strong> words
        </span>
        <span class="stat-item">
          Top: <strong>{{ topCount }}</strong> displayed
        </span>
      </div>
      <div v-if="selectedWord" class="selected-word">
        <span class="selected-label">Selected:</span>
        <el-tag type="primary" size="small">
          {{ selectedWord.text }} ({{ selectedWord.frequency }})
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

interface WordData {
  text: string
  frequency: number
  weight?: number
  score?: number
  highlighted?: boolean
}

interface Props {
  words: WordData[]
  title?: string
  height?: number
  topCount?: number
  minFontSize?: number
  maxFontSize?: number
  colorScheme?: string[]
  isLoading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Word Cloud',
  height: 300,
  topCount: 20,
  minFontSize: 12,
  maxFontSize: 48,
  colorScheme: () => [
    '#165DFF', '#00B42A', '#FF7D00', '#F53F3F', '#86909C',
    '#722ED1', '#EB2F96', '#52C41A', '#1890FF', '#FA8C16'
  ],
  isLoading: false
})

const emit = defineEmits<{
  'word-click': [word: WordData]
  'word-hover': [word: WordData]
  'metric-change': [metric: string]
  'refresh': []
}>()

// Reactive data
const cloudContainer = ref<HTMLElement>()
const selectedMetric = ref('frequency')
const selectedWord = ref<WordData | null>(null)

// Computed properties
const displayWords = computed(() => {
  const sorted = [...props.words]
    .sort((a, b) => {
      const aValue = getMetricValue(a)
      const bValue = getMetricValue(b)
      return bValue - aValue
    })
    .slice(0, props.topCount)
  
  return sorted.map((word, index) => ({
    ...word,
    size: calculateFontSize(word, index),
    color: props.colorScheme[index % props.colorScheme.length],
    x: Math.random() * 80 + 10, // 10-90% position
    y: Math.random() * 80 + 10
  }))
})

// Methods
const getMetricValue = (word: WordData) => {
  switch (selectedMetric.value) {
    case 'frequency':
      return word.frequency
    case 'weight':
      return word.weight || word.frequency
    case 'score':
      return word.score || word.frequency
    default:
      return word.frequency
  }
}

const calculateFontSize = (word: WordData, index: number) => {
  const maxValue = getMetricValue(displayWords.value[0])
  const minValue = getMetricValue(displayWords.value[displayWords.value.length - 1])
  const currentValue = getMetricValue(word)
  
  if (maxValue === minValue) {
    return props.minFontSize
  }
  
  const ratio = (currentValue - minValue) / (maxValue - minValue)
  return props.minFontSize + (props.maxFontSize - props.minFontSize) * ratio
}

const getWordStyle = (word: WordData, index: number) => {
  return {
    fontSize: `${word.size}px`,
    color: word.color,
    left: `${word.x}%`,
    top: `${word.y}%`,
    transform: `translate(-50%, -50%)`,
    opacity: word.highlighted ? 1 : 0.8,
    fontWeight: word.size > 24 ? 'bold' : 'normal',
    cursor: 'pointer',
    transition: 'all 0.3s ease'
  }
}

const handleWordClick = (word: WordData) => {
  selectedWord.value = word
  
  // Toggle highlight
  word.highlighted = !word.highlighted
  
  emit('word-click', word)
}

const handleWordHover = (word: WordData) => {
  emit('word-hover', word)
}

const handleWordLeave = (word: WordData) => {
  // Handle leave if needed
}

const updateMetric = () => {
  emit('metric-change', selectedMetric.value)
}

const refreshCloud = () => {
  emit('refresh')
}

const highlightWord = (wordText: string) => {
  const word = props.words.find(w => w.text === wordText)
  if (word) {
    word.highlighted = true
    selectedWord.value = word
  }
}

const clearHighlights = () => {
  props.words.forEach(word => {
    word.highlighted = false
  })
  selectedWord.value = null
}

// Watch for words changes
watch(() => props.words, () => {
  clearHighlights()
}, { deep: true })

// Expose methods
defineExpose({
  highlightWord,
  clearHighlights
})
</script>

<style scoped>
.word-cloud-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
}

.cloud-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-base);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-hover);
}

.cloud-title {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.cloud-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.cloud-content {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.word-cloud {
  position: relative;
  width: 100%;
  height: 100%;
}

.word-item {
  position: absolute;
  white-space: nowrap;
  user-select: none;
  transition: all 0.3s ease;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
}

.word-item:hover {
  transform: translate(-50%, -50%) scale(1.1);
  opacity: 1;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
  z-index: 10;
}

.word-item.highlighted {
  transform: translate(-50%, -50%) scale(1.15);
  opacity: 1;
  text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.3);
  z-index: 20;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1.15);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.25);
  }
}

.cloud-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-base);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-hover);
}

.word-stats {
  display: flex;
  gap: var(--spacing-lg);
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.stat-item strong {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.selected-word {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.selected-label {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

/* Responsive */
@media (max-width: 768px) {
  .cloud-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .cloud-controls {
    justify-content: center;
  }
  
  .cloud-footer {
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: center;
  }
  
  .word-stats {
    justify-content: center;
  }
}

/* Accessibility */
.word-item:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: var(--border-radius-small);
}
</style>
