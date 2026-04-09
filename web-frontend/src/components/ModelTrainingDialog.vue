<template>
  <el-dialog
    v-model="visible"
    title="模型训练"
    width="900px"
    :close-on-click-modal="false"
    :close-on-press-escape="!isTraining"
    @close="handleClose"
  >
    <el-steps :active="currentStep" finish-status="success" simple style="margin-bottom: 20px;">
      <el-step title="数据选择" />
      <el-step title="参数配置" />
      <el-step title="训练监控" />
    </el-steps>

    <!-- Step 1: 训练数据选择 -->
    <div v-show="currentStep === 0" class="step-content">
      <el-form label-width="120px">
        <el-form-item label="数据来源">
          <el-radio-group v-model="dataSource">
            <el-radio label="existing">已有标注数据集</el-radio>
            <el-radio label="upload">上传自定义数据集</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 已有数据集选择 -->
        <el-form-item v-if="dataSource === 'existing'" label="选择数据集">
          <el-select v-model="selectedDataset" placeholder="选择数据集" style="width: 100%;">
            <el-option
              v-for="ds in existingDatasets"
              :key="ds.id"
              :label="ds.name"
              :value="ds.id"
            >
              <div class="dataset-option">
                <span>{{ ds.name }}</span>
                <span class="dataset-info">{{ ds.count }} 条 | {{ ds.date }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <!-- 上传数据集 -->
        <el-form-item v-if="dataSource === 'upload'" label="上传文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".csv,.json"
            :on-change="handleFileChange"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 CSV 或 JSON 格式，文件大小不超过 100MB</div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 数据分布预览 -->
        <el-form-item label="数据分布预览">
          <div class="data-preview">
            <div id="data-distribution-chart" style="width: 100%; height: 200px;"></div>
            <div class="data-stats">
              <div class="stat-item">
                <span class="stat-label">总样本数</span>
                <span class="stat-value">{{ dataStats.total }}</span>
              </div>
              <div class="stat-item positive">
                <span class="stat-label">正面样本</span>
                <span class="stat-value">{{ dataStats.positive }} ({{ dataStats.positiveRatio }}%)</span>
              </div>
              <div class="stat-item neutral">
                <span class="stat-label">中性样本</span>
                <span class="stat-value">{{ dataStats.neutral }} ({{ dataStats.neutralRatio }}%)</span>
              </div>
              <div class="stat-item negative">
                <span class="stat-label">负面样本</span>
                <span class="stat-value">{{ dataStats.negative }} ({{ dataStats.negativeRatio }}%)</span>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- Step 2: 训练参数配置 -->
    <div v-show="currentStep === 1" class="step-content">
      <el-row :gutter="30">
        <el-col :span="12">
          <el-form label-width="120px" label-position="top">
            <el-form-item label="数据集划分比例">
              <div class="split-config">
                <div class="split-item">
                  <span class="split-label">训练集</span>
                  <el-input-number v-model="trainConfig.trainRatio" :min="50" :max="90" :step="5" />
                  <span class="split-unit">%</span>
                </div>
                <div class="split-item">
                  <span class="split-label">验证集</span>
                  <el-input-number v-model="trainConfig.valRatio" :min="5" :max="30" :step="5" />
                  <span class="split-unit">%</span>
                </div>
                <div class="split-item">
                  <span class="split-label">测试集</span>
                  <el-input-number v-model="trainConfig.testRatio" :min="5" :max="30" :step="5" disabled />
                  <span class="split-unit">%</span>
                </div>
              </div>
              <div class="split-bar">
                <div class="split-train" :style="{ width: trainConfig.trainRatio + '%' }">训练</div>
                <div class="split-val" :style="{ width: trainConfig.valRatio + '%' }">验证</div>
                <div class="split-test" :style="{ width: trainConfig.testRatio + '%' }">测试</div>
              </div>
            </el-form-item>

            <el-form-item label="批处理大小 (Batch Size)">
              <el-select v-model="trainConfig.batchSize" style="width: 100%;">
                <el-option label="16 (低内存)" :value="16" />
                <el-option label="32 (推荐)" :value="32" />
                <el-option label="64 (高性能)" :value="64" />
                <el-option label="128 (大内存)" :value="128" />
              </el-select>
            </el-form-item>

            <el-form-item label="学习率 (Learning Rate)">
              <el-select v-model="trainConfig.learningRate" style="width: 100%;">
                <el-option label="1e-5 (保守)" :value="0.00001" />
                <el-option label="2e-5 (推荐)" :value="0.00002" />
                <el-option label="3e-5 (适中)" :value="0.00003" />
                <el-option label="5e-5 (激进)" :value="0.00005" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-col>

        <el-col :span="12">
          <el-form label-width="120px" label-position="top">
            <el-form-item label="训练轮数 (Epochs)">
              <el-slider
                v-model="trainConfig.epochs"
                :min="1"
                :max="50"
                :marks="epochMarks"
                show-input
              />
            </el-form-item>

            <el-form-item label="早停策略 (Early Stopping)">
              <el-switch v-model="trainConfig.earlyStop" active-text="启用" />
              <div v-if="trainConfig.earlyStop" class="early-stop-config">
                <el-form-item label="耐心值" label-width="80px">
                  <el-input-number v-model="trainConfig.patience" :min="1" :max="10" />
                  <span class="config-tip">连续N轮无改善则停止</span>
                </el-form-item>
                <el-form-item label="最小改善" label-width="80px">
                  <el-input-number v-model="trainConfig.minDelta" :min="0.001" :max="0.1" :step="0.001" :precision="3" />
                </el-form-item>
              </div>
            </el-form-item>

            <el-form-item label="模型保存">
              <el-checkbox v-model="trainConfig.saveBest">保存最佳模型</el-checkbox>
              <el-checkbox v-model="trainConfig.saveCheckpoint">保存检查点</el-checkbox>
            </el-form-item>

            <el-form-item label="GPU 加速">
              <el-switch v-model="trainConfig.useGpu" active-text="启用" />
              <el-tag v-if="trainConfig.useGpu" type="success" size="small" style="margin-left: 10px;">
                GPU 可用: NVIDIA RTX 3080
              </el-tag>
            </el-form-item>
          </el-form>
        </el-col>
      </el-row>
    </div>

    <!-- Step 3: 训练过程监控 -->
    <div v-show="currentStep === 2" class="step-content">
      <el-row :gutter="20">
        <!-- 训练曲线 -->
        <el-col :span="16">
          <el-card shadow="never" class="monitor-card">
            <template #header>
              <div class="card-header">
                <span>训练曲线</span>
                <el-radio-group v-model="chartType" size="small">
                  <el-radio-button label="loss">损失</el-radio-button>
                  <el-radio-button label="accuracy">准确率</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div id="training-curve" style="width: 100%; height: 280px;"></div>
          </el-card>

          <!-- 训练日志 -->
          <el-card shadow="never" class="monitor-card log-card">
            <template #header>
              <div class="card-header">
                <span>训练日志</span>
                <el-button size="small" text @click="clearLogs">清空</el-button>
              </div>
            </template>
            <el-scrollbar ref="logScrollbar" height="150px">
              <div class="training-logs">
                <div v-for="(log, index) in trainingLogs" :key="index" :class="['log-line', `log-${log.level}`]">
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </el-scrollbar>
          </el-card>
        </el-col>

        <!-- 状态面板 -->
        <el-col :span="8">
          <el-card shadow="never" class="monitor-card status-card">
            <template #header>训练状态</template>
            <div class="status-content">
              <div class="status-item">
                <span class="status-label">当前状态</span>
                <el-tag :type="getStatusType(trainingStatus)">{{ getStatusText(trainingStatus) }}</el-tag>
              </div>
              <div class="status-item">
                <span class="status-label">当前轮次</span>
                <span class="status-value">{{ currentEpoch }} / {{ trainConfig.epochs }}</span>
              </div>
              <div class="status-item">
                <span class="status-label">当前批次</span>
                <span class="status-value">{{ currentBatch }} / {{ totalBatches }}</span>
              </div>
              <div class="status-item">
                <span class="status-label">训练损失</span>
                <span class="status-value">{{ currentLoss.toFixed(4) }}</span>
              </div>
              <div class="status-item">
                <span class="status-label">验证准确率</span>
                <span class="status-value">{{ currentAccuracy.toFixed(2) }}%</span>
              </div>
              <div class="status-item">
                <span class="status-label">最佳准确率</span>
                <span class="status-value highlight">{{ bestAccuracy.toFixed(2) }}%</span>
              </div>

              <el-divider />

              <div class="status-item">
                <span class="status-label">已用时间</span>
                <span class="status-value">{{ formatTime(elapsedTime) }}</span>
              </div>
              <div class="status-item">
                <span class="status-label">预计剩余</span>
                <span class="status-value">{{ formatTime(remainingTime) }}</span>
              </div>

              <el-divider />

              <div class="resource-usage">
                <div class="resource-item">
                  <span class="resource-label">GPU 使用率</span>
                  <el-progress :percentage="gpuUsage" :stroke-width="10" :color="getUsageColor(gpuUsage)" />
                </div>
                <div class="resource-item">
                  <span class="resource-label">内存使用</span>
                  <el-progress :percentage="memoryUsage" :stroke-width="10" :color="getUsageColor(memoryUsage)" />
                </div>
              </div>
            </div>
          </el-card>

          <!-- 训练进度 -->
          <el-card shadow="never" class="monitor-card">
            <template #header>总体进度</template>
            <el-progress
              :percentage="overallProgress"
              :stroke-width="20"
              :text-inside="true"
              :color="progressColors"
            />
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <div class="footer-left">
          <el-button v-if="currentStep > 0 && !isTraining" @click="prevStep">上一步</el-button>
        </div>
        <div class="footer-right">
          <el-button @click="handleClose" :disabled="isTraining">取消</el-button>
          
          <!-- Step 0 & 1: 下一步 -->
          <el-button v-if="currentStep < 2" type="primary" @click="nextStep">
            {{ currentStep === 1 ? '开始训练' : '下一步' }}
          </el-button>
          
          <!-- Step 2: 训练控制 -->
          <template v-if="currentStep === 2">
            <el-button
              v-if="trainingStatus === 'idle' || trainingStatus === 'completed' || trainingStatus === 'stopped'"
              type="primary"
              @click="startTraining"
            >
              <el-icon><VideoPlay /></el-icon> 开始训练
            </el-button>
            <el-button
              v-if="trainingStatus === 'training'"
              type="warning"
              @click="pauseTraining"
            >
              <el-icon><VideoPause /></el-icon> 暂停
            </el-button>
            <el-button
              v-if="trainingStatus === 'paused'"
              type="success"
              @click="resumeTraining"
            >
              <el-icon><VideoPlay /></el-icon> 继续
            </el-button>
            <el-button
              v-if="trainingStatus === 'training' || trainingStatus === 'paused'"
              type="danger"
              @click="stopTraining"
            >
              <el-icon><Close /></el-icon> 停止
            </el-button>
            <el-button
              v-if="trainingStatus === 'completed'"
              type="success"
              @click="saveModel"
            >
              <el-icon><FolderChecked /></el-icon> 保存模型
            </el-button>
          </template>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as echarts from 'echarts';
import { UploadFilled, VideoPlay, VideoPause, Close, FolderChecked } from '@element-plus/icons-vue';

// Props & Emits
const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'training-complete', result: any): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

