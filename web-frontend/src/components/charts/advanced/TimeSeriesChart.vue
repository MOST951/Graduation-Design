<template>
  <div class="time-series-chart">
    <div class="chart-toolbar">
      <el-button-group size="small">
        <el-button :type="timeScale === '1h' ? 'primary' : ''" @click="changeTimeScale('1h')">1小时</el-button>
        <el-button :type="timeScale === '1d' ? 'primary' : ''" @click="changeTimeScale('1d')">1天</el-button>
        <el-button :type="timeScale === '1w' ? 'primary' : ''" @click="changeTimeScale('1w')">1周</el-button>
        <el-button :type="timeScale === '1m' ? 'primary' : ''" @click="changeTimeScale('1m')">1月</el-button>
      </el-button-group>
      
      <el-switch
        v-model="showAnomalies"
        active-text="显示异常点"
        @change="updateChart"
      />
      
      <el-switch
        v-model="isRealtime"
        active-text="实时数据"
        @change="toggleRealtime"
      />
    </div>
    
    <div ref="chartRef" class="chart-container"></div>
    
    <div v-if="selectedPoint" class="point-detail">
      <el-card>
        <template #header>
          <span>数据详情</span>
          <el-button text @click="selectedPoint = null">关闭</el-button>
        </template>
        <el-descriptions :column="2" size="small">
          <el-descriptions-item label="时间">{{ formatTime(selectedPoint.time) }}</el-descriptions-item>
          <el-descriptions-item label="值">{{ selectedPoint.value }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedPoint.isAnomaly" label="异常类型">
            <el-tag type="danger">{{ selectedPoint.anomalyType }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import * as echarts from 'echarts';

interface DataPoint {
  time: number;
  value: number;
  isAnomaly?: boolean;
  anomalyType?: string;
}

const props = defineProps<{
  data?: DataPoint[];
  title?: string;
  yAxisName?: string;
  enableDataZoom?: boolean;
  samplingThreshold?: number;
}>();

const emit = defineEmits<{
  (e: 'anomalyDetected', point: DataPoint): void;
  (e: 'timeRangeChange', range: { start: number; end: number }): void;
}>();

const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let realtimeTimer: number | null = null;

const timeScale = ref('1d');
const showAnomalies = ref(true);
const isRealtime = ref(false);
const selectedPoint = ref<DataPoint | null>(null);

// 数据采样优化
const sampledData = computed(() => {
  if (!props.data || props.data.length <= (props.samplingThreshold || 10000)) {
    return props.data || [];
  }
  
  // 使用LTTB算法进行数据采样
  return lttbSampling(props.data, props.samplingThreshold || 10000);
});

// 异常检测
const anomalies = computed(() => {
  if (!props.data) return [];
  return detectAnomalies(props.data);
});

function getOption(): echarts.EChartsOption {
  const data = sampledData.value;
  const times = data.map(d => d.time);
  const values = data.map(d => d.value);
  
  // 标记异常点
  const anomalyData = showAnomalies.value
    ? anomalies.value.map(a => [a.time, a.value])
    : [];
  
  return {
    title: {
      text: props.title,
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
      },
      formatter: (params: any) => {
        const param = Array.isArray(params) ? params[0] : params;
        const time = new Date(param.data[0]).toLocaleString();
        return `${time}<br/>值: ${param.data[1]}`;
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: props.enableDataZoom ? '15%' : '3%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLabel: {
        formatter: (value: number) => {
          const date = new Date(value);
          if (timeScale.value === '1h') {
            return date.toLocaleTimeString();
          } else if (timeScale.value === '1d') {
            return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:00`;
          } else {
            return `${date.getMonth() + 1}/${date.getDate()}`;
          }
        },
      },
    },
    yAxis: {
      type: 'value',
      name: props.yAxisName,
      splitLine: {
        lineStyle: {
          type: 'dashed',
        },
      },
    },
    dataZoom: props.enableDataZoom ? [
      {
        type: 'inside',
        start: 0,
        end: 100,
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        handleSize: '80%',
      },
    ] : undefined,
    series: [
      {
        name: '数据',
        type: 'line',
        data: data.map(d => [d.time, d.value]),
        smooth: true,
        symbol: 'none',
        sampling: 'lttb',
        lineStyle: {
          width: 2,
          color: '#5470c6',
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(84, 112, 198, 0.3)' },
            { offset: 1, color: 'rgba(84, 112, 198, 0.05)' },
          ]),
        },
      },
      {
        name: '异常点',
        type: 'scatter',
        data: anomalyData,
        symbol: 'circle',
        symbolSize: 10,
        itemStyle: {
          color: '#ff4d4f',
          borderColor: '#fff',
          borderWidth: 2,
        },
        emphasis: {
          scale: 1.5,
        },
        z: 10,
      },
    ],
  };
}

// LTTB采样算法（Largest-Triangle-Three-Buckets）
function lttbSampling(data: DataPoint[], threshold: number): DataPoint[] {
  if (data.length <= threshold) return data;
  
  const sampled: DataPoint[] = [];
  const bucketSize = (data.length - 2) / (threshold - 2);
  
  sampled.push(data[0]); // 保留第一个点
  
  let a = 0;
  for (let i = 0; i < threshold - 2; i++) {
    const avgRangeStart = Math.floor((i + 1) * bucketSize) + 1;
    const avgRangeEnd = Math.floor((i + 2) * bucketSize) + 1;
    const avgRangeLength = avgRangeEnd - avgRangeStart;
    
    let avgX = 0;
    let avgY = 0;
    
    for (let j = avgRangeStart; j < avgRangeEnd; j++) {
      avgX += data[j].time;
      avgY += data[j].value;
    }
    avgX /= avgRangeLength;
    avgY /= avgRangeLength;
    
    const rangeStart = Math.floor(i * bucketSize) + 1;
    const rangeEnd = Math.floor((i + 1) * bucketSize) + 1;
    
    const pointAX = data[a].time;
    const pointAY = data[a].value;
    
    let maxArea = -1;
    let maxAreaPoint = 0;
    
    for (let j = rangeStart; j < rangeEnd; j++) {
      const area = Math.abs(
        (pointAX - avgX) * (data[j].value - pointAY) -
        (pointAX - data[j].time) * (avgY - pointAY)
      ) * 0.5;
      
      if (area > maxArea) {
        maxArea = area;
        maxAreaPoint = j;
      }
    }
    
    sampled.push(data[maxAreaPoint]);
    a = maxAreaPoint;
  }
  
  sampled.push(data[data.length - 1]); // 保留最后一个点
  
  return sampled;
}

// 异常检测（使用Z-score方法）
function detectAnomalies(data: DataPoint[]): DataPoint[] {
  if (data.length < 10) return [];
  
  const values = data.map(d => d.value);
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
  const stdDev = Math.sqrt(variance);
  
  const threshold = 3; // 3倍标准差
  
  return data.filter(d => {
    const zScore = Math.abs((d.value - mean) / stdDev);
    if (zScore > threshold) {
      const anomaly = { ...d, isAnomaly: true, anomalyType: '统计异常' };
      emit('anomalyDetected', anomaly);
      return true;
    }
    return false;
  });
}

function changeTimeScale(scale: string) {
  timeScale.value = scale;
  updateChart();
}

function toggleRealtime(enabled: boolean) {
  if (enabled) {
    startRealtimeUpdate();
  } else {
    stopRealtimeUpdate();
  }
}

function startRealtimeUpdate() {
  realtimeTimer = window.setInterval(() => {
    // 模拟实时数据更新
    if (chart && props.data) {
      const lastPoint = props.data[props.data.length - 1];
      const newPoint: DataPoint = {
        time: Date.now(),
        value: lastPoint.value + (Math.random() - 0.5) * 10,
      };
      
      const dataArr = props.data as DataPoint[];
      dataArr.push(newPoint);
      if (dataArr.length > 1000) {
        dataArr.shift();
      }
      
      updateChart();
    }
  }, 1000);
}

function stopRealtimeUpdate() {
  if (realtimeTimer) {
    clearInterval(realtimeTimer);
    realtimeTimer = null;
  }
}

function initChart() {
  if (!chartRef.value) return;
  
  chart = echarts.init(chartRef.value);
  chart.setOption(getOption());
  
  // 点击事件
  chart.on('click', (params: any) => {
    if (params.componentType === 'series') {
      const point = props.data?.find(d => 
        d.time === params.data[0] && d.value === params.data[1]
      );
      if (point) {
        selectedPoint.value = point;
      }
    }
  });
  
  // 数据缩放事件
  chart.on('datazoom', (params: any) => {
    if (params.batch && params.batch[0]) {
      const { startValue, endValue } = params.batch[0];
      emit('timeRangeChange', { start: startValue, end: endValue });
    }
  });
}

function updateChart() {
  if (chart) {
    chart.setOption(getOption(), true);
  }
}

function handleResize() {
  chart?.resize();
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleString();
}

watch(() => props.data, () => {
  updateChart();
}, { deep: true });

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  stopRealtimeUpdate();
  window.removeEventListener('resize', handleResize);
  chart?.dispose();
});

defineExpose({ resize: handleResize, updateChart });
</script>

<style scoped lang="scss">
.time-series-chart {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.chart-container {
  flex: 1;
  min-height: 300px;
}

.point-detail {
  position: absolute;
  top: 60px;
  right: 20px;
  width: 300px;
  z-index: 10;
  
  .el-card {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
}
</style>
