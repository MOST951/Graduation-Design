<template>
  <div class="advanced-visualization">
    <!-- 顶部控制栏 -->
    <div class="control-bar">
      <div class="control-left">
        <el-button-group>
          <el-button :type="viewMode === 'dashboard' ? 'primary' : ''" @click="viewMode = 'dashboard'">
            <el-icon><Odometer /></el-icon> 监控仪表盘
          </el-button>
          <el-button :type="viewMode === 'scatter' ? 'primary' : ''" @click="viewMode = 'scatter'">
            <el-icon><DataAnalysis /></el-icon> 四象限分析
          </el-button>
          <el-button :type="viewMode === 'trend' ? 'primary' : ''" @click="viewMode = 'trend'">
            <el-icon><TrendCharts /></el-icon> 趋势分析
          </el-button>
        </el-button-group>
      </div>
      
      <div class="control-right">
        <el-switch v-model="autoRefresh" active-text="自动刷新" />
        <el-select v-model="refreshInterval" style="width: 100px; margin-left: 10px" :disabled="!autoRefresh">
          <el-option label="5秒" :value="5000" />
          <el-option label="10秒" :value="10000" />
          <el-option label="30秒" :value="30000" />
        </el-select>
        <el-button type="primary" :icon="Refresh" :loading="loading" style="margin-left: 10px" @click="refreshData">
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 实时监控仪表盘视图 -->
    <div v-show="viewMode === 'dashboard'" class="dashboard-view">
      <el-row :gutter="16">
        <!-- 核心指标卡片 -->
        <el-col v-for="metric in coreMetrics" :key="metric.key" :span="6">
          <el-card shadow="hover" class="metric-card" :class="metric.status">
            <div class="metric-content">
              <div class="metric-icon" :style="{ background: metric.color }">
                <el-icon :size="28"><component :is="metric.icon" /></el-icon>
              </div>
              <div class="metric-info">
                <div class="metric-value">
                  <CountUp :end-val="metric.value" :duration="1" :decimals="metric.decimals || 0" />
                  <span class="metric-unit">{{ metric.unit }}</span>
                </div>
                <div class="metric-label">{{ metric.label }}</div>
                <div class="metric-trend" :class="metric.trend > 0 ? 'up' : 'down'">
                  <el-icon><component :is="metric.trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
                  {{ Math.abs(metric.trend) }}%
                </div>
              </div>
            </div>
            <div ref="sparklineRefs" class="metric-sparkline"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <!-- 实时数据流 -->
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span><el-icon><DataLine /></el-icon> 实时数据流</span>
                <el-tag :type="streamStatus === 'running' ? 'success' : 'info'" size="small">
                  {{ streamStatus === 'running' ? '运行中' : '已暂停' }}
                </el-tag>
              </div>
            </template>
            <div ref="realtimeChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>

        <!-- 情感分布仪表盘 -->
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span><el-icon><PieChart /></el-icon> 情感分布</span>
                <el-radio-group v-model="distributionType" size="small">
                  <el-radio-button label="pie">饼图</el-radio-button>
                  <el-radio-button label="gauge">仪表盘</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div ref="distributionChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <!-- 预警面板 -->
        <el-col :span="8">
          <el-card shadow="hover" class="alert-card">
            <template #header>
              <div class="card-header">
                <span><el-icon><Bell /></el-icon> 预警中心</span>
                <el-badge :value="alerts.length" :max="99" />
              </div>
            </template>
            <div class="alert-list">
              <TransitionGroup name="alert">
                <div v-for="alert in alerts" :key="alert.id" class="alert-item" :class="alert.level">
                  <div class="alert-icon">
                    <el-icon><WarningFilled /></el-icon>
                  </div>
                  <div class="alert-content">
                    <div class="alert-title">{{ alert.title }}</div>
                    <div class="alert-desc">{{ alert.description }}</div>
                    <div class="alert-time">{{ formatTime(alert.time) }}</div>
                  </div>
                  <el-button type="text" size="small" @click="dismissAlert(alert.id)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </TransitionGroup>
              <el-empty v-if="alerts.length === 0" description="暂无预警" :image-size="60" />
            </div>
          </el-card>
        </el-col>

        <!-- 预警阈值设置 -->
        <el-col :span="8">
          <el-card shadow="hover">
            <template #header>
              <span><el-icon><Setting /></el-icon> 预警阈值设置</span>
            </template>
            <el-form label-position="top" size="small">
              <el-form-item label="负面情感阈值">
                <el-slider v-model="thresholds.negativeRatio" :format-tooltip="v => v + '%'" />
                <div class="threshold-hint">当负面情感占比超过 {{ thresholds.negativeRatio }}% 时触发预警</div>
              </el-form-item>
              <el-form-item label="热度突增阈值">
                <el-slider v-model="thresholds.heatSpike" :max="500" :format-tooltip="v => v + '%'" />
                <div class="threshold-hint">当热度增长超过 {{ thresholds.heatSpike }}% 时触发预警</div>
              </el-form-item>
              <el-form-item label="数据量阈值">
                <el-input-number v-model="thresholds.dataVolume" :min="100" :max="100000" :step="100" />
                <div class="threshold-hint">当单位时间数据量超过 {{ thresholds.dataVolume }} 条时触发预警</div>
              </el-form-item>
              <el-button type="primary" style="width: 100%" @click="saveThresholds">保存设置</el-button>
            </el-form>
          </el-card>
        </el-col>

        <!-- 历史趋势对比 -->
        <el-col :span="8">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span><el-icon><Calendar /></el-icon> 历史对比</span>
                <el-date-picker v-model="compareDate" type="date" size="small" placeholder="选择对比日期" />
              </div>
            </template>
            <div ref="compareChartRef" style="height: 250px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 四象限散点图视图 -->
    <div v-show="viewMode === 'scatter'" class="scatter-view">
      <el-row :gutter="16">
        <!-- 参数配置面板 -->
        <el-col :span="6">
          <el-card shadow="hover" class="config-panel">
            <template #header>
              <span><el-icon><Operation /></el-icon> 参数配置</span>
            </template>
            
            <div class="config-section">
              <div class="config-title">
                <span>权重配置</span>
                <el-tooltip content="情感权重α和热度权重β的和为1">
                  <el-icon><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              
              <div class="weight-display">
                <div class="weight-item">
                  <span class="weight-label">情感权重 (α)</span>
                  <el-tag type="primary" effect="dark">{{ (config.sentimentWeight * 100).toFixed(0) }}%</el-tag>
                </div>
                <div class="weight-item">
                  <span class="weight-label">热度权重 (β)</span>
                  <el-tag type="success" effect="dark">{{ (config.heatWeight * 100).toFixed(0) }}%</el-tag>
                </div>
              </div>
              
              <div class="weight-slider">
                <el-slider 
                  v-model="config.sentimentWeight" 
                  :min="0" 
                  :max="1" 
                  :step="0.05"
                  :format-tooltip="v => `α=${(v*100).toFixed(0)}% β=${((1-v)*100).toFixed(0)}%`"
                  @change="onWeightChange"
                />
                <div class="slider-labels">
                  <span>热度优先</span>
                  <span>情感优先</span>
                </div>
              </div>
            </div>

            <el-divider />

            <div class="config-section">
              <div class="config-title">互动权重</div>
              <el-form label-position="left" label-width="80px" size="small">
                <el-form-item label="转发">
                  <el-slider v-model="config.repostWeight" :min="0" :max="10" :step="0.5" show-input />
                </el-form-item>
                <el-form-item label="评论">
                  <el-slider v-model="config.commentWeight" :min="0" :max="10" :step="0.5" show-input />
                </el-form-item>
                <el-form-item label="点赞">
                  <el-slider v-model="config.likeWeight" :min="0" :max="10" :step="0.5" show-input />
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <div class="config-section">
              <div class="config-title">时间衰减</div>
              <el-form label-position="left" label-width="80px" size="small">
                <el-form-item label="启用">
                  <el-switch v-model="config.timeDecayEnabled" />
                </el-form-item>
                <el-form-item v-if="config.timeDecayEnabled" label="半衰期">
                  <el-select v-model="config.decayHalfLife" style="width: 100%">
                    <el-option label="6小时" :value="6" />
                    <el-option label="12小时" :value="12" />
                    <el-option label="24小时" :value="24" />
                    <el-option label="48小时" :value="48" />
                    <el-option label="72小时" :value="72" />
                  </el-select>
                </el-form-item>
              </el-form>
              
              <!-- 衰减曲线预览 -->
              <div v-if="config.timeDecayEnabled" ref="decayCurveRef" style="height: 100px; margin-top: 10px"></div>
            </div>

            <el-divider />

            <div class="config-section">
              <div class="config-title">四象限阈值</div>
              <el-form label-position="left" label-width="80px" size="small">
                <el-form-item label="情感阈值">
                  <el-slider v-model="config.sentimentThreshold" :min="0" :max="1" :step="0.05" />
                </el-form-item>
                <el-form-item label="热度阈值">
                  <el-slider v-model="config.heatThreshold" :min="0" :max="1" :step="0.05" />
                </el-form-item>
              </el-form>
            </div>

            <el-button type="primary" style="width: 100%; margin-top: 16px" @click="applyConfig">
              应用配置
            </el-button>
            <el-button style="width: 100%; margin-top: 8px" @click="resetConfig">
              重置默认
            </el-button>
          </el-card>
        </el-col>

        <!-- 四象限散点图 -->
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span><el-icon><DataAnalysis /></el-icon> 情感-热度四象限分析</span>
                <div>
                  <el-button size="small" @click="exportScatterData">
                    <el-icon><Download /></el-icon> 导出
                  </el-button>
                  <el-button size="small" @click="toggleFullscreen">
                    <el-icon><FullScreen /></el-icon>
                  </el-button>
                </div>
              </div>
            </template>
            <div ref="scatterChartRef" style="height: 500px"></div>
          </el-card>
        </el-col>

        <!-- 象限统计和详情 -->
        <el-col :span="6">
          <!-- 象限统计 -->
          <el-card shadow="hover" class="quadrant-stats">
            <template #header>
              <span><el-icon><Histogram /></el-icon> 象限分布</span>
            </template>
            <div class="quadrant-grid">
              <div 
                v-for="(quad, key) in quadrantInfo" 
                :key="key" 
                class="quadrant-item"
                :class="{ active: selectedQuadrant === key }"
                :style="{ borderColor: quad.color }"
                @click="filterByQuadrant(key)"
              >
                <div class="quadrant-count" :style="{ color: quad.color }">
                  {{ quadrantStats[key]?.count || 0 }}
                </div>
                <div class="quadrant-label">{{ quad.label }}</div>
                <div class="quadrant-ratio">
                  {{ ((quadrantStats[key]?.ratio || 0) * 100).toFixed(1) }}%
                </div>
                <el-progress 
                  :percentage="(quadrantStats[key]?.ratio || 0) * 100" 
                  :color="quad.color"
                  :show-text="false"
                  :stroke-width="4"
                />
              </div>
            </div>
          </el-card>

          <!-- 选中项详情 -->
          <el-card v-if="selectedPoint" shadow="hover" style="margin-top: 16px">
            <template #header>
              <span><el-icon><Document /></el-icon> 详情</span>
            </template>
            <div class="point-detail">
              <div class="detail-text">{{ selectedPoint.text }}</div>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="情感">
                  <el-tag :type="getSentimentType(selectedPoint.sentiment)">
                    {{ getSentimentLabel(selectedPoint.sentiment) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="情感得分">
                  {{ selectedPoint.sentimentScore }}
                </el-descriptions-item>
                <el-descriptions-item label="热度得分">
                  {{ selectedPoint.heatScore }}
                </el-descriptions-item>
                <el-descriptions-item label="综合得分">
                  <span class="highlight">{{ selectedPoint.dualScore }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="象限">
                  <el-tag :color="quadrantInfo[selectedPoint.quadrant]?.color" effect="dark">
                    {{ quadrantInfo[selectedPoint.quadrant]?.label }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 趋势分析视图 -->
    <div v-show="viewMode === 'trend'" class="trend-view">
      <el-row :gutter="16">
        <el-col :span="24">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span><el-icon><TrendCharts /></el-icon> 多维度趋势分析</span>
                <div>
                  <el-radio-group v-model="trendPeriod" size="small">
                    <el-radio-button label="hour">小时</el-radio-button>
                    <el-radio-button label="day">日</el-radio-button>
                    <el-radio-button label="week">周</el-radio-button>
                    <el-radio-button label="month">月</el-radio-button>
                  </el-radio-group>
                  <el-date-picker 
                    v-model="trendDateRange" 
                    type="daterange" 
                    size="small"
                    range-separator="至"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    style="margin-left: 10px"
                  />
                </div>
              </div>
            </template>
            <div ref="trendChartRef" style="height: 400px"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <span><el-icon><Histogram /></el-icon> 情感强度分布</span>
            </template>
            <div ref="intensityChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <span><el-icon><Connection /></el-icon> 热度-情感相关性</span>
            </template>
            <div ref="correlationChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  Odometer, DataAnalysis, TrendCharts, Refresh, DataLine, PieChart,
  Bell, Setting, Calendar, Operation, QuestionFilled, Download,
  FullScreen, Histogram, Document, WarningFilled, Close, Top, Bottom, Connection
} from '@element-plus/icons-vue';

// ==================== 状态定义 ====================

const viewMode = ref<'dashboard' | 'scatter' | 'trend'>('dashboard');
const loading = ref(false);
const autoRefresh = ref(true);
const refreshInterval = ref(10000);
const streamStatus = ref<'running' | 'paused'>('running');
const distributionType = ref<'pie' | 'gauge'>('pie');
const compareDate = ref<Date | null>(null);
const trendPeriod = ref('day');
const trendDateRange = ref<[Date, Date] | null>(null);
const selectedQuadrant = ref<string | null>(null);
const selectedPoint = ref<any>(null);

// 图表引用
const realtimeChartRef = ref<HTMLElement>();
const distributionChartRef = ref<HTMLElement>();
const compareChartRef = ref<HTMLElement>();
const scatterChartRef = ref<HTMLElement>();
const decayCurveRef = ref<HTMLElement>();
const trendChartRef = ref<HTMLElement>();
const intensityChartRef = ref<HTMLElement>();
const correlationChartRef = ref<HTMLElement>();

// 图表实例
let realtimeChart: echarts.ECharts | null = null;
let distributionChart: echarts.ECharts | null = null;
let compareChart: echarts.ECharts | null = null;
let scatterChart: echarts.ECharts | null = null;
let decayCurveChart: echarts.ECharts | null = null;
let trendChart: echarts.ECharts | null = null;
let intensityChart: echarts.ECharts | null = null;
let correlationChart: echarts.ECharts | null = null;

// 定时器
let refreshTimer: number | null = null;
let realtimeTimer: number | null = null;

// ==================== 配置 ====================

const config = reactive({
  sentimentWeight: 0.5,
  heatWeight: 0.5,
  repostWeight: 3.0,
  commentWeight: 2.0,
  likeWeight: 1.0,
  timeDecayEnabled: true,
  decayHalfLife: 24,
  sentimentThreshold: 0.5,
  heatThreshold: 0.5,
});

const thresholds = reactive({
  negativeRatio: 30,
  heatSpike: 200,
  dataVolume: 1000,
});

// ==================== 数据 ====================

const coreMetrics = ref([
  { key: 'total', label: '总数据量', value: 125680, unit: '条', icon: 'DataLine', color: '#409EFF', trend: 12.5, status: 'normal' },
  { key: 'positive', label: '正面情感', value: 45.2, unit: '%', icon: 'Top', color: '#67C23A', trend: 3.2, decimals: 1, status: 'normal' },
  { key: 'negative', label: '负面情感', value: 18.5, unit: '%', icon: 'Bottom', color: '#F56C6C', trend: -2.1, decimals: 1, status: 'warning' },
  { key: 'heat', label: '平均热度', value: 8520, unit: '', icon: 'Histogram', color: '#E6A23C', trend: 25.8, status: 'normal' },
]);

const alerts = ref([
  { id: 1, level: 'warning', title: '负面情感上升', description: '近1小时负面情感占比上升5%', time: new Date() },
  { id: 2, level: 'danger', title: '热度异常', description: '话题#测试#热度突增300%', time: new Date(Date.now() - 300000) },
  { id: 3, level: 'info', title: '新热点出现', description: '检测到新兴话题#新话题#', time: new Date(Date.now() - 600000) },
]);

const quadrantInfo: Record<string, any> = {
  high_sentiment_high_heat: { label: '重点关注', color: '#F56C6C', description: '高情感高热度' },
  high_sentiment_low_heat: { label: '潜在风险', color: '#E6A23C', description: '高情感低热度' },
  low_sentiment_high_heat: { label: '热门中性', color: '#409EFF', description: '低情感高热度' },
  low_sentiment_low_heat: { label: '一般内容', color: '#909399', description: '低情感低热度' },
};

const quadrantStats = ref<Record<string, any>>({
  high_sentiment_high_heat: { count: 156, ratio: 0.25 },
  high_sentiment_low_heat: { count: 89, ratio: 0.14 },
  low_sentiment_high_heat: { count: 234, ratio: 0.38 },
  low_sentiment_low_heat: { count: 142, ratio: 0.23 },
});

const scatterData = ref<any[]>([]);
const realtimeData = ref<any[]>([]);

// ==================== 方法 ====================

const onWeightChange = () => {
  config.heatWeight = 1 - config.sentimentWeight;
};

const applyConfig = () => {
  ElMessage.success('配置已应用');
  updateScatterChart();
};

const resetConfig = () => {
  config.sentimentWeight = 0.5;
  config.heatWeight = 0.5;
  config.repostWeight = 3.0;
  config.commentWeight = 2.0;
  config.likeWeight = 1.0;
  config.timeDecayEnabled = true;
  config.decayHalfLife = 24;
  config.sentimentThreshold = 0.5;
  config.heatThreshold = 0.5;
  ElMessage.info('已重置为默认配置');
};

const refreshData = async () => {
  loading.value = true;
  try {
    // 模拟数据刷新
    await new Promise(resolve => setTimeout(resolve, 500));
    generateMockData();
    updateAllCharts();
    ElMessage.success('数据已刷新');
  } catch (error) {
    ElMessage.warning('刷新失败');
  } finally {
    loading.value = false;
  }
};

const generateMockData = () => {
  // 生成散点图数据
  scatterData.value = [];
  for (let i = 0; i < 200; i++) {
    const sentiment = Math.random() * 2 - 1;
    const heat = Math.random();
    const sentimentNorm = (sentiment + 1) / 2;
    
    let quadrant: string;
    if (sentimentNorm >= config.sentimentThreshold && heat >= config.heatThreshold) {
      quadrant = 'high_sentiment_high_heat';
    } else if (sentimentNorm >= config.sentimentThreshold && heat < config.heatThreshold) {
      quadrant = 'high_sentiment_low_heat';
    } else if (sentimentNorm < config.sentimentThreshold && heat >= config.heatThreshold) {
      quadrant = 'low_sentiment_high_heat';
    } else {
      quadrant = 'low_sentiment_low_heat';
    }
    
    scatterData.value.push({
      id: i,
      x: heat * 100,
      y: sentimentNorm * 100,
      value: (config.sentimentWeight * sentimentNorm + config.heatWeight * heat) * 100,
      quadrant,
      text: `这是第${i + 1}条微博内容示例...`,
      sentiment: sentiment > 0.2 ? 'positive' : sentiment < -0.2 ? 'negative' : 'neutral',
      sentimentScore: sentiment.toFixed(3),
      heatScore: heat.toFixed(3),
      dualScore: (config.sentimentWeight * sentimentNorm + config.heatWeight * heat).toFixed(3),
    });
  }
  
  // 更新象限统计
  const stats: Record<string, any> = {};
  for (const q of Object.keys(quadrantInfo)) {
    const items = scatterData.value.filter(d => d.quadrant === q);
    stats[q] = {
      count: items.length,
      ratio: items.length / scatterData.value.length,
    };
  }
  quadrantStats.value = stats;
};

const saveThresholds = () => {
  ElMessage.success('预警阈值已保存');
};

const dismissAlert = (id: number) => {
  const index = alerts.value.findIndex(a => a.id === id);
  if (index > -1) {
    alerts.value.splice(index, 1);
  }
};

const filterByQuadrant = (quadrant: string) => {
  selectedQuadrant.value = selectedQuadrant.value === quadrant ? null : quadrant;
  updateScatterChart();
};

const formatTime = (time: Date) => {
  const diff = Date.now() - time.getTime();
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  return time.toLocaleDateString();
};

const getSentimentType = (sentiment: string) => {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger' };
  return map[sentiment] || 'info';
};

const getSentimentLabel = (sentiment: string) => {
  const map: Record<string, string> = { positive: '正面', neutral: '中性', negative: '负面' };
  return map[sentiment] || '未知';
};

const exportScatterData = () => {
  const dataStr = JSON.stringify(scatterData.value, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `scatter_data_${Date.now()}.json`;
  link.click();
  URL.revokeObjectURL(url);
  ElMessage.success('数据已导出');
};

const toggleFullscreen = () => {
  const el = scatterChartRef.value?.parentElement;
  if (el) {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      el.requestFullscreen();
    }
  }
};

// ==================== 图表初始化 ====================

const initRealtimeChart = () => {
  if (!realtimeChartRef.value) return;
  realtimeChart = echarts.init(realtimeChartRef.value);
  
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '中性', '负面'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: Array.from({ length: 20 }, (_, i) => `${i}s`),
    },
    yAxis: { type: 'value' },
    series: [
      { name: '正面', type: 'line', smooth: true, areaStyle: { opacity: 0.3 }, data: [], itemStyle: { color: '#67C23A' } },
      { name: '中性', type: 'line', smooth: true, areaStyle: { opacity: 0.3 }, data: [], itemStyle: { color: '#909399' } },
      { name: '负面', type: 'line', smooth: true, areaStyle: { opacity: 0.3 }, data: [], itemStyle: { color: '#F56C6C' } },
    ],
  };
  
  realtimeChart.setOption(option);
  
  // 模拟实时数据
  realtimeTimer = window.setInterval(() => {
    if (streamStatus.value !== 'running') return;
    
    const series = realtimeChart?.getOption()?.series as any[];
    if (series) {
      series.forEach((s, i) => {
        const data = s.data || [];
        data.push(Math.floor(Math.random() * 100));
        if (data.length > 20) data.shift();
        s.data = data;
      });
      realtimeChart?.setOption({ series });
    }
  }, 1000);
};

const initDistributionChart = () => {
  if (!distributionChartRef.value) return;
  distributionChart = echarts.init(distributionChartRef.value);
  updateDistributionChart();
};

const updateDistributionChart = () => {
  if (!distributionChart) return;
  
  const option: echarts.EChartsOption = distributionType.value === 'pie' ? {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: [
        { value: 45, name: '正面', itemStyle: { color: '#67C23A' } },
        { value: 30, name: '中性', itemStyle: { color: '#909399' } },
        { value: 25, name: '负面', itemStyle: { color: '#F56C6C' } },
      ],
    }],
  } : {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 10,
        itemStyle: { color: '#67C23A' },
        progress: { show: true, width: 30 },
        pointer: { show: false },
        axisLine: { lineStyle: { width: 30 } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: { offsetCenter: [0, '-20%'], fontSize: 16 },
        detail: { valueAnimation: true, offsetCenter: [0, '10%'], fontSize: 30, formatter: '{value}%', color: '#67C23A' },
        data: [{ value: 45, name: '正面情感占比' }],
      },
    ],
  };
  
  distributionChart.setOption(option, true);
};