// 步骤控制
const currentStep = ref(0);

// ==================== Step 1: 数据选择 ====================
const dataSource = ref<'existing' | 'upload'>('existing');
const selectedDataset = ref('');
const uploadRef = ref();

const existingDatasets = ref([
  { id: 'ds1', name: '微博情感数据集 v1', count: 50000, date: '2025-12-01' },
  { id: 'ds2', name: '产品评论数据集', count: 32000, date: '2025-11-15' },
  { id: 'ds3', name: '新闻评论数据集', count: 28000, date: '2025-10-20' },
  { id: 'ds4', name: '自定义标注数据', count: 5600, date: '2025-12-08' },
]);

const dataStats = reactive({
  total: 50000,
  positive: 22500,
  positiveRatio: 45,
  neutral: 15000,
  neutralRatio: 30,
  negative: 12500,
  negativeRatio: 25,
});

// ==================== Step 2: 训练参数 ====================
const trainConfig = reactive({
  trainRatio: 70,
  valRatio: 15,
  testRatio: 15,
  batchSize: 32,
  learningRate: 0.00002,
  epochs: 10,
  earlyStop: true,
  patience: 3,
  minDelta: 0.001,
  saveBest: true,
  saveCheckpoint: false,
  useGpu: true,
});

const epochMarks = { 1: '1', 10: '10', 20: '20', 30: '30', 50: '50' };

