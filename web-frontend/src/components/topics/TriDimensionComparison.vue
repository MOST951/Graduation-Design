<template>
  <div class="tri-dimension-comparison">
    <!-- 顶部控制栏 -->
    <div class="control-bar">
      <div class="time-range">
        <span>时间范围:</span>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          size="small"
          @change="loadData"
        />
      </div>
      <div class="actions">
        <el-button-group>
          <el-button size="small" @click="exportChart">
            <el-icon><Picture /></el-icon> 导出图片
          </el-button>
          <el-button size="small" @click="exportCSV">
            <el-icon><Download /></el-icon> 导出CSV
          </el-button>
          <el-button size="small" @click="generateReport">
            <el-icon><Document /></el-icon> 生成报告
          </el-button>
        </el-button-group>
        <el-button type="primary" size="small" :loading="loading" @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 对比视图 -->
    <el-row :gutter="20" class="comparison-view">
      <!-- 左侧：三维度排序 -->
      <el-col :span="10">
        <el-card class="ranking-card tri" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="title">
                <el-icon><DataAnalysis /></el-icon>
                三维度排序
              </span>
              <el-tag type="success" size="small">情感×热度</el-tag>
            </div>
          </template>
          <div v-loading="loading" class="ranking-list">
            <div 
              v-for="(item, index) in triRanking" 
              :key="'tri-' + index"
              class="ranking-item"
              :class="{ highlight: isSignificantChange(item.topic) }"
              @click="selectTopic(item)"
            >
              <div class="rank-badge" :class="getRankClass(index)">{{ index + 1 }}</div>
              <div class="topic-info">
                <div class="topic-name">{{ item.topic }}</div>
                <div class="topic-meta">
                  <span class="sentiment" :class="getSentimentClass(item.sentiment)">
                    情感: {{ item.sentiment.toFixed(2) }}
                  </span>
                  <span class="heat">热度: {{ item.heat.toFixed(0) }}</span>
                </div>
              </div>
              <div class="score">
                <div class="score-value">{{ item.triScore.toFixed(2) }}</div>
                <div class="score-label">综合分</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 中间：差异统计 -->
      <el-col :span="4">
        <div class="diff-stats">
          <div class="diff-title">差异对比</div>
          <div class="diff-item">
            <div class="diff-value">{{ diffStats.changedCount }}</div>
            <div class="diff-label">排名变化</div>
          </div>
          <div class="diff-item">
            <div class="diff-value">{{ diffStats.avgChange.toFixed(1) }}</div>
            <div class="diff-label">平均变化</div>
          </div>
          <div class="diff-item">
            <div class="diff-value">{{ diffStats.maxChange }}</div>
            <div class="diff-label">最大变化</div>
          </div>
          <div class="diff-item highlight">
            <div class="diff-value">{{ diffStats.newInTop10 }}</div>
            <div class="diff-label">新进Top10</div>
          </div>
          <div class="diff-arrows">
            <div 
              v-for="(change, index) in rankChanges.slice(0, 10)" 
              :key="index"
              class="arrow-item"
              :class="{ up: change > 0, down: change < 0 }"
            >
              <el-icon v-if="change > 0"><Top /></el-icon>
              <el-icon v-else-if="change < 0"><Bottom /></el-icon>
              <span v-else>—</span>
              <span v-if="change !== 0" class="change-num">{{ Math.abs(change) }}</span>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 右侧：传统热度排序 -->
      <el-col :span="10">
        <el-card class="ranking-card traditional" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="title">
                <el-icon><TrendCharts /></el-icon>
                传统热度排序
              </span>
              <el-tag type="info" size="small">仅热度</el-tag>
            </div>
          </template>
          <div v-loading="loading" class="ranking-list">
            <div 
              v-for="(item, index) in traditionalRanking" 
              :key="'trad-' + index"
              class="ranking-item"
              @click="selectTopic(item)"
            >
              <div class="rank-badge" :class="getRankClass(index)">{{ index + 1 }}</div>
              <div class="topic-info">
                <div class="topic-name">{{ item.topic }}</div>
                <div class="topic-meta">
                  <span>转发: {{ item.reposts }}</span>
                  <span>评论: {{ item.comments }}</span>
                  <span>点赞: {{ item.likes }}</span>
                </div>
              </div>
              <div class="score">
                <div class="score-value">{{ item.heat.toFixed(0) }}</div>
                <div class="score-label">热度</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 散点图 -->
    <el-card class="scatter-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><el-icon><PieChart /></el-icon> 情感-热度散点图</span>
          <div class="chart-controls">
            <el-checkbox v-model="showTrajectory">显示轨迹</el-checkbox>
            <el-checkbox v-model="showQuadrantLabels">显示象限</el-checkbox>
          </div>
        </div>
      </template>
      <div ref="scatterChartRef" class="scatter-chart"></div>
      
      <!-- 象限说明 -->
      <div v-if="showQuadrantLabels" class="quadrant-legend">
        <div class="quadrant q1">
          <strong>第一象限</strong>
          <span>高情感+高热度</span>
          <em>重点关注</em>
        </div>
        <div class="quadrant q2">
          <strong>第二象限</strong>
          <span>高情感+低热度</span>
          <em>潜在舆情</em>
        </div>
        <div class="quadrant q3">
          <strong>第三象限</strong>
          <span>低情感+低热度</span>
          <em>普通话题</em>
        </div>
        <div class="quadrant q4">
          <strong>第四象限</strong>
          <span>低情感+高热度</span>
          <em>广泛传播</em>
        </div>
      </div>
    </el-card>

    <!-- 趋势分析 -->
    <el-card v-if="selectedTopic" class="trend-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><el-icon><TrendCharts /></el-icon> 话题趋势: {{ selectedTopic.topic }}</span>
          <el-button text size="small" @click="selectedTopic = null">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </template>
      <div ref="trendChartRef" class="trend-chart"></div>
    </el-card>

    <!-- 快速上升话题 -->
    <el-card class="rising-card" shadow="hover">
      <template #header>
        <span><el-icon><Top /></el-icon> 快速上升话题</span>
      </template>
      <div class="rising-topics">
        <div 
          v-for="(topic, index) in risingTopics" 
          :key="index"
          class="rising-item"
        >
          <div class="rising-rank">
            <el-icon color="#67c23a"><Top /></el-icon>
            <span>+{{ topic.change }}</span>
          </div>
          <div class="rising-info">
            <div class="rising-name">{{ topic.topic }}</div>
            <div class="rising-reason">{{ topic.reason }}</div>
          </div>
          <el-tag :type="topic.sentiment > 0 ? 'success' : topic.sentiment < 0 ? 'danger' : 'info'" size="small">
            {{ topic.sentiment > 0 ? '正面' : topic.sentiment < 0 ? '负面' : '中性' }}
          </el-tag>
        </div>
        <el-empty v-if="risingTopics.length === 0" description="暂无快速上升话题" :image-size="60" />
      </div>
    </el-card>

    <!-- 导出报告对话框 -->
    <el-dialog v-model="showReportDialog" title="对比分析报告" width="600px">
      <div class="report-preview" v-html="reportContent"></div>
      <template #footer>
        <el-button @click="showReportDialog = false">取消</el-button>
        <el-button type="primary" @click="downloadReport">下载报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Picture, Download, Document, Refresh, DataAnalysis, TrendCharts,
  PieChart, Top, Bottom, Close
} from '@element-plus/icons-vue';
import * as echarts from 'echarts';

