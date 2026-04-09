<template>
  <div class="visualization-dashboard">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header with Time Filter -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="page-title">Visualization Dashboard</h1>
        <div class="header-stats">
          <span class="stat-item">
            <strong>{{ totalDataPoints.toLocaleString() }}</strong> data points
          </span>
          <span class="stat-item">
            <strong>{{ activeCharts }}</strong> active charts
          </span>
        </div>
      </div>
      
      <div class="header-right">
        <div class="header-controls">
          <TimeRangeFilter
            @range-change="handleTimeRangeChange"
            :default-range="'7d'"
          />
          
          <el-button
            type="primary"
            size="large"
            :icon="Refresh"
            @click="refreshAllCharts"
            :loading="isRefreshing"
            :aria-label="'Refresh all charts'"
          >
            Refresh All
          </el-button>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Top Row: Sentiment Distribution and Word Cloud -->
        <el-col :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <el-icon><PieChart /></el-icon>
                <span>Sentiment Distribution</span>
                <div class="chart-controls">
                  <el-radio-group v-model="distributionType" size="small" @change="updateDistributionChart">
                    <el-radio-button label="pie">Pie</el-radio-button>
                    <el-radio-button label="donut">Donut</el-radio-button>
                    <el-radio-button label="bar">Bar</el-radio-button>
                  </el-radio-group>
                  
                  <ChartExportMenu
                    :chart-instance="distributionChart"
                    chart-title="sentiment_distribution"
                  />
                </div>
              </div>
            </template>
            
            <div class="chart-container">
              <div ref="distributionChartRef" class="chart"></div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <el-icon><Cloud /></el-icon>
                <span>Hot Topics Word Cloud</span>
                <div class="chart-controls">
                  <el-button
                    text
                    size="small"
                    @click="refreshWordCloud"
                    :loading="isRefreshingWordCloud"
                    :aria-label="'Refresh word cloud'"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                  
                  <ChartExportMenu
                    :chart-instance="wordCloudChart"
                    chart-title="hot_topics_wordcloud"
                  />
                </div>
              </div>
            </template>
            
            <div class="chart-container">
              <div ref="wordCloudChartRef" class="chart"></div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <el-row :gutter="20" style="margin-top: 20px;">
        <!-- Middle Row: Sentiment Trends and Propagation Path -->
        <el-col :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <el-icon><LineChart /></el-icon>
                <span>Sentiment Trends</span>
                <div class="chart-controls">
                  <el-checkbox-group v-model="trendDimensions" size="small" @change="updateTrendChart">
                    <el-checkbox-button label="positive">Positive</el-checkbox-button>
                    <el-checkbox-button label="negative">Negative</el-checkbox-button>
                    <el-checkbox-button label="neutral">Neutral</el-checkbox-button>
                  </el-checkbox-group>
                  
                  <ChartExportMenu
                    :chart-instance="trendChart"
                    chart-title="sentiment_trends"
                  />
                </div>
              </div>
            </template>
            
            <div class="chart-container">
              <div ref="trendChartRef" class="chart"></div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <el-icon><Share /></el-icon>
                <span>Propagation Path</span>
                <div class="chart-controls">
                  <el-input
                    v-model="selectedWeiboId"
                    placeholder="Weibo ID"
                    size="small"
                    style="width: 120px"
                    @change="updatePropagationChart"
                  />
                  
                  <el-button
                    text
                    size="small"
                    @click="refreshPropagationChart"
                    :loading="isRefreshingPropagation"
                    :aria-label="'Refresh propagation chart'"
                  >
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                  
                  <ChartExportMenu
                    :chart-instance="propagationChart"
                    chart-title="propagation_path"
                  />
                </div>
              </div>
            </template>
            
            <div class="chart-container">
              <div ref="propagationChartRef" class="chart"></div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  PieChart, Cloud, LineChart, Share, Refresh
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import TimeRangeFilter from '@/components/common/TimeRangeFilter.vue'
import ChartExportMenu from '@/components/common/ChartExportMenu.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Router
const router = useRouter()

// Reactive data
const distributionType = ref('pie')
const trendDimensions = ref(['positive', 'negative', 'neutral'])
const selectedWeiboId = ref('weibo_12345')
const isRefreshing = ref(false)
const isRefreshingWordCloud = ref(false)
const isRefreshingPropagation = ref(false)
const totalDataPoints = ref(0)
const activeCharts = ref(4)

// Chart refs
const distributionChartRef = ref()
const wordCloudChartRef = ref()
const trendChartRef = ref()
const propagationChartRef = ref()

// Chart instances
const distributionChart = ref<echarts.ECharts | null>(null)
const wordCloudChart = ref<echarts.ECharts | null>(null)
const trendChart = ref<echarts.ECharts | null>(null)
const propagationChart = ref<echarts.ECharts | null>(null)