const initScatterChart = () => {
  if (!scatterChartRef.value) return;
  scatterChart = echarts.init(scatterChartRef.value);
  
  scatterChart.on('click', (params: any) => {
    if (params.data) {
      const point = scatterData.value.find(d => d.x === params.data[0] && d.y === params.data[1]);
      if (point) {
        selectedPoint.value = point;
      }
    }
  });
  
  updateScatterChart();
};

const updateScatterChart = () => {
  if (!scatterChart) return;
  
  // 按象限分组
  const seriesData: Record<string, any[]> = {};
  for (const q of Object.keys(quadrantInfo)) {
    seriesData[q] = [];
  }
  
  for (const item of scatterData.value) {
    if (selectedQuadrant.value && item.quadrant !== selectedQuadrant.value) continue;
    seriesData[item.quadrant]?.push([item.x, item.y, item.value, item.text, item.id]);
  }
  
  const series = Object.entries(quadrantInfo).map(([key, info]) => ({
    name: info.label,
    type: 'scatter',
    symbolSize: (data: any) => Math.max(8, Math.min(25, data[2] / 4)),
    data: seriesData[key],
    itemStyle: { color: info.color, opacity: 0.8 },
    emphasis: {
      focus: 'series',
      itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
    },
  }));
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => `
        <div style="padding: 8px">
          <div style="font-weight: bold; margin-bottom: 4px">${params.data[3]?.slice(0, 30)}...</div>
          <div>热度: ${params.data[0].toFixed(1)}</div>
          <div>情感: ${params.data[1].toFixed(1)}</div>
          <div>综合: ${params.data[2].toFixed(1)}</div>
        </div>
      `,
    },
    legend: { data: Object.values(quadrantInfo).map(q => q.label), bottom: 0 },
    grid: { left: '8%', right: '8%', top: '8%', bottom: '15%' },
    xAxis: {
      name: '热度得分',
      nameLocation: 'middle',
      nameGap: 30,
      min: 0,
      max: 100,
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#eee' } },
    },
    yAxis: {
      name: '情感得分',
      nameLocation: 'middle',
      nameGap: 40,
      min: 0,
      max: 100,
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#eee' } },
    },
    series,
    graphic: [
      // 垂直分界线
      {
        type: 'line',
        shape: {
          x1: scatterChart.convertToPixel('grid', [config.heatThreshold * 100, 0])[0],
          y1: scatterChart.convertToPixel('grid', [0, 0])[1],
          x2: scatterChart.convertToPixel('grid', [config.heatThreshold * 100, 100])[0],
          y2: scatterChart.convertToPixel('grid', [0, 100])[1],
        },
        style: { stroke: '#999', lineDash: [5, 5], lineWidth: 2 },
      },
      // 水平分界线
      {
        type: 'line',
        shape: {
          x1: scatterChart.convertToPixel('grid', [0, config.sentimentThreshold * 100])[0],
          y1: scatterChart.convertToPixel('grid', [0, config.sentimentThreshold * 100])[1],
          x2: scatterChart.convertToPixel('grid', [100, config.sentimentThreshold * 100])[0],
          y2: scatterChart.convertToPixel('grid', [100, config.sentimentThreshold * 100])[1],
        },
        style: { stroke: '#999', lineDash: [5, 5], lineWidth: 2 },
      },
      // 象限标签
      { type: 'text', left: '15%', top: '15%', style: { text: '潜在风险', fill: '#E6A23C', fontSize: 12 } },
      { type: 'text', right: '15%', top: '15%', style: { text: '重点关注', fill: '#F56C6C', fontSize: 12 } },
      { type: 'text', left: '15%', bottom: '20%', style: { text: '一般内容', fill: '#909399', fontSize: 12 } },
      { type: 'text', right: '15%', bottom: '20%', style: { text: '热门中性', fill: '#409EFF', fontSize: 12 } },
    ],
  };
  
  scatterChart.setOption(option);
};

