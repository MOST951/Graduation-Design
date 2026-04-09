<template>
  <div class="linkable-chart" :class="{ 'is-linked': isLinked, 'is-previewing': isPreviewing }">
    <!-- 联动指示器 -->
    <div v-if="showIndicator && isLinked" class="linkage-indicator">
      <el-tooltip :content="linkageTooltip">
        <el-icon :size="16" color="#409EFF"><Connection /></el-icon>
      </el-tooltip>
    </div>
    
    <!-- 筛选状态显示 -->
    <div v-if="currentFilter" class="filter-badge">
      <el-tag size="small" closable @close="clearFilter">
        筛选: {{ formatFilterValue(currentFilter.value) }}
      </el-tag>
    </div>
    
    <!-- 图表内容 -->
    <div ref="chartRef" class="chart-content" :style="chartStyle"></div>
    
    <!-- 下钻面包屑 -->
    <div v-if="drillPath.length > 0 && supportDrillDown" class="drill-breadcrumb">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item @click="resetDrill">
          <el-icon><HomeFilled /></el-icon>
        </el-breadcrumb-item>
        <el-breadcrumb-item
          v-for="(item, index) in drillPath"
          :key="index"
          @click="drillToLevel(index)"
        >
          {{ formatDrillItem(item) }}
        </el-breadcrumb-item>
      </el-breadcrumb>
      <el-button size="small" text @click="drillUp">
        <el-icon><Back /></el-icon> 返回
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { Connection, HomeFilled, Back } from '@element-plus/icons-vue';
import { useLinkage, createEChartsLinkageHandlers, applyFilterToData } from '@/composables/useLinkage';
import { useLinkageStore } from '@/store/bindage';

const props = defineProps<{
  componentId: string;
  chartType: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'radar' | 'gauge';
  option: echarts.EChartsOption;
  data?: any[];
  showIndicator?: boolean;
  supportDrillDown?: boolean;
  drillDownField?: string;
}>();

const emit = defineEmits<{
  (e: 'click', data: any): void;
  (e: 'hover', data: any): void;
  (e: 'filter', data: any): void;
  (e: 'drill-down', data: any): void;
}>();

const linkageStore = useLinkageStore();
const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let cleanupLinkage: (() => void) | null = null;

// 使用联动 composable
const {
  isLinked,
  currentFilter,
  highlightedData,
  drillPath,
  isPreviewing,
  triggerClick,
  triggerHover,
  clearHighlight,
} = useLinkage({
  componentId: props.componentId,
  onFilter: (data) => {
    emit('filter', data);
    updateChartWithFilter(data);
  },
  onHighlight: (data) => {
    updateChartHighlight(data);
  },
  onDrillDown: (data) => {
    emit('drill-down', data);
  },
  onSyncZoom: (range) => {
    if (chart) {
      chart.dispatchAction({
        type: 'dataZoom',
        start: range.start,
        end: range.end,
      });
    }
  },
});

const chartStyle = computed(() => ({
  width: '100%',
  height: props.drillPath?.length > 0 ? 'calc(100% - 32px)' : '100%',
}));

const linkageTooltip = computed(() => {
  const linkages = linkageStore.getComponentLinkages(props.componentId);
  const parts = [];
  if (linkages.asSource.length > 0) {
    parts.push(`作为源: ${linkages.asSource.length}条规则`);
  }
  if (linkages.asTarget.length > 0) {
    parts.push(`作为目标: ${linkages.asTarget.length}条规则`);
  }
  return parts.join('\n') || '已配置联动';
});

function formatFilterValue(value: any): string {
  if (typeof value === 'object') {
    return value.name || JSON.stringify(value).substring(0, 20);
  }
  return String(value).substring(0, 20);
}

function formatDrillItem(item: any): string {
  if (typeof item.data === 'object') {
    return item.data.name || `Level ${item.level}`;
  }
  return String(item.data).substring(0, 15);
}

function clearFilter() {
  linkageStore.clearFilter();
  updateChart();
}

function drillUp() {
  linkageStore.drillUp();
}

function resetDrill() {
  linkageStore.resetDrill();
}

function drillToLevel(index: number) {
  while (drillPath.value.length > index + 1) {
    linkageStore.drillUp();
  }
}

function initChart() {
  if (!chartRef.value) return;
  
  chart = echarts.init(chartRef.value);
  chart.setOption(props.option);
  
  // 设置联动事件处理
  cleanupLinkage = createEChartsLinkageHandlers(props.componentId, chart);
  
  // 添加自定义事件
  chart.on('click', (params: any) => {
    emit('click', params);
  });
  
  chart.on('mouseover', (params: any) => {
    emit('hover', params);
  });
}

function updateChart() {
  if (!chart) return;
  chart.setOption(props.option, true);
}

function updateChartWithFilter(filterData: any) {
  if (!chart || !props.data) return;
  
  const filteredData = applyFilterToData(props.data, { value: filterData });
  
  // 根据图表类型更新数据
  const newOption = { ...props.option };
  if (Array.isArray(newOption.series)) {
    newOption.series = newOption.series.map((s: any) => ({
      ...s,
      data: filteredData,
    }));
  }
  
  chart.setOption(newOption, true);
}

function updateChartHighlight(data: any[]) {
  if (!chart) return;
  
  // 先取消所有高亮
  chart.dispatchAction({
    type: 'downplay',
  });
  
  // 高亮匹配的数据
  data.forEach(item => {
    chart!.dispatchAction({
      type: 'highlight',
      name: item.name,
    });
  });
}

function handleResize() {
  chart?.resize();
}

// 监听 option 变化
watch(() => props.option, () => {
  nextTick(() => {
    updateChart();
  });
}, { deep: true });

// 监听高亮数据变化
watch(highlightedData, (data) => {
  if (data.length > 0) {
    updateChartHighlight(data);
  } else {
    chart?.dispatchAction({ type: 'downplay' });
  }
});

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  cleanupLinkage?.();
  chart?.dispose();
});

defineExpose({
  resize: handleResize,
  getChart: () => chart,
});
</script>

<style scoped lang="scss">
.linkable-chart {
  position: relative;
  width: 100%;
  height: 100%;
  
  &.is-linked {
    // 可以添加联动状态的视觉效果
  }
  
  &.is-previewing {
    outline: 2px dashed #E6A23C;
    outline-offset: -2px;
  }
}

.linkage-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  z-index: 10;
  padding: 4px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 4px;
  cursor: help;
}

.filter-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  z-index: 10;
}

.chart-content {
  width: 100%;
  height: 100%;
}

.drill-breadcrumb {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;
  
  .el-breadcrumb {
    flex: 1;
  }
  
  .el-breadcrumb-item {
    cursor: pointer;
    
    &:hover {
      color: #409EFF;
    }
  }
}
</style>
