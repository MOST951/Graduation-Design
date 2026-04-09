<template>
  <div class="sentiment-trend">
    <!-- 控制栏 -->
    <div class="trend-controls">
      <div class="control-left">
        <!-- 时间粒度选择 -->
        <span class="control-label">时间粒度：</span>
        <el-radio-group v-model="timeGranularity" size="small" @change="handleGranularityChange">
          <el-radio-button label="hour">按小时</el-radio-button>
          <el-radio-button label="day">按天</el-radio-button>
          <el-radio-button label="week">按周</el-radio-button>
          <el-radio-button label="month">按月</el-radio-button>
        </el-radio-group>

        <!-- 对比模式 -->
        <el-divider direction="vertical" />
        <el-switch v-model="compareEnabled" active-text="对比模式" style="margin-right: 10px;" />
        <el-date-picker
          v-if="compareEnabled"
          v-model="compareDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="对比开始"
          end-placeholder="对比结束"
          size="small"
          style="width: 240px;"
        />
      </div>

      <div class="control-right">
        <!-- 预测按钮 -->
        <el-button type="primary" size="small" :loading="predicting" @click="handlePredict">
          <el-icon><TrendCharts /></el-icon>
          预测未来趋势
        </el-button>
        <el-button size="small" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出数据
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- 左侧：趋势图表 -->
      <el-col :span="16">
        <!-- 情感得分趋势 -->
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>情感得分趋势</span>
              <div class="header-options">
                <el-checkbox v-model="showConfidenceInterval" size="small">显示置信区间</el-checkbox>
                <el-checkbox v-model="showAnomalies" size="small">标注异常点</el-checkbox>
              </div>
            </div>
          </template>
          <div id="score-trend-chart" style="width: 100%; height: 300px;"></div>
          <!-- 异常点说明 -->
          <div v-if="showAnomalies && anomalyPoints.length > 0" class="anomaly-list">
            <div class="anomaly-title">
              <el-icon><WarningFilled /></el-icon>
              检测到 {{ anomalyPoints.length }} 个异常波动点
            </div>
            <div v-for="point in anomalyPoints.slice(0, 3)" :key="point.time" class="anomaly-item" @click="showAnomalyDetail(point)">
              <span class="anomaly-time">{{ point.time }}</span>
              <span :class="['anomaly-change', point.change > 0 ? 'up' : 'down']">
                {{ point.change > 0 ? '↑' : '↓' }} {{ Math.abs(point.change).toFixed(1) }}%
              </span>
              <span class="anomaly-reason">{{ point.reason }}</span>
            </div>
          </div>
        </el-card>

        <!-- 正负面数量堆叠面积图 -->
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>情感数量趋势</span>
              <el-radio-group v-model="areaChartMode" size="small">
                <el-radio-button label="stack">堆叠</el-radio-button>
                <el-radio-button label="percent">百分比</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div id="sentiment-area-chart" style="width: 100%; height: 280px;"></div>
        </el-card>

        <!-- 情感波动率 -->
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>情感波动率 (标准差)</span>
              <el-tooltip content="波动率越高表示情感变化越剧烈" placement="top">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
          <div id="volatility-chart" style="width: 100%; height: 200px;"></div>
        </el-card>
      </el-col>

      <!-- 右侧：相关性分析 -->
      <el-col :span="8">
        <!-- 发布时间相关性 -->
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>情感与发布时间相关性</span>
          </template>
          <div id="time-correlation-chart" style="width: 100%; height: 220px;"></div>
          <div class="correlation-insight">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ timeCorrelationInsight }}</span>
          </div>
        </el-card>

        <!-- 关键词相关性热力图 -->
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>关键词情感热力图</span>
          </template>
          <div id="keyword-heatmap" style="width: 100%; height: 280px;"></div>
        </el-card>

        <!-- 预测结果 -->
        <el-card v-if="predictionData.length > 0" shadow="hover" class="chart-card prediction-card">
          <template #header>
            <div class="card-header">
              <span>趋势预测</span>
              <el-tag type="warning" size="small">预测</el-tag>
            </div>
          </template>
          <div id="prediction-chart" style="width: 100%; height: 200px;"></div>
          <div class="prediction-summary">
            <div class="prediction-item">
              <span class="pred-label">预测趋势</span>
              <span :class="['pred-value', predictionTrend > 0 ? 'up' : 'down']">
                {{ predictionTrend > 0 ? '上升' : '下降' }} {{ Math.abs(predictionTrend).toFixed(1) }}%
              </span>
            </div>
            <div class="prediction-item">
              <span class="pred-label">置信度</span>
              <span class="pred-value">{{ predictionConfidence }}%</span>
            </div>
            <div class="prediction-item">
              <span class="pred-label">预测周期</span>
              <span class="pred-value">未来 {{ predictionDays }} 天</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 异常详情弹窗 -->
    <el-dialog v-model="anomalyDialogVisible" title="异常点详情" width="600px">
      <div v-if="selectedAnomaly" class="anomaly-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="发生时间">{{ selectedAnomaly.time }}</el-descriptions-item>
          <el-descriptions-item label="变化幅度">
            <span :class="selectedAnomaly.change > 0 ? 'text-success' : 'text-danger'">
              {{ selectedAnomaly.change > 0 ? '+' : '' }}{{ selectedAnomaly.change.toFixed(2) }}%
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="情感得分">{{ selectedAnomaly.score.toFixed(3) }}</el-descriptions-item>
          <el-descriptions-item label="数据量">{{ selectedAnomaly.count }} 条</el-descriptions-item>
          <el-descriptions-item label="可能原因" :span="2">{{ selectedAnomaly.reason }}</el-descriptions-item>
        </el-descriptions>
        <div class="anomaly-keywords">
          <div class="keywords-title">相关热词</div>
          <el-tag v-for="kw in selectedAnomaly.keywords" :key="kw" style="margin: 3px;">{{ kw }}</el-tag>
        </div>
        <div class="anomaly-samples">
          <div class="samples-title">典型样本</div>
          <div v-for="(sample, idx) in selectedAnomaly.samples" :key="idx" class="sample-item">
            <el-tag :type="getSentimentType(sample.sentiment)" size="small">{{ sample.sentiment }}</el-tag>
            <span class="sample-content">{{ sample.content }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { TrendCharts, Download, WarningFilled, QuestionFilled, InfoFilled } from '@element-plus/icons-vue';

// 控制状态
const timeGranularity = ref<'hour' | 'day' | 'week' | 'month'>('day');
const compareEnabled = ref(false);
const compareDateRange = ref<[Date, Date] | null>(null);
const showConfidenceInterval = ref(true);
const showAnomalies = ref(true);
const areaChartMode = ref<'stack' | 'percent'>('stack');

// 预测状态
const predicting = ref(false);
const predictionData = ref<any[]>([]);
const predictionTrend = ref(0);
const predictionConfidence = ref(0);
const predictionDays = ref(7);

// 异常点
const anomalyPoints = ref([
  { time: '12/08 14:00', change: 25.3, score: 0.45, count: 1250, reason: '热点事件引发正面情感激增', keywords: ['好评', '推荐', '优秀'], samples: [{ sentiment: '正面', content: '这个产品太棒了！' }] },
  { time: '12/06 22:00', change: -18.7, score: -0.32, count: 890, reason: '负面舆情爆发', keywords: ['投诉', '差评', '失望'], samples: [{ sentiment: '负面', content: '服务太差了' }] },
  { time: '12/05 10:00', change: 15.2, score: 0.28, count: 1100, reason: '营销活动带动正面评价', keywords: ['活动', '优惠', '划算'], samples: [{ sentiment: '正面', content: '活动力度很大' }] },
]);

const anomalyDialogVisible = ref(false);
const selectedAnomaly = ref<any>(null);

// 时间相关性洞察
const timeCorrelationInsight = ref('晚间 20:00-22:00 负面情感占比较高，建议加强该时段舆情监控');

// 图表实例
let scoreTrendChart: echarts.ECharts | null = null;
let sentimentAreaChart: echarts.ECharts | null = null;
let volatilityChart: echarts.ECharts | null = null;
let timeCorrelationChart: echarts.ECharts | null = null;
let keywordHeatmap: echarts.ECharts | null = null;
let predictionChart: echarts.ECharts | null = null;

// 生成时间轴数据
function generateTimeAxis() {
  const now = new Date();
  const axis: string[] = [];
  const count = timeGranularity.value === 'hour' ? 24 : 
                timeGranularity.value === 'day' ? 14 : 
                timeGranularity.value === 'week' ? 8 : 6;
  
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now);
    if (timeGranularity.value === 'hour') {
      d.setHours(d.getHours() - i);
      axis.push(`${d.getHours()}:00`);
    } else if (timeGranularity.value === 'day') {
      d.setDate(d.getDate() - i);
      axis.push(`${d.getMonth() + 1}/${d.getDate()}`);
    } else if (timeGranularity.value === 'week') {
      d.setDate(d.getDate() - i * 7);
      axis.push(`第${Math.ceil((d.getDate()) / 7)}周`);
    } else {
      d.setMonth(d.getMonth() - i);
      axis.push(`${d.getMonth() + 1}月`);
    }
  }
  return axis;
}

