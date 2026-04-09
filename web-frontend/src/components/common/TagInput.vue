<template>
  <div class="tag-input-container">
    <div class="tag-list">
      <el-tag
        v-for="(tag, index) in tags"
        :key="tag"
        closable
        class="tag-item"
        :type="getTagType(tag)"
        size="default"
        @close="removeTag(index)"
      >
        {{ tag }}
      </el-tag>
    </div>
    
    <div class="input-wrapper">
      <el-input
        v-model="inputValue"
        :placeholder="placeholder"
        :disabled="disabled"
        clearable
        class="tag-input"
        :aria-label="placeholder"
        @keyup.enter="addTag"
        @blur="addTag"
      >
        <template #prefix>
          <el-icon><Plus /></el-icon>
        </template>
      </el-input>
    </div>
    
    <div v-if="showSuggestions && suggestions.length > 0" class="suggestions">
      <div
        v-for="suggestion in suggestions"
        :key="suggestion"
        class="suggestion-item"
        @click="addSuggestion(suggestion)"
      >
        {{ suggestion }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

interface Props {
  modelValue: string[]
  placeholder?: string
  disabled?: boolean
  maxTags?: number
  suggestions?: string[]
  showSuggestions?: boolean
  validateTag?: (tag: string) => boolean
  duplicateMessage?: string
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Enter keywords, press Enter to add',
  disabled: false,
  maxTags: 20,
  suggestions: () => [],
  showSuggestions: false,
  validateTag: () => true,
  duplicateMessage: 'Tag already exists'
})

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
  'tag-add': [tag: string]
  'tag-remove': [tag: string, index: number]
}>()

const inputValue = ref('')
const tags = ref<string[]>([...props.modelValue])

// Watch for external changes
watch(() => props.modelValue, (newValue) => {
  tags.value = [...newValue]
})

watch(tags, (newValue) => {
  emit('update:modelValue', newValue)
})

const addTag = () => {
  const value = inputValue.value.trim()
  
  if (!value) return
  
  if (tags.value.length >= props.maxTags) {
    ElMessage.warning(`Maximum ${props.maxTags} tags allowed`)
    return
  }
  
  if (tags.value.includes(value)) {
    ElMessage.warning(props.duplicateMessage)
    return
  }
  
  if (!props.validateTag(value)) {
    ElMessage.error('Invalid tag format')
    return
  }
  
  tags.value.push(value)
  inputValue.value = ''
  emit('tag-add', value)
}

const removeTag = (index: number) => {
  const removedTag = tags.value[index]
  tags.value.splice(index, 1)
  emit('tag-remove', removedTag, index)
}

const addSuggestion = (suggestion: string) => {
  if (!tags.value.includes(suggestion)) {
    tags.value.push(suggestion)
    emit('tag-add', suggestion)
  }
  inputValue.value = ''
}

const getTagType = (tag: string) => {
  // Different types based on tag content or length
  if (tag.length > 10) return 'warning'
  if (tag.includes('#')) return 'success'
  return 'primary'
}
</script>

<style scoped>
.tag-input-container {
  width: 100%;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.tag-item {
  transition: var(--transition-fast);
}

.tag-item:hover {
  transform: var(--hover-transform);
}

.input-wrapper {
  width: 100%;
}

.tag-input {
  width: 100%;
}

.suggestions {
  margin-top: var(--spacing-xs);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  max-height: 120px;
  overflow-y: auto;
  background: var(--color-bg-white);
}

.suggestion-item {
  padding: var(--spacing-sm) var(--spacing-base);
  cursor: pointer;
  transition: var(--transition-fast);
  border-bottom: 1px solid var(--color-border-lighter);
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-primary);
}

.suggestion-item:first-child:hover {
  border-radius: var(--border-radius-base) var(--border-radius-base) 0 0;
}

.suggestion-item:last-child:hover {
  border-radius: 0 0 var(--border-radius-base) var(--border-radius-base);
}

/* Responsive */
@media (max-width: 768px) {
  .tag-list {
    gap: var(--spacing-xxs);
  }
  
  .tag-item {
    font-size: var(--font-size-small);
  }
}
</style>
