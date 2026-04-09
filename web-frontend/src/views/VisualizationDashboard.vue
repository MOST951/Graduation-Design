<template>
  <div class="visualization-dashboard">
    <!-- 顶部控制栏 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h2>数据可视化</h2>
        <el-radio-group v-model="currentDashboard" size="small" @change="handleDashboardChange">
          <el-radio-button label="overview">舆情概览</el-radio-button>
          <el-radio-button label="sentiment">情感分析</el-radio-button>
          <el-radio-button label="topics">热点话题</el-radio-button>
          <el-radio-button label="users">用户画像</el-radio-button>
          <el-radio-button label="realtime">实时监控</el-radio-button>
          <el-radio-button label="propagation">传播路径</el-radio-button>
        </el-radio-group>
      </div>
      <div class="header-right">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          value-format="YYYY-MM-DD"
          :shortcuts="dateShortcuts"
          @change="handleDateChange"
        />
        <el-button :icon="Refresh" size="small" :loading="isLoading" @click="refreshData">刷新</el-button>
        <el-button :icon="FullScreen" size="small" :type="isFullscreen ? 'primary' : 'default'" @click="toggleFullscreen">
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </el-button>
        <el-dropdown @command="handleExport">
          <el-button size="small">
            导出 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="dashboard">导出仪表盘</el-dropdown-item>
              <el-dropdown-item command="png">导出为图片</el-dropdown-item>
              <el-dropdown-item command="pdf">导出为PDF</el-dropdown-item>
              <el-dropdown-item command="excel">导出数据</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 舆情概览仪表盘 -->
    <div v-if="currentDashboard === 'overview'" class="dashboard-content">
      <!-- 核心指标卡片 -->
      <el-row :gutter="16" class="metric-row">
        <el-col :span="6">
          <div class="metric-card primary">
            <div class="metric-icon"><el-icon><Document /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ formatNumber(overviewData.totalPosts) }}</div>
              <div class="metric-label">微博总量</div>
              <div class="metric-trend" :class="overviewData.postsTrend >= 0 ? 'up' : 'down'">
                <el-icon><component :is="overviewData.postsTrend >= 0 ? 'CaretTop' : 'CaretBottom'" /></el-icon>
                {{ Math.abs(overviewData.postsTrend) }}%
              </div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card success">
            <div class="metric-icon"><el-icon><CircleCheck /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ overviewData.positiveRate }}%</div>
              <div class="metric-label">正面情感占比</div>
              <div class="metric-trend up"><el-icon><CaretTop /></el-icon>{{ overviewData.positiveTrend }}%</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card danger">
            <div class="metric-icon"><el-icon><CircleClose /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ overviewData.negativeRate }}%</div>
              <div class="metric-label">负面情感占比</div>
              <div class="metric-trend down"><el-icon><CaretBottom /></el-icon>{{ overviewData.negativeTrend }}%</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card warning">
            <div class="metric-icon"><el-icon><Warning /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ overviewData.hotTopics }}</div>
              <div class="metric-label">热点话题数</div>
              <div class="metric-trend up"><el-icon><CaretTop /></el-icon>{{ overviewData.topicsTrend }}%</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 图表区域 -->
      <el-row :gutter="16">
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>舆情趋势分析</span>
                <el-radio-group v-model="trendTimeRange" size="small">
                  <el-radio-button label="7d">7天</el-radio-button>
                  <el-radio-button label="30d">30天</el-radio-button>
                  <el-radio-button label="90d">90天</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div ref="trendChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>情感分布</span></template>
            <div ref="sentimentPieRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>热门话题TOP10</span></template>
            <div ref="topicsBarRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>地域分布</span></template>
            <div ref="regionMapRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 情感分析仪表盘 -->
    <div v-else-if="currentDashboard === 'sentiment'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>情感极性分布</span></template>
            <div ref="sentimentDonutRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>情感趋势对比</span>
                <el-checkbox-group v-model="sentimentTypes" size="small">
                  <el-checkbox label="positive">正面</el-checkbox>
                  <el-checkbox label="negative">负面</el-checkbox>
                  <el-checkbox label="neutral">中性</el-checkbox>
                </el-checkbox-group>
              </div>
            </template>
            <div ref="sentimentTrendRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>情感强度分布</span></template>
            <div ref="intensityHistogramRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>情感-互动关系</span></template>
            <div ref="sentimentScatterRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header><span>情感词云</span></template>
            <div ref="sentimentWordCloudRef" class="chart-container" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 热点话题仪表盘 -->
    <div v-else-if="currentDashboard === 'topics'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>话题热度排行</span></template>
            <div ref="topicRankRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>话题词云</span></template>
            <div ref="topicWordCloudRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header><span>话题热度趋势</span></template>
            <div ref="topicTrendRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>话题情感构成</span></template>
            <div ref="topicSentimentRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header><span>话题传播时间线</span></template>
            <div ref="topicTimelineRef" class="chart-container" style="height: 250px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 用户画像仪表盘 -->
    <div v-else-if="currentDashboard === 'users'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>用户活跃度分布</span></template>
            <div ref="userActivityRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>用户认证类型</span></template>
            <div ref="userVerifyRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>粉丝数分布</span></template>
            <div ref="userFollowersRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>用户发布时段分析</span></template>
            <div ref="userTimeHeatmapRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>用户影响力雷达图</span></template>
            <div ref="userInfluenceRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header><span>用户地域分布</span></template>
            <div ref="userRegionRef" class="chart-container" style="height: 350px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 传播路径仪表盘 -->
    <div v-else-if="currentDashboard === 'propagation'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="18">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>微博传播路径图</span>
                <div style="display:flex;gap:8px;align-items:center">
                  <el-select v-model="propagationTopic" size="small" style="width:160px" @change="updatePropagationChart">
                    <el-option label="#科技创新#" value="tech" />
                    <el-option label="#春节档电影#" value="movie" />
                    <el-option label="#健康生活#" value="health" />
                  </el-select>
                  <el-button size="small" @click="exportChart('propagation', 'png')">PNG</el-button>
                  <el-button size="small" @click="exportChart('propagation', 'pdf')">PDF</el-button>
                </div>
              </div>
            </template>
            <div ref="propagationGraphRef" class="chart-container" style="height: 500px"></div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="chart-card">
            <template #header><span>传播统计</span></template>
            <div class="prop-stats">
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.totalNodes }}</div><div class="prop-lbl">涉及用户</div></div>
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.totalEdges }}</div><div class="prop-lbl">转发链路</div></div>
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.maxDepth }}</div><div class="prop-lbl">最大深度</div></div>
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.avgRepost }}</div><div class="prop-lbl">平均转发</div></div>
            </div>
          </el-card>
          <el-card class="chart-card" style="margin-top:16px">
            <template #header><span>关键传播节点</span></template>
            <div class="key-nodes">
              <div v-for="node in keyPropagationNodes" :key="node.name" class="key-node-item">
                <el-avatar :size="32">{{ node.name.charAt(0) }}</el-avatar>
                <div class="key-node-info">
                  <div class="key-node-name">{{ node.name }}</div>
                  <div class="key-node-meta">转发 {{ node.reposts }} | 粉丝 {{ node.followers }}</div>
                </div>
              </div>
            </div>
          </el-card>
          <el-card class="chart-card" style="margin-top:16px">
            <template #header><span>图例</span></template>
            <div class="graph-legend">
              <div class="legend-row"><span class="legend-circle" :style="{background: DANGER}"></span> 原始发布者</div>
              <div class="legend-row"><span class="legend-circle" :style="{background: WARNING}"></span> 认证用户 (大V)</div>
              <div class="legend-row"><span class="legend-circle" :style="{background: PRIMARY}"></span> 普通用户</div>
              <div class="legend-row"><span class="legend-line"></span> 转发关系</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 实时监控仪表盘 -->
    <div v-else-if="currentDashboard === 'realtime'" class="dashboard-content">
      <el-row :gutter="16" class="metric-row">
        <el-col :span="6">
          <div class="metric-card realtime">
            <div class="metric-icon pulse"><el-icon><Connection /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.currentRate }}</div>
              <div class="metric-label">当前采集速率/分钟</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card realtime">
            <div class="metric-icon"><el-icon><Timer /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.todayTotal }}</div>
              <div class="metric-label">今日采集总量</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card realtime">
            <div class="metric-icon"><el-icon><DataAnalysis /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.analyzedCount }}</div>
              <div class="metric-label">已分析数量</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card" :class="realtimeData.alertCount > 0 ? 'danger' : 'success'">
            <div class="metric-icon"><el-icon><Bell /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.alertCount }}</div>
              <div class="metric-label">预警数量</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>实时数据流</span>
                <el-tag :type="isStreaming ? 'success' : 'info'" size="small">
                  {{ isStreaming ? '实时更新中' : '已暂停' }}
                </el-tag>
                <el-switch v-model="isStreaming" size="small" style="margin-left: 12px" />
              </div>
            </template>
            <div ref="realtimeLineRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>实时情感分布</span></template>
            <div ref="realtimePieRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card>
            <template #header><span>最新微博动态</span></template>
            <el-table :data="latestPosts" max-height="300" size="small">
              <el-table-column prop="time" label="时间" width="100" />
              <el-table-column prop="content" label="内容" show-overflow-tooltip />
              <el-table-column prop="sentiment" label="情感" width="80">
                <template #default="{ row }">
                  <el-tag :type="getSentimentTagType(row.sentiment)" size="small">{{ row.sentiment }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="likes" label="点赞" width="80" />
              <el-table-column prop="reposts" label="转发" width="80" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import {
  Refresh, ArrowDown, Document, CircleCheck, CircleClose, Warning,
  CaretTop, CaretBottom, Connection, Timer, DataAnalysis, Bell, FullScreen,
} from '@element-plus/icons-vue';
import { SUCCESS, PRIMARY, PRIMARY_LIGHT, DANGER, INFO, WARNING } from '@/styles/colors';

// ==================== 状态定义 ====================
const currentDashboard = ref('overview');
const dateRange = ref<string[]>([]);
const isLoading = ref(false);
const trendTimeRange = ref('7d');
const sentimentTypes = ref(['positive', 'negative', 'neutral']);
const isStreaming = ref(true);
const isFullscreen = ref(false);
const selectedSentiment = ref<string | null>(null);
const propagationLoading = ref(false);
const hotWeiboList = ref([
  { id: 1, title: ' ', content: '...', reposts: 5000, likes: 12000 },
  { id: 2, title: ' ', content: '...', reposts: 3200, likes: 8900 },
  { id: 3, title: ' ', content: '...', reposts: 2800, likes: 7600 },
]);

// 传播路径
const propagationGraphRef = ref<HTMLElement>();
const propagationTopic = ref('tech');
const propagationStats = ref({ totalNodes: 42, totalEdges: 56, maxDepth: 5, avgRepost: 3.2 });
const keyPropagationNodes = ref([
  { name: '科技媒体', reposts: 1280, followers: '520万' },
  { name: '行业大V', reposts: 890, followers: '320万' },
  { name: '热搜用户', reposts: 560, followers: '180万' },
  { name: '普通达人', reposts: 340, followers: '45万' },
]);

// 图表引用
const trendChartRef = ref<HTMLElement>();
const sentimentPieRef = ref<HTMLElement>();
const topicsBarRef = ref<HTMLElement>();
const regionMapRef = ref<HTMLElement>();
const sentimentDonutRef = ref<HTMLElement>();
const sentimentTrendRef = ref<HTMLElement>();
const intensityHistogramRef = ref<HTMLElement>();
const sentimentScatterRef = ref<HTMLElement>();
const sentimentWordCloudRef = ref<HTMLElement>();
const topicRankRef = ref<HTMLElement>();
const topicWordCloudRef = ref<HTMLElement>();
const topicTrendRef = ref<HTMLElement>();
const topicSentimentRef = ref<HTMLElement>();
const topicTimelineRef = ref<HTMLElement>();
const userActivityRef = ref<HTMLElement>();
const userVerifyRef = ref<HTMLElement>();
const userFollowersRef = ref<HTMLElement>();
const userTimeHeatmapRef = ref<HTMLElement>();
const userInfluenceRef = ref<HTMLElement>();
const userRegionRef = ref<HTMLElement>();
const realtimeLineRef = ref<HTMLElement>();
const realtimePieRef = ref<HTMLElement>();

// 图表实例
const charts: echarts.ECharts[] = [];

// 数据
const overviewData = ref({
  totalPosts: 125680,
  postsTrend: 12.5,
  positiveRate: 45.2,
  positiveTrend: 3.2,
  negativeRate: 18.6,
  negativeTrend: 2.1,
  hotTopics: 28,
  topicsTrend: 15.3,
});

const realtimeData = ref({
  currentRate: 156,
  todayTotal: 23456,
  analyzedCount: 22890,
  alertCount: 3,
});

const latestPosts = ref([
  { time: '10:32:15', content: '今天天气真好，心情也很棒！#美好生活#', sentiment: '正面', likes: 128, reposts: 23 },
  { time: '10:31:58', content: '这个产品质量太差了，完全不值这个价格', sentiment: '负面', likes: 56, reposts: 12 },
  { time: '10:31:42', content: '刚看完这部电影，剧情一般般吧', sentiment: '中性', likes: 34, reposts: 5 },
  { time: '10:31:25', content: '强烈推荐这家餐厅，味道超级棒！', sentiment: '正面', likes: 89, reposts: 18 },
  { time: '10:31:08', content: '等了一个小时还没送到，差评！', sentiment: '负面', likes: 45, reposts: 8 },
]);

// 日期快捷选项
const dateShortcuts = [
  { text: '最近7天', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 7); return [start, end]; } },
  { text: '最近30天', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 30); return [start, end]; } },
  { text: '最近90天', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 90); return [start, end]; } },
];

