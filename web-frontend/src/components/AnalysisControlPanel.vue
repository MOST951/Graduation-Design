<template>
  <div class="analysis-control-panel">
    <!-- 1. 数据源选择 -->
    <div class="panel-section">
      <div class="section-title">
        <el-icon><DataAnalysis /></el-icon>
        数据源选择
      </div>
      
      <el-form :model="config" label-position="top" size="default">
        <el-form-item label="数据范围">
          <el-select v-model="config.dataSource" placeholder="选择数据范围" style="width: 100%;">
            <el-option label="全部数据" value="all" />
            <el-option label="指定任务" value="task" />
            <el-option label="自定义筛选" value="custom" />
          </el-select>
        </el-form-item>

        <!-- 指定任务时显示任务选择 -->
        <el-form-item v-if="config.dataSource === 'task'" label="选择任务">
          <el-select
            v-model="config.selectedTasks"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择要分析的任务"
            style="width: 100%;"
          >
            <el-option
              v-for="task in availableTasks"
              :key="task.id"
              :label="task.name"
              :value="task.id"
            >
              <span>{{ task.name }}</span>
              <span class="task-count">{{ task.dataCount }}条</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-date-picker
            v-model="config.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%;"
            :shortcuts="dateShortcuts"
          />
        </el-form-item>

        <el-form-item label="关键词筛选">
          <el-select
            v-model="config.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入关键词"
            style="width: 100%;"
          >
            <el-option
              v-for="kw in availableKeywords"
              :key="kw"
              :label="kw"
              :value="kw"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- 2. 分析模型配置 -->
    <div class="panel-section">
      <div class="section-title">
        <el-icon><Cpu /></el-icon>
        分析模型配置
      </div>

      <el-form :model="config" label-position="top" size="default">
        <el-form-item label="模型选择">
          <el-select v-model="config.model" placeholder="选择分析模型" style="width: 100%;">
            <el-option label="BERT (推荐)" value="bert">
              <div class="model-option">
                <span>BERT</span>
                <el-tag size="small" type="success">推荐</el-tag>
              </div>
            </el-option>
            <el-option label="LSTM" value="lstm" />
            <el-option label="SVM" value="svm" />
            <el-option label="集成模型" value="ensemble">
              <div class="model-option">
                <span>集成模型</span>
                <el-tag size="small" type="warning">高精度</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="情感粒度">
          <el-radio-group v-model="config.granularity" class="granularity-group">
            <el-radio-button label="binary">
              <el-tooltip content="正面/负面" placement="top">
                <span>二分类</span>
              </el-tooltip>
            </el-radio-button>
            <el-radio-button label="ternary">
              <el-tooltip content="正面/中性/负面" placement="top">
                <span>三分类</span>
              </el-tooltip>
            </el-radio-button>
            <el-radio-button label="fine">
              <el-tooltip content="8种细粒度情感" placement="top">
                <span>细粒度</span>
              </el-tooltip>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 细粒度情感说明 -->
        <div v-if="config.granularity === 'fine'" class="fine-emotions">
          <el-tag v-for="emotion in fineEmotions" :key="emotion.name" :type="emotion.type" size="small">
            {{ emotion.name }}
          </el-tag>
        </div>

        <el-form-item label="置信度阈值">
          <el-slider
            v-model="config.confidenceThreshold"
            :min="0.5"
            :max="1.0"
            :step="0.05"
            :marks="confidenceMarks"
            show-stops
          />
          <div class="threshold-hint">
            低于 {{ config.confidenceThreshold }} 的结果将标记为"不确定"
          </div>
        </el-form-item>

        <!-- 高级参数 -->
        <el-collapse v-model="advancedExpanded" class="advanced-collapse">
          <el-collapse-item title="高级参数" name="advanced">
            <el-form-item label="学习率">
              <el-select v-model="config.learningRate" style="width: 100%;">
                <el-option label="1e-5 (保守)" :value="0.00001" />
                <el-option label="2e-5 (推荐)" :value="0.00002" />
                <el-option label="5e-5 (激进)" :value="0.00005" />
              </el-select>
            </el-form-item>

            <el-form-item label="批次大小">
              <el-select v-model="config.batchSize" style="width: 100%;">
                <el-option label="16 (低内存)" :value="16" />
                <el-option label="32 (推荐)" :value="32" />
                <el-option label="64 (高性能)" :value="64" />
              </el-select>
            </el-form-item>

            <el-form-item label="最大序列长度">
              <el-input-number
                v-model="config.maxSeqLength"
                :min="64"
                :max="512"
                :step="64"
                style="width: 100%;"
              />
            </el-form-item>

            <el-form-item label="GPU 加速">
              <el-switch v-model="config.useGpu" active-text="启用" inactive-text="禁用" />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </div>

    <!-- 3. 操作按钮组 -->
    <div class="panel-section action-section">
      <el-button
        type="primary"
        :loading="isAnalyzing"
        :disabled="!canStartAnalysis"
        @click="handleStartAnalysis"
        style="width: 100%;"
      >
        <el-icon><VideoPlay /></el-icon>
        {{ isAnalyzing ? '分析中...' : '开始分析' }}
      </el-button>

      <el-button
        v-if="config.selectedTasks.length > 1"
        type="success"
        :loading="isAnalyzing"
        @click="handleBatchAnalysis"
        style="width: 100%; margin-top: 10px;"
      >
        <el-icon><Files /></el-icon>
        批量分析 ({{ config.selectedTasks.length }}个任务)
      </el-button>

      <div class="button-row">
        <el-button @click="handleSaveConfig">
          <el-icon><FolderChecked /></el-icon>
          保存配置
        </el-button>
        <el-button plain @click="handleReset">
          <el-icon><RefreshLeft /></el-icon>
          重置
        </el-button>
      </div>

      <el-button
        type="warning"
        plain
        @click="trainingDialogVisible = true"
        style="width: 100%; margin-top: 10px;"
      >
        <el-icon><Setting /></el-icon>
        模型训练
      </el-button>
    </div>

    <!-- 模型训练对话框 -->
    <ModelTrainingDialog
      v-model="trainingDialogVisible"
      @training-complete="handleTrainingComplete"
    />

    <!-- 4. 历史分析记录 -->
    <div class="panel-section history-section">
      <div class="section-title">
        <el-icon><Clock /></el-icon>
        历史分析记录
        <el-button text size="small" @click="clearHistory" class="clear-btn">清空</el-button>
      </div>

      <el-scrollbar height="200px" v-if="analysisHistory.length > 0">
        <el-timeline>
          <el-timeline-item
            v-for="item in analysisHistory"
            :key="item.id"
            :timestamp="item.time"
            :type="getHistoryItemType(item.status)"
            placement="top"
          >
            <div class="history-item" @click="loadHistoryConfig(item)">
              <div class="history-title">{{ item.name }}</div>
              <div class="history-meta">
                <el-tag size="small" :type="getModelTagType(item.model)">{{ item.model }}</el-tag>
                <span class="history-count">{{ item.dataCount }}条</span>
              </div>
              <div class="history-result" v-if="item.status === 'completed'">
                <span class="positive">正面 {{ item.result?.positive }}%</span>
                <span class="negative">负面 {{ item.result?.negative }}%</span>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-scrollbar>

      <el-empty v-else description="暂无分析记录" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  DataAnalysis, Cpu, VideoPlay, Files, FolderChecked,
  RefreshLeft, Clock, Setting
} from '@element-plus/icons-vue';
import ModelTrainingDialog from './ModelTrainingDialog.vue';

