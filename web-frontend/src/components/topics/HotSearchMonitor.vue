<template>
  <div class="hot-search-monitor">
    <!-- 控制栏 -->
    <div class="monitor-controls">
      <div class="control-left">
        <!-- 平台选择 -->
        <el-select v-model="platform" placeholder="选择平台" style="width: 120px;" @change="handlePlatformChange">
          <el-option label="微博" value="weibo">
            <span class="platform-option">
              <span class="platform-icon weibo">微</span>
              微博热搜
            </span>
          </el-option>
          <el-option label="百度" value="baidu">
            <span class="platform-option">
              <span class="platform-icon baidu">百</span>
              百度热搜
            </span>
          </el-option>
          <el-option label="知乎" value="zhihu">
            <span class="platform-option">
              <span class="platform-icon zhihu">知</span>
              知乎热榜
            </span>
          </el-option>
          <el-option label="抖音" value="douyin">
            <span class="platform-option">
              <span class="platform-icon douyin">抖</span>
              抖音热点
            </span>
          </el-option>
        </el-select>

        <!-- 刷新设置 -->
        <el-divider direction="vertical" />
        <span class="control-label">刷新：</span>
        <el-radio-group v-model="refreshMode" size="small">
          <el-radio-button label="auto">自动</el-radio-button>
          <el-radio-button label="manual">手动</el-radio-button>
        </el-radio-group>

        <el-select
          v-if="refreshMode === 'auto'"
          v-model="refreshInterval"
          size="small"
          style="width: 90px; margin-left: 10px;"
          @change="handleRefreshIntervalChange"
        >
          <el-option label="30秒" :value="30" />
          <el-option label="1分钟" :value="60" />
          <el-option label="5分钟" :value="300" />
        </el-select>

        <el-button v-if="refreshMode === 'manual'" size="small" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>

        <span class="last-update">
          <el-icon><Clock /></el-icon>
          {{ lastUpdateTime }}
        </span>
      </div>

      <div class="control-right">
        <el-button size="small" type="warning" @click="showAlertDialog">
          <el-icon><Bell /></el-icon>
          预警设置 ({{ alertKeywords.length }})
        </el-button>
        <el-button size="small" @click="exportData">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- 热搜榜单 -->
      <el-col :span="16">
        <el-card shadow="never" class="hotsearch-table-card">
          <template #header>
            <div class="card-header">
              <span>{{ platformName }}热搜榜</span>
              <div class="header-stats">
                <el-tag type="success" size="small">新入榜 {{ newCount }}</el-tag>
                <el-tag type="danger" size="small">上升 {{ riseCount }}</el-tag>
                <el-tag type="info" size="small">下降 {{ fallCount }}</el-tag>
              </div>
            </div>
          </template>

          <el-table
            :data="hotSearchList"
            :row-class-name="getRowClassName"
            max-height="600"
            v-loading="isLoading"
          >
            <!-- 排名 -->
            <el-table-column label="排名" width="80" fixed>
              <template #default="{ row }">
                <div class="rank-cell">
                  <span :class="['rank-num', `rank-${row.rank}`]">{{ row.rank }}</span>
                  <span :class="['rank-change', row.changeType]">
                    <template v-if="row.changeType === 'new'">✨</template>
                    <template v-else-if="row.changeType === 'rise'">↑{{ row.changeValue }}</template>
                    <template v-else-if="row.changeType === 'fall'">↓{{ row.changeValue }}</template>
                    <template v-else>→</template>
                  </span>
                </div>
              </template>
            </el-table-column>

            <!-- 话题名称 -->
            <el-table-column label="话题" min-width="200">
              <template #default="{ row }">
                <div class="topic-cell" @click="showTopicDetail(row)">
                  <span class="topic-title">{{ row.title }}</span>
                  <div class="topic-tags">
                    <el-tag v-if="row.isHot" type="danger" size="small" effect="dark">热</el-tag>
                    <el-tag v-if="row.isNew" type="warning" size="small" effect="dark">新</el-tag>
                    <el-tag v-if="row.isAd" type="info" size="small">广告</el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 热搜指数 -->
            <el-table-column label="热搜指数" width="150">
              <template #default="{ row }">
                <div class="heat-cell">
                  <span class="heat-value">{{ formatHeat(row.heat) }}</span>
                  <div class="mini-trend" :id="`trend-${row.rank}`"></div>
                </div>
              </template>
            </el-table-column>

            <!-- 情感倾向 -->
            <el-table-column label="情感" width="80">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.sentiment)" size="small">
                  {{ getSentimentLabel(row.sentiment) }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 讨论量 -->
            <el-table-column label="讨论量" width="100">
              <template #default="{ row }">{{ formatNumber(row.discussCount) }}</template>
            </el-table-column>

            <!-- 热度变化率 -->
            <el-table-column label="变化率" width="100">
              <template #default="{ row }">
                <span :class="['change-rate', row.changeRate > 0 ? 'up' : 'down']">
                  {{ row.changeRate > 0 ? '+' : '' }}{{ row.changeRate.toFixed(1) }}%
                </span>
              </template>
            </el-table-column>

            <!-- 上榜时长 -->
            <el-table-column label="上榜时长" width="100">
              <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
            </el-table-column>

            <!-- 操作 -->
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="addToMonitor(row)">
                  <el-icon><Bell /></el-icon>
                </el-button>
                <el-button type="success" link size="small" @click="analyzeTopic(row)">
                  <el-icon><DataAnalysis /></el-icon>
                </el-button>
                <el-button type="warning" link size="small" @click="shareTopic(row)">
                  <el-icon><Share /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 趋势分析 -->
      <el-col :span="8">
        <!-- 上榜时间分布 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <span>上榜时间分布</span>
          </template>
          <div id="time-distribution-heatmap" style="height: 200px;"></div>
        </el-card>

        <!-- 生命周期分析 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <div class="card-header">
              <span>话题生命周期</span>
              <el-select v-model="lifecycleTopic" size="small" style="width: 120px;">
                <el-option
                  v-for="item in hotSearchList.slice(0, 10)"
                  :key="item.rank"
                  :label="item.title.slice(0, 8) + '...'"
                  :value="item.rank"
                />
              </el-select>
            </div>
          </template>
          <div id="lifecycle-chart" style="height: 180px;"></div>
          <div class="lifecycle-stats">
            <div class="stat-item">
              <span class="stat-label">上榜时间</span>
              <span class="stat-value">{{ lifecycleData.startTime }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">峰值排名</span>
              <span class="stat-value highlight">#{{ lifecycleData.peakRank }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">当前阶段</span>
              <el-tag :type="getStageType(lifecycleData.stage)" size="small">
                {{ lifecycleData.stageLabel }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <!-- 传播路径 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <span>传播路径分析</span>
          </template>
          <div id="spread-path-chart" style="height: 200px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 预警设置弹窗 -->
    <el-dialog v-model="alertDialogVisible" title="预警设置" width="600px">
      <div class="alert-settings">
        <!-- 添加预警 -->
        <div class="add-alert">
          <el-input v-model="newAlertKeyword" placeholder="输入要监控的关键词" style="width: 200px;" />
          <el-select v-model="newAlertRank" placeholder="触发排名" style="width: 120px;">
            <el-option label="进入前10" :value="10" />
            <el-option label="进入前20" :value="20" />
            <el-option label="进入前50" :value="50" />
            <el-option label="任意上榜" :value="100" />
          </el-select>
          <el-select v-model="newAlertPlatform" placeholder="平台" style="width: 100px;">
            <el-option label="全部" value="all" />
            <el-option label="微博" value="weibo" />
            <el-option label="百度" value="baidu" />
            <el-option label="知乎" value="zhihu" />
            <el-option label="抖音" value="douyin" />
          </el-select>
          <el-button type="primary" @click="addAlert">添加</el-button>
        </div>

        <!-- 预警列表 -->
        <el-table :data="alertKeywords" style="margin-top: 15px;">
          <el-table-column prop="keyword" label="关键词" />
          <el-table-column prop="rankThreshold" label="触发排名" width="100">
            <template #default="{ row }">前{{ row.rankThreshold }}</template>
          </el-table-column>
          <el-table-column prop="platform" label="平台" width="80">
            <template #default="{ row }">{{ row.platform === 'all' ? '全部' : row.platform }}</template>
          </el-table-column>
          <el-table-column prop="enabled" label="状态" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row, $index }">
              <el-button type="danger" link size="small" @click="removeAlert($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 通知方式 -->
        <div class="notify-settings">
          <h4>通知方式</h4>
          <el-checkbox-group v-model="notifyMethods">
            <el-checkbox label="browser">浏览器通知</el-checkbox>
            <el-checkbox label="email">邮件通知</el-checkbox>
            <el-checkbox label="sms">短信通知</el-checkbox>
            <el-checkbox label="webhook">Webhook</el-checkbox>
          </el-checkbox-group>
        </div>
      </div>
    </el-dialog>

    <!-- 话题详情弹窗 -->
    <el-dialog v-model="topicDetailVisible" :title="selectedTopic?.title" width="700px">
      <div v-if="selectedTopic" class="topic-detail-dialog">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="当前排名">#{{ selectedTopic.rank }}</el-descriptions-item>
          <el-descriptions-item label="热搜指数">{{ formatHeat(selectedTopic.heat) }}</el-descriptions-item>
          <el-descriptions-item label="讨论量">{{ formatNumber(selectedTopic.discussCount) }}</el-descriptions-item>
          <el-descriptions-item label="上榜时间">{{ selectedTopic.onboardTime }}</el-descriptions-item>
          <el-descriptions-item label="上榜时长">{{ formatDuration(selectedTopic.duration) }}</el-descriptions-item>
          <el-descriptions-item label="情感倾向">
            <el-tag :type="getSentimentType(selectedTopic.sentiment)">
              {{ getSentimentLabel(selectedTopic.sentiment) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>热度趋势</h4>
          <div id="topic-heat-trend" style="height: 200px;"></div>
        </div>

        <div class="detail-section">
          <h4>相关微博</h4>
          <div class="related-weibos">
            <div v-for="(weibo, idx) in relatedWeibos" :key="idx" class="weibo-item">
              <div class="weibo-content">{{ weibo.content }}</div>
              <div class="weibo-meta">
                <span>@{{ weibo.author }}</span>
                <span>{{ weibo.likes }} 赞</span>
                <span>{{ weibo.time }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage, ElNotification } from 'element-plus';
import * as echarts from 'echarts';
import { Refresh, Clock, Bell, Download, DataAnalysis, Share } from '@element-plus/icons-vue';

// 平台设置
const platform = ref('weibo');
const platformName = computed(() => {
  const names: Record<string, string> = { weibo: '微博', baidu: '百度', zhihu: '知乎', douyin: '抖音' };
  return names[platform.value];
});

// 刷新设置
const refreshMode = ref('auto');
const refreshInterval = ref(60);
const lastUpdateTime = ref('刚刚');
let refreshTimer: number | null = null;

// 加载状态
const isLoading = ref(false);

// 热搜数据
interface HotSearchItem {
  rank: number;
  title: string;
  heat: number;
  changeType: 'new' | 'rise' | 'fall' | 'same';
  changeValue: number;
  sentiment: string;
  discussCount: number;
  changeRate: number;
  duration: number;
  isHot: boolean;
  isNew: boolean;
  isAd: boolean;
  onboardTime: string;
  trendData: number[];
}

const hotSearchList = ref<HotSearchItem[]>([]);

// 统计
const newCount = computed(() => hotSearchList.value.filter(i => i.changeType === 'new').length);
const riseCount = computed(() => hotSearchList.value.filter(i => i.changeType === 'rise').length);
const fallCount = computed(() => hotSearchList.value.filter(i => i.changeType === 'fall').length);

// 生命周期分析
const lifecycleTopic = ref(1);
const lifecycleData = reactive({
  startTime: '10:30',
  peakRank: 3,
  stage: 'peak',
  stageLabel: '峰值期',
});

// 预警设置
const alertDialogVisible = ref(false);
const alertKeywords = ref([
  { keyword: '品牌名', rankThreshold: 20, platform: 'all', enabled: true },
  { keyword: '竞品', rankThreshold: 10, platform: 'weibo', enabled: true },
]);
const newAlertKeyword = ref('');
const newAlertRank = ref(20);
const newAlertPlatform = ref('all');
const notifyMethods = ref(['browser']);

// 话题详情
const topicDetailVisible = ref(false);
const selectedTopic = ref<HotSearchItem | null>(null);
const relatedWeibos = ref<any[]>([]);

// 图表实例
let timeHeatmap: echarts.ECharts | null = null;
let lifecycleChart: echarts.ECharts | null = null;
let spreadChart: echarts.ECharts | null = null;
let topicTrendChart: echarts.ECharts | null = null;
const miniTrendCharts: Map<number, echarts.ECharts> = new Map();

// 生成模拟数据
function generateHotSearchData() {
  const titles = [
    '年度热词揭晓', '科技峰会召开', '明星官宣恋情', '新品发布会', '体育赛事决赛',
    '政策新规解读', '电影票房破纪录', '网红事件', '社会热点话题', '财经股市动态',
    '游戏新版本上线', '综艺节目热议', '教育改革方案', '健康养生话题', '美食探店推荐',
    '旅游景点推荐', '时尚潮流趋势', '汽车新能源', '房产市场分析', '职场话题讨论',
    '情感故事分享', '文化艺术展览', '环保公益活动', '国际新闻动态', '军事科技发展',
  ];

  hotSearchList.value = Array.from({ length: 50 }, (_, i) => {
    const changeTypes: ('new' | 'rise' | 'fall' | 'same')[] = ['new', 'rise', 'fall', 'same'];
    const changeType = i < 3 ? 'new' : changeTypes[Math.floor(Math.random() * 4)];
    
    return {
      rank: i + 1,
      title: titles[i % titles.length] + (i >= titles.length ? ` ${Math.floor(i / titles.length) + 1}` : ''),
      heat: Math.floor(Math.random() * 5000000 + 500000),
      changeType,
      changeValue: changeType === 'new' ? 0 : Math.floor(Math.random() * 10 + 1),
      sentiment: ['positive', 'neutral', 'negative'][Math.floor(Math.random() * 3)],
      discussCount: Math.floor(Math.random() * 100000 + 10000),
      changeRate: (Math.random() * 40 - 10),
      duration: Math.floor(Math.random() * 720 + 30),
      isHot: i < 3,
      isNew: changeType === 'new',
      isAd: Math.random() > 0.95,
      onboardTime: `${Math.floor(Math.random() * 12 + 8)}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
      trendData: Array.from({ length: 12 }, () => Math.floor(Math.random() * 100)),
    };
  });
}

// 初始化迷你趋势图
function initMiniTrendCharts() {
  hotSearchList.value.slice(0, 20).forEach(item => {
    const dom = document.getElementById(`trend-${item.rank}`);
    if (!dom) return;

    const chart = echarts.init(dom);
    chart.setOption({
      grid: { left: 0, right: 0, top: 0, bottom: 0 },
      xAxis: { type: 'category', show: false },
      yAxis: { type: 'value', show: false },
      series: [{
        type: 'line',
        data: item.trendData,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: item.changeRate > 0 ? '#67c23a' : '#f56c6c' },
        areaStyle: { color: item.changeRate > 0 ? 'rgba(103,194,58,0.2)' : 'rgba(245,108,108,0.2)' },
      }],
    });
    miniTrendCharts.set(item.rank, chart);
  });
}

// 初始化时间分布热力图
function initTimeHeatmap() {
  const dom = document.getElementById('time-distribution-heatmap');
  if (!dom) return;

  timeHeatmap = echarts.init(dom);
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  
  const data: [number, number, number][] = [];
  days.forEach((_, di) => {
    hours.forEach((_, hi) => {
      data.push([hi, di, Math.floor(Math.random() * 50)]);
    });
  });

  timeHeatmap.setOption({
    tooltip: { formatter: (p: any) => `${days[p.data[1]]} ${hours[p.data[0]]}: ${p.data[2]}条` },
    grid: { left: '15%', right: '5%', top: '5%', bottom: '15%' },
    xAxis: { type: 'category', data: hours, axisLabel: { fontSize: 9, interval: 3 } },
    yAxis: { type: 'category', data: days, axisLabel: { fontSize: 10 } },
    visualMap: { min: 0, max: 50, show: false, inRange: { color: ['#ebeef5', '#409eff', '#f56c6c'] } },
    series: [{ type: 'heatmap', data, label: { show: false } }],
  });
}

// 初始化生命周期图
function initLifecycleChart() {
  const dom = document.getElementById('lifecycle-chart');
  if (!dom) return;

  lifecycleChart = echarts.init(dom);
  const hours = Array.from({ length: 12 }, (_, i) => `${10 + i}:00`);
  
  // 模拟生命周期曲线：上升 -> 峰值 -> 下降
  const rankData = [45, 32, 18, 8, 3, 2, 3, 5, 8, 12, 18, 25];

  lifecycleChart.setOption({
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>排名: #${p[0].value}` },
    grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: hours, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', inverse: true, min: 1, max: 50, name: '排名', axisLabel: { fontSize: 10 } },
    series: [{
      type: 'line',
      data: rankData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#409eff' },
      areaStyle: { color: 'rgba(64, 158, 255, 0.2)' },
      markPoint: {
        data: [{ type: 'min', name: '峰值' }],
        symbol: 'pin',
        symbolSize: 30,
        label: { formatter: '#{c}' },
      },
    }],
  });
}

// 初始化传播路径图
function initSpreadChart() {
  const dom = document.getElementById('spread-path-chart');
  if (!dom) return;

  spreadChart = echarts.init(dom);
  
  const nodes = [
    { name: '原创', value: 100, category: 0 },
    { name: 'KOL转发', value: 80, category: 1 },
    { name: '媒体报道', value: 60, category: 1 },
    { name: '普通用户', value: 40, category: 2 },
    { name: '二次传播', value: 30, category: 2 },
  ];

  const links = [
    { source: '原创', target: 'KOL转发' },
    { source: '原创', target: '媒体报道' },
    { source: 'KOL转发', target: '普通用户' },
    { source: '媒体报道', target: '普通用户' },
    { source: '普通用户', target: '二次传播' },
  ];

  spreadChart.setOption({
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      label: { show: true, fontSize: 10 },
      force: { repulsion: 100, edgeLength: 50 },
      data: nodes.map(n => ({ ...n, symbolSize: n.value / 3 + 10 })),
      links,
      categories: [{ name: '源头' }, { name: '一级传播' }, { name: '二级传播' }],
      lineStyle: { color: '#aaa', curveness: 0.2 },
    }],
  });
}

// 初始化话题趋势图
function initTopicTrendChart() {
  const dom = document.getElementById('topic-heat-trend');
  if (!dom) return;

  topicTrendChart = echarts.init(dom);
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);

  topicTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: '热度' },
    series: [{
      type: 'line',
      data: hours.map(() => Math.floor(Math.random() * 5000000 + 500000)),
      smooth: true,
      areaStyle: { color: 'rgba(64, 158, 255, 0.3)' },
      itemStyle: { color: '#409eff' },
    }],
  });
}

