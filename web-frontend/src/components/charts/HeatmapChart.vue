<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  title?: string;
  xAxisData?: string[];
  yAxisData?: string[];
  data?: number[][];
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function getOption(): echarts.EChartsOption {
  const data = props.data || [];
  const maxValue = Math.max(...data.map(d => d[2] || 0), 1);

  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : undefined,
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const xLabel = props.xAxisData?.[params.value[0]] || params.value[0];
        const yLabel = props.yAxisData?.[params.value[1]] || params.value[1];
        return `${xLabel} - ${yLabel}: ${params.value[2]}`;
      },
    },
    grid: {
      left: '3%',
      right: '10%',
      bottom: '3%',
      top: props.title ? '15%' : '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: props.xAxisData || [],
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: props.yAxisData || [],
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      calculable: true,
      orient: 'vertical',
      right: '2%',
      top: 'center',
      inRange: {
        color: ['#f0f9e8', '#bae4bc', '#7bccc4', '#43a2ca', '#0868ac'],
      },
    },
    series: [{
      type: 'heatmap',
      data: data,
      label: { show: true },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
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

watch(() => [props.title, props.xAxisData, props.yAxisData, props.data], updateChart, { deep: true });

defineExpose({ resize: handleResize });
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
