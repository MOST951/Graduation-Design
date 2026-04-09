<template>
  <div class="enhanced-dashboard">
    <!-- 顶部状态栏 -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="title">微博舆情分析系统</h1>
        <span class="subtitle">Weibo Sentiment Analysis Platform</span>
      </div>
      <div class="header-right">
        <div class="status-indicator" :class="{ online: serviceStatus.online }">
          <span class="dot"></span>
          <span>{{ serviceStatus.online ? '服务正常' : '服务离线' }}</span>
        </div>
        <span class="update-time">更新于 {{ lastUpdateTime }}</span>
        <button class="refresh-btn" @click="refreshData" :disabled="loading">
          <span class="icon" :class="{ spinning: loading }">↻</span>
          刷新
        </button>
      </div>
    </header>

    <!-- 快速操作面板 -->
    <section class="quick-actions">
      <div class="action-card" @click="startNewAnalysis">
        <div class="action-icon">🔍</div>
        <div class="action-text">
          <h3>新建分析</h3>
          <p>启动微博数据采集与分析任务</p>
        </div>
      </div>
      <div class="action-card" @click="goToRealtime">
        <div class="action-icon">📡</div>
        <div class="action-text">
          <h3>实时监控</h3>
          <p>查看实时舆情动态与预警</p>
        </div>
      </div>
      <div class="action-card" @click="goToReports">
        <div class="action-icon">📊</div>
        <div class="action-text">
          <h3>分析报告</h3>
          <p>查看历史分析报告与统计</p>
        </div>
      </div>
      <div class="action-card" @click="goToSettings">
        <div class="action-icon">⚙️</div>
        <div class="action-text">
          <h3>系统设置</h3>
          <p>配置分析参数与模型权重</p>
        </div>
      </div>
    </section>

    <!-- 统计卡片 -->
    <section class="stats-section">
      <div class="stat-card primary">
        <div class="stat-value">{{ formatNumber(stats.totalWeibos) }}</div>
        <div class="stat-label">总微博数</div>
        <div class="stat-trend up">↑ {{ stats.weiboGrowth }}%</div>
      </div>
      <div class="stat-card success">
        <div class="stat-value">{{ stats.positiveRate }}%</div>
        <div class="stat-label">正面情感占比</div>
        <div class="stat-progress">
          <div class="progress-bar positive" :style="{ width: stats.positiveRate + '%' }"></div>
        </div>
      </div>
      <div class="stat-card danger">
        <div class="stat-value">{{ stats.negativeRate }}%</div>
        <div class="stat-label">负面情感占比</div>
        <div class="stat-progress">
          <div class="progress-bar negative" :style="{ width: stats.negativeRate + '%' }"></div>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-value">{{ stats.alertCount }}</div>
        <div class="stat-label">待处理预警</div>
        <div class="stat-trend" :class="{ up: stats.alertGrowth > 0 }">
          {{ stats.alertGrowth > 0 ? '↑' : '↓' }} {{ Math.abs(stats.alertGrowth) }}%
        </div>
      </div>
    </section>

    <!-- 图表区域 -->
    <section class="charts-section">
      <!-- 情感分布 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>情感分布</h3>
          <div class="chart-actions">
            <button 
              v-for="period in timePeriods" 
              :key="period.value"
              class="period-btn"
              :class="{ active: selectedPeriod === period.value }"
              @click="selectedPeriod = period.value"
            >
              {{ period.label }}
            </button>
          </div>
        </div>
        <OptimizedCharts
          type="sentiment-pie"
          :data="sentimentData"
          height="300px"
          :theme="theme"
        />
      </div>

      <!-- 热度趋势 -->
      <div class="chart-card wide">
        <div class="chart-header">
          <h3>热度趋势</h3>
        </div>
        <OptimizedCharts
          type="heat-trend"
          :data="trendData"
          height="300px"
          :theme="theme"
        />
      </div>

      <!-- 四象限分布 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>四象限分布</h3>
          <span class="chart-tip">情感-热度双维度分析</span>
        </div>
        <OptimizedCharts
          type="quadrant"
          :data="quadrantData"
          height="300px"
          :theme="theme"
        />
      </div>

      <!-- 双维度散点图 -->
      <div class="chart-card wide">
        <div class="chart-header">
          <h3>情感-热度分布</h3>
        </div>
        <OptimizedCharts
          type="dual-scatter"
          :data="topWeibos"
          height="350px"
          :theme="theme"
          @click="handleWeiboClick"
        />
      </div>
    </section>

    <!-- 热门话题与Top微博 -->
    <section class="lists-section">
      <!-- 热门话题 -->
      <div class="list-card">
        <div class="list-header">
          <h3>🔥 热门话题</h3>
          <a href="#" class="more-link">查看更多</a>
        </div>
        <div class="topic-list">
          <div 
            v-for="(topic, index) in hotTopics" 
            :key="topic.id"
            class="topic-item"
            :class="{ hot: index < 3 }"
          >
            <span class="topic-rank">{{ index + 1 }}</span>
            <span class="topic-name">{{ topic.title }}</span>
            <span class="topic-heat">{{ formatNumber(topic.heat) }}</span>
            <span 
              class="topic-sentiment"
              :class="topic.sentiment"
            >
              {{ getSentimentLabel(topic.sentiment) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Top微博 -->
      <div class="list-card wide">
        <div class="list-header">
          <h3>📊 高分微博排行</h3>
          <div class="sort-options">
            <button 
              v-for="sort in sortOptions"
              :key="sort.value"
              class="sort-btn"
              :class="{ active: currentSort === sort.value }"
              @click="currentSort = sort.value"
            >
              {{ sort.label }}
            </button>
          </div>
        </div>
        <div class="weibo-list">
          <div 
            v-for="weibo in sortedWeibos" 
            :key="weibo.id"
            class="weibo-item"
          >
            <div class="weibo-rank">
              <span class="rank-number">{{ weibo.rank }}</span>
              <span class="rank-score">{{ weibo.dual_score?.toFixed(2) }}</span>
            </div>
            <div class="weibo-content">
              <p class="weibo-text">{{ weibo.text }}</p>
              <div class="weibo-meta">
                <span class="meta-item">
                  <span class="icon">🔄</span> {{ formatNumber(weibo.reposts_count) }}
                </span>
                <span class="meta-item">
                  <span class="icon">💬</span> {{ formatNumber(weibo.comments_count) }}
                </span>
                <span class="meta-item">
                  <span class="icon">❤️</span> {{ formatNumber(weibo.attitudes_count) }}
                </span>
              </div>
            </div>
            <div class="weibo-sentiment" :class="weibo.sentiment">
              {{ getSentimentLabel(weibo.sentiment) }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 新建分析弹窗 -->
    <div v-if="showAnalysisModal" class="modal-overlay" @click.self="showAnalysisModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>新建分析任务</h2>
          <button class="close-btn" @click="showAnalysisModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>搜索关键词</label>
            <div class="keyword-input">
              <input 
                v-model="analysisForm.keyword"
                placeholder="输入关键词后按回车添加"
                @keyup.enter="addKeyword"
              />
            </div>
            <div class="keyword-tags">
              <span 
                v-for="(kw, index) in analysisForm.keywords"
                :key="index"
                class="keyword-tag"
              >
                {{ kw }}
                <button @click="removeKeyword(index)">×</button>
              </span>
            </div>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="analysisForm.crawlHot" />
              采集热搜话题
            </label>
          </div>
          <div class="form-group">
            <label>采集页数</label>
            <input type="number" v-model="analysisForm.pages" min="1" max="10" />
          </div>
          <div class="form-group">
            <label>权重配置</label>
            <div class="weight-sliders">
              <div class="slider-item">
                <span>情感 {{ (analysisForm.sentimentWeight * 100).toFixed(0) }}%</span>
                <input type="range" v-model.number="analysisForm.sentimentWeight" min="0" max="1" step="0.05" />
              </div>
              <div class="slider-item">
                <span>热度 {{ (analysisForm.heatWeight * 100).toFixed(0) }}%</span>
                <input type="range" v-model.number="analysisForm.heatWeight" min="0" max="1" step="0.05" />
              </div>
              <div class="slider-item">
                <span>时效 {{ (analysisForm.timelinessWeight * 100).toFixed(0) }}%</span>
                <input type="range" v-model.number="analysisForm.timelinessWeight" min="0" max="1" step="0.05" />
              </div>
              <div class="slider-item">
                <span>影响力 {{ (analysisForm.influenceWeight * 100).toFixed(0) }}%</span>
                <input type="range" v-model.number="analysisForm.influenceWeight" min="0" max="1" step="0.05" />
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showAnalysisModal = false">取消</button>
          <button class="btn-primary" @click="submitAnalysis" :disabled="submitting">
            {{ submitting ? '提交中...' : '开始分析' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import OptimizedCharts from '@/components/OptimizedCharts.vue';

const router = useRouter();

// 主题
const theme = ref<'light' | 'dark'>('light');

// 加载状态
const loading = ref(false);
const submitting = ref(false);

// 服务状态
const serviceStatus = reactive({
  online: true,
  crawlerAvailable: true,
  analyzerAvailable: true,
  rankingAvailable: true,
});

// 最后更新时间
const lastUpdateTime = ref(new Date().toLocaleTimeString());

// 时间周期选项
const timePeriods = [
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
];
const selectedPeriod = ref('today');

// 排序选项
const sortOptions = [
  { label: '综合得分', value: 'dual_score' },
  { label: '情感强度', value: 'sentiment' },
  { label: '热度', value: 'heat' },
];
const currentSort = ref('dual_score');

// 统计数据
const stats = reactive({
  totalWeibos: 45218,
  weiboGrowth: 12.5,
  positiveRate: 45.0,
  negativeRate: 24.0,
  alertCount: 8,
  alertGrowth: -15,
});

// 情感分布数据
const sentimentData = reactive({
  positive: 20348,
  neutral: 14020,
  negative: 10850,
});

// 趋势数据
const trendData = reactive({
  dates: ['12-07', '12-08', '12-09', '12-10', '12-11', '12-12', '12-13'],
  values: [2400, 3100, 2800, 3500, 4200, 3900, 4500],
  sentiment: [0.15, 0.22, 0.18, 0.25, 0.30, 0.20, 0.28],
});

// 四象限数据
const quadrantData = reactive({
  high_sentiment_high_heat: 1250,
  high_sentiment_low_heat: 3200,
  low_sentiment_high_heat: 2100,
  low_sentiment_low_heat: 8500,
});

// 热门话题
const hotTopics = ref([
  { id: 1, title: '人工智能', heat: 2500000, sentiment: 'positive' },
  { id: 2, title: '新能源汽车', heat: 1800000, sentiment: 'positive' },
  { id: 3, title: '房价走势', heat: 1500000, sentiment: 'negative' },
  { id: 4, title: '明星八卦', heat: 1200000, sentiment: 'neutral' },
  { id: 5, title: '科技创新', heat: 980000, sentiment: 'positive' },
  { id: 6, title: '就业形势', heat: 850000, sentiment: 'negative' },
  { id: 7, title: '旅游攻略', heat: 720000, sentiment: 'positive' },
  { id: 8, title: '美食推荐', heat: 650000, sentiment: 'positive' },
]);

// Top微博
const topWeibos = ref([
  { 
    id: '1', rank: 1, text: '重大突破！我国在人工智能领域取得重大进展，相关技术达到国际领先水平...',
    sentiment: 'positive', sentiment_score: 0.92, dual_score: 0.89,
    reposts_count: 5000, comments_count: 2000, attitudes_count: 15000,
  },
  { 
    id: '2', rank: 2, text: '紧急提醒：发现某品牌产品存在安全隐患，请消费者注意...',
    sentiment: 'negative', sentiment_score: -0.85, dual_score: 0.86,
    reposts_count: 8000, comments_count: 3500, attitudes_count: 2000,
  },
  { 
    id: '3', rank: 3, text: '今日热点：新能源汽车销量再创新高，环保出行成为新趋势...',
    sentiment: 'positive', sentiment_score: 0.75, dual_score: 0.78,
    reposts_count: 3000, comments_count: 1200, attitudes_count: 8000,
  },
  { 
    id: '4', rank: 4, text: '深度分析：当前经济形势与未来发展趋势，专家解读...',
    sentiment: 'neutral', sentiment_score: 0.1, dual_score: 0.72,
    reposts_count: 2500, comments_count: 800, attitudes_count: 5000,
  },
  { 
    id: '5', rank: 5, text: '生活小技巧：教你如何高效利用时间，提升生活质量...',
    sentiment: 'positive', sentiment_score: 0.6, dual_score: 0.65,
    reposts_count: 1500, comments_count: 600, attitudes_count: 4500,
  },
]);

// 排序后的微博
const sortedWeibos = computed(() => {
  return [...topWeibos.value].sort((a, b) => {
    switch (currentSort.value) {
      case 'sentiment':
        return Math.abs(b.sentiment_score) - Math.abs(a.sentiment_score);
      case 'heat':
        return (b.reposts_count + b.comments_count) - (a.reposts_count + a.comments_count);
      default:
        return b.dual_score - a.dual_score;
    }
  });
});

// 新建分析表单
const showAnalysisModal = ref(false);
const analysisForm = reactive({
  keyword: '',
  keywords: [] as string[],
  crawlHot: true,
  pages: 3,
  sentimentWeight: 0.35,
  heatWeight: 0.35,
  timelinessWeight: 0.15,
  influenceWeight: 0.15,
});

// 刷新数据
async function refreshData() {
  loading.value = true;
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    lastUpdateTime.value = new Date().toLocaleTimeString();
  } finally {
    loading.value = false;
  }
}

// 格式化数字
function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w';
  }
  return num.toLocaleString();
}

// 获取情感标签
function getSentimentLabel(sentiment: string): string {
  const labels: Record<string, string> = {
    positive: '正面',
    neutral: '中性',
    negative: '负面',
  };
  return labels[sentiment] || sentiment;
}

// 导航函数
function startNewAnalysis() {
  showAnalysisModal.value = true;
}

function goToRealtime() {
  router.push('/realtime');
}

function goToReports() {
  router.push('/reports');
}

function goToSettings() {
  router.push('/admin');
}

// 关键词管理
function addKeyword() {
  const kw = analysisForm.keyword.trim();
  if (kw && !analysisForm.keywords.includes(kw)) {
    analysisForm.keywords.push(kw);
    analysisForm.keyword = '';
  }
}

function removeKeyword(index: number) {
  analysisForm.keywords.splice(index, 1);
}

// 提交分析
async function submitAnalysis() {
  submitting.value = true;
  try {
    // 调用API
    const response = await fetch('/api/analysis/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keywords: analysisForm.keywords,
        crawl_hot: analysisForm.crawlHot,
        pages: analysisForm.pages,
        sentiment_weight: analysisForm.sentimentWeight,
        heat_weight: analysisForm.heatWeight,
        timeliness_weight: analysisForm.timelinessWeight,
        influence_weight: analysisForm.influenceWeight,
      }),
    });
    
    if (response.ok) {
      const data = await response.json();
      showAnalysisModal.value = false;
      // 跳转到任务详情或显示提示
      alert(`分析任务已创建: ${data.data.task_id}`);
    }
  } catch (error) {
    console.error('提交失败:', error);
  } finally {
    submitting.value = false;
  }
}