// ==================== 工具函数 ====================
const formatNumber = (num: number) => num.toLocaleString();

const getSentimentTagType = (sentiment: string) => {
  const types: Record<string, any> = { '正面': 'success', '负面': 'danger', '中性': 'info' };
  return types[sentiment] || 'info';
};

// ==================== 图表初始化 ====================
const initChart = (el: HTMLElement | undefined, option: echarts.EChartsOption) => {
  if (!el) return null;
  const chart = echarts.init(el);
  chart.setOption(option);
  charts.push(chart);
  return chart;
};

const initOverviewCharts = () => {
  // 舆情趋势图
  initChart(trendChartRef.value, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['微博数量', '正面', '负面', '中性'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: generateDates(7) },
    yAxis: { type: 'value' },
    series: [
      { name: '微博数量', type: 'line', smooth: true, data: [1200, 1320, 1010, 1340, 900, 1230, 1100], areaStyle: { opacity: 0.1 } },
      { name: '正面', type: 'line', smooth: true, data: [540, 594, 454, 603, 405, 553, 495], lineStyle: { color: SUCCESS }, itemStyle: { color: SUCCESS } },
      { name: '负面', type: 'line', smooth: true, data: [216, 237, 182, 241, 162, 221, 198], lineStyle: { color: DANGER }, itemStyle: { color: DANGER } },
      { name: '中性', type: 'line', smooth: true, data: [444, 489, 374, 496, 333, 456, 407], lineStyle: { color: INFO }, itemStyle: { color: INFO } },
    ],
  });

  // 情感分布饼图
  initChart(sentimentPieRef.value, {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: [
        { value: 45.2, name: '正面', itemStyle: { color: SUCCESS } },
        { value: 18.6, name: '负面', itemStyle: { color: DANGER } },
        { value: 36.2, name: '中性', itemStyle: { color: INFO } },
      ],
    }],
  });

  // 热门话题柱状图
  initChart(topicsBarRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: ['#春节档电影#', '#科技创新#', '#健康生活#', '#教育改革#', '#环保行动#', '#美食推荐#', '#旅游攻略#', '#职场话题#', '#体育赛事#', '#娱乐八卦#'].reverse() },
    series: [{
      type: 'bar',
      data: [8520, 7830, 6540, 5890, 5230, 4780, 4320, 3980, 3560, 3120],
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: PRIMARY }, { offset: 1, color: SUCCESS }]), borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  });

  // 地域分布（简化版柱状图代替地图）
  initChart(regionMapRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['北京', '上海', '广东', '江苏', '浙江', '四川', '湖北', '山东', '河南', '福建'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [15680, 14230, 12890, 9870, 8960, 7650, 6890, 6540, 5980, 5230],
      itemStyle: { color: PRIMARY, borderRadius: [4, 4, 0, 0] },
    }],
  });
};