const initDecayCurveChart = () => {
  if (!decayCurveRef.value) return;
  decayCurveChart = echarts.init(decayCurveRef.value);
  updateDecayCurveChart();
};

const updateDecayCurveChart = () => {
  if (!decayCurveChart) return;
  
  const halfLife = config.decayHalfLife;
  const lambda = Math.log(2) / halfLife;
  const data = [];
  
  for (let t = 0; t <= 72; t += 1) {
    data.push([t, Math.exp(-lambda * t) * 100]);
  }
  
  const option: echarts.EChartsOption = {
    grid: { left: '10%', right: '5%', top: '10%', bottom: '20%' },
    xAxis: { type: 'value', name: '小时', nameLocation: 'middle', nameGap: 20, max: 72 },
    yAxis: { type: 'value', name: '%', max: 100, show: false },
    series: [{
      type: 'line',
      data,
      smooth: true,
      areaStyle: { opacity: 0.3 },
      itemStyle: { color: '#409EFF' },
      markLine: {
        data: [{ xAxis: halfLife, label: { formatter: '半衰期' } }],
        lineStyle: { type: 'dashed', color: '#F56C6C' },
      },
    }],
  };
  
  decayCurveChart.setOption(option);
};

const initTrendChart = () => {
  if (!trendChartRef.value) return;
  trendChart = echarts.init(trendChartRef.value);
  
  const dates = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - 29 + i);
    return d.toLocaleDateString();
  });
  
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['正面', '中性', '负面', '热度'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '情感数量' },
      { type: 'value', name: '热度', position: 'right' },
    ],
    dataZoom: [{ type: 'inside', start: 50, end: 100 }, { type: 'slider', start: 50, end: 100 }],
    series: [
      { name: '正面', type: 'bar', stack: 'sentiment', data: dates.map(() => Math.floor(Math.random() * 500 + 300)), itemStyle: { color: '#67C23A' } },
      { name: '中性', type: 'bar', stack: 'sentiment', data: dates.map(() => Math.floor(Math.random() * 300 + 200)), itemStyle: { color: '#909399' } },
      { name: '负面', type: 'bar', stack: 'sentiment', data: dates.map(() => Math.floor(Math.random() * 200 + 100)), itemStyle: { color: '#F56C6C' } },
      { name: '热度', type: 'line', yAxisIndex: 1, data: dates.map(() => Math.floor(Math.random() * 10000 + 5000)), itemStyle: { color: '#E6A23C' } },
    ],
  };
  
  trendChart.setOption(option);
};