// Time range
const currentTimeRange = ref({ startDate: new Date(), endDate: new Date() })

// Computed properties
const activeCharts = computed(() => {
  let count = 0
  if (distributionChart.value) count++
  if (wordCloudChart.value) count++
  if (trendChart.value) count++
  if (propagationChart.value) count++
  return count
})

// Methods
const handleTimeRangeChange = (startDate: Date, endDate: Date) => {
  currentTimeRange.value = { startDate, endDate }
  ElMessage.info(`Time range updated: ${startDate.toDateString()} - ${endDate.toDateString()}`)
  refreshAllCharts()
}

const refreshAllCharts = async () => {
  isRefreshing.value = true
  
  try {
    await withErrorHandling(
      async () => {
        await Promise.all([
          updateDistributionChart(),
          refreshWordCloud(),
          updateTrendChart(),
          refreshPropagationChart()
        ])
        
        ElMessage.success('All charts refreshed successfully')
      },
      'Refresh Charts',
      { showLoading: false }
    )
  } finally {
    isRefreshing.value = false
  }
}

// Sentiment Distribution Chart
const updateDistributionChart = async () => {
  if (!distributionChartRef.value) return
  
  if (!distributionChart.value) {
    distributionChart.value = echarts.init(distributionChartRef.value)
  }
  
  // Mock data
  const data = [
    { value: 4500, name: 'Positive', itemStyle: { color: '#52c41a' } },
    { value: 2300, name: 'Negative', itemStyle: { color: '#ff4d4f' } },
    { value: 3200, name: 'Neutral', itemStyle: { color: '#faad14' } }
  ]
  
  totalDataPoints.value = data.reduce((sum, item) => sum + item.value, 0)
  
  let option: any = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      data: data.map(item => item.name),
      selected: {
        'Positive': true,
        'Negative': true,
        'Neutral': true
      }
    }
  }
  
  if (distributionType.value === 'pie') {
    option.series = [{
      type: 'pie',
      radius: '60%',
      center: ['60%', '50%'],
      data,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  } else if (distributionType.value === 'donut') {
    option.series = [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '50%'],
      data,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  } else if (distributionType.value === 'bar') {
    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.map(item => item.name),
        axisLabel: {
          interval: 0,
          rotate: 0
        }
      },
      yAxis: {
        type: 'value'
      },
      series: [{
        type: 'bar',
        data: data.map(item => ({
          value: item.value,
          itemStyle: { color: item.itemStyle.color }
        }))
      }]
    }
  }
  
  distributionChart.value.setOption(option, true)
  
  // Add legend click handler
  distributionChart.value.off('legendselectchanged')
  distributionChart.value.on('legendselectchanged', (params: any) => {
    ElMessage.info(`Legend ${Object.keys(params.selected)[0]} ${params.selected[Object.keys(params.selected)[0]] ? 'shown' : 'hidden'}`)
  })
}

// Word Cloud Chart
const refreshWordCloud = async () => {
  isRefreshingWordCloud.value = true
  
  try {
    await withErrorHandling(
      async () => {
        if (!wordCloudChartRef.value) return
        
        if (!wordCloudChart.value) {
          wordCloudChart.value = echarts.init(wordCloudChartRef.value)
        }
        
        // Mock TF-IDF data from weibo_core_data topics field
        const wordData = [
          { name: 'AI', value: 95, textStyle: { color: '#ff6b6b' } },
          { name: 'Machine Learning', value: 88, textStyle: { color: '#4ecdc4' } },
          { name: 'Vue.js', value: 82, textStyle: { color: '#45b7d1' } },
          { name: 'React', value: 78, textStyle: { color: '#96ceb4' } },
          { name: 'Python', value: 75, textStyle: { color: '#feca57' } },
          { name: 'JavaScript', value: 72, textStyle: { color: '#ff9ff3' } },
          { name: 'TypeScript', value: 68, textStyle: { color: '#54a0ff' } },
          { name: 'Big Data', value: 65, textStyle: { color: '#5f27cd' } },
          { name: 'Cloud Computing', value: 62, textStyle: { color: '#00d2d3' } },
          { name: 'Blockchain', value: 58, textStyle: { color: '#ff6348' } },
          { name: 'IoT', value: 55, textStyle: { color: '#48dbfb' } },
          { name: '5G', value: 52, textStyle: { color: '#ee5a24' } },
          { name: 'Data Science', value: 48, textStyle: { color: '#0abde3' } },
          { name: 'Neural Networks', value: 45, textStyle: { color: '#c44569' } },
          { name: 'Deep Learning', value: 42, textStyle: { color: '#f8b500' } },
          { name: 'Frontend', value: 40, textStyle: { color: '#786fa6' } },
          { name: 'Backend', value: 38, textStyle: { color: '#f19066' } },
          { name: 'DevOps', value: 35, textStyle: { color: '#63cdda' } },
          { name: 'Microservices', value: 32, textStyle: { color: '#cf6a87' } },
          { name: 'Kubernetes', value: 30, textStyle: { color: '#e66767' } }
        ]
        
        const option = {
          tooltip: {
            show: true,
            formatter: (params: any) => {
              return `${params.name}: ${params.value} (TF-IDF)`
            }
          },
          series: [{
            type: 'wordCloud',
            gridSize: 2,
            sizeRange: [12, 60],
            rotationRange: [-90, 90],
            shape: 'pentagon',
            width: '100%',
            height: '100%',
            drawOutOfBound: false,
            layoutAnimation: true,
            textStyle: {
              fontFamily: 'sans-serif',
              fontWeight: 'bold'
            },
            emphasis: {
              focus: 'self',
              textStyle: {
                shadowBlur: 10,
                shadowColor: '#333'
              }
            },
            data: wordData
          }]
        }
        
        wordCloudChart.value.setOption(option, true)
        
        // Add click handler for global search
        wordCloudChart.value.off('click')
        wordCloudChart.value.on('click', (params: any) => {
          handleWordCloudClick(params.name)
        })
      },
      'Refresh Word Cloud',
      { showLoading: false }
    )
  } finally {
    isRefreshingWordCloud.value = false
  }
}

