<template>
  <div class="quadrant-scatter" ref="containerRef">
    <div ref="chartRef" :style="{ height: height + 'px' }"></div>
    
    <!-- 图例和统计 -->
    <div class="chart-legend" v-if="showLegend">
      <div 
        v-for="(info, key) in quadrantConfig" 
        :key="key" 
        class="legend-item"
        :class="{ active: activeQuadrant === key, dimmed: activeQuadrant && activeQuadrant !== key }"
        @click="toggleQuadrant(key as string)"
      >
        <span class="legend-dot" :style="{ background: info.color }"></span>
        <span class="legend-label">{{ info.label }}</span>
        <span class="legend-count">{{ getQuadrantCount(key as string) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick, computed } from 'vue';
import * as echarts from 'echarts';

// Props
interface Props {
  data: Array<{
    id: string | number;
    x: number;  // 热度 0-100
    y: number;  // 情感 0-100
    value?: number;  // 综合得分
    quadrant: string;
    label?: string;
    [key: string]: any;
  }>;
  height?: number;
  xThreshold?: number;  // X轴阈值 (0-100)
  yThreshold?: number;  // Y轴阈值 (0-100)
  showLegend?: boolean;
  xAxisName?: string;
  yAxisName?: string;
}

const props = withDefaults(defineProps<Props>(), {
  height: 400,
  xThreshold: 50,
  yThreshold: 50,
  showLegend: true,
  xAxisName: '热度得分',
  yAxisName: '情感得分',
});

// Emits
const emit = defineEmits<{
  (e: 'point-click', point: any): void;
  (e: 'quadrant-filter', quadrant: string | null): void;
}>();

// 四象限配置
const quadrantConfig = {
  high_sentiment_high_heat: { label: '重点关注', color: '#F56C6C', position: 'top-right' },
  high_sentiment_low_heat: { label: '潜在风险', color: '#E6A23C', position: 'top-left' },
  low_sentiment_high_heat: { label: '热门中性', color: '#409EFF', position: 'bottom-right' },
  low_sentiment_low_heat: { label: '一般内容', color: '#909399', position: 'bottom-left' },
};

// Refs
const containerRef = ref<HTMLElement>();
const chartRef = ref<HTMLElement>();
let chart: echarts.ECharts | null = null;

const activeQuadrant = ref<string | null>(null);

// 计算各象限数量
const getQuadrantCount = (quadrant: string) => {
  return props.data.filter(d => d.quadrant === quadrant).length;
};

// 切换象限筛选
const toggleQuadrant = (quadrant: string) => {
  activeQuadrant.value = activeQuadrant.value === quadrant ? null : quadrant;
  emit('quadrant-filter', activeQuadrant.value);
  updateChart();
};

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return;
  
  chart = echarts.init(chartRef.value);
  
  chart.on('click', (params: any) => {
    if (params.componentType === 'series' && params.data) {
      const point = props.data.find(d => 
        d.x === params.data[0] && d.y === params.data[1]
      );
      if (point) {
        emit('point-click', point);
      }
    }
  });
  
  updateChart();
};

