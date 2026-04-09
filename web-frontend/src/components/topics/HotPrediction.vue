<template>
  <div class="hot-prediction">
    <!-- 控制面板 -->
    <div class="prediction-controls">
      <el-row :gutter="20">
        <!-- 模型选择 -->
        <el-col :span="6">
          <div class="control-section">
            <div class="section-title">预测模型</div>
            <el-select v-model="predictionModel" style="width: 100%;">
              <el-option label="时间序列模型 (ARIMA)" value="arima">
                <div class="model-option">
                  <el-icon><Clock /></el-icon>
                  <span>时间序列模型 (ARIMA)</span>
                </div>
              </el-option>
              <el-option label="社交网络模型" value="social">
                <div class="model-option">
                  <el-icon><Connection /></el-icon>
                  <span>社交网络模型</span>
                </div>
              </el-option>
              <el-option label="深度学习模型 (LSTM)" value="lstm">
                <div class="model-option">
                  <el-icon><Cpu /></el-icon>
                  <span>深度学习模型 (LSTM)</span>
                </div>
              </el-option>
              <el-option label="集成模型" value="ensemble">
                <div class="model-option">
                  <el-icon><Grid /></el-icon>
                  <span>集成模型 (推荐)</span>
                </div>
              </el-option>
            </el-select>
            <div class="model-desc">{{ modelDescription }}</div>
          </div>
        </el-col>

        <!-- 预测参数 -->
        <el-col :span="10">
          <div class="control-section">
            <div class="section-title">预测参数</div>
            <el-row :gutter="15">
              <el-col :span="8">
                <div class="param-item">
                  <span class="param-label">预测时间范围</span>
                  <el-select v-model="predictionRange" size="small" style="width: 100%;">
                    <el-option label="未来1小时" value="1h" />
                    <el-option label="未来6小时" value="6h" />
                    <el-option label="未来24小时" value="24h" />
                    <el-option label="未来7天" value="7d" />
                  </el-select>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="param-item">
                  <span class="param-label">置信度阈值</span>
                  <el-slider
                    v-model="confidenceThreshold"
                    :min="50"
                    :max="99"
                    :format-tooltip="(val: number) => val + '%'"
                    size="small"
                  />
                </div>
              </el-col>
              <el-col :span="8">
                <div class="param-item">
                  <span class="param-label">预测数量</span>
                  <el-input-number v-model="predictionCount" :min="5" :max="50" size="small" style="width: 100%;" />
                </div>
              </el-col>
            </el-row>
          </div>
        </el-col>

        <!-- 特征选择 -->
        <el-col :span="5">
          <div class="control-section">
            <div class="section-title">特征选择</div>
            <el-select
              v-model="selectedFeatures"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择预测特征"
              size="small"
              style="width: 100%;"
            >
              <el-option label="历史热度" value="history_heat" />
              <el-option label="传播速度" value="spread_speed" />
              <el-option label="用户参与度" value="engagement" />
              <el-option label="KOL影响" value="kol_influence" />
              <el-option label="时间因素" value="time_factor" />
              <el-option label="情感倾向" value="sentiment" />
              <el-option label="话题关联" value="topic_relation" />
            </el-select>
          </div>
        </el-col>

        <!-- 操作按钮 -->
        <el-col :span="3">
          <div class="control-section action-section">
            <el-button type="primary" :loading="isPredicting" @click="runPrediction">
              <el-icon><TrendCharts /></el-icon>
              开始预测
            </el-button>
            <el-button @click="showAlertSettings">
              <el-icon><Bell /></el-icon>
              预警设置
            </el-button>
          </div>
        </el-col>
      </el-row>
    </div>

    <el-row :gutter="20">
      <!-- 预测结果 -->
      <el-col :span="16">
        <!-- 预测热点列表 -->
        <el-card shadow="never" class="prediction-card">
          <template #header>
            <div class="card-header">
              <span>预测热点话题</span>
              <div class="header-actions">
                <el-tag type="info" size="small">预测时间: {{ predictionTime }}</el-tag>
                <el-button text size="small" @click="exportPredictions">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>

          <el-table :data="predictedTopics" v-loading="isPredicting" max-height="400">
            <el-table-column label="排名" width="70">
              <template #default="{ $index }">
                <span :class="['rank-badge', `rank-${$index + 1}`]">{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="topic" label="话题" min-width="200">
              <template #default="{ row }">
                <div class="topic-cell">
                  <span class="topic-name">{{ row.topic }}</span>
                  <el-tag v-if="row.isNew" type="success" size="small" effect="dark">新</el-tag>
                  <el-tag v-if="row.isRising" type="danger" size="small" effect="dark">爆</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="预测热度" width="150">
              <template #default="{ row }">
                <div class="heat-cell">
                  <span class="heat-value">{{ formatHeat(row.predictedHeat) }}</span>
                  <span :class="['heat-change', row.heatChange > 0 ? 'up' : 'down']">
                    {{ row.heatChange > 0 ? '↑' : '↓' }}{{ Math.abs(row.heatChange) }}%
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="置信度" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.confidence"
                  :stroke-width="8"
                  :color="getConfidenceColor(row.confidence)"
                />
              </template>
            </el-table-column>
            <el-table-column label="预测峰值时间" width="130">
              <template #default="{ row }">{{ row.peakTime }}</template>
            </el-table-column>
            <el-table-column label="关键因素" min-width="180">
              <template #default="{ row }">
                <el-tag
                  v-for="factor in row.keyFactors.slice(0, 2)"
                  :key="factor"
                  size="small"
                  type="info"
                  style="margin-right: 5px;"
                >
                  {{ factor }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="showTopicDetail(row)">详情</el-button>
                <el-button type="warning" link size="small" @click="addToWatch(row)">监控</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 预测趋势图 -->
        <el-card shadow="never" class="prediction-card">
          <template #header>
            <div class="card-header">
              <span>热度预测趋势</span>
              <el-select v-model="trendTopic" size="small" style="width: 200px;">
                <el-option
                  v-for="topic in predictedTopics.slice(0, 10)"
                  :key="topic.id"
                  :label="topic.topic"
                  :value="topic.id"
                />
              </el-select>
            </div>
          </template>
          <div id="prediction-trend-chart" style="height: 280px;"></div>
        </el-card>
      </el-col>

      <!-- 右侧分析面板 -->
      <el-col :span="8">
        <!-- 模型准确性评估 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <div class="card-header">
              <span>预测准确性评估</span>
              <el-tooltip content="基于历史预测数据的回测结果" placement="top">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
          <div class="accuracy-metrics">
            <div class="metric-item">
              <div class="metric-circle" :style="{ '--progress': accuracyMetrics.overall + '%' }">
                <span class="metric-value">{{ accuracyMetrics.overall }}%</span>
              </div>
              <span class="metric-label">综合准确率</span>
            </div>
            <div class="metric-details">
              <div class="detail-item">
                <span class="detail-label">Top10 命中率</span>
                <el-progress :percentage="accuracyMetrics.top10Hit" :stroke-width="8" />
              </div>
              <div class="detail-item">
                <span class="detail-label">热度预测误差</span>
                <span class="detail-value">±{{ accuracyMetrics.heatError }}%</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">峰值时间误差</span>
                <span class="detail-value">±{{ accuracyMetrics.timeError }}分钟</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">误报率</span>
                <span class="detail-value warning">{{ accuracyMetrics.falsePositive }}%</span>
              </div>
            </div>
          </div>
          <div id="accuracy-trend-chart" style="height: 150px;"></div>
        </el-card>

        <!-- 预测因素分析 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <span>预测因素权重</span>
          </template>
          <div id="factor-weight-chart" style="height: 200px;"></div>
          <div class="factor-insights">
            <div class="insight-title">
              <el-icon><InfoFilled /></el-icon>
              关键洞察
            </div>
            <ul class="insight-list">
              <li v-for="(insight, idx) in factorInsights" :key="idx">{{ insight }}</li>
            </ul>
          </div>
        </el-card>

        <!-- 预警统计 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <div class="card-header">
              <span>预警统计</span>
              <el-tag :type="alertStats.status === 'normal' ? 'success' : 'warning'" size="small">
                {{ alertStats.statusLabel }}
              </el-tag>
            </div>
          </template>
          <div class="alert-stats">
            <div class="alert-stat-item">
              <span class="stat-value">{{ alertStats.totalAlerts }}</span>
              <span class="stat-label">今日预警</span>
            </div>
            <div class="alert-stat-item">
              <span class="stat-value success">{{ alertStats.hitCount }}</span>
              <span class="stat-label">命中数</span>
            </div>
            <div class="alert-stat-item">
              <span class="stat-value warning">{{ alertStats.missCount }}</span>
              <span class="stat-label">误报数</span>
            </div>
            <div class="alert-stat-item">
              <span class="stat-value">{{ alertStats.hitRate }}%</span>
              <span class="stat-label">命中率</span>
            </div>
          </div>
          <el-divider />
          <div class="recent-alerts">
            <div class="alerts-title">最近预警</div>
            <div v-for="alert in recentAlerts" :key="alert.id" class="alert-item">
              <div class="alert-info">
                <span class="alert-topic">{{ alert.topic }}</span>
                <el-tag :type="alert.hit ? 'success' : 'danger'" size="small">
                  {{ alert.hit ? '命中' : '误报' }}
                </el-tag>
              </div>
              <div class="alert-meta">
                <span>预测: {{ alert.predictedRank }}</span>
                <span>实际: {{ alert.actualRank || '-' }}</span>
                <span>{{ alert.time }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 预警设置弹窗 -->
    <el-dialog v-model="alertSettingsVisible" title="预警设置" width="600px">
      <el-form label-width="120px">
        <el-form-item label="预测阈值">
          <div class="threshold-setting">
            <span>预测排名进入前</span>
            <el-input-number v-model="alertConfig.rankThreshold" :min="1" :max="50" size="small" />
            <span>名时触发预警</span>
          </div>
        </el-form-item>

        <el-form-item label="置信度要求">
          <el-slider
            v-model="alertConfig.minConfidence"
            :min="50"
            :max="99"
            :marks="{ 50: '50%', 70: '70%', 90: '90%' }"
          />
        </el-form-item>

        <el-form-item label="预警频率">
          <el-radio-group v-model="alertConfig.frequency">
            <el-radio label="realtime">实时推送</el-radio>
            <el-radio label="hourly">每小时汇总</el-radio>
            <el-radio label="daily">每日汇总</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="推送方式">
          <el-checkbox-group v-model="alertConfig.pushMethods">
            <el-checkbox label="browser">浏览器通知</el-checkbox>
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
            <el-checkbox label="webhook">Webhook</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="Webhook URL" v-if="alertConfig.pushMethods.includes('webhook')">
          <el-input v-model="alertConfig.webhookUrl" placeholder="https://your-webhook-url.com" />
        </el-form-item>

        <el-form-item label="关键词过滤">
          <el-select
            v-model="alertConfig.keywords"
            multiple
            filterable
            allow-create
            placeholder="添加关注的关键词"
            style="width: 100%;"
          >
            <el-option v-for="kw in suggestedKeywords" :key="kw" :label="kw" :value="kw" />
          </el-select>
        </el-form-item>

        <el-form-item label="排除词">
          <el-select
            v-model="alertConfig.excludeKeywords"
            multiple
            filterable
            allow-create
            placeholder="添加要排除的关键词"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="alertConfig.enabled" active-text="开启" inactive-text="关闭" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="alertSettingsVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAlertSettings">保存设置</el-button>
      </template>
    </el-dialog>

    <!-- 话题详情弹窗 -->
    <el-dialog v-model="topicDetailVisible" :title="selectedTopic?.topic" width="700px">
      <div v-if="selectedTopic" class="topic-detail">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="预测热度">{{ formatHeat(selectedTopic.predictedHeat) }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ selectedTopic.confidence }}%</el-descriptions-item>
          <el-descriptions-item label="预测峰值">{{ selectedTopic.peakTime }}</el-descriptions-item>
          <el-descriptions-item label="当前热度">{{ formatHeat(selectedTopic.currentHeat) }}</el-descriptions-item>
          <el-descriptions-item label="预测变化">
            <span :class="selectedTopic.heatChange > 0 ? 'text-success' : 'text-danger'">
              {{ selectedTopic.heatChange > 0 ? '+' : '' }}{{ selectedTopic.heatChange }}%
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="预测模型">{{ modelNames[predictionModel] }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>关键影响因素</h4>
          <div class="factors-list">
            <div v-for="(factor, idx) in selectedTopic.factorDetails" :key="idx" class="factor-item">
              <span class="factor-name">{{ factor.name }}</span>
              <el-progress :percentage="factor.weight" :stroke-width="10" :color="getFactorColor(factor.weight)" />
              <span class="factor-desc">{{ factor.description }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>预测依据</h4>
          <div id="topic-prediction-chart" style="height: 200px;"></div>
        </div>

        <div class="detail-section">
          <h4>相似历史案例</h4>
          <el-table :data="similarCases" size="small">
            <el-table-column prop="topic" label="话题" />
            <el-table-column prop="predictedRank" label="预测排名" width="100" />
            <el-table-column prop="actualRank" label="实际排名" width="100" />
            <el-table-column prop="accuracy" label="准确度" width="100">
              <template #default="{ row }">
                <el-tag :type="row.accuracy >= 80 ? 'success' : 'warning'" size="small">
                  {{ row.accuracy }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="date" label="日期" width="120" />
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  Clock, Connection, Cpu, Grid, TrendCharts, Bell, Download,
  QuestionFilled, InfoFilled
} from '@element-plus/icons-vue';

// 预测配置
const predictionModel = ref('ensemble');
const predictionRange = ref('24h');
const confidenceThreshold = ref(70);
const predictionCount = ref(20);
const selectedFeatures = ref(['history_heat', 'spread_speed', 'engagement', 'kol_influence']);

const modelNames: Record<string, string> = {
  arima: '时间序列模型 (ARIMA)',
  social: '社交网络模型',
  lstm: '深度学习模型 (LSTM)',
  ensemble: '集成模型',
};

const modelDescription = computed(() => {
  const descriptions: Record<string, string> = {
    arima: '基于历史热度数据的时间序列分析，适合短期预测',
    social: '分析社交网络传播特征，适合病毒式传播预测',
    lstm: '深度学习模型，综合多维特征，准确率最高',
    ensemble: '多模型集成，综合各模型优势，推荐使用',
  };
  return descriptions[predictionModel.value];
});

// 预测状态
const isPredicting = ref(false);
const predictionTime = ref('--');

// 预测结果
interface PredictedTopic {
  id: number;
  topic: string;
  predictedHeat: number;
  currentHeat: number;
  heatChange: number;
  confidence: number;
  peakTime: string;
  isNew: boolean;
  isRising: boolean;
  keyFactors: string[];
  factorDetails: { name: string; weight: number; description: string }[];
}

const predictedTopics = ref<PredictedTopic[]>([]);
const trendTopic = ref<number | null>(null);

// 准确性指标
const accuracyMetrics = reactive({
  overall: 82,
  top10Hit: 78,
  heatError: 15,
  timeError: 45,
  falsePositive: 12,
});

// 因素洞察
const factorInsights = ref([
  'KOL参与度是当前最重要的预测因素',
  '晚间20-22点是热点爆发高峰期',
  '带有争议性话题更容易快速传播',
]);

// 预警配置
const alertSettingsVisible = ref(false);
const alertConfig = reactive({
  rankThreshold: 20,
  minConfidence: 70,
  frequency: 'realtime',
  pushMethods: ['browser'],
  webhookUrl: '',
  keywords: [] as string[],
  excludeKeywords: [] as string[],
  enabled: true,
});

const suggestedKeywords = ['品牌名', '竞品', '行业', '产品', '热点'];

// 预警统计
const alertStats = reactive({
  status: 'normal',
  statusLabel: '正常',
  totalAlerts: 15,
  hitCount: 12,
  missCount: 3,
  hitRate: 80,
});

const recentAlerts = ref([
  { id: 1, topic: '科技峰会召开', predictedRank: 5, actualRank: 3, hit: true, time: '10:30' },
  { id: 2, topic: '明星官宣', predictedRank: 8, actualRank: 12, hit: true, time: '09:15' },
  { id: 3, topic: '新品发布', predictedRank: 15, actualRank: null, hit: false, time: '08:00' },
]);

// 话题详情
const topicDetailVisible = ref(false);
const selectedTopic = ref<PredictedTopic | null>(null);
const similarCases = ref([
  { topic: '类似话题A', predictedRank: 5, actualRank: 4, accuracy: 92, date: '2025-12-05' },
  { topic: '类似话题B', predictedRank: 8, actualRank: 10, accuracy: 85, date: '2025-12-03' },
  { topic: '类似话题C', predictedRank: 12, actualRank: 15, accuracy: 78, date: '2025-11-28' },
]);

// 图表实例
let trendChart: echarts.ECharts | null = null;
let accuracyChart: echarts.ECharts | null = null;
let factorChart: echarts.ECharts | null = null;
let topicPredictionChart: echarts.ECharts | null = null;

// 生成预测数据
function generatePredictions() {
  const topics = [
    '年度热词揭晓', '科技创新大会', '明星新动态', '体育赛事决赛', '政策新规解读',
    '电影票房新高', '网红事件', '财经市场动态', '游戏新版本', '综艺节目热议',
    '教育改革方案', '健康话题', '美食推荐', '旅游攻略', '时尚潮流',
    '汽车新能源', '房产市场', '职场话题', '情感故事', '文化艺术',
  ];

  const factors = ['KOL参与', '传播速度', '用户互动', '时间因素', '话题关联', '情感倾向'];

  predictedTopics.value = topics.slice(0, predictionCount.value).map((topic, i) => ({
    id: i + 1,
    topic,
    predictedHeat: Math.floor(Math.random() * 5000000 + 1000000),
    currentHeat: Math.floor(Math.random() * 3000000 + 500000),
    heatChange: Math.floor(Math.random() * 100 - 20),
    confidence: Math.floor(Math.random() * 30 + confidenceThreshold.value),
    peakTime: `${Math.floor(Math.random() * 12 + 12)}:00`,
    isNew: i < 3,
    isRising: Math.random() > 0.7,
    keyFactors: factors.slice(0, Math.floor(Math.random() * 3 + 2)),
    factorDetails: factors.map(f => ({
      name: f,
      weight: Math.floor(Math.random() * 40 + 30),
      description: `${f}对该话题的影响程度`,
    })),
  }));

  if (predictedTopics.value.length > 0) {
    trendTopic.value = predictedTopics.value[0].id;
  }
}

// 初始化趋势图
function initTrendChart() {
  const dom = document.getElementById('prediction-trend-chart');
  if (!dom) return;

  trendChart = echarts.init(dom);
  updateTrendChart();
}

function updateTrendChart() {
  if (!trendChart) return;

  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const historyData = hours.slice(0, 12).map(() => Math.floor(Math.random() * 2000000 + 500000));
  const predictedData = [...Array(12).fill(null), ...hours.slice(12).map(() => Math.floor(Math.random() * 3000000 + 1000000))];
  const upperBound = predictedData.map(v => v ? v * 1.15 : null);
  const lowerBound = predictedData.map(v => v ? v * 0.85 : null);

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史热度', '预测热度'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: hours, boundaryGap: false },
    yAxis: { type: 'value', name: '热度' },
    series: [
      {
        name: '历史热度',
        type: 'line',
        data: [...historyData, ...Array(12).fill(null)],
        smooth: true,
        itemStyle: { color: '#409eff' },
        lineStyle: { width: 2 },
      },
      {
        name: '预测热度',
        type: 'line',
        data: predictedData,
        smooth: true,
        itemStyle: { color: '#e6a23c' },
        lineStyle: { width: 2, type: 'dashed' },
      },
      {
        name: '置信上界',
        type: 'line',
        data: upperBound,
        lineStyle: { opacity: 0 },
        stack: 'confidence',
        symbol: 'none',
      },
      {
        name: '置信区间',
        type: 'line',
        data: lowerBound.map((v, i) => v && upperBound[i] ? upperBound[i]! - v : null),
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(230, 162, 60, 0.2)' },
        stack: 'confidence',
        symbol: 'none',
      },
    ],
  });
}

// 初始化准确率趋势图
function initAccuracyChart() {
  const dom = document.getElementById('accuracy-trend-chart');
  if (!dom) return;

  accuracyChart = echarts.init(dom);
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return `${d.getMonth() + 1}/${d.getDate()}`;
  });

  accuracyChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: days },
    yAxis: { type: 'value', min: 60, max: 100, name: '%' },
    series: [{
      type: 'line',
      data: [75, 78, 82, 80, 85, 83, 82],
      smooth: true,
      areaStyle: { color: 'rgba(103, 194, 58, 0.2)' },
      itemStyle: { color: '#67c23a' },
    }],
  });
}

