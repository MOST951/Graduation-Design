<template>
  <div class="sentiment-distribution">
    <el-row :gutter="20">
      <!-- 区域1: 核心指标卡片 -->
      <el-col :xs="24" :sm="24" :md="6">
        <div class="metrics-column">
          <!-- 总分析量 -->
          <div class="metric-card" @click="handleMetricClick('total')">
            <div class="metric-header">
              <span class="metric-title">总分析量</span>
              <div :class="['trend-badge', metrics.totalTrend > 0 ? 'up' : 'down']">
                <el-icon><component :is="metrics.totalTrend > 0 ? 'CaretTop' : 'CaretBottom'" /></el-icon>
                {{ Math.abs(metrics.totalTrend) }}%
              </div>
            </div>
            <div class="metric-value">{{ formatNumber(metrics.totalCount) }}</div>
            <div class="metric-compare">较昨日 {{ metrics.totalTrend > 0 ? '+' : '' }}{{ metrics.yesterdayDiff }}</div>
          </div>

          <!-- 正面情感率 -->
          <div class="metric-card positive" @click="handleMetricClick('positive')">
            <div class="metric-header">
              <span class="metric-title">正面情感率</span>
              <el-icon class="sentiment-icon"><Sunny /></el-icon>
            </div>
            <div class="metric-value">{{ metrics.positiveRate }}%</div>
            <el-progress :percentage="metrics.positiveRate" :stroke-width="6" :show-text="false" color="#67c23a" />
          </div>

          <!-- 负面情感率 -->
          <div class="metric-card negative" @click="handleMetricClick('negative')">
            <div class="metric-header">
              <span class="metric-title">负面情感率</span>
              <el-icon class="sentiment-icon"><Cloudy /></el-icon>
            </div>
            <div class="metric-value">{{ metrics.negativeRate }}%</div>
            <el-progress :percentage="metrics.negativeRate" :stroke-width="6" :show-text="false" color="#f56c6c" />
          </div>

          <!-- 平均情感得分 -->
          <div class="metric-card score">
            <div class="metric-header">
              <span class="metric-title">平均情感得分</span>
              <el-tooltip content="范围: -1(极负面) 到 +1(极正面)" placement="top">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="metric-value" :class="getScoreClass(metrics.avgScore)">
              {{ metrics.avgScore > 0 ? '+' : '' }}{{ metrics.avgScore.toFixed(2) }}
            </div>
            <div class="score-bar">
              <div class="score-indicator" :style="{ left: getScorePosition(metrics.avgScore) }"></div>
            </div>
            <div class="score-labels">
              <span>-1</span>
              <span>0</span>
              <span>+1</span>
            </div>
          </div>

          <!-- 情感极值 -->
          <div class="metric-card extremes">
            <div class="metric-header">
              <span class="metric-title">情感极值</span>
            </div>
            <div class="extreme-item positive" @click="showExtremeDetail('positive')">
              <el-icon><Top /></el-icon>
              <div class="extreme-content">
                <div class="extreme-label">最正面</div>
                <div class="extreme-text">{{ truncate(metrics.mostPositive.content, 30) }}</div>
                <div class="extreme-score">+{{ metrics.mostPositive.score.toFixed(2) }}</div>
              </div>
            </div>
            <div class="extreme-item negative" @click="showExtremeDetail('negative')">
              <el-icon><Bottom /></el-icon>
              <div class="extreme-content">
                <div class="extreme-label">最负面</div>
                <div class="extreme-text">{{ truncate(metrics.mostNegative.content, 30) }}</div>
                <div class="extreme-score">{{ metrics.mostNegative.score.toFixed(2) }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 区域2: 情感分布饼图 -->
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>情感分布</span>
              <el-radio-group v-model="pieChartMode" size="small">
                <el-radio-button label="basic">基础分类</el-radio-button>
                <el-radio-button label="fine">细粒度</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          
          <div class="pie-charts-container">
            <!-- 基础分类饼图 -->
            <div v-show="pieChartMode === 'basic'" id="basic-pie-chart" style="width: 100%; height: 350px;"></div>
            <!-- 细粒度环形图 -->
            <div v-show="pieChartMode === 'fine'" id="fine-pie-chart" style="width: 100%; height: 350px;"></div>
          </div>

          <!-- 图例说明 -->
          <div class="chart-legend" v-if="pieChartMode === 'fine'">
            <div v-for="emotion in fineEmotions" :key="emotion.name" class="legend-item" @click="filterByEmotion(emotion.name)">
              <span class="legend-color" :style="{ background: emotion.color }"></span>
              <span class="legend-name">{{ emotion.name }}</span>
              <span class="legend-value">{{ emotion.count }}</span>
            </div>
          </div>
        </el-card>

        <!-- 时间对比 -->
        <el-card shadow="hover" class="chart-card compare-card">
          <template #header>
            <div class="card-header">
              <span>历史对比</span>
              <el-select v-model="compareMode" size="small" style="width: 120px;">
                <el-option label="昨日" value="yesterday" />
                <el-option label="上周同期" value="lastWeek" />
                <el-option label="上月同期" value="lastMonth" />
              </el-select>
            </div>
          </template>
          <div class="compare-content">
            <div class="compare-item">
              <span class="compare-label">正面</span>
              <div class="compare-bars">
                <div class="compare-bar current" :style="{ width: metrics.positiveRate + '%' }">
                  <span>{{ metrics.positiveRate }}%</span>
                </div>
                <div class="compare-bar history" :style="{ width: compareData.positiveRate + '%' }">
                  <span>{{ compareData.positiveRate }}%</span>
                </div>
              </div>
              <span :class="['compare-diff', getDiffClass(metrics.positiveRate - compareData.positiveRate)]">
                {{ formatDiff(metrics.positiveRate - compareData.positiveRate) }}
              </span>
            </div>
            <div class="compare-item">
              <span class="compare-label">中性</span>
              <div class="compare-bars">
                <div class="compare-bar current neutral" :style="{ width: metrics.neutralRate + '%' }">
                  <span>{{ metrics.neutralRate }}%</span>
                </div>
                <div class="compare-bar history" :style="{ width: compareData.neutralRate + '%' }">
                  <span>{{ compareData.neutralRate }}%</span>
                </div>
              </div>
              <span :class="['compare-diff', getDiffClass(metrics.neutralRate - compareData.neutralRate)]">
                {{ formatDiff(metrics.neutralRate - compareData.neutralRate) }}
              </span>
            </div>
            <div class="compare-item">
              <span class="compare-label">负面</span>
              <div class="compare-bars">
                <div class="compare-bar current negative" :style="{ width: metrics.negativeRate + '%' }">
                  <span>{{ metrics.negativeRate }}%</span>
                </div>
                <div class="compare-bar history" :style="{ width: compareData.negativeRate + '%' }">
                  <span>{{ compareData.negativeRate }}%</span>
                </div>
              </div>
              <span :class="['compare-diff reverse', getDiffClass(compareData.negativeRate - metrics.negativeRate)]">
                {{ formatDiff(metrics.negativeRate - compareData.negativeRate) }}
              </span>
            </div>
          </div>
          <div class="compare-legend">
            <span class="legend-current">■ 当前</span>
            <span class="legend-history">■ {{ compareMode === 'yesterday' ? '昨日' : compareMode === 'lastWeek' ? '上周' : '上月' }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 区域3: 情感强度分布 -->
      <el-col :xs="24" :sm="24" :md="6">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>强度分布</span>
          </template>
          <div id="intensity-histogram" style="width: 100%; height: 200px;"></div>
          <div class="intensity-stats">
            <div class="intensity-stat">
              <span class="stat-label">强烈情感占比</span>
              <span class="stat-value">{{ intensityStats.strongRatio }}%</span>
            </div>
            <div class="intensity-stat">
              <span class="stat-label">中等情感占比</span>
              <span class="stat-value">{{ intensityStats.mediumRatio }}%</span>
            </div>
            <div class="intensity-stat">
              <span class="stat-label">弱情感占比</span>
              <span class="stat-value">{{ intensityStats.weakRatio }}%</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>强度趋势</span>
          </template>
          <div id="intensity-trend" style="width: 100%; height: 180px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据下钻弹窗 -->
    <el-dialog v-model="drillDownVisible" :title="drillDownTitle" width="800px">
      <el-table :data="drillDownData" max-height="400">
        <el-table-column prop="content" label="内容" min-width="300">
          <template #default="{ row }">
            <el-tooltip :content="row.content" placement="top">
              <span>{{ truncate(row.content, 50) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="sentiment" label="情感" width="100">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment)" size="small">{{ row.sentiment }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="得分" width="100">
          <template #default="{ row }">
            <span :class="getScoreClass(row.score)">{{ row.score > 0 ? '+' : '' }}{{ row.score.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="80" />
        <el-table-column prop="time" label="时间" width="150" />
      </el-table>
      <template #footer>
        <el-button @click="drillDownVisible = false">关闭</el-button>
        <el-button type="primary" @click="exportDrillDownData">导出数据</el-button>
      </template>
    </el-dialog>

    <!-- 极值详情弹窗 -->
    <el-dialog v-model="extremeDetailVisible" :title="extremeDetailTitle" width="500px">
      <div class="extreme-detail" v-if="extremeDetailData">
        <div class="detail-content">{{ extremeDetailData.content }}</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="情感得分">
            <span :class="getScoreClass(extremeDetailData.score)">
              {{ extremeDetailData.score > 0 ? '+' : '' }}{{ extremeDetailData.score.toFixed(3) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="情感类型">
            <el-tag :type="getSentimentType(extremeDetailData.sentiment)">{{ extremeDetailData.sentiment }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源">{{ extremeDetailData.source }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="时间">{{ extremeDetailData.time }}</el-descriptions-item>
          <el-descriptions-item label="关键词" :span="2">
            <el-tag v-for="kw in extremeDetailData.keywords" :key="kw" size="small" style="margin-right: 5px;">{{ kw }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { Sunny, Cloudy, QuestionFilled, Top, Bottom, CaretTop, CaretBottom } from '@element-plus/icons-vue';

// Props & Emits
const emit = defineEmits<{
  (e: 'filter-change', filter: { type: string; value: string }): void;
  (e: 'drill-down', data: any[]): void;
}>();

// 图表模式
const pieChartMode = ref<'basic' | 'fine'>('basic');
const compareMode = ref('yesterday');

// 核心指标
const metrics = reactive({
  totalCount: 45218,
  totalTrend: 12.5,
  yesterdayDiff: 5023,
  positiveRate: 45.2,
  neutralRate: 31.0,
  negativeRate: 23.8,
  avgScore: 0.23,
  mostPositive: {
    content: '这个产品真的太棒了！用了之后效果非常好，强烈推荐给大家，五星好评！',
    score: 0.98,
    sentiment: '正面',
    source: '微博',
    time: '2025-12-10 02:30',
    keywords: ['产品', '效果', '推荐', '好评'],
  },
  mostNegative: {
    content: '太失望了，质量差到极点，客服态度也很恶劣，再也不会买了！',
    score: -0.95,
    sentiment: '负面',
    source: '微信',
    time: '2025-12-10 01:45',
    keywords: ['失望', '质量', '客服', '态度'],
  },
});

// 对比数据
const compareData = reactive({
  positiveRate: 42.1,
  neutralRate: 33.5,
  negativeRate: 24.4,
});

// 强度统计
const intensityStats = reactive({
  strongRatio: 28.5,
  mediumRatio: 45.2,
  weakRatio: 26.3,
});

// 细粒度情感
const fineEmotions = ref([
  { name: '喜悦', count: 8520, color: '#67c23a' },
  { name: '信任', count: 6230, color: '#85ce61' },
  { name: '期待', count: 5680, color: '#b3e19d' },
  { name: '惊讶', count: 3240, color: '#909399' },
  { name: '悲伤', count: 4120, color: '#a0cfff' },
  { name: '恐惧', count: 2850, color: '#f89898' },
  { name: '厌恶', count: 3560, color: '#f56c6c' },
  { name: '愤怒', count: 4210, color: '#c45656' },
]);

// 下钻数据
const drillDownVisible = ref(false);
const drillDownTitle = ref('');
const drillDownData = ref<any[]>([]);

// 极值详情
const extremeDetailVisible = ref(false);
const extremeDetailTitle = ref('');
const extremeDetailData = ref<any>(null);

// 图表实例
let basicPieChart: echarts.ECharts | null = null;
let finePieChart: echarts.ECharts | null = null;
let intensityHistogram: echarts.ECharts | null = null;
let intensityTrend: echarts.ECharts | null = null;

// 初始化基础饼图
function initBasicPieChart() {
  const dom = document.getElementById('basic-pie-chart');
  if (!dom) return;

  basicPieChart = echarts.init(dom);
  basicPieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: 10,
      left: 'center'
    },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: '{b}\n{d}%',
        fontSize: 12
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold'
        },
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      data: [
        { value: metrics.positiveRate, name: '正面', itemStyle: { color: '#67c23a' } },
        { value: metrics.neutralRate, name: '中性', itemStyle: { color: '#909399' } },
        { value: metrics.negativeRate, name: '负面', itemStyle: { color: '#f56c6c' } },
      ]
    }]
  });

  // 点击事件 - 数据下钻
  basicPieChart.on('click', (params: any) => {
    handlePieClick(params.name);
  });
}

// 初始化细粒度饼图
function initFinePieChart() {
  const dom = document.getElementById('fine-pie-chart');
  if (!dom) return;

  finePieChart = echarts.init(dom);
  finePieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    series: [{
      type: 'pie',
      radius: ['30%', '70%'],
      center: ['50%', '50%'],
      roseType: 'radius',
      itemStyle: {
        borderRadius: 5
      },
      label: {
        show: true,
        formatter: '{b}',
        fontSize: 11
      },
      data: fineEmotions.value.map(e => ({
        value: e.count,
        name: e.name,
        itemStyle: { color: e.color }
      }))
    }]
  });

  finePieChart.on('click', (params: any) => {
    filterByEmotion(params.name);
  });
}

// 初始化强度直方图
function initIntensityHistogram() {
  const dom = document.getElementById('intensity-histogram');
  if (!dom) return;

  intensityHistogram = echarts.init(dom);
  intensityHistogram.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: '强度 {b}: {c} 条'
    },
    grid: {
      left: '5%',
      right: '5%',
      top: '10%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
      axisLabel: { fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 10 }
    },
    series: [{
      type: 'bar',
      data: [
        { value: 1200, itemStyle: { color: '#e8f5e9' } },
        { value: 2100, itemStyle: { color: '#c8e6c9' } },
        { value: 3500, itemStyle: { color: '#a5d6a7' } },
        { value: 5200, itemStyle: { color: '#81c784' } },
        { value: 6800, itemStyle: { color: '#66bb6a' } },
        { value: 7200, itemStyle: { color: '#ffa726' } },
        { value: 5800, itemStyle: { color: '#ff7043' } },
        { value: 4200, itemStyle: { color: '#ef5350' } },
        { value: 2800, itemStyle: { color: '#e53935' } },
        { value: 1500, itemStyle: { color: '#c62828' } },
      ],
      barWidth: '60%',
      itemStyle: { borderRadius: [3, 3, 0, 0] }
    }]
  });

  intensityHistogram.on('click', (params: any) => {
    handleIntensityClick(params.dataIndex + 1);
  });
}