// 自动计算测试集比例
watch([() => trainConfig.trainRatio, () => trainConfig.valRatio], () => {
  trainConfig.testRatio = 100 - trainConfig.trainRatio - trainConfig.valRatio;
});

// ==================== Step 3: 训练监控 ====================
type TrainingStatus = 'idle' | 'training' | 'paused' | 'completed' | 'stopped';
const trainingStatus = ref<TrainingStatus>('idle');
const isTraining = computed(() => trainingStatus.value === 'training' || trainingStatus.value === 'paused');

const chartType = ref<'loss' | 'accuracy'>('loss');
const currentEpoch = ref(0);
const currentBatch = ref(0);
const totalBatches = ref(100);
const currentLoss = ref(0);
const currentAccuracy = ref(0);
const bestAccuracy = ref(0);
const elapsedTime = ref(0);
const remainingTime = ref(0);
const gpuUsage = ref(0);
const memoryUsage = ref(0);
const overallProgress = ref(0);

const progressColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#67c23a', percentage: 100 },
];

// 训练曲线数据
const lossData = reactive({ train: [] as number[], val: [] as number[] });
const accuracyData = reactive({ train: [] as number[], val: [] as number[] });

// 训练日志
const trainingLogs = ref<{ time: string; level: string; message: string }[]>([]);
const logScrollbar = ref();

