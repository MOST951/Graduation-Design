<template>
  <div class="topic-modeling-panel">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: LDA主题分析 -->
      <el-tab-pane label="LDA主题分析" name="lda">
        <div class="lda-content">
          <!-- 控制栏 -->
          <div class="lda-controls">
            <div class="control-item">
              <span class="control-label">主题数量：</span>
              <el-slider
                v-model="topicCount"
                :min="2"
                :max="20"
                :marks="topicMarks"
                style="width: 200px;"
                @change="handleTopicCountChange"
              />
              <span class="control-value">{{ topicCount }} 个主题</span>
            </div>
            <div class="control-item">
              <el-button type="primary" size="small" :loading="isAnalyzing" @click="runLDAAnalysis">
                <el-icon><Cpu /></el-icon>
                运行分析
              </el-button>
              <el-button size="small" @click="exportTopics">
                <el-icon><Download /></el-icon>
                导出结果
              </el-button>
            </div>
          </div>

          <el-row :gutter="20">
            <!-- 主题列表 -->
            <el-col :span="12">
              <el-card shadow="never" class="topic-list-card">
                <template #header>
                  <span>主题列表</span>
                </template>
                <el-scrollbar height="450px">
                  <div
                    v-for="topic in topics"
                    :key="topic.id"
                    :class="['topic-item', { active: selectedTopic?.id === topic.id }]"
                    @click="selectTopic(topic)"
                  >
                    <div class="topic-header">
                      <div class="topic-name">
                        <el-input
                          v-if="editingTopicId === topic.id"
                          v-model="topic.name"
                          size="small"
                          @blur="editingTopicId = null"
                          @keyup.enter="editingTopicId = null"
                        />
                        <span v-else @dblclick="editingTopicId = topic.id">
                          {{ topic.name }}
                          <el-icon class="edit-icon"><Edit /></el-icon>
                        </span>
                      </div>
                      <el-tag size="small" :type="getTopicType(topic.sentiment)">
                        {{ topic.sentimentLabel }}
                      </el-tag>
                    </div>

                    <div class="topic-keywords">
                      <el-tag
                        v-for="kw in topic.keywords.slice(0, 8)"
                        :key="kw.word"
                        size="small"
                        type="info"
                        effect="plain"
                      >
                        {{ kw.word }}
                      </el-tag>
                      <span v-if="topic.keywords.length > 8" class="more-keywords">
                        +{{ topic.keywords.length - 8 }}
                      </span>
                    </div>

                    <div class="topic-stats">
                      <div class="stat-item">
                        <span class="stat-label">热度</span>
                        <el-progress
                          :percentage="topic.heat"
                          :stroke-width="8"
                          :show-text="false"
                          :color="getHeatColor(topic.heat)"
                        />
                        <span class="stat-value">{{ topic.heat }}%</span>
                      </div>
                      <div :id="`mini-pie-${topic.id}`" class="mini-pie"></div>
                    </div>
                  </div>
                </el-scrollbar>
              </el-card>
            </el-col>

            <!-- 主题分布图 -->
            <el-col :span="12">
              <el-card shadow="never" class="chart-card">
                <template #header>
                  <span>主题分布</span>
                </template>
                <div id="topic-distribution-chart" style="height: 220px;"></div>
              </el-card>

              <el-card shadow="never" class="chart-card">
                <template #header>
                  <div class="card-header">
                    <span>主题热力图</span>
                    <el-radio-group v-model="heatmapTimeRange" size="small">
                      <el-radio-button label="7d">7天</el-radio-button>
                      <el-radio-button label="30d">30天</el-radio-button>
                    </el-radio-group>
                  </div>
                </template>
                <div id="topic-heatmap" style="height: 200px;"></div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 主题演变分析 -->
      <el-tab-pane label="主题演变分析" name="evolution">
        <div class="evolution-content">
          <el-row :gutter="20">
            <!-- 时间轴 -->
            <el-col :span="16">
              <el-card shadow="never">
                <template #header>
                  <div class="card-header">
                    <span>主题演变时间轴</span>
                    <el-select v-model="evolutionTimeRange" size="small" style="width: 120px;">
                      <el-option label="近7天" value="7d" />
                      <el-option label="近30天" value="30d" />
                      <el-option label="近90天" value="90d" />
                    </el-select>
                  </div>
                </template>
                <div id="evolution-timeline" style="height: 300px;"></div>
              </el-card>

              <!-- 主题关系图 -->
              <el-card shadow="never" style="margin-top: 15px;">
                <template #header>
                  <div class="card-header">
                    <span>主题关系网络</span>
                    <el-button-group size="small">
                      <el-button @click="zoomGraph(1.2)">
                        <el-icon><ZoomIn /></el-icon>
                      </el-button>
                      <el-button @click="zoomGraph(0.8)">
                        <el-icon><ZoomOut /></el-icon>
                      </el-button>
                      <el-button @click="resetGraph">
                        <el-icon><Refresh /></el-icon>
                      </el-button>
                    </el-button-group>
                  </div>
                </template>
                <div id="topic-relation-graph" style="height: 350px;"></div>
              </el-card>
            </el-col>

            <!-- 演变模式检测 -->
            <el-col :span="8">
              <el-card shadow="never" class="evolution-patterns">
                <template #header>
                  <span>演变模式检测</span>
                </template>
                <el-scrollbar height="680px">
                  <div v-for="pattern in evolutionPatterns" :key="pattern.id" class="pattern-item">
                    <div class="pattern-header">
                      <el-tag :type="getPatternType(pattern.type)" size="small">
                        {{ pattern.typeLabel }}
                      </el-tag>
                      <span class="pattern-time">{{ pattern.time }}</span>
                    </div>
                    <div class="pattern-content">
                      <div class="pattern-topics">
                        <template v-if="pattern.type === 'merge'">
                          <span class="topic-tag">{{ pattern.from[0] }}</span>
                          <span class="merge-symbol">+</span>
                          <span class="topic-tag">{{ pattern.from[1] }}</span>
                          <span class="arrow">→</span>
                          <span class="topic-tag highlight">{{ pattern.to }}</span>
                        </template>
                        <template v-else-if="pattern.type === 'split'">
                          <span class="topic-tag">{{ pattern.from }}</span>
                          <span class="arrow">→</span>
                          <span class="topic-tag highlight">{{ pattern.to[0] }}</span>
                          <span class="split-symbol">/</span>
                          <span class="topic-tag highlight">{{ pattern.to[1] }}</span>
                        </template>
                        <template v-else-if="pattern.type === 'emerge'">
                          <span class="topic-tag new">{{ pattern.topic }}</span>
                          <span class="emerge-label">新兴主题</span>
                        </template>
                        <template v-else>
                          <span class="topic-tag fade">{{ pattern.topic }}</span>
                          <span class="fade-label">逐渐消退</span>
                        </template>
                      </div>
                      <div class="pattern-desc">{{ pattern.description }}</div>
                    </div>
                  </div>
                </el-scrollbar>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 主题详情 -->
      <el-tab-pane label="主题详情" name="detail">
        <div v-if="selectedTopic" class="detail-content">
          <el-row :gutter="20">
            <!-- 基本信息 -->
            <el-col :span="24">
              <div class="detail-header">
                <h3>{{ selectedTopic.name }}</h3>
                <div class="header-tags">
                  <el-tag :type="getTopicType(selectedTopic.sentiment)">
                    {{ selectedTopic.sentimentLabel }}
                  </el-tag>
                  <el-tag type="info">热度: {{ selectedTopic.heat }}%</el-tag>
                  <el-tag type="warning">文档数: {{ selectedTopic.docCount }}</el-tag>
                </div>
              </div>
            </el-col>

            <!-- 关键词权重 -->
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>关键词权重分布</span>
                </template>
                <div id="keyword-weight-chart" style="height: 300px;"></div>
              </el-card>
            </el-col>

            <!-- 情感趋势 -->
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>主题情感趋势</span>
                </template>
                <div id="topic-sentiment-trend" style="height: 300px;"></div>
              </el-card>
            </el-col>

            <!-- 相关文档 -->
            <el-col :span="16">
              <el-card shadow="never" style="margin-top: 15px;">
                <template #header>
                  <div class="card-header">
                    <span>相关文档</span>
                    <el-select v-model="docSortBy" size="small" style="width: 120px;">
                      <el-option label="按相关性" value="relevance" />
                      <el-option label="按时间" value="time" />
                      <el-option label="按热度" value="heat" />
                    </el-select>
                  </div>
                </template>
                <el-table :data="relatedDocs" max-height="300">
                  <el-table-column prop="content" label="内容" min-width="300">
                    <template #default="{ row }">
                      <el-tooltip :content="row.content" placement="top">
                        <span class="doc-content">{{ truncate(row.content, 60) }}</span>
                      </el-tooltip>
                    </template>
                  </el-table-column>
                  <el-table-column prop="relevance" label="相关度" width="100">
                    <template #default="{ row }">
                      <el-progress :percentage="row.relevance" :stroke-width="6" :show-text="false" />
                      <span class="relevance-text">{{ row.relevance }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="sentiment" label="情感" width="80">
                    <template #default="{ row }">
                      <el-tag :type="getSentimentType(row.sentiment)" size="small">
                        {{ row.sentimentLabel }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="time" label="时间" width="150" />
                </el-table>
              </el-card>
            </el-col>

            <!-- 地理分布 -->
            <el-col :span="8">
              <el-card shadow="never" style="margin-top: 15px;">
                <template #header>
                  <span>地理分布</span>
                </template>
                <div id="topic-geo-chart" style="height: 300px;"></div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <el-empty v-else description="请从主题列表中选择一个主题查看详情" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { Cpu, Download, Edit, ZoomIn, ZoomOut, Refresh } from '@element-plus/icons-vue';

// Tab 状态
const activeTab = ref('lda');

// LDA 分析
const topicCount = ref(8);
const topicMarks = { 2: '2', 5: '5', 10: '10', 15: '15', 20: '20' };
const isAnalyzing = ref(false);
const editingTopicId = ref<number | null>(null);
const heatmapTimeRange = ref('7d');

// 主题数据
interface Topic {
  id: number;
  name: string;
  keywords: { word: string; weight: number }[];
  heat: number;
  sentiment: string;
  sentimentLabel: string;
  sentimentDist: { positive: number; neutral: number; negative: number };
  docCount: number;
}

const topics = ref<Topic[]>([]);
const selectedTopic = ref<Topic | null>(null);

// 演变分析
const evolutionTimeRange = ref('30d');
const evolutionPatterns = ref([
  { id: 1, type: 'merge', typeLabel: '主题合并', time: '12/08', from: ['科技创新', '人工智能'], to: 'AI科技', description: '两个相关主题逐渐融合为一个更大的主题' },
  { id: 2, type: 'split', typeLabel: '主题分裂', time: '12/06', from: '社会热点', to: ['民生话题', '政策解读'], description: '一个大主题分化为两个细分主题' },
  { id: 3, type: 'emerge', typeLabel: '新兴主题', time: '12/05', topic: '年终盘点', description: '新出现的热门话题，热度快速上升' },
  { id: 4, type: 'fade', typeLabel: '主题消退', time: '12/03', topic: '双十一', description: '热度逐渐下降，关注度减少' },
]);

// 主题详情
const docSortBy = ref('relevance');
const relatedDocs = ref<any[]>([]);

// 图表实例
let distributionChart: echarts.ECharts | null = null;
let heatmapChart: echarts.ECharts | null = null;
let timelineChart: echarts.ECharts | null = null;
let relationGraph: echarts.ECharts | null = null;
let keywordChart: echarts.ECharts | null = null;
let sentimentTrendChart: echarts.ECharts | null = null;
let geoChart: echarts.ECharts | null = null;
const miniPieCharts: Map<number, echarts.ECharts> = new Map();

// 生成模拟主题数据
function generateTopics() {
  const topicNames = [
    '科技创新', '娱乐八卦', '社会民生', '财经股市', '体育赛事',
    '教育培训', '健康养生', '美食旅游', '时尚潮流', '游戏电竞',
    '汽车出行', '房产家居', '职场发展', '情感生活', '文化艺术',
    '环保公益', '国际新闻', '军事动态', '法律法规', '农业农村',
  ];

  topics.value = Array.from({ length: topicCount.value }, (_, i) => ({
    id: i + 1,
    name: topicNames[i] || `主题 ${i + 1}`,
    keywords: Array.from({ length: 10 }, (_, j) => ({
      word: `关键词${i + 1}-${j + 1}`,
      weight: Math.random() * 0.5 + 0.1,
    })).sort((a, b) => b.weight - a.weight),
    heat: Math.floor(Math.random() * 60 + 40),
    sentiment: ['positive', 'neutral', 'negative'][Math.floor(Math.random() * 3)],
    sentimentLabel: ['正面', '中性', '负面'][Math.floor(Math.random() * 3)],
    sentimentDist: {
      positive: Math.floor(Math.random() * 40 + 20),
      neutral: Math.floor(Math.random() * 30 + 20),
      negative: Math.floor(Math.random() * 30 + 10),
    },
    docCount: Math.floor(Math.random() * 5000 + 1000),
  }));
}

// 初始化主题分布图
function initDistributionChart() {
  const dom = document.getElementById('topic-distribution-chart');
  if (!dom) return;

  distributionChart = echarts.init(dom);
  updateDistributionChart();
}

function updateDistributionChart() {
  if (!distributionChart) return;

  distributionChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['30%', '70%'],
      data: topics.value.map(t => ({
        name: t.name,
        value: t.docCount,
        itemStyle: { color: getTopicColor(t.id) },
      })),
      label: { formatter: '{b}', fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  });
}

// 初始化热力图
function initHeatmapChart() {
  const dom = document.getElementById('topic-heatmap');
  if (!dom) return;

  heatmapChart = echarts.init(dom);
  updateHeatmapChart();
}

function updateHeatmapChart() {
  if (!heatmapChart) return;

  const days = heatmapTimeRange.value === '7d' ? 7 : 30;
  const dates = Array.from({ length: days }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    return `${d.getMonth() + 1}/${d.getDate()}`;
  });

  const data: [number, number, number][] = [];
  topics.value.slice(0, 8).forEach((_, ti) => {
    dates.forEach((_, di) => {
      data.push([di, ti, Math.floor(Math.random() * 100)]);
    });
  });

  heatmapChart.setOption({
    tooltip: { formatter: (p: any) => `${topics.value[p.data[1]]?.name || ''}<br/>${dates[p.data[0]]}: ${p.data[2]}` },
    grid: { left: '15%', right: '5%', top: '5%', bottom: '15%' },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, interval: Math.floor(days / 7) } },
    yAxis: { type: 'category', data: topics.value.slice(0, 8).map(t => t.name), axisLabel: { fontSize: 10 } },
    visualMap: { min: 0, max: 100, show: false, inRange: { color: ['#f5f5f5', '#409eff', '#f56c6c'] } },
    series: [{ type: 'heatmap', data, label: { show: false } }],
  });
}

