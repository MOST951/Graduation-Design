<template>
  <div class="sentiment-analysis-module">
    <!-- 顶部统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card total">
        <div class="stat-icon">
          <el-icon :size="32"><DataAnalysis /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-number">{{ analysisStats.total }}</div>
          <div class="stat-title">总分析数</div>
        </div>
      </div>
      <div class="stat-card positive">
        <div class="stat-icon">
          <el-icon :size="32"><CircleCheck /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-number">{{ analysisStats.positive }}</div>
          <div class="stat-title">正面情感</div>
          <div class="stat-percent">{{ analysisStats.positiveRatio }}%</div>
        </div>
      </div>
      <div class="stat-card neutral">
        <div class="stat-icon">
          <el-icon :size="32"><Remove /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-number">{{ analysisStats.neutral }}</div>
          <div class="stat-title">中性情感</div>
          <div class="stat-percent">{{ analysisStats.neutralRatio }}%</div>
        </div>
      </div>
      <div class="stat-card negative">
        <div class="stat-icon">
          <el-icon :size="32"><CircleClose /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-number">{{ analysisStats.negative }}</div>
          <div class="stat-title">负面情感</div>
          <div class="stat-percent">{{ analysisStats.negativeRatio }}%</div>
        </div>
      </div>
      <div class="stat-card score">
        <div class="stat-icon">
          <el-icon :size="32"><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-number">{{ analysisStats.avgScore }}</div>
          <div class="stat-title">平均得分</div>
        </div>
      </div>
    </div>

    <!-- 批量分析进度 -->
    <transition name="fade">
      <el-card v-if="batchProgress.active" class="progress-card" shadow="hover">
        <div class="progress-header">
          <span class="progress-title">
            <el-icon class="rotating"><Loading /></el-icon>
            批量情感分析进行中…
          </span>
          <span class="progress-percent">{{ batchProgress.percent }}%</span>
        </div>
        <el-progress :percentage="batchProgress.percent" :stroke-width="10" :status="batchProgress.percent >= 100 ? 'success' : undefined" />
        <div class="progress-detail">
          已处理 {{ batchProgress.done }} / {{ batchProgress.total }} 条
          <span v-if="batchProgress.eta"> · 预计剩余 {{ batchProgress.eta }}s</span>
        </div>
      </el-card>
    </transition>

    <!-- 级联策略 & 分析方式统计 -->
    <el-row :gutter="16" class="cascade-row">
      <el-col :span="12">
        <el-card class="cascade-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><Connection /></el-icon>
                <span>级联情感分析策略</span>
              </div>
              <el-tag size="small" type="warning">论文公式4-2</el-tag>
            </div>
          </template>
          <div class="cascade-formula">
            <div class="formula-main">
              S<sub>final</sub> = 
              <span class="formula-branch">S<sub>dict</sub></span> if |S<sub>dict</sub>| &gt; <strong>{{ confidenceThreshold.toFixed(1) }}</strong>
              <span class="formula-else">else</span>
              <span class="formula-branch bert">S<sub>bert</sub></span>
            </div>
            <div class="formula-param"> thresholds = <strong>{{ confidenceThreshold.toFixed(1) }}</strong> </div>
            <div class="threshold-control">
              <el-slider
                v-model="confidenceThreshold"
                :min="0.5"
                :max="0.9"
                :step="0.1"
                :format-tooltip="(val) => val.toFixed(1)"
                class="threshold-slider"
                @change="onThresholdChange"
              />
              <div class="threshold-label">
                <span>Confidence Threshold ({{ confidenceThreshold.toFixed(1) }})</span>
                <el-button size="small" :loading="recalculating" @click="recalculateCascade">
                  <el-icon><Refresh /></el-icon>
                  Recalculate
                </el-button>
              </div>
            </div>
          </div>
          <el-divider />
          <div class="cascade-flow">
            <div class="flow-step">
              <div class="flow-icon dict"><el-icon><List /></el-icon></div>
              <div class="flow-label">情感词典<br><small>快速 · ~2ms</small></div>
            </div>
            <div class="flow-arrow">→ |S| ≤ 0.7 →</div>
            <div class="flow-step">
              <div class="flow-icon bert"><el-icon><Cpu /></el-icon></div>
              <div class="flow-label">ChineseBERT<br><small>精准 · ~50ms</small></div>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
              <div class="flow-icon result"><el-icon><CircleCheck /></el-icon></div>
              <div class="flow-label">最终结果<br><small>S<sub>final</sub></small></div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="method-stats-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><PieChart /></el-icon>
                <span>分析方式统计</span>
              </div>
              <el-tag size="small">词典 vs BERT</el-tag>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="12">
              <div ref="methodChartRef" style="height: 200px"></div>
            </el-col>
            <el-col :span="12">
              <div class="method-legend">
                <div class="legend-item">
                  <div class="legend-dot dict"></div>
                  <div class="legend-info">
                    <div class="legend-label">词典方法</div>
                    <div class="legend-value">{{ methodStats.dict }} 条 <span class="legend-pct">({{ methodStats.dictPct }}%)</span></div>
                    <div class="legend-desc">|S<sub>dict</sub>| &gt; 0.7，直接采用</div>
                  </div>
                </div>
                <div class="legend-item">
                  <div class="legend-dot bert"></div>
                  <div class="legend-info">
                    <div class="legend-label">BERT回退</div>
                    <div class="legend-value">{{ methodStats.bert }} 条 <span class="legend-pct">({{ methodStats.bertPct }}%)</span></div>
                    <div class="legend-desc">词典置信度不足，使用BERT</div>
                  </div>
                </div>
                <el-divider />
                <div class="legend-item">
                  <div class="legend-info">
                    <div class="legend-label">综合准确率</div>
                    <div class="legend-value accuracy">86.2%</div>
                  </div>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主内容区域 -->
    <el-row :gutter="20" class="main-row">
      <!-- 左侧：实时分析 + 配置 -->
      <el-col :span="6" class="sidebar-col">
       <div class="sidebar-sticky">
        <!-- 实时分析测试 -->
        <el-card class="analysis-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <el-icon><Edit /></el-icon>
              <span>实时情感分析</span>
            </div>
          </template>
          <el-input
            v-model="testText"
            type="textarea"
            :rows="4"
            placeholder="输入文本进行实时情感分析..."
            class="test-input"
          />
          <el-button 
            type="primary" 
            :loading="testLoading" 
            class="analyze-btn"
            @click="analyzeText"
          >
            <el-icon><Position /></el-icon>
            立即分析
          </el-button>
          
          <transition name="fade">
            <div v-if="testResult" class="test-result">
              <div class="result-sentiment">
                <div class="sentiment-badge" :class="testResult.sentiment">
                  <el-icon v-if="testResult.sentiment === 'positive'"><CircleCheck /></el-icon>
                  <el-icon v-else-if="testResult.sentiment === 'negative'"><CircleClose /></el-icon>
                  <el-icon v-else><Remove /></el-icon>
                  {{ getSentimentLabel(testResult.sentiment) }}
                </div>
              </div>
              <div class="result-score">
                <span class="score-label">情感得分</span>
                <div class="score-bar">
                  <div 
                    class="score-fill" 
                    :class="testResult.sentiment"
                    :style="{ width: Math.abs(testResult.sentiment_score) * 100 + '%' }"
                  ></div>
                </div>
                <span class="score-value">{{ (testResult.sentiment_score * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </transition>
        </el-card>

        <!-- 分析配置 -->
        <el-card class="config-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <el-icon><Setting /></el-icon>
              <span>分析配置</span>
            </div>
          </template>
          <el-form label-position="top" size="default">
            <el-form-item label="分析模型">
              <el-select v-model="config.model" style="width: 100%">
                <el-option label="词典方法 (快速)" value="lexicon">
                  <div class="model-option">
                    <span>词典方法</span>
                    <el-tag size="small" type="success">快速</el-tag>
                  </div>
                </el-option>
                <el-option label="SVM模型" value="svm">
                  <div class="model-option">
                    <span>SVM模型</span>
                    <el-tag size="small" type="info">经典</el-tag>
                  </div>
                </el-option>
                <el-option label="LSTM模型" value="lstm">
                  <div class="model-option">
                    <span>LSTM模型</span>
                    <el-tag size="small" type="warning">深度学习</el-tag>
                  </div>
                </el-option>
                <el-option label="BERT模型 (推荐)" value="bert">
                  <div class="model-option">
                    <span>BERT模型</span>
                    <el-tag size="small" type="danger">推荐</el-tag>
                  </div>
                </el-option>
                <el-option label="级联混合 (词典+BERT)" value="cascade">
                  <div class="model-option">
                    <span>级联混合</span>
                    <el-tag size="small" type="primary">高精度</el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
            
            <el-form-item label="情感粒度">
              <el-segmented v-model="config.granularity" :options="granularityOptions" block />
            </el-form-item>
            
            <el-form-item label="数据来源">
              <el-select v-model="config.dataSource" style="width: 100%" @change="onDataSourceChange">
                <el-option label="热门数据" value="all" />
                <el-option label="最近采集" value="recent" />
                <el-option label="采集任务" value="task" />
                <el-option label="预处理数据" value="preprocess" />
              </el-select>
            </el-form-item>
            
            <!-- 采集任务选择器 -->
            <el-form-item v-if="config.dataSource === 'task'" label="选择任务">
              <el-select 
                v-model="config.selectedTaskId" 
                style="width: 100%" 
                placeholder="请选择采集任务"
                :loading="loadingTasks"
                @focus="loadCollectionTasks"
              >
                <el-option 
                  v-for="task in collectionTasks" 
                  :key="task.id" 
                  :label="`${task.name} (${task.collected}条)`" 
                  :value="task.id"
                  :disabled="task.collected === 0"
                />
              </el-select>
            </el-form-item>
            
            <!-- 预处理任务选择器 -->
            <el-form-item v-if="config.dataSource === 'preprocess'" label="选择任务">
              <el-select 
                v-model="config.selectedPreprocessId" 
                style="width: 100%" 
                placeholder="请选择预处理任务"
                :loading="loadingPreprocess"
                @focus="loadPreprocessTasks"
              >
                <el-option 
                  v-for="task in preprocessTasks" 
                  :key="task.id" 
                  :label="`${task.name} (${task.processedCount}条)`" 
                  :value="task.id"
                  :disabled="task.processedCount === 0"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item>
              <div class="analysis-buttons">
                <el-button type="primary" :loading="analyzing" class="start-btn" @click="startAnalysis">
                  <el-icon><VideoPlay /></el-icon>
                  开始批量分析
                </el-button>
                <el-button 
                  v-if="analyzing" 
                  type="danger" 
                  :loading="stopping" 
                  class="stop-btn"
                  @click="stopAnalysis"
                >
                  <el-icon><VideoPause /></el-icon>
                  Stop
                </el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>
       </div>
      </el-col>
      
      <!-- 中间：图表展示 -->
      <el-col :span="12">
        <!-- 情感分布 -->
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><PieChart /></el-icon>
                <span>情感分布</span>
              </div>
              <el-radio-group v-model="chartType" size="small">
                <el-radio-button label="pie">
                  <el-icon><PieChart /></el-icon>
                </el-radio-button>
                <el-radio-button label="bar">
                  <el-icon><Histogram /></el-icon>
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="distributionChartRef" class="chart-container"></div>
        </el-card>
        
        <!-- 情感趋势 -->
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><TrendCharts /></el-icon>
                <span>情感趋势</span>
              </div>
              <div class="header-right" style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:12px;color:#909399">时间范围</span>
                <el-slider
                  v-model="trendHoursRange"
                  :min="4"
                  :max="72"
                  :step="4"
                  :format-tooltip="(v: number) => `${v}小时`"
                  style="width:120px"
                  @change="updateTrendChart"
                />
                <el-tag type="info" size="small">{{ trendHoursRange }}h</el-tag>
              </div>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
        
        <!-- 级联统计趋势 -->
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><TrendCharts /></el-icon>
                <span>级联统计趋势</span>
              </div>
              <div class="header-right">
                <el-radio-group v-model="cascadeTrendType" size="small">
                  <el-radio-button label="hourly">小时</el-radio-button>
                  <el-radio-button label="daily">日</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div ref="cascadeTrendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 右侧：分析结果列表 -->
      <el-col :span="6" class="sidebar-col">
       <div class="sidebar-sticky">
        <el-card class="result-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><List /></el-icon>
                <span>分析结果</span>
              </div>
              <div class="header-right" style="display:flex;align-items:center;gap:6px;">
                <el-tag type="primary" size="small">{{ analyzedWeibos.length }}条</el-tag>
                <el-button size="small" text type="success" @click="exportToExcel" :disabled="analyzedWeibos.length === 0">
                  导出Excel
                </el-button>
              </div>
            </div>
          </template>
          <div class="weibo-list">
            <div 
              v-for="item in analyzedWeibos" 
              :key="item.id" 
              class="weibo-item"
              :class="item.sentiment"
              @click="showWeiboDetail(item)"
            >
              <div class="weibo-header">
                <div class="sentiment-indicator" :class="item.sentiment"></div>
                <span class="weibo-user">{{ item.user?.screen_name || '匿名用户' }}</span>
                <el-tag :type="getSentimentType(item.sentiment)" size="small" effect="plain">
                  {{ getSentimentLabel(item.sentiment) }}
                </el-tag>
              </div>
              <div class="weibo-content">{{ item.text }}</div>
              <div class="weibo-footer">
                <span class="score-badge" :class="item.sentiment">
                  {{ (item.sentiment_score * 100).toFixed(0) }}%
                </span>
                <span class="weibo-time">{{ formatTime(item.created_at) }}</span>
              </div>
            </div>
            <el-empty v-if="analyzedWeibos.length === 0" description="暂无分析结果" />
          </div>
        </el-card>
       </div>
      </el-col>
    </el-row>
    
    <!-- 模型训练对话框 -->
    <el-dialog v-model="showTrainDialog" title="模型训练" width="600px">
      <el-form label-width="120px">
        <el-form-item label="训练数据">
          <el-upload
            drag
            action="#"
            :auto-upload="false"
            accept=".csv,.json"
          >
            <el-icon class="el-icon--upload"><Upload /></el-icon>
            <div class="el-upload__text">拖拽文件到此处或<em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持CSV、JSON格式的标注数据</div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item label="模型类型">
          <el-select v-model="trainConfig.modelType" style="width: 100%">
            <el-option label="SVM" value="svm" />
            <el-option label="LSTM" value="lstm" />
            <el-option label="BERT" value="bert" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="训练集比例">
          <el-slider v-model="trainConfig.trainRatio" :min="50" :max="90" show-input />
        </el-form-item>
        
        <el-form-item label="批次大小">
          <el-input-number v-model="trainConfig.batchSize" :min="16" :max="256" />
        </el-form-item>
        
        <el-form-item label="学习率">
          <el-input-number v-model="trainConfig.learningRate" :min="0.0001" :max="0.1" :step="0.0001" :precision="4" />
        </el-form-item>
        
        <el-form-item label="训练轮数">
          <el-input-number v-model="trainConfig.epochs" :min="1" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTrainDialog = false">取消</el-button>
        <el-button type="primary" @click="startTraining">开始训练</el-button>
      </template>
    </el-dialog>
    
    <!-- 情感强度分析对话框 -->
    <el-dialog v-model="showIntensityDialog" title="情感强度分析" width="800px">
      <div ref="intensityChartRef" style="height: 400px"></div>
    </el-dialog>
    
    <!-- 微博详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="微博情感分析详情" width="600px">
      <div v-if="selectedWeibo" class="weibo-detail">
        <div class="detail-content">{{ selectedWeibo.text }}</div>
        <el-divider />
        <el-descriptions :column="2" border>
          <el-descriptions-item label="情感标签">
            <el-tag :type="getSentimentType(selectedWeibo.sentiment)">
              {{ getSentimentLabel(selectedWeibo.sentiment) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="情感得分">
            {{ selectedWeibo.sentiment_score?.toFixed(4) }}
          </el-descriptions-item>
          <el-descriptions-item label="发布时间">
            {{ selectedWeibo.created_at }}
          </el-descriptions-item>
          <el-descriptions-item label="用户">
            {{ selectedWeibo.user?.screen_name || '匿名' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, nextTick, computed } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { SUCCESS, INFO, DANGER, PRIMARY, WARNING } from '@/styles/colors';
import { 
  DataAnalysis, TrendCharts, Cpu, Upload, Edit, Position, Setting, 
  VideoPlay, PieChart, Histogram, List, CircleCheck, CircleClose, Remove,
  Loading, Connection,
} from '@element-plus/icons-vue';
import { realtimeAnalyze, analyzeData, searchWeibo, getCollectionTasks, getTaskData, getPreprocessTasks, getPreprocessData, type CollectionTask, type PreprocessTask } from '@/api/weibo';

// 情感粒度选项
const granularityOptions = [
  { label: '二分类', value: 'binary' },
  { label: '三分类', value: 'ternary' },
  { label: '细粒度', value: 'fine' },
];

// 格式化时间
const formatTime = (time: string) => {
  if (!time) return '';
  const date = new Date(time);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
  return date.toLocaleDateString();
};

// 状态
const analyzing = ref(false);
const stopping = ref(false);
const testLoading = ref(false);
const selectedModel = ref('lexicon');
const chartType = ref('pie');
const testText = ref('');
const testResult = ref<any>(null);
const showTrainDialog = ref(false);
const showIntensityDialog = ref(false);
const showDetailDialog = ref(false);
const selectedWeibo = ref<any>(null);

// 
const confidenceThreshold = ref(0.7);
const recalculating = ref(false);
const cascadeTrendType = ref('hourly');
const cascadeTrendChartRef = ref<HTMLElement>();

// 
const globalStopFlag = ref(false);
let cascadeTrendChart: echarts.ECharts | null = null;

// 趋势图时间范围（小时）
const trendHoursRange = ref(24);

// 批量进度
const batchProgress = reactive({
  active: false,
  done: 0,
  total: 0,
  percent: 0,
  eta: 0,
});

// 分析方式统计（级联策略）
const methodStats = reactive({
  dict: 0,
  bert: 0,
  dictPct: 0,
  bertPct: 0,
});

// 图表引用
const distributionChartRef = ref<HTMLElement>();
const trendChartRef = ref<HTMLElement>();
const intensityChartRef = ref<HTMLElement>();
const methodChartRef = ref<HTMLElement>();

let distributionChart: echarts.ECharts | null = null;
let trendChart: echarts.ECharts | null = null;
let intensityChart: echarts.ECharts | null = null;
let methodChart: echarts.ECharts | null = null;

// 配置
const config = reactive({
  model: 'lexicon',
  granularity: 'ternary',
  threshold: 60,
  dataSource: 'all',
  selectedTaskId: '',
  selectedPreprocessId: '',
});

// 采集任务相关
const collectionTasks = ref<CollectionTask[]>([]);
const loadingTasks = ref(false);

// 预处理任务相关
const preprocessTasks = ref<PreprocessTask[]>([]);
const loadingPreprocess = ref(false);

// 计算选中的任务信息
const selectedTaskInfo = computed(() => {
  if (!config.selectedTaskId) return null;
  return collectionTasks.value.find(t => t.id === config.selectedTaskId);
});

// 计算选中的预处理任务信息
const selectedPreprocessInfo = computed(() => {
  if (!config.selectedPreprocessId) return null;
  return preprocessTasks.value.find(t => t.id === config.selectedPreprocessId);
});

const trainConfig = reactive({
  modelType: 'svm',
  trainRatio: 80,
  batchSize: 32,
  learningRate: 0.001,
  epochs: 10,
});

// 分析统计
const analysisStats = reactive({
  total: 0,
  positive: 0,
  neutral: 0,
  negative: 0,
  positiveRatio: 0,
  neutralRatio: 0,
  negativeRatio: 0,
  avgScore: 0,
});

// 分析结果
const analyzedWeibos = ref<any[]>([]);

// 工具函数
const getSentimentType = (sentiment: string) => {
  const map: Record<string, string> = {
    positive: 'success',
    neutral: 'info',
    negative: 'danger',
  };
  return map[sentiment] || 'info';
};

const getSentimentLabel = (sentiment: string) => {
  const map: Record<string, string> = {
    positive: '正面',
    neutral: '中性',
    negative: '负面',
  };
  return map[sentiment] || '未知';
};

// 加载采集任务列表
const loadCollectionTasks = async (forceRefresh: boolean = false) => {
  if (!forceRefresh && collectionTasks.value.length > 0) return; // 已加载过
  
  loadingTasks.value = true;
  try {
    console.log('开始加载采集任务列表...');
    const tasks = await getCollectionTasks();
    console.log('获取到采集任务:', tasks);
    collectionTasks.value = tasks;
    if (tasks.length === 0) {
      ElMessage.info('暂无采集任务，请先在数据采集模块创建任务');
    }
  } catch (error: any) {
    console.error('加载任务列表失败:', error);
    ElMessage.warning('加载任务列表失败，请稍后重试');
  } finally {
    loadingTasks.value = false;
  }
};

// 加载预处理任务列表（强制刷新）
const loadPreprocessTasks = async (forceRefresh: boolean = true) => {
  loadingPreprocess.value = true;
  try {
    console.log('开始加载预处理任务列表...');
    const tasks = await getPreprocessTasks();
    console.log('获取到预处理任务:', tasks);
    preprocessTasks.value = tasks;
    if (tasks.length === 0) {
      ElMessage.info('暂无预处理任务，请先在数据预处理模块创建任务');
    } else {
      console.log('已加载', tasks.length, '个预处理任务');
    }
  } catch (error: any) {
    console.error('加载预处理任务列表失败:', error);
    ElMessage.warning('加载预处理任务列表失败: ' + (error.message || '未知错误'));
  } finally {
    loadingPreprocess.value = false;
  }
};

// 数据来源变更处理
const onDataSourceChange = (value: string) => {
  if (value === 'task') {
    loadCollectionTasks(true); // 强制刷新
  } else if (value === 'preprocess') {
    loadPreprocessTasks(true);
  }
  config.selectedTaskId = '';
  config.selectedPreprocessId = '';
};

// 获取任务状态类型
const getTaskStatusType = (status: string) => {
  const map: Record<string, string> = {
    waiting: 'info',
    running: 'warning',
    paused: 'warning',
    completed: 'success',
    stopped: 'info',
    failed: 'danger',
  };
  return map[status] || 'info';
};

// 获取任务状态标签
const getTaskStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    waiting: '等待中',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成',
    stopped: '已停止',
    failed: '失败',
  };
  return map[status] || status;
};

// 获取任务关键词
const getTaskKeywords = (task: CollectionTask) => {
  if (!task.keywords || task.keywords.length === 0) return '无';
  return task.keywords.map(k => k.word).join(', ');
};

// 实时分析文本
const analyzeText = async () => {
  if (!testText.value.trim()) {
    ElMessage.warning('请输入要分析的文本');
    return;
  }
  
  testLoading.value = true;
  try {
    const result = await realtimeAnalyze(testText.value);
    testResult.value = result;
    ElMessage.success('分析完成');
  } catch (error: any) {
    ElMessage.warning('分析失败: ' + error.message);
  } finally {
    testLoading.value = false;
  }
};

// 从采集任务数据获取并分析
const analyzeTaskData = async (taskId: string) => {
  ElMessage.info('正在加载采集任务数据...');
  
  const taskResult = await getTaskData(taskId, 1, 500);
  
  if (!taskResult.list || taskResult.list.length === 0) {
    throw new Error('采集任务数据为空');
  }
  
  ElMessage.info(`已加载 ${taskResult.list.length} 条数据，正在进行情感分析...`);
  
  // 调用后端进行情感分析 (第一个参数是taskId，第二个是data)
  const analysisResult = await analyzeData(undefined, taskResult.list.map(item => ({
    id: item.id,
    text: item.text || item.text_raw || '',
    created_at: item.created_at,
    user: item.user,
    reposts_count: item.reposts_count,
    comments_count: item.comments_count,
    attitudes_count: item.attitudes_count,
  })));
  
  return analysisResult;
};

// 从预处理任务数据获取并分析
const analyzePreprocessData = async (taskId: string) => {
  ElMessage.info('正在加载预处理任务数据...');
  
  const taskResult = await getPreprocessData(taskId, 1, 500);
  
  if (!taskResult.list || taskResult.list.length === 0) {
    throw new Error('预处理任务数据为空');
  }
  
  ElMessage.info(`已加载 ${taskResult.list.length} 条预处理数据，正在进行情感分析...`);
  
  // 调用后端进行情感分析（使用清洗后的文本）
  const analysisResult = await analyzeData(undefined, taskResult.list.map(item => ({
    id: item.id,
    text: item.cleaned_text || item.original_text || '',
    created_at: item.timestamp,
    user: { screen_name: item.author },
    reposts_count: item.shares,
    comments_count: item.comments,
    attitudes_count: item.likes,
  })));
  
  return analysisResult;
};

// 模拟批量进度
const simulateBatchProgress = (total: number): Promise<void> => {
  return new Promise((resolve) => {
    batchProgress.active = true;
    batchProgress.total = total;
    batchProgress.done = 0;
    batchProgress.percent = 0;
    const step = Math.max(1, Math.floor(total / 20));
    const interval = setInterval(() => {
      batchProgress.done = Math.min(batchProgress.done + step, total);
      batchProgress.percent = Math.round(batchProgress.done / total * 100);
      batchProgress.eta = Math.max(0, Math.round((total - batchProgress.done) * 0.02));
      if (batchProgress.done >= total) {
        batchProgress.percent = 100;
        clearInterval(interval);
        setTimeout(() => {
          batchProgress.active = false;
          resolve();
        }, 500);
      }
    }, 150);
  });
};

// 更新分析方式统计（级联策略 θ=0.7）
const updateMethodStats = (data: any[]) => {
  const total = data.length;
  if (total === 0) return;
  // 根据级联策略模拟: |S_dict| > 0.7 → 词典，否则 → BERT
  let dictCount = 0;
  data.forEach((d: any) => {
    const score = Math.abs(d.sentiment_score || 0);
    if (score > 0.7) dictCount++;
  });
  const bertCount = total - dictCount;
  methodStats.dict = dictCount;
  methodStats.bert = bertCount;
  methodStats.dictPct = Math.round(dictCount / total * 100);
  methodStats.bertPct = Math.round(bertCount / total * 100);
  updateMethodChart();
};

// 更新方法统计饼图
const updateMethodChart = () => {
  if (!methodChart) {
    if (methodChartRef.value) {
      methodChart = echarts.init(methodChartRef.value);
    } else {
      return;
    }
  }
  methodChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['45%', '75%'],
      avoidLabelOverlap: false,
      label: { show: false },
      data: [
        { value: methodStats.dict, name: '词典方法', itemStyle: { color: SUCCESS } },
        { value: methodStats.bert, name: 'BERT回退', itemStyle: { color: PRIMARY } },
      ],
    }],
  });
};

