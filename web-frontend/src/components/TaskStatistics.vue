<template>
  <div class="task-statistics">
    <!-- 时间选择器 -->
    <div class="time-selector">
      <el-radio-group v-model="timeRange" @change="handleTimeChange">
        <el-radio-button label="today">今天</el-radio-button>
        <el-radio-button label="yesterday">昨天</el-radio-button>
        <el-radio-button label="week">近7天</el-radio-button>
        <el-radio-button label="month">近30天</el-radio-button>
        <el-radio-button label="custom">自定义</el-radio-button>
      </el-radio-group>
      <el-date-picker
        v-if="timeRange === 'custom'"
        v-model="customDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="margin-left: 15px;"
        @change="handleCustomDateChange"
      />
      <el-button type="primary" :icon="Refresh" circle style="margin-left: 15px;" @click="refreshData" />
    </div>

    <!-- 统计指标卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col v-for="card in statCards" :key="card.title" :xs="24" :sm="12" :md="6">
        <div class="stat-card" :class="card.type">
          <div class="stat-header">
            <span class="stat-title">{{ card.title }}</span>
            <el-icon :class="['trend-icon', card.trend > 0 ? 'up' : 'down']">
              <component :is="card.trend > 0 ? CaretTop : CaretBottom" />
            </el-icon>
          </div>
          <div class="stat-value">{{ formatValue(card.value, card.format) }}</div>
          <div class="stat-footer">
            <span :class="['trend-text', card.trend > 0 ? 'up' : 'down']">
              {{ card.trend > 0 ? '+' : '' }}{{ card.trend }}%
            </span>
            <span class="compare-text">较昨日</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <!-- 每日任务执行折线图 -->
      <el-col :xs="24" :lg="14">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>每日任务执行情况</span>
              <el-button-group size="small">
                <el-button :type="lineChartType === 'count' ? 'primary' : ''" @click="lineChartType = 'count'">任务数</el-button>
                <el-button :type="lineChartType === 'data' ? 'primary' : ''" @click="lineChartType = 'data'">数据量</el-button>
              </el-button-group>
            </div>
          </template>
          <div id="line-chart" style="width: 100%; height: 320px;"></div>
        </el-card>
      </el-col>

      <!-- 平台分布玫瑰图 -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <span>平台任务分布</span>
          </template>
          <div id="rose-chart" style="width: 100%; height: 320px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 时长分布柱状图 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="24">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>任务执行时长分布</span>
              <el-tag type="info" size="small">单位：分钟</el-tag>
            </div>
          </template>
          <div id="bar-chart" style="width: 100%; height: 280px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { Refresh, CaretTop, CaretBottom } from '@element-plus/icons-vue';

// 时间选择
const timeRange = ref('week');
const customDateRange = ref<[Date, Date] | null>(null);

// 图表类型切换
const lineChartType = ref<'count' | 'data'>('count');

// 统计卡片数据
const statCards = ref([
  { title: '总任务数', value: 156, trend: 12.5, type: 'primary', format: 'number' },
  { title: '运行中任务', value: 23, trend: -5.2, type: 'success', format: 'number' },
  { title: '成功率', value: 94.8, trend: 2.3, type: 'warning', format: 'percent' },
  { title: '总数据量', value: 1258340, trend: 18.7, type: 'danger', format: 'number' },
]);

// 图表实例
let lineChart: echarts.ECharts | null = null;
let roseChart: echarts.ECharts | null = null;
let barChart: echarts.ECharts | null = null;

// 格式化数值
function formatValue(value: number, format: string) {
  if (format === 'percent') return value.toFixed(1) + '%';
  if (value >= 1000000) return (value / 1000000).toFixed(2) + 'M';
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
  return value.toString();
}

// 获取日期范围
function getDateRange() {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  
  switch (timeRange.value) {
    case 'today':
      return { start: today, end: now };
    case 'yesterday':
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      return { start: yesterday, end: today };
    case 'week':
      const weekAgo = new Date(today);
      weekAgo.setDate(weekAgo.getDate() - 7);
      return { start: weekAgo, end: now };
    case 'month':
      const monthAgo = new Date(today);
      monthAgo.setDate(monthAgo.getDate() - 30);
      return { start: monthAgo, end: now };
    case 'custom':
      if (customDateRange.value) {
        return { start: customDateRange.value[0], end: customDateRange.value[1] };
      }
      return { start: today, end: now };
    default:
      return { start: today, end: now };
  }
}

