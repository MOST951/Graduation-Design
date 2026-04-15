<template>
  <div class="dashboard">
    <!-- 1. 指标卡片 -->
    <div class="metric-grid">
      <div
        v-for="(card, idx) in overviewCards"
        :key="card.title"
        class="metric-card slide-up"
        :class="'stagger-' + (idx + 1)"
      >
        <div class="metric-icon-wrap" :style="{ background: card.color + '14' }">
          <i :class="card.icon" :style="{ color: card.color }"></i>
        </div>
        <div class="metric-body">
          <span class="metric-label">{{ card.title }}</span>
          <span class="metric-value">{{ formatNumber(card.value) }}</span>
          <span class="metric-trend" :class="card.trendClass">
            <i :class="card.trendIcon"></i>
            {{ card.trend }}
          </span>
        </div>
      </div>
    </div>

    <!-- 2. 双列: 情感分布 + 实时数据流 -->
    <div class="chart-grid">
      <div class="chart-card slide-up stagger-5">
        <div class="chart-card-header">
          <span class="chart-card-title">情感分布</span>
          <el-select v-model="sentimentPeriod" size="small" class="chart-select">
            <el-option label="今日" value="today" />
            <el-option label="本周" value="week" />
            <el-option label="本月" value="month" />
          </el-select>
        </div>
        <div ref="sentimentChartRef" class="chart-area"></div>
      </div>

      <div class="chart-card slide-up stagger-6">
        <div class="chart-card-header">
          <span class="chart-card-title">实时数据流</span>
          <span class="live-badge">
            <span class="live-dot"></span>
            实时
          </span>
        </div>
        <div class="realtime-stream">
          <transition-group name="stream-list" tag="div">
            <div v-for="item in realtimeData" :key="item.id" class="stream-item">
              <div class="stream-content">
                <span class="stream-text">{{ item.content }}</span>
                <el-tag
                  :type="getSentimentTagType(item.sentiment)"
                  size="small"
                  effect="light"
                  round
                >
                  {{ formatSentiment(item.sentiment) }}
                </el-tag>
              </div>
              <div class="stream-meta">
                <span class="stream-time">{{ formatTime(item.time) }}</span>
                <span class="stream-source">{{ item.source }}</span>
              </div>
            </div>
          </transition-group>
        </div>
      </div>
    </div>

    <!-- 3. 趋势分析 -->
    <div class="chart-card chart-card--full slide-up stagger-7">
      <div class="chart-card-header">
        <span class="chart-card-title">情感趋势分析</span>
        <el-date-picker
          v-model="trendDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
        />
      </div>
      <div ref="trendChartRef" class="chart-area chart-area--tall"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import { getDashboardData } from '@/api/dashboard';
import { formatTime, formatNumber } from '@/utils/formatter';

// --- 类型定义 ---
interface OverviewCard {
  title: string;
  value: string;
  icon: string;
  color: string;
  trend: string;
  trendIcon: string;
  trendClass: string;
}

interface RealtimeItem {
  id: string | number;
  content: string;
  sentiment: number;
  time: string | Date;
  source: string;
}

// --- Refs ---
const sentimentChartRef = ref<HTMLElement | null>(null);
const trendChartRef = ref<HTMLElement | null>(null);
const overviewCards = ref<OverviewCard[]>([]);
const sentimentPeriod = ref('today');
const trendDateRange = ref<[Date, Date]>([new Date(Date.now() - 7 * 24 * 3600 * 1000), new Date()]);
const realtimeData = ref<RealtimeItem[]>([]);

let sentimentChart: echarts.ECharts | null = null;
let trendChart: echarts.ECharts | null = null;

// --- 生命周期钩子 ---
onMounted(async () => {
  initCharts();
  await loadDashboardData();
  startRealtimeConnection();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  disconnectRealtime();
  sentimentChart?.dispose();
  trendChart?.dispose();
  window.removeEventListener('resize', handleResize);
});

// --- 数据加载方法 ---
async function loadDashboardData() {
  try {
    const response = await getDashboardData({
      period: sentimentPeriod.value,
      dateRange: trendDateRange.value,
    });
    if (response.overviewCards) overviewCards.value = response.overviewCards;
    if (response.sentimentDistribution) updateSentimentChart(response.sentimentDistribution);
    if (response.trendData) updateTrendChart(response.trendData);
  } catch (error) {
    console.error('加载仪表盘数据失败:', error);
  }
}

// --- ECharts 图表方法 ---
function initCharts() {
  if (sentimentChartRef.value) {
    sentimentChart = echarts.init(sentimentChartRef.value);
  }
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value);
  }
}

function updateSentimentChart(data: { positive: number; negative: number; neutral: number }) {
  sentimentChart?.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#F2F3F5',
      borderWidth: 1,
      textStyle: { color: '#1D2129', fontSize: 13 },
      extraCssText: 'border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.08);',
    },
    legend: {
      bottom: 8,
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 20,
      textStyle: { color: '#86909C', fontSize: 12 },
      icon: 'circle',
    },
    series: [
      {
        name: '情感分布',
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '45%'],
        padAngle: 2,
        itemStyle: { borderRadius: 6 },
        label: { show: false },
        emphasis: {
          scaleSize: 6,
          itemStyle: { shadowBlur: 16, shadowColor: 'rgba(0,0,0,0.12)' },
        },
        data: [
          { value: data.positive, name: '正面', itemStyle: { color: '#00B42A' } },
          { value: data.negative, name: '负面', itemStyle: { color: '#F53F3F' } },
          { value: data.neutral, name: '中性', itemStyle: { color: '#C9CDD4' } },
        ],
        animationType: 'scale',
        animationEasing: 'cubicOut',
      },
    ],
  });
}

