<template>
  <div class="hot-topics-module">
    <!-- 顶部标题 -->
    <div class="page-header">
      <h2>热点话题分析</h2>
      <div class="header-badges">
        <el-tag type="success" size="large" effect="dark">
          <el-icon><TrendCharts /></el-icon>
          核心创新：三维度综合排序
        </el-tag>
        <el-tag 
          :type="connectivityTagType" 
          size="small" 
          effect="plain"
          class="connectivity-tag"
          :loading="connectivityChecking"
          @click="checkConnectivity"
        >
          <el-icon v-if="!connectivityChecking"><Connection /></el-icon>
          {{ connectivityText }} ({{ overallConnectivity.toFixed(0) }}%)
        </el-tag>
      </div>
    </div>

    <!-- 上部区域：词云 + 权重调节 -->
    <el-row :gutter="20" class="mb-4">
      <!-- 词云图 -->
      <el-col :span="14">
        <el-card class="wordcloud-card">
          <template #header>
            <div class="card-header">
              <span>话题词云 <el-tag v-if="selectedKeyword" size="small" closable @close="clearKeywordFilter">已选: {{ selectedKeyword }}</el-tag></span>
              <div class="header-actions">
                <el-switch v-model="sentimentColoring" active-text="情感着色" inactive-text="默认" size="small" style="margin-right:8px" @change="renderWordcloud" />
                <el-button :icon="Refresh" size="small" :loading="hotSearchLoading" @click="doRefreshHotSearch">刷新</el-button>
                <el-button :icon="Download" size="small" @click="downloadWordcloud">下载</el-button>
              </div>
            </div>
          </template>
          <div ref="wordcloudRef" style="height: 360px"></div>
          <p class="wordcloud-hint">点击词云中的关键词，右下方列表自动筛选展示相关微博</p>
        </el-card>
      </el-col>

      <!-- 权重调节 + 关键词搜索 -->
      <el-col :span="10">
        <el-card class="control-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Setting /></el-icon> 排序参数调节</span>
              <el-button text size="small" @click="resetWeights">重置</el-button>
            </div>
          </template>

          <!-- 三维度公式说明 -->
          <div class="formula-banner">
            <div class="formula-text">
              S = <span class="w-sentiment">α</span> × 情感强度 + <span class="w-heat">β</span> × 互动热度 + <span class="w-time">γ</span> × 时效性
            </div>
          </div>

          <!-- 情感强度权重 -->
          <div class="weight-row">
            <span class="weight-label">α 情感强度</span>
            <el-slider
              v-model="weights.sentiment"
              :min="0" :max="1" :step="0.05"
              :format-tooltip="(v:number) => (v*100).toFixed(0)+'%'"
              class="weight-slider"
              @input="() => onWeightChange('sentiment')"
            />
            <span class="weight-val">{{ (weights.sentiment*100).toFixed(0) }}%</span>
          </div>

          <!-- 互动热度权重 -->
          <div class="weight-row">
            <span class="weight-label">β 互动热度</span>
            <el-slider
              v-model="weights.heat"
              :min="0" :max="1" :step="0.05"
              :format-tooltip="(v:number) => (v*100).toFixed(0)+'%'"
              class="weight-slider"
              @input="() => onWeightChange('heat')"
            />
            <span class="weight-val">{{ (weights.heat*100).toFixed(0) }}%</span>
          </div>

          <!-- 时效性权重（默认随 α+β 自动补齐，也可手动拖动） -->
          <div class="weight-row">
            <span class="weight-label">γ 时效性</span>
            <el-slider
              v-model="weights.timeliness"
              :min="0" :max="1" :step="0.05"
              :format-tooltip="(v:number) => (v*100).toFixed(0)+'%'"
              class="weight-slider"
              @input="() => onWeightChange('timeliness')"
            />
            <span class="weight-val">{{ (weights.timeliness*100).toFixed(0) }}%</span>
          </div>

          <div class="weight-sum" :class="{ warn: Math.abs(weightSum - 1) > 0.06 }">
            α + β + γ = {{ weightSum.toFixed(2) }}
            <el-tag v-if="Math.abs(weightSum-1)<=0.06" type="success" size="small">正常</el-tag>
            <el-tag v-else type="warning" size="small">建议为1</el-tag>
          </div>

          <el-divider />

          <!-- 关键词搜索 -->
          <div class="search-box">
            <el-input
              v-model="searchKeyword"
              placeholder="输入关键词检索话题"
              clearable
              :prefix-icon="Search"
              @keyup.enter="doSearch"
              @clear="clearKeywordFilter"
            />
            <el-button type="primary" :icon="Search" @click="doSearch">搜索</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下部区域：排序结果列表 -->
    <el-card class="ranking-card">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon><TrendCharts /></el-icon>
            <span>综合排序结果</span>
            <el-tag type="success" size="small" effect="plain">核心创新点</el-tag>
            <el-tag v-if="selectedKeyword" type="primary" size="small">
              筛选: {{ selectedKeyword }}
            </el-tag>
          </div>
          <div class="header-actions">
            <span class="topic-count">共 {{ filteredTopics.length }} 条</span>
            <el-button size="small" type="success" plain @click="exportFilteredResults" :disabled="filteredTopics.length === 0">
              <el-icon><Download /></el-icon> 导出
            </el-button>
            <el-button :icon="Refresh" size="small" :loading="isLoadingRanked" @click="loadRankedTopics">刷新数据</el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="isLoadingRanked"
        :data="filteredTopics"
        stripe
        highlight-current-row
        @row-click="handleRowClick"
        style="width: 100%"
      >
        <el-table-column label="排名" width="70" align="center">
          <template #default="{ $index }">
            <el-tag
              :type="$index < 3 ? 'danger' : $index < 5 ? 'warning' : 'info'"
              size="large"
              class="rank-badge"
            >{{ $index + 1 }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="微博内容" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="topic-cell">
              <span class="topic-name">{{ row.name }}</span>
              <div class="topic-keywords">
                <el-tag v-for="kw in (row.keywords||[]).slice(0,4)" :key="kw" size="small" type="info" @click.stop="onKeywordTagClick(kw)">{{ kw }}</el-tag>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="发布用户" width="110" align="center" prop="user_name">
          <template #default="{ row }">
            <span>{{ row.user_name || row.author || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="发布时间" width="150" align="center">
          <template #default="{ row }">
            <span>{{ formatPublishTime(row.publish_time || row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="情感标签" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment_avg > 0.3 ? 'positive' : row.sentiment_avg < -0.3 ? 'negative' : 'neutral')" size="small">
              {{ row.sentiment_avg > 0.3 ? '正面' : row.sentiment_avg < -0.3 ? '负面' : '中性' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="情感得分" width="100" align="center" sortable prop="sentiment_avg">
          <template #default="{ row }">
            <div class="meta-score">{{ row.sentiment_avg.toFixed(2) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="互动热度" width="110" align="center" sortable prop="popularity_score">
          <template #default="{ row }">
            <span>{{ row.popularity_score.toFixed(4) }}</span>
            <el-icon :color="getTrendColor(row.trend)" style="margin-left:4px">
              <component :is="getTrendIcon(row.trend)" />
            </el-icon>
          </template>
        </el-table-column>

        <el-table-column label="综合得分" width="130" align="center" sortable prop="composite_score">
          <template #default="{ row }">
            <div class="score-cell">
              <span class="score-value">{{ row.composite_score.toFixed(4) }}</span>
              <el-progress :percentage="row.composite_score*100" :show-text="false" :stroke-width="6" :color="getScoreColor(row.composite_score)" />
            </div>
          </template>
        </el-table-column>

        <el-table-column label="四象限分类" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="getQuadrantTag(row).type"
              size="small"
              effect="dark"
              :title="getQuadrantTag(row).tooltip"
            >{{ getQuadrantTag(row).label }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="handleRowClick(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 下方图表区 -->
    <el-row :gutter="20" class="mt-4">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>情感-热度分布</span></template>
          <div ref="scatterChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>Top 5 三维度贡献对比</span></template>
          <div ref="barChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import { storeToRefs } from 'pinia';
import { ElMessage, ElNotification } from 'element-plus';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import { Refresh, Download, Setting, Search, CaretTop, CaretBottom, Minus, TrendCharts, Connection } from '@element-plus/icons-vue';
import { useWeiboStore } from '@/store/weibo';
import { useTopicsStore } from '@/store/topics';
import useConnectivityMonitor from '@/composables/useConnectivityMonitor';
import type { RankedTopic } from '@/api/topics';

// Store
const weiboStore = useWeiboStore();
const topicsStore = useTopicsStore();

// 连通性监控
const {
  status: connectivityStatus,
  checking: connectivityChecking,
  overallConnectivity,
  connectivityTagType,
  connectivityText,
  connectivitySummary,
  checkConnectivity
} = useConnectivityMonitor();

// 从store获取响应式状态
const { hotSearches, lastRefreshTime, isLoading: hotSearchLoading, wordcloudDataFromHotSearch } = storeToRefs(weiboStore);
const { rankedTopics, isLoadingRankedTopics } = storeToRefs(topicsStore);

const isLoadingRanked = computed(() => isLoadingRankedTopics.value);

// ==================== 三维度权重 ====================
const weights = reactive({ sentiment: 0.4, heat: 0.35, timeliness: 0.25 });
const weightSum = computed(() => weights.sentiment + weights.heat + weights.timeliness);

const resetWeights = () => {
  weights.sentiment = 0.4;
  weights.heat = 0.35;
  weights.timeliness = 0.25;
  recomputeScores();
};

// 防止补齐递归触发自身
let _normalizing = false;

const onWeightChange = (changedKey?: 'sentiment' | 'heat' | 'timeliness') => {
  if (_normalizing) return;
  _normalizing = true;
  try {
    // 需求：用户调整情感(α) 或 热度(β) 后，时效(γ) 自动补齐 = 1 - α - β
    // 反之调整 γ 时，按当前 α/β 比例分摊剩余权重，保证 α+β+γ=1
    const round = (v: number) => Math.max(0, Math.min(1, Math.round(v * 20) / 20));
    if (changedKey === 'timeliness') {
      const remain = round(1 - weights.timeliness);
      const sumAB = weights.sentiment + weights.heat;
      if (sumAB > 0) {
        weights.sentiment = round(remain * (weights.sentiment / sumAB));
        weights.heat = round(remain - weights.sentiment);
      } else {
        weights.sentiment = round(remain / 2);
        weights.heat = round(remain - weights.sentiment);
      }
    } else {
      // 默认：调整 α 或 β（或未指定来源时），γ 自动补齐
      const remain = round(1 - weights.sentiment - weights.heat);
      weights.timeliness = remain;
    }
  } finally {
    _normalizing = false;
  }
  recomputeScores();
};

// ==================== 关键词筛选 ====================
const selectedKeyword = ref('');
const searchKeyword = ref('');

const clearKeywordFilter = () => {
  selectedKeyword.value = '';
  searchKeyword.value = '';
};

const doSearch = () => {
  if (searchKeyword.value.trim()) {
    selectedKeyword.value = searchKeyword.value.trim();
  }
};

const onKeywordTagClick = (kw: string) => {
  selectedKeyword.value = kw;
  searchKeyword.value = kw;
};

// ==================== 排序结果 ====================
// 本地重算综合得分（三维度）
const recomputedTopics = ref<RankedTopic[]>([]);

const recomputeScores = () => {
  const topics = rankedTopics.value.map((t, idx) => {
    const timeScore = Math.max(0, 1 - idx * 0.03);
    const composite = weights.sentiment * Math.abs(t.sentiment_avg)
                    + weights.heat * t.popularity_score
                    + weights.timeliness * timeScore;
    return { ...t, composite_score: composite };
  });
  topics.sort((a, b) => b.composite_score - a.composite_score);
  topics.forEach((t, i) => t.rank = i + 1);
  recomputedTopics.value = topics;
  nextTick(updateCharts);
};

const filteredTopics = computed(() => {
  const kw = selectedKeyword.value.toLowerCase();
  if (!kw) return recomputedTopics.value;
  return recomputedTopics.value.filter(t =>
    t.name.toLowerCase().includes(kw)
    || (t.keywords || []).some(k => k.toLowerCase().includes(kw))
  );
});

// ==================== 词云 ====================
const wordcloudRef = ref<HTMLElement>();
let wordcloudChart: echarts.ECharts | null = null;
const wordcloudData: { name: string; value: number }[] = reactive([]);
const sentimentColoring = ref(false);

let autoRefreshTimer: number | null = null;

const loadHotSearch = async () => {
  try {
    await weiboStore.fetchHotSearch();
    if (hotSearches.value.length > 0) {
      updateWordcloudFromHotSearch();
      ElNotification({ title: '热搜已更新', message: `获取到 ${hotSearches.value.length} 条实时热搜`, type: 'success', duration: 2000 });
    }
  } catch (error: any) {
    console.error('加载热搜失败:', error);
  }
};

const updateWordcloudFromHotSearch = () => {
  if (wordcloudDataFromHotSearch.value.length > 0) {
    wordcloudData.length = 0;
    wordcloudDataFromHotSearch.value.forEach(item => wordcloudData.push(item));
    renderWordcloud();
  }
};

const initWordcloud = () => {
  if (!wordcloudRef.value) return;
  wordcloudChart = echarts.init(wordcloudRef.value);
  renderWordcloud();
};

// 根据词名获取情感色
const getWordSentimentColor = (name: string): string => {
  const topic = recomputedTopics.value.find(t =>
    t.name === name || (t.keywords || []).includes(name)
  );
  if (!topic) return '#909399';
  if (topic.sentiment_avg > 0.3) return '#67C23A'; // positive green
  if (topic.sentiment_avg < -0.3) return '#F56C6C'; // negative red
  return '#409EFF'; // neutral blue
};

const renderWordcloud = () => {
  if (!wordcloudChart) return;
  wordcloudChart.setOption({
    tooltip: { show: true, formatter: (p: any) => `${p.name}: ${p.value}` },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center', top: 'center', width: '90%', height: '90%',
      sizeRange: [14, 72],
      rotationRange: [-30, 30],
      rotationStep: 45,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
        fontWeight: 'bold',
        color: (params: any) => {
          if (sentimentColoring.value) {
            return getWordSentimentColor(params.name);
          }
          const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#8B5CF6'];
          return colors[Math.floor(Math.random() * colors.length)];
        },
      },
      emphasis: { focus: 'self', textStyle: { textShadowBlur: 10, textShadowColor: '#333' } },
      data: wordcloudData,
    }],
  });

  wordcloudChart.off('click');
  wordcloudChart.on('click', (params: any) => {
    selectedKeyword.value = params.name;
    searchKeyword.value = params.name;
    ElMessage.success(`已筛选关键词: ${params.name}`);
  });
};

const doRefreshHotSearch = async () => {
  try {
    await weiboStore.forceRefreshHotSearch();
    updateWordcloudFromHotSearch();
    ElMessage.success('热搜已刷新');
  } catch (error: any) {
    ElMessage.warning('刷新失败: ' + (error.message || '请检查后端服务'));
  }
};

const downloadWordcloud = () => {
  if (!wordcloudChart) return;
  const url = wordcloudChart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
  const link = document.createElement('a');
  link.href = url;
  link.download = '词云图.png';
  link.click();
  ElMessage.success('词云图已下载');
};

// ==================== 图表 ====================
const scatterChartRef = ref<HTMLElement>();
const barChartRef = ref<HTMLElement>();
let scatterChart: echarts.ECharts | null = null;
let barChart: echarts.ECharts | null = null;

const initCharts = () => {
  if (scatterChartRef.value) scatterChart = echarts.init(scatterChartRef.value);
  if (barChartRef.value) barChart = echarts.init(barChartRef.value);
};

const updateCharts = () => {
  const data = recomputedTopics.value;
  if (!data.length) return;

  if (scatterChart) {
    scatterChart.setOption({
      tooltip: {
        formatter: (p: any) => `${p.data.name}<br/>情感: ${p.data.value[0].toFixed(2)}<br/>热度: ${p.data.value[1].toFixed(4)}<br/>综合: ${p.data.value[2].toFixed(4)}`
      },
      xAxis: { name: '情感强度', type: 'value', max: 1 },
      yAxis: { name: '互动热度', type: 'value', max: 1 },
      series: [{
        type: 'scatter',
        symbolSize: (d: number[]) => Math.max(10, d[2] * 50),
        data: data.map(t => ({
          name: t.name,
          value: [Math.abs(t.sentiment_avg), t.popularity_score, t.composite_score],
          itemStyle: { color: t.sentiment_avg > 0 ? '#67C23A' : t.sentiment_avg < 0 ? '#F56C6C' : '#909399' }
        }))
      }]
    });
  }

  if (barChart) {
    const top5 = data.slice(0, 5);
    barChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['情感贡献', '热度贡献', '时效贡献'] },
      xAxis: { type: 'category', data: top5.map(t => t.name), axisLabel: { rotate: 15, interval: 0 } },
      yAxis: { type: 'value', max: 1 },
      series: [
        { name: '情感贡献', type: 'bar', stack: 'total', data: top5.map(t => +(Math.abs(t.sentiment_avg) * weights.sentiment).toFixed(4)), itemStyle: { color: '#409EFF' } },
        { name: '热度贡献', type: 'bar', stack: 'total', data: top5.map(t => +(t.popularity_score * weights.heat).toFixed(4)), itemStyle: { color: '#67C23A' } },
        { name: '时效贡献', type: 'bar', stack: 'total', data: top5.map((_, i) => +(Math.max(0, 1 - i * 0.03) * weights.timeliness).toFixed(4)), itemStyle: { color: '#E6A23C' } },
      ]
    });
  }
};

// ==================== 导出筛选结果 ====================
const exportFilteredResults = () => {
  const data = filteredTopics.value;
  if (data.length === 0) {
    ElMessage.warning('暂无数据可导出');
    return;
  }
  const headers = ['排名', '话题名称', '关键词', '综合得分', '情感强度', '互动热度', '微博数', '趋势'];
  const rows = data.map((t, idx) => [
    idx + 1,
    `"${t.name.replace(/"/g, '""')}"`,
    `"${(t.keywords || []).join(', ')}"`,
    t.composite_score.toFixed(4),
    t.sentiment_avg.toFixed(4),
    t.popularity_score.toFixed(4),
    t.post_count,
    t.trend === 'up' ? '↑' : t.trend === 'down' ? '↓' : '→',
  ]);
  const BOM = '\uFEFF';
  const csv = BOM + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `热点话题排序_${selectedKeyword.value || '全部'}_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success(`已导出 ${data.length} 条话题数据`);
};

// ==================== 工具函数 ====================
const formatCount = (c: number) => c >= 10000 ? (c / 10000).toFixed(1) + '万' : String(c);
const getScoreColor = (s: number) => s > 0.7 ? '#67C23A' : s > 0.4 ? '#E6A23C' : '#909399';
const getSentimentType = (s: string) => ({ positive: 'success', neutral: 'info', negative: 'danger' } as any)[s] || 'info';
const getTrendColor = (t: string) => t === 'up' ? '#67C23A' : t === 'down' ? '#F56C6C' : '#909399';
const getTrendIcon = (t: string) => t === 'up' ? CaretTop : t === 'down' ? CaretBottom : Minus;

// 四象限分类：根据情感强度和互动热度划分
const getQuadrantTag = (row: any): { label: string; type: string; tooltip: string } => {
  const sentimentHigh = Math.abs(row.sentiment_avg) > 0.3;
  const heatHigh = row.popularity_score > 0.5;
  if (sentimentHigh && heatHigh) {
    return { label: '高情感高热度', type: 'danger', tooltip: '高情感强度 + 高互动热度：重点关注话题' };
  }
  if (sentimentHigh && !heatHigh) {
    return { label: '高情感低热度', type: 'warning', tooltip: '高情感强度 + 低互动热度：潜力话题' };
  }
  if (!sentimentHigh && heatHigh) {
    return { label: '低情感高热度', type: 'primary', tooltip: '低情感强度 + 高互动热度：热门中性话题' };
  }
  return { label: '低情感低热度', type: 'info', tooltip: '低情感强度 + 低互动热度：冷门话题' };
};

// 格式化发布时间
const formatPublishTime = (time: string | undefined): string => {
  if (!time) return '-';
  try {
    const d = new Date(time);
    if (isNaN(d.getTime())) return time;
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return time;
  }
};

const handleRowClick = (row: RankedTopic) => {
  ElMessage.info(`查看话题: ${row.name}`);
};

// ==================== 加载排序数据 ====================
const loadRankedTopics = async () => {
  try {
    await topicsStore.fetchRankedTopics();
    recomputeScores();
    ElMessage.success(`加载了 ${rankedTopics.value.length} 个话题`);
  } catch (error: any) {
    ElMessage.warning('加载失败: ' + (error.message || '请检查后端服务'));
  }
};

// ==================== 生命周期 ====================
onMounted(async () => {
  initWordcloud();
  initCharts();

  try { await weiboStore.startHotSearch(60); } catch { /* ignore */ }
  await loadHotSearch();
  await loadRankedTopics();

  autoRefreshTimer = window.setInterval(() => loadHotSearch(), 60000);

  window.addEventListener('resize', () => {
    wordcloudChart?.resize();
    scatterChart?.resize();
    barChart?.resize();
  });
});

onUnmounted(() => {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  wordcloudChart?.dispose();
  scatterChart?.dispose();
  barChart?.dispose();
});

watch(rankedTopics, () => recomputeScores(), { deep: true });
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.hot-topics-module {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 { margin: 0; font-size: 22px; color: #303133; }

  .header-badges {
    display: flex; align-items: center; gap: 12px;
    :deep(.el-tag) { font-size: 14px; padding: 8px 16px; .el-icon { margin-right: 6px; } }
    .connectivity-tag { cursor: pointer; font-size: 12px; padding: 4px 10px; &:hover { opacity: 0.8; } }
  }
}

.mb-4 { margin-bottom: 16px; }
.mt-4 { margin-top: 16px; }

.card-header {
  display: flex; justify-content: space-between; align-items: center;
  .header-actions { display: flex; align-items: center; gap: 10px; }
  .header-title {
    display: flex; align-items: center; gap: 8px; font-weight: bold;
    .el-icon { color: var(--color-success); }
  }
  .topic-count { font-size: 13px; color: #909399; }
}

/* 词云卡片 */
.wordcloud-card {
  .wordcloud-hint {
    text-align: center; font-size: 12px; color: #909399; margin: 8px 0 0;
  }
}

/* 控制面板 */
.control-card {
  .formula-banner {
    background: linear-gradient(135deg, #ecf5ff, #f0f9eb);
    border-radius: 8px; padding: 12px 16px; margin-bottom: 18px;
    .formula-text {
      font-family: 'Courier New', monospace; font-size: 15px; font-weight: 600; color: #303133;
      .w-sentiment { color: #409EFF; }
      .w-heat { color: #67C23A; }
      .w-time { color: #E6A23C; }
    }
  }

  .weight-row {
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
    .weight-label { width: 90px; font-size: 13px; color: #606266; white-space: nowrap; }
    .weight-slider { flex: 1; }
    .weight-val { width: 42px; text-align: right; font-weight: bold; color: #409EFF; font-size: 13px; }
  }

  .weight-sum {
    text-align: center; font-size: 13px; color: #606266; margin-bottom: 4px;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    &.warn { color: #E6A23C; }
  }

  .search-box {
    display: flex; gap: 10px;
    :deep(.el-input) { flex: 1; }
  }
}

/* 排序结果卡片 */
.ranking-card {
  .rank-badge { font-size: 16px; font-weight: bold; }

  .topic-cell {
    .topic-name { font-weight: 500; display: block; margin-bottom: 4px; cursor: pointer; &:hover { color: var(--el-color-primary); } }
    .topic-keywords { display: flex; gap: 4px; flex-wrap: wrap; cursor: pointer; }
  }

  .score-cell {
    .score-value { font-weight: bold; display: block; margin-bottom: 4px; }
  }

  .meta-score { font-size: 12px; color: #909399; margin-top: 2px; }
}

/* 响应式 */
@media (max-width: 1200px) {
  .el-row { flex-direction: column; }
}
</style>