// 事件处理
function handlePlatformChange() {
  refreshData();
}

function handleRefreshIntervalChange() {
  setupAutoRefresh();
}

function setupAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  
  if (refreshMode.value === 'auto') {
    refreshTimer = window.setInterval(() => {
      refreshData();
    }, refreshInterval.value * 1000);
  }
}

async function refreshData() {
  isLoading.value = true;
  
  await new Promise(r => setTimeout(r, 500));
  generateHotSearchData();
  
  // 检查预警
  checkAlerts();
  
  lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  isLoading.value = false;
  
  nextTick(() => {
    initMiniTrendCharts();
  });
}

function checkAlerts() {
  alertKeywords.value.forEach(alert => {
    if (!alert.enabled) return;
    
    const matched = hotSearchList.value.find(item => 
      item.title.includes(alert.keyword) && 
      item.rank <= alert.rankThreshold &&
      (alert.platform === 'all' || alert.platform === platform.value)
    );
    
    if (matched) {
      ElNotification({
        title: '热搜预警',
        message: `"${alert.keyword}" 已进入${platformName.value}热搜第 ${matched.rank} 名！`,
        type: 'warning',
        duration: 5000,
      });
    }
  });
}

function showAlertDialog() {
  alertDialogVisible.value = true;
}

function addAlert() {
  if (!newAlertKeyword.value) {
    ElMessage.warning('请输入关键词');
    return;
  }
  
  alertKeywords.value.push({
    keyword: newAlertKeyword.value,
    rankThreshold: newAlertRank.value,
    platform: newAlertPlatform.value,
    enabled: true,
  });
  
  newAlertKeyword.value = '';
  ElMessage.success('预警已添加');
}