// 初始化情感得分趋势图
function initScoreTrendChart() {
  const dom = document.getElementById('score-trend-chart');
  if (!dom) return;

  scoreTrendChart = echarts.init(dom);
  const timeAxis = generateTimeAxis();
  const scoreData = timeAxis.map(() => (Math.random() * 0.6 - 0.1).toFixed(2));
  const upperBound = scoreData.map(s => (parseFloat(s) + 0.15).toFixed(2));
  const lowerBound = scoreData.map(s => (parseFloat(s) - 0.15).toFixed(2));

  const series: any[] = [
    {
      name: '情感得分',
      type: 'line',
      smooth: true,
      data: scoreData,
      itemStyle: { color: '#409eff' },
      lineStyle: { width: 3 },
      symbol: 'circle',
      symbolSize: 8,
    }
  ];

  // 置信区间
  if (showConfidenceInterval.value) {
    series.push({
      name: '置信上界',
      type: 'line',
      smooth: true,
      data: upperBound,
      lineStyle: { opacity: 0 },
      stack: 'confidence',
      symbol: 'none',
    });
    series.push({
      name: '置信区间',
      type: 'line',
      smooth: true,
      data: lowerBound.map((v, i) => (parseFloat(upperBound[i]) - parseFloat(v)).toFixed(2)),
      lineStyle: { opacity: 0 },
      areaStyle: { color: 'rgba(64, 158, 255, 0.2)' },
      stack: 'confidence',
      symbol: 'none',
    });
  }

  // 异常点标注
  const markPoints = showAnomalies.value ? {
    data: [
      { name: '异常高点', coord: [timeAxis[5], scoreData[5]], itemStyle: { color: '#67c23a' } },
      { name: '异常低点', coord: [timeAxis[9], scoreData[9]], itemStyle: { color: '#f56c6c' } },
    ],
    symbol: 'pin',
    symbolSize: 40,
    label: { show: true, formatter: '{b}' }
  } : undefined;

  scoreTrendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0];
        return `${p.axisValue}<br/>情感得分: <b>${p.value}</b>`;
      }
    },
    legend: { show: false },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: timeAxis, boundaryGap: false },
    yAxis: { type: 'value', name: '得分', min: -1, max: 1, splitNumber: 4 },
    series: series,
    markPoint: markPoints,
  });
}

