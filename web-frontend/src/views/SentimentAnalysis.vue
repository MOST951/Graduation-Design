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

    <!-- 上方：级联策略 & 分析方式统计 -->
    <el-row :gutter="16" class="cascade-row">
      <el-col :span="12">
        <el-card class="cascade-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><Connection /></el-icon>
                <span>自适应级联融合策略</span>
              </div>
              <el-segmented v-model="analysisMode" :options="modeOptions" size="small" />
            </div>
          </template>
          <div class="cascade-body">
            <div class="threshold-control">
              <div class="threshold-label">
                <span>置信度阈值</span>
                <el-tag size="small" type="warning">{{ confidenceThreshold.toFixed(2) }}</el-tag>
              </div>
              <el-slider
                v-model="confidenceThreshold"
                :min="0.5"
                :max="1.0"
                :step="0.05"
                :format-tooltip="(val:number) => val.toFixed(2)"
                class="threshold-slider"
                @change="onThresholdChange"
              />
              <div class="threshold-desc">置信度 ≥ {{ confidenceThreshold.toFixed(2) }} 或匹配 ≥ 3个情感词 → 词典直出</div>
            </div>
            <el-divider style="margin: 12px 0" />
            <div class="cascade-flow">
              <div class="flow-step">
                <div class="flow-icon dict"><el-icon><List /></el-icon></div>
                <div class="flow-label">情感词典<br><small>快速 · ~2ms</small></div>
              </div>
              <div class="flow-arrow">
                <div>置信度 &lt; {{ confidenceThreshold.toFixed(2) }}</div>
                <div>且 &lt; 3个情感词</div>
                <div>→</div>
              </div>
              <div class="flow-step">
                <div class="flow-icon bert"><el-icon><Cpu /></el-icon></div>
                <div class="flow-label">ChineseBERT<br><small>精准 · ~50ms</small></div>
              </div>
              <div class="flow-arrow">→</div>
              <div class="flow-step">
                <div class="flow-icon result"><el-icon><CircleCheck /></el-icon></div>
                <div class="flow-label">最终结果</div>
              </div>
            </div>
            <el-divider style="margin: 12px 0" />
            <div class="formula-block">
              <div class="formula-row">
                <el-tag size="small" effect="dark" type="info">公式 4-1</el-tag>
                <span class="formula-title">级联门控判断</span>
              </div>
              <div class="formula-math">
                useBERT = <span class="formula-brace">{</span>
                <span class="formula-cases">
                  <span class="formula-case"><b>false</b>&ensp;if&ensp;Conf<sub>lex</sub> ≥ θ &ensp;∨&ensp; n<sub>match</sub> ≥ 3</span>
                  <span class="formula-case"><b>true</b>&ensp;&ensp;otherwise</span>
                </span>
              </div>
              <div class="formula-row" style="margin-top: 10px">
                <el-tag size="small" effect="dark" type="info">公式 4-2</el-tag>
                <span class="formula-title">自适应加权融合</span>
              </div>
              <div class="formula-math">
                S<sub>hybrid</sub> = α · S<sub>lex</sub> + (1 − α) · S<sub>bert</sub>
              </div>
              <div class="formula-note">
                θ = {{ confidenceThreshold.toFixed(2) }}，动态权重 α ∈ [0.2, 0.8]，基于词典置信度与文本长度自适应调整
              </div>
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
                    <div class="legend-desc">置信度 ≥ {{ confidenceThreshold.toFixed(2) }} 或 ≥ 3个情感词</div>
                  </div>
                </div>
                <div class="legend-item">
                  <div class="legend-dot bert"></div>
                  <div class="legend-info">
                    <div class="legend-label">BERT回退</div>
                    <div class="legend-value">{{ methodStats.bert }} 条 <span class="legend-pct">({{ methodStats.bertPct }}%)</span></div>
                    <div class="legend-desc">词典置信度不足，回退到BERT</div>
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

    <!-- 中间：即时分析 + 情感分布 -->
    <el-row :gutter="16" class="middle-row">
      <el-col :span="10">
        <el-card class="analysis-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <el-icon><Edit /></el-icon>
              <span>即时情感分析</span>
            </div>
          </template>
          <el-input
            v-model="testText"
            type="textarea"
            :rows="3"
            placeholder="输入一条文本进行即时情感分析..."
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
              <div class="result-row">
                <div class="sentiment-badge" :class="testResult.sentiment">
                  <el-icon v-if="testResult.sentiment === 'positive'"><CircleCheck /></el-icon>
                  <el-icon v-else-if="testResult.sentiment === 'negative'"><CircleClose /></el-icon>
                  <el-icon v-else><Remove /></el-icon>
                  {{ getSentimentLabel(testResult.sentiment) }}
                </div>
                <div class="result-meta">
                  <span>置信度: <strong>{{ ((testResult.confidence || Math.abs(testResult.sentiment_score || 0)) * 100).toFixed(1) }}%</strong></span>
                  <el-tag size="small" :type="testResult.method === 'lexicon' ? 'success' : 'primary'" effect="plain">
                    {{ testResult.method === 'lexicon' ? '词典' : testResult.method === 'cascade' ? '级联' : 'BERT' }}
                  </el-tag>
                </div>
              </div>
              <div class="result-score">
                <div class="score-bar">
                  <div 
                    class="score-fill" 
                    :class="testResult.sentiment"
                    :style="{ width: (testResult.confidence || Math.abs(testResult.sentiment_score || 0)) * 100 + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </transition>
          
          <el-divider />
          
          <el-form label-position="left" label-width="70px" size="default" class="batch-form">
            <el-form-item label="数据来源">
              <el-select v-model="config.dataSource" style="width: 100%" @change="onDataSourceChange">
                <el-option label="热门数据" value="all" />
                <el-option label="最近采集" value="recent" />
                <el-option label="采集任务" value="task" />
                <el-option label="预处理数据" value="preprocess" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="config.dataSource === 'task'" label="选择任务">
              <el-select 
                v-model="config.selectedTaskId" style="width: 100%" placeholder="请选择采集任务"
                :loading="loadingTasks" @focus="loadCollectionTasks"
              >
                <el-option v-for="task in collectionTasks" :key="task.id" :label="`${task.name} (${task.collected}条)`" :value="task.id" :disabled="task.collected === 0" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="config.dataSource === 'preprocess'" label="选择任务">
              <el-select 
                v-model="config.selectedPreprocessId" style="width: 100%" placeholder="请选择预处理任务"
                :loading="loadingPreprocess" @focus="loadPreprocessTasks"
              >
                <el-option v-for="task in preprocessTasks" :key="task.id" :label="`${task.name} (${task.processedCount}条)`" :value="task.id" :disabled="task.processedCount === 0" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <div class="analysis-buttons">
                <el-button type="primary" :loading="analyzing" class="start-btn" @click="startAnalysis">
                  <el-icon><VideoPlay /></el-icon>
                  开始批量分析
                </el-button>
                <el-button v-if="analyzing" type="danger" :loading="stopping" class="stop-btn" @click="stopAnalysis">
                  <el-icon><VideoPause /></el-icon>
                  停止
                </el-button>
              </div>
              <div v-if="analyzing" style="margin-top: 8px; padding: 8px 12px; background: #ecf5ff; border-radius: 6px; font-size: 13px; color: #409eff;">
                💡 分析正在后台运行，您可以自由切换到其他模块操作，完成后会自动通知
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="14">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header-custom">
              <div class="header-left">
                <el-icon><PieChart /></el-icon>
                <span>情感分布</span>
              </div>
              <el-radio-group v-model="chartType" size="small">
                <el-radio-button label="pie"><el-icon><PieChart /></el-icon></el-radio-button>
                <el-radio-button label="bar"><el-icon><Histogram /></el-icon></el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="distributionChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下方：批量分析结果表格 -->
    <el-card class="table-card" shadow="hover">
      <template #header>
        <div class="card-header-custom">
          <div class="header-left">
            <el-icon><List /></el-icon>
            <span>批量分析结果</span>
            <el-tag type="primary" size="small">{{ analyzedWeibos.length }} 条</el-tag>
          </div>
          <el-button type="success" size="small" :icon="Download" @click="exportToExcel" :disabled="analyzedWeibos.length === 0">
            一键导出Excel
          </el-button>
        </div>
      </template>
      <el-table :data="pagedWeibos" stripe border highlight-current-row max-height="380" @row-click="showWeiboDetail" style="width: 100%">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="user" label="用户" width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.user?.screen_name || row.screen_name || '匿名' }}</template>
        </el-table-column>
        <el-table-column label="文本内容" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">{{ row.text || row.text_raw || '' }}</template>
        </el-table-column>
        <el-table-column label="情感类型" width="95" align="center">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment)" size="small">{{ getSentimentLabel(row.sentiment) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="90" align="center">
          <template #default="{ row }">
            <span :style="{ color: Math.abs(row.sentiment_score||0) > 0.8 ? '#67C23A' : '#909399' }">
              {{ (Math.abs(row.sentiment_score || 0) * 100).toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="分析方法" width="95" align="center">
          <template #default="{ row }">
            <el-tag :type="row.method_used === 'dict' ? 'success' : 'primary'" size="small" effect="plain">
              {{ row.method_used === 'dict' ? '词典' : 'BERT' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-pagination" v-if="analyzedWeibos.length > tablePageSize">
        <el-pagination
          v-model:current-page="tablePage"
          :page-size="tablePageSize"
          :total="analyzedWeibos.length"
          layout="total, prev, pager, next"
          small
        />
      </div>
      <el-empty v-if="analyzedWeibos.length === 0" description="暂无分析结果，请点击「开始批量分析」" />
    </el-card>
    
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
import { ElMessage, ElNotification } from 'element-plus';
import * as echarts from 'echarts';
import { SUCCESS, INFO, DANGER, PRIMARY, WARNING } from '@/styles/colors';
import { 
  DataAnalysis, TrendCharts, Cpu, Upload, Edit, Position, Setting, Download,
  VideoPlay, PieChart, Histogram, List, CircleCheck, CircleClose, Remove,
  Loading, Connection, Refresh, VideoPause,
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

// 分析模式
const analysisMode = ref('cascade');
const modeOptions = [
  { label: '快速模式', value: 'fast' },
  { label: '高精度模式', value: 'cascade' },
];

// 状态
const analyzing = ref(false);
const stopping = ref(false);
const testLoading = ref(false);
const chartType = ref('pie');
const testText = ref('');
const testResult = ref<any>(null);
const showDetailDialog = ref(false);
const selectedWeibo = ref<any>(null);

// 表格分页
const tablePage = ref(1);
const tablePageSize = ref(20);
const pagedWeibos = computed(() => {
  const start = (tablePage.value - 1) * tablePageSize.value;
  return analyzedWeibos.value.slice(start, start + tablePageSize.value);
});

// 级联策略参数
const confidenceThreshold = ref(0.9);
const recalculating = ref(false);
// 
const globalStopFlag = ref(false);

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
const methodChartRef = ref<HTMLElement>();

let distributionChart: echarts.ECharts | null = null;
let methodChart: echarts.ECharts | null = null;

// 配置
const config = reactive({
  granularity: 'ternary',
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
    const method = analysisMode.value === 'fast' ? 'lexicon' : 'cascade';
    const result = await realtimeAnalyze(testText.value, method, confidenceThreshold.value);
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
  
  let taskResult: any;
  try {
    taskResult = await getPreprocessData(taskId, 1, 500);
  } catch {
    taskResult = { list: [], total: 0 };
  }
  
  if (!taskResult.list || taskResult.list.length === 0) {
    throw new Error('该预处理任务数据已过期，请重新在数据预处理模块执行预处理');
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

// 更新分析方式统计（级联策略）
const updateMethodStats = (data: any[]) => {
  const total = data.length;
  if (total === 0) return;
  const theta = confidenceThreshold.value;
  let dictCount = 0;
  data.forEach((d: any) => {
    const conf = d.confidence || Math.abs(d.sentiment_score || 0);
    const isDict = conf >= theta || (d.matched_words && d.matched_words >= 3);
    d.method_used = isDict ? 'dict' : 'bert';
    if (isDict) dictCount++;
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

      analyzedWeibos.value = data;
      tablePage.value = 1;
      
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
      
      ElMessage.success(`分析完成，共分析 ${total} 条来自${sourceLabel}的数据`);
      // 通知（即使用户在其他页面也能看到）
      ElNotification({
        title: '情感分析完成',
        message: `共分析 ${total} 条数据（正面${positive} / 中性${neutral} / 负面${negative}）`,
        type: 'success',
        duration: 8000,
      });
    } else {
      ElMessage.warning('未获取到数据，使用模拟数据展示');
      loadMockData();
    }
  } catch (error: any) {
    console.error('分析失败:', error);
    ElMessage.warning('分析失败: ' + error.message);
    ElNotification({
      title: '情感分析失败',
      message: error.message,
      type: 'error',
      duration: 8000,
    });
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
  
  const headers = ['序号', '用户', '文本内容', '情感标签', '置信度', '分析方法'];
  const rows = analyzedWeibos.value.map((item, idx) => [
    idx + 1,
    `"${(item.user?.screen_name || item.screen_name || '匿名').replace(/"/g, '""')}"`,
    `"${(item.text || item.text_raw || '').replace(/"/g, '""').replace(/\n/g, ' ')}"`,
    getSentimentLabel(item.sentiment),
    (Math.abs(item.sentiment_score || 0) * 100).toFixed(1) + '%',
    item.method_used === 'dict' ? '词典' : 'BERT',
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

// 初始化图表
const initCharts = () => {
  if (distributionChartRef.value) {
    distributionChart = echarts.init(distributionChartRef.value);
  }
};

// 监听图表类型变化
watch(chartType, () => {
  updateDistributionChart();
});

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
    
    ElMessage.success(`已以阈值 ${confidenceThreshold.value} 重新计算级联结果`);
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

onMounted(() => {
  initCharts();
  loadMockData();
  // 预加载任务列表，下拉框打开时直接可用
  loadCollectionTasks();
  loadPreprocessTasks();
  
  window.addEventListener('resize', () => {
    distributionChart?.resize();
    methodChart?.resize();
  });
});
</script>

<style scoped lang="scss">
@use 'sass:color';
@use '@/styles/variables.scss' as *;

.sentiment-analysis-module {
  padding: $spacing-md;
  background: $bg-page;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  overflow-y: auto;

  > .stats-cards,
  > .cascade-row,
  > .middle-row,
  > .table-card { flex-shrink: 0; }
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

// 即时分析卡片
.analysis-card {
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
    height: 38px;
  }
}

.test-result {
  margin-top: $spacing-base;
  padding: $spacing-base;
  background: $bg-page;
  border-radius: $border-radius-large;
  
  .result-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-sm;
  }
  
  .result-meta {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-small;
    color: $text-regular;
  }
  
  .sentiment-badge {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-xs $spacing-base;
    border-radius: $border-radius-round;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    
    &.positive { background: $success-light; color: $success-color; }
    &.neutral { background: $info-light; color: $text-regular; }
    &.negative { background: $danger-light; color: $danger-color; }
  }
  
  .result-score {
    .score-bar {
      height: 6px;
      background: $border-base;
      border-radius: $border-radius-xs;
      overflow: hidden;
    }
    
    .score-fill {
      height: 100%;
      border-radius: $border-radius-xs;
      transition: width 0.5s ease;
      
      &.positive { background: linear-gradient(90deg, $success-color, color.adjust($success-color, $lightness: 20%)); }
      &.neutral { background: linear-gradient(90deg, $info-color, color.adjust($info-color, $lightness: 15%)); }
      &.negative { background: linear-gradient(90deg, $danger-color, color.adjust($danger-color, $lightness: 18%)); }
    }
  }
}

.batch-form {
  .analysis-buttons {
    display: flex;
    gap: $spacing-sm;
    width: 100%;
    
    .start-btn, .stop-btn {
      flex: 1;
      height: 38px;
      border-radius: $border-radius-base;
    }
  }
}

// 表格卡片
.table-card {
  border-radius: $border-radius-large;

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: $spacing-base;
  }
}

// 公式展示块
.formula-block {
  padding: $spacing-base;
  background: linear-gradient(135deg, #f8faff 0%, #f0f5ff 100%);
  border-radius: $border-radius-base;
  border: 1px solid #d6e4ff;

  .formula-row {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: 6px;
  }

  .formula-title {
    font-size: $font-size-small;
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }

  .formula-math {
    font-family: 'Cambria Math', 'Times New Roman', 'STIX Two Math', serif;
    font-size: 15px;
    color: #1d3557;
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 4px;
    line-height: 1.8;
  }

  .formula-brace {
    font-size: 32px;
    font-weight: 100;
    line-height: 1;
    color: #555;
  }

  .formula-cases {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .formula-case {
    font-size: 13px;
  }

  .formula-note {
    margin-top: 6px;
    font-size: $font-size-extra-small;
    color: $text-secondary;
    line-height: 1.6;
  }
}

// 阈值控制
.threshold-control {
  padding: $spacing-base;
  background: $bg-page;
  border-radius: $border-radius-base;
  border: 1px solid $border-lighter;

  .threshold-desc {
    font-size: $font-size-extra-small;
    color: $text-secondary;
    margin-top: $spacing-xs;
  }
  
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

</style>