// 生成模拟数据
function generateMockData() {
  const { start, end } = getDateRange();
  const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) || 1;
  
  const dates: string[] = [];
  const successData: number[] = [];
  const failedData: number[] = [];
  const dataVolume: number[] = [];
  
  for (let i = 0; i < days; i++) {
    const date = new Date(start);
    date.setDate(date.getDate() + i);
    dates.push(`${date.getMonth() + 1}/${date.getDate()}`);
    
    const success = Math.floor(50 + Math.random() * 100);
    const failed = Math.floor(Math.random() * 15);
    successData.push(success);
    failedData.push(failed);
    dataVolume.push(Math.floor(success * (800 + Math.random() * 400)));
  }
  
  return { dates, successData, failedData, dataVolume };
}

// 初始化折线图
function initLineChart() {
  const chartDom = document.getElementById('line-chart');
  if (!chartDom) return;
  
  lineChart = echarts.init(chartDom);
  updateLineChart();
}

function updateLineChart() {
  if (!lineChart) return;
  
  const { dates, successData, failedData, dataVolume } = generateMockData();
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: lineChartType.value === 'count' ? ['成功任务', '失败任务'] : ['数据量'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#606266' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#ebeef5', type: 'dashed' } },
      axisLabel: { color: '#909399' }
    },
    series: lineChartType.value === 'count' ? [
      {
        name: '成功任务',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: successData,
        itemStyle: { color: '#67c23a' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
            { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
          ])
        }
      },
      {
        name: '失败任务',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: failedData,
        itemStyle: { color: '#f56c6c' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 108, 108, 0.3)' },
            { offset: 1, color: 'rgba(245, 108, 108, 0.05)' }
          ])
        }
      }
    ] : [
      {
        name: '数据量',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: dataVolume,
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ])
        }
      }
    ]
  };
  
  lineChart.setOption(option);
}

// 初始化玫瑰图
function initRoseChart() {
  const chartDom = document.getElementById('rose-chart');
  if (!chartDom) return;
  
  roseChart = echarts.init(chartDom);
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: 0,
      left: 'center'
    },
    series: [{
      type: 'pie',
      radius: ['20%', '70%'],
      center: ['50%', '45%'],
      roseType: 'area',
      itemStyle: {
        borderRadius: 8
      },
      label: {
        show: true,
        formatter: '{b}\n{d}%'
      },
      data: [
        { value: 68, name: '微博', itemStyle: { color: '#ff6b6b' } },
        { value: 45, name: '微信', itemStyle: { color: '#4ecdc4' } },
        { value: 32, name: '抖音', itemStyle: { color: '#45b7d1' } },
        { value: 18, name: '知乎', itemStyle: { color: '#96ceb4' } },
        { value: 12, name: '小红书', itemStyle: { color: '#ffeaa7' } }
      ]
    }]
  };
  
  roseChart.setOption(option);
}

// 初始化柱状图
function initBarChart() {
  const chartDom = document.getElementById('bar-chart');
  if (!chartDom) return;
  
  barChart = echarts.init(chartDom);
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: '{b}: {c} 个任务'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['<1分钟', '1-5分钟', '5-15分钟', '15-30分钟', '30-60分钟', '>60分钟'],
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#606266' }
    },
    yAxis: {
      type: 'value',
      name: '任务数',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#ebeef5', type: 'dashed' } },
      axisLabel: { color: '#909399' }
    },
    series: [{
      type: 'bar',
      barWidth: '50%',
      data: [
        { value: 45, itemStyle: { color: '#67c23a' } },
        { value: 78, itemStyle: { color: '#85ce61' } },
        { value: 52, itemStyle: { color: '#e6a23c' } },
        { value: 28, itemStyle: { color: '#f89898' } },
        { value: 15, itemStyle: { color: '#f56c6c' } },
        { value: 8, itemStyle: { color: '#c45656' } }
      ],
      label: {
        show: true,
        position: 'top',
        color: '#606266',
        fontSize: 12
      },
      itemStyle: {
        borderRadius: [4, 4, 0, 0]
      }
    }]
  };
  
  barChart.setOption(option);
}

