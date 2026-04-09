<template>
  <div class="realtime-monitor-module">
    <div class="monitor-layout">
      <!-- 中央数据流 (70%) -->
      <main class="center-panel">
        <el-card class="dataflow-card">
          <template #header>
            <div class="card-header">
              <div class="connection-status">
                <el-icon><DataLine /></el-icon>
                <span> </span>
                <div class="status-indicator">
                  <el-tooltip :content="connectionStatus.tooltip" placement="top">
                    <div class="status-dot" :class="connectionStatus.class"></div>
                  </el-tooltip>
                  <el-tag :type="connectionStatus.tagType" size="small" effect="plain" style="margin-left: 8px">
                    <el-icon v-if="connectionStatus.connected" class="rotating-icon"><Refresh /></el-icon>
                    {{ connectionStatus.text }}
                  </el-tag>
                </div>
              </div>
              <el-tag v-if="dataSource" type="info" size="small">来源: {{ dataSource }}</el-tag>
            </div>
          </template>
          <div class="dataflow-controls">
            <el-switch v-model="autoScroll" active-text="自动滚动" />
            <el-button-group size="small">
              <el-button :type="filterType === 'all' ? 'primary' : ''" @click="filterType = 'all'">
                全部 ({{ dataStream.length }})
              </el-button>
              <el-button :type="filterType === 'positive' ? 'primary' : ''" @click="filterType = 'positive'">
                正面 ({{ positiveCount }})
              </el-button>
              <el-button :type="filterType === 'negative' ? 'primary' : ''" @click="filterType = 'negative'">
                负面 ({{ negativeCount }})
              </el-button>
            </el-button-group>
            <el-button :icon="Refresh" :loading="loading" @click="refreshData">刷新</el-button>
          </div>
          
          <el-tabs v-model="activeKeywordTab" type="card" class="keyword-tabs">
            <el-tab-pane label=" " name="all">
              <template #label>
                <span> </span>
                <el-badge :value="dataStream.length" class="tab-badge" />
              </template>
              
              <el-scrollbar ref="scrollbarRef" height="550px">
                <el-timeline class="data-timeline">
                  <el-timeline-item
                    v-for="item in filteredDataStream"
                    :key="item.id"
                    :timestamp="item.time"
                    :type="getSentimentType(item.sentiment)"
                    size="large"
                  >
                    <el-card class="data-card" :class="`sentiment-${item.sentiment}`">
                      <div class="data-header">
                        <div class="user-info">
                          <el-avatar :size="32" :src="item.avatar" />
                          <span class="username">{{ item.username }}</span>
                          <el-tag :type="getSentimentType(item.sentiment)" size="small">
                            {{ getSentimentLabel(item.sentiment) }}
                            <span v-if="item.sentimentScore" style="margin-left: 4px">
                              {{ (item.sentimentScore * 100).toFixed(0) }}%
                            </span>
                          </el-tag>
                        </div>
                        <div class="data-meta">
                          <el-tag v-if="item.keyword" type="warning" size="small" effect="plain">
                            #{{ item.keyword }}
                          </el-tag>
                          <span v-if="item.source">{{ item.source }}</span>
                          <span v-if="item.location">{{ item.location }}</span>
                        </div>
                      </div>
                      <div class="data-content">{{ item.content }}</div>
                      <div class="data-stats">
                        <span><el-icon><View /></el-icon> {{ item.views }}</span>
                        <span><el-icon><ChatDotRound /></el-icon> {{ item.comments }}</span>
                        <span><el-icon><Star /></el-icon> {{ item.likes }}</span>
                      </div>
                    </el-card>
                  </el-timeline-item>
                </el-timeline>
              </el-scrollbar>
            </el-tab-pane>
            
            <el-tab-pane 
              v-for="keyword in monitorKeywords" 
              :key="keyword"
              :label="keyword"
              :name="keyword"
            >
              <template #label>
                <span>#{{ keyword }}</span>
                <el-badge :value="getKeywordDataCount(keyword)" class="tab-badge" />
              </template>
              
              <!--  -->
              <div class="keyword-stats">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-statistic title=" " :value="getKeywordSentimentCount(keyword, 'positive')" />
                  </el-col>
                  <el-col :span="8">
                    <el-statistic title=" " :value="getKeywordSentimentCount(keyword, 'negative')" />
                  </el-col>
                  <el-col :span="8">
                    <el-statistic title=" " :value="getKeywordSentimentCount(keyword, 'neutral')" />
                  </el-col>
                </el-row>
                
                <el-progress 
                  :percentage="getKeywordSentimentRatio(keyword, 'positive')" 
                  status="success" 
                  :show-text="false"
                  style="margin: 8px 0"
                />
                <el-progress 
                  :percentage="getKeywordSentimentRatio(keyword, 'negative')" 
                  status="danger" 
                  :show-text="false"
                  style="margin: 8px 0"
                />
                <el-progress 
                  :percentage="getKeywordSentimentRatio(keyword, 'neutral')" 
                  status="warning" 
                  :show-text="false"
                  style="margin: 8px 0"
                />
              </div>
              
              <!--  -->
              <el-scrollbar height="400px">
                <el-timeline class="data-timeline">
                  <el-timeline-item
                    v-for="item in getKeywordDataStream(keyword)"
                    :key="item.id"
                    :timestamp="item.time"
                    :type="getSentimentType(item.sentiment)"
                    size="large"
                  >
                    <el-card class="data-card" :class="`sentiment-${item.sentiment}`">
                      <div class="data-header">
                        <div class="user-info">
                          <el-avatar :size="32" :src="item.avatar" />
                          <span class="username">{{ item.username }}</span>
                          <el-tag :type="getSentimentType(item.sentiment)" size="small">
                            {{ getSentimentLabel(item.sentiment) }}
                            <span v-if="item.sentimentScore" style="margin-left: 4px">
                              {{ (item.sentimentScore * 100).toFixed(0) }}%
                            </span>
                          </el-tag>
                        </div>
                        <div class="data-meta">
                          <el-tag type="warning" size="small" effect="plain">
                            #{{ keyword }}
                          </el-tag>
                          <span v-if="item.source">{{ item.source }}</span>
                          <span v-if="item.location">{{ item.location }}</span>
                        </div>
                      </div>
                      <div class="data-content">{{ item.content }}</div>
                      <div class="data-stats">
                        <span><el-icon><View /></el-icon> {{ item.views }}</span>
                        <span><el-icon><ChatDotRound /></el-icon> {{ item.comments }}</span>
                        <span><el-icon><Star /></el-icon> {{ item.likes }}</span>
                      </div>
                    </el-card>
                  </el-timeline-item>
                </el-timeline>
              </el-scrollbar>
            </el-tab-pane>
          </el-tabs>
        </el-card>
        
        <!-- 实时指标卡片 -->
        <el-row :gutter="16" style="margin-top: 16px">
          <el-col :span="6">
            <StatCard
              title="在线用户"
              :value="realtimeMetrics.onlineUsers"
              :icon="User"
              type="primary"
              :trend="{ type: 'up', value: '+5%' }"
            />
          </el-col>
          <el-col :span="6">
            <StatCard
              title="处理速度"
              :value="realtimeMetrics.processSpeed"
              suffix="条/秒"
              :icon="Timer"
              type="success"
            />
          </el-col>
          <el-col :span="6">
            <StatCard
              title="平均延迟"
              :value="realtimeMetrics.avgDelay"
              suffix="ms"
              :icon="Connection"
              type="warning"
            />
          </el-col>
          <el-col :span="6">
            <StatCard
              title="错误率"
              :value="realtimeMetrics.errorRate"
              suffix="%"
              :icon="Warning"
              type="danger"
            />
          </el-col>
        </el-row>
      </main>
      
      <!-- 右侧监控面板 (30%) -->
      <aside class="right-panel">
        <!-- 关键词订阅管理 -->
        <el-card class="keyword-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Search /></el-icon> 监控关键词</span>
              <el-button size="small" :icon="Refresh" circle :loading="loadingKeywords" @click="loadKeywords" />
            </div>
          </template>
          <div class="keyword-tags">
            <el-tag
              v-for="kw in monitorKeywords"
              :key="kw"
              closable
              size="default"
              class="keyword-tag"
              @close="removeKeyword(kw)"
            >
              {{ kw }}
            </el-tag>
          </div>
          <div class="keyword-input">
            <el-input
              v-model="newKeyword"
              placeholder="输入关键词"
              size="small"
              @keyup.enter="addKeyword"
            >
              <template #append>
                <el-button :icon="Plus" @click="addKeyword" />
              </template>
            </el-input>
          </div>
        </el-card>

        <!-- 预警阈值配置 -->
        <el-card class="threshold-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Setting /></el-icon> 预警阈值</span>
              <el-switch v-model="alertConfig.alert_enabled" size="small" active-text="启用" />
            </div>
          </template>
          <el-form label-position="top" size="small">
            <el-form-item label="负面情感比例阈值">
              <el-slider v-model="alertConfig.negative_ratio_threshold" :min="0" :max="1" :step="0.05" :format-tooltip="(v: number) => (v * 100).toFixed(0) + '%'" />
            </el-form-item>
            <el-form-item label="情感强度预警阈值">
              <el-slider v-model="alertConfig.intensity_threshold" :min="0" :max="1" :step="0.05" :format-tooltip="(v: number) => v.toFixed(2)" />
            </el-form-item>
            <el-form-item label="检查间隔(秒)">
              <el-input-number v-model="alertConfig.check_interval_seconds" :min="10" :max="600" :step="10" style="width: 100%" />
            </el-form-item>
            
            <!-- 组合预警规则 -->
            <el-divider> 组合预警规则 </el-divider>
            
            <div v-for="rule in alertConfig.composite_rules" :key="rule.id" class="composite-rule">
              <el-form-item :label="`${rule.name}`">
                <el-switch v-model="rule.enabled" size="small" style="margin-right: 8px" />
              </el-form-item>
              
              <el-form-item label="负面情感比例阈值">
                <el-slider 
                  v-model="rule.negative_ratio_threshold" 
                  :min="0" :max="1" :step="0.05" 
                  :format-tooltip="(v: number) => (v * 100).toFixed(0) + '%'"
                  :disabled="!rule.enabled"
                />
              </el-form-item>
              
              <el-form-item label="转发量阈值">
                <el-input-number 
                  v-model="rule.reposts_threshold" 
                  :min="100" :max="10000" :step="100"
                  style="width: 100%"
                  :disabled="!rule.enabled"
                />
              </el-form-item>
              
              <el-form-item label="逻辑运算符">
                <el-radio-group v-model="rule.operator" :disabled="!rule.enabled">
                  <el-radio label="AND"> 并且 </el-radio>
                  <el-radio label="OR"> 或者 </el-radio>
                </el-radio-group>
              </el-form-item>
              
              <el-form-item>
                <el-text type="info" size="small">
                  {{ rule.negative_ratio_threshold * 100 }}% {{ rule.operator === 'AND' ? ' 并且 ' : ' 或者 ' }} {{ rule.reposts_threshold }} 
                </el-text>
              </el-form-item>
            </div>
            
            <el-button type="primary" size="small" :loading="savingConfig" style="width: 100%" @click="saveAlertConfig">
              保存配置
            </el-button>
          </el-form>
        </el-card>

        <!-- 预警系统 -->
        <el-card header="预警系统" class="alert-card">
          <div class="alert-rules">
            <div
              v-for="rule in alertRules"
              :key="rule.id"
              class="rule-item"
              :class="{ active: rule.enabled }"
            >
              <div class="rule-header">
                <el-switch v-model="rule.enabled" size="small" />
                <span class="rule-name">{{ rule.name }}</span>
              </div>
              <div class="rule-condition">{{ rule.condition }}</div>
              <div class="rule-status">
                <el-tag v-if="rule.triggered" type="danger" size="small">
                  已触发 {{ rule.triggerCount }}次
                </el-tag>
                <el-tag v-else type="success" size="small">正常</el-tag>
              </div>
            </div>
          </div>
          
          <el-button type="primary" size="small" block style="margin-top: 12px" @click="showRuleDialog = true">
            <el-icon><Plus /></el-icon>
            添加规则
          </el-button>
        </el-card>
        
        <el-card header="触发记录" class="trigger-card">
          <el-timeline>
            <el-timeline-item
              v-for="trigger in triggerHistory"
              :key="trigger.id"
              :timestamp="trigger.time"
              :type="trigger.level === 'critical' ? 'danger' : 'warning'"
              size="small"
            >
              <div class="trigger-content">
                <div class="trigger-title">{{ trigger.rule }}</div>
                <div class="trigger-desc">{{ trigger.description }}</div>
                <el-button type="primary" link size="small" @click="handleTrigger(trigger)">
                  处理
                </el-button>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
        
        <el-card header="系统状态" class="system-card">
          <div class="system-metrics">
            <div class="metric-item">
              <div class="metric-label">CPU使用率</div>
              <el-progress :percentage="systemStatus.cpu" :color="getStatusColor(systemStatus.cpu)" />
            </div>
            <div class="metric-item">
              <div class="metric-label">内存使用率</div>
              <el-progress :percentage="systemStatus.memory" :color="getStatusColor(systemStatus.memory)" />
            </div>
            <div class="metric-item">
              <div class="metric-label">网络流量</div>
              <el-progress :percentage="systemStatus.network" :color="getStatusColor(systemStatus.network)" />
            </div>
            <div class="metric-item">
              <div class="metric-label">连接状态</div>
              <el-tag :type="systemStatus.connected ? 'success' : 'danger'">
                {{ systemStatus.connected ? '已连接' : '断开' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </aside>
    </div>
    
    <!-- 添加规则对话框 -->
    <el-dialog v-model="showRuleDialog" title="添加预警规则" width="500px">
      <el-form label-width="100px">
        <el-form-item label="规则名称">
          <el-input v-model="newRule.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="监控指标">
          <el-select v-model="newRule.metric" placeholder="选择指标">
            <el-option label="情感负面率" value="negative_rate" />
            <el-option label="数据量激增" value="data_surge" />
            <el-option label="关键词出现" value="keyword" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值">
          <el-input-number v-model="newRule.threshold" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="通知方式">
          <el-checkbox-group v-model="newRule.notifyMethods">
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
            <el-checkbox label="wechat">微信</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRuleDialog = false">取消</el-button>
        <el-button type="primary" @click="addRule">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Refresh, Plus, User, Timer, Connection, Warning,
  View, ChatDotRound, Star, DataLine, Search, Setting,
} from '@element-plus/icons-vue';
import StatCard from '@/components/common/StatCard.vue';
import apiClient from '@/api/index';
import { SUCCESS, WARNING, DANGER } from '@/styles/colors';

// 自动滚动
const autoScroll = ref(true);
const filterType = ref('all');
const scrollbarRef = ref();
const loading = ref(false);
const activeKeywordTab = ref('all');

// SSE 
const connectionStatus = reactive({
  connected: false,
  reconnecting: false,
  retryCount: 0,
  maxRetries: 5,
  text: ' ',
  tooltip: ' ',
  class: 'status-disconnected',
  tagType: 'danger'
});

// SSE 
let eventSource: EventSource | null = null;
let reconnectTimer: NodeJS.Timeout | null = null;
let reconnectDelay = 1000; // 1

// 关键词订阅
const monitorKeywords = ref<string[]>([]);
const newKeyword = ref('');
const loadingKeywords = ref(false);

// 预警配置
const alertConfig = reactive({
  negative_ratio_threshold: 0.30,
  intensity_threshold: 0.80,
  alert_enabled: true,
  check_interval_seconds: 60,
  composite_rules: [
    {
      id: 'composite_1',
      name: '负面情感激增',
      enabled: true,
      negative_ratio_threshold: 0.40,
      reposts_threshold: 1000,
      operator: 'AND'
    },
    {
      id: 'composite_2', 
      name: '负面情感激增',
      enabled: false,
      negative_ratio_threshold: 0.50,
      reposts_threshold: 5000,
      operator: 'AND'
    }
  ]
});
const savingConfig = ref(false);

// 预警记录(从后端)
const alertRecords = ref<any[]>([]);

// 数据流
const dataStream = ref<any[]>([]);
const dataSource = ref('');

// 计算情感分类数量
const positiveCount = computed(() => dataStream.value.filter(item => item.sentiment === 'positive').length);
const negativeCount = computed(() => dataStream.value.filter(item => item.sentiment === 'negative').length);

// 实时指标
const realtimeMetrics = reactive({
  onlineUsers: 12580,
  processSpeed: 156,
  avgDelay: 45,
  errorRate: 0.5,
});

// 预警规则
const alertRules = ref([
  {
    id: '1',
    name: '负面情感激增',
    condition: '负面率 > 30%',
    enabled: true,
    triggered: true,
    triggerCount: 3,
  },
  {
    id: '2',
    name: '数据量异常',
    condition: '数据量 > 10000条/分钟',
    enabled: true,
    triggered: false,
    triggerCount: 0,
  },
  {
    id: '3',
    name: '关键词监控',
    condition: '包含敏感词',
    enabled: false,
    triggered: false,
    triggerCount: 0,
  },
]);

// 触发记录
const triggerHistory = ref([
  {
    id: '1',
    time: '10:25:30',
    rule: '负面情感激增',
    description: '最近5分钟负面情感占比达到35%',
    level: 'critical',
  },
  {
    id: '2',
    time: '10:20:15',
    rule: '数据量异常',
    description: '数据采集速度异常增长',
    level: 'warning',
  },
]);

// 系统状态
const systemStatus = reactive({
  cpu: 65,
  memory: 72,
  network: 45,
  connected: true,
});

// 新规则
const showRuleDialog = ref(false);
const newRule = reactive({
  name: '',
  metric: '',
  threshold: 50,
  notifyMethods: [],
});

// 计算属性
const filteredDataStream = computed(() => {
  if (filterType.value === 'all') return dataStream.value;
  return dataStream.value.filter(item => item.sentiment === filterType.value);
});

// 工具函数
const getSentimentType = (sentiment: string) => {
  const map: Record<string, any> = {
    positive: 'success',
    neutral: 'info',
    negative: 'danger',
  };
  return map[sentiment] || 'info';
};

const getSentimentLabel = (sentiment: string) => {
  const map: Record<string, string> = {
    positive: '正面',
    neutral: '中性',
    negative: '负面',
  };
  return map[sentiment] || '未知';
};

const getStatusColor = (value: number) => {
  if (value < 60) return SUCCESS;
  if (value < 80) return WARNING;
  return DANGER;
};

// 从后端API获取真实数据
const fetchRealtimeData = async (refresh = false) => {
  try {
    loading.value = true;
    const response = await apiClient.get('/monitor/stream', {
      params: { limit: 20, refresh: refresh ? 'true' : 'false' }
    });
    
    if (response.data.code === 200 && response.data.data) {
      const items = response.data.data.items || response.data.data || [];
      dataSource.value = response.data.data.source === 'realtime_weibo' ? '实时微博' : '数据库';
      
      dataStream.value = items.map((item: any) => ({
        id: item.id || item.weibo_id,
        time: item.time || item.created_at || new Date().toLocaleTimeString(),
        username: item.username || item.screen_name || item.user_name || '微博用户',
        avatar: item.avatar || 'https://tvax1.sinaimg.cn/default/images/default_avatar_male_180.gif',
        content: item.content || item.text || '',
        sentiment: item.sentiment || 'neutral',
        sentimentScore: item.sentiment_score || 0,
        source: item.source || '微博',
        location: item.location || '',
        keyword: item.keyword || '',
        views: item.views || 0,
        comments: item.comments || item.comments_count || 0,
        likes: item.likes || item.attitudes_count || 0,
      }));
      
      if (refresh) {
        ElMessage.success(`已刷新 ${dataStream.value.length} 条实时微博数据`);
      }
    }
  } catch (error: any) {
    console.error('获取实时数据失败:', error);
    // 失败时不显示错误，保持现有数据
  } finally {
    loading.value = false;
  }
};

// 事件处理
const refreshData = () => {
  fetchRealtimeData(true);
};

const handleTrigger = (trigger: any) => {
  ElMessage.info(`处理预警: ${trigger.rule}`);
};

const addRule = () => {
  ElMessage.success('规则添加成功');
  showRuleDialog.value = false;
};

// 关键词管理
const loadKeywords = async () => {
  loadingKeywords.value = true;
  try {
    const res = await apiClient.get('/monitor/keywords');
    if (res.data.code === 200) {
      monitorKeywords.value = res.data.data.keywords || [];
    }
  } catch (e) {
    // silent
  } finally {
    loadingKeywords.value = false;
  }
};

const addKeyword = async () => {
  const kw = newKeyword.value.trim();
  if (!kw) return;
  if (monitorKeywords.value.includes(kw)) {
    ElMessage.warning('关键词已存在');
    return;
  }
  const updated = [...monitorKeywords.value, kw];
  try {
    await apiClient.post('/monitor/keywords', { keywords: updated });
    monitorKeywords.value = updated;
    newKeyword.value = '';
    ElMessage.success(`已添加关键词: ${kw}`);
  } catch (e) {
    ElMessage.error('添加失败');
  }
};

const removeKeyword = async (kw: string) => {
  const updated = monitorKeywords.value.filter(k => k !== kw);
  try {
    await apiClient.post('/monitor/keywords', { keywords: updated });
    monitorKeywords.value = updated;
    ElMessage.success(`已移除关键词: ${kw}`);
  } catch (e) {
    ElMessage.error('移除失败');
  }
};

// 预警配置
const loadAlertConfig = async () => {
  try {
    const res = await apiClient.get('/monitor/alert-config');
    if (res.data.code === 200) {
      Object.assign(alertConfig, res.data.data);
    }
  } catch (e) {
    // silent
  }
};

const saveAlertConfig = async () => {
  savingConfig.value = true;
  try {
    await apiClient.post('/monitor/alert-config', alertConfig);
    ElMessage.success('预警配置已保存');
  } catch (e) {
    ElMessage.error('保存失败');
  } finally {
    savingConfig.value = false;
  }
};

// 关键词相关函数
const getKeywordDataCount = (keyword: string) => {
  return dataStream.value.filter(item => item.keyword === keyword).length;
};

const getKeywordDataStream = (keyword: string) => {
  return dataStream.value.filter(item => item.keyword === keyword);
};

const getKeywordSentimentCount = (keyword: string, sentiment: string) => {
  return dataStream.value.filter(item => 
    item.keyword === keyword && item.sentiment === sentiment
  ).length;
};

const getKeywordSentimentRatio = (keyword: string, sentiment: string) => {
  const keywordData = dataStream.value.filter(item => item.keyword === keyword);
  if (keywordData.length === 0) return 0;
  
  const sentimentCount = keywordData.filter(item => item.sentiment === sentiment).length;
  return Math.round((sentimentCount / keywordData.length) * 100);
};

// 加载预警记录
const loadAlertRecords = async () => {
  try {
    const res = await apiClient.get('/monitor/alerts');
    if (res.data.code === 200) {
      alertRecords.value = res.data.data.alerts || [];
    }
  } catch (e) {
    // silent
  }
};

// 自动滚动
let scrollInterval: any = null;

onMounted(() => {
  // 
  fetchRealtimeData();
  loadKeywords();
  loadAlertConfig();
  loadAlertRecords();
  
  // 
  connectSSE();
  
  // 
  scrollInterval = setInterval(() => {
    if (autoScroll.value) {
      fetchRealtimeData();
      nextTick(() => {
        if (scrollbarRef.value) {
          scrollbarRef.value.setScrollTop(0);
        }
      });
    }
  }, 30000);  // 30
});

onUnmounted(() => {
  if (scrollInterval) {
    clearInterval(scrollInterval);
  }
  
  // 
  disconnectSSE();
});

</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.realtime-monitor-module {
  height: calc(100vh - 120px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .status-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      
      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse 2s infinite;
        
        &.status-connected {
          background-color: #67c23a;
          box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.2);
        }
        
        &.status-reconnecting {
          background-color: #e6a23c;
          box-shadow: 0 0 0 2px rgba(230, 162, 60, 0.2);
          animation: pulse 1s infinite;
        }
        
        &.status-disconnected {
          background-color: #f56c6c;
          box-shadow: 0 0 0 2px rgba(245, 108, 108, 0.2);
          animation: none;
        }
      }
    }
  }
  
  span {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
  }
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.7;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.rotating-icon {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.monitor-layout {
  display: flex;
  gap: $spacing-sm;
  height: 100%;
}

.center-panel {
  flex: 1;
  overflow-y: auto;
  
  .dataflow-card {
    box-shadow: $box-shadow-base;
    
    .dataflow-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: $spacing-md;
      padding-bottom: $spacing-sm;
      border-bottom: 1px solid $border-lighter;
    }
    
    .data-timeline {
      padding: 0 $spacing-sm;
      
      .data-card {
        margin-bottom: $spacing-sm;
        border-left: 3px solid transparent;
        transition: $transition-fast;
        
        &.sentiment-positive {
          border-left-color: $success-color;
        }
        
        &.sentiment-negative {
          border-left-color: $danger-color;
        }
        
        &.sentiment-neutral {
          border-left-color: $info-color;
        }
        
        &:hover {
          box-shadow: $box-shadow-light;
        }
        
        .data-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: $spacing-xs;
          
          .user-info {
            display: flex;
            align-items: center;
            gap: $spacing-xs;
            
            .username {
              font-weight: $font-weight-medium;
              color: $text-primary;
            }
          }
          
          .data-meta {
            display: flex;
            gap: $spacing-sm;
            font-size: $font-size-small;
            color: $text-secondary;
          }
        }
        
        .data-content {
          margin-bottom: $spacing-sm;
          line-height: 1.6;
          color: $text-regular;
        }
        
        .data-stats {
          display: flex;
          gap: $spacing-md;
          font-size: $font-size-small;
          color: $text-secondary;
          
          span {
            display: flex;
            align-items: center;
            gap: 4px;
          }
        }
      }
    }
  }
}

