<template>
  <div class="keyword-subscription">
    <div class="subscription-header">
      <div class="header-left">
        <el-icon><Collection /></el-icon>
        <span class="header-title">Keyword Subscription</span>
        <el-tag type="info" size="small">{{ keywords.length }} active</el-tag>
      </div>
      <div class="header-right">
        <el-button
          text
          size="small"
          :disabled="keywords.length === 0"
          :aria-label="'Clear all keywords'"
          @click="clearAll"
        >
          <el-icon><Delete /></el-icon>
          Clear All
        </el-button>
      </div>
    </div>
    
    <div class="subscription-content">
      <!-- Quick Add Input -->
      <div class="quick-add">
        <el-input
          v-model="inputValue"
          placeholder="Enter keyword to subscribe..."
          clearable
          class="keyword-input"
          :aria-label="'Keyword input for subscription'"
          @keyup.enter="addKeyword"
        >
          <template #append>
            <el-button
              type="primary"
              :disabled="!inputValue.trim()"
              :aria-label="'Add keyword'"
              @click="addKeyword"
            >
              <el-icon><Plus /></el-icon>
              Add
            </el-button>
          </template>
        </el-input>
      </div>
      
      <!-- Keywords List -->
      <div class="keywords-list">
        <div
          v-for="(keyword, index) in keywords"
          :key="keyword.id"
          class="keyword-item"
          :class="{ active: keyword.active }"
        >
          <div class="keyword-content">
            <el-icon class="keyword-icon"><Search /></el-icon>
            <span class="keyword-text">{{ keyword.text }}</span>
            <div class="keyword-stats">
              <span class="stat-item">
                <el-icon><ChatDotRound /></el-icon>
                {{ keyword.matchCount }}
              </span>
              <span class="stat-item">
                <el-icon><Clock /></el-icon>
                {{ formatTime(keyword.lastMatch) }}
              </span>
            </div>
          </div>
          
          <div class="keyword-actions">
            <el-switch
              v-model="keyword.active"
              size="small"
              :aria-label="`Toggle keyword ${keyword.text}`"
              @change="toggleKeyword(keyword)"
            />
            <el-button
              text
              size="small"
              type="danger"
              :aria-label="`Remove keyword ${keyword.text}`"
              @click="removeKeyword(index)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-if="keywords.length === 0" class="empty-state">
        <el-icon class="empty-icon"><Document /></el-icon>
        <p class="empty-text">No keywords subscribed</p>
        <p class="empty-description">Add keywords to start monitoring</p>
      </div>
    </div>
    
    <!-- Preset Keywords -->
    <div class="preset-keywords">
      <div class="preset-header">
        <span class="preset-title">Popular Keywords:</span>
      </div>
      <div class="preset-list">
        <el-tag
          v-for="preset in presetKeywords"
          :key="preset"
          class="preset-tag"
          :aria-label="`Add preset keyword ${preset}`"
          @click="addPresetKeyword(preset)"
        >
          {{ preset }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Collection, Delete, Plus, Search, ChatDotRound, Clock, Close, Document
} from '@element-plus/icons-vue'

interface Keyword {
  id: string
  text: string
  active: boolean
  matchCount: number
  lastMatch: Date
}

interface Props {
  keywords: Keyword[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:keywords': [keywords: Keyword[]]
  'add': [keyword: Keyword]
  'remove': [index: number]
  'toggle': [keyword: Keyword]
  'clear': []
}>()

// Reactive data
const inputValue = ref('')

// Constants
const presetKeywords = ref([
  'AI', 'Machine Learning', 'Vue.js', 'React', 'TypeScript',
  'Python', 'JavaScript', 'Frontend', 'Backend', 'DevOps',
  'Cloud Computing', 'Big Data', 'Blockchain', 'IoT', '5G'
])

// Methods
const addKeyword = () => {
  const text = inputValue.value.trim()
  
  if (!text) {
    ElMessage.warning('Please enter a keyword')
    return
  }
  
  if (props.keywords.some(kw => kw.text.toLowerCase() === text.toLowerCase())) {
    ElMessage.warning('Keyword already exists')
    return
  }
  
  const newKeyword: Keyword = {
    id: `kw_${Date.now()}`,
    text,
    active: true,
    matchCount: 0,
    lastMatch: new Date()
  }
  
  emit('add', newKeyword)
  inputValue.value = ''
  ElMessage.success(`Added keyword: ${text}`)
}

const addPresetKeyword = (preset: string) => {
  inputValue.value = preset
  addKeyword()
}

const removeKeyword = (index: number) => {
  const keyword = props.keywords[index]
  emit('remove', index)
  ElMessage.info(`Removed keyword: ${keyword.text}`)
}

const toggleKeyword = (keyword: Keyword) => {
  emit('toggle', keyword)
  ElMessage.info(`${keyword.active ? 'Enabled' : 'Disabled'} keyword: ${keyword.text}`)
}

const clearAll = () => {
  emit('clear')
  ElMessage.success('Cleared all keywords')
}

const formatTime = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / (1000 * 60))
  
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)}h ago`
  return `${Math.floor(minutes / (24 * 60))}d ago`
}
</script>

<style scoped>
.keyword-subscription {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
  padding: var(--spacing-lg);
}

.subscription-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.subscription-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.quick-add {
  display: flex;
  gap: var(--spacing-sm);
}

.keyword-input {
  flex: 1;
}

.keywords-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  max-height: 300px;
  overflow-y: auto;
}

.keyword-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  background: var(--color-bg-white);
  transition: var(--transition-fast);
}

.keyword-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.keyword-item.active {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.keyword-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
}

.keyword-icon {
  color: var(--color-info);
}

.keyword-text {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.keyword-stats {
  display: flex;
  gap: var(--spacing-sm);
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xxs);
}

.keyword-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  color: var(--color-text-placeholder);
  margin-bottom: var(--spacing-md);
}

.empty-text {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.empty-description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.preset-keywords {
  border-top: 1px solid var(--color-border-light);
  padding-top: var(--spacing-md);
}

.preset-header {
  margin-bottom: var(--spacing-sm);
}

.preset-title {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.preset-tag {
  cursor: pointer;
  transition: var(--transition-fast);
}

.preset-tag:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Scrollbar styling */
.keywords-list::-webkit-scrollbar {
  width: 6px;
}

.keywords-list::-webkit-scrollbar-track {
  background: transparent;
}

.keywords-list::-webkit-scrollbar-thumb {
  background: var(--color-border-base);
  border-radius: var(--border-radius-round);
}

.keywords-list::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-placeholder);
}

/* Responsive */
@media (max-width: 768px) {
  .keyword-subscription {
    padding: var(--spacing-md);
  }
  
  .subscription-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .keyword-item {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .keyword-content {
    justify-content: center;
  }
  
  .keyword-actions {
    justify-content: space-between;
  }
  
  .preset-list {
    justify-content: center;
  }
}

/* Accessibility */
.keyword-item:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