const initSentimentCharts = () => {
  // 情感极性环形图
  initChart(sentimentDonutRef.value, {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10 },
      label: { show: true, formatter: '{b}: {d}%' },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      data: [
        { value: 45200, name: '正面', itemStyle: { color: SUCCESS } },
        { value: 18600, name: '负面', itemStyle: { color: DANGER } },
        { value: 36200, name: '中性', itemStyle: { color: INFO } },
      ],
    }],
  });

  // 情感趋势对比
  initChart(sentimentTrendRef.value, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '负面', '中性'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: generateDates(14) },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '正面', type: 'line', smooth: true, data: generateRandomData(14, 400, 600), lineStyle: { color: SUCCESS }, itemStyle: { color: SUCCESS }, areaStyle: { color: 'rgba(0, 180, 42, 0.1)' } },
      { name: '负面', type: 'line', smooth: true, data: generateRandomData(14, 150, 250), lineStyle: { color: DANGER }, itemStyle: { color: DANGER }, areaStyle: { color: 'rgba(245, 63, 63, 0.1)' } },
      { name: '中性', type: 'line', smooth: true, data: generateRandomData(14, 300, 450), lineStyle: { color: INFO }, itemStyle: { color: INFO }, areaStyle: { color: 'rgba(134, 144, 156, 0.1)' } },
    ],
  });

  // 情感强度分布
  initChart(intensityHistogramRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['极负面', '负面', '轻微负面', '中性', '轻微正面', '正面', '极正面'], axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: [
        { value: 2100, itemStyle: { color: '#c45656' } },
        { value: 5800, itemStyle: { color: DANGER } },
        { value: 8900, itemStyle: { color: '#fab6b6' } },
        { value: 36200, itemStyle: { color: INFO } },
        { value: 12300, itemStyle: { color: '#b3e19d' } },
        { value: 18500, itemStyle: { color: SUCCESS } },
        { value: 5200, itemStyle: { color: '#529b2e' } },
      ],
      barWidth: '60%',
    }],
  });

  // 情感-互动散点图
  initChart(sentimentScatterRef.value, {
    tooltip: { trigger: 'item', formatter: (params: any) => `情感分数: ${params.value[0]}<br/>互动量: ${params.value[1]}` },
    xAxis: { type: 'value', name: '情感分数', min: -1, max: 1 },
    yAxis: { type: 'value', name: '互动量' },
    series: [{
      type: 'scatter',
      symbolSize: 10,
      data: generateScatterData(100),
      itemStyle: { color: (params: any) => params.value[0] > 0.3 ? SUCCESS : params.value[0] < -0.3 ? DANGER : INFO },
    }],
  });

  // 情感词云（简化为柱状图）
  initChart(sentimentWordCloudRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['喜欢', '推荐', '满意', '开心', '失望', '差评', '垃圾', '不错', '一般', '还行', '超棒', '难吃'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [
        { value: 2890, itemStyle: { color: SUCCESS } },
        { value: 2450, itemStyle: { color: SUCCESS } },
        { value: 2100, itemStyle: { color: SUCCESS } },
        { value: 1890, itemStyle: { color: SUCCESS } },
        { value: 1560, itemStyle: { color: DANGER } },
        { value: 1230, itemStyle: { color: DANGER } },
        { value: 980, itemStyle: { color: DANGER } },
        { value: 1780, itemStyle: { color: SUCCESS } },
        { value: 1450, itemStyle: { color: INFO } },
        { value: 1320, itemStyle: { color: INFO } },
        { value: 1680, itemStyle: { color: SUCCESS } },
        { value: 890, itemStyle: { color: DANGER } },
      ],
    }],
  });
};