// Props & Emits
const emit = defineEmits<{
  (e: 'start-analysis', config: any): void;
  (e: 'batch-analysis', config: any): void;
  (e: 'config-change', config: any): void;
}>();

// 分析配置
const config = reactive({
  // 数据源
  dataSource: 'all',
  selectedTasks: [] as number[],
  dateRange: null as [Date, Date] | null,
  keywords: [] as string[],
  // 模型配置
  model: 'bert',
  granularity: 'ternary',
  confidenceThreshold: 0.7,
  // 高级参数
  learningRate: 0.00002,
  batchSize: 32,
  maxSeqLength: 128,
  useGpu: true,
});

// 状态
const isAnalyzing = ref(false);
const advancedExpanded = ref<string[]>([]);
const trainingDialogVisible = ref(false);

// 可用任务列表（模拟数据）
const availableTasks = ref([
  { id: 1, name: '热点话题监控', dataCount: 4521 },
  { id: 2, name: '品牌舆情分析', dataCount: 8934 },
  { id: 3, name: '竞品监控任务', dataCount: 2156 },
  { id: 4, name: '用户反馈收集', dataCount: 3678 },
  { id: 5, name: '行业动态追踪', dataCount: 5432 },
]);

// 可用关键词
const availableKeywords = ref([
  '热搜', '头条', '品牌', '产品', '竞品', '反馈', '投诉', '好评', '差评'
]);

