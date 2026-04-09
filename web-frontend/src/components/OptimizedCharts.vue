<template>
  <div class="optimized-charts">
    <!-- 情感分布饼图 -->
    <div v-if="type === 'sentiment-pie'" class="chart-container" ref="pieChart"></div>
    
    <!-- 热度趋势折线图 -->
    <div v-if="type === 'heat-trend'" class="chart-container" ref="trendChart"></div>
    
    <!-- 双维度散点图 -->
    <div v-if="type === 'dual-scatter'" class="chart-container" ref="scatterChart"></div>
    
    <!-- 四象限分布图 -->
    <div v-if="type === 'quadrant'" class="chart-container quadrant-chart" ref="quadrantChart"></div>
    
    <!-- 词云图 -->
    <div v-if="type === 'wordcloud'" class="chart-container" ref="wordcloudChart"></div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import * as echarts from 'echarts';

// Props
const props = defineProps<{
  type: 'sentiment-pie' | 'heat-trend' | 'dual-scatter' | 'quadrant' | 'wordcloud';
  data: any;
  title?: string;
  height?: string;
  theme?: 'light' | 'dark';
  autoRefresh?: boolean;
  refreshInterval?: number;
}>();

// Emits
const emit = defineEmits<{
  (e: 'click', data: any): void;
  (e: 'loaded'): void;
}>();

// Refs
const pieChart = ref<HTMLElement>();
const trendChart = ref<HTMLElement>();
const scatterChart = ref<HTMLElement>();
const quadrantChart = ref<HTMLElement>();
const wordcloudChart = ref<HTMLElement>();

const loading = ref(true);
let chartInstance: echarts.ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;
let refreshTimer: number | null = null;

// 主题配置
const themeColors = computed(() => ({
  positive: props.theme === 'dark' ? '#67C23A' : '#52c41a',
  neutral: props.theme === 'dark' ? '#909399' : '#8c8c8c',
  negative: props.theme === 'dark' ? '#F56C6C' : '#f5222d',
  primary: props.theme === 'dark' ? '#409EFF' : '#1890ff',
  background: props.theme === 'dark' ? '#1a1a2e' : '#ffffff',
  text: props.theme === 'dark' ? '#e0e0e0' : '#333333',
}));

// 初始化图表
onMounted(() => {
  initChart();
  setupResizeObserver();
  
  if (props.autoRefresh && props.refreshInterval) {
    refreshTimer = window.setInterval(() => {
      updateChart();
    }, props.refreshInterval);
  }
});

// 清理
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
});

// 监听数据变化
watch(() => props.data, () => {
  updateChart();
}, { deep: true });

// 初始化图表
function initChart() {
  const container = getChartContainer();
  if (!container) return;
  
  chartInstance = echarts.init(container, props.theme === 'dark' ? 'dark' : undefined);
  updateChart();
  
  // 点击事件
  chartInstance.on('click', (params: any) => {
    emit('click', params);
  });
}

// 获取图表容器
function getChartContainer(): HTMLElement | undefined {
  switch (props.type) {
    case 'sentiment-pie': return pieChart.value;
    case 'heat-trend': return trendChart.value;
    case 'dual-scatter': return scatterChart.value;
    case 'quadrant': return quadrantChart.value;
    case 'wordcloud': return wordcloudChart.value;
    default: return undefined;
  }
}

// 设置ResizeObserver
function setupResizeObserver() {
  const container = getChartContainer();
  if (!container) return;
  
  resizeObserver = new ResizeObserver(() => {
    chartInstance?.resize();
  });
  resizeObserver.observe(container);
}

// 更新图表
function updateChart() {
  if (!chartInstance || !props.data) {
    loading.value = false;
    return;
  }
  
  loading.value = true;
  
  let options: echarts.EChartsOption;
  
  switch (props.type) {
    case 'sentiment-pie':
      options = getSentimentPieOptions();
      break;
    case 'heat-trend':
      options = getHeatTrendOptions();
      break;
    case 'dual-scatter':
      options = getDualScatterOptions();
      break;
    case 'quadrant':
      options = getQuadrantOptions();
      break;
    case 'wordcloud':
      options = getWordCloudOptions();
      break;
    default:
      options = {};
  }
  
  chartInstance.setOption(options, true);
  loading.value = false;
  emit('loaded');
}

// 情感分布饼图配置
function getSentimentPieOptions(): echarts.EChartsOption {
  const { positive = 0, neutral = 0, negative = 0 } = props.data || {};
  
  return {
    title: {
      text: props.title || '情感分布',
      left: 'center',
      textStyle: { color: themeColors.value.text },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      textStyle: { color: themeColors.value.text },
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: themeColors.value.background,
        borderWidth: 2,
      },
      label: {
        show: true,
        formatter: '{b}\n{d}%',
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      data: [
        { value: positive, name: '正面', itemStyle: { color: themeColors.value.positive } },
        { value: neutral, name: '中性', itemStyle: { color: themeColors.value.neutral } },
        { value: negative, name: '负面', itemStyle: { color: themeColors.value.negative } },
      ],
    }],
  };
}

// 热度趋势折线图配置
function getHeatTrendOptions(): echarts.EChartsOption {
  const { dates = [], values = [], sentiment = [] } = props.data || {};
  
  return {
    title: {
      text: props.title || '热度趋势',
      left: 'center',
      textStyle: { color: themeColors.value.text },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['热度', '情感均值'],
      top: 30,
      textStyle: { color: themeColors.value.text },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 80,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: { color: themeColors.value.text },
    },
    yAxis: [
      {
        type: 'value',
        name: '热度',
        axisLabel: { color: themeColors.value.text },
      },
      {
        type: 'value',
        name: '情感',
        min: -1,
        max: 1,
        axisLabel: { color: themeColors.value.text },
      },
    ],
    series: [
      {
        name: '热度',
        type: 'line',
        smooth: true,
        data: values,
        lineStyle: { width: 3 },
        areaStyle: {
          opacity: 0.3,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: themeColors.value.primary },
            { offset: 1, color: 'transparent' },
          ]),
        },
      },
      {
        name: '情感均值',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: sentiment,
        lineStyle: { 
          width: 2,
          type: 'dashed',
        },
        itemStyle: { color: themeColors.value.positive },
      },
    ],
  };
}