const initTopicsCharts = () => {
  // 话题热度排行
  initChart(topicRankRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: ['#春节档电影#', '#科技创新#', '#健康生活#', '#教育改革#', '#环保行动#', '#美食推荐#', '#旅游攻略#', '#职场话题#'].reverse() },
    series: [{
      type: 'bar',
      data: [8520, 7830, 6540, 5890, 5230, 4780, 4320, 3980],
      itemStyle: { color: (params: any) => [DANGER, WARNING, WARNING, PRIMARY, PRIMARY, PRIMARY, SUCCESS, SUCCESS][params.dataIndex], borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  });

  // 话题词云（柱状图代替）
  initChart(topicWordCloudRef.value, {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '70%',
      data: [
        { value: 8520, name: '春节档电影' },
        { value: 7830, name: '科技创新' },
        { value: 6540, name: '健康生活' },
        { value: 5890, name: '教育改革' },
        { value: 5230, name: '环保行动' },
        { value: 4780, name: '美食推荐' },
      ],
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
    }],
  });

  // 话题热度趋势
  initChart(topicTrendRef.value, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['春节档电影', '科技创新', '健康生活'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: generateDates(7) },
    yAxis: { type: 'value' },
    series: [
      { name: '春节档电影', type: 'line', smooth: true, data: [1200, 1800, 2500, 3200, 2800, 2100, 1500] },
      { name: '科技创新', type: 'line', smooth: true, data: [800, 950, 1100, 1250, 1400, 1300, 1150] },
      { name: '健康生活', type: 'line', smooth: true, data: [600, 720, 850, 980, 920, 880, 810] },
    ],
  });

  // 话题情感构成
  initChart(topicSentimentRef.value, {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: 52, name: '正面', itemStyle: { color: SUCCESS } },
        { value: 28, name: '中性', itemStyle: { color: INFO } },
        { value: 20, name: '负面', itemStyle: { color: DANGER } },
      ],
    }],
  });

  // 话题传播时间线
  initChart(topicTimelineRef.value, {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'] },
    yAxis: { type: 'value', name: '讨论量' },
    series: [{
      type: 'line',
      smooth: true,
      data: [120, 80, 45, 60, 350, 680, 520, 450, 380, 620, 780, 450],
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(22, 93, 255, 0.5)' }, { offset: 1, color: 'rgba(22, 93, 255, 0.1)' }]) },
      lineStyle: { color: PRIMARY, width: 2 },
      itemStyle: { color: PRIMARY },
    }],
  });
};