function removeAlert(index: number) {
  alertKeywords.value.splice(index, 1);
}

function showTopicDetail(item: HotSearchItem) {
  selectedTopic.value = item;
  relatedWeibos.value = Array.from({ length: 5 }, (_, i) => ({
    content: `这是关于"${item.title}"的第${i + 1}条热门微博内容，包含了用户的讨论和观点。`,
    author: `用户${i + 1}`,
    likes: Math.floor(Math.random() * 10000),
    time: `${Math.floor(Math.random() * 12)}小时前`,
  }));
  topicDetailVisible.value = true;
  
  nextTick(() => {
    initTopicTrendChart();
  });
}

function addToMonitor(item: HotSearchItem) {
  alertKeywords.value.push({
    keyword: item.title,
    rankThreshold: 50,
    platform: platform.value,
    enabled: true,
  });
  ElMessage.success(`已添加"${item.title}"到监控列表`);
}

function analyzeTopic(item: HotSearchItem) {
  ElMessage.info(`正在分析话题: ${item.title}`);
}

function shareTopic(item: HotSearchItem) {
  navigator.clipboard.writeText(`${platformName.value}热搜 #${item.rank}: ${item.title}`);
  ElMessage.success('已复制到剪贴板');
}

function exportData() {
  ElMessage.success('热搜数据已导出');
}