// 初始化堆叠面积图
function initSentimentAreaChart() {
  const dom = document.getElementById('sentiment-area-chart');
  if (!dom) return;

  sentimentAreaChart = echarts.init(dom);
  const timeAxis = generateTimeAxis();
  
  const positiveData = timeAxis.map(() => Math.floor(Math.random() * 500 + 300));
  const neutralData = timeAxis.map(() => Math.floor(Math.random() * 300 + 200));
  const negativeData = timeAxis.map(() => Math.floor(Math.random() * 200 + 100));

  sentimentAreaChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['正面', '中性', '负面'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: timeAxis, boundaryGap: false },
    yAxis: { type: 'value', name: areaChartMode.value === 'percent' ? '占比(%)' : '数量' },
    series: [
      {
        name: '正面',
        type: 'line',
        stack: 'total',
        areaStyle: { color: 'rgba(103, 194, 58, 0.6)' },
        lineStyle: { color: '#67c23a' },
        data: areaChartMode.value === 'percent' 
          ? positiveData.map((v, i) => ((v / (v + neutralData[i] + negativeData[i])) * 100).toFixed(1))
          : positiveData,
      },
      {
        name: '中性',
        type: 'line',
        stack: 'total',
        areaStyle: { color: 'rgba(144, 147, 153, 0.6)' },
        lineStyle: { color: '#909399' },
        data: areaChartMode.value === 'percent'
          ? neutralData.map((v, i) => ((v / (positiveData[i] + v + negativeData[i])) * 100).toFixed(1))
          : neutralData,
      },
      {
        name: '负面',
        type: 'line',
        stack: 'total',
        areaStyle: { color: 'rgba(245, 108, 108, 0.6)' },
        lineStyle: { color: '#f56c6c' },
        data: areaChartMode.value === 'percent'
          ? negativeData.map((v, i) => ((v / (positiveData[i] + neutralData[i] + v)) * 100).toFixed(1))
          : negativeData,
      },
    ],
  });
}