const initUsersCharts = () => {
  // 用户活跃度分布
  initChart(userActivityRef.value, {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 35, name: '高活跃', itemStyle: { color: SUCCESS } },
        { value: 45, name: '中活跃', itemStyle: { color: PRIMARY } },
        { value: 20, name: '低活跃', itemStyle: { color: INFO } },
      ],
    }],
  });

  // 用户认证类型
  initChart(userVerifyRef.value, {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: 15, name: '蓝V认证', itemStyle: { color: PRIMARY } },
        { value: 8, name: '黄V认证', itemStyle: { color: WARNING } },
        { value: 77, name: '普通用户', itemStyle: { color: INFO } },
      ],
    }],
  });

  // 粉丝数分布
  initChart(userFollowersRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['<100', '100-1k', '1k-10k', '10k-100k', '100k-1M', '>1M'] },
    yAxis: { type: 'value', name: '用户数' },
    series: [{
      type: 'bar',
      data: [12500, 35600, 28900, 15200, 5800, 1200],
      itemStyle: { color: PRIMARY, borderRadius: [4, 4, 0, 0] },
    }],
  });

  // 用户发布时段热力图
  initChart(userTimeHeatmapRef.value, {
    tooltip: { position: 'top', formatter: (params: any) => `${params.value[1]}:00 周${['日', '一', '二', '三', '四', '五', '六'][params.value[0]]}: ${params.value[2]}条` },
    grid: { height: '70%', top: '10%' },
    xAxis: { type: 'category', data: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'], splitArea: { show: true } },
    yAxis: { type: 'category', data: ['0', '3', '6', '9', '12', '15', '18', '21'], splitArea: { show: true } },
    visualMap: { min: 0, max: 500, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%', inRange: { color: ['#f5f5f5', PRIMARY] } },
    series: [{ type: 'heatmap', data: generateHeatmapData(), label: { show: false } }],
  });

  // 用户影响力雷达图
  initChart(userInfluenceRef.value, {
    tooltip: {},
    radar: { indicator: [{ name: '发帖量', max: 100 }, { name: '互动率', max: 100 }, { name: '粉丝数', max: 100 }, { name: '转发量', max: 100 }, { name: '评论量', max: 100 }, { name: '点赞量', max: 100 }] },
    series: [{ type: 'radar', data: [{ value: [85, 72, 68, 78, 82, 90], name: '平均影响力', areaStyle: { color: 'rgba(22, 93, 255, 0.3)' }, lineStyle: { color: PRIMARY }, itemStyle: { color: PRIMARY } }] }],
  });

  // 用户地域分布
  initChart(userRegionRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['北京', '上海', '广东', '江苏', '浙江', '四川', '湖北', '山东', '河南', '福建', '湖南', '河北'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [18500, 16800, 15200, 12300, 11500, 9800, 8900, 8200, 7600, 6800, 6200, 5800],
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: PRIMARY }, { offset: 1, color: SUCCESS }]), borderRadius: [4, 4, 0, 0] },
    }],
  });
};

const initRealtimeCharts = () => {
  // 实时数据流
  initChart(realtimeLineRef.value, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['采集量', '分析量'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: generateTimeLabels(20) },
    yAxis: { type: 'value' },
    series: [
      { name: '采集量', type: 'line', smooth: true, data: generateRandomData(20, 100, 200), areaStyle: { opacity: 0.3 }, lineStyle: { color: PRIMARY }, itemStyle: { color: PRIMARY } },
      { name: '分析量', type: 'line', smooth: true, data: generateRandomData(20, 90, 180), areaStyle: { opacity: 0.3 }, lineStyle: { color: SUCCESS }, itemStyle: { color: SUCCESS } },
    ],
  });

  // 实时情感分布
  initChart(realtimePieRef.value, {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 48, name: '正面', itemStyle: { color: SUCCESS } },
        { value: 32, name: '中性', itemStyle: { color: INFO } },
        { value: 20, name: '负面', itemStyle: { color: DANGER } },
      ],
    }],
  });
};

// ==================== 传播路径图 ====================
const generatePropagationData = () => {
  const nodes: any[] = [];
  const links: any[] = [];
  const categories = ['原始发布', '认证用户', '普通用户'];

  // Root node
  nodes.push({ id: '0', name: '原始发布者', symbolSize: 50, category: 0, itemStyle: { color: DANGER } });
  let nodeId = 1;

  // Level 1: verified users
  const l1Count = 3 + Math.floor(Math.random() * 3);
  for (let i = 0; i < l1Count; i++) {
    const id = String(nodeId++);
    nodes.push({ id, name: `大V_${i + 1}`, symbolSize: 35, category: 1, itemStyle: { color: WARNING } });
    links.push({ source: '0', target: id });
    // Level 2: regular users from each verified
    const l2Count = 2 + Math.floor(Math.random() * 5);
    for (let j = 0; j < l2Count; j++) {
      const id2 = String(nodeId++);
      nodes.push({ id: id2, name: `用户_${nodeId}`, symbolSize: 15 + Math.floor(Math.random() * 15), category: 2, itemStyle: { color: PRIMARY } });
      links.push({ source: id, target: id2 });
      // Level 3: occasional deeper
      if (Math.random() > 0.6) {
        const id3 = String(nodeId++);
        nodes.push({ id: id3, name: `用户_${nodeId}`, symbolSize: 10 + Math.floor(Math.random() * 10), category: 2, itemStyle: { color: PRIMARY_LIGHT } });
        links.push({ source: id2, target: id3 });
      }
    }
  }

  propagationStats.value = {
    totalNodes: nodes.length,
    totalEdges: links.length,
    maxDepth: 4,
    avgRepost: Number((links.length / l1Count).toFixed(1)),
  };

  return { nodes, links, categories: categories.map(c => ({ name: c })) };
};

