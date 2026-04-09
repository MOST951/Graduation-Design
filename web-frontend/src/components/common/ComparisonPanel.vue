<template>
  <div class="comparison-panel">
    <div class="panel-header">
      <h3 class="panel-title">{{ title }}</h3>
      <div class="panel-controls">
        <el-button-group size="small">
          <el-button
            :type="viewMode === 'side-by-side' ? 'primary' : 'default'"
            @click="viewMode = 'side-by-side'"
            :aria-label="'Side by side view'"
          >
            <el-icon><Operation /></el-icon>
            Side by Side
          </el-button>
          <el-button
            :type="viewMode === 'overlay' ? 'primary' : 'default'"
            @click="viewMode = 'overlay'"
            :aria-label="'Overlay view'"
          >
            <el-icon><View /></el-icon>
            Overlay
          </el-button>
        </el-button-group>
        <el-switch
          v-model="showDifferences"
          active-text="Show differences"
          size="small"
          :aria-label="'Toggle difference highlighting'"
        />
      </div>
    </div>
    
    <div class="panel-content">
      <!-- Side by side view -->
      <div v-if="viewMode === 'side-by-side'" class="side-by-side-view">
        <div class="comparison-column">
          <div class="column-header">
            <span class="column-title">Original Text</span>
            <el-tag type="info" size="small">{{ currentIndex + 1 }} / {{ items.length }}</el-tag>
          </div>
          <div class="column-content">
            <div class="text-content" :class="{ highlighted: showDifferences }">
              <span
                v-for="(segment, index) in originalSegments"
                :key="index"
                :class="getSegmentClass(segment)"
                :style="getSegmentStyle(segment)"
              >
                {{ segment.text }}
              </span>
            </div>
          </div>
        </div>
        
        <div class="comparison-divider">
          <el-icon><ArrowRight /></el-icon>
        </div>
        
        <div class="comparison-column">
          <div class="column-header">
            <span class="column-title">Processed Text</span>
            <el-tag type="success" size="small">{{ currentIndex + 1 }} / {{ items.length }}</el-tag>
          </div>
          <div class="column-content">
            <div class="text-content" :class="{ highlighted: showDifferences }">
              <span
                v-for="(segment, index) in processedSegments"
                :key="index"
                :class="getSegmentClass(segment)"
                :style="getSegmentStyle(segment)"
              >
                {{ segment.text }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Overlay view -->
      <div v-else class="overlay-view">
        <div class="overlay-controls">
          <el-radio-group v-model="overlayMode" size="small">
            <el-radio-button label="original">Original</el-radio-button>
            <el-radio-button label="processed">Processed</el-radio-button>
            <el-radio-button label="diff">Differences</el-radio-button>
          </el-radio-group>
        </div>
        
        <div class="overlay-content">
          <div class="text-overlay">
            <div
              v-for="(segment, index) in overlaySegments"
              :key="index"
              class="overlay-segment"
              :class="getOverlaySegmentClass(segment)"
              :style="getOverlaySegmentStyle(segment)"
            >
              <span class="segment-text">{{ segment.text }}</span>
              <span v-if="segment.diff" class="diff-indicator">{{ segment.diff }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="panel-footer">
      <div class="pagination-controls">
        <el-button
          :disabled="currentIndex === 0"
          @click="previousItem"
          :aria-label="'Previous item'"
        >
          <el-icon><ArrowLeft /></el-icon>
          Previous
        </el-button>
        
        <div class="page-info">
          <el-input-number
            v-model="currentPage"
            :min="1"
            :max="totalPages"
            size="small"
            style="width: 80px"
            @change="goToPage"
            :aria-label="'Go to page'"
          />
          <span class="page-text">/ {{ totalPages }}</span>
        </div>
        
        <el-button
          :disabled="currentIndex === items.length - 1"
          @click="nextItem"
          :aria-label="'Next item'"
        >
          Next
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      
      <div class="statistics">
        <span class="stat-item">
          Changes: <strong>{{ totalChanges }}</strong>
        </span>
        <span class="stat-item">
          Similarity: <strong>{{ similarityScore }}%</strong>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  Operation, View, ArrowRight, ArrowLeft, ArrowDown
} from '@element-plus/icons-vue'

interface TextSegment {
  text: string
  type: 'unchanged' | 'added' | 'removed' | 'modified'
  originalIndex?: number
  processedIndex?: number
}

interface ComparisonItem {
  id: string
  original: string
  processed: string
  metadata?: Record<string, any>
}

interface Props {
  items: ComparisonItem[]
  title?: string
  showDifferences?: boolean
  autoDiff?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Text Comparison',
  showDifferences: true,
  autoDiff: true
})

