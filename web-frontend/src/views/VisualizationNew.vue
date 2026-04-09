<template>
  <div class="visualization-module">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-section">
        <span class="section-label">图表类型:</span>
        <el-select v-model="selectedChartType" placeholder="选择图表" style="width: 150px" size="small">
          <el-option label="柱状图" value="bar" />
          <el-option label="折线图" value="line" />
          <el-option label="饼图" value="pie" />
          <el-option label="散点图" value="scatter" />
          <el-option label="热力图" value="heatmap" />
        </el-select>
      </div>
      
      <el-divider direction="vertical" />
      
      <div class="toolbar-section">
        <span class="section-label">数据源:</span>
        <el-select v-model="selectedDataSource" placeholder="选择数据源" style="width: 150px" size="small">
          <el-option label="情感分析" value="sentiment" />
          <el-option label="用户行为" value="behavior" />
          <el-option label="热点话题" value="topics" />
        </el-select>
      </div>
      
      <el-divider direction="vertical" />
      
      <div class="toolbar-section">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          size="small"
          style="width: 240px"
        />
      </div>
      
      <el-divider direction="vertical" />
      
      <el-button-group size="small">
        <el-button :icon="Plus" type="primary" @click="addChart">添加图表</el-button>
        <el-button :icon="Download" @click="exportDashboard">导出</el-button>
        <el-button :icon="Share" @click="shareDashboard">分享</el-button>
      </el-button-group>
      
      <div class="toolbar-right">
        <el-button
          :icon="Setting"
          circle
          size="small"
          @click="showPropertyPanel = !showPropertyPanel"
        />
      </div>
    </div>
    
    <!-- 主工作区 -->
    <div class="workbench-layout">
      <!-- 可拖拽画布 -->
      <main class="canvas-area" :class="{ 'full-width': !showPropertyPanel }">
        <div class="canvas-grid">
          <div
            v-for="item in chartItems"
            :key="item.id"
            class="chart-item"
            :style="getItemStyle(item)"
            @click="selectChart(item)"
          >
            <div class="chart-header">
              <span>{{ item.title }}</span>
              <el-button-group size="small">
                <el-button :icon="Edit" circle @click.stop="editChart(item)" />
                <el-button :icon="Delete" circle @click.stop="deleteChart(item.id)" />
              </el-button-group>
            </div>
            <div :ref="el => chartRefs[item.id] = el" class="chart-container"></div>
          </div>
        </div>
        
        <div v-if="chartItems.length === 0" class="empty-canvas">
          <el-empty description="暂无图表，点击上方"添加图表"开始创建" />
        </div>
      </main>
      
      <!-- 右侧属性面板 -->
      <aside v-if="showPropertyPanel" class="property-panel">
        <el-card header="图表属性">
          <el-form v-if="selectedChart" label-width="80px" size="small">
            <el-form-item label="标题">
              <el-input v-model="selectedChart.title" />
            </el-form-item>
            <el-form-item label="图表类型">
              <el-select v-model="selectedChart.type" @change="updateChart">
                <el-option label="柱状图" value="bar" />
                <el-option label="折线图" value="line" />
                <el-option label="饼图" value="pie" />
              </el-select>
            </el-form-item>
            <el-form-item label="宽度">
              <el-slider v-model="selectedChart.width" :min="200" :max="800" />
            </el-form-item>
            <el-form-item label="高度">
              <el-slider v-model="selectedChart.height" :min="200" :max="600" />
            </el-form-item>
            <el-form-item label="颜色主题">
              <el-select v-model="selectedChart.theme">
                <el-option label="默认" value="default" />
                <el-option label="深色" value="dark" />
                <el-option label="彩色" value="colorful" />
              </el-select>
            </el-form-item>
          </el-form>
          <el-empty v-else description="请选择一个图表" />
        </el-card>
        
        <el-card header="数据配置" style="margin-top: 16px">
          <el-form v-if="selectedChart" label-width="80px" size="small">
            <el-form-item label="数据源">
              <el-select v-model="selectedChart.dataSource">
                <el-option label="情感分析" value="sentiment" />
                <el-option label="用户行为" value="behavior" />
              </el-select>
            </el-form-item>
            <el-form-item label="刷新间隔">
              <el-input-number v-model="selectedChart.refreshInterval" :min="0" :max="60" />
              <span style="margin-left: 8px">秒</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="small" block @click="updateChart">
                应用更改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { Plus, Download, Share, Setting, Edit, Delete } from '@element-plus/icons-vue';

// 工具栏状态
const selectedChartType = ref('bar');
const selectedDataSource = ref('sentiment');
const dateRange = ref<[Date, Date] | null>(null);
const showPropertyPanel = ref(true);