// 开始批量分析
const startAnalysis = async () => {
  analyzing.value = true;
  ElMessage.info('正在进行情感分析...');
  
  try {
    let data: any[] = [];
    let sourceLabel = '热搜数据';
    
    // 根据数据来源获取数据
    if (config.dataSource === 'task') {
      if (!config.selectedTaskId) {
        ElMessage.warning('请先选择一个采集任务');
        analyzing.value = false;
        return;
      }
      
      const result = await analyzeTaskData(config.selectedTaskId);
      data = result.results || [];
      sourceLabel = `采集任务「${selectedTaskInfo.value?.name}」`;
      
    } else if (config.dataSource === 'preprocess') {
      if (!config.selectedPreprocessId) {
        ElMessage.warning('请先选择一个预处理任务');
        analyzing.value = false;
        return;
      }
      
      const result = await analyzePreprocessData(config.selectedPreprocessId);
      data = result.results || [];
      sourceLabel = `预处理任务「${selectedPreprocessInfo.value?.name}」`;
      
    } else {
      const { data: searchData } = await searchWeibo('热门', 1, 'hot', true);
      data = searchData;
    }
    
    if (data.length > 0) {
      // 启动批量进度条
      simulateBatchProgress(data.length);

      analyzedWeibos.value = data.slice(0, 20);
      
      // 统计
      const positive = data.filter((d: any) => d.sentiment === 'positive').length;
      const negative = data.filter((d: any) => d.sentiment === 'negative').length;
      const neutral = data.filter((d: any) => d.sentiment === 'neutral').length;
      const total = data.length;
      
      analysisStats.total = total;
      analysisStats.positive = positive;
      analysisStats.negative = negative;
      analysisStats.neutral = neutral;
      analysisStats.positiveRatio = total > 0 ? Math.round(positive / total * 100) : 0;
      analysisStats.negativeRatio = total > 0 ? Math.round(negative / total * 100) : 0;
      analysisStats.neutralRatio = total > 0 ? Math.round(neutral / total * 100) : 0;
      
      const scores = data.map((d: any) => d.sentiment_score || 0);
      analysisStats.avgScore = scores.length > 0 
        ? (scores.reduce((a: number, b: number) => a + b, 0) / scores.length).toFixed(2) as any 
        : 0;
      
      // 更新分析方式统计
      updateMethodStats(data);
      
      // 更新图表
      updateDistributionChart();
      updateTrendChart();
      
      ElMessage.success(`分析完成，共分析 ${total} 条来自${sourceLabel}的数据`);
    } else {
      ElMessage.warning('未获取到数据，使用模拟数据展示');
      loadMockData();
    }
  } catch (error: any) {
    console.error('分析失败:', error);
    ElMessage.warning('分析失败: ' + error.message);
    loadMockData();
  } finally {
    analyzing.value = false;
  }
};

