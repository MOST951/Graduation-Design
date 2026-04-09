<template>
  <div class="realtime-dashboard">
    <!-- 连接状态栏 -->
    <div class="connection-bar">
      <div class="connection-status">
        <span :class="['status-dot', connectionStatus]"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <div class="connection-actions">
        <el-button v-if="connectionStatus === 'disconnected'" size="small" type="primary" @click="connect">
          连接
        </el-button>
        <el-button v-else size="small" @click="disconnect">断开</el-button>
        <span class="connection-stats">
          收: {{ formatBytes(connectionStats.bytesReceived) }} | 
          发: {{ formatBytes(connectionStats.bytesSent) }}
        </span>
      </div>
    </div>

    <el-row :gutter="15">
      <!-- 区域1: 核心指标 -->
      <el-col :span="8">
        <el-card shadow="never" class="metrics-card">
          <template #header>
            <div class="card-header">
              <span>核心指标</span>
              <el-tag :type="isNegativeAlert ? 'danger' : 'success'" size="small">
                {{ isNegativeAlert ? '预警' : '正常' }}
              </el-tag>
            </div>
          </template>

          <div class="metrics-grid">
            <!-- 在线用户 -->
            <div class="metric-item">
              <div class="metric-icon" style="background: #409eff;">
                <el-icon><User /></el-icon>
              </div>
              <div class="metric-content">
                <div class="metric-value">{{ formatNumber(stats?.onlineUsers || 0) }}</div>
                <div class="metric-label">在线用户</div>
                <div :class="['metric-trend', (stats?.onlineUsersTrend || 0) > 0 ? 'up' : 'down']">
                  {{ (stats?.onlineUsersTrend || 0) > 0 ? '↑' : '↓' }}
                  {{ Math.abs(stats?.onlineUsersTrend || 0).toFixed(1) }}%
                </div>
              </div>
            </div>

            <!-- 每秒新增 -->
            <div class="metric-item">
              <div class="metric-icon" style="background: #67c23a;">
                <el-icon><Document /></el-icon>
              </div>
              <div class="metric-content">
                <div class="metric-value">{{ stats?.newWeiboPerSecond || 0 }}</div>
                <div class="metric-label">新增/秒</div>
                <div :class="['metric-trend', (stats?.newWeiboTrend || 0) > 0 ? 'up' : 'down']">
                  {{ (stats?.newWeiboTrend || 0) > 0 ? '↑' : '↓' }}
                  {{ Math.abs(stats?.newWeiboTrend || 0).toFixed(1) }}%
                </div>
              </div>
            </div>

            <!-- 情感得分仪表盘 -->
            <div class="metric-item gauge-item">
              <div class="gauge-label">情感得分</div>
              <div id="sentiment-gauge" class="gauge-chart"></div>
            </div>

            <!-- 负面占比 -->
            <div class="metric-item negative-item">
              <div class="negative-header">
                <span class="negative-label">负面舆情占比</span>
                <span :class="['negative-value', isNegativeAlert ? 'alert' : '']">
                  {{ (stats?.negativeRatio || 0).toFixed(1) }}%
                </span>
              </div>
              <el-progress
                :percentage="stats?.negativeRatio || 0"
                :stroke-width="12"
                :color="getNegativeColor(stats?.negativeRatio || 0)"
              />
              <div class="threshold-line" :style="{ left: '25%' }">
                <span class="threshold-label">阈值 25%</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 区域2: 实时情感分布 -->
      <el-col :span="8">
        <el-card shadow="never" class="sentiment-card">
          <template #header>
            <div class="card-header">
              <span>实时情感分布</span>
              <span class="update-time">{{ sentimentDist?.timestamp ? formatTime(sentimentDist.timestamp) : '--' }}</span>
            </div>
          </template>
          <div id="sentiment-pie" class="chart-container"></div>
          <div class="sentiment-legend">
            <div class="legend-item">
              <span class="legend-dot positive"></span>
              <span class="legend-label">正面</span>
              <span class="legend-value">{{ sentimentDist?.positive || 0 }}%</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot neutral"></span>
              <span class="legend-label">中性</span>
              <span class="legend-value">{{ sentimentDist?.neutral || 0 }}%</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot negative"></span>
              <span class="legend-label">负面</span>
              <span class="legend-value">{{ sentimentDist?.negative || 0 }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 区域3: 实时词云 -->
      <el-col :span="8">
        <el-card shadow="never" class="wordcloud-card">
          <template #header>
            <div class="card-header">
              <span>实时热词 (近5分钟)</span>
              <el-button text size="small" @click="refreshWordCloud">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          <div id="realtime-wordcloud" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 区域4: 实时微博流 -->
    <el-card shadow="never" class="stream-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>实时微博流</span>
            <el-tag type="info" size="small">{{ filteredWeibos.length }} 条</el-tag>
          </div>
          <div class="header-right">
            <!-- 情感筛选 -->
            <el-select v-model="streamFilter.sentiment" placeholder="情感筛选" clearable size="small" style="width: 100px;">
              <el-option label="全部" value="" />
              <el-option label="正面" value="positive" />
              <el-option label="中性" value="neutral" />
              <el-option label="负面" value="negative" />
            </el-select>
            <!-- 关键词搜索 -->
            <el-input
              v-model="streamFilter.keyword"
              placeholder="关键词高亮"
              size="small"
              style="width: 150px;"
              clearable
            />
            <!-- 暂停/继续 -->
            <el-button :type="streamPaused ? 'success' : 'warning'" size="small" @click="togglePause">
              <el-icon>
                <VideoPlay v-if="streamPaused" />
                <VideoPause v-else />
              </el-icon>
              {{ streamPaused ? '继续' : '暂停' }}
            </el-button>
            <!-- 清空 -->
            <el-button size="small" @click="clearStream">清空</el-button>
          </div>
        </div>
      </template>

      <div class="weibo-stream" ref="streamRef">
        <transition-group name="weibo-list">
          <div
            v-for="weibo in filteredWeibos"
            :key="weibo.id"
            :class="['weibo-item', weibo.sentiment]"
          >
            <div class="weibo-avatar">
              <el-avatar :size="40" :src="weibo.userAvatar">{{ weibo.userName.charAt(0) }}</el-avatar>
              <el-icon v-if="weibo.userVerified" class="verified-icon"><CircleCheckFilled /></el-icon>
            </div>
            <div class="weibo-content">
              <div class="weibo-header">
                <span class="user-name">{{ weibo.userName }}</span>
                <el-tag :type="getSentimentType(weibo.sentiment)" size="small">
                  {{ getSentimentLabel(weibo.sentiment) }}
                </el-tag>
                <span class="weibo-time">{{ formatRelativeTime(weibo.time) }}</span>
              </div>
              <div class="weibo-text" v-html="highlightKeyword(weibo.content)"></div>
              <div class="weibo-meta">
                <span v-if="weibo.location">
                  <el-icon><Location /></el-icon>
                  {{ weibo.location }}
                </span>
                <span><el-icon><ChatDotRound /></el-icon> {{ weibo.comments }}</span>
                <span><el-icon><Share /></el-icon> {{ weibo.reposts }}</span>
                <span><el-icon><Star /></el-icon> {{ weibo.likes }}</span>
              </div>
            </div>
          </div>
        </transition-group>
        
        <el-empty v-if="filteredWeibos.length === 0" description="暂无数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import {
  User, Document, Refresh, VideoPlay, VideoPause, CircleCheckFilled,
  Location, ChatDotRound, Share, Star
} from '@element-plus/icons-vue';
import { useRealtimeStore } from '@/store/realtime';
import { storeToRefs } from 'pinia';

