<template>
  <div class="spread-analysis">
    <!-- 控制栏 -->
    <div class="analysis-controls">
      <div class="control-left">
        <!-- 话题选择器 -->
        <span class="control-label">选择话题：</span>
        <el-select
          v-model="selectedTopic"
          filterable
          placeholder="搜索或选择话题"
          style="width: 280px;"
          @change="handleTopicChange"
        >
          <el-option
            v-for="topic in topicList"
            :key="topic.id"
            :label="topic.name"
            :value="topic.id"
          >
            <div class="topic-option">
              <span>{{ topic.name }}</span>
              <el-tag size="small" type="info">{{ formatNumber(topic.spreadCount) }}次传播</el-tag>
            </div>
          </el-option>
        </el-select>

        <el-divider direction="vertical" />

        <!-- 时间范围 -->
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          size="default"
          style="width: 360px;"
        />
      </div>

      <div class="control-right">
        <el-button type="primary" :loading="isAnalyzing" @click="runAnalysis">
          <el-icon><DataAnalysis /></el-icon>
          开始分析
        </el-button>
        <el-button @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
      </div>
    </div>

    <!-- 统计概览 -->
    <div class="stats-overview">
      <div class="stat-card">
        <div class="stat-icon" style="background: #409eff;">
          <el-icon><User /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(spreadStats.totalNodes) }}</div>
          <div class="stat-label">参与用户</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #67c23a;">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(spreadStats.totalEdges) }}</div>
          <div class="stat-label">传播关系</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e6a23c;">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ spreadStats.maxDepth }}</div>
          <div class="stat-label">最大深度</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f56c6c;">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ spreadStats.avgSpeed }}</div>
          <div class="stat-label">平均传播速度</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #909399;">
          <el-icon><View /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(spreadStats.totalReach) }}</div>
          <div class="stat-label">覆盖人数</div>
        </div>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- 传播网络图 -->
      <el-col :span="16">
        <el-card shadow="never" class="graph-card">
          <template #header>
            <div class="card-header">
              <span>传播网络图</span>
              <div class="graph-controls">
                <!-- 节点颜色模式 -->
                <el-select v-model="colorMode" size="small" style="width: 120px;">
                  <el-option label="按用户类型" value="type" />
                  <el-option label="按情感倾向" value="sentiment" />
                  <el-option label="按传播层级" value="level" />
                </el-select>
                <!-- 布局模式 -->
                <el-select v-model="layoutMode" size="small" style="width: 100px;" @change="updateLayout">
                  <el-option label="力导向" value="force" />
                  <el-option label="圆形" value="circular" />
                  <el-option label="树形" value="tree" />
                </el-select>
                <!-- 缩放控制 -->
                <el-button-group size="small">
                  <el-button @click="zoomGraph(1.2)"><el-icon><ZoomIn /></el-icon></el-button>
                  <el-button @click="zoomGraph(0.8)"><el-icon><ZoomOut /></el-icon></el-button>
                  <el-button @click="resetGraph"><el-icon><Refresh /></el-icon></el-button>
                </el-button-group>
              </div>
            </div>
          </template>

          <div class="graph-container">
            <div id="spread-network-graph" ref="graphRef" style="width: 100%; height: 500px;"></div>
            
            <!-- 图例 -->
            <div class="graph-legend">
              <div class="legend-title">图例</div>
              <template v-if="colorMode === 'type'">
                <div class="legend-item"><span class="legend-dot" style="background: #f56c6c;"></span>原创</div>
                <div class="legend-item"><span class="legend-dot" style="background: #e6a23c;"></span>KOL</div>
                <div class="legend-item"><span class="legend-dot" style="background: #409eff;"></span>媒体</div>
                <div class="legend-item"><span class="legend-dot" style="background: #67c23a;"></span>普通用户</div>
              </template>
              <template v-else-if="colorMode === 'sentiment'">
                <div class="legend-item"><span class="legend-dot" style="background: #67c23a;"></span>正面</div>
                <div class="legend-item"><span class="legend-dot" style="background: #909399;"></span>中性</div>
                <div class="legend-item"><span class="legend-dot" style="background: #f56c6c;"></span>负面</div>
              </template>
              <template v-else>
                <div class="legend-item"><span class="legend-dot" style="background: #f56c6c;"></span>源头</div>
                <div class="legend-item"><span class="legend-dot" style="background: #e6a23c;"></span>一级</div>
                <div class="legend-item"><span class="legend-dot" style="background: #409eff;"></span>二级</div>
                <div class="legend-item"><span class="legend-dot" style="background: #67c23a;"></span>三级+</div>
              </template>
              <div class="legend-divider"></div>
              <div class="legend-item"><span class="legend-line solid"></span>转发</div>
              <div class="legend-item"><span class="legend-line dashed"></span>评论</div>
              <div class="legend-item"><span class="legend-line dotted"></span>引用</div>
            </div>
          </div>
        </el-card>

        <!-- 传播路径分析 -->
        <el-card shadow="never" class="path-card">
          <template #header>
            <div class="card-header">
              <span>关键传播路径</span>
              <el-radio-group v-model="pathSortBy" size="small">
                <el-radio-button label="influence">按影响力</el-radio-button>
                <el-radio-button label="speed">按速度</el-radio-button>
                <el-radio-button label="depth">按深度</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <div class="path-list">
            <div v-for="(path, index) in topPaths" :key="index" class="path-item">
              <div class="path-header">
                <span class="path-rank">#{{ index + 1 }}</span>
                <div class="path-stats">
                  <el-tag size="small">影响力: {{ path.influence }}</el-tag>
                  <el-tag size="small" type="success">覆盖: {{ formatNumber(path.reach) }}</el-tag>
                  <el-tag size="small" type="warning">深度: {{ path.depth }}</el-tag>
                </div>
              </div>
              <div class="path-nodes">
                <template v-for="(node, ni) in path.nodes" :key="ni">
                  <div :class="['path-node', node.type]" @click="showNodeDetail(node)">
                    <el-avatar :size="32" :src="node.avatar">{{ node.name.charAt(0) }}</el-avatar>
                    <span class="node-name">{{ node.name }}</span>
                  </div>
                  <el-icon v-if="ni < path.nodes.length - 1" class="path-arrow"><Right /></el-icon>
                </template>
              </div>
              <div class="path-timeline">
                <span class="time-start">{{ path.startTime }}</span>
                <div class="time-bar">
                  <div class="time-progress" :style="{ width: path.progress + '%' }"></div>
                </div>
                <span class="time-end">{{ path.endTime }}</span>
                <span class="time-duration">耗时 {{ path.duration }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧分析面板 -->
      <el-col :span="8">
        <!-- 传播深度分析 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <span>传播深度分布</span>
          </template>
          <div id="depth-distribution-chart" style="height: 200px;"></div>
          <div class="depth-stats">
            <div class="depth-item">
              <span class="depth-label">平均深度</span>
              <span class="depth-value">{{ depthStats.avgDepth.toFixed(1) }}</span>
            </div>
            <div class="depth-item">
              <span class="depth-label">最大深度</span>
              <span class="depth-value highlight">{{ depthStats.maxDepth }}</span>
            </div>
            <div class="depth-item">
              <span class="depth-label">深度>3占比</span>
              <span class="depth-value">{{ depthStats.deepRatio }}%</span>
            </div>
          </div>
        </el-card>

        <!-- 传播速度分析 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <span>传播速度趋势</span>
          </template>
          <div id="speed-trend-chart" style="height: 180px;"></div>
          <div class="speed-stats">
            <div class="speed-item">
              <span class="speed-label">峰值速度</span>
              <span class="speed-value">{{ speedStats.peakSpeed }}/分钟</span>
            </div>
            <div class="speed-item">
              <span class="speed-label">峰值时间</span>
              <span class="speed-value">{{ speedStats.peakTime }}</span>
            </div>
          </div>
        </el-card>

        <!-- KOL影响力排行 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <div class="card-header">
              <span>关键节点 (KOL)</span>
              <el-button text size="small" @click="showAllKOL">查看全部</el-button>
            </div>
          </template>
          <div class="kol-list">
            <div v-for="(kol, index) in topKOLs" :key="kol.id" class="kol-item" @click="showNodeDetail(kol)">
              <span class="kol-rank">{{ index + 1 }}</span>
              <el-avatar :size="36" :src="kol.avatar">{{ kol.name.charAt(0) }}</el-avatar>
              <div class="kol-info">
                <div class="kol-name">
                  {{ kol.name }}
                  <el-tag v-if="kol.verified" type="warning" size="small">V</el-tag>
                </div>
                <div class="kol-stats">
                  <span>{{ formatNumber(kol.followers) }} 粉丝</span>
                  <span>{{ formatNumber(kol.spreadCount) }} 次传播</span>
                </div>
              </div>
              <div class="kol-influence">
                <el-progress
                  type="circle"
                  :percentage="kol.influenceScore"
                  :width="40"
                  :stroke-width="4"
                  :color="getInfluenceColor(kol.influenceScore)"
                />
              </div>
            </div>
          </div>
        </el-card>

        <!-- 传播效果评估 -->
        <el-card shadow="never" class="analysis-card">
          <template #header>
            <span>传播效果评估</span>
          </template>
          <div id="effect-radar-chart" style="height: 200px;"></div>
          <div class="effect-summary">
            <div class="effect-score">
              <span class="score-value">{{ effectScore }}</span>
              <span class="score-label">综合评分</span>
            </div>
            <div class="effect-level">
              <el-tag :type="getEffectLevelType(effectScore)" size="large">{{ getEffectLevel(effectScore) }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 节点详情弹窗 -->
    <el-dialog v-model="nodeDetailVisible" :title="selectedNode?.name" width="500px">
      <div v-if="selectedNode" class="node-detail">
        <div class="node-header">
          <el-avatar :size="64" :src="selectedNode.avatar">{{ selectedNode.name.charAt(0) }}</el-avatar>
          <div class="node-basic">
            <div class="node-name">
              {{ selectedNode.name }}
              <el-tag v-if="selectedNode.verified" type="warning" size="small">认证</el-tag>
              <el-tag :type="getNodeTypeTag(selectedNode.type)" size="small">{{ selectedNode.typeLabel }}</el-tag>
            </div>
            <div class="node-bio">{{ selectedNode.bio || '暂无简介' }}</div>
          </div>
        </div>

        <el-descriptions :column="2" border style="margin-top: 15px;">
          <el-descriptions-item label="粉丝数">{{ formatNumber(selectedNode.followers) }}</el-descriptions-item>
          <el-descriptions-item label="关注数">{{ formatNumber(selectedNode.following) }}</el-descriptions-item>
          <el-descriptions-item label="传播次数">{{ selectedNode.spreadCount }}</el-descriptions-item>
          <el-descriptions-item label="传播深度">{{ selectedNode.spreadDepth }}</el-descriptions-item>
          <el-descriptions-item label="影响力得分">
            <el-progress :percentage="selectedNode.influenceScore" :stroke-width="10" />
          </el-descriptions-item>
          <el-descriptions-item label="情感倾向">
            <el-tag :type="getSentimentType(selectedNode.sentiment)">{{ selectedNode.sentimentLabel }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedNode.content" class="node-content">
          <h4>发布内容</h4>
          <div class="content-text">{{ selectedNode.content }}</div>
          <div class="content-stats">
            <span><el-icon><ChatDotRound /></el-icon> {{ selectedNode.comments }}</span>
            <span><el-icon><Share /></el-icon> {{ selectedNode.reposts }}</span>
            <span><el-icon><Star /></el-icon> {{ selectedNode.likes }}</span>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- KOL列表弹窗 -->
    <el-dialog v-model="kolListVisible" title="关键节点列表" width="800px">
      <el-table :data="allKOLs" max-height="500">
        <el-table-column label="排名" width="60" type="index" />
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="kol-cell">
              <el-avatar :size="32" :src="row.avatar">{{ row.name.charAt(0) }}</el-avatar>
              <span>{{ row.name }}</span>
              <el-tag v-if="row.verified" type="warning" size="small">V</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="followers" label="粉丝数" width="120">
          <template #default="{ row }">{{ formatNumber(row.followers) }}</template>
        </el-table-column>
        <el-table-column prop="spreadCount" label="传播次数" width="100" />
        <el-table-column prop="influenceScore" label="影响力" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.influenceScore" :stroke-width="8" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showNodeDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  DataAnalysis, Download, User, Connection, TrendCharts, Timer, View,
  ZoomIn, ZoomOut, Refresh, Right, ChatDotRound, Share, Star
} from '@element-plus/icons-vue';

// 话题选择
const selectedTopic = ref<number | null>(null);
const topicList = ref([
  { id: 1, name: '年度热词揭晓', spreadCount: 125000 },
  { id: 2, name: '科技峰会召开', spreadCount: 89000 },
  { id: 3, name: '明星官宣恋情', spreadCount: 256000 },
  { id: 4, name: '新品发布会', spreadCount: 67000 },
  { id: 5, name: '体育赛事决赛', spreadCount: 178000 },
]);

const dateRange = ref<[Date, Date] | null>(null);
const isAnalyzing = ref(false);

// 统计数据
const spreadStats = reactive({
  totalNodes: 12580,
  totalEdges: 45230,
  maxDepth: 8,
  avgSpeed: '1250/分钟',
  totalReach: 5680000,
});

// 图表配置
const colorMode = ref<'type' | 'sentiment' | 'level'>('type');
const layoutMode = ref<'force' | 'circular' | 'tree'>('force');
const graphRef = ref<HTMLElement>();

// 传播路径
const pathSortBy = ref('influence');
const topPaths = ref([
  {
    influence: 95,
    reach: 580000,
    depth: 6,
    startTime: '10:30',
    endTime: '14:20',
    duration: '3小时50分',
    progress: 100,
    nodes: [
      { name: '原创博主', type: 'origin', avatar: '' },
      { name: '科技大V', type: 'kol', avatar: '' },
      { name: '央视新闻', type: 'media', avatar: '' },
      { name: '热门转发', type: 'user', avatar: '' },
    ],
  },
  {
    influence: 88,
    reach: 420000,
    depth: 5,
    startTime: '10:35',
    endTime: '13:50',
    duration: '3小时15分',
    progress: 85,
    nodes: [
      { name: '原创博主', type: 'origin', avatar: '' },
      { name: '娱乐博主', type: 'kol', avatar: '' },
      { name: '粉丝群体', type: 'user', avatar: '' },
    ],
  },
  {
    influence: 76,
    reach: 280000,
    depth: 4,
    startTime: '11:00',
    endTime: '15:30',
    duration: '4小时30分',
    progress: 70,
    nodes: [
      { name: '原创博主', type: 'origin', avatar: '' },
      { name: '地方媒体', type: 'media', avatar: '' },
      { name: '本地用户', type: 'user', avatar: '' },
    ],
  },
]);

// 深度统计
const depthStats = reactive({
  avgDepth: 3.2,
  maxDepth: 8,
  deepRatio: 15,
});

// 速度统计
const speedStats = reactive({
  peakSpeed: 3500,
  peakTime: '11:30',
});

// KOL数据
const topKOLs = ref([
  { id: 1, name: '科技大V', avatar: '', followers: 5800000, spreadCount: 12500, influenceScore: 95, verified: true },
  { id: 2, name: '央视新闻', avatar: '', followers: 12000000, spreadCount: 8900, influenceScore: 92, verified: true },
  { id: 3, name: '娱乐博主', avatar: '', followers: 3200000, spreadCount: 6700, influenceScore: 85, verified: true },
  { id: 4, name: '财经观察', avatar: '', followers: 2100000, spreadCount: 4500, influenceScore: 78, verified: true },
  { id: 5, name: '热点追踪', avatar: '', followers: 1500000, spreadCount: 3200, influenceScore: 72, verified: false },
]);

const allKOLs = ref([...topKOLs.value]);

// 传播效果
const effectScore = ref(85);

// 弹窗
const nodeDetailVisible = ref(false);
const kolListVisible = ref(false);
const selectedNode = ref<any>(null);

// 图表实例
let networkGraph: echarts.ECharts | null = null;
let depthChart: echarts.ECharts | null = null;
let speedChart: echarts.ECharts | null = null;
let radarChart: echarts.ECharts | null = null;

// 生成网络图数据
function generateGraphData() {
  const nodes: any[] = [];
  const links: any[] = [];
  
  // 源头节点
  nodes.push({
    id: '0',
    name: '原创博主',
    symbolSize: 50,
    category: 0,
    type: 'origin',
    sentiment: 'positive',
    level: 0,
    x: 400,
    y: 300,
  });

  // 生成传播节点
  const types = ['kol', 'media', 'user', 'user'];
  const sentiments = ['positive', 'neutral', 'negative'];
  
  for (let level = 1; level <= 4; level++) {
    const count = Math.pow(2, level + 1);
    for (let i = 0; i < count; i++) {
      const id = `${level}-${i}`;
      const type = types[Math.floor(Math.random() * types.length)];
      nodes.push({
        id,
        name: `${type === 'kol' ? 'KOL' : type === 'media' ? '媒体' : '用户'}${level}-${i}`,
        symbolSize: Math.max(15, 40 - level * 8),
        category: type === 'origin' ? 0 : type === 'kol' ? 1 : type === 'media' ? 2 : 3,
        type,
        sentiment: sentiments[Math.floor(Math.random() * sentiments.length)],
        level,
      });

      // 创建连接
      const parentLevel = level - 1;
      const parentCount = parentLevel === 0 ? 1 : Math.pow(2, parentLevel + 1);
      const parentIndex = Math.floor(Math.random() * parentCount);
      const parentId = parentLevel === 0 ? '0' : `${parentLevel}-${parentIndex}`;
      
      links.push({
        source: parentId,
        target: id,
        lineStyle: {
          type: ['solid', 'dashed', 'dotted'][Math.floor(Math.random() * 3)],
        },
      });
    }
  }

  return { nodes, links };
}

// 初始化网络图
function initNetworkGraph() {
  const dom = document.getElementById('spread-network-graph');
  if (!dom) return;

  networkGraph = echarts.init(dom);
  const { nodes, links } = generateGraphData();

  const categories = [
    { name: '原创', itemStyle: { color: '#f56c6c' } },
    { name: 'KOL', itemStyle: { color: '#e6a23c' } },
    { name: '媒体', itemStyle: { color: '#409eff' } },
    { name: '普通用户', itemStyle: { color: '#67c23a' } },
  ];

  networkGraph.setOption({
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `${params.data.name}<br/>类型: ${categories[params.data.category]?.name || '未知'}`;
        }
        return '';
      },
    },
    legend: { show: false },
    series: [{
      type: 'graph',
      layout: layoutMode.value,
      roam: true,
      draggable: true,
      zoom: 1,
      categories,
      data: nodes.map(n => ({
        ...n,
        itemStyle: getNodeColor(n),
        label: { show: n.symbolSize > 25, fontSize: 10 },
      })),
      links,
      force: {
        repulsion: 150,
        edgeLength: [50, 100],
        gravity: 0.1,
      },
      circular: {
        rotateLabel: true,
      },
      lineStyle: {
        color: '#aaa',
        curveness: 0.2,
        opacity: 0.6,
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3 },
      },
    }],
  });

  networkGraph.on('click', (params: any) => {
    if (params.dataType === 'node') {
      showNodeDetail({
        name: params.data.name,
        type: params.data.type,
        typeLabel: categories[params.data.category]?.name || '未知',
        sentiment: params.data.sentiment,
        sentimentLabel: { positive: '正面', neutral: '中性', negative: '负面' }[params.data.sentiment] || '未知',
        followers: Math.floor(Math.random() * 1000000 + 10000),
        following: Math.floor(Math.random() * 1000 + 100),
        spreadCount: Math.floor(Math.random() * 1000 + 10),
        spreadDepth: params.data.level,
        influenceScore: Math.floor(Math.random() * 40 + 60),
        verified: Math.random() > 0.7,
        bio: '这是用户的简介信息',
        content: '这是用户发布的内容示例...',
        comments: Math.floor(Math.random() * 1000),
        reposts: Math.floor(Math.random() * 5000),
        likes: Math.floor(Math.random() * 10000),
      });
    }
  });
}