const initPropagationChart = () => {
  const { nodes, links, categories } = generatePropagationData();
  initChart(propagationGraphRef.value, {
    tooltip: { formatter: (params: any) => params.dataType === 'node' ? `${params.data.name}<br/>影响力: ${params.data.symbolSize}` : `${params.data.source} → ${params.data.target}` },
    legend: [{ data: categories.map((c: any) => c.name), orient: 'vertical', right: 10, top: 20 }],
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      categories: categories,
      roam: true,
      label: { show: true, position: 'right', fontSize: 10 },
      force: { repulsion: 200, gravity: 0.1, edgeLength: [50, 150], layoutAnimation: true },
      lineStyle: { color: 'source', curveness: 0.3, opacity: 0.6 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    }],
  });
};

const updatePropagationChart = () => {
  // Re-init with new random data for selected topic
  if (propagationGraphRef.value) {
    const existing = echarts.getInstanceByDom(propagationGraphRef.value);
    if (existing) existing.dispose();
    // Remove from charts array
    const idx = charts.findIndex(c => c === existing);
    if (idx !== -1) charts.splice(idx, 1);
  }
  initPropagationChart();
};

// ==================== 辅助函数 ====================
const generateDates = (days: number) => {
  const dates = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push(`${d.getMonth() + 1}/${d.getDate()}`);
  }
  return dates;
};

const generateTimeLabels = (count: number) => {
  const labels = [];
  const now = new Date();
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 60000);
    labels.push(`${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`);
  }
  return labels;
};

const generateRandomData = (count: number, min: number, max: number) => {
  return Array.from({ length: count }, () => Math.floor(Math.random() * (max - min) + min));
};

const generateScatterData = (count: number) => {
  return Array.from({ length: count }, () => [
    (Math.random() * 2 - 1).toFixed(2),
    Math.floor(Math.random() * 1000),
  ]);
};

const generateHeatmapData = () => {
  const data = [];
  for (let i = 0; i < 7; i++) {
    for (let j = 0; j < 8; j++) {
      data.push([i, j, Math.floor(Math.random() * 500)]);
    }
  }
  return data;
};

// ==================== 事件处理 ====================
const handleDashboardChange = async () => {
  await nextTick();
  charts.forEach(c => c.dispose());
  charts.length = 0;
  
  switch (currentDashboard.value) {
    case 'overview': initOverviewCharts(); break;
    case 'sentiment': initSentimentCharts(); break;
    case 'topics': initTopicsCharts(); break;
    case 'users': initUsersCharts(); break;
    case 'realtime': initRealtimeCharts(); break;
    case 'propagation': initPropagationChart(); break;
  }
};

const handleDateChange = () => {
  refreshData();
};

const refreshData = async () => {
  isLoading.value = true;
  await new Promise(r => setTimeout(r, 500));
  handleDashboardChange();
  isLoading.value = false;
  ElMessage.success('数据已刷新');
};

const exportAllChartsPNG = () => {
  if (charts.length === 0) { ElMessage.warning('暂无图表可导出'); return; }
  charts.forEach((chart, idx) => {
    const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
    const link = document.createElement('a');
    link.href = url;
    link.download = `chart_${currentDashboard.value}_${idx + 1}_${Date.now()}.png`;
    link.click();
  });
  ElMessage.success(`已导出 ${charts.length} 张图表图片`);
};

const exportAllChartsPDF = () => {
  if (charts.length === 0) { ElMessage.warning('暂无图表可导出'); return; }
  // Export each chart as PNG then trigger download (simple approach without jspdf)
  charts.forEach((chart, idx) => {
    const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
    const link = document.createElement('a');
    link.href = url;
    link.download = `chart_${currentDashboard.value}_${idx + 1}_${Date.now()}.png`;
    link.click();
  });
  ElMessage.success(`已导出 ${charts.length} 张图表 (高清PNG格式)`);
};

const exportChart = (chartName: string, format: string) => {
  let chart: echarts.ECharts | null = null;
  if (chartName === 'propagation' && propagationGraphRef.value) {
    chart = echarts.getInstanceByDom(propagationGraphRef.value) || null;
  }
  if (!chart) { ElMessage.warning('图表未初始化'); return; }
  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
  const link = document.createElement('a');
  link.href = url;
  link.download = `${chartName}_${Date.now()}.png`;
  link.click();
  ElMessage.success(`已导出 ${chartName} 图表`);
};

// ==================== 新增功能 ====================
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
  
  if (isFullscreen.value) {
    document.documentElement.requestFullscreen?.();
    document.body.classList.add('fullscreen-dashboard');
  } else {
    document.exitFullscreen?.();
    document.body.classList.remove('fullscreen-dashboard');
  }
  
  nextTick(() => {
    charts.forEach(c => c.resize());
  });
};

const setupChartLinkage = () => {
  if (sentimentPieRef.value) {
    const chart = echarts.getInstanceByDom(sentimentPieRef.value);
    if (chart) {
      chart.on('click', (params: any) => {
        selectedSentiment.value = params.name;
        filterChartsBySentiment(params.name);
        ElMessage.info(`已选中 ${params.name} 情感`);
      });
    }
  }
};