const initIntensityChart = () => {
  if (!intensityChartRef.value) return;
  intensityChart = echarts.init(intensityChartRef.value);
  
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['0-20', '20-40', '40-60', '60-80', '80-100'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [120, 200, 350, 280, 150],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409EFF' },
          { offset: 1, color: '#67C23A' },
        ]),
      },
    }],
  };
  
  intensityChart.setOption(option);
};

const initCorrelationChart = () => {
  if (!correlationChartRef.value) return;
  correlationChart = echarts.init(correlationChartRef.value);
  
  const data = Array.from({ length: 100 }, () => [Math.random() * 100, Math.random() * 100]);
  
  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'item' },
    xAxis: { type: 'value', name: '热度' },
    yAxis: { type: 'value', name: '情感强度' },
    series: [{
      type: 'scatter',
      data,
      symbolSize: 8,
      itemStyle: { color: '#409EFF', opacity: 0.6 },
    }],
  };
  
  correlationChart.setOption(option);
};

const updateAllCharts = () => {
  updateScatterChart();
  updateDistributionChart();
  updateDecayCurveChart();
};

// ==================== 生命周期 ====================

onMounted(() => {
  generateMockData();
  
  nextTick(() => {
    initRealtimeChart();
    initDistributionChart();
    initScatterChart();
    initDecayCurveChart();
    initTrendChart();
    initIntensityChart();
    initCorrelationChart();
  });
  
  // 自动刷新
  watch([autoRefresh, refreshInterval], () => {
    if (refreshTimer) clearInterval(refreshTimer);
    if (autoRefresh.value) {
      refreshTimer = window.setInterval(refreshData, refreshInterval.value);
    }
  }, { immediate: true });
  
  // 监听分布类型变化
  watch(distributionType, updateDistributionChart);
  
  // 监听衰减参数变化
  watch(() => config.decayHalfLife, updateDecayCurveChart);
  
  // 窗口大小变化
  window.addEventListener('resize', () => {
    realtimeChart?.resize();
    distributionChart?.resize();
    scatterChart?.resize();
    decayCurveChart?.resize();
    trendChart?.resize();
    intensityChart?.resize();
    correlationChart?.resize();
  });
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  if (realtimeTimer) clearInterval(realtimeTimer);
  
  realtimeChart?.dispose();
  distributionChart?.dispose();
  scatterChart?.dispose();
  decayCurveChart?.dispose();
  trendChart?.dispose();
  intensityChart?.dispose();
  correlationChart?.dispose();
});