// 初始化强度趋势图
function initIntensityTrend() {
  const dom = document.getElementById('intensity-trend');
  if (!dom) return;

  intensityTrend = echarts.init(dom);
  intensityTrend.setOption({
    tooltip: { trigger: 'axis' },
    grid: {
      left: '5%',
      right: '5%',
      top: '15%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['12/04', '12/05', '12/06', '12/07', '12/08', '12/09', '12/10'],
      axisLabel: { fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '平均强度',
      nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10 }
    },
    series: [{
      type: 'line',
      smooth: true,
      data: [5.2, 5.8, 5.5, 6.1, 5.9, 6.3, 6.5],
      itemStyle: { color: '#409eff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      }
    }]
  });
}

// 事件处理
function handleMetricClick(type: string) {
  emit('filter-change', { type: 'sentiment', value: type });
}

function handlePieClick(sentiment: string) {
  drillDownTitle.value = `${sentiment}情感数据详情`;
  drillDownData.value = generateMockDrillDownData(sentiment);
  drillDownVisible.value = true;
  emit('drill-down', drillDownData.value);
}

function filterByEmotion(emotion: string) {
  drillDownTitle.value = `${emotion}情感数据详情`;
  drillDownData.value = generateMockDrillDownData(emotion);
  drillDownVisible.value = true;
  emit('filter-change', { type: 'emotion', value: emotion });
}

function handleIntensityClick(intensity: number) {
  drillDownTitle.value = `强度 ${intensity} 级数据详情`;
  drillDownData.value = generateMockDrillDownData(`强度${intensity}`);
  drillDownVisible.value = true;
}

function showExtremeDetail(type: 'positive' | 'negative') {
  extremeDetailTitle.value = type === 'positive' ? '最正面微博详情' : '最负面微博详情';
  extremeDetailData.value = type === 'positive' ? metrics.mostPositive : metrics.mostNegative;
  extremeDetailVisible.value = true;
}

function exportDrillDownData() {
  ElMessage.success('数据导出中...');
}

// 工具函数
function formatNumber(num: number) {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toLocaleString();
}

function truncate(text: string, length: number) {
  return text.length > length ? text.slice(0, length) + '...' : text;
}

function getScoreClass(score: number) {
  if (score > 0.3) return 'score-positive';
  if (score < -0.3) return 'score-negative';
  return 'score-neutral';
}

function getScorePosition(score: number) {
  return ((score + 1) / 2 * 100) + '%';
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { '正面': 'success', '中性': 'info', '负面': 'danger' };
  return map[sentiment] || 'info';
}

function getDiffClass(diff: number) {
  if (diff > 0) return 'positive';
  if (diff < 0) return 'negative';
  return '';
}

function formatDiff(diff: number) {
  if (diff > 0) return '+' + diff.toFixed(1) + '%';
  return diff.toFixed(1) + '%';
}

function generateMockDrillDownData(type: string) {
  const sentiments = ['正面', '中性', '负面'];
  const sources = ['微博', '微信', '抖音'];
  const contents = [
    '这个产品真的很不错，推荐给大家！',
    '服务态度一般，有待改进',
    '太失望了，质量很差',
    '物流很快，包装也很好',
    '价格有点贵，但质量还行',
    '客服回复很及时，好评',
    '不太满意，希望能改进',
    '非常喜欢，会继续支持',
  ];

  return Array.from({ length: 20 }, (_, i) => ({
    id: i + 1,
    content: contents[i % contents.length],
    sentiment: sentiments[i % 3],
    score: (Math.random() * 2 - 1),
    source: sources[i % 3],
    time: `2025-12-10 0${i % 9 + 1}:${String(i * 3 % 60).padStart(2, '0')}`,
  }));
}

// 监听图表模式切换
watch(pieChartMode, (mode) => {
  nextTick(() => {
    if (mode === 'basic') {
      basicPieChart?.resize();
    } else {
      finePieChart?.resize();
    }
  });
});

// 监听对比模式切换
watch(compareMode, (mode) => {
  // 模拟不同时期的对比数据
  if (mode === 'yesterday') {
    compareData.positiveRate = 42.1;
    compareData.neutralRate = 33.5;
    compareData.negativeRate = 24.4;
  } else if (mode === 'lastWeek') {
    compareData.positiveRate = 40.5;
    compareData.neutralRate = 35.2;
    compareData.negativeRate = 24.3;
  } else {
    compareData.positiveRate = 38.8;
    compareData.neutralRate = 36.1;
    compareData.negativeRate = 25.1;
  }
});

// 窗口大小变化
function handleResize() {
  basicPieChart?.resize();
  finePieChart?.resize();
  intensityHistogram?.resize();
  intensityTrend?.resize();
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initBasicPieChart();
    initFinePieChart();
    initIntensityHistogram();
    initIntensityTrend();
  });
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  basicPieChart?.dispose();
  finePieChart?.dispose();
  intensityHistogram?.dispose();
  intensityTrend?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.sentiment-distribution {
  padding: 20px;
}