// 初始化迷你饼图
function initMiniPieCharts() {
  topics.value.forEach(topic => {
    const dom = document.getElementById(`mini-pie-${topic.id}`);
    if (!dom) return;

    const chart = echarts.init(dom);
    chart.setOption({
      series: [{
        type: 'pie',
        radius: ['50%', '80%'],
        silent: true,
        label: { show: false },
        data: [
          { value: topic.sentimentDist.positive, itemStyle: { color: '#67c23a' } },
          { value: topic.sentimentDist.neutral, itemStyle: { color: '#909399' } },
          { value: topic.sentimentDist.negative, itemStyle: { color: '#f56c6c' } },
        ],
      }],
    });
    miniPieCharts.set(topic.id, chart);
  });
}

// 初始化演变时间轴
function initEvolutionTimeline() {
  const dom = document.getElementById('evolution-timeline');
  if (!dom) return;

  timelineChart = echarts.init(dom);
  const dates = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return `${d.getMonth() + 1}/${d.getDate()}`;
  });

  timelineChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: topics.value.slice(0, 5).map(t => t.name), bottom: 0, type: 'scroll' },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', name: '热度' },
    series: topics.value.slice(0, 5).map(t => ({
      name: t.name,
      type: 'line',
      smooth: true,
      data: dates.map(() => Math.floor(Math.random() * 100)),
      areaStyle: { opacity: 0.1 },
    })),
  });
}

