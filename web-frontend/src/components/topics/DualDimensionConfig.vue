<template>
  <div class="dual-dimension-config">
    <!-- 公式展示 -->
    <div class="formula-display">
      <div class="formula-title">双维度排序公式</div>
      <div class="formula-content">
        <span class="formula-text">S = </span>
        <span class="formula-alpha">{{ config.alpha.toFixed(2) }}</span>
        <span class="formula-text"> · |E| + </span>
        <span class="formula-beta">{{ config.beta.toFixed(2) }}</span>
        <span class="formula-text"> · P</span>
      </div>
      <div class="formula-legend">
        <span><strong>S</strong>: 综合得分</span>
        <span><strong>E</strong>: 情感强度</span>
        <span><strong>P</strong>: 热度得分</span>
      </div>
    </div>

    <!-- 主要权重调节 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><el-icon><Setting /></el-icon> 权重配置</span>
          <el-switch v-model="linkedSliders" active-text="联动" inactive-text="独立" size="small" />
        </div>
      </template>
      
      <div class="weight-sliders">
        <div class="slider-item">
          <div class="slider-label">
            <span>α 情感权重</span>
            <el-input-number 
              v-model="config.alpha" 
              :min="0" 
              :max="1" 
              :step="0.05" 
              :precision="2"
              size="small"
              @change="onAlphaChange"
            />
          </div>
          <el-slider 
            v-model="config.alpha" 
            :min="0" 
            :max="1" 
            :step="0.01"
            :format-tooltip="(val: number) => val.toFixed(2)"
            @input="onAlphaChange"
          />
        </div>
        
        <div class="slider-item">
          <div class="slider-label">
            <span>β 热度权重</span>
            <el-input-number 
              v-model="config.beta" 
              :min="0" 
              :max="1" 
              :step="0.05" 
              :precision="2"
              size="small"
              @change="onBetaChange"
            />
          </div>
          <el-slider 
            v-model="config.beta" 
            :min="0" 
            :max="1" 
            :step="0.01"
            :format-tooltip="(val: number) => val.toFixed(2)"
            @input="onBetaChange"
          />
        </div>
        
        <div class="weight-sum" :class="{ warning: Math.abs(config.alpha + config.beta - 1) > 0.01 }">
          <span>α + β = {{ (config.alpha + config.beta).toFixed(2) }}</span>
          <el-tag v-if="Math.abs(config.alpha + config.beta - 1) <= 0.01" type="success" size="small">正常</el-tag>
          <el-tag v-else type="warning" size="small">建议为1</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 高级参数 -->
    <el-collapse v-model="activeCollapse">
      <el-collapse-item title="高级参数" name="advanced">
        <div class="advanced-params">
          <div class="param-group">
            <div class="param-title">时间衰减系数 γ</div>
            <div class="param-row">
              <el-slider 
                v-model="config.gamma" 
                :min="0" 
                :max="1" 
                :step="0.01"
                :format-tooltip="(val: number) => val.toFixed(2)"
                style="flex: 1;"
              />
              <el-input-number 
                v-model="config.gamma" 
                :min="0" 
                :max="1" 
                :step="0.01" 
                :precision="2"
                size="small"
              />
            </div>
            <div class="param-desc">值越大，旧数据衰减越快</div>
          </div>
          
          <el-divider />
          
          <div class="param-title">互动权重配置</div>
          <div class="interaction-weights">
            <div class="interaction-item">
              <span class="interaction-label"><el-icon><Share /></el-icon> 转发权重</span>
              <el-input-number 
                v-model="config.repostWeight" 
                :min="0" 
                :max="10" 
                :step="0.1" 
                :precision="1"
                size="small"
              />
            </div>
            <div class="interaction-item">
              <span class="interaction-label"><el-icon><ChatDotRound /></el-icon> 评论权重</span>
              <el-input-number 
                v-model="config.commentWeight" 
                :min="0" 
                :max="10" 
                :step="0.1" 
                :precision="1"
                size="small"
              />
            </div>
            <div class="interaction-item">
              <span class="interaction-label"><el-icon><Star /></el-icon> 点赞权重</span>
              <el-input-number 
                v-model="config.likeWeight" 
                :min="0" 
                :max="10" 
                :step="0.1" 
                :precision="1"
                size="small"
              />
            </div>
          </div>
          <div class="param-desc">
            热度公式: P = log(1 + {{ config.repostWeight }}×转发 + {{ config.commentWeight }}×评论 + {{ config.likeWeight }}×点赞)
          </div>
        </div>
      </el-collapse-item>
      
      <el-collapse-item title="预设配置" name="presets">
        <div class="presets-section">
          <div class="preset-list">
            <div 
              v-for="preset in presets" 
              :key="preset.name"
              class="preset-item"
              :class="{ active: currentPreset === preset.name }"
              @click="loadPreset(preset)"
            >
              <div class="preset-name">{{ preset.name }}</div>
              <div class="preset-desc">{{ preset.description }}</div>
              <div class="preset-values">
                α={{ preset.config.alpha }}, β={{ preset.config.beta }}
              </div>
            </div>
          </div>
          
          <el-divider />
          
          <div class="preset-actions">
            <el-input 
              v-model="newPresetName" 
              placeholder="预设名称" 
              size="small" 
              style="width: 150px;"
            />
            <el-button type="primary" size="small" :disabled="!newPresetName" @click="savePreset">
              保存当前配置
            </el-button>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 实时效果预览 -->
    <el-card v-if="showPreview" class="preview-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><el-icon><DataAnalysis /></el-icon> 排序效果预览</span>
          <el-button text size="small" :loading="previewLoading" @click="refreshPreview">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      
      <div v-loading="previewLoading" class="preview-content">
        <div class="ranking-comparison">
          <div class="ranking-column">
            <div class="ranking-title">调整前</div>
            <div class="ranking-list">
              <div 
                v-for="(item, index) in previewData.before" 
                :key="'before-' + index"
                class="ranking-item"
              >
                <span class="rank">{{ index + 1 }}</span>
                <span class="topic">{{ item.topic }}</span>
                <span class="score">{{ item.score.toFixed(2) }}</span>
              </div>
            </div>
          </div>
          
          <div class="ranking-changes">
            <div class="change-title">排名变化</div>
            <div class="change-list">
              <div 
                v-for="(change, index) in rankingChanges" 
                :key="'change-' + index"
                class="change-item"
                :class="{ 
                  'up': change > 0, 
                  'down': change < 0, 
                  'same': change === 0,
                  'highlight': Math.abs(change) >= 3
                }"
              >
                <el-icon v-if="change > 0"><Top /></el-icon>
                <el-icon v-else-if="change < 0"><Bottom /></el-icon>
                <span v-else>-</span>
                <span v-if="change !== 0">{{ Math.abs(change) }}</span>
              </div>
            </div>
          </div>
          
          <div class="ranking-column">
            <div class="ranking-title">调整后</div>
            <div class="ranking-list">
              <div 
                v-for="(item, index) in previewData.after" 
                :key="'after-' + index"
                class="ranking-item"
                :class="{ highlight: isHighlightTopic(item.topic) }"
              >
                <span class="rank">{{ index + 1 }}</span>
                <span class="topic">{{ item.topic }}</span>
                <span class="score">{{ item.score.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="preview-stats">
          <el-statistic title="排名变化话题数" :value="changedCount" />
          <el-statistic title="最大变化幅度" :value="maxChange" />
          <el-statistic title="平均变化幅度" :value="avgChange.toFixed(1)" />
        </div>
      </div>
    </el-card>

    <!-- 操作按钮 -->
    <div class="config-actions">
      <el-button @click="resetConfig">
        <el-icon><RefreshLeft /></el-icon> 重置默认
      </el-button>
      <el-button type="primary" :loading="applying" @click="applyConfig">
        <el-icon><Check /></el-icon> 应用配置
      </el-button>
      <el-button type="success" :loading="saving" @click="saveToBackend">
        <el-icon><Upload /></el-icon> 保存到服务器
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { 
  Setting, Share, ChatDotRound, Star, DataAnalysis, Refresh,
  Top, Bottom, RefreshLeft, Check, Upload
} from '@element-plus/icons-vue';
import { debounce } from 'lodash-es';

// Props
const props = defineProps<{
  showPreview?: boolean;
}>();

// Emits
const emit = defineEmits<{
  (e: 'config-change', config: typeof config): void;
  (e: 'apply', config: typeof config): void;
}>();

// 配置状态
const config = reactive({
  alpha: 0.6,           // 情感权重
  beta: 0.4,            // 热度权重
  gamma: 0.1,           // 时间衰减系数
  repostWeight: 1.0,    // 转发权重
  commentWeight: 2.0,   // 评论权重
  likeWeight: 1.0,      // 点赞权重
});

// UI状态
const linkedSliders = ref(true);
const activeCollapse = ref<string[]>([]);
const previewLoading = ref(false);
const applying = ref(false);
const saving = ref(false);
const currentPreset = ref('');
const newPresetName = ref('');

// 预设配置
const presets = ref([
  {
    name: '默认配置',
    description: '情感与热度均衡',
    config: { alpha: 0.6, beta: 0.4, gamma: 0.1, repostWeight: 1.0, commentWeight: 2.0, likeWeight: 1.0 }
  },
  {
    name: '情感优先',
    description: '更关注情感强度',
    config: { alpha: 0.8, beta: 0.2, gamma: 0.1, repostWeight: 1.0, commentWeight: 2.0, likeWeight: 1.0 }
  },
  {
    name: '热度优先',
    description: '更关注传播热度',
    config: { alpha: 0.3, beta: 0.7, gamma: 0.1, repostWeight: 1.5, commentWeight: 2.0, likeWeight: 1.0 }
  },
  {
    name: '舆情监控',
    description: '强调负面情感',
    config: { alpha: 0.7, beta: 0.3, gamma: 0.2, repostWeight: 2.0, commentWeight: 3.0, likeWeight: 0.5 }
  },
]);

// 预览数据
const previewData = reactive({
  before: [] as Array<{ topic: string; score: number }>,
  after: [] as Array<{ topic: string; score: number }>,
});

// 计算属性
const rankingChanges = computed(() => {
  if (previewData.before.length === 0 || previewData.after.length === 0) return [];
  
  return previewData.after.map((afterItem, afterIndex) => {
    const beforeIndex = previewData.before.findIndex(b => b.topic === afterItem.topic);
    return beforeIndex >= 0 ? beforeIndex - afterIndex : 0;
  });
});

const changedCount = computed(() => rankingChanges.value.filter(c => c !== 0).length);
const maxChange = computed(() => Math.max(...rankingChanges.value.map(Math.abs), 0));
const avgChange = computed(() => {
  const changes = rankingChanges.value.filter(c => c !== 0);
  return changes.length > 0 ? changes.reduce((a, b) => a + Math.abs(b), 0) / changes.length : 0;
});

const highlightTopics = computed(() => {
  const threshold = 3;
  return previewData.after
    .filter((_, index) => Math.abs(rankingChanges.value[index] || 0) >= threshold)
    .map(item => item.topic);
});

// 方法
const onAlphaChange = (val: number) => {
  if (linkedSliders.value) {
    config.beta = Math.max(0, Math.min(1, 1 - val));
  }
  debouncedPreview();
};

const onBetaChange = (val: number) => {
  if (linkedSliders.value) {
    config.alpha = Math.max(0, Math.min(1, 1 - val));
  }
  debouncedPreview();
};

const loadPreset = (preset: typeof presets.value[0]) => {
  Object.assign(config, preset.config);
  currentPreset.value = preset.name;
  ElMessage.success(`已加载预设: ${preset.name}`);
  debouncedPreview();
};

const savePreset = () => {
  if (!newPresetName.value) return;
  
  presets.value.push({
    name: newPresetName.value,
    description: '自定义配置',
    config: { ...config }
  });
  
  // 保存到localStorage
  localStorage.setItem('dual_dimension_presets', JSON.stringify(presets.value));
  
  ElMessage.success(`预设 "${newPresetName.value}" 已保存`);
  newPresetName.value = '';
};

const resetConfig = () => {
  config.alpha = 0.6;
  config.beta = 0.4;
  config.gamma = 0.1;
  config.repostWeight = 1.0;
  config.commentWeight = 2.0;
  config.likeWeight = 1.0;
  currentPreset.value = '默认配置';
  ElMessage.info('已重置为默认配置');
  debouncedPreview();
};

const applyConfig = async () => {
  applying.value = true;
  try {
    emit('apply', { ...config });
    ElMessage.success('配置已应用');
  } finally {
    applying.value = false;
  }
};

const saveToBackend = async () => {
  saving.value = true;
  try {
    // 调用后端API保存配置
    const response = await fetch('/api/weibo/ranking/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    if (response.ok) {
      ElMessage.success('配置已保存到服务器');
    } else {
      throw new Error('保存失败');
    }
  } catch (error) {
    // 保存到localStorage作为备份
    localStorage.setItem('dual_dimension_config', JSON.stringify(config));
    ElMessage.warning('服务器保存失败，已保存到本地');
  } finally {
    saving.value = false;
  }
};

const refreshPreview = async () => {
  previewLoading.value = true;
  try {
    // 调用后端API获取预览数据
    const response = await fetch('/api/weibo/ranking/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    if (response.ok) {
      const data = await response.json();
      previewData.before = data.data?.before || [];
      previewData.after = data.data?.after || [];
    } else {
      throw new Error('获取预览失败');
    }
  } catch (error) {
    // 使用模拟数据
    generateMockPreview();
  } finally {
    previewLoading.value = false;
  }
};

const generateMockPreview = () => {
  const topics = [
    '人工智能发展', '新能源汽车', '房价走势', '教育改革', '医疗保障',
    '环境保护', '科技创新', '就业形势', '消费升级', '数字经济'
  ];
  
  // 生成调整前数据（按热度排序）
  previewData.before = topics.map((topic, i) => ({
    topic,
    score: 100 - i * 8 + Math.random() * 5
  })).sort((a, b) => b.score - a.score);
  
  // 生成调整后数据（按双维度排序）
  previewData.after = topics.map((topic) => {
    const sentiment = Math.random() * 2 - 1; // -1 to 1
    const heat = Math.random() * 100;
    const score = config.alpha * Math.abs(sentiment) * 100 + config.beta * heat;
    return { topic, score };
  }).sort((a, b) => b.score - a.score);
};

const isHighlightTopic = (topic: string) => highlightTopics.value.includes(topic);

// 防抖预览
const debouncedPreview = debounce(() => {
  if (props.showPreview) {
    refreshPreview();
  }
  emit('config-change', { ...config });
}, 300);

// 监听配置变化
watch(config, () => {
  // 保存到localStorage
  localStorage.setItem('dual_dimension_config', JSON.stringify(config));
}, { deep: true });

// 初始化
onMounted(() => {
  // 从localStorage加载配置
  const savedConfig = localStorage.getItem('dual_dimension_config');
  if (savedConfig) {
    try {
      Object.assign(config, JSON.parse(savedConfig));
    } catch (e) {
      console.error('加载配置失败:', e);
    }
  }
  
  // 加载自定义预设
  const savedPresets = localStorage.getItem('dual_dimension_presets');
  if (savedPresets) {
    try {
      presets.value = JSON.parse(savedPresets);
    } catch (e) {
      console.error('加载预设失败:', e);
    }
  }
  
  // 初始预览
  if (props.showPreview) {
    refreshPreview();
  }
});
</script>

<style scoped lang="scss">
.dual-dimension-config {
  padding: 20px;
}

.formula-display {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 20px;
  color: #fff;
  text-align: center;
  margin-bottom: 20px;
  
  .formula-title {
    font-size: 14px;
    opacity: 0.9;
    margin-bottom: 10px;
  }
  
  .formula-content {
    font-size: 28px;
    font-family: 'Times New Roman', serif;
    margin-bottom: 15px;
    
    .formula-alpha {
      color: #ffd700;
      font-weight: bold;
    }
    
    .formula-beta {
      color: #00ff88;
      font-weight: bold;
    }
  }
  
  .formula-legend {
    font-size: 12px;
    opacity: 0.8;
    
    span {
      margin: 0 15px;
    }
  }
}

.config-card {
  margin-bottom: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.weight-sliders {
  .slider-item {
    margin-bottom: 25px;
    
    .slider-label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      font-weight: 500;
    }
  }
  
  .weight-sum {
    text-align: center;
    padding: 10px;
    background: #f5f7fa;
    border-radius: 8px;
    
    &.warning {
      background: #fdf6ec;
      color: #e6a23c;
    }
    
    span {
      margin-right: 10px;
    }
  }
}

.advanced-params {
  .param-group {
    margin-bottom: 20px;
  }
  
  .param-title {
    font-weight: 500;
    margin-bottom: 10px;
    color: #303133;
  }
  
  .param-row {
    display: flex;
    align-items: center;
    gap: 15px;
  }
  
  .param-desc {
    font-size: 12px;
    color: #909399;
    margin-top: 8px;
  }
}

.interaction-weights {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  
  .interaction-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    
    .interaction-label {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 13px;
      color: #606266;
    }
  }
}

.presets-section {
  .preset-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 15px;
  }
  
  .preset-item {
    padding: 12px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover {
      border-color: #409eff;
      background: #f5f7fa;
    }
    
    &.active {
      border-color: #409eff;
      background: #ecf5ff;
    }
    
    .preset-name {
      font-weight: 500;
      margin-bottom: 5px;
    }
    
    .preset-desc {
      font-size: 12px;
      color: #909399;
      margin-bottom: 5px;
    }
    
    .preset-values {
      font-size: 11px;
      color: #606266;
      font-family: monospace;
    }
  }
  
  .preset-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }
}