// 初始化因素权重图
function initFactorChart() {
  const dom = document.getElementById('factor-weight-chart');
  if (!dom) return;

  factorChart = echarts.init(dom);
  const factors = ['KOL影响', '传播速度', '用户参与', '时间因素', '历史热度', '情感倾向'];
  const weights = [28, 22, 18, 12, 12, 8];

  factorChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '25%', right: '10%', top: '5%', bottom: '5%' },
    xAxis: { type: 'value', max: 35 },
    yAxis: { type: 'category', data: factors.reverse() },
    series: [{
      type: 'bar',
      data: weights.reverse().map((v, i) => ({
        value: v,
        itemStyle: { color: `hsl(${200 - i * 30}, 70%, 50%)` },
      })),
      label: { show: true, position: 'right', formatter: '{c}%' },
    }],
  });
}

// 初始化话题预测图
function initTopicPredictionChart() {
  const dom = document.getElementById('topic-prediction-chart');
  if (!dom) return;

  topicPredictionChart = echarts.init(dom);
  const hours = Array.from({ length: 12 }, (_, i) => `${12 + i}:00`);

  topicPredictionChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: '热度' },
    series: [{
      type: 'line',
      data: hours.map((_, i) => Math.floor(Math.random() * 1000000 + 500000 + i * 200000)),
      smooth: true,
      areaStyle: { color: 'rgba(64, 158, 255, 0.3)' },
      itemStyle: { color: '#409eff' },
      markPoint: {
        data: [{ type: 'max', name: '峰值' }],
        symbol: 'pin',
        symbolSize: 40,
      },
    }],
  });
}