// 状态
const loading = ref(false);
const timeRange = ref<[Date, Date] | null>(null);
const showTrajectory = ref(false);
const showQuadrantLabels = ref(true);
const selectedTopic = ref<any>(null);
const showReportDialog = ref(false);
const reportContent = ref('');

// 图表引用
const scatterChartRef = ref<HTMLElement>();
const trendChartRef = ref<HTMLElement>();
let scatterChart: echarts.ECharts | null = null;
let trendChart: echarts.ECharts | null = null;

// 数据
const triRanking = ref<any[]>([]);
const traditionalRanking = ref<any[]>([]);
const risingTopics = ref<any[]>([]);

// 计算属性
const rankChanges = computed(() => {
  return triRanking.value.map(triItem => {
    const tradIndex = traditionalRanking.value.findIndex(t => t.topic === triItem.topic);
    return tradIndex >= 0 ? tradIndex - triRanking.value.indexOf(triItem) : 0;
  });
});

const diffStats = computed(() => {
  const changes = rankChanges.value;
  const changedCount = changes.filter(c => c !== 0).length;
  const avgChange = changes.length > 0 
    ? changes.reduce((a, b) => a + Math.abs(b), 0) / changes.length 
    : 0;
  const maxChange = Math.max(...changes.map(Math.abs), 0);
  
  // 计算新进Top10的话题数
  const triTop10 = new Set(triRanking.value.slice(0, 10).map(t => t.topic));
  const tradTop10 = new Set(traditionalRanking.value.slice(0, 10).map(t => t.topic));
  const newInTop10 = [...triTop10].filter(t => !tradTop10.has(t)).length;
  
  return { changedCount, avgChange, maxChange, newInTop10 };
});