.right-panel {
  width: 30%;
  overflow-y: auto;
  
  .keyword-card,
  .threshold-card,
  .alert-card,
  .trigger-card,
  .system-card {
    margin-bottom: $spacing-sm;
    box-shadow: $box-shadow-base;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  .keyword-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;

    .keyword-tag {
      margin: 0;
    }
  }

  .keyword-input {
    margin-top: 8px;
  }

  .alert-rules {
    max-height: 300px;
    overflow-y: auto;
    
    .rule-item {
      padding: $spacing-sm;
      margin-bottom: $spacing-xs;
      border: 1px solid $border-lighter;
      border-radius: $border-radius-base;
      opacity: 0.6;
      transition: $transition-fast;
      
      &.active {
        opacity: 1;
        border-color: $primary-color;
      }
      
      .rule-header {
        display: flex;
        align-items: center;
        gap: $spacing-xs;
        margin-bottom: 4px;
        
        .rule-name {
          font-weight: $font-weight-medium;
          color: $text-primary;
        }
      }
      
      .rule-condition {
        font-size: $font-size-small;
        color: $text-secondary;
        margin-bottom: 4px;
      }
    }
  }
  
  .trigger-content {
    .trigger-title {
      font-weight: $font-weight-medium;
      margin-bottom: 4px;
    }
    
    .trigger-desc {
      font-size: $font-size-small;
      color: $text-secondary;
      margin-bottom: 4px;
    }
  }
  
  .system-metrics {
    .metric-item {
      margin-bottom: $spacing-sm;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .metric-label {
        font-size: $font-size-small;
        color: $text-secondary;
        margin-bottom: 4px;
      }
    }
  }
}

// 响应式
@media (max-width: 1200px) {
  .monitor-layout {
    flex-direction: column;
  }
  
  .center-panel,
  .right-panel {
    width: 100%;
  }
}
</style>