// 初始化关系图
function initRelationGraph() {
  const dom = document.getElementById('topic-relation-graph');
  if (!dom) return;

  relationGraph = echarts.init(dom);
  
  const nodes = topics.value.slice(0, 10).map(t => ({
    id: String(t.id),
    name: t.name,
    symbolSize: 30 + t.heat / 3,
    category: Math.floor(Math.random() * 3),
    itemStyle: { color: getTopicColor(t.id) },
  }));

  const links: { source: string; target: string; value: number }[] = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (Math.random() > 0.6) {
        links.push({
          source: nodes[i].id,
          target: nodes[j].id,
          value: Math.random(),
        });
      }
    }
  }

  relationGraph.setOption({
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      label: { show: true, fontSize: 10 },
      force: { repulsion: 200, edgeLength: [80, 150] },
      data: nodes,
      links,
      lineStyle: { color: '#aaa', curveness: 0.1 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    }],
  });
}

// 初始化关键词权重图
function initKeywordChart() {
  const dom = document.getElementById('keyword-weight-chart');
  if (!dom || !selectedTopic.value) return;

  keywordChart = echarts.init(dom);
  const keywords = selectedTopic.value.keywords.slice(0, 15);

  keywordChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '20%', right: '10%', top: '5%', bottom: '5%' },
    xAxis: { type: 'value', max: 1 },
    yAxis: { type: 'category', data: keywords.map(k => k.word).reverse() },
    series: [{
      type: 'bar',
      data: keywords.map(k => ({
        value: k.weight.toFixed(3),
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#67c23a' },
        ]) },
      })).reverse(),
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  });
}