function getNodeColor(node: any) {
  if (colorMode.value === 'type') {
    const colors: Record<string, string> = { origin: '#f56c6c', kol: '#e6a23c', media: '#409eff', user: '#67c23a' };
    return { color: colors[node.type] || '#909399' };
  } else if (colorMode.value === 'sentiment') {
    const colors: Record<string, string> = { positive: '#67c23a', neutral: '#909399', negative: '#f56c6c' };
    return { color: colors[node.sentiment] || '#909399' };
  } else {
    const colors = ['#f56c6c', '#e6a23c', '#409eff', '#67c23a', '#909399'];
    return { color: colors[Math.min(node.level, colors.length - 1)] };
  }
}

function updateLayout() {
  if (networkGraph) {
    networkGraph.setOption({
      series: [{ layout: layoutMode.value }],
    });
  }
}

function zoomGraph(scale: number) {
  if (networkGraph) {
    const option = networkGraph.getOption() as any;
    const zoom = (option.series?.[0]?.zoom || 1) * scale;
    networkGraph.setOption({ series: [{ zoom: Math.max(0.3, Math.min(3, zoom)) }] });
  }
}

function resetGraph() {
  initNetworkGraph();
}

// 初始化深度分布图
function initDepthChart() {
  const dom = document.getElementById('depth-distribution-chart');
  if (!dom) return;

  depthChart = echarts.init(dom);
  depthChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: ['1层', '2层', '3层', '4层', '5层', '6层', '7层', '8层'] },
    yAxis: { type: 'value', name: '节点数' },
    series: [{
      type: 'bar',
      data: [2, 8, 32, 128, 256, 180, 80, 20],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#67c23a' },
        ]),
      },
    }],
  });
}