const emit = defineEmits<{
  'item-change': [item: ComparisonItem, index: number]
  'page-change': [page: number]
}>()

// Reactive data
const viewMode = ref<'side-by-side' | 'overlay'>('side-by-side')
const overlayMode = ref<'original' | 'processed' | 'diff'>('original')
const currentIndex = ref(0)
const showDifferences = ref(props.showDifferences)

// Computed properties
const currentItem = computed(() => props.items[currentIndex.value] || null)

const totalPages = computed(() => Math.ceil(props.items.length / 1))
const currentPage = computed({
  get: () => currentIndex.value + 1,
  set: (value) => goToPage(value)
})

const originalSegments = computed(() => {
  if (!currentItem.value) return []
  return segmentText(currentItem.value.original, 'original')
})

const processedSegments = computed(() => {
  if (!currentItem.value) return []
  return segmentText(currentItem.value.processed, 'processed')
})

const overlaySegments = computed(() => {
  if (!currentItem.value) return []
  return createOverlaySegments(currentItem.value.original, currentItem.value.processed)
})

const totalChanges = computed(() => {
  return overlaySegments.value.filter(segment => segment.type !== 'unchanged').length
})

const similarityScore = computed(() => {
  if (!currentItem.value) return 0
  
  const original = currentItem.value.original
  const processed = currentItem.value.processed
  
  // Simple similarity calculation (can be enhanced with more sophisticated algorithms)
  const originalWords = original.split(/\s+/).filter(word => word.length > 0)
  const processedWords = processed.split(/\s+/).filter(word => word.length > 0)
  
  const commonWords = originalWords.filter(word => processedWords.includes(word))
  const totalWords = new Set([...originalWords, ...processedWords]).size
  
  return totalWords > 0 ? Math.round((commonWords.length / totalWords) * 100) : 0
})

// Methods
const segmentText = (text: string, type: 'original' | 'processed'): TextSegment[] => {
  if (!showDifferences.value) {
    return [{ text, type: 'unchanged' }]
  }
  
  // Simple diff implementation (can be enhanced with proper diff algorithm)
  const original = type === 'original' ? text : ''
  const processed = type === 'processed' ? text : ''
  
  // For now, return as unchanged segments
  // In a real implementation, you'd use a proper diff algorithm
  return [{ text, type: 'unchanged' }]
}

const createOverlaySegments = (original: string, processed: string): TextSegment[] => {
  if (overlayMode.value === 'original') {
    return [{ text: original, type: 'unchanged' }]
  }
  
  if (overlayMode.value === 'processed') {
    return [{ text: processed, type: 'unchanged' }]
  }
  
  // Diff mode - simple implementation
  const segments: TextSegment[] = []
  
  // This is a simplified diff - in production, use a proper diff library
  const originalWords = original.split(/\s+/)
  const processedWords = processed.split(/\s+/)
  
  let originalIndex = 0
  let processedIndex = 0
  
  while (originalIndex < originalWords.length || processedIndex < processedWords.length) {
    const originalWord = originalWords[originalIndex]
    const processedWord = processedWords[processedIndex]
    
    if (originalIndex < originalWords.length && processedIndex < processedWords.length) {
      if (originalWord === processedWord) {
        segments.push({ text: originalWord + ' ', type: 'unchanged' })
        originalIndex++
        processedIndex++
      } else {
        // Word changed
        segments.push({ text: originalWord + ' ', type: 'removed' })
        segments.push({ text: processedWord + ' ', type: 'added' })
        originalIndex++
        processedIndex++
      }
    } else if (originalIndex < originalWords.length) {
      segments.push({ text: originalWord + ' ', type: 'removed' })
      originalIndex++
    } else {
      segments.push({ text: processedWord + ' ', type: 'added' })
      processedIndex++
    }
  }
  
  return segments
}

const getSegmentClass = (segment: TextSegment) => {
  return `segment-${segment.type}`
}

const getSegmentStyle = (segment: TextSegment) => {
  const styles: Record<string, string> = {}
  
  switch (segment.type) {
    case 'added':
      styles.backgroundColor = 'rgba(0, 180, 42, 0.2)'
      styles.color = 'var(--color-success)'
      break
    case 'removed':
      styles.backgroundColor = 'rgba(245, 63, 63, 0.2)'
      styles.color = 'var(--color-danger)'
      styles.textDecoration = 'line-through'
      break
    case 'modified':
      styles.backgroundColor = 'rgba(255, 125, 0, 0.2)'
      styles.color = 'var(--color-warning)'
      break
  }
  
  return styles
}