const realtimeStore = useRealtimeStore();
const {
  stats,
  sentimentDist,
  wordCloud,
  filteredWeibos,
  connectionStatus,
  connectionStats,
  streamPaused,
  streamFilter,
  isNegativeAlert,
} = storeToRefs(realtimeStore);

const streamRef = ref<HTMLElement>();

// 图表实例
let gaugeChart: echarts.ECharts | null = null;
let pieChart: echarts.ECharts | null = null;
let wordCloudChart: echarts.ECharts | null = null;

// 状态文本
const statusText = computed(() => {
  const map: Record<string, string> = {
    connected: '已连接',
    connecting: '连接中...',
    disconnected: '未连接',
  };
  return map[connectionStatus.value];
});

// 初始化仪表盘
function initGaugeChart() {
  const dom = document.getElementById('sentiment-gauge');
  if (!dom) return;

  gaugeChart = echarts.init(dom);
  updateGaugeChart();
}

function updateGaugeChart() {
  if (!gaugeChart) return;

  const score = (stats.value?.sentimentScore || 0.5) * 100;
  gaugeChart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 100,
      radius: '100%',
      center: ['50%', '75%'],
      axisLine: {
        lineStyle: {
          width: 15,
          color: [
            [0.3, '#f56c6c'],
            [0.7, '#e6a23c'],
            [1, '#67c23a'],
          ],
        },
      },
      pointer: { show: true, length: '60%', width: 4 },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      detail: {
        formatter: '{value}',
        fontSize: 20,
        fontWeight: 'bold',
        offsetCenter: [0, '20%'],
        color: score > 70 ? '#67c23a' : score > 30 ? '#e6a23c' : '#f56c6c',
      },
      data: [{ value: score.toFixed(0) }],
    }],
  });
}