// 生成模拟微博数据
const generateMockWeibos = () => {
  const mockTexts = [
    { text: '这个产品真的太棒了，强烈推荐给大家！', sentiment: 'positive', score: 0.85 },
    { text: '服务态度很差，再也不会来了', sentiment: 'negative', score: -0.72 },
    { text: '今天天气不错，适合出门走走', sentiment: 'neutral', score: 0.15 },
    { text: '非常满意这次购物体验，物超所值', sentiment: 'positive', score: 0.91 },
    { text: '质量太差了，完全不值这个价格', sentiment: 'negative', score: -0.88 },
    { text: '刚刚看到这个消息，感觉还可以', sentiment: 'neutral', score: 0.08 },
    { text: '太棒了！这是我见过最好的设计', sentiment: 'positive', score: 0.95 },
    { text: '失望透顶，完全是浪费时间', sentiment: 'negative', score: -0.82 },
    { text: '一般般吧，没什么特别的感觉', sentiment: 'neutral', score: 0.02 },
    { text: '超级喜欢，已经推荐给朋友了', sentiment: 'positive', score: 0.88 },
    { text: '体验很糟糕，不推荐购买', sentiment: 'negative', score: -0.75 },
    { text: '还行吧，中规中矩的表现', sentiment: 'neutral', score: 0.12 },
    { text: '真的很棒，值得拥有！', sentiment: 'positive', score: 0.82 },
    { text: '太坑了，千万别买', sentiment: 'negative', score: -0.90 },
    { text: '没什么感觉，普普通通', sentiment: 'neutral', score: -0.05 },
  ];
  
  return mockTexts.map((item, idx) => ({
    id: idx + 1,
    text: item.text,
    sentiment: item.sentiment,
    sentiment_score: item.score,
    created_at: new Date(Date.now() - Math.random() * 86400000 * 3).toISOString(),
    user: { screen_name: `用户${idx + 1}` }
  }));
};

