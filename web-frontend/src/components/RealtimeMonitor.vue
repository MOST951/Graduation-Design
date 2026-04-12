<template>
  <div class="realtime-monitor">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: 采集进度 -->
      <el-tab-pane label="采集进度" name="progress">
        <div class="progress-container">
          <!-- 环形进度图 -->
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="progress-ring-wrapper">
                <el-progress
                  type="circle"
                  :percentage="overallProgress"
                  :width="180"
                  :stroke-width="12"
                  :color="progressColors"
                >
                  <template #default>
                    <div class="progress-inner">
                      <div class="progress-value">{{ overallProgress }}%</div>
                      <div class="progress-label">整体进度</div>
                    </div>
                  </template>
                </el-progress>
                <div class="progress-status">
                  <el-tag :type="statusType" size="large">{{ statusText }}</el-tag>
                </div>
              </div>
            </el-col>

            <!-- 指标卡片 -->
            <el-col :span="16">
              <el-row :gutter="16">
                <el-col :span="12">
                  <div class="metric-card success">
                    <div class="metric-icon">
                      <el-icon><SuccessFilled /></el-icon>
                    </div>
                    <div class="metric-info">
                      <div class="metric-value">{{ formatNumber(metrics.collected) }}</div>
                      <div class="metric-label">已采集</div>
                    </div>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="metric-card danger">
                    <div class="metric-icon">
                      <el-icon><CircleCloseFilled /></el-icon>
                    </div>
                    <div class="metric-info">
                      <div class="metric-value">{{ formatNumber(metrics.failed) }}</div>
                      <div class="metric-label">失败数</div>
                    </div>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="metric-card primary">
                    <div class="metric-icon">
                      <el-icon><TrendCharts /></el-icon>
                    </div>
                    <div class="metric-info">
                      <div class="metric-value">{{ metrics.successRate }}%</div>
                      <div class="metric-label">成功率</div>
                    </div>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="metric-card warning">
                    <div class="metric-icon">
                      <el-icon><Odometer /></el-icon>
                    </div>
                    <div class="metric-info">
                      <div class="metric-value">{{ metrics.speed }}</div>
                      <div class="metric-label">条/分钟</div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </el-col>
          </el-row>

          <!-- 平台分布饼图 -->
          <div class="platform-chart-wrapper">
            <div class="section-title">平台数据分布</div>
            <div id="platform-chart" style="width: 100%; height: 280px;"></div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 实时日志 -->
      <el-tab-pane label="实时日志" name="logs">
        <div class="logs-container">
          <!-- 日志工具栏 -->
          <div class="logs-toolbar">
            <el-select v-model="logLevel" placeholder="日志级别" style="width: 120px;">
              <el-option label="全部" value="all" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARN" value="WARN" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
            <el-switch v-model="autoScroll" active-text="自动滚动" style="margin-left: 15px;" />
            <div class="toolbar-right">
              <el-button size="small" @click="clearLogs">
                <el-icon><Delete /></el-icon> 清空日志
              </el-button>
              <el-button size="small" type="primary" @click="exportLogs">
                <el-icon><Download /></el-icon> 导出日志
              </el-button>
            </div>
          </div>

          <!-- 日志显示区域 -->
          <el-scrollbar ref="logScrollbar" class="logs-scrollbar" height="400px">
            <div class="logs-content">
              <div
                v-for="(log, index) in filteredLogs"
                :key="index"
                :class="['log-line', `log-${log.level.toLowerCase()}`]"
              >
                <span class="log-time">{{ log.time }}</span>
                <span :class="['log-level', `level-${log.level.toLowerCase()}`]">[{{ log.level }}]</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
              <div v-if="filteredLogs.length === 0" class="logs-empty">
                暂无日志
              </div>
            </div>
          </el-scrollbar>

          <!-- 连接状态 -->
          <div class="connection-status">
            <el-tag :type="wsConnected ? 'success' : 'danger'" size="small">
              <el-icon><Connection /></el-icon>
              {{ wsConnected ? 'WebSocket 已连接' : 'WebSocket 未连接' }}
            </el-tag>
            <span class="log-count">共 {{ logs.length }} 条日志</span>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 数据预览 -->
      <el-tab-pane label="数据预览" name="preview">
        <div class="preview-container">
          <div class="preview-header">
            <span>最新采集数据（实时更新）</span>
            <el-button size="small" @click="refreshPreview">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>

          <el-table :data="previewData" style="width: 100%" highlight-current-row @row-click="handleRowClick">
            <el-table-column prop="content" label="内容" min-width="300">
              <template #default="{ row }">
                <div class="content-cell">{{ truncateText(row.content, 80) }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="getSourceType(row.source)">{{ row.source }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="时间" width="170" />
            <el-table-column prop="url" label="原始链接" width="120">
              <template #default="{ row }">
                <el-link type="primary" :href="row.url" target="_blank" :underline="false">
                  <el-icon><Link /></el-icon> 查看
                </el-link>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 数据详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="数据详情" width="600px">
      <div v-if="selectedData" class="data-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="内容">
            <div class="detail-content">{{ selectedData.content }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="getSourceType(selectedData.source)">{{ selectedData.source }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="采集时间">{{ selectedData.time }}</el-descriptions-item>
          <el-descriptions-item label="原始链接">
            <el-link type="primary" :href="selectedData.url" target="_blank">{{ selectedData.url }}</el-link>
          </el-descriptions-item>
          <el-descriptions-item label="作者">{{ selectedData.author || '-' }}</el-descriptions-item>
          <el-descriptions-item label="互动数据">
            点赞: {{ selectedData.likes || 0 }} | 评论: {{ selectedData.comments || 0 }} | 转发: {{ selectedData.shares || 0 }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import {
  SuccessFilled, CircleCloseFilled, TrendCharts, Odometer,
  Delete, Download, Connection, Refresh, Link
} from '@element-plus/icons-vue';
import { useReconnectingWebSocket } from '@/composables/useReconnect';

// Tab 状态
const activeTab = ref('progress');

// ========== 采集进度相关 ==========
const overallProgress = ref(0);
const metrics = reactive({
  collected: 0,
  failed: 0,
  successRate: 0,
  speed: 0,
});

const progressColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#67c23a', percentage: 100 },
];

const statusType = computed(() => {
  if (overallProgress.value === 100) return 'success';
  if (overallProgress.value > 0) return 'primary';
  return 'info';
});

const statusText = computed(() => {
  if (overallProgress.value === 100) return '已完成';
  if (overallProgress.value > 0) return '采集中';
  return '等待中';
});

// 平台分布图表
let platformChart: echarts.ECharts | null = null;
const platformData = ref([
  { name: '微博', value: 0 },
  { name: '微信', value: 0 },
  { name: '抖音', value: 0 },
]);

function initPlatformChart() {
  const chartDom = document.getElementById('platform-chart');
  if (!chartDom) return;
  
  platformChart = echarts.init(chartDom);
  updatePlatformChart();
}

function updatePlatformChart() {
  if (!platformChart) return;
  
  platformChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 10, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: platformData.value.map((item, index) => ({
        ...item,
        itemStyle: { color: ['#ff6b6b', '#4ecdc4', '#45b7d1'][index] }
      })),
    }],
  });
}

