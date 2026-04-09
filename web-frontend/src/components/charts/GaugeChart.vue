<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  title?: string;
  value?: number;
  min?: number;
  max?: number;
  unit?: string;
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function getOption(): echarts.EChartsOption {
  const min = props.min ?? 0;
  const max = props.max ?? 100;
  const value = props.value ?? 0;

  return {
    series: [{
      type: 'gauge',
      min,
      max,
      progress: { show: true, width: 18 },
      axisLine: {
        lineStyle: { width: 18 },
      },
      axisTick: { show: false },
      splitLine: {
        length: 15,
        lineStyle: { width: 2, color: '#999' },
      },
      axisLabel: {
        distance: 25,
        color: '#999',
        fontSize: 12,
      },
      anchor: {
        show: true,
        showAbove: true,
        size: 25,
        itemStyle: { borderWidth: 10 },
      },
      title: {
        show: true,
        offsetCenter: [0, '70%'],
        fontSize: 14,
      },
      detail: {
        valueAnimation: true,
        fontSize: 24,
        offsetCenter: [0, '40%'],
        formatter: `{value}${props.unit || ''}`,
      },
      data: [{
        value,
        name: props.title || '',
      }],
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

watch(() => [props.title, props.value, props.min, props.max, props.unit], updateChart, { deep: true });

defineExpose({ resize: handleResize });
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 150px;
}
</style>