const getOverlaySegmentClass = (segment: TextSegment) => {
  return `overlay-segment-${segment.type}`
}

const getOverlaySegmentStyle = (segment: TextSegment) => {
  const styles: Record<string, string> = {}
  
  switch (segment.type) {
    case 'added':
      styles.backgroundColor = 'rgba(0, 180, 42, 0.3)'
      styles.color = 'var(--color-success)'
      break
    case 'removed':
      styles.backgroundColor = 'rgba(245, 63, 63, 0.3)'
      styles.color = 'var(--color-danger)'
      styles.textDecoration = 'line-through'
      break
    case 'modified':
      styles.backgroundColor = 'rgba(255, 125, 0, 0.3)'
      styles.color = 'var(--color-warning)'
      break
  }
  
  return styles
}

const previousItem = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    emit('item-change', currentItem.value!, currentIndex.value)
  }
}

const nextItem = () => {
  if (currentIndex.value < props.items.length - 1) {
    currentIndex.value++
    emit('item-change', currentItem.value!, currentIndex.value)
  }
}

const goToPage = (page: number) => {
  const index = page - 1
  if (index >= 0 && index < props.items.length) {
    currentIndex.value = index
    emit('item-change', currentItem.value!, currentIndex.value)
  }
}

// Watch for items changes
watch(() => props.items, () => {
  if (currentIndex.value >= props.items.length) {
    currentIndex.value = Math.max(0, props.items.length - 1)
  }
})

// Expose methods
defineExpose({
  previousItem,
  nextItem,
  goToPage,
  currentIndex: computed(() => currentIndex.value)
})
</script>

<style scoped>
.comparison-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-base);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-hover);
}

.panel-title {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.panel-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.panel-content {
  flex: 1;
  overflow: hidden;
}

.side-by-side-view {
  display: flex;
  height: 100%;
  gap: var(--spacing-sm);
}

.comparison-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--border-radius-base);
  overflow: hidden;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-base);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-border-lighter);
}

.column-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.column-content {
  flex: 1;
  padding: var(--spacing-base);
  overflow-y: auto;
}

.text-content {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-small);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.text-content.highlighted .segment-unchanged {
  opacity: 0.6;
}

.segment-added {
  background-color: rgba(0, 180, 42, 0.2);
  color: var(--color-success);
  border-radius: var(--border-radius-xs);
  padding: 0 2px;
}

.segment-removed {
  background-color: rgba(245, 63, 63, 0.2);
  color: var(--color-danger);
  text-decoration: line-through;
  border-radius: var(--border-radius-xs);
  padding: 0 2px;
}

.segment-modified {
  background-color: rgba(255, 125, 0, 0.2);
  color: var(--color-warning);
  border-radius: var(--border-radius-xs);
  padding: 0 2px;
}

.comparison-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-large);
}

.overlay-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.overlay-controls {
  padding: var(--spacing-sm) var(--spacing-base);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-hover);
}

.overlay-content {
  flex: 1;
  padding: var(--spacing-base);
  overflow-y: auto;
}

.text-overlay {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-small);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.overlay-segment {
  display: inline-block;
  margin: 0 2px;
  padding: 2px 4px;
  border-radius: var(--border-radius-xs);
  transition: var(--transition-fast);
}

.overlay-segment-unchanged {
  background-color: transparent;
}

.overlay-segment-added {
  background-color: rgba(0, 180, 42, 0.3);
  color: var(--color-success);
}

.overlay-segment-removed {
  background-color: rgba(245, 63, 63, 0.3);
  color: var(--color-danger);
  text-decoration: line-through;
}

.overlay-segment-modified {
  background-color: rgba(255, 125, 0, 0.3);
  color: var(--color-warning);
}

.diff-indicator {
  font-size: var(--font-size-tiny);
  margin-left: var(--spacing-xxs);
  opacity: 0.7;
}

.panel-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-base);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-hover);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.page-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.page-text {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.statistics {
  display: flex;
  gap: var(--spacing-lg);
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.stat-item strong {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

/* Responsive */
@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .panel-controls {
    justify-content: center;
  }
  
  .side-by-side-view {
    flex-direction: column;
  }
  
  .comparison-divider {
    transform: rotate(90deg);
    margin: var(--spacing-sm) 0;
  }
  
  .panel-footer {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: center;
  }
  
  .pagination-controls {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .statistics {
    justify-content: center;
  }
}

/* Accessibility */
.segment-added:focus,
.segment-removed:focus,
.segment-modified:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