// 细粒度情感列表
const fineEmotions = [
  { name: '喜悦', type: 'success' },
  { name: '愤怒', type: 'danger' },
  { name: '悲伤', type: 'info' },
  { name: '恐惧', type: 'warning' },
  { name: '惊讶', type: '' },
  { name: '厌恶', type: 'danger' },
  { name: '信任', type: 'success' },
  { name: '期待', type: 'warning' },
];

// 日期快捷选项
const dateShortcuts = [
  {
    text: '最近一周',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
      return [start, end];
    },
  },
  {
    text: '最近一月',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30);
      return [start, end];
    },
  },
  {
    text: '最近三月',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90);
      return [start, end];
    },
  },
];

// 置信度标记
const confidenceMarks = {
  0.5: '0.5',
  0.7: '0.7',
  0.9: '0.9',
  1.0: '1.0',
};

// 历史分析记录
const analysisHistory = ref([
  {
    id: 1,
    name: '热点话题分析',
    time: '2025-12-10 02:30',
    model: 'BERT',
    dataCount: 4521,
    status: 'completed',
    result: { positive: 45.2, negative: 23.8, neutral: 31.0 },
    config: { model: 'bert', granularity: 'ternary', confidenceThreshold: 0.7 },
  },
  {
    id: 2,
    name: '品牌舆情分析',
    time: '2025-12-09 18:45',
    model: 'LSTM',
    dataCount: 8934,
    status: 'completed',
    result: { positive: 52.1, negative: 18.3, neutral: 29.6 },
    config: { model: 'lstm', granularity: 'ternary', confidenceThreshold: 0.65 },
  },
  {
    id: 3,
    name: '用户反馈分析',
    time: '2025-12-09 14:20',
    model: '集成模型',
    dataCount: 3678,
    status: 'failed',
    config: { model: 'ensemble', granularity: 'fine', confidenceThreshold: 0.8 },
  },
]);

// 计算属性
const canStartAnalysis = computed(() => {
  if (config.dataSource === 'task' && config.selectedTasks.length === 0) {
    return false;
  }
  return true;
});

// 方法
function handleStartAnalysis() {
  if (!canStartAnalysis.value) {
    ElMessage.warning('请先选择要分析的数据');
    return;
  }

  isAnalyzing.value = true;
  emit('start-analysis', { ...config });

  // 模拟分析过程
  setTimeout(() => {
    isAnalyzing.value = false;
    
    // 添加到历史记录
    analysisHistory.value.unshift({
      id: Date.now(),
      name: config.dataSource === 'task' 
        ? `任务分析 (${config.selectedTasks.length}个)`
        : '全量数据分析',
      time: new Date().toLocaleString('zh-CN', { 
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' 
      }),
      model: config.model.toUpperCase(),
      dataCount: Math.floor(Math.random() * 5000) + 1000,
      status: 'completed',
      result: {
        positive: Number((Math.random() * 40 + 30).toFixed(1)),
        negative: Number((Math.random() * 30 + 10).toFixed(1)),
        neutral: Number((Math.random() * 30 + 20).toFixed(1)),
      },
      config: { ...config },
    });

    ElMessage.success('分析完成！');
  }, 2000);
}