// 方法
const loadData = async () => {
  loading.value = true;
  try {
    // 调用后端API
    const response = await fetch('/api/weibo/ranking/comparison', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_time: timeRange.value?.[0]?.toISOString(),
        end_time: timeRange.value?.[1]?.toISOString(),
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      triRanking.value = data.data?.tri || [];
      traditionalRanking.value = data.data?.traditional || [];
      risingTopics.value = data.data?.rising || [];
    } else {
      throw new Error('获取数据失败');
    }
  } catch (error) {
    // 使用模拟数据
    generateMockData();
  } finally {
    loading.value = false;
    await nextTick();
    initScatterChart();
  }
};

const generateMockData = () => {
  const topics = [
    '人工智能发展', '新能源汽车', '房价走势', '教育改革', '医疗保障',
    '环境保护', '科技创新', '就业形势', '消费升级', '数字经济',
    '乡村振兴', '养老问题', '食品安全', '网络安全', '文化传承'
  ];
  
  // 生成三维度排序数据
  triRanking.value = topics.map(topic => {
    const sentiment = Math.random() * 2 - 1;
    const heat = Math.random() * 100;
    const reposts = Math.floor(Math.random() * 10000);
    const comments = Math.floor(Math.random() * 5000);
    const likes = Math.floor(Math.random() * 50000);
    const triScore = 0.6 * Math.abs(sentiment) * 100 + 0.4 * heat;
    
    return { topic, sentiment, heat, reposts, comments, likes, triScore };
  }).sort((a, b) => b.triScore - a.triScore);
  
  // 生成传统排序数据
  traditionalRanking.value = [...triRanking.value].sort((a, b) => b.heat - a.heat);
  
  // 生成快速上升话题
  risingTopics.value = [
    { topic: '人工智能发展', change: 5, sentiment: 0.8, reason: '情感强度高，引发广泛讨论' },
    { topic: '教育改革', change: 3, sentiment: -0.5, reason: '负面情绪上升，需关注' },
    { topic: '环境保护', change: 4, sentiment: 0.6, reason: '正面报道增多' },
  ];
};

