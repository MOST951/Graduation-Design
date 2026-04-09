<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  title?: string;
  xAxisData?: string[];
  seriesData?: number[] | { name: string; data: number[] }[];
  smooth?: boolean;
  showArea?: boolean;
  showLegend?: boolean;
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function getOption(): echarts.EChartsOption {
  const isMultiSeries = Array.isArray(props.seriesData) && props.seriesData.length > 0 && typeof props.seriesData[0] === 'object';
  
  const series = isMultiSeries
    ? (props.seriesData as { name: string; data: number[] }[]).map((s, i) => ({
        name: s.name,
        type: 'line' as const,
        data: s.data,
        smooth: props.smooth,
        areaStyle: props.showArea ? { opacity: 0.3 } : undefined,
      }))
    : [{
        type: 'line' as const,
        data: props.seriesData as number[] || [],
        smooth: props.smooth,
        areaStyle: props.showArea ? {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(84, 112, 198, 0.5)' },
            { offset: 1, color: 'rgba(84, 112, 198, 0.1)' },
          ]),
        } : undefined,
      }];

  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : undefined,
    tooltip: {
      trigger: 'axis',
    },
    legend: props.showLegend && isMultiSeries ? { bottom: 0 } : undefined,
    grid: {
      left: '3%',
      right: '4%',
      bottom: props.showLegend && isMultiSeries ? '15%' : '3%',
      top: props.title ? '15%' : '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: props.xAxisData || [],
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
    },
    series,
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

watch(() => [props.title, props.xAxisData, props.seriesData, props.smooth, props.showArea, props.showLegend], updateChart, { deep: true });

defineExpose({ resize: handleResize });
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 150px;
}
</style>
