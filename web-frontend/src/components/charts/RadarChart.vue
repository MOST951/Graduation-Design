<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  title?: string;
  indicator?: { name: string; max: number }[];
  data?: number[];
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function getOption(): echarts.EChartsOption {
  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : undefined,
    tooltip: {
      trigger: 'item',
    },
    radar: {
      indicator: props.indicator || [],
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#666',
      },
      splitLine: {
        lineStyle: { color: ['#e4e7ed'] },
      },
      splitArea: {
        show: true,
        areaStyle: { color: ['rgba(64, 158, 255, 0.1)', 'rgba(64, 158, 255, 0.2)'] },
      },
    },
    series: [{
      type: 'radar',
      data: [{
        value: props.data || [],
        name: props.title || '数据',
        areaStyle: {
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' },
          ]),
        },
        lineStyle: { color: '#409EFF', width: 2 },
        itemStyle: { color: '#409EFF' },
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

watch(() => [props.title, props.indicator, props.data], updateChart, { deep: true });

defineExpose({ resize: handleResize });
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