// 事件处理
async function runPrediction() {
  isPredicting.value = true;
  ElMessage.info('正在运行预测模型...');

  await new Promise(r => setTimeout(r, 2000));

  generatePredictions();
  predictionTime.value = new Date().toLocaleString('zh-CN');

  nextTick(() => {
    initTrendChart();
    initAccuracyChart();
    initFactorChart();
  });

  isPredicting.value = false;
  ElMessage.success('预测完成！');
}

function showAlertSettings() {
  alertSettingsVisible.value = true;
}

function saveAlertSettings() {
  alertSettingsVisible.value = false;
  ElMessage.success('预警设置已保存');
}

function exportPredictions() {
  ElMessage.success('预测结果已导出');
}

function showTopicDetail(topic: PredictedTopic) {
  selectedTopic.value = topic;
  topicDetailVisible.value = true;
  nextTick(() => {
    initTopicPredictionChart();
  });
}

function addToWatch(topic: PredictedTopic) {
  alertConfig.keywords.push(topic.topic);
  ElMessage.success(`已将"${topic.topic}"添加到监控列表`);
}

// 工具函数
function formatHeat(heat: number) {
  if (heat >= 10000000) return (heat / 10000000).toFixed(1) + '千万';
  if (heat >= 10000) return (heat / 10000).toFixed(0) + '万';
  return heat.toLocaleString();
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 85) return '#67c23a';
  if (confidence >= 70) return '#e6a23c';
  return '#f56c6c';
}