// 初始化饼图
function initPieChart() {
  const dom = document.getElementById('sentiment-pie');
  if (!dom) return;

  pieChart = echarts.init(dom);
  updatePieChart();
}

function updatePieChart() {
  if (!pieChart || !sentimentDist.value) return;

  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '50%'],
      data: [
        { value: sentimentDist.value.positive, name: '正面', itemStyle: { color: '#67c23a' } },
        { value: sentimentDist.value.neutral, name: '中性', itemStyle: { color: '#909399' } },
        { value: sentimentDist.value.negative, name: '负面', itemStyle: { color: '#f56c6c' } },
      ],
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
      },
    }],
  });

  pieChart.on('click', (params: any) => {
    realtimeStore.setStreamFilter({ sentiment: params.name === '正面' ? 'positive' : params.name === '负面' ? 'negative' : 'neutral' });
  });
}

// 初始化词云
function initWordCloudChart() {
  const dom = document.getElementById('realtime-wordcloud');
  if (!dom) return;

  wordCloudChart = echarts.init(dom);
  updateWordCloudChart();
}

function updateWordCloudChart() {
  if (!wordCloudChart || !wordCloud.value) return;

  wordCloudChart.setOption({
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [12, 40],
      rotationRange: [-45, 45],
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'Microsoft YaHei',
        fontWeight: 'bold',
        color: () => `hsl(${Math.random() * 360}, 70%, 50%)`,
      },
      data: wordCloud.value.words.map(w => ({
        name: w.name,
        value: w.value,
      })),
    }],
  });
}

// 事件处理
function connect() {
  realtimeStore.connectWebSocket();
  realtimeStore.startAutoRefresh();
}

function disconnect() {
  realtimeStore.disconnectWebSocket();
  realtimeStore.stopAutoRefresh();
}

function togglePause() {
  realtimeStore.toggleStreamPause();
}

function clearStream() {
  realtimeStore.clearWeibos();
}

function refreshWordCloud() {
  realtimeStore.fetchWordCloud();
}

// 工具函数
function formatNumber(num: number) {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toLocaleString();
}

function formatBytes(bytes: number) {
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + 'MB';
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + 'KB';
  return bytes + 'B';
}

function formatTime(time: string) {
  return new Date(time).toLocaleTimeString('zh-CN');
}

function formatRelativeTime(time: string) {
  const diff = Date.now() - new Date(time).getTime();
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
  return new Date(time).toLocaleDateString('zh-CN');
}

function getNegativeColor(ratio: number) {
  if (ratio >= 30) return '#f56c6c';
  if (ratio >= 25) return '#e6a23c';
  return '#67c23a';
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger' };
  return map[sentiment] || 'info';
}

function getSentimentLabel(sentiment: string) {
  const map: Record<string, string> = { positive: '正面', neutral: '中性', negative: '负面' };
  return map[sentiment] || '未知';
}