const handleWordCloudClick = (keyword: string) => {
  ElMessage.info(`Searching for: ${keyword}`)
  
  // Navigate to hot topics page with keyword filter
  router.push({
    path: '/hot-topics',
    query: { keyword }
  })
}

// Sentiment Trends Chart
const updateTrendChart = async () => {
  if (!trendChartRef.value) return
  
  if (!trendChart.value) {
    trendChart.value = echarts.init(trendChartRef.value)
  }
  
  // Generate mock trend data
  const dates = []
  const positiveData = []
  const negativeData = []
  const neutralData = []
  
  const now = new Date()
  for (let i = 29; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
    dates.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
    
    positiveData.push(Math.floor(Math.random() * 500 + 300))
    negativeData.push(Math.floor(Math.random() * 300 + 100))
    neutralData.push(Math.floor(Math.random() * 400 + 200))
  }
  
  const series = []
  
  if (trendDimensions.value.includes('positive')) {
    series.push({
      name: 'Positive',
      type: 'line',
      data: positiveData,
      itemStyle: { color: '#52c41a' },
      areaStyle: { color: 'rgba(82, 196, 26, 0.3)' }
    })
  }
  
  if (trendDimensions.value.includes('negative')) {
    series.push({
      name: 'Negative',
      type: 'line',
      data: negativeData,
      itemStyle: { color: '#ff4d4f' },
      areaStyle: { color: 'rgba(255, 77, 79, 0.3)' }
    })
  }
  
  if (trendDimensions.value.includes('neutral')) {
    series.push({
      name: 'Neutral',
      type: 'line',
      data: neutralData,
      itemStyle: { color: '#faad14' },
      areaStyle: { color: 'rgba(250, 173, 20, 0.3)' }
    })
  }
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      }
    },
    legend: {
      data: trendDimensions.value.map(dim => dim.charAt(0).toUpperCase() + dim.slice(1))
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: {
      type: 'value'
    },
    series
  }
  
  trendChart.value.setOption(option, true)
}

// Propagation Path Chart
const refreshPropagationChart = async () => {
  isRefreshingPropagation.value = true
  
  try {
    await withErrorHandling(
      async () => {
        await updatePropagationChart()
      },
      'Refresh Propagation Chart',
      { showLoading: false }
    )
  } finally {
    isRefreshingPropagation.value = false
  }
}