const initScatterChart = () => {
  if (!scatterChartRef.value) return;
  
  if (scatterChart) {
    scatterChart.dispose();
  }
  
  scatterChart = echarts.init(scatterChartRef.value);
  
  const scatterData = triRanking.value.map(item => ({
    name: item.topic,
    value: [item.heat, Math.abs(item.sentiment) * 100],
    sentiment: item.sentiment,
    triScore: item.triScore,
    itemStyle: {
      color: item.sentiment > 0 ? '#67c23a' : item.sentiment < 0 ? '#f56c6c' : '#909399'
    }
  }));
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data;
        return `
          <strong>${data.name}</strong><br/>
          热度: ${data.value[0].toFixed(1)}<br/>
          情感强度: ${data.value[1].toFixed(1)}<br/>
          情感倾向: ${data.sentiment > 0 ? '正面' : data.sentiment < 0 ? '负面' : '中性'}<br/>
          综合得分: ${data.triScore.toFixed(2)}
        `;
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      top: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'value',
      name: '热度',
      nameLocation: 'middle',
      nameGap: 30,
      splitLine: {
        lineStyle: { type: 'dashed' }
      },
      axisLine: {
        lineStyle: { color: '#909399' }
      }
    },
    yAxis: {
      type: 'value',
      name: '情感强度',
      nameLocation: 'middle',
      nameGap: 40,
      splitLine: {
        lineStyle: { type: 'dashed' }
      },
      axisLine: {
        lineStyle: { color: '#909399' }
      }
    },
    series: [
      {
        type: 'scatter',
        data: scatterData,
        symbolSize: (data: any) => Math.max(10, data[2] || data.triScore / 2),
        emphasis: {
          focus: 'self',
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        },
        markLine: showQuadrantLabels.value ? {
          silent: true,
          lineStyle: { color: '#dcdfe6', type: 'dashed' },
          data: [
            { xAxis: 50 },
            { yAxis: 50 }
          ]
        } : undefined,
        markArea: showQuadrantLabels.value ? {
          silent: true,
          data: [
            [{ xAxis: 50, yAxis: 50 }, { xAxis: 100, yAxis: 100 }],  // Q1
            [{ xAxis: 0, yAxis: 50 }, { xAxis: 50, yAxis: 100 }],   // Q2
            [{ xAxis: 0, yAxis: 0 }, { xAxis: 50, yAxis: 50 }],     // Q3
            [{ xAxis: 50, yAxis: 0 }, { xAxis: 100, yAxis: 50 }],   // Q4
          ].map((coords, i) => [{
            ...coords[0],
            itemStyle: {
              color: ['rgba(103,194,58,0.1)', 'rgba(230,162,60,0.1)', 'rgba(144,147,153,0.1)', 'rgba(64,158,255,0.1)'][i]
            }
          }, coords[1]])
        } : undefined
      }
    ]
  };
  
  scatterChart.setOption(option);
  
  scatterChart.on('click', (params: any) => {
    if (params.data) {
      const topic = triRanking.value.find(t => t.topic === params.data.name);
      if (topic) {
        selectTopic(topic);
      }
    }
  });
};

const initTrendChart = () => {
  if (!trendChartRef.value || !selectedTopic.value) return;
  
  if (trendChart) {
    trendChart.dispose();
  }
  
  trendChart = echarts.init(trendChartRef.value);
  
  // 生成模拟趋势数据
  const dates = [];
  const sentimentData = [];
  const heatData = [];
  
  for (let i = 6; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }));
    sentimentData.push((Math.random() * 2 - 1) * 50 + 50);
    heatData.push(Math.random() * 50 + 30);
  }
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['情感强度', '热度']
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: dates
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '情感强度',
        type: 'line',
        data: sentimentData,
        smooth: true,
        lineStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64,158,255,0.2)' }
      },
      {
        name: '热度',
        type: 'line',
        data: heatData,
        smooth: true,
        lineStyle: { color: '#67c23a' },
        areaStyle: { color: 'rgba(103,194,58,0.2)' }
      }
    ]
  };
  
  trendChart.setOption(option);
};

const selectTopic = (topic: any) => {
  selectedTopic.value = topic;
  nextTick(() => {
    initTrendChart();
  });
};

const isSignificantChange = (topic: string) => {
  const index = triRanking.value.findIndex(t => t.topic === topic);
  return Math.abs(rankChanges.value[index] || 0) >= 3;
};

const getRankClass = (index: number) => {
  if (index === 0) return 'gold';
  if (index === 1) return 'silver';
  if (index === 2) return 'bronze';
  return '';
};