const filterChartsBySentiment = (sentiment: string) => {
  const trendChart = echarts.getInstanceByDom(trendChartRef.value);
  if (trendChart && sentiment === '正面') {
    const option = trendChart.getOption();
    if (option.series) {
      option.series.forEach((series: any) => {
        if (series.name === '正面') {
          series.emphasis = { focus: 'series' };
          series.lineStyle = { width: 4 };
        } else {
          series.lineStyle = { opacity: 0.3, type: 'dashed' };
        }
      });
      trendChart.setOption(option);
    }
  }
  
  const wordCloudChart = echarts.getInstanceByDom(sentimentWordCloudRef.value);
  if (wordCloudChart) {
    const sentimentWords = {
      '正面': ['好', '棒', '赞', '喜欢', '支持'],
      '中性': ['一般', '还行', '不错', '可以', '还好'],
      '负面': ['不好', '差', '不满', '反对', '不喜欢']
    };
    
    const words = sentimentWords[sentiment as keyof typeof sentimentWords] || [];
    const option = {
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        data: words.map((word, idx) => ({
          name: word,
          value: Math.floor(Math.random() * 100) + 50,
          textStyle: {
            color: sentiment === '正面' ? SUCCESS : sentiment === '负面' ? DANGER : INFO
          }
        }))
      }]
    };
    wordCloudChart.setOption(option);
  }
};

const loadPropagationNetwork = async (weiboId: number) => {
  propagationLoading.value = true;
  
  try {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const { nodes, links, categories } = generatePropagationData();
    
    if (propagationGraphRef.value) {
      const existing = echarts.getInstanceByDom(propagationGraphRef.value);
      if (existing) existing.dispose();
      
      const chart = echarts.init(propagationGraphRef.value);
      chart.setOption({
        tooltip: { 
          formatter: (params: any) => params.dataType === 'node' 
            ? `${params.data.name}<br/>影响力: ${params.data.symbolSize}<br/>转发数: ${params.data.reposts || 0}<br/>粉丝数: ${params.data.followers || 0}`
            : `${params.data.source} → ${params.data.target}` 
        },
        legend: [{ data: categories.map((c: any) => c.name), orient: 'vertical', right: 10, top: 20 }],
        series: [{
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: categories,
          roam: true,
          label: { show: true, position: 'right', fontSize: 10 },
          force: { repulsion: 300, gravity: 0.1, edgeLength: [80, 200], layoutAnimation: true },
          lineStyle: { color: 'source', curveness: 0.3, opacity: 0.7, width: 2 },
          emphasis: { 
            focus: 'adjacency', 
            lineStyle: { width: 4 },
            itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0, 0, 0, 0.3)' }
          },
          animationDuration: 1500,
          animationEasing: 'elasticOut'
        }],
      });
      
      charts.push(chart);
    }
    
    ElMessage.success('已加载传播网络');
  } catch (error) {
    ElMessage.error('加载传播网络失败');
  } finally {
    propagationLoading.value = false;
  }
};

const exportDashboardAsImage = async () => {
  try {
    const { default: html2canvas } = await import('html2canvas');
    
    const dashboard = document.querySelector('.visualization-dashboard') as HTMLElement;
    if (!dashboard) {
      ElMessage.error('无法找到仪表板元素');
      return;
    }
    
    const canvas = await html2canvas(dashboard, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
      allowTaint: true
    });
    
    const link = document.createElement('a');
    link.href = canvas.toDataURL('image/png');
    link.download = `dashboard_${currentDashboard.value}_${Date.now()}.png`;
    link.click();
    
    ElMessage.success('已导出仪表板图片');
  } catch (error) {
    ElMessage.error('导出仪表板图片失败');
    exportAllChartsPNG();
  }
};

const handleExport = (type: string) => {
  if (type === 'dashboard') {
    exportDashboardAsImage();
  } else if (type === 'png') {
    exportAllChartsPNG();
  } else if (type === 'pdf') {
    exportAllChartsPDF();
  } else {
    ElMessage.info('正在导出数据...');
  }
};

// ==================== 生命周期 ====================
let resizeHandler: () => void;
let realtimeTimer: number;

onMounted(() => {
  initOverviewCharts();
  
  resizeHandler = () => charts.forEach(c => c.resize());
  window.addEventListener('resize', resizeHandler);
  
  // 
  setupChartLinkage();
  
  // 
  realtimeTimer = window.setInterval(() => {
    if (currentDashboard.value === 'realtime' && isStreaming.value) {
      realtimeData.value.currentRate = Math.floor(Math.random() * 50 + 130);
      realtimeData.value.todayTotal += Math.floor(Math.random() * 10);
      realtimeData.value.analyzedCount += Math.floor(Math.random() * 8);
    }
  }, 3000);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler);
  clearInterval(realtimeTimer);
  charts.forEach(c => c.dispose());
});