// 初始化情感趋势图
function initSentimentTrendChart() {
  const dom = document.getElementById('topic-sentiment-trend');
  if (!dom) return;

  sentimentTrendChart = echarts.init(dom);
  const dates = Array.from({ length: 14 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (13 - i));
    return `${d.getMonth() + 1}/${d.getDate()}`;
  });

  sentimentTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '中性', '负面'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '占比%' },
    series: [
      { name: '正面', type: 'line', stack: 'total', areaStyle: {}, data: dates.map(() => Math.floor(Math.random() * 30 + 30)), itemStyle: { color: '#67c23a' } },
      { name: '中性', type: 'line', stack: 'total', areaStyle: {}, data: dates.map(() => Math.floor(Math.random() * 20 + 25)), itemStyle: { color: '#909399' } },
      { name: '负面', type: 'line', stack: 'total', areaStyle: {}, data: dates.map(() => Math.floor(Math.random() * 20 + 15)), itemStyle: { color: '#f56c6c' } },
    ],
  });
}

// 初始化地理分布图
function initGeoChart() {
  const dom = document.getElementById('topic-geo-chart');
  if (!dom) return;

  geoChart = echarts.init(dom);
  const provinces = ['北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '山东'];
  
  geoChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['20%', '70%'],
      roseType: 'radius',
      data: provinces.map(p => ({
        name: p,
        value: Math.floor(Math.random() * 1000 + 200),
      })),
      label: { formatter: '{b}' },
    }],
  });
}