function highlightKeyword(content: string) {
  if (!streamFilter.value.keyword) return content;
  const regex = new RegExp(`(${streamFilter.value.keyword})`, 'gi');
  return content.replace(regex, '<span class="highlight">$1</span>');
}

// 监听数据变化
watch(stats, () => {
  updateGaugeChart();
});

watch(sentimentDist, () => {
  updatePieChart();
});

watch(wordCloud, () => {
  updateWordCloudChart();
});

// 窗口大小变化
function handleResize() {
  gaugeChart?.resize();
  pieChart?.resize();
  wordCloudChart?.resize();
}

// 生命周期
onMounted(async () => {
  await realtimeStore.initialize();
  
  nextTick(() => {
    initGaugeChart();
    initPieChart();
    initWordCloudChart();
  });
  
  realtimeStore.startAutoRefresh();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  realtimeStore.stopAutoRefresh();
  gaugeChart?.dispose();
  pieChart?.dispose();
  wordCloudChart?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.realtime-dashboard {
  padding: 15px;
}

/* 连接状态栏 */
.connection-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.connected { background: #67c23a; }
.status-dot.connecting { background: #e6a23c; }
.status-dot.disconnected { background: #909399; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 13px;
  color: #606266;
}

.connection-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.connection-stats {
  font-size: 12px;
  color: #909399;
}

/* 卡片 */
.metrics-card, .sentiment-card, .wordcloud-card, .stream-card {
  margin-bottom: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.update-time {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

/* 核心指标 */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
}

.metric-content {
  flex: 1;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.metric-label {
  font-size: 12px;
  color: #909399;
}

.metric-trend {
  font-size: 12px;
  font-weight: 500;
}

.metric-trend.up { color: #67c23a; }
.metric-trend.down { color: #f56c6c; }

.gauge-item {
  flex-direction: column;
  align-items: center;
}

.gauge-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.gauge-chart {
  width: 100%;
  height: 80px;
}

.negative-item {
  grid-column: span 2;
  flex-direction: column;
  align-items: stretch;
  position: relative;
}

.negative-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.negative-label {
  font-size: 13px;
  color: #606266;
}

.negative-value {
  font-size: 16px;
  font-weight: bold;
  color: #67c23a;
}

.negative-value.alert {
  color: #f56c6c;
}

.threshold-line {
  position: absolute;
  bottom: 12px;
  height: 20px;
  border-left: 2px dashed #e6a23c;
}

.threshold-label {
  position: absolute;
  top: -18px;
  left: 5px;
  font-size: 10px;
  color: #e6a23c;
  white-space: nowrap;
}

/* 情感分布 */
.chart-container {
  height: 200px;
}

.sentiment-legend {
  display: flex;
  justify-content: space-around;
  padding-top: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-dot.positive { background: #67c23a; }
.legend-dot.neutral { background: #909399; }
.legend-dot.negative { background: #f56c6c; }

.legend-label {
  font-size: 12px;
  color: #606266;
}

.legend-value {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
}

/* 微博流 */
.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.weibo-stream {
  max-height: 500px;
  overflow-y: auto;
  padding: 10px 0;
}

.weibo-item {
  display: flex;
  gap: 12px;
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
  transition: background 0.2s;
}

.weibo-item:hover {
  background: #f5f7fa;
}

.weibo-item.positive { border-left: 3px solid #67c23a; }
.weibo-item.neutral { border-left: 3px solid #909399; }
.weibo-item.negative { border-left: 3px solid #f56c6c; }

.weibo-avatar {
  position: relative;
}

.verified-icon {
  position: absolute;
  bottom: -2px;
  right: -2px;
  color: #e6a23c;
  background: #fff;
  border-radius: 50%;
}

.weibo-content {
  flex: 1;
  min-width: 0;
}

.weibo-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.user-name {
  font-weight: 500;
  color: #303133;
}

.weibo-time {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.weibo-text {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 8px;
}

.weibo-text :deep(.highlight) {
  background: #fef0f0;
  color: #f56c6c;
  padding: 0 2px;
  border-radius: 2px;
}

.weibo-meta {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #909399;
}

.weibo-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 动画 */
.weibo-list-enter-active {
  transition: all 0.3s ease;
}

.weibo-list-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