// 双维度散点图配置
function getDualScatterOptions(): echarts.EChartsOption {
  const items = props.data || [];
  
  // 转换数据格式: [情感, 热度, 大小, 名称, 极性]
  const scatterData = items.map((item: any) => [
    item.sentiment_score || item.scores?.sentiment_intensity || 0,
    item.heat_score || item.scores?.heat_score || 0,
    Math.sqrt(item.interactions?.total || item.attitudes_count || 100),
    item.text?.slice(0, 20) || '',
    item.quadrant || 'neutral',
  ]);
  
  return {
    title: {
      text: props.title || '情感-热度分布',
      left: 'center',
      textStyle: { color: themeColors.value.text },
    },
    tooltip: {
      formatter: (params: any) => {
        const data = params.data;
        return `
          <div style="padding: 8px;">
            <div style="font-weight: bold;">${data[3]}...</div>
            <div>情感: ${data[0].toFixed(2)}</div>
            <div>热度: ${data[1].toFixed(2)}</div>
          </div>
        `;
      },
    },
    grid: {
      left: '10%',
      right: '10%',
      top: 60,
      bottom: 60,
    },
    xAxis: {
      name: '情感强度',
      nameLocation: 'middle',
      nameGap: 30,
      type: 'value',
      min: -1,
      max: 1,
      axisLabel: { color: themeColors.value.text },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      name: '热度',
      nameLocation: 'middle',
      nameGap: 40,
      type: 'value',
      axisLabel: { color: themeColors.value.text },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [{
      type: 'scatter',
      symbolSize: (data: any) => Math.max(10, Math.min(50, data[2])),
      data: scatterData,
      itemStyle: {
        color: (params: any) => {
          const sentiment = params.data[0];
          if (sentiment > 0.2) return themeColors.value.positive;
          if (sentiment < -0.2) return themeColors.value.negative;
          return themeColors.value.neutral;
        },
        opacity: 0.7,
      },
      emphasis: {
        itemStyle: { opacity: 1 },
      },
    }],
    // 添加四象限分割线
    markLine: {
      silent: true,
      data: [
        { xAxis: 0 },
        { yAxis: 5 },
      ],
      lineStyle: {
        color: '#999',
        type: 'dashed',
      },
    },
  };
}

// 四象限分布图配置
function getQuadrantOptions(): echarts.EChartsOption {
  const { 
    high_sentiment_high_heat = 0,
    high_sentiment_low_heat = 0,
    low_sentiment_high_heat = 0,
    low_sentiment_low_heat = 0,
  } = props.data || {};
  
  const total = high_sentiment_high_heat + high_sentiment_low_heat + 
                low_sentiment_high_heat + low_sentiment_low_heat || 1;
  
  return {
    title: {
      text: props.title || '四象限分布',
      left: 'center',
      textStyle: { color: themeColors.value.text },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    series: [{
      type: 'pie',
      radius: '65%',
      center: ['50%', '55%'],
      roseType: 'area',
      itemStyle: {
        borderRadius: 8,
      },
      label: {
        formatter: '{b}\n{d}%',
      },
      data: [
        { 
          value: high_sentiment_high_heat, 
          name: '高情感高热度',
          itemStyle: { color: '#ff6b6b' },
        },
        { 
          value: high_sentiment_low_heat, 
          name: '高情感低热度',
          itemStyle: { color: '#ffa94d' },
        },
        { 
          value: low_sentiment_high_heat, 
          name: '低情感高热度',
          itemStyle: { color: '#69db7c' },
        },
        { 
          value: low_sentiment_low_heat, 
          name: '低情感低热度',
          itemStyle: { color: '#748ffc' },
        },
      ],
    }],
  };
}

// 词云图配置
function getWordCloudOptions(): echarts.EChartsOption {
  const words = props.data || [];
  
  return {
    title: {
      text: props.title || '热门词汇',
      left: 'center',
      textStyle: { color: themeColors.value.text },
    },
    tooltip: {
      show: true,
      formatter: (params: any) => `${params.name}: ${params.value}`,
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '80%',
      sizeRange: [14, 60],
      rotationRange: [-45, 45],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => {
          const colors = [
            themeColors.value.primary,
            themeColors.value.positive,
            themeColors.value.negative,
            '#9c27b0',
            '#ff9800',
          ];
          return colors[Math.floor(Math.random() * colors.length)];
        },
      },
      emphasis: {
        textStyle: {
          shadowBlur: 10,
          shadowColor: '#333',
        },
      },
      data: words.map((w: any) => ({
        name: w.name || w.word,
        value: w.value || w.count,
      })),
    }],
  };
}

// 公开方法
defineExpose({
  refresh: updateChart,
  resize: () => chartInstance?.resize(),
  getInstance: () => chartInstance,
});
</script>

<style scoped lang="scss">
.optimized-charts {
  position: relative;
  width: 100%;
  height: v-bind('props.height || "400px"');
  
  .chart-container {
    width: 100%;
    height: 100%;
  }
  
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.8);
    z-index: 10;
    
    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid #f3f3f3;
      border-top: 3px solid #3498db;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 10px;
    }
    
    span {
      color: #666;
      font-size: 14px;
    }
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>