// CountUp组件（简化版）
const CountUp = {
  props: ['endVal', 'duration', 'decimals'],
  setup(props: any) {
    const displayValue = ref(0);
    onMounted(() => {
      const step = props.endVal / (props.duration * 60);
      const timer = setInterval(() => {
        displayValue.value += step;
        if (displayValue.value >= props.endVal) {
          displayValue.value = props.endVal;
          clearInterval(timer);
        }
      }, 1000 / 60);
    });
    return () => displayValue.value.toFixed(props.decimals || 0);
  },
};
</script>

<style scoped lang="scss">
.advanced-visualization {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.control-right {
  display: flex;
  align-items: center;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

// 指标卡片
.metric-card {
  border-radius: 12px;
  transition: transform 0.3s, box-shadow 0.3s;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  }
  
  &.warning {
    border-left: 4px solid var(--color-warning);
  }
  
  &.danger {
    border-left: 4px solid var(--color-danger);
  }
  
  .metric-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  .metric-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }
  
  .metric-info {
    flex: 1;
    
    .metric-value {
      font-size: 28px;
      font-weight: bold;
      color: #303133;
      
      .metric-unit {
        font-size: 14px;
        color: var(--color-text-secondary);
        margin-left: 4px;
      }
    }
    
    .metric-label {
      font-size: 14px;
      color: #606266;
      margin-top: 4px;
    }
    
    .metric-trend {
      font-size: 12px;
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 2px;
      
      &.up { color: var(--color-success); }
      &.down { color: var(--color-danger); }
    }
  }
}