// ========== 实时日志相关 ==========
interface LogEntry {
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
}

const logs = ref<LogEntry[]>([]);
const logLevel = ref('all');
const autoScroll = ref(true);
const logScrollbar = ref<any>(null);
const wsConnected = ref(false);

const filteredLogs = computed(() => {
  if (logLevel.value === 'all') return logs.value;
  return logs.value.filter(log => log.level === logLevel.value);
});

function addLog(level: LogEntry['level'], message: string) {
  const now = new Date();
  const time = now.toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(now.getMilliseconds()).padStart(3, '0');
  
  logs.value.push({ time, level, message });
  
  // 超过1000行自动清理
  if (logs.value.length > 1000) {
    logs.value = logs.value.slice(-800);
  }
  
  // 自动滚动
  if (autoScroll.value) {
    nextTick(() => {
      logScrollbar.value?.setScrollTop(999999);
    });
  }
}

function clearLogs() {
  logs.value = [];
}

function exportLogs() {
  const content = logs.value.map(log => `${log.time} [${log.level}] ${log.message}`).join('\n');
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `collection-logs-${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

// ========== 数据预览相关 ==========
interface PreviewItem {
  id: number;
  content: string;
  source: string;
  time: string;
  url: string;
  author?: string;
  likes?: number;
  comments?: number;
  shares?: number;
}

const previewData = ref<PreviewItem[]>([]);
const detailDialogVisible = ref(false);
const selectedData = ref<PreviewItem | null>(null);

function truncateText(text: string, maxLength: number) {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

function getSourceType(source: string) {
  const map: Record<string, string> = {
    '微博': 'danger',
    '微信': 'success',
    '抖音': 'primary',
  };
  return map[source] || 'info';
}

function handleRowClick(row: PreviewItem) {
  selectedData.value = row;
  detailDialogVisible.value = true;
}

function refreshPreview() {
  // 模拟刷新
  addLog('INFO', '刷新数据预览...');
}

// ========== WebSocket 连接 (auto-reconnect) ==========
let simulationTimer: number | null = null;

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.hostname}:8081/api/ws/collection`;

const { connect: connectWs, disconnect: disconnectWs } = useReconnectingWebSocket(wsUrl, {
  immediate: false,
  maxAttempts: 5,
  initialDelay: 1000,
  onOpen: () => {
    wsConnected.value = true;
    addLog('INFO', 'WebSocket 连接成功');
  },
  onParsedMessage: (data) => {
    handleWebSocketMessage(data as Record<string, unknown>);
  },
  onError: () => {
    addLog('ERROR', 'WebSocket 连接错误');
  },
  onStatusChange: (status) => {
    if (status === 'disconnected' && !wsConnected.value) {
      // 达到最大重连后降级到模拟数据
      addLog('WARN', 'WebSocket 重连失败，切换到模拟数据');
      startSimulation();
    } else if (status === 'reconnecting') {
      wsConnected.value = false;
      addLog('WARN', 'WebSocket 连接断开，正在重连…');
    }
  },
});

function handleWebSocketMessage(data: Record<string, unknown>) {
  if (data.type === 'progress') {
    overallProgress.value = data.progress;
    metrics.collected = data.collected;
    metrics.failed = data.failed;
    metrics.successRate = data.successRate;
    metrics.speed = data.speed;
  } else if (data.type === 'platform') {
    platformData.value = data.platforms;
    updatePlatformChart();
  } else if (data.type === 'log') {
    addLog(data.level, data.message);
  } else if (data.type === 'data') {
    previewData.value.unshift(data.item);
    if (previewData.value.length > 10) {
      previewData.value.pop();
    }
  }
}

// 模拟数据（WebSocket 不可用时）
function startSimulation() {
  addLog('INFO', '启动模拟数据模式');
  
  // 初始化模拟数据
  previewData.value = [
    { id: 1, content: '今天天气真好，心情也跟着好起来了！#生活日常#', source: '微博', time: '2025-12-10 03:10:15', url: 'https://weibo.com/1', author: '用户A', likes: 128, comments: 23, shares: 5 },
    { id: 2, content: '新产品发布会圆满成功，感谢所有支持我们的用户！', source: '微信', time: '2025-12-10 03:09:42', url: 'https://mp.weixin.qq.com/1', author: '官方账号', likes: 1024, comments: 156, shares: 89 },
    { id: 3, content: '分享一个超实用的编程技巧，学会了效率翻倍！', source: '抖音', time: '2025-12-10 03:08:33', url: 'https://douyin.com/1', author: '技术博主', likes: 5678, comments: 432, shares: 234 },
    { id: 4, content: '这家店的奶茶真的绝了，强烈推荐芋泥波波！', source: '微博', time: '2025-12-10 03:07:21', url: 'https://weibo.com/2', author: '美食达人', likes: 89, comments: 12, shares: 3 },
    { id: 5, content: '周末去爬山，风景太美了，分享给大家看看', source: '微信', time: '2025-12-10 03:06:18', url: 'https://mp.weixin.qq.com/2', author: '旅行者', likes: 256, comments: 34, shares: 12 },
  ];
  
  platformData.value = [
    { name: '微博', value: 4521 },
    { name: '微信', value: 2834 },
    { name: '抖音', value: 1892 },
  ];
  
  metrics.collected = 9247;
  metrics.failed = 123;
  metrics.successRate = 98.7;
  metrics.speed = 156;
  overallProgress.value = 65;
  
  // 定时更新模拟数据
  simulationTimer = window.setInterval(() => {
    // 更新进度
    if (overallProgress.value < 100) {
      overallProgress.value = Math.min(100, overallProgress.value + Math.random() * 2);
    }
    
    // 更新指标
    metrics.collected += Math.floor(Math.random() * 10);
    metrics.failed += Math.random() > 0.9 ? 1 : 0;
    metrics.successRate = Number(((metrics.collected / (metrics.collected + metrics.failed)) * 100).toFixed(1));
    metrics.speed = Math.floor(100 + Math.random() * 100);
    
    // 更新平台数据
    platformData.value[0].value += Math.floor(Math.random() * 5);
    platformData.value[1].value += Math.floor(Math.random() * 3);
    platformData.value[2].value += Math.floor(Math.random() * 2);
    updatePlatformChart();
    
    // 添加随机日志
    const logTypes: LogEntry['level'][] = ['INFO', 'INFO', 'INFO', 'WARN', 'ERROR'];
    const messages = [
      '成功采集数据 1 条',
      '正在处理微博热搜数据...',
      '数据写入队列成功',
      '请求超时，正在重试...',
      '代理连接失败，切换备用代理',
      '数据解析完成',
      '发现新的热点话题',
    ];
    if (Math.random() > 0.5) {
      const level = logTypes[Math.floor(Math.random() * logTypes.length)];
      const message = messages[Math.floor(Math.random() * messages.length)];
      addLog(level, message);
    }
  }, 2000);
}

// ========== 工具函数 ==========
function formatNumber(num: number) {
  return num.toLocaleString();
}

// ========== 生命周期 ==========
onMounted(() => {
  nextTick(() => {
    initPlatformChart();
  });
  
  // 尝试连接 WebSocket（composable 处理重连，最终降级到模拟数据）
  connectWs();
  
  window.addEventListener('resize', () => platformChart?.resize());
});

onUnmounted(() => {
  disconnectWs();
  if (simulationTimer) clearInterval(simulationTimer);
  platformChart?.dispose();
  window.removeEventListener('resize', () => platformChart?.resize());
});

// 切换到进度 tab 时刷新图表
watch(activeTab, (tab) => {
  if (tab === 'progress') {
    nextTick(() => {
      platformChart?.resize();
    });
  }
});
</script>

<style scoped>
.realtime-monitor {
  background: #fff;
  border-radius: 4px;
}

/* 采集进度样式 */
.progress-container {
  padding: 20px;
}
.progress-ring-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}
.progress-inner {
  text-align: center;
}
.progress-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}
.progress-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
.progress-status {
  margin-top: 15px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}