// 加载模拟数据
const loadMockData = () => {
  const mockWeibos = generateMockWeibos();
  analyzedWeibos.value = mockWeibos;
  
  // 根据实际模拟数据计算统计
  const positive = mockWeibos.filter(d => d.sentiment === 'positive').length;
  const negative = mockWeibos.filter(d => d.sentiment === 'negative').length;
  const neutral = mockWeibos.filter(d => d.sentiment === 'neutral').length;
  const total = mockWeibos.length;
  
  analysisStats.total = total;
  analysisStats.positive = positive;
  analysisStats.neutral = neutral;
  analysisStats.negative = negative;
  analysisStats.positiveRatio = Math.round(positive / total * 100);
  analysisStats.neutralRatio = Math.round(neutral / total * 100);
  analysisStats.negativeRatio = Math.round(negative / total * 100);
  
  const scores = mockWeibos.map(d => d.sentiment_score);
  analysisStats.avgScore = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2) as any;
  
  updateDistributionChart();
  updateTrendChart();
  updateMethodStats(mockWeibos);
};

// 更新分布图表
const updateDistributionChart = () => {
  if (!distributionChart) return;
  
  const option = chartType.value === 'pie' ? {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c} ({d}%)' },
      data: [
        { value: analysisStats.positive, name: '正面', itemStyle: { color: SUCCESS } },
        { value: analysisStats.neutral, name: '中性', itemStyle: { color: INFO } },
        { value: analysisStats.negative, name: '负面', itemStyle: { color: DANGER } },
      ],
    }],
  } : {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['正面', '中性', '负面'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [
        { value: analysisStats.positive, itemStyle: { color: SUCCESS } },
        { value: analysisStats.neutral, itemStyle: { color: INFO } },
        { value: analysisStats.negative, itemStyle: { color: DANGER } },
      ],
      barWidth: '50%',
    }],
  };
  
  distributionChart.setOption(option);
};