// 预警列表
.alert-card {
  .alert-list {
    max-height: 300px;
    overflow-y: auto;
  }
  
  .alert-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 8px;
    background: #f5f7fa;
    transition: background 0.3s;
    
    &:hover {
      background: #ecf5ff;
    }
    
    &.warning {
      border-left: 3px solid var(--color-warning);
    }
    
    &.danger {
      border-left: 3px solid var(--color-danger);
    }
    
    &.info {
      border-left: 3px solid var(--color-primary);
    }
    
    .alert-icon {
      color: var(--color-warning);
    }
    
    .alert-content {
      flex: 1;
      
      .alert-title {
        font-weight: 500;
        color: #303133;
      }
      
      .alert-desc {
        font-size: 12px;
        color: #606266;
        margin-top: 4px;
      }
      
      .alert-time {
        font-size: 12px;
        color: var(--color-text-secondary);
        margin-top: 4px;
      }
    }
  }
}

.threshold-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

// 配置面板
.config-panel {
  .config-section {
    margin-bottom: 16px;
  }
  
  .config-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 12px;
  }
  
  .weight-display {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    
    .weight-item {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .weight-label {
        font-size: 13px;
        color: #606266;
      }
    }
  }
  
  .weight-slider {
    .slider-labels {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--color-text-secondary);
      margin-top: 4px;
    }
  }
}

// 象限统计
.quadrant-stats {
  .quadrant-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .quadrant-item {
    padding: 12px;
    border-radius: 8px;
    border: 2px solid #eee;
    cursor: pointer;
    transition: all 0.3s;
    text-align: center;
    
    &:hover, &.active {
      border-color: currentColor;
      background: rgba(0, 0, 0, 0.02);
    }
    
    .quadrant-count {
      font-size: 24px;
      font-weight: bold;
    }
    
    .quadrant-label {
      font-size: 12px;
      color: #606266;
      margin: 4px 0;
    }
    
    .quadrant-ratio {
      font-size: 14px;
      color: var(--color-text-secondary);
    }
  }
}

// 详情面板
.point-detail {
  .detail-text {
    padding: 12px;
    background: #f5f7fa;
    border-radius: 8px;
    margin-bottom: 12px;
    font-size: 14px;
    line-height: 1.6;
    color: #303133;
  }
  
  .highlight {
    font-size: 18px;
    font-weight: bold;
    color: var(--color-primary);
  }
}

// 动画
.alert-enter-active,
.alert-leave-active {
  transition: all 0.3s ease;
}

.alert-enter-from,
.alert-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