.metric-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}
.metric-card .metric-icon {
  font-size: 36px;
  margin-right: 15px;
}
.metric-card.success .metric-icon { color: #67c23a; }
.metric-card.danger .metric-icon { color: #f56c6c; }
.metric-card.primary .metric-icon { color: #409eff; }
.metric-card.warning .metric-icon { color: #e6a23c; }
.metric-info .metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
.metric-info .metric-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.platform-chart-wrapper {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
.section-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 15px;
}

/* 实时日志样式 */
.logs-container {
  padding: 15px;
}
.logs-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}
.toolbar-right {
  margin-left: auto;
  display: flex;
  gap: 10px;
}
.logs-scrollbar {
  background: #1e1e1e;
  border-radius: 4px;
}
.logs-content {
  padding: 15px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.log-line {
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-time {
  color: #6a9955;
  margin-right: 10px;
}
.log-level {
  margin-right: 10px;
  font-weight: bold;
}
.level-info { color: #4fc3f7; }
.level-warn { color: #ffb74d; }
.level-error { color: #ef5350; }
.log-message { color: #d4d4d4; }
.log-warn .log-message { color: #ffb74d; }
.log-error .log-message { color: #ef5350; }
.logs-empty {
  color: #6a9955;
  text-align: center;
  padding: 40px;
}
.connection-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
.log-count {
  font-size: 12px;
  color: #909399;
}

/* 数据预览样式 */
.preview-container {
  padding: 15px;
}
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  font-weight: bold;
  color: #303133;
}
.content-cell {
  line-height: 1.5;
  color: #606266;
}
.data-detail .detail-content {
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