// 图表项
const chartItems = ref([
  {
    id: '1',
    title: '情感分布',
    type: 'pie',
    width: 400,
    height: 300,
    x: 0,
    y: 0,
    dataSource: 'sentiment',
    theme: 'default',
    refreshInterval: 0,
  },
  {
    id: '2',
    title: '趋势分析',
    type: 'line',
    width: 400,
    height: 300,
    x: 420,
    y: 0,
    dataSource: 'sentiment',
    theme: 'default',
    refreshInterval: 0,
  },
]);

const selectedChart = ref<any>(null);
const chartRefs = reactive<Record<string, any>>({});
const chartInstances = reactive<Record<string, echarts.ECharts>>({});

// 工具函数
const getItemStyle = (item: any) => {
  return {
    width: `${item.width}px`,
    height: `${item.height}px`,
    left: `${item.x}px`,
    top: `${item.y}px`,
  };
};

// 初始化图表
const initChart = (id: string, type: string) => {
  const el = chartRefs[id];
  if (!el) return;
  
  const chart = echarts.init(el);
  chartInstances[id] = chart;
  
  if (type === 'pie') {
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: '60%',
        data: [
          { value: 45, name: '正面' },
          { value: 30, name: '中性' },
          { value: 25, name: '负面' },
        ],
      }],
    });
  } else if (type === 'line') {
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五'] },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        data: [120, 200, 150, 80, 70],
      }],
    });
  } else if (type === 'bar') {
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['正面', '中性', '负面'] },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar',
        data: [450, 300, 250],
      }],
    });
  }
};

// 事件处理
const addChart = () => {
  const newChart = {
    id: Date.now().toString(),
    title: `新图表 ${chartItems.value.length + 1}`,
    type: selectedChartType.value,
    width: 400,
    height: 300,
    x: 0,
    y: chartItems.value.length * 320,
    dataSource: selectedDataSource.value,
    theme: 'default',
    refreshInterval: 0,
  };
  chartItems.value.push(newChart);
  ElMessage.success('图表已添加');
  
  setTimeout(() => {
    initChart(newChart.id, newChart.type);
  }, 100);
};

const selectChart = (item: any) => {
  selectedChart.value = item;
};

const editChart = (item: any) => {
  selectedChart.value = item;
  showPropertyPanel.value = true;
};

const deleteChart = (id: string) => {
  const index = chartItems.value.findIndex(item => item.id === id);
  if (index > -1) {
    chartItems.value.splice(index, 1);
    if (chartInstances[id]) {
      chartInstances[id].dispose();
      delete chartInstances[id];
    }
    ElMessage.success('图表已删除');
  }
};

const updateChart = () => {
  if (!selectedChart.value) return;
  const chart = chartInstances[selectedChart.value.id];
  if (chart) {
    chart.dispose();
    initChart(selectedChart.value.id, selectedChart.value.type);
  }
  ElMessage.success('图表已更新');
};

const exportDashboard = () => {
  ElMessage.success('导出功能开发中');
};

const shareDashboard = () => {
  ElMessage.success('分享功能开发中');
};

// 生命周期
onMounted(() => {
  setTimeout(() => {
    chartItems.value.forEach(item => {
      initChart(item.id, item.type);
    });
  }, 100);
  
  window.addEventListener('resize', () => {
    Object.values(chartInstances).forEach(chart => chart.resize());
  });
});

onUnmounted(() => {
  Object.values(chartInstances).forEach(chart => chart.dispose());
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.visualization-module {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.toolbar {
  height: 60px;
  background: $bg-white;
  border-bottom: 1px solid $border-lighter;
  padding: 0 $spacing-md;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
  
  .toolbar-section {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    
    .section-label {
      font-size: $font-size-small;
      color: $text-secondary;
      white-space: nowrap;
    }
  }
  
  .toolbar-right {
    margin-left: auto;
  }
}

.workbench-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.canvas-area {
  flex: 1;
  background: #f5f7fa;
  padding: $spacing-md;
  overflow: auto;
  position: relative;
  transition: $transition-fast;
  
  &.full-width {
    width: 100%;
  }
  
  .canvas-grid {
    position: relative;
    min-height: 100%;
  }
  
  .chart-item {
    position: absolute;
    background: $bg-white;
    border-radius: $border-radius-base;
    box-shadow: $box-shadow-base;
    cursor: move;
    transition: $transition-fast;
    
    &:hover {
      box-shadow: $box-shadow-light;
    }
    
    .chart-header {
      height: 40px;
      padding: 0 $spacing-sm;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid $border-lighter;
      font-weight: $font-weight-medium;
    }
    
    .chart-container {
      height: calc(100% - 40px);
      padding: $spacing-sm;
    }
  }
  
  .empty-canvas {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
  }
}

.property-panel {
  width: 300px;
  background: $bg-white;
  border-left: 1px solid $border-lighter;
  padding: $spacing-md;
  overflow-y: auto;
  flex-shrink: 0;
}

// 响应式
@media (max-width: 1200px) {
  .property-panel {
    width: 250px;
  }
}
</style>