function updateTrendChart(data: { dates: string[]; positive: number[]; negative: number[] }) {
  trendChart?.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#F2F3F5',
      borderWidth: 1,
      textStyle: { color: '#1D2129', fontSize: 13 },
      extraCssText: 'border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.08);',
    },
    legend: {
      data: ['正面指数', '负面指数'],
      right: 0,
      top: 0,
      itemWidth: 12,
      itemHeight: 3,
      itemGap: 20,
      textStyle: { color: '#86909C', fontSize: 12 },
    },
    grid: { left: 0, right: 0, top: 36, bottom: 0, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.dates,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#C9CDD4', fontSize: 11, margin: 12 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#F2F3F5', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#C9CDD4', fontSize: 11 },
    },
    series: [
      {
        name: '正面指数',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.5, color: '#00B42A' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 180, 42, 0.15)' },
            { offset: 1, color: 'rgba(0, 180, 42, 0)' },
          ]),
        },
        data: data.positive,
      },
      {
        name: '负面指数',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.5, color: '#F53F3F' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 63, 63, 0.12)' },
            { offset: 1, color: 'rgba(245, 63, 63, 0)' },
          ]),
        },
        data: data.negative,
      },
    ],
  });
}

// --- 实时数据 ---
let realtimeInterval: ReturnType<typeof setInterval> | null = null;

async function startRealtimeConnection() {
  // 从后端API获取真实微博数据
  console.log('获取真实微博实时数据...');
  
  // 立即加载一次数据
  await fetchRealtimeData();
  
  // 每30秒刷新一次数据
  realtimeInterval = setInterval(async () => {
    await fetchRealtimeData();
  }, 30000);
}

async function fetchRealtimeData() {
  try {
    const response = await fetch('/api/dashboard/realtime');
    const result = await response.json();
    
    if (result.code === 200 && result.data) {
      // 清空旧数据，使用新数据
      realtimeData.value = result.data.map((item: any) => ({
        id: item.id || Date.now() + Math.random(),
        content: item.content || '',
        sentiment: item.sentiment || 0,
        time: item.time || new Date().toISOString(),
        source: item.source || '微博',
        author: item.author || '',
      }));
    }
  } catch (error) {
    console.error('获取实时数据失败:', error);
  }
}

function addRealtimeData(data: RealtimeItem) {
  realtimeData.value.unshift(data);
  if (realtimeData.value.length > 20) {
    realtimeData.value.pop();
  }
}

function disconnectRealtime() {
  if (realtimeInterval) {
    clearInterval(realtimeInterval);
    realtimeInterval = null;
  }
}

// --- 工具与辅助函数 ---
function getSentimentTagType(score: number): string {
  if (score > 0.3) return 'success';
  if (score < -0.3) return 'danger';
  return 'info';
}

function formatSentiment(score: number): string {
  if (score > 0.3) return '积极';
  if (score < -0.3) return '消极';
  return '中性';
}

function handleResize() {
  sentimentChart?.resize();
  trendChart?.resize();
}

// --- 监听器 ---
watch(sentimentPeriod, loadDashboardData);
watch(trendDateRange, loadDashboardData);
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// ==================== 指标卡片 ====================
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  @media (max-width: 1200px) { grid-template-columns: repeat(2, 1fr); }
  @media (max-width: 600px) { grid-template-columns: 1fr; }
}

.metric-card {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: $border-radius-large;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.25s $ease-smooth;
  cursor: default;

  &:hover {
    border-color: $border-base;
    box-shadow: $shadow-sm;
    transform: translateY(-2px);
  }
}

.metric-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: $border-radius-medium;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.metric-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.metric-label {
  font-size: 13px;
  color: $text-secondary;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: $font-weight-bold;
  color: $text-primary;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.metric-trend {
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 2px;

  &.positive { color: $success-color; }
  &.negative { color: $danger-color; }
}

// ==================== 图表卡片 ====================
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;

  @media (max-width: 900px) { grid-template-columns: 1fr; }
}

.chart-card {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: $border-radius-large;
  padding: 20px 24px;
  transition: $transition-base;

  &:hover {
    border-color: $border-base;
    box-shadow: $shadow-sm;
  }

  &--full {
    width: 100%;
  }
}

.chart-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-card-title {
  font-size: 15px;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.chart-select {
  width: 90px;
}

.chart-area {
  width: 100%;
  height: 300px;
}

.chart-area--tall {
  height: 360px;
}

// ==================== 实时数据流 ====================
.live-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: $border-radius-round;
  background: rgba(0, 180, 42, 0.08);
  color: $success-color;
  font-size: 12px;
  font-weight: $font-weight-medium;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: $success-color;
  animation: pulse 1.5s ease-in-out infinite;
}

.realtime-stream {
  height: 300px;
  overflow-y: auto;
}

.stream-item {
  padding: 12px 0;
  border-bottom: 1px solid $border-lighter;
  transition: background 0.15s;

  &:last-child { border-bottom: none; }

  &:hover {
    background: $bg-hover;
    margin: 0 -12px;
    padding-left: 12px;
    padding-right: 12px;
    border-radius: 8px;
  }
}

.stream-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 6px;
}

.stream-text {
  flex: 1;
  font-size: 13px;
  line-height: 1.6;
  color: $text-primary;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.stream-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: $text-placeholder;
}

// 流列表动画
.stream-list-enter-active {
  transition: all 0.3s $ease-smooth;
}
.stream-list-leave-active {
  transition: all 0.2s $ease-smooth;
}
.stream-list-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}
.stream-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
.stream-list-move {
  transition: transform 0.3s $ease-smooth;
}
</style>