// 初始化速度趋势图
function initSpeedChart() {
  const dom = document.getElementById('speed-trend-chart');
  if (!dom) return;

  speedChart = echarts.init(dom);
  const hours = Array.from({ length: 12 }, (_, i) => `${10 + i}:00`);
  
  speedChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: '传播/分钟' },
    series: [{
      type: 'line',
      data: [500, 1200, 2800, 3500, 2900, 2100, 1500, 1100, 800, 600, 400, 300],
      smooth: true,
      areaStyle: { color: 'rgba(64, 158, 255, 0.3)' },
      itemStyle: { color: '#409eff' },
      markPoint: {
        data: [{ type: 'max', name: '峰值' }],
        symbol: 'pin',
        symbolSize: 40,
      },
    }],
  });
}

// 初始化雷达图
function initRadarChart() {
  const dom = document.getElementById('effect-radar-chart');
  if (!dom) return;

  radarChart = echarts.init(dom);
  radarChart.setOption({
    radar: {
      indicator: [
        { name: '传播广度', max: 100 },
        { name: '传播深度', max: 100 },
        { name: '传播速度', max: 100 },
        { name: '影响力', max: 100 },
        { name: '情感正向', max: 100 },
      ],
      radius: 70,
    },
    series: [{
      type: 'radar',
      data: [{
        value: [88, 75, 92, 85, 70],
        areaStyle: { color: 'rgba(64, 158, 255, 0.3)' },
        lineStyle: { color: '#409eff' },
        itemStyle: { color: '#409eff' },
      }],
    }],
  });
}