watch(trendTimeRange, () => {
  if (currentDashboard.value === 'overview') {
    handleDashboardChange();
  }
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.visualization-dashboard {
  padding: $spacing-md;
  background: $bg-page;
  min-height: calc(100vh - 120px);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  padding: $spacing-base $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    h2 { margin: 0; font-size: $font-size-extra-large; font-weight: $font-weight-semibold; }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

.dashboard-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.metric-row {
  margin-bottom: $spacing-base;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: $spacing-base;
  padding: $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  .metric-icon {
    width: 56px;
    height: 56px;
    border-radius: $border-radius-medium;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-hero;
    
    &.pulse {
      animation: pulse 2s infinite;
    }
  }
  
  &.primary .metric-icon { background: rgba($primary-color, 0.08); color: $primary-color; }
  &.success .metric-icon { background: rgba($success-color, 0.1); color: $success-color; }
  &.danger .metric-icon { background: rgba($danger-color, 0.08); color: $danger-color; }
  &.warning .metric-icon { background: rgba($warning-color, 0.1); color: $warning-color; }
  &.realtime .metric-icon { background: rgba($info-color, 0.1); color: $info-color; }
  
  .metric-info {
    flex: 1;
    .metric-value { font-size: $font-size-hero; font-weight: $font-weight-bold; color: $text-primary; line-height: 1.2; }
    .metric-label { font-size: $font-size-base; color: $text-secondary; margin-top: $spacing-xxs; }
    .metric-trend {
      display: inline-flex;
      align-items: center;
      font-size: $font-size-small;
      margin-top: 6px;
      &.up { color: $success-color; }
      &.down { color: $danger-color; }
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.chart-card {
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  :deep(.el-card__header) {
    padding: $spacing-sm $spacing-base;
    border-bottom: 1px solid $border-light;
    font-weight: $font-weight-medium;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.chart-container {
  height: 300px;
  padding: $spacing-sm;
}

.prop-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-sm;
  text-align: center;

  .prop-stat-item {
    padding: $spacing-sm;
    background: $bg-page;
    border-radius: $border-radius-small;

    .prop-val {
      font-size: 22px;
      font-weight: $font-weight-bold;
      color: $primary-color;
    }

    .prop-lbl {
      font-size: $font-size-tiny;
      color: $text-secondary;
      margin-top: 2px;
    }
  }
}

.key-nodes {
  .key-node-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-xs 0;
    border-bottom: 1px solid $border-light;

    &:last-child { border-bottom: none; }

    .key-node-info {
      .key-node-name { font-weight: $font-weight-medium; font-size: $font-size-small; color: $text-primary; }
      .key-node-meta { font-size: $font-size-tiny; color: $text-secondary; margin-top: 2px; }
    }
  }
}

.graph-legend {
  .legend-row {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: 6px 0;
    font-size: $font-size-small;
    color: $text-regular;
  }

  .legend-circle {
    width: 12px;
    height: 12px;
    border-radius: $border-radius-circle;
    display: inline-block;
  }

  .legend-line {
    width: 24px;
    height: 2px;
    background: $text-placeholder;
    display: inline-block;
  }
}

// 
:global(.fullscreen-dashboard) {
  .visualization-dashboard {
    padding: 0;
    background: #000;
    min-height: 100vh;
    
    .dashboard-header {
      display: none;
    }
    
    .dashboard-content {
      height: 100vh;
      overflow: hidden;
      
      .chart-card {
        height: 50vh;
        margin-bottom: 0;
        
        .chart-container {
          height: 100% !important;
        }
      }
      
      .metric-row {
        .el-col {
          margin-bottom: 0;
        }
      }
    }
  }
  
  // 
  .el-header,
  .el-aside,
  .el-footer {
    display: none !important;
  }
  
  .el-main {
    padding: 0 !important;
    margin: 0 !important;
  }
}

// 
@media (max-width: 768px) {
  .visualization-dashboard {
    padding: $spacing-sm;
    
    .dashboard-header {
      flex-direction: column;
      gap: $spacing-sm;
      
      .header-left {
        flex-direction: column;
        gap: $spacing-sm;
        width: 100%;
        
        h2 {
          font-size: $font-size-large;
        }
        
        .el-radio-group {
          width: 100%;
          overflow-x: auto;
          flex-wrap: nowrap;
        }
      }
      
      .header-right {
        flex-wrap: wrap;
        justify-content: center;
        gap: $spacing-xs;
        
        .el-button,
        .el-dropdown {
          flex: 1;
          min-width: 0;
        }
      }
    }
    
    .dashboard-content {
      .metric-row {
        .el-col {
          margin-bottom: $spacing-sm;
        }
      }
      
      .chart-card {
        margin-bottom: $spacing-sm;
        
        .card-header {
          flex-direction: column;
          gap: $spacing-sm;
          align-items: flex-start;
        }
      }
    }
  }
  
  .metric-card {
    flex-direction: column;
    text-align: center;
    gap: $spacing-sm;
    
    .metric-icon {
      width: 48px;
      height: 48px;
      font-size: $font-size-large;
    }
    
    .metric-info {
      .metric-value {
        font-size: $font-size-large;
      }
      
      .metric-label {
        font-size: $font-size-small;
      }
    }
  }
  
  .chart-container {
    height: 250px !important;
  }
  
  .prop-stats {
    grid-template-columns: 1fr;
  }
  
  .key-nodes {
    .key-node-item {
      flex-direction: column;
      align-items: flex-start;
      gap: $spacing-xs;
    }
  }
}

// 
@media (max-width: 480px) {
  .visualization-dashboard {
    padding: $spacing-xs;
    
    .dashboard-header {
      .header-left {
        h2 {
          font-size: $font-size-medium;
        }
      }
      
      .header-right {
        .el-button {
          font-size: $font-size-tiny;
          padding: 6px 12px;
        }
      }
    }
  }
  
  .metric-card {
    padding: $spacing-sm;
    
    .metric-icon {
      width: 40px;
      height: 40px;
      font-size: $font-size-medium;
    }
    
    .metric-info {
      .metric-value {
        font-size: $font-size-medium;
      }
      
      .metric-label {
        font-size: $font-size-tiny;
      }
    }
  }
  
  .chart-container {
    height: 200px !important;
    padding: $spacing-xs;
  }
}
</style>