// 事件处理
function handleTopicCountChange() {
  generateTopics();
  nextTick(() => {
    updateDistributionChart();
    updateHeatmapChart();
    initMiniPieCharts();
  });
}

async function runLDAAnalysis() {
  isAnalyzing.value = true;
  ElMessage.info('正在运行LDA主题分析...');
  
  await new Promise(r => setTimeout(r, 1500));
  
  generateTopics();
  nextTick(() => {
    updateDistributionChart();
    updateHeatmapChart();
    initMiniPieCharts();
  });
  
  isAnalyzing.value = false;
  ElMessage.success('分析完成！');
}

function exportTopics() {
  ElMessage.success('主题分析结果已导出');
}

function selectTopic(topic: Topic) {
  selectedTopic.value = topic;
  activeTab.value = 'detail';
  
  // 生成相关文档
  relatedDocs.value = Array.from({ length: 20 }, (_, i) => ({
    id: i + 1,
    content: `这是与主题"${topic.name}"相关的第${i + 1}条文档内容，包含了该主题的关键词和相关讨论。`,
    relevance: Math.floor(Math.random() * 30 + 70),
    sentiment: ['positive', 'neutral', 'negative'][i % 3],
    sentimentLabel: ['正面', '中性', '负面'][i % 3],
    time: `2025-12-${String(10 - Math.floor(i / 5)).padStart(2, '0')} ${String(10 + i % 12).padStart(2, '0')}:00`,
  }));
  
  nextTick(() => {
    initKeywordChart();
    initSentimentTrendChart();
    initGeoChart();
  });
}

