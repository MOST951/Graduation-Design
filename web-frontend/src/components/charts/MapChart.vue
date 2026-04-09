<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  title?: string;
  mapType?: string;
  data?: { name: string; value: number }[];
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

// 注意：实际使用需要注册地图数据
// import chinaMap from './china.json';
// echarts.registerMap('china', chinaMap);

function getOption(): echarts.EChartsOption {
  const data = props.data || [];
  const maxValue = Math.max(...data.map(d => d.value), 1);

  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : undefined,
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}',
    },
    visualMap: {
      min: 0,
      max: maxValue,
      left: 'left',
      top: 'bottom',
      text: ['高', '低'],
      calculable: true,
      inRange: {
        color: ['#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695'],
      },
    },
    series: [{
      type: 'map',
      map: props.mapType || 'china',
      roam: true,
      label: {
        show: true,
        fontSize: 10,
      },
      data: data,
      emphasis: {
        label: { show: true },
        itemStyle: { areaColor: '#ffd700' },
      },
    }],
  };
}

function initChart() {
  if (!chartRef.value) return;
  chart = echarts.init(chartRef.value);
  // 由于没有注册地图，这里显示提示
  chart.setOption({
    title: {
      text: '地图组件',
      subtext: '需要注册地图数据后使用',
      left: 'center',
      top: 'center',
    },
  });
}

function updateChart() {
  if (chart) {
    // chart.setOption(getOption());
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

watch(() => [props.title, props.mapType, props.data], updateChart, { deep: true });

defineExpose({ resize: handleResize });
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}
</style>