// 图表实例
let trainingCurveChart: echarts.ECharts | null = null;
let dataDistributionChart: echarts.ECharts | null = null;
let trainingTimer: number | null = null;
let timeTimer: number | null = null;

// ==================== 方法 ====================
function handleFileChange(file: any) {
  if (file) {
    addLog('info', `已选择文件: ${file.name}`);
    // 模拟解析文件
    setTimeout(() => {
      dataStats.total = Math.floor(Math.random() * 30000 + 10000);
      dataStats.positive = Math.floor(dataStats.total * 0.4);
      dataStats.neutral = Math.floor(dataStats.total * 0.35);
      dataStats.negative = dataStats.total - dataStats.positive - dataStats.neutral;
      dataStats.positiveRatio = Math.round(dataStats.positive / dataStats.total * 100);
      dataStats.neutralRatio = Math.round(dataStats.neutral / dataStats.total * 100);
      dataStats.negativeRatio = Math.round(dataStats.negative / dataStats.total * 100);
      updateDataDistributionChart();
      addLog('info', `文件解析完成，共 ${dataStats.total} 条数据`);
    }, 500);
  }
}

function initDataDistributionChart() {
  const dom = document.getElementById('data-distribution-chart');
  if (!dom) return;

  dataDistributionChart = echarts.init(dom);
  updateDataDistributionChart();
}

function updateDataDistributionChart() {
  if (!dataDistributionChart) return;

  dataDistributionChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: dataStats.positive, name: '正面', itemStyle: { color: '#67c23a' } },
        { value: dataStats.neutral, name: '中性', itemStyle: { color: '#909399' } },
        { value: dataStats.negative, name: '负面', itemStyle: { color: '#f56c6c' } },
      ],
      label: { formatter: '{b}: {d}%' },
    }],
  });
}

function initTrainingCurveChart() {
  const dom = document.getElementById('training-curve');
  if (!dom) return;

  trainingCurveChart = echarts.init(dom);
  updateTrainingCurveChart();
}

function updateTrainingCurveChart() {
  if (!trainingCurveChart) return;

  const data = chartType.value === 'loss' ? lossData : accuracyData;
  const yAxisName = chartType.value === 'loss' ? '损失值' : '准确率 (%)';

  trainingCurveChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['训练集', '验证集'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', name: 'Epoch', data: data.train.map((_, i) => i + 1) },
    yAxis: { type: 'value', name: yAxisName },
    series: [
      { name: '训练集', type: 'line', smooth: true, data: data.train, itemStyle: { color: '#409eff' } },
      { name: '验证集', type: 'line', smooth: true, data: data.val, itemStyle: { color: '#67c23a' } },
    ],
  });
}

function addLog(level: string, message: string) {
  const now = new Date();
  const time = now.toLocaleTimeString('zh-CN', { hour12: false });
  trainingLogs.value.push({ time, level, message });
  
  nextTick(() => {
    logScrollbar.value?.setScrollTop(999999);
  });
}

function clearLogs() {
  trainingLogs.value = [];
}