// 初始化波动率图表
function initVolatilityChart() {
  const dom = document.getElementById('volatility-chart');
  if (!dom) return;

  volatilityChart = echarts.init(dom);
  const timeAxis = generateTimeAxis();
  const volatilityData = timeAxis.map(() => (Math.random() * 0.3 + 0.1).toFixed(2));

  volatilityChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: timeAxis },
    yAxis: { type: 'value', name: '标准差', max: 0.5 },
    visualMap: {
      show: false,
      pieces: [
        { lte: 0.15, color: '#67c23a' },
        { gt: 0.15, lte: 0.25, color: '#e6a23c' },
        { gt: 0.25, color: '#f56c6c' },
      ],
    },
    series: [{
      type: 'bar',
      data: volatilityData,
      barWidth: '50%',
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    }],
  });
}

// 初始化时间相关性图表
function initTimeCorrelationChart() {
  const dom = document.getElementById('time-correlation-chart');
  if (!dom) return;

  timeCorrelationChart = echarts.init(dom);
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const positiveData = hours.map((_, i) => {
    // 模拟：白天正面情感较多
    if (i >= 9 && i <= 18) return Math.floor(Math.random() * 30 + 50);
    return Math.floor(Math.random() * 20 + 20);
  });
  const negativeData = hours.map((_, i) => {
    // 模拟：晚间负面情感较多
    if (i >= 20 || i <= 2) return Math.floor(Math.random() * 20 + 30);
    return Math.floor(Math.random() * 15 + 10);
  });

  timeCorrelationChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '负面'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '20%', top: '10%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: hours,
      axisLabel: { interval: 3, fontSize: 10 }
    },
    yAxis: { type: 'value', name: '占比%', max: 100 },
    series: [
      {
        name: '正面',
        type: 'bar',
        stack: 'total',
        data: positiveData,
        itemStyle: { color: '#67c23a' },
      },
      {
        name: '负面',
        type: 'bar',
        stack: 'total',
        data: negativeData,
        itemStyle: { color: '#f56c6c' },
      },
    ],
  });
}

// 初始化关键词热力图
function initKeywordHeatmap() {
  const dom = document.getElementById('keyword-heatmap');
  if (!dom) return;

  keywordHeatmap = echarts.init(dom);
  const keywords = ['产品', '服务', '价格', '质量', '物流', '客服', '体验', '推荐'];
  const sentiments = ['正面', '中性', '负面'];
  
  const data: [number, number, number][] = [];
  keywords.forEach((_, ki) => {
    sentiments.forEach((_, si) => {
      data.push([ki, si, Math.floor(Math.random() * 100)]);
    });
  });

  keywordHeatmap.setOption({
    tooltip: {
      position: 'top',
      formatter: (params: any) => `${keywords[params.data[0]]} - ${sentiments[params.data[1]]}: ${params.data[2]}条`
    },
    grid: { left: '15%', right: '10%', bottom: '15%', top: '5%' },
    xAxis: { type: 'category', data: keywords, axisLabel: { fontSize: 10, rotate: 45 } },
    yAxis: { type: 'category', data: sentiments },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 10,
      itemHeight: 60,
      inRange: { color: ['#f5f5f5', '#67c23a'] }
    },
    series: [{
      type: 'heatmap',
      data: data,
      label: { show: true, fontSize: 10 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
    }],
  });
}

// 初始化预测图表
function initPredictionChart() {
  const dom = document.getElementById('prediction-chart');
  if (!dom) return;

  predictionChart = echarts.init(dom);
  const historyDays = ['12/08', '12/09', '12/10'];
  const futureDays = ['12/11', '12/12', '12/13', '12/14', '12/15', '12/16', '12/17'];
  const allDays = [...historyDays, ...futureDays];
  
  const historyData = [0.25, 0.28, 0.32];
  const predictedData = [null, null, 0.32, 0.35, 0.38, 0.36, 0.40, 0.42, 0.45];
  const upperBound = predictedData.map(v => v ? (v + 0.1).toFixed(2) : null);
  const lowerBound = predictedData.map(v => v ? (v - 0.1).toFixed(2) : null);

  predictionChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史数据', '预测值'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '20%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: allDays, boundaryGap: false },
    yAxis: { type: 'value', min: 0, max: 0.6 },
    series: [
      {
        name: '历史数据',
        type: 'line',
        data: [...historyData, ...Array(futureDays.length).fill(null)],
        itemStyle: { color: '#409eff' },
        lineStyle: { width: 2 },
      },
      {
        name: '预测值',
        type: 'line',
        data: predictedData,
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
        data: lowerBound.map((v, i) => v && upperBound[i] ? (parseFloat(upperBound[i]!) - parseFloat(v)).toFixed(2) : null),
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(230, 162, 60, 0.2)' },
        stack: 'confidence',
        symbol: 'none',
      },
    ],
  });
}