// 微博点击事件
function handleWeiboClick(params: any) {
  console.log('点击微博:', params);
}

// 自动刷新
let refreshInterval: number;

onMounted(() => {
  refreshInterval = window.setInterval(() => {
    lastUpdateTime.value = new Date().toLocaleTimeString();
  }, 60000);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style scoped lang="scss">
.enhanced-dashboard {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #e0e0e0;
  padding: 20px;
  font-family: 'Noto Sans SC', 'PingFang SC', sans-serif;
}

// 顶部状态栏
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  
  .header-left {
    .title {
      font-size: 28px;
      font-weight: 700;
      margin: 0;
      background: linear-gradient(90deg, #00d4ff, #7b2ff7);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    
    .subtitle {
      font-size: 14px;
      color: #888;
      margin-top: 4px;
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;
    
    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #ff4757;
      }
      
      &.online .dot {
        background: #2ed573;
        box-shadow: 0 0 10px #2ed573;
      }
    }
    
    .update-time {
      color: #888;
      font-size: 13px;
    }
    
    .refresh-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: rgba(0, 212, 255, 0.2);
      border: 1px solid rgba(0, 212, 255, 0.3);
      border-radius: 8px;
      color: #00d4ff;
      cursor: pointer;
      transition: all 0.3s;
      
      &:hover {
        background: rgba(0, 212, 255, 0.3);
      }
      
      .icon {
        display: inline-block;
        
        &.spinning {
          animation: spin 1s linear infinite;
        }
      }
    }
  }
}

// 快速操作
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
  
  .action-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s;
    border: 1px solid transparent;
    
    &:hover {
      transform: translateY(-4px);
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(0, 212, 255, 0.3);
    }
    
    .action-icon {
      font-size: 32px;
    }
    
    .action-text {
      h3 {
        font-size: 16px;
        margin: 0 0 4px 0;
      }
      
      p {
        font-size: 12px;
        color: #888;
        margin: 0;
      }
    }
  }
}