// 事件处理
function handleTopicChange() {
  if (selectedTopic.value) {
    runAnalysis();
  }
}

async function runAnalysis() {
  if (!selectedTopic.value) {
    ElMessage.warning('请选择要分析的话题');
    return;
  }

  isAnalyzing.value = true;
  ElMessage.info('正在分析传播数据...');

  await new Promise(r => setTimeout(r, 1500));

  // 更新数据
  spreadStats.totalNodes = Math.floor(Math.random() * 10000 + 5000);
  spreadStats.totalEdges = Math.floor(Math.random() * 50000 + 20000);
  spreadStats.maxDepth = Math.floor(Math.random() * 5 + 5);
  spreadStats.totalReach = Math.floor(Math.random() * 5000000 + 1000000);

  nextTick(() => {
    initNetworkGraph();
    initDepthChart();
    initSpeedChart();
    initRadarChart();
  });

  isAnalyzing.value = false;
  ElMessage.success('分析完成！');
}

function exportReport() {
  ElMessage.success('传播分析报告已导出');
}

function showNodeDetail(node: any) {
  selectedNode.value = node;
  nodeDetailVisible.value = true;
}

function showAllKOL() {
  kolListVisible.value = true;
}

// 工具函数
function formatNumber(num: number) {
  if (num >= 10000000) return (num / 10000000).toFixed(1) + '千万';
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toLocaleString();
}