function handleBatchAnalysis() {
  ElMessageBox.confirm(
    `确定要对选中的 ${config.selectedTasks.length} 个任务进行批量分析吗？`,
    '批量分析确认',
    { type: 'info' }
  ).then(() => {
    isAnalyzing.value = true;
    emit('batch-analysis', { ...config });

    setTimeout(() => {
      isAnalyzing.value = false;
      ElMessage.success('批量分析任务已提交！');
    }, 1500);
  }).catch(() => {});
}

function handleSaveConfig() {
  // 保存配置到本地存储
  localStorage.setItem('analysisConfig', JSON.stringify(config));
  ElMessage.success('配置已保存');
}

function handleReset() {
  config.dataSource = 'all';
  config.selectedTasks = [];
  config.dateRange = null;
  config.keywords = [];
  config.model = 'bert';
  config.granularity = 'ternary';
  config.confidenceThreshold = 0.7;
  config.learningRate = 0.00002;
  config.batchSize = 32;
  config.maxSeqLength = 128;
  config.useGpu = true;
  ElMessage.info('配置已重置');
}

function handleTrainingComplete(result: any) {
  ElMessage.success(`模型训练完成！最佳准确率: ${result.bestAccuracy.toFixed(2)}%`);
  // 可以在这里更新模型列表或其他状态
}

function loadHistoryConfig(item: any) {
  if (item.config) {
    Object.assign(config, item.config);
    ElMessage.success(`已加载 "${item.name}" 的配置`);
  }
}

function clearHistory() {
  ElMessageBox.confirm('确定要清空所有历史记录吗？', '确认清空', { type: 'warning' })
    .then(() => {
      analysisHistory.value = [];
      ElMessage.success('历史记录已清空');
    })
    .catch(() => {});
}

function getHistoryItemType(status: string) {
  return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : 'primary';
}

function getModelTagType(model: string) {
  const map: Record<string, string> = {
    'BERT': 'success',
    'LSTM': 'primary',
    'SVM': 'info',
    '集成模型': 'warning',
  };
  return map[model] || '';
}

// 初始化：加载保存的配置
onMounted(() => {
  const savedConfig = localStorage.getItem('analysisConfig');
  if (savedConfig) {
    try {
      const parsed = JSON.parse(savedConfig);
      Object.assign(config, parsed);
    } catch (e) {
      console.error('加载配置失败:', e);
    }
  }
});
</script>

<style scoped>
.analysis-control-panel {
  width: 300px;
  height: 100%;
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.panel-section {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 15px;
}

.section-title .el-icon {
  color: #409eff;
}

.section-title .clear-btn {
  margin-left: auto;
  color: #909399;
}

/* 任务选项样式 */
.task-count {
  float: right;
  color: #909399;
  font-size: 12px;
}

/* 模型选项样式 */
.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

/* 情感粒度按钮组 */
.granularity-group {
  width: 100%;
}
.granularity-group :deep(.el-radio-button) {
  flex: 1;
}
.granularity-group :deep(.el-radio-button__inner) {
  width: 100%;
}

/* 细粒度情感标签 */
.fine-emotions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

/* 置信度提示 */
.threshold-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

/* 高级参数折叠面板 */
.advanced-collapse {
  border: none;
  margin-top: 10px;
}
.advanced-collapse :deep(.el-collapse-item__header) {
  background: #f5f7fa;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 13px;
}
.advanced-collapse :deep(.el-collapse-item__content) {
  padding: 15px 0 0;
}

/* 操作按钮区域 */
.action-section {
  background: #fafafa;
}
.button-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.button-row .el-button {
  flex: 1;
}

/* 历史记录区域 */
.history-section {
  flex: 1;
  min-height: 200px;
}

.history-item {
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background 0.2s;
}
.history-item:hover {
  background: #f5f7fa;
}

.history-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 5px;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.history-count {
  font-size: 12px;
  color: #909399;
}

.history-result {
  font-size: 12px;
  display: flex;
  gap: 10px;
}
.history-result .positive {
  color: #67c23a;
}
.history-result .negative {
  color: #f56c6c;
}

/* 表单样式调整 */
:deep(.el-form-item) {
  margin-bottom: 15px;
}
:deep(.el-form-item__label) {
  font-size: 13px;
  color: #606266;
  padding-bottom: 5px;
}
</style>