// 统计卡片
.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
  
  .stat-card {
    padding: 24px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    border-left: 4px solid;
    
    &.primary { border-color: #00d4ff; }
    &.success { border-color: #2ed573; }
    &.danger { border-color: #ff4757; }
    &.warning { border-color: #ffa502; }
    
    .stat-value {
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    
    .stat-label {
      font-size: 14px;
      color: #888;
      margin-bottom: 12px;
    }
    
    .stat-trend {
      font-size: 12px;
      color: #2ed573;
      
      &.up { color: #2ed573; }
    }
    
    .stat-progress {
      height: 6px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 3px;
      overflow: hidden;
      
      .progress-bar {
        height: 100%;
        border-radius: 3px;
        
        &.positive { background: #2ed573; }
        &.negative { background: #ff4757; }
      }
    }
  }
}

// 图表区域
.charts-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
  
  .chart-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    
    &.wide {
      grid-column: span 2;
    }
    
    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      
      h3 {
        font-size: 16px;
        margin: 0;
      }
      
      .chart-tip {
        font-size: 12px;
        color: #888;
      }
      
      .chart-actions {
        display: flex;
        gap: 8px;
        
        .period-btn {
          padding: 4px 12px;
          background: transparent;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 4px;
          color: #888;
          cursor: pointer;
          font-size: 12px;
          
          &.active {
            background: rgba(0, 212, 255, 0.2);
            border-color: #00d4ff;
            color: #00d4ff;
          }
        }
      }
    }
  }
}

// 列表区域
.lists-section {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
  
  .list-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    
    &.wide {
      grid-column: span 1;
    }
    
    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      
      h3 {
        font-size: 16px;
        margin: 0;
      }
      
      .more-link {
        font-size: 12px;
        color: #00d4ff;
        text-decoration: none;
      }
      
      .sort-options {
        display: flex;
        gap: 8px;
        
        .sort-btn {
          padding: 4px 10px;
          background: transparent;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 4px;
          color: #888;
          cursor: pointer;
          font-size: 12px;
          
          &.active {
            background: rgba(0, 212, 255, 0.2);
            border-color: #00d4ff;
            color: #00d4ff;
          }
        }
      }
    }
  }
  
  // 话题列表
  .topic-list {
    .topic-item {
      display: flex;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      
      &.hot .topic-rank {
        background: linear-gradient(135deg, #ff4757, #ff6b81);
      }
      
      .topic-rank {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        font-size: 12px;
        margin-right: 12px;
      }
      
      .topic-name {
        flex: 1;
        font-size: 14px;
      }
      
      .topic-heat {
        font-size: 12px;
        color: #888;
        margin-right: 12px;
      }
      
      .topic-sentiment {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        
        &.positive { background: rgba(46, 213, 115, 0.2); color: #2ed573; }
        &.neutral { background: rgba(255, 255, 255, 0.1); color: #888; }
        &.negative { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
      }
    }
  }
  
  // 微博列表
  .weibo-list {
    .weibo-item {
      display: flex;
      align-items: flex-start;
      padding: 16px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      
      .weibo-rank {
        text-align: center;
        margin-right: 16px;
        
        .rank-number {
          display: block;
          font-size: 20px;
          font-weight: 700;
          color: #00d4ff;
        }
        
        .rank-score {
          font-size: 11px;
          color: #888;
        }
      }
      
      .weibo-content {
        flex: 1;
        
        .weibo-text {
          font-size: 14px;
          line-height: 1.6;
          margin: 0 0 8px 0;
        }
        
        .weibo-meta {
          display: flex;
          gap: 16px;
          
          .meta-item {
            font-size: 12px;
            color: #888;
            
            .icon {
              margin-right: 4px;
            }
          }
        }
      }
      
      .weibo-sentiment {
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        margin-left: 16px;
        
        &.positive { background: rgba(46, 213, 115, 0.2); color: #2ed573; }
        &.neutral { background: rgba(255, 255, 255, 0.1); color: #888; }
        &.negative { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
      }
    }
  }
}

// 弹窗
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  
  .modal-content {
    background: #1a1a2e;
    border-radius: 16px;
    width: 500px;
    max-width: 90vw;
    border: 1px solid rgba(255, 255, 255, 0.1);
    
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      
      h2 {
        margin: 0;
        font-size: 18px;
      }
      
      .close-btn {
        background: none;
        border: none;
        color: #888;
        font-size: 24px;
        cursor: pointer;
        
        &:hover {
          color: #fff;
        }
      }
    }
    
    .modal-body {
      padding: 20px;
      
      .form-group {
        margin-bottom: 20px;
        
        label {
          display: block;
          margin-bottom: 8px;
          font-size: 14px;
          color: #888;
        }
        
        input[type="text"],
        input[type="number"] {
          width: 100%;
          padding: 10px 14px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          color: #fff;
          font-size: 14px;
          
          &:focus {
            outline: none;
            border-color: #00d4ff;
          }
        }
        
        .keyword-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 10px;
          
          .keyword-tag {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: rgba(0, 212, 255, 0.2);
            border-radius: 4px;
            font-size: 12px;
            
            button {
              background: none;
              border: none;
              color: #888;
              cursor: pointer;
              padding: 0;
              
              &:hover {
                color: #ff4757;
              }
            }
          }
        }
        
        .weight-sliders {
          .slider-item {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            
            span {
              width: 100px;
              font-size: 12px;
            }
            
            input[type="range"] {
              flex: 1;
              -webkit-appearance: none;
              height: 6px;
              background: rgba(255, 255, 255, 0.1);
              border-radius: 3px;
              
              &::-webkit-slider-thumb {
                -webkit-appearance: none;
                width: 16px;
                height: 16px;
                background: #00d4ff;
                border-radius: 50%;
                cursor: pointer;
              }
            }
          }
        }
      }
    }
    
    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 20px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      
      button {
        padding: 10px 24px;
        border-radius: 8px;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.3s;
        
        &.btn-secondary {
          background: transparent;
          border: 1px solid rgba(255, 255, 255, 0.2);
          color: #888;
          
          &:hover {
            border-color: #fff;
            color: #fff;
          }
        }
        
        &.btn-primary {
          background: linear-gradient(135deg, #00d4ff, #7b2ff7);
          border: none;
          color: #fff;
          
          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.4);
          }
          
          &:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
          }
        }
      }
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 响应式
@media (max-width: 1200px) {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-section {
    grid-template-columns: 1fr;
    
    .chart-card.wide {
      grid-column: span 1;
    }
  }
  
  .lists-section {
    grid-template-columns: 1fr;
  }
}
</style>