/* 指标卡片列 */
.metrics-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-card {
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: all 0.3s;
}
.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.metric-title {
  font-size: 13px;
  color: #909399;
}

.sentiment-icon {
  font-size: 18px;
}
.metric-card.positive .sentiment-icon { color: #67c23a; }
.metric-card.negative .sentiment-icon { color: #f56c6c; }

.trend-badge {
  display: flex;
  align-items: center;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}
.trend-badge.up {
  color: #67c23a;
  background: #f0f9eb;
}
.trend-badge.down {
  color: #f56c6c;
  background: #fef0f0;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.metric-compare {
  font-size: 12px;
  color: #909399;
}

/* 得分条 */
.score-bar {
  height: 6px;
  background: linear-gradient(to right, #f56c6c, #909399, #67c23a);
  border-radius: 3px;
  position: relative;
  margin: 10px 0 5px;
}
.score-indicator {
  position: absolute;
  top: -3px;
  width: 12px;
  height: 12px;
  background: #303133;
  border-radius: 50%;
  transform: translateX(-50%);
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.score-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #909399;
}

.score-positive { color: #67c23a; }
.score-neutral { color: #909399; }
.score-negative { color: #f56c6c; }

/* 极值卡片 */
.extreme-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  border-radius: 6px;
  margin-top: 8px;
  cursor: pointer;
}
.extreme-item.positive {
  background: #f0f9eb;
}
.extreme-item.positive .el-icon { color: #67c23a; }
.extreme-item.negative {
  background: #fef0f0;
}
.extreme-item.negative .el-icon { color: #f56c6c; }

.extreme-content {
  flex: 1;
  min-width: 0;
}
.extreme-label {
  font-size: 11px;
  color: #909399;
}
.extreme-text {
  font-size: 12px;
  color: #606266;
  margin: 3px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.extreme-score {
  font-size: 14px;
  font-weight: bold;
}
.extreme-item.positive .extreme-score { color: #67c23a; }
.extreme-item.negative .extreme-score { color: #f56c6c; }

/* 图表卡片 */
.chart-card {
  margin-bottom: 15px;
}
.chart-card :deep(.el-card__header) {
  padding: 12px 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

/* 图例 */
.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 15px;
  border-top: 1px solid #ebeef5;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  cursor: pointer;
  padding: 3px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}
.legend-item:hover {
  background: #f5f7fa;
}
.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
.legend-name {
  color: #606266;
}
.legend-value {
  color: #909399;
}

/* 对比卡片 */
.compare-content {
  padding: 10px 0;
}
.compare-item {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}
.compare-label {
  width: 40px;
  font-size: 12px;
  color: #606266;
}
.compare-bars {
  flex: 1;
  margin: 0 10px;
}
.compare-bar {
  height: 18px;
  border-radius: 4px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  padding-left: 8px;
  font-size: 11px;
  color: #fff;
  min-width: 40px;
}
.compare-bar.current {
  background: #67c23a;
}
.compare-bar.current.neutral {
  background: #909399;
}
.compare-bar.current.negative {
  background: #f56c6c;
}
.compare-bar.history {
  background: #dcdfe6;
  color: #606266;
}
.compare-diff {
  width: 60px;
  text-align: right;
  font-size: 12px;
  font-weight: 500;
}
.compare-diff.positive { color: #67c23a; }
.compare-diff.negative { color: #f56c6c; }
.compare-diff.reverse.positive { color: #f56c6c; }
.compare-diff.reverse.negative { color: #67c23a; }

.compare-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  font-size: 12px;
  color: #909399;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
.legend-current { color: #67c23a; }
.legend-history { color: #dcdfe6; }

/* 强度统计 */
.intensity-stats {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
  border-top: 1px solid #ebeef5;
}
.intensity-stat {
  text-align: center;
}
.intensity-stat .stat-label {
  font-size: 11px;
  color: #909399;
}
.intensity-stat .stat-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

/* 弹窗 */
.extreme-detail .detail-content {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 15px;
  line-height: 1.8;
  font-size: 14px;
}
</style>