function zoomGraph(scale: number) {
  if (relationGraph) {
    const option = relationGraph.getOption() as any;
    const zoom = (option.series?.[0]?.zoom || 1) * scale;
    relationGraph.setOption({ series: [{ zoom: Math.max(0.5, Math.min(3, zoom)) }] });
  }
}

function resetGraph() {
  initRelationGraph();
}

// 工具函数
function truncate(text: string, length: number) {
  return text.length > length ? text.slice(0, length) + '...' : text;
}

function getTopicType(sentiment: string) {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger' };
  return map[sentiment] || 'info';
}

function getSentimentType(sentiment: string) {
  return getTopicType(sentiment);
}

function getTopicColor(id: number) {
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#00d4ff', '#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff'];
  return colors[(id - 1) % colors.length];
}

function getHeatColor(heat: number) {
  if (heat >= 80) return '#f56c6c';
  if (heat >= 60) return '#e6a23c';
  return '#67c23a';
}

function getPatternType(type: string) {
  const map: Record<string, string> = { merge: 'primary', split: 'warning', emerge: 'success', fade: 'info' };
  return map[type] || 'info';
}

// 监听 Tab 切换
watch(activeTab, (tab) => {
  nextTick(() => {
    if (tab === 'lda') {
      distributionChart?.resize();
      heatmapChart?.resize();
    } else if (tab === 'evolution') {
      if (!timelineChart) initEvolutionTimeline();
      if (!relationGraph) initRelationGraph();
      timelineChart?.resize();
      relationGraph?.resize();
    } else if (tab === 'detail' && selectedTopic.value) {
      keywordChart?.resize();
      sentimentTrendChart?.resize();
      geoChart?.resize();
    }
  });
});

// 窗口大小变化
function handleResize() {
  distributionChart?.resize();
  heatmapChart?.resize();
  timelineChart?.resize();
  relationGraph?.resize();
  keywordChart?.resize();
  sentimentTrendChart?.resize();
  geoChart?.resize();
  miniPieCharts.forEach(c => c.resize());
}

// 生命周期
onMounted(() => {
  generateTopics();
  nextTick(() => {
    initDistributionChart();
    initHeatmapChart();
    initMiniPieCharts();
  });
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  distributionChart?.dispose();
  heatmapChart?.dispose();
  timelineChart?.dispose();
  relationGraph?.dispose();
  keywordChart?.dispose();
  sentimentTrendChart?.dispose();
  geoChart?.dispose();
  miniPieCharts.forEach(c => c.dispose());
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.topic-modeling-panel {
  height: 100%;
}

/* LDA 内容 */
.lda-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 15px;
}

.control-label {
  font-size: 13px;
  color: #606266;
}

.control-value {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  min-width: 80px;
}

/* 主题列表 */
.topic-list-card {
  height: 500px;
}

.topic-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.topic-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.topic-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.topic-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.topic-name {
  font-weight: 500;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 5px;
}

.edit-icon {
  font-size: 12px;
  color: #909399;
  opacity: 0;
  transition: opacity 0.2s;
}

.topic-name:hover .edit-icon {
  opacity: 1;
}

.topic-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 10px;
}

.more-keywords {
  font-size: 12px;
  color: #909399;
}

.topic-stats {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
}

.mini-pie {
  width: 40px;
  height: 40px;
}

/* 图表卡片 */
.chart-card {
  margin-bottom: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 演变模式 */
.evolution-patterns {
  height: 720px;
}

.pattern-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 10px;
}

.pattern-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.pattern-time {
  font-size: 12px;
  color: #909399;
}

.pattern-topics {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.topic-tag {
  padding: 4px 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
}

.topic-tag.highlight {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}

.topic-tag.new {
  background: #f0f9eb;
  color: #67c23a;
}

.topic-tag.fade {
  background: #fef0f0;
  color: #f56c6c;
  text-decoration: line-through;
}

.merge-symbol, .split-symbol {
  font-weight: bold;
  color: #909399;
}

.arrow {
  color: #409eff;
}

.emerge-label, .fade-label {
  font-size: 11px;
  color: #909399;
}

.pattern-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

/* 主题详情 */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.detail-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.header-tags {
  display: flex;
  gap: 10px;
}

.doc-content {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.relevance-text {
  font-size: 12px;
  color: #909399;
  margin-left: 5px;
}
</style>
