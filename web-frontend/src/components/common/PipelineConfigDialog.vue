<template>
  <el-dialog
    v-model="visible"
    title="Pipeline Configuration"
    width="600px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    :aria-label="'Pipeline configuration dialog'"
  >
    <el-form :model="config" :rules="rules" ref="formRef" label-position="top">
      <!-- Keywords Preset -->
      <el-form-item label="Keywords Preset" prop="keywords">
        <div class="keywords-config">
          <div class="preset-selector">
            <el-select
              v-model="config.presetType"
              placeholder="Select preset"
              style="width: 100%"
              @change="handlePresetChange"
            >
              <el-option label="Custom" value="custom" />
              <el-option label="AI & Technology" value="tech" />
              <el-option label="Business & Finance" value="business" />
              <el-option label="Entertainment" value="entertainment" />
              <el-option label="News & Politics" value="news" />
            </el-select>
          </div>
          
          <div class="keywords-input">
            <el-input
              v-model="config.keywordsText"
              type="textarea"
              :rows="4"
              placeholder="Enter keywords, one per line"
              :disabled="config.presetType !== 'custom'"
            />
            <div class="keywords-count">
              {{ keywordCount }} keywords
            </div>
          </div>
        </div>
      </el-form-item>
      
      <!-- Max Processing Count -->
      <el-form-item label="Max Processing Count" prop="maxCount">
        <el-input-number
          v-model="config.maxCount"
          :min="100"
          :max="100000"
          :step="1000"
          style="width: 100%"
        />
        <div class="form-help">
          Maximum number of items to process in this pipeline run
        </div>
      </el-form-item>
      
      <!-- Execution Mode -->
      <el-form-item label="Execution Mode" prop="executionMode">
        <el-radio-group v-model="config.executionMode">
          <el-radio label="sync" class="mode-option">
            <div class="mode-content">
              <div class="mode-title">Synchronous Mode</div>
              <div class="mode-desc">Process all stages sequentially, wait for completion</div>
            </div>
          </el-radio>
          <el-radio label="async" class="mode-option">
            <div class="mode-content">
              <div class="mode-title">Asynchronous Mode</div>
              <div class="mode-desc">Process stages in parallel, track progress via task ID</div>
            </div>
          </el-radio>
        </el-radio-group>
      </el-form-item>
      
      <!-- Advanced Options -->
      <el-form-item>
        <el-collapse v-model="advancedExpanded">
          <el-collapse-item title="Advanced Options" name="advanced">
            <!-- Processing Timeout -->
            <div class="advanced-item">
              <label class="advanced-label">Processing Timeout (minutes)</label>
              <el-input-number
                v-model="config.timeout"
                :min="1"
                :max="120"
                :step="1"
                style="width: 200px"
              />
            </div>
            
            <!-- Retry Attempts -->
            <div class="advanced-item">
              <label class="advanced-label">Retry Attempts on Failure</label>
              <el-input-number
                v-model="config.retryAttempts"
                :min="0"
                :max="5"
                :step="1"
                style="width: 200px"
              />
            </div>
            
            <!-- Enable Notifications -->
            <div class="advanced-item">
              <label class="advanced-label">Enable Browser Notifications</label>
              <el-switch
                v-model="config.enableNotifications"
                active-text="Enabled"
                inactive-text="Disabled"
              />
            </div>
            
            <!-- Save as Default -->
            <div class="advanced-item">
              <el-checkbox v-model="config.saveAsDefault">
                Save as default configuration
              </el-checkbox>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel" :aria-label="'Cancel pipeline configuration'">
          Cancel
        </el-button>
        <el-button type="primary" @click="handleConfirm" :loading="isSubmitting" :aria-label="'Start pipeline with configuration'">
          {{ isSubmitting ? 'Starting...' : 'Start Pipeline' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

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

interface Props {
  visible: boolean
  defaultConfig?: Partial<PipelineConfig>
}

const props = withDefaults(defineProps<Props>(), {
  defaultConfig: () => ({})
})

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  'confirm': [config: PipelineConfig]
  'cancel': []
}>()

// Reactive data
const formRef = ref()
const isSubmitting = ref(false)
const advancedExpanded = ref([''])

const config = ref<PipelineConfig>({
  presetType: 'custom',
  keywordsText: '',
  maxCount: 1000,
  executionMode: 'async',
  timeout: 30,
  retryAttempts: 2,
  enableNotifications: true,
  saveAsDefault: false
})

// Presets
const keywordPresets = {
  tech: [
    'AI', 'Machine Learning', 'Deep Learning', 'Neural Networks',
    'Python', 'JavaScript', 'Vue.js', 'React', 'TypeScript',
    'Cloud Computing', 'Big Data', 'Blockchain', 'IoT', '5G'
  ],
  business: [
    'Finance', 'Investment', 'Stock Market', 'Economy',
    'Business Strategy', 'Marketing', 'Sales', 'Revenue',
    'Profit', 'Growth', 'Startup', 'Entrepreneur', 'Innovation'
  ],
  entertainment: [
    'Movie', 'Music', 'TV Show', 'Celebrity', 'Entertainment',
    'Concert', 'Festival', 'Game', 'Sports', 'Hollywood',
    'Bollywood', 'Streaming', 'Netflix', 'YouTube', 'TikTok'
  ],
  news: [
    'Politics', 'Election', 'Government', 'Policy', 'News',
    'World News', 'Local News', 'Breaking News', 'Journalism',
    'Media', 'Press', 'Report', 'Analysis', 'Opinion'
  ]
}

// Computed properties
const keywordCount = computed(() => {
  if (!config.value.keywordsText) return 0
  return config.value.keywordsText.split('\n').filter(line => line.trim()).length
})

// Validation rules
const rules = {
  keywordsText: [
    { required: true, message: 'Please enter keywords', trigger: 'blur' },
    { min: 1, message: 'Please enter at least one keyword', trigger: 'blur' }
  ],
  maxCount: [
    { required: true, message: 'Please set max processing count', trigger: 'blur' },
    { type: 'number', min: 100, max: 100000, message: 'Must be between 100 and 100000', trigger: 'blur' }
  ],
  executionMode: [
    { required: true, message: 'Please select execution mode', trigger: 'change' }
  ]
}

// Methods
const handlePresetChange = (presetType: string) => {
  if (presetType === 'custom') {
    config.value.keywordsText = ''
  } else {
    const keywords = keywordPresets[presetType as keyof typeof keywordPresets]
    config.value.keywordsText = keywords.join('\n')
  }
}

const handleConfirm = async () => {
  try {
    await formRef.value.validate()
    isSubmitting.value = true
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    emit('confirm', { ...config.value })
    emit('update:visible', false)
    
    ElMessage.success('Pipeline started successfully')
  } catch (error) {
    console.error('Validation failed:', error)
  } finally {
    isSubmitting.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
  emit('update:visible', false)
}

// Watch for default config changes
watch(() => props.defaultConfig, (newConfig) => {
  if (newConfig && Object.keys(newConfig).length > 0) {
    Object.assign(config.value, newConfig)
  }
}, { immediate: true, deep: true })
</script>

<style scoped>
.keywords-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.preset-selector {
  margin-bottom: var(--spacing-sm);
}

.keywords-input {
  position: relative;
}

.keywords-count {
  position: absolute;
  bottom: var(--spacing-xs);
  right: var(--spacing-xs);
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
  background: var(--color-bg-white);
  padding: 2px 6px;
  border-radius: var(--border-radius-xs);
}

.form-help {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.mode-option {
  width: 100%;
  margin-bottom: var(--spacing-sm);
}

.mode-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-left: var(--spacing-lg);
}

.mode-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.mode-desc {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.advanced-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.advanced-label {
  font-size: var(--font-size-small);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

/* Responsive */
@media (max-width: 768px) {
  .keywords-config {
    gap: var(--spacing-sm);
  }
  
  .advanced-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }
  
  .dialog-footer {
    flex-direction: column;
  }
  
  .dialog-footer .el-button {
    width: 100%;
  }
}
</style>