.preview-card {
  margin-bottom: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.preview-content {
  .ranking-comparison {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
  }
  
  .ranking-column {
    flex: 1;
    
    .ranking-title {
      text-align: center;
      font-weight: 500;
      padding: 10px;
      background: #f5f7fa;
      border-radius: 8px 8px 0 0;
    }
    
    .ranking-list {
      border: 1px solid #ebeef5;
      border-top: none;
      border-radius: 0 0 8px 8px;
    }
    
    .ranking-item {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      border-bottom: 1px solid #ebeef5;
      
      &:last-child {
        border-bottom: none;
      }
      
      &.highlight {
        background: #fdf6ec;
      }
      
      .rank {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #409eff;
        color: #fff;
        border-radius: 50%;
        font-size: 12px;
        margin-right: 10px;
      }
      
      .topic {
        flex: 1;
        font-size: 13px;
      }
      
      .score {
        font-size: 12px;
        color: #909399;
        font-family: monospace;
      }
    }
  }
  
  .ranking-changes {
    width: 60px;
    
    .change-title {
      text-align: center;
      font-size: 12px;
      color: #909399;
      padding: 10px 0;
    }
    
    .change-list {
      display: flex;
      flex-direction: column;
    }
    
    .change-item {
      height: 41px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 2px;
      font-size: 12px;
      
      &.up {
        color: #67c23a;
      }
      
      &.down {
        color: #f56c6c;
      }
      
      &.same {
        color: #909399;
      }
      
      &.highlight {
        font-weight: bold;
        background: #fef0f0;
      }
    }
  }
  
  .preview-stats {
    display: flex;
    justify-content: space-around;
    padding: 15px;
    background: #f5f7fa;
    border-radius: 8px;
  }
}

.config-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
}
</style>