// 工具函数
function formatHeat(heat: number) {
  if (heat >= 10000000) return (heat / 10000000).toFixed(1) + '千万';
  if (heat >= 10000) return (heat / 10000).toFixed(0) + '万';
  return heat.toLocaleString();
}

function formatNumber(num: number) {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toLocaleString();
}

function formatDuration(minutes: number) {
  if (minutes >= 60) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h}小时${m > 0 ? m + '分' : ''}`;
  }
  return `${minutes}分钟`;
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger' };
  return map[sentiment] || 'info';
}

function getSentimentLabel(sentiment: string) {
  const map: Record<string, string> = { positive: '正面', neutral: '中性', negative: '负面' };
  return map[sentiment] || '未知';
}

function getRowClassName({ row }: { row: HotSearchItem }) {
  if (row.rank <= 3) return 'top-row';
  if (row.changeType === 'new') return 'new-row';
  return '';
}

function getStageType(stage: string) {
  const map: Record<string, string> = { rise: 'success', peak: 'danger', fall: 'warning', stable: 'info' };
  return map[stage] || 'info';
}

// 监听刷新模式变化
watch(refreshMode, () => {
  setupAutoRefresh();
});

// 生命周期
onMounted(() => {
  generateHotSearchData();
  nextTick(() => {
    initMiniTrendCharts();
    initTimeHeatmap();
    initLifecycleChart();
    initSpreadChart();
  });
  setupAutoRefresh();
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  timeHeatmap?.dispose();
  lifecycleChart?.dispose();
  spreadChart?.dispose();
  topicTrendChart?.dispose();
  miniTrendCharts.forEach(c => c.dispose());
});
</script>

<style scoped>
.hot-search-monitor {
  padding: 15px;
}

/* 控制栏 */
.monitor-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.control-left, .control-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-label {
  font-size: 13px;
  color: #606266;
}

.platform-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
}

.platform-icon.weibo { background: #e6162d; }
.platform-icon.baidu { background: #2932e1; }
.platform-icon.zhihu { background: #0084ff; }
.platform-icon.douyin { background: #000; }

.last-update {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #909399;
  margin-left: 15px;
}

/* 热搜表格 */
.hotsearch-table-card {
  margin-bottom: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.header-stats {
  display: flex;
  gap: 10px;
}

/* 排名单元格 */
.rank-cell {
  display: flex;
  align-items: center;
  gap: 5px;
}

.rank-num {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  background: #909399;
  color: #fff;
}

.rank-1 { background: #f56c6c; }
.rank-2 { background: #e6a23c; }
.rank-3 { background: #f4e04d; color: #333; }

.rank-change {
  font-size: 11px;
}

.rank-change.new { color: #e6a23c; }
.rank-change.rise { color: #67c23a; }
.rank-change.fall { color: #f56c6c; }
.rank-change.same { color: #909399; }

/* 话题单元格 */
.topic-cell {
  cursor: pointer;
}

.topic-cell:hover .topic-title {
  color: #409eff;
}

.topic-title {
  font-weight: 500;
  transition: color 0.2s;
}

.topic-tags {
  display: flex;
  gap: 5px;
  margin-top: 3px;
}

/* 热度单元格 */
.heat-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.heat-value {
  font-weight: 500;
  min-width: 50px;
}

.mini-trend {
  width: 60px;
  height: 25px;
}

/* 变化率 */
.change-rate {
  font-weight: 500;
}

.change-rate.up { color: #67c23a; }
.change-rate.down { color: #f56c6c; }

/* 表格行样式 */
:deep(.top-row) {
  background: #fef0f0;
}

:deep(.new-row) {
  background: #fdf6ec;
}

/* 分析卡片 */
.analysis-card {
  margin-bottom: 15px;
}

.lifecycle-stats {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
  border-top: 1px solid #ebeef5;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  display: block;
}

.stat-value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.stat-value.highlight {
  color: #f56c6c;
  font-size: 18px;
}

/* 预警设置 */
.add-alert {
  display: flex;
  gap: 10px;
  align-items: center;
}

.notify-settings {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.notify-settings h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

/* 话题详情 */
.topic-detail-dialog .detail-section {
  margin-top: 20px;
}

.topic-detail-dialog h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.related-weibos {
  max-height: 200px;
  overflow-y: auto;
}

.weibo-item {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
}

.weibo-content {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
  margin-bottom: 8px;
}

.weibo-meta {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #909399;
}
</style>