// 事件处理
function handleGranularityChange() {
  nextTick(() => {
    initScoreTrendChart();
    initSentimentAreaChart();
    initVolatilityChart();
  });
}

async function handlePredict() {
  predicting.value = true;
  ElMessage.info('正在生成趋势预测...');
  
  // 模拟预测过程
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  predictionData.value = [
    { day: '12/11', score: 0.35, upper: 0.45, lower: 0.25 },
    { day: '12/12', score: 0.38, upper: 0.48, lower: 0.28 },
    { day: '12/13', score: 0.36, upper: 0.46, lower: 0.26 },
    { day: '12/14', score: 0.40, upper: 0.50, lower: 0.30 },
    { day: '12/15', score: 0.42, upper: 0.52, lower: 0.32 },
    { day: '12/16', score: 0.45, upper: 0.55, lower: 0.35 },
    { day: '12/17', score: 0.48, upper: 0.58, lower: 0.38 },
  ];
  predictionTrend.value = 15.2;
  predictionConfidence.value = 85;
  predictionDays.value = 7;
  
  predicting.value = false;
  ElMessage.success('预测完成！');
  
  nextTick(() => {
    initPredictionChart();
  });
}

function handleExport() {
  ElMessage.success('数据导出中...');
}

function showAnomalyDetail(point: any) {
  selectedAnomaly.value = point;
  anomalyDialogVisible.value = true;
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { '正面': 'success', '中性': 'info', '负面': 'danger' };
  return map[sentiment] || 'info';
}

// 监听配置变化
watch([showConfidenceInterval, showAnomalies], () => {
  nextTick(() => initScoreTrendChart());
});

watch(areaChartMode, () => {
  nextTick(() => initSentimentAreaChart());
});

// 窗口大小变化
function handleResize() {
  scoreTrendChart?.resize();
  sentimentAreaChart?.resize();
  volatilityChart?.resize();
  timeCorrelationChart?.resize();
  keywordHeatmap?.resize();
  predictionChart?.resize();
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initScoreTrendChart();
    initSentimentAreaChart();
    initVolatilityChart();
    initTimeCorrelationChart();
    initKeywordHeatmap();
  });
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  scoreTrendChart?.dispose();
  sentimentAreaChart?.dispose();
  volatilityChart?.dispose();
  timeCorrelationChart?.dispose();
  keywordHeatmap?.dispose();
  predictionChart?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.sentiment-trend {
  padding: 15px;
}

/* 控制栏 */
.trend-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.control-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-label {
  font-size: 13px;
  color: #606266;
}

.control-right {
  display: flex;
  gap: 10px;
}

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

.header-options {
  display: flex;
  gap: 15px;
}

/* 异常点列表 */
.anomaly-list {
  padding: 10px 15px;
  background: #fef0f0;
  border-radius: 4px;
  margin-top: 10px;
}

.anomaly-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  color: #f56c6c;
  margin-bottom: 10px;
}

.anomaly-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: #fff;
  border-radius: 4px;
  margin-bottom: 5px;
  cursor: pointer;
  transition: background 0.2s;
}
.anomaly-item:hover {
  background: #f5f7fa;
}

.anomaly-time {
  font-size: 12px;
  color: #909399;
  width: 80px;
}

.anomaly-change {
  font-size: 13px;
  font-weight: 500;
  width: 60px;
}
.anomaly-change.up { color: #67c23a; }
.anomaly-change.down { color: #f56c6c; }

.anomaly-reason {
  font-size: 12px;
  color: #606266;
  flex: 1;
}

/* 相关性洞察 */
.correlation-insight {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  background: #ecf5ff;
  border-radius: 4px;
  margin-top: 10px;
  font-size: 12px;
  color: #409eff;
}

/* 预测卡片 */
.prediction-card {
  border: 2px solid #e6a23c;
}

.prediction-summary {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
  border-top: 1px solid #ebeef5;
}

.prediction-item {
  text-align: center;
}

.pred-label {
  font-size: 12px;
  color: #909399;
  display: block;
}

.pred-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
.pred-value.up { color: #67c23a; }
.pred-value.down { color: #f56c6c; }

/* 异常详情弹窗 */
.anomaly-detail {
  padding: 10px 0;
}

.anomaly-keywords {
  margin-top: 15px;
}

.keywords-title, .samples-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}

.anomaly-samples {
  margin-top: 15px;
}

.sample-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 5px;
}

.sample-content {
  font-size: 13px;
  color: #606266;
}

.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
</style>
