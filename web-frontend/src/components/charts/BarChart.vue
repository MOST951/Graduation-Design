<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  title?: string;
  xAxisData?: string[];
  seriesData?: number[];
  showLegend?: boolean;
  colorScheme?: string;
  horizontal?: boolean;
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

const colors = computed(() => {
  const schemes: Record<string, string[]> = {
    default: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'],
    warm: ['#ff7f50', '#ff6347', '#ff4500', '#ffa500', '#ffd700'],
    cool: ['#00ced1', '#20b2aa', '#48d1cc', '#40e0d0', '#00ffff'],
    sentiment: ['#67C23A', '#F56C6C', '#909399'],
  };
  return schemes[props.colorScheme || 'default'] || schemes.default;
});

function getOption(): echarts.EChartsOption {
  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : undefined,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: props.showLegend ? { bottom: 0 } : undefined,
    grid: {
      left: '3%',
      right: '4%',
      bottom: props.showLegend ? '15%' : '3%',
      top: props.title ? '15%' : '3%',
      containLabel: true,
    },
    xAxis: props.horizontal ? {
      type: 'value',
    } : {
      type: 'category',
      data: props.xAxisData || [],
      axisLabel: { rotate: 30 },
    },
    yAxis: props.horizontal ? {
      type: 'category',
      data: props.xAxisData || [],
    } : {
      type: 'value',
    },
    series: [{
      type: 'bar',
      data: props.seriesData || [],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: colors.value[0] },
          { offset: 1, color: colors.value[1] || colors.value[0] },
        ]),
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
      },
    }],
  };
}

function initChart() {
  if (!chartRef.value) return;
  
  chart = echarts.init(chartRef.value);
  chart.setOption(getOption());
}

function updateChart() {
  if (chart) {
    chart.setOption(getOption());
  }
}

function handleResize() {
  chart?.resize();
}

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chart?.dispose();
});

watch(() => [props.title, props.xAxisData, props.seriesData, props.showLegend, props.colorScheme, props.horizontal], updateChart, { deep: true });

defineExpose({ resize: handleResize });
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 150px;
}
</style>