function startTraining() {
  trainingStatus.value = 'training';
  currentEpoch.value = 0;
  currentBatch.value = 0;
  lossData.train = [];
  lossData.val = [];
  accuracyData.train = [];
  accuracyData.val = [];
  elapsedTime.value = 0;
  bestAccuracy.value = 0;
  
  addLog('info', '开始训练...');
  addLog('info', `训练参数: Batch Size=${trainConfig.batchSize}, LR=${trainConfig.learningRate}, Epochs=${trainConfig.epochs}`);
  
  // 模拟训练过程
  simulateTraining();
  
  // 计时器
  timeTimer = window.setInterval(() => {
    if (trainingStatus.value === 'training') {
      elapsedTime.value++;
      const progress = (currentEpoch.value + currentBatch.value / totalBatches.value) / trainConfig.epochs;
      if (progress > 0) {
        remainingTime.value = Math.floor(elapsedTime.value / progress * (1 - progress));
      }
    }
  }, 1000);
}

function simulateTraining() {
  trainingTimer = window.setInterval(() => {
    if (trainingStatus.value !== 'training') return;

    currentBatch.value++;
    
    // 更新资源使用
    gpuUsage.value = Math.min(95, 60 + Math.random() * 30);
    memoryUsage.value = Math.min(90, 50 + Math.random() * 25);
    
    // 模拟损失下降
    currentLoss.value = Math.max(0.1, 2 - currentEpoch.value * 0.15 - currentBatch.value * 0.001 + Math.random() * 0.1);
    
    if (currentBatch.value >= totalBatches.value) {
      currentBatch.value = 0;
      currentEpoch.value++;
      
      // 记录每轮数据
      const trainLoss = Math.max(0.1, 2 - currentEpoch.value * 0.18 + Math.random() * 0.05);
      const valLoss = Math.max(0.15, 2 - currentEpoch.value * 0.15 + Math.random() * 0.08);
      const trainAcc = Math.min(98, 50 + currentEpoch.value * 5 + Math.random() * 3);
      const valAcc = Math.min(95, 48 + currentEpoch.value * 4.5 + Math.random() * 2);
      
      lossData.train.push(Number(trainLoss.toFixed(4)));
      lossData.val.push(Number(valLoss.toFixed(4)));
      accuracyData.train.push(Number(trainAcc.toFixed(2)));
      accuracyData.val.push(Number(valAcc.toFixed(2)));
      
      currentAccuracy.value = valAcc;
      if (valAcc > bestAccuracy.value) {
        bestAccuracy.value = valAcc;
        addLog('success', `Epoch ${currentEpoch.value}: 新的最佳准确率 ${valAcc.toFixed(2)}%`);
      } else {
        addLog('info', `Epoch ${currentEpoch.value}: Loss=${trainLoss.toFixed(4)}, Val Acc=${valAcc.toFixed(2)}%`);
      }
      
      updateTrainingCurveChart();
      
      // 检查是否完成
      if (currentEpoch.value >= trainConfig.epochs) {
        completeTraining();
      }
    }
    
    // 更新总进度
    overallProgress.value = Math.round((currentEpoch.value + currentBatch.value / totalBatches.value) / trainConfig.epochs * 100);
  }, 100);
}

function pauseTraining() {
  trainingStatus.value = 'paused';
  addLog('warn', '训练已暂停');
}

function resumeTraining() {
  trainingStatus.value = 'training';
  addLog('info', '训练已继续');
}

function stopTraining() {
  ElMessageBox.confirm('确定要停止训练吗？当前进度将丢失。', '确认停止', { type: 'warning' })
    .then(() => {
      trainingStatus.value = 'stopped';
      clearTimers();
      addLog('error', '训练已停止');
    })
    .catch(() => {});
}

function completeTraining() {
  trainingStatus.value = 'completed';
  clearTimers();
  addLog('success', `训练完成！最佳准确率: ${bestAccuracy.value.toFixed(2)}%`);
  ElMessage.success('模型训练完成！');
  
  emit('training-complete', {
    bestAccuracy: bestAccuracy.value,
    epochs: currentEpoch.value,
    elapsedTime: elapsedTime.value,
  });
}

function clearTimers() {
  if (trainingTimer) {
    clearInterval(trainingTimer);
    trainingTimer = null;
  }
  if (timeTimer) {
    clearInterval(timeTimer);
    timeTimer = null;
  }
}

function saveModel() {
  ElMessage.success('模型已保存');
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}