const updatePropagationChart = async () => {
  if (!propagationChartRef.value) return
  
  if (!propagationChart.value) {
    propagationChart.value = echarts.init(propagationChartRef.value)
  }
  
  // Mock propagation data for a specific weibo
  const nodes = [
    { id: 'original', name: 'Original User', x: 300, y: 300, symbolSize: 30, category: 0 },
    { id: 'user1', name: 'User 1', x: 200, y: 200, symbolSize: 20, category: 1 },
    { id: 'user2', name: 'User 2', x: 400, y: 200, symbolSize: 20, category: 1 },
    { id: 'user3', name: 'User 3', x: 200, y: 400, symbolSize: 20, category: 1 },
    { id: 'user4', name: 'User 4', x: 400, y: 400, symbolSize: 20, category: 1 },
    { id: 'user5', name: 'User 5', x: 100, y: 300, symbolSize: 15, category: 2 },
    { id: 'user6', name: 'User 6', x: 500, y: 300, symbolSize: 15, category: 2 },
    { id: 'user7', name: 'User 7', x: 300, y: 100, symbolSize: 15, category: 2 },
    { id: 'user8', name: 'User 8', x: 300, y: 500, symbolSize: 15, category: 2 }
  ]
  
  const links = [
    { source: 'original', target: 'user1', value: 10 },
    { source: 'original', target: 'user2', value: 8 },
    { source: 'original', target: 'user3', value: 12 },
    { source: 'original', target: 'user4', value: 6 },
    { source: 'user1', target: 'user5', value: 3 },
    { source: 'user2', target: 'user6', value: 4 },
    { source: 'user3', target: 'user7', value: 5 },
    { source: 'user4', target: 'user8', value: 2 }
  ]
  
  const categories = [
    { name: 'Original', itemStyle: { color: '#ff6b6b' } },
    { name: 'First Level', itemStyle: { color: '#4ecdc4' } },
    { name: 'Second Level', itemStyle: { color: '#45b7d1' } }
  ]
  
  const option = {
    title: {
      text: `Propagation Path for ${selectedWeiboId}`,
      subtext: 'Retweet Network Visualization',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `${params.data.name}<br/>Connections: ${params.data.value || 0}`
        } else if (params.dataType === 'edge') {
          return `${params.data.source} -> ${params.data.target}<br/>Weight: ${params.data.value}`
        }
      }
    },
    legend: {
      data: categories.map(cat => cat.name),
      orient: 'vertical',
      right: 10,
      top: 20
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      categories: categories,
      roam: true,
      label: {
        show: true,
        position: 'right',
        formatter: '{b}'
      },
      force: {
        repulsion: 1000,
        edgeLength: 200,
        layoutAnimation: true
      },
      lineStyle: {
        color: 'source',
        curveness: 0.3,
        width: (params: any) => params.data.value
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 4
        }
      }
    }]
  }
  
  propagationChart.value.setOption(option, true)
}

// Lifecycle
onMounted(async () => {
  await nextTick()
  
  // Initialize all charts
  await Promise.all([
    updateDistributionChart(),
    refreshWordCloud(),
    updateTrendChart(),
    refreshPropagationChart()
  ])
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
  
  // Handle window resize
  const handleResize = () => {
    distributionChart.value?.resize()
    wordCloudChart.value?.resize()
    trendChart.value?.resize()
    propagationChart.value?.resize()
  }
  
  window.addEventListener('resize', handleResize)
  
  // Cleanup on unmount
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    
    // Dispose charts
    distributionChart.value?.dispose()
    wordCloudChart.value?.dispose()
    trendChart.value?.dispose()
    propagationChart.value?.dispose()
  })
})
</script>

<style scoped>
.visualization-dashboard {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.page-title {
  font-size: var(--font-size-extra-large);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.header-stats {
  display: flex;
  gap: var(--spacing-lg);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
}

.stat-item strong {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.header-right {
  display: flex;
  align-items: center;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.main-content {
  margin-top: var(--spacing-lg);
}

.chart-card {
  margin-bottom: var(--spacing-lg);
  transition: var(--transition-base);
}

.chart-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-semibold);
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.chart-container {
  position: relative;
  min-height: 400px;
}

.chart {
  width: 100%;
  height: 400px;
}

/* Responsive layout */
@media (max-width: 1200px) {
  .dashboard-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-controls {
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .chart-controls {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .visualization-dashboard {
    padding: var(--spacing-md);
  }
  
  .dashboard-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .header-stats {
    justify-content: center;
    gap: var(--spacing-md);
  }
  
  .header-controls {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }
  
  .chart-controls {
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .chart {
    height: 300px;
  }
}

@media (max-width: 480px) {
  .chart-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .chart-controls .el-radio-group,
  .chart-controls .el-checkbox-group {
    justify-content: center;
  }
  
  .chart-controls .el-input {
    width: 100% !important;
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .chart-card {
    border-width: 2px;
  }
}

/* Chart loading state */
.chart-container::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border-light);
  border-top: 3px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  opacity: 0;
  transition: opacity 0.3s;
}

.chart-container.loading::before {
  opacity: 1;
}

@keyframes spin {
  0% { transform: translate(-50%, -50%) rotate(0deg); }
  100% { transform: translate(-50%, -50%) rotate(360deg); }
}

/* Custom scrollbar for charts */
.chart::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.chart::-webkit-scrollbar-track {
  background: transparent;
}

.chart::-webkit-scrollbar-thumb {
  background: var(--color-border-base);
  border-radius: var(--border-radius-round);
}

.chart::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-placeholder);
}
</style>