function getFactorColor(weight: number) {
  if (weight >= 70) return '#f56c6c';
  if (weight >= 50) return '#e6a23c';
  return '#409eff';
}

// 监听趋势话题变化
watch(trendTopic, () => {
  updateTrendChart();
});

// 窗口大小变化
function handleResize() {
  trendChart?.resize();
  accuracyChart?.resize();
  factorChart?.resize();
  topicPredictionChart?.resize();
}

// 生命周期
onMounted(() => {
  generatePredictions();
  nextTick(() => {
    initTrendChart();
    initAccuracyChart();
    initFactorChart();
  });
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  trendChart?.dispose();
  accuracyChart?.dispose();
  factorChart?.dispose();
  topicPredictionChart?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.hot-prediction {
  padding: 15px;
}

/* 控制面板 */
.prediction-controls {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.control-section {
  height: 100%;
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 10px;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.param-item {
  margin-bottom: 5px;
}

.param-label {
  font-size: 12px;
  color: #606266;
  display: block;
  margin-bottom: 5px;
}

.action-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
}

/* 卡片 */
.prediction-card, .analysis-card {
  margin-bottom: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 排名徽章 */
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-weight: bold;
  font-size: 14px;
  background: #909399;
  color: #fff;
}

.rank-badge.rank-1 { background: #f56c6c; }
.rank-badge.rank-2 { background: #e6a23c; }
.rank-badge.rank-3 { background: #f4e04d; color: #333; }

/* 话题单元格 */
.topic-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.topic-name {
  font-weight: 500;
}

/* 热度单元格 */
.heat-cell {
  display: flex;
  flex-direction: column;
}

.heat-value {
  font-weight: 500;
}

.heat-change {
  font-size: 12px;
}

.heat-change.up { color: #67c23a; }
.heat-change.down { color: #f56c6c; }

/* 准确性指标 */
.accuracy-metrics {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 10px 0;
}

.metric-item {
  text-align: center;
}

.metric-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: conic-gradient(#67c23a var(--progress), #ebeef5 var(--progress));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.metric-circle::before {
  content: '';
  position: absolute;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: #fff;
}

.metric-value {
  position: relative;
  font-size: 18px;
  font-weight: bold;
  color: #67c23a;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  display: block;
}

.metric-details {
  flex: 1;
}

.detail-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-label {
  font-size: 12px;
  color: #606266;
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.detail-value.warning {
  color: #e6a23c;
}

/* 因素洞察 */
.factor-insights {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-top: 10px;
}

.insight-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  color: #409eff;
  margin-bottom: 8px;
}

.insight-list {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: #606266;
  line-height: 1.8;
}

/* 预警统计 */
.alert-stats {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
}

.alert-stat-item {
  text-align: center;
}

.alert-stat-item .stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.alert-stat-item .stat-value.success { color: #67c23a; }
.alert-stat-item .stat-value.warning { color: #e6a23c; }

.alert-stat-item .stat-label {
  font-size: 12px;
  color: #909399;
}

.recent-alerts {
  max-height: 200px;
  overflow-y: auto;
}

.alerts-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 10px;
}

.alert-item {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 8px;
}

.alert-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.alert-topic {
  font-size: 13px;
  font-weight: 500;
}

.alert-meta {
  display: flex;
  gap: 15px;
  font-size: 11px;
  color: #909399;
}

/* 阈值设置 */
.threshold-setting {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 话题详情 */
.topic-detail .detail-section {
  margin-top: 20px;
}

.topic-detail h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.factors-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.factor-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.factor-name {
  width: 80px;
  font-size: 13px;
  color: #606266;
}

.factor-item :deep(.el-progress) {
  flex: 1;
}

.factor-desc {
  font-size: 12px;
  color: #909399;
  width: 150px;
}

.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
</style>