// 事件处理
function handleTimeChange() {
  if (timeRange.value !== 'custom') {
    refreshData();
  }
}

function handleCustomDateChange() {
  if (customDateRange.value) {
    refreshData();
  }
}

function refreshData() {
  // 更新统计卡片（模拟数据变化）
  statCards.value = statCards.value.map(card => ({
    ...card,
    value: card.format === 'percent' 
      ? Number((90 + Math.random() * 8).toFixed(1))
      : Math.floor(card.value * (0.9 + Math.random() * 0.2)),
    trend: Number((Math.random() * 30 - 10).toFixed(1))
  }));
  
  // 更新图表
  updateLineChart();
  
  // 更新玫瑰图数据
  if (roseChart) {
    roseChart.setOption({
      series: [{
        data: [
          { value: Math.floor(50 + Math.random() * 30), name: '微博', itemStyle: { color: '#ff6b6b' } },
          { value: Math.floor(30 + Math.random() * 25), name: '微信', itemStyle: { color: '#4ecdc4' } },
          { value: Math.floor(20 + Math.random() * 20), name: '抖音', itemStyle: { color: '#45b7d1' } },
          { value: Math.floor(10 + Math.random() * 15), name: '知乎', itemStyle: { color: '#96ceb4' } },
          { value: Math.floor(5 + Math.random() * 12), name: '小红书', itemStyle: { color: '#ffeaa7' } }
        ]
      }]
    });
  }
  
  // 更新柱状图数据
  if (barChart) {
    barChart.setOption({
      series: [{
        data: [
          { value: Math.floor(30 + Math.random() * 30), itemStyle: { color: '#67c23a' } },
          { value: Math.floor(50 + Math.random() * 40), itemStyle: { color: '#85ce61' } },
          { value: Math.floor(30 + Math.random() * 35), itemStyle: { color: '#e6a23c' } },
          { value: Math.floor(15 + Math.random() * 25), itemStyle: { color: '#f89898' } },
          { value: Math.floor(8 + Math.random() * 15), itemStyle: { color: '#f56c6c' } },
          { value: Math.floor(3 + Math.random() * 10), itemStyle: { color: '#c45656' } }
        ]
      }]
    });
  }
}

// 监听图表类型切换
watch(lineChartType, () => {
  updateLineChart();
});

// 窗口大小变化时重绘图表
function handleResize() {
  lineChart?.resize();
  roseChart?.resize();
  barChart?.resize();
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initLineChart();
    initRoseChart();
    initBarChart();
  });
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  lineChart?.dispose();
  roseChart?.dispose();
  barChart?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.task-statistics {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

/* 时间选择器 */
.time-selector {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* 统计卡片 */
.stat-cards {
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
  border-left: 4px solid;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}
.stat-card.primary { border-left-color: #409eff; }
.stat-card.success { border-left-color: #67c23a; }
.stat-card.warning { border-left-color: #e6a23c; }
.stat-card.danger { border-left-color: #f56c6c; }

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.stat-title {
  font-size: 14px;
  color: #909399;
}
.trend-icon {
  font-size: 18px;
}
.trend-icon.up { color: #67c23a; }
.trend-icon.down { color: #f56c6c; }

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 10px;
}

.stat-footer {
  display: flex;
  align-items: center;
  gap: 8px;
}
.trend-text {
  font-size: 13px;
  font-weight: 500;
}
.trend-text.up { color: #67c23a; }
.trend-text.down { color: #f56c6c; }
.compare-text {
  font-size: 12px;
  color: #c0c4cc;
}

/* 图表区域 */
.chart-row {
  margin-bottom: 20px;
}
.chart-card {
  border-radius: 8px;
}
.chart-card :deep(.el-card__header) {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  font-weight: bold;
  color: #303133;
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