const getSentimentClass = (sentiment: number) => {
  if (sentiment > 0.3) return 'positive';
  if (sentiment < -0.3) return 'negative';
  return 'neutral';
};

const exportChart = () => {
  if (!scatterChart) return;
  
  const url = scatterChart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff'
  });
  
  const link = document.createElement('a');
  link.download = `tri_dimension_scatter_${Date.now()}.png`;
  link.href = url;
  link.click();
  
  ElMessage.success('图表已导出');
};

const exportCSV = () => {
  const headers = ['排名', '话题', '情感值', '热度', '综合得分', '传统排名'];
  const rows = triRanking.value.map((item, index) => {
    const tradRank = traditionalRanking.value.findIndex(t => t.topic === item.topic) + 1;
    return [index + 1, item.topic, item.sentiment.toFixed(2), item.heat.toFixed(0), item.triScore.toFixed(2), tradRank];
  });
  
  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.download = `ranking_comparison_${Date.now()}.csv`;
  link.href = url;
  link.click();
  
  URL.revokeObjectURL(url);
  ElMessage.success('数据已导出');
};

const generateReport = () => {
  reportContent.value = `
    <h2>三维度排序对比分析报告</h2>
    <p><strong>生成时间:</strong> ${new Date().toLocaleString('zh-CN')}</p>
    
    <h3>1. 概述</h3>
    <p>本报告对比了三维度排序（情感×热度）与传统热度排序的差异。</p>
    
    <h3>2. 差异统计</h3>
    <ul>
      <li>排名变化话题数: ${diffStats.value.changedCount}</li>
      <li>平均变化幅度: ${diffStats.value.avgChange.toFixed(1)}</li>
      <li>最大变化幅度: ${diffStats.value.maxChange}</li>
      <li>新进Top10话题: ${diffStats.value.newInTop10}</li>
    </ul>
    
    <h3>3. Top5话题对比</h3>
    <table border="1" style="border-collapse: collapse; width: 100%;">
      <tr><th>三维度排名</th><th>话题</th><th>综合得分</th><th>传统排名</th></tr>
      ${triRanking.value.slice(0, 5).map((item, i) => {
        const tradRank = traditionalRanking.value.findIndex(t => t.topic === item.topic) + 1;
        return `<tr><td>${i + 1}</td><td>${item.topic}</td><td>${item.triScore.toFixed(2)}</td><td>${tradRank}</td></tr>`;
      }).join('')}
    </table>
    
    <h3>4. 结论</h3>
    <p>三维度排序能够更好地识别具有强烈情感倾向的话题，有助于舆情监控和热点分析。</p>
  `;
  showReportDialog.value = true;
};