function nextStep() {
  if (currentStep.value === 0) {
    if (dataSource.value === 'existing' && !selectedDataset.value) {
      ElMessage.warning('请选择数据集');
      return;
    }
    currentStep.value++;
  } else if (currentStep.value === 1) {
    currentStep.value++;
    nextTick(() => {
      initTrainingCurveChart();
    });
  }
}

function handleClose() {
  if (isTraining.value) {
    ElMessage.warning('训练进行中，请先停止训练');
    return;
  }
  clearTimers();
  visible.value = false;
}

function formatTime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function getStatusType(status: TrainingStatus) {
  const map: Record<TrainingStatus, string> = {
    idle: 'info',
    training: 'primary',
    paused: 'warning',
    completed: 'success',
    stopped: 'danger',
  };
  return map[status];
}

function getStatusText(status: TrainingStatus) {
  const map: Record<TrainingStatus, string> = {
    idle: '待开始',
    training: '训练中',
    paused: '已暂停',
    completed: '已完成',
    stopped: '已停止',
  };
  return map[status];
}

function getUsageColor(usage: number) {
  if (usage < 60) return '#67c23a';
  if (usage < 80) return '#e6a23c';
  return '#f56c6c';
}

// 监听图表类型切换
watch(chartType, () => {
  updateTrainingCurveChart();
});

// 监听步骤切换
watch(currentStep, (step) => {
  nextTick(() => {
    if (step === 0) {
      initDataDistributionChart();
    } else if (step === 2) {
      initTrainingCurveChart();
    }
  });
});

// 监听对话框打开
watch(visible, (val) => {
  if (val) {
    currentStep.value = 0;
    trainingStatus.value = 'idle';
    nextTick(() => {
      initDataDistributionChart();
    });
  }
});

// 清理
onUnmounted(() => {
  clearTimers();
  trainingCurveChart?.dispose();
  dataDistributionChart?.dispose();
});
</script>

<style scoped>
.step-content {
  min-height: 400px;
  padding: 20px 0;
}

/* 数据集选项 */
.dataset-option {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.dataset-info {
  color: #909399;
  font-size: 12px;
}

/* 数据预览 */
.data-preview {
  display: flex;
  gap: 20px;
  align-items: center;
}
.data-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.data-stats .stat-item {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  min-width: 180px;
}
.data-stats .stat-item.positive { border-left: 3px solid #67c23a; }
.data-stats .stat-item.neutral { border-left: 3px solid #909399; }
.data-stats .stat-item.negative { border-left: 3px solid #f56c6c; }
.stat-label { color: #606266; font-size: 13px; }
.stat-value { font-weight: bold; color: #303133; }

/* 数据集划分 */
.split-config {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
}
.split-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.split-label {
  font-size: 13px;
  color: #606266;
}
.split-unit {
  font-size: 13px;
  color: #909399;
}
.split-bar {
  display: flex;
  height: 24px;
  border-radius: 4px;
  overflow: hidden;
}
.split-train {
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.split-val {
  background: #67c23a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.split-test {
  background: #e6a23c;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

/* 早停配置 */
.early-stop-config {
  margin-top: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}
.config-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

/* 监控卡片 */
.monitor-card {
  margin-bottom: 15px;
}
.monitor-card :deep(.el-card__header) {
  padding: 10px 15px;
  background: #f5f7fa;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 状态面板 */
.status-content {
  padding: 10px 0;
}
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}
.status-label {
  font-size: 13px;
  color: #606266;
}
.status-value {
  font-weight: 500;
  color: #303133;
}
.status-value.highlight {
  color: #67c23a;
  font-size: 16px;
}

/* 资源使用 */
.resource-usage {
  margin-top: 10px;
}
.resource-item {
  margin-bottom: 15px;
}
.resource-label {
  font-size: 12px;
  color: #909399;
  display: block;
  margin-bottom: 5px;
}

/* 训练日志 */
.training-logs {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  padding: 10px;
  background: #1e1e1e;
  border-radius: 4px;
  min-height: 130px;
}
.log-line {
  padding: 2px 0;
}
.log-time {
  color: #6a9955;
  margin-right: 10px;
}
.log-info .log-message { color: #d4d4d4; }
.log-success .log-message { color: #67c23a; }
.log-warn .log-message { color: #e6a23c; }
.log-error .log-message { color: #f56c6c; }

/* 底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: space-between;
}
.footer-left, .footer-right {
  display: flex;
  gap: 10px;
}
</style>