// 更新图表
const updateChart = () => {
  if (!chart) return;
  
  // 按象限分组数据
  const seriesData: Record<string, any[]> = {};
  for (const key of Object.keys(quadrantConfig)) {
    seriesData[key] = [];
  }
  
  for (const item of props.data) {
    // 如果有筛选，只显示选中象限
    if (activeQuadrant.value && item.quadrant !== activeQuadrant.value) continue;
    
    if (seriesData[item.quadrant]) {
      seriesData[item.quadrant].push([
        item.x,
        item.y,
        item.value || 50,
        item.label || '',
        item.id,
      ]);
    }
  }
  
  // 构建系列
  const series = Object.entries(quadrantConfig).map(([key, config]) => ({
    name: config.label,
    type: 'scatter',
    symbolSize: (data: any) => Math.max(6, Math.min(20, data[2] / 5)),
    data: seriesData[key],
    itemStyle: {
      color: config.color,
      opacity: activeQuadrant.value && activeQuadrant.value !== key ? 0.2 : 0.8,
    },
    emphasis: {
      focus: 'series',
      itemStyle: {
        shadowBlur: 10,
        shadowColor: 'rgba(0, 0, 0, 0.3)',
      },
    },
  }));
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data;
        return `
          <div style="padding: 8px; max-width: 200px;">
            <div style="font-weight: bold; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              ${data[3] || '数据点'}
            </div>
            <div>${props.xAxisName}: ${data[0].toFixed(1)}</div>
            <div>${props.yAxisName}: ${data[1].toFixed(1)}</div>
            <div>综合得分: ${data[2].toFixed(1)}</div>
          </div>
        `;
      },
    },
    grid: {
      left: '10%',
      right: '10%',
      top: '10%',
      bottom: '15%',
    },
    xAxis: {
      type: 'value',
      name: props.xAxisName,
      nameLocation: 'middle',
      nameGap: 30,
      min: 0,
      max: 100,
      splitLine: {
        show: true,
        lineStyle: { type: 'dashed', color: '#eee' },
      },
    },
    yAxis: {
      type: 'value',
      name: props.yAxisName,
      nameLocation: 'middle',
      nameGap: 40,
      min: 0,
      max: 100,
      splitLine: {
        show: true,
        lineStyle: { type: 'dashed', color: '#eee' },
      },
    },
    series,
    // 四象限分界线和标签
    graphic: [
      // 垂直分界线
      {
        type: 'line',
        shape: {
          x1: chart.convertToPixel('grid', [props.xThreshold, 0])[0],
          y1: chart.convertToPixel('grid', [0, 0])[1],
          x2: chart.convertToPixel('grid', [props.xThreshold, 100])[0],
          y2: chart.convertToPixel('grid', [0, 100])[1],
        },
        style: {
          stroke: '#ccc',
          lineDash: [5, 5],
          lineWidth: 2,
        },
      },
      // 水平分界线
      {
        type: 'line',
        shape: {
          x1: chart.convertToPixel('grid', [0, props.yThreshold])[0],
          y1: chart.convertToPixel('grid', [0, props.yThreshold])[1],
          x2: chart.convertToPixel('grid', [100, props.yThreshold])[0],
          y2: chart.convertToPixel('grid', [100, props.yThreshold])[1],
        },
        style: {
          stroke: '#ccc',
          lineDash: [5, 5],
          lineWidth: 2,
        },
      },
      // 象限标签
      {
        type: 'text',
        left: '15%',
        top: '15%',
        style: {
          text: '潜在风险',
          fill: quadrantConfig.high_sentiment_low_heat.color,
          fontSize: 12,
          fontWeight: 'bold',
        },
      },
      {
        type: 'text',
        right: '15%',
        top: '15%',
        style: {
          text: '重点关注',
          fill: quadrantConfig.high_sentiment_high_heat.color,
          fontSize: 12,
          fontWeight: 'bold',
        },
      },
      {
        type: 'text',
        left: '15%',
        bottom: '20%',
        style: {
          text: '一般内容',
          fill: quadrantConfig.low_sentiment_low_heat.color,
          fontSize: 12,
          fontWeight: 'bold',
        },
      },
      {
        type: 'text',
        right: '15%',
        bottom: '20%',
        style: {
          text: '热门中性',
          fill: quadrantConfig.low_sentiment_high_heat.color,
          fontSize: 12,
          fontWeight: 'bold',
        },
      },
    ],
  };
  
  chart.setOption(option, true);
};

// 监听数据变化
watch(() => props.data, () => {
  nextTick(updateChart);
}, { deep: true });

// 监听阈值变化
watch([() => props.xThreshold, () => props.yThreshold], () => {
  nextTick(updateChart);
});

// 生命周期
onMounted(() => {
  nextTick(initChart);
  
  window.addEventListener('resize', () => {
    chart?.resize();
  });
});

onUnmounted(() => {
  chart?.dispose();
});

// 暴露方法
defineExpose({
  refresh: updateChart,
  resize: () => chart?.resize(),
  clearFilter: () => {
    activeQuadrant.value = null;
    updateChart();
  },
});
</script>

<style scoped lang="scss">
.quadrant-scatter {
  position: relative;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 12px;
  flex-wrap: wrap;
  
  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.3s;
    background: #f5f7fa;
    
    &:hover {
      background: #ecf5ff;
    }
    
    &.active {
      background: #ecf5ff;
      box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
    }
    
    &.dimmed {
      opacity: 0.5;
    }
    
    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    
    .legend-label {
      font-size: 13px;
      color: #606266;
    }
    
    .legend-count {
      font-size: 12px;
      color: #909399;
      background: #fff;
      padding: 2px 6px;
      border-radius: 10px;
    }
  }
}
</style>