const downloadReport = () => {
  const blob = new Blob([reportContent.value], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.download = `comparison_report_${Date.now()}.html`;
  link.href = url;
  link.click();
  
  URL.revokeObjectURL(url);
  showReportDialog.value = false;
  ElMessage.success('报告已下载');
};

// 窗口大小变化处理
const handleResize = () => {
  scatterChart?.resize();
  trendChart?.resize();
};

// 生命周期
onMounted(() => {
  loadData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  scatterChart?.dispose();
  trendChart?.dispose();
});

watch(showQuadrantLabels, () => {
  initScatterChart();
});

watch(selectedTopic, (val) => {
  if (val) {
    nextTick(() => initTrendChart());
  }
});
</script>

<style scoped lang="scss">
.tri-dimension-comparison {
  padding: 20px;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  
  .time-range {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .actions {
    display: flex;
    gap: 10px;
  }
}

.comparison-view {
  margin-bottom: 20px;
}

.ranking-card {
  height: 500px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }
  
  &.tri .card-header .title {
    color: #67c23a;
  }
  
  &.traditional .card-header .title {
    color: #909399;
  }
  
  .ranking-list {
    height: calc(100% - 20px);
    overflow-y: auto;
  }
  
  .ranking-item {
    display: flex;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid #ebeef5;
    cursor: pointer;
    transition: background 0.3s;
    
    &:hover {
      background: #f5f7fa;
    }
    
    &.highlight {
      background: #fdf6ec;
    }
    
    .rank-badge {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      background: #909399;
      color: #fff;
      font-size: 12px;
      font-weight: bold;
      margin-right: 12px;
      
      &.gold { background: linear-gradient(135deg, #ffd700, #ffb800); }
      &.silver { background: linear-gradient(135deg, #c0c0c0, #a0a0a0); }
      &.bronze { background: linear-gradient(135deg, #cd7f32, #b87333); }
    }
    
    .topic-info {
      flex: 1;
      
      .topic-name {
        font-weight: 500;
        margin-bottom: 4px;
      }
      
      .topic-meta {
        font-size: 12px;
        color: #909399;
        
        span {
          margin-right: 10px;
        }
        
        .sentiment {
          &.positive { color: #67c23a; }
          &.negative { color: #f56c6c; }
          &.neutral { color: #909399; }
        }
      }
    }
    
    .score {
      text-align: right;
      
      .score-value {
        font-size: 18px;
        font-weight: bold;
        color: #303133;
      }
      
      .score-label {
        font-size: 11px;
        color: #909399;
      }
    }
  }
}

.diff-stats {
  height: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: #fff;
  
  .diff-title {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 20px;
  }
  
  .diff-item {
    text-align: center;
    margin-bottom: 15px;
    
    .diff-value {
      font-size: 24px;
      font-weight: bold;
    }
    
    .diff-label {
      font-size: 11px;
      opacity: 0.8;
    }
    
    &.highlight {
      background: rgba(255, 255, 255, 0.2);
      padding: 10px;
      border-radius: 8px;
    }
  }
  
  .diff-arrows {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-around;
    width: 100%;
    
    .arrow-item {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      font-size: 12px;
      
      &.up { color: #67c23a; }
      &.down { color: #f56c6c; }
      
      .change-num {
        font-weight: bold;
      }
    }
  }
}

.scatter-card {
  margin-bottom: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .chart-controls {
      display: flex;
      gap: 15px;
    }
  }
  
  .scatter-chart {
    height: 400px;
  }
  
  .quadrant-legend {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-top: 15px;
    
    .quadrant {
      padding: 10px;
      border-radius: 8px;
      text-align: center;
      
      strong {
        display: block;
        font-size: 12px;
        margin-bottom: 4px;
      }
      
      span {
        display: block;
        font-size: 11px;
        color: #606266;
      }
      
      em {
        display: block;
        font-size: 10px;
        color: #909399;
        font-style: normal;
        margin-top: 4px;
      }
      
      &.q1 { background: rgba(103, 194, 58, 0.2); }
      &.q2 { background: rgba(230, 162, 60, 0.2); }
      &.q3 { background: rgba(144, 147, 153, 0.2); }
      &.q4 { background: rgba(64, 158, 255, 0.2); }
    }
  }
}

.trend-card {
  margin-bottom: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .trend-chart {
    height: 250px;
  }
}

.rising-card {
  .rising-topics {
    .rising-item {
      display: flex;
      align-items: center;
      padding: 12px;
      border-bottom: 1px solid #ebeef5;
      
      &:last-child {
        border-bottom: none;
      }
      
      .rising-rank {
        display: flex;
        align-items: center;
        gap: 4px;
        color: #67c23a;
        font-weight: bold;
        margin-right: 15px;
        min-width: 50px;
      }
      
      .rising-info {
        flex: 1;
        
        .rising-name {
          font-weight: 500;
          margin-bottom: 4px;
        }
        
        .rising-reason {
          font-size: 12px;
          color: #909399;
        }
      }
    }
  }
}

.report-preview {
  max-height: 400px;
  overflow-y: auto;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  
  h2, h3 {
    color: #303133;
  }
  
  table {
    width: 100%;
    margin: 10px 0;
    
    th, td {
      padding: 8px;
      text-align: left;
    }
    
    th {
      background: #f5f7fa;
    }
  }
}
</style>