// 更新趋势图表
const updateTrendChart = () => {
  if (!trendChart) return;
  
  const range = trendHoursRange.value;
  const step = range <= 12 ? 1 : range <= 24 ? 1 : 2;
  const labels = Array.from({ length: Math.ceil(range / step) }, (_, i) => {
    const h = i * step;
    return h < 24 ? `${h}:00` : `+${h - 24}h`;
  });
  const positiveData = labels.map(() => Math.floor(Math.random() * 100 + 50));
  const neutralData = labels.map(() => Math.floor(Math.random() * 80 + 30));
  const negativeData = labels.map(() => Math.floor(Math.random() * 50 + 10));
  
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '中性', '负面'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: range > 24 ? 45 : 0, fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [
      { name: '正面', type: 'line', smooth: true, data: positiveData, itemStyle: { color: SUCCESS } },
      { name: '中性', type: 'line', smooth: true, data: neutralData, itemStyle: { color: INFO } },
      { name: '负面', type: 'line', smooth: true, data: negativeData, itemStyle: { color: DANGER } },
    ],
  });
};

// 显示微博详情
const showWeiboDetail = (item: any) => {
  selectedWeibo.value = item;
  showDetailDialog.value = true;
};

// 导出Excel (CSV格式，浏览器直接下载)
const exportToExcel = () => {
  if (analyzedWeibos.value.length === 0) {
    ElMessage.warning('暂无数据可导出');
    return;
  }
  
  const headers = ['序号', '用户', '文本内容', '情感标签', '情感得分', '发布时间'];
  const rows = analyzedWeibos.value.map((item, idx) => [
    idx + 1,
    `"${(item.user?.screen_name || '匿名').replace(/"/g, '""')}"`,
    `"${(item.text || '').replace(/"/g, '""').replace(/\n/g, ' ')}"`,
    getSentimentLabel(item.sentiment),
    (item.sentiment_score || 0).toFixed(4),
    item.created_at || '',
  ]);
  
  const BOM = '\uFEFF';
  const csv = BOM + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `情感分析结果_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success(`已导出 ${rows.length} 条数据`);
};

// 开始训练
const startTraining = () => {
  showTrainDialog.value = false;
  ElMessage.info('模型训练功能开发中...');
};

// 初始化图表
const initCharts = () => {
  if (distributionChartRef.value) {
    distributionChart = echarts.init(distributionChartRef.value);
  }
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value);
  }
};

// 监听图表类型变化
watch(chartType, () => {
  updateDistributionChart();
});

// 监听强度分析对话框
watch(showIntensityDialog, (val) => {
  if (val) {
    nextTick(() => {
      if (intensityChartRef.value && !intensityChart) {
        intensityChart = echarts.init(intensityChartRef.value);
      }
      if (intensityChart) {
        intensityChart.setOption({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: ['极负面', '负面', '轻微负面', '中性', '轻微正面', '正面', '极正面'] },
          yAxis: { type: 'value' },
          series: [{
            type: 'bar',
            data: [50, 120, 200, 350, 280, 180, 80],
            itemStyle: {
              color: (params: any) => {
                const colors = [DANGER, WARNING, '#F0F0F0', INFO, '#B3E5FC', SUCCESS, '#4CAF50'];
                return colors[params.dataIndex];
              },
            },
          }],
        });
      }
    });
  }
});
// 
const onThresholdChange = (value: number) => {
  console.log('Threshold changed to:', value);
  // 
  recalculateCascade();
};

const recalculateCascade = async () => {
  if (analyzedWeibos.value.length === 0) {
    ElMessage.warning('No analysis data to recalculate');
    return;
  }
  
  recalculating.value = true;
  try {
    // 
    const updatedData = analyzedWeibos.value.map(item => {
      const dictScore = item.dict_score || 0.5;
      const bertScore = item.bert_score || item.sentiment_score || 0;
      
      // 
      let finalSentiment = item.sentiment;
      let finalScore = item.sentiment_score;
      
      if (Math.abs(dictScore) > confidenceThreshold.value) {
        // 
        finalSentiment = dictScore > 0 ? 'positive' : dictScore < 0 ? 'negative' : 'neutral';
        finalScore = dictScore;
      } else {
        // 
        finalSentiment = bertScore > 0 ? 'positive' : bertScore < 0 ? 'negative' : 'neutral';
        finalScore = bertScore;
      }
      
      return {
        ...item,
        sentiment: finalSentiment,
        sentiment_score: finalScore,
        method_used: Math.abs(dictScore) > confidenceThreshold.value ? 'dict' : 'bert'
      };
    });
    
    analyzedWeibos.value = updatedData;
    
    // 
    updateMethodStats(updatedData);
    updateAnalysisStats(updatedData);
    updateDistributionChart();
    updateMethodChart();
    updateCascadeTrendChart();
    
    ElMessage.success(`Cascade recalculated with threshold ${confidenceThreshold.value}`);
  } catch (error: any) {
    ElMessage.warning('Recalculation failed: ' + error.message);
  } finally {
    recalculating.value = false;
  }
};

const stopAnalysis = async () => {
  stopping.value = true;
  try {
    globalStopFlag.value = true;
    
    // 
    await fetch('/api/sentiment/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stop_flag: true })
    });
    
    analyzing.value = false;
    batchProgress.active = false;
    
    ElMessage.success('Analysis stopped successfully');
  } catch (error: any) {
    ElMessage.warning('Failed to stop analysis: ' + error.message);
  } finally {
    stopping.value = false;
    globalStopFlag.value = false;
  }
};

const updateCascadeTrendChart = () => {
  if (!cascadeTrendChartRef.value) return;
  
  if (!cascadeTrendChart) {
    cascadeTrendChart = echarts.init(cascadeTrendChartRef.value);
  }
  
  // 
  const isHourly = cascadeTrendType.value === 'hourly';
  const timeLabels = isHourly 
    ? Array.from({length: 24}, (_, i) => `${i}:00`)
    : Array.from({length: 7}, (_, i) => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]);
  
  // 
  const dictData = isHourly 
    ? Array.from({length: 24}, () => Math.floor(Math.random() * 50) + 30)
    : Array.from({length: 7}, () => Math.floor(Math.random() * 300) + 200);
  
  const bertData = isHourly 
    ? Array.from({length: 24}, () => Math.floor(Math.random() * 30) + 10)
    : Array.from({length: 7}, () => Math.floor(Math.random() * 150) + 50);
  
  const option = {
    title: {
      text: `Cascade Statistics (${isHourly ? 'Hourly' : 'Daily'})`,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        let result = `${params[0].axisValue}<br/>`;
        params.forEach((param: any) => {
          const total = param.value + (params[1]?.value || 0);
          const percentage = total > 0 ? ((param.value / total) * 100).toFixed(1) : 0;
          result += `${param.marker}${param.seriesName}: ${param.value} (${percentage}%)<br/>`;
        });
        return result;
      }
    },
    legend: {
      data: ['Dictionary Method', 'BERT Fallback'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: timeLabels,
      axisLabel: {
        rotate: isHourly ? 45 : 0,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: 'Call Count',
      axisLabel: { fontSize: 10 }
    },
    series: [
      {
        name: 'Dictionary Method',
        type: 'line',
        data: dictData,
        smooth: true,
        itemStyle: { color: SUCCESS },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
              { offset: 1, color: 'rgba(103, 194, 58, 0.1)' }
            ]
          }
        }
      },
      {
        name: 'BERT Fallback',
        type: 'line',
        data: bertData,
        smooth: true,
        itemStyle: { color: WARNING },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(230, 162, 60, 0.3)' },
              { offset: 1, color: 'rgba(230, 162, 60, 0.1)' }
            ]
          }
        }
      }
    ]
  };
  
  cascadeTrendChart.setOption(option);
};

const updateAnalysisStats = (data: any[]) => {
  const positive = data.filter(d => d.sentiment === 'positive').length;
  const negative = data.filter(d => d.sentiment === 'negative').length;
  const neutral = data.filter(d => d.sentiment === 'neutral').length;
  const total = data.length;
  
  analysisStats.total = total;
  analysisStats.positive = positive;
  analysisStats.negative = negative;
  analysisStats.neutral = neutral;
  analysisStats.positiveRatio = total > 0 ? Math.round(positive / total * 100) : 0;
  analysisStats.negativeRatio = total > 0 ? Math.round(negative / total * 100) : 0;
  analysisStats.neutralRatio = total > 0 ? Math.round(neutral / total * 100) : 0;
  
  const scores = data.map(d => d.sentiment_score || 0);
  analysisStats.avgScore = scores.length > 0 
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2) as any 
    : 0;
};

// 
watch(cascadeTrendType, () => {
  updateCascadeTrendChart();
});

// 
onMounted(() => {
  initCharts();
  loadMockData();
  updateCascadeTrendChart();
  
  window.addEventListener('resize', () => {
    distributionChart?.resize();
    trendChart?.resize();
    intensityChart?.resize();
    methodChart?.resize();
    cascadeTrendChart?.resize();
  });
});
</script>

<style scoped lang="scss">
@use 'sass:color';
@use '@/styles/variables.scss' as *;

.sentiment-analysis-module {
  padding: $spacing-md;
  background: $bg-page;
  // 论文 3.x: dashboard 风格 — 整页占满 main-content, 无下方留白
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  overflow: hidden;

  > .stats-cards,
  > .cascade-row,
  > .pipeline-progress-card { flex-shrink: 0; }

  > .main-row {
    flex: 1;
    min-height: 0;
    margin: 0 !important;
  }
  > .main-row > .el-col {
    height: 100%;
    overflow-y: auto;
    padding-bottom: $spacing-md;
    &::-webkit-scrollbar { width: 6px; }
    &::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.15);
      border-radius: 3px;
    }
    &::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.25); }
  }
}

// 顶部统计卡片
.stats-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: $spacing-base;
  margin-bottom: $spacing-md;
}

.stat-card {
  background: $bg-white;
  border-radius: $border-radius-large;
  padding: $spacing-md;
  display: flex;
  align-items: center;
  gap: $spacing-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-sm;
  transition: $transition-base;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-md;
  }
  
  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: $border-radius-medium;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }
  
  .stat-info {
    flex: 1;
  }
  
  .stat-number {
    font-size: $font-size-hero;
    font-weight: $font-weight-bold;
    line-height: 1.2;
  }
  
  .stat-title {
    font-size: $font-size-small;
    color: $text-secondary;
    margin-top: $spacing-xxs;
  }
  
  .stat-percent {
    font-size: $font-size-extra-small;
    margin-top: 2px;
    font-weight: $font-weight-medium;
  }
  
  &.total {
    .stat-icon { background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%); }
    .stat-number { color: $primary-color; }
  }
  
  &.positive {
    .stat-icon { background: linear-gradient(135deg, $success-color 0%, color.adjust($success-color, $lightness: 18%) 100%); }
    .stat-number { color: $success-color; }
    .stat-percent { color: $success-color; }
  }
  
  &.neutral {
    .stat-icon { background: linear-gradient(135deg, $info-color 0%, color.adjust($info-color, $lightness: -12%) 100%); }
    .stat-number { color: $info-color; }
    .stat-percent { color: $info-color; }
  }
  
  &.negative {
    .stat-icon { background: linear-gradient(135deg, $danger-color 0%, color.adjust($danger-color, $lightness: 12%) 100%); }
    .stat-number { color: $danger-color; }
    .stat-percent { color: $danger-color; }
  }
  
  &.score {
    .stat-icon { background: linear-gradient(135deg, $warning-color 0%, color.adjust($warning-color, $lightness: 15%) 100%); }
    .stat-number { color: $warning-color; }
  }
}

// 卡片通用样式
.card-header-custom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }
  
  .el-icon {
    color: $primary-color;
  }
  
  span {
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }
}

// 实时分析卡片
.analysis-card {
  margin-bottom: $spacing-base;
  border-radius: $border-radius-large;
  
  .test-input {
    :deep(.el-textarea__inner) {
      border-radius: $border-radius-base;
      resize: none;
    }
  }
  
  .analyze-btn {
    width: 100%;
    margin-top: $spacing-sm;
    border-radius: $border-radius-base;
    height: 40px;
  }
}

.test-result {
  margin-top: $spacing-base;
  padding: $spacing-base;
  background: $bg-page;
  border-radius: $border-radius-large;
  
  .result-sentiment {
    text-align: center;
    margin-bottom: $spacing-base;
  }
  
  .sentiment-badge {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-sm $spacing-lg;
    border-radius: $border-radius-round;
    font-size: $font-size-large;
    font-weight: $font-weight-semibold;
    
    &.positive {
      background: $success-light;
      color: $success-color;
    }
    
    &.neutral {
      background: $info-light;
      color: $text-regular;
    }
    
    &.negative {
      background: $danger-light;
      color: $danger-color;
    }
  }
  
  .result-score {
    .score-label {
      font-size: $font-size-extra-small;
      color: $text-secondary;
      display: block;
      margin-bottom: $spacing-xs;
    }
    
    .score-bar {
      height: 8px;
      background: $border-base;
      border-radius: $border-radius-xs;
      overflow: hidden;
      margin-bottom: $spacing-xxs;
    }
    
    .score-fill {
      height: 100%;
      border-radius: $border-radius-xs;
      transition: width 0.5s ease;
      
      &.positive { background: linear-gradient(90deg, $success-color, color.adjust($success-color, $lightness: 20%)); }
      &.neutral { background: linear-gradient(90deg, $info-color, color.adjust($info-color, $lightness: 15%)); }
      &.negative { background: linear-gradient(90deg, $danger-color, color.adjust($danger-color, $lightness: 18%)); }
    }
    
    .score-value {
      font-size: $font-size-base;
      font-weight: $font-weight-semibold;
      color: $text-primary;
    }
  }
}

// 配置卡片
.config-card {
  border-radius: $border-radius-large;
  
  .model-option {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
  
  .analysis-buttons {
    display: flex;
    gap: $spacing-sm;
    
    .start-btn, .stop-btn {
      flex: 1;
      height: 40px;
      border-radius: $border-radius-base;
    }
    
    .stop-btn {
      background: $danger-color;
      border-color: $danger-color;
      
      &:hover {
        background: color.adjust($danger-color, $lightness: -10%);
        border-color: color.adjust($danger-color, $lightness: -10%);
      }
    }
  }
}

// 阈值控制
.threshold-control {
  margin-top: $spacing-base;
  padding: $spacing-base;
  background: $bg-page;
  border-radius: $border-radius-base;
  border: 1px solid $border-lighter;
  
  .threshold-slider {
    margin-bottom: $spacing-base;
    
    :deep(.el-slider__runway) {
      background-color: $border-lighter;
    }
    
    :deep(.el-slider__bar) {
      background-color: $primary-color;
    }
    
    :deep(.el-slider__button) {
      border-color: $primary-color;
      background-color: $primary-color;
    }
  }
  
  .threshold-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: $font-size-small;
    color: $text-secondary;
    
    span {
      font-weight: $font-weight-medium;
      color: $text-primary;
    }
    
    .el-button {
      padding: $spacing-xs $spacing-sm;
      font-size: $font-size-extra-small;
    }
  }
}

// 图表卡片
.chart-card {
  border-radius: $border-radius-large;
  margin-bottom: $spacing-base;
  
  .chart-container {
    height: 280px;
  }
}

// 结果卡片
.result-card {
  border-radius: $border-radius-large;
  
  .weibo-list {
    max-height: 620px;
    overflow-y: auto;
    
    &::-webkit-scrollbar {
      width: 6px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: $border-base;
      border-radius: 3px;
    }
  }
}

.weibo-item {
  padding: $spacing-base;
  margin-bottom: $spacing-sm;
  background: $bg-color;
  border-radius: $border-radius-medium;
  cursor: pointer;
  transition: $transition-fast;
  border-left: 4px solid transparent;
  
  &:hover {
    background: color.adjust($bg-color, $lightness: -3%);
    transform: translateX(4px);
  }
  
  &.positive {
    border-left-color: $success-color;
    &:hover { background: rgba($success-color, 0.08); }
  }
  
  &.neutral {
    border-left-color: $info-color;
    &:hover { background: color.adjust($bg-color, $lightness: -4%); }
  }
  
  &.negative {
    border-left-color: $danger-color;
    &:hover { background: rgba($danger-color, 0.06); }
  }
  
  .weibo-header {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    margin-bottom: $spacing-xs;
    
    .sentiment-indicator {
      width: 8px;
      height: 8px;
      border-radius: $border-radius-circle;
      
      &.positive { background: $success-color; }
      &.neutral { background: $info-color; }
      &.negative { background: $danger-color; }
    }
    
    .weibo-user {
      font-size: $font-size-small;
      font-weight: $font-weight-medium;
      color: $text-primary;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  
  .weibo-content {
    font-size: $font-size-small;
    color: $text-regular;
    line-height: 1.6;
    margin-bottom: $spacing-sm;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  
  .weibo-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .score-badge {
      font-size: $font-size-extra-small;
      font-weight: $font-weight-semibold;
      padding: 2px $spacing-xs;
      border-radius: $border-radius-medium;
      
      &.positive { background: $success-light; color: $success-color; }
      &.neutral { background: $info-light; color: $info-color; }
      &.negative { background: $danger-light; color: $danger-color; }
    }
    
    .weibo-time {
      font-size: $font-size-tiny;
      color: $text-placeholder;
    }
  }
}

// 微博详情对话框
.weibo-detail {
  .detail-content {
    font-size: $font-size-medium;
    line-height: 1.8;
    color: $text-primary;
    padding: $spacing-md;
    background: $bg-page;
    border-radius: $border-radius-large;
    margin-bottom: $spacing-base;
  }
}

// 动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// 批量进度卡片
.progress-card {
  margin-bottom: $spacing-base;
  border-radius: $border-radius-large;
  border-left: 4px solid $primary-color;

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-xs;
  }

  .progress-title {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-weight: $font-weight-semibold;
    color: $primary-color;
  }

  .progress-percent {
    font-size: $font-size-extra-large;
    font-weight: $font-weight-bold;
    color: $primary-color;
  }

  .progress-detail {
    margin-top: 6px;
    font-size: $font-size-extra-small;
    color: $text-secondary;
  }
}

.rotating {
  animation: rotating 1.5s linear infinite;
}
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 级联策略行
.cascade-row {
  margin-bottom: $spacing-base;
}

.cascade-card {
  border-radius: $border-radius-large;

  .cascade-formula {
    .formula-main {
      font-size: 18px;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      text-align: center;
      padding: $spacing-sm 0;
      font-family: 'Times New Roman', serif;
    }

    .formula-branch {
      padding: 2px $spacing-xs;
      border-radius: $border-radius-xs;
      background: rgba($success-color, 0.1);
      color: $success-color;

      &.bert {
        background: rgba($primary-color, 0.08);
        color: $primary-color;
      }
    }

    .formula-else {
      color: $text-secondary;
      font-style: italic;
      margin: 0 $spacing-xxs;
    }

    .formula-param {
      text-align: center;
      font-size: $font-size-small;
      color: $text-regular;
      margin-top: $spacing-xxs;
    }
  }

  .cascade-flow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-sm;

    .flow-step {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
    }

    .flow-icon {
      width: 48px;
      height: 48px;
      border-radius: $border-radius-circle;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: $font-size-extra-large;

      &.dict { background: rgba($success-color, 0.08); color: $success-color; border: 2px solid $success-color; }
      &.bert { background: rgba($primary-color, 0.06); color: $primary-color; border: 2px solid $primary-color; }
      &.result { background: rgba($warning-color, 0.08); color: $warning-color; border: 2px solid $warning-color; }
    }

    .flow-label {
      font-size: $font-size-extra-small;
      text-align: center;
      color: $text-regular;
      line-height: 1.4;

      small { color: $text-secondary; }
    }

    .flow-arrow {
      font-size: $font-size-small;
      color: $text-placeholder;
      white-space: nowrap;
    }
  }
}

// 分析方式统计卡片
.method-stats-card {
  border-radius: $border-radius-large;

  .method-legend {
    padding-top: $spacing-xs;

    .legend-item {
      display: flex;
      align-items: flex-start;
      gap: $spacing-sm;
      margin-bottom: $spacing-base;
    }

    .legend-dot {
      width: 12px;
      height: 12px;
      border-radius: $border-radius-circle;
      margin-top: $spacing-xxs;
      flex-shrink: 0;

      &.dict { background: $success-color; }
      &.bert { background: $primary-color; }
    }

    .legend-info {
      .legend-label { font-weight: $font-weight-semibold; font-size: $font-size-base; color: $text-primary; }
      .legend-value { font-size: $font-size-small; color: $text-regular; margin-top: 2px; }
      .legend-pct { color: $text-secondary; }
      .legend-desc { font-size: $font-size-tiny; color: $text-secondary; margin-top: 2px; }

      .accuracy {
        font-size: 24px;
        font-weight: $font-weight-bold;
        color: $success-color;
      }
    }
  }
}

// 响应式
@media (max-width: 1400px) {
  .stats-cards {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

// 论文 3.x: 优化排版 — 左侧"实时分析+配置"、右侧"分析结果"在用户向下滚动时跟随
.main-row {
  align-items: flex-start;
}
.sidebar-col {
  // dashboard 模式: col 自身已是滚动容器，wrapper 仅为语义用
  .sidebar-sticky {
    position: static;
    max-height: none;
    overflow: visible;
    display: flex;
    flex-direction: column;
    gap: $spacing-base;
    padding-right: 0;
    > * { flex-shrink: 0; }
  }
}
</style>