function getInfluenceColor(score: number) {
  if (score >= 90) return '#f56c6c';
  if (score >= 70) return '#e6a23c';
  return '#67c23a';
}

function getEffectLevel(score: number) {
  if (score >= 90) return '爆发级';
  if (score >= 70) return '优秀';
  if (score >= 50) return '良好';
  return '一般';
}

function getEffectLevelType(score: number) {
  if (score >= 90) return 'danger';
  if (score >= 70) return 'warning';
  if (score >= 50) return 'success';
  return 'info';
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger' };
  return map[sentiment] || 'info';
}

function getNodeTypeTag(type: string) {
  const map: Record<string, string> = { origin: 'danger', kol: 'warning', media: 'primary', user: 'success' };
  return map[type] || 'info';
}

// 监听颜色模式变化
watch(colorMode, () => {
  initNetworkGraph();
});

// 窗口大小变化
function handleResize() {
  networkGraph?.resize();
  depthChart?.resize();
  speedChart?.resize();
  radarChart?.resize();
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initNetworkGraph();
    initDepthChart();
    initSpeedChart();
    initRadarChart();
  });
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  networkGraph?.dispose();
  depthChart?.dispose();
  speedChart?.dispose();
  radarChart?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.spread-analysis {
  padding: 15px;
}

/* 控制栏 */
.analysis-controls {
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

.topic-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

/* 统计概览 */
.stats-overview {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
}

.stat-content .stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.stat-content .stat-label {
  font-size: 12px;
  color: #909399;
}

/* 图表卡片 */
.graph-card, .path-card, .analysis-card {
  margin-bottom: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.graph-controls {
  display: flex;
  gap: 10px;
}

/* 图表容器 */
.graph-container {
  position: relative;
}

/* 图例 */
.graph-legend {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  font-size: 12px;
}

.legend-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #303133;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
  color: #606266;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-line {
  width: 20px;
  height: 2px;
  background: #aaa;
}

.legend-line.dashed {
  background: repeating-linear-gradient(90deg, #aaa 0, #aaa 4px, transparent 4px, transparent 8px);
}

.legend-line.dotted {
  background: repeating-linear-gradient(90deg, #aaa 0, #aaa 2px, transparent 2px, transparent 6px);
}

.legend-divider {
  height: 1px;
  background: #ebeef5;
  margin: 8px 0;
}

/* 传播路径 */
.path-list {
  max-height: 300px;
  overflow-y: auto;
}

.path-item {
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 10px;
}

.path-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.path-rank {
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.path-stats {
  display: flex;
  gap: 8px;
}

.path-nodes {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.path-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.path-node:hover {
  background: #ecf5ff;
}

.path-node.origin { border-bottom: 2px solid #f56c6c; }
.path-node.kol { border-bottom: 2px solid #e6a23c; }
.path-node.media { border-bottom: 2px solid #409eff; }
.path-node.user { border-bottom: 2px solid #67c23a; }

.node-name {
  font-size: 11px;
  color: #606266;
}

.path-arrow {
  color: #909399;
}

.path-timeline {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #909399;
}

.time-bar {
  flex: 1;
  height: 6px;
  background: #ebeef5;
  border-radius: 3px;
  overflow: hidden;
}

.time-progress {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #67c23a);
  border-radius: 3px;
}

.time-duration {
  color: #409eff;
  font-weight: 500;
}

/* 深度统计 */
.depth-stats, .speed-stats {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
  border-top: 1px solid #ebeef5;
}

.depth-item, .speed-item {
  text-align: center;
}

.depth-label, .speed-label {
  font-size: 12px;
  color: #909399;
  display: block;
}

.depth-value, .speed-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.depth-value.highlight {
  color: #f56c6c;
}

/* KOL列表 */
.kol-list {
  max-height: 300px;
  overflow-y: auto;
}

.kol-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.kol-item:hover {
  background: #f5f7fa;
}

.kol-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.kol-info {
  flex: 1;
}

.kol-name {
  font-weight: 500;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 5px;
}

.kol-stats {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 10px;
}

/* 传播效果 */
.effect-summary {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 15px 0;
  border-top: 1px solid #ebeef5;
}

.effect-score {
  text-align: center;
}

.score-value {
  font-size: 36px;
  font-weight: bold;
  color: #409eff;
}

.score-label {
  font-size: 12px;
  color: #909399;
  display: block;
}

/* 节点详情 */
.node-detail .node-header {
  display: flex;
  gap: 15px;
  align-items: center;
}

.node-basic .node-name {
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-basic .node-bio {
  font-size: 13px;
  color: #909399;
  margin-top: 5px;
}

.node-content {
  margin-top: 15px;
}

.node-content h4 {
  margin: 0 0 10px;
  font-size: 14px;
}

.content-text {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.content-stats {
  display: flex;
  gap: 20px;
  margin-top: 10px;
  font-size: 13px;
  color: #909399;
}

.content-stats span {
  display: flex;
  align-items: center;
  gap: 5px;
}

/* KOL表格 */
.kol-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
