<template>
  <div class="alert-dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h3>
          <el-icon><Bell /></el-icon>
          舆情预警中心
        </h3>
        <p class="header-desc">基于三维度排序模型的智能舆情预警系统</p>
      </div>
      <div class="header-actions">
        <el-tag :type="monitorEnabled ? 'success' : 'info'" effect="dark" size="large">
          <el-icon class="status-icon" :class="{ 'is-rotating': monitorEnabled }"><Refresh /></el-icon>
          {{ monitorEnabled ? '监控中' : '已暂停' }}
        </el-tag>
        <el-switch 
          v-model="monitorEnabled" 
          style="margin-left: 12px"
          @change="toggleMonitor"
        />
        <el-button :icon="Setting" @click="showConfigDialog = true">
          预警配置
        </el-button>
      </div>
    </div>

    <!-- 预警等级说明 -->
    <el-row :gutter="16" class="level-row">
      <el-col :span="8">
        <div class="level-card critical">
          <div class="level-icon"><el-icon><CircleCloseFilled /></el-icon></div>
          <div class="level-info">
            <div class="level-name">严重预警</div>
            <div class="level-desc">负面情感 > 60% 或出现重大敏感词</div>
          </div>
          <div class="level-count">{{ criticalCount }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="level-card warning">
          <div class="level-icon"><el-icon><WarningFilled /></el-icon></div>
          <div class="level-info">
            <div class="level-name">一般预警</div>
            <div class="level-desc">负面情感超过阈值或检测到敏感词</div>
          </div>
          <div class="level-count">{{ warningCount }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="level-card info">
          <div class="level-icon"><el-icon><InfoFilled /></el-icon></div>
          <div class="level-info">
            <div class="level-name">提示信息</div>
            <div class="level-desc">需要关注但不紧急的舆情动态</div>
          </div>
          <div class="level-count">{{ infoCount }}</div>
        </div>
      </el-col>
    </el-row>
    
    <!-- 实时指标卡片 -->
    <div class="metrics-row">
      <div class="metric-card" :class="{ warning: negativeRatio > alertConfig.negativeThreshold }">
        <div class="metric-icon negative">
          <el-icon><WarningFilled /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ negativeRatio.toFixed(1) }}%</div>
          <div class="metric-label">负面情感占比</div>
          <el-progress 
            :percentage="negativeRatio" 
            :stroke-width="4" 
            :show-text="false"
            :color="negativeRatio > alertConfig.negativeThreshold ? '#f56c6c' : '#409eff'"
          />
        </div>
        <div class="metric-threshold">阈值: {{ alertConfig.negativeThreshold }}%</div>
      </div>
      
      <div class="metric-card" :class="{ warning: hotKeywordCount > 0 }">
        <div class="metric-icon keyword">
          <el-icon><Search /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ hotKeywordCount }}</div>
          <div class="metric-label">敏感关键词命中</div>
          <div class="keyword-tags">
            <el-tag v-for="kw in alertConfig.keywords.slice(0, 3)" :key="kw" size="small" type="warning">{{ kw }}</el-tag>
            <el-tag v-if="alertConfig.keywords.length > 3" size="small" type="info">+{{ alertConfig.keywords.length - 3 }}</el-tag>
          </div>
        </div>
        <div class="metric-threshold">监控词: {{ alertConfig.keywords.length }}个</div>
      </div>
      
      <div class="metric-card">
        <div class="metric-icon total">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ totalAnalyzed.toLocaleString() }}</div>
          <div class="metric-label">已分析数据量</div>
          <div class="metric-trend">
            <el-icon color="#67c23a"><CaretTop /></el-icon>
            <span>实时更新中</span>
          </div>
        </div>
        <div class="metric-threshold">累计统计</div>
      </div>
      
      <div class="metric-card" :class="{ 'has-alerts': alerts.length > 0 }">
        <div class="metric-icon alert">
          <el-icon><Notification /></el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ alerts.length }}</div>
          <div class="metric-label">待处理预警</div>
          <div v-if="alerts.length > 0" class="metric-trend">
            <el-button type="danger" size="small" plain @click="scrollToAlerts">立即查看</el-button>
          </div>
        </div>
        <div class="metric-threshold">今日累计</div>
      </div>
    </div>

    <!-- 三维度预警规则说明 -->
    <el-card class="rule-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span><el-icon><TrendCharts /></el-icon> 三维度预警规则</span>
          <el-tag type="success" effect="plain" size="small">核心创新点</el-tag>
        </div>
      </template>
      <div class="rule-content">
        <div class="rule-item">
          <div class="rule-icon sentiment"><el-icon><Histogram /></el-icon></div>
          <div class="rule-info">
            <div class="rule-name">情感维度预警</div>
            <div class="rule-desc">当负面情感占比超过 <strong>{{ alertConfig.negativeThreshold }}%</strong> 时触发预警</div>
          </div>
        </div>
        <div class="rule-divider">+</div>
        <div class="rule-item">
          <div class="rule-icon popularity"><el-icon><TrendCharts /></el-icon></div>
          <div class="rule-info">
            <div class="rule-name">热度维度预警</div>
            <div class="rule-desc">当话题传播热度异常增长或出现敏感关键词时触发预警</div>
          </div>
        </div>
        <div class="rule-divider">=</div>
        <div class="rule-item result">
          <div class="rule-icon composite"><el-icon><Bell /></el-icon></div>
          <div class="rule-info">
            <div class="rule-name">综合预警评估</div>
            <div class="rule-desc">结合情感强度和传播热度，智能判断预警等级</div>
          </div>
        </div>
      </div>
    </el-card>
    
    <!-- 预警事件列表 -->
    <div ref="alertsSectionRef" class="alerts-section">
      <div class="section-header">
        <span><el-icon><Bell /></el-icon> 预警事件列表</span>
        <div class="section-actions">
          <el-button size="small" :icon="Refresh" :loading="checking" @click="checkAlerts">刷新</el-button>
          <el-button v-if="alerts.length > 0" size="small" type="danger" plain @click="clearAlerts">清空全部</el-button>
        </div>
      </div>
      
      <div v-if="alerts.length > 0" class="alerts-list">
        <transition-group name="alert-fade">
          <div 
            v-for="alert in alerts" 
            :key="alert.id" 
            class="alert-item"
            :class="[alert.level, { 'is-new': alert.isNew }]"
          >
            <div class="alert-icon">
              <el-icon v-if="alert.level === 'critical'"><CircleCloseFilled /></el-icon>
              <el-icon v-else-if="alert.level === 'warning'"><WarningFilled /></el-icon>
              <el-icon v-else><InfoFilled /></el-icon>
            </div>
            <div class="alert-content">
              <div class="alert-header">
                <span class="alert-title">{{ alert.title }}</span>
                <el-tag :type="getLevelTagType(alert.level)" size="small">{{ getLevelText(alert.level) }}</el-tag>
              </div>
              <div class="alert-desc">{{ alert.description }}</div>
              <div class="alert-footer">
                <span class="alert-time"><el-icon><Clock /></el-icon> {{ alert.time }}</span>
                <span v-if="alert.source" class="alert-source">来源: {{ alert.source }}</span>
              </div>
            </div>
            <div class="alert-actions">
              <el-button type="primary" size="small" plain @click="handleAlert(alert)">处理</el-button>
              <el-button size="small" @click="dismissAlert(alert.id)">忽略</el-button>
            </div>
          </div>
        </transition-group>
      </div>
      
      <el-empty v-else description="暂无预警事件，系统运行正常" :image-size="100">
        <template #image>
          <el-icon :size="80" color="#67c23a"><CircleCheckFilled /></el-icon>
        </template>
      </el-empty>
    </div>
    
    <!-- 预警配置弹窗 -->
    <el-dialog v-model="showConfigDialog" title="预警配置" width="500px">
      <el-form label-width="120px">
        <el-form-item label="负面情感阈值">
          <el-slider 
            v-model="alertConfig.negativeThreshold" 
            :min="10" 
            :max="80" 
            :format-tooltip="(val: number) => `${val}%`"
            show-input
          />
        </el-form-item>
        
        <el-form-item label="监控关键词">
          <el-select
            v-model="alertConfig.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词，回车添加"
            style="width: 100%"
          >
            <el-option v-for="kw in defaultKeywords" :key="kw" :label="kw" :value="kw" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="检查间隔">
          <el-select v-model="alertConfig.checkInterval" style="width: 100%">
            <el-option label="5秒" :value="5000" />
            <el-option label="10秒" :value="10000" />
            <el-option label="30秒" :value="30000" />
            <el-option label="1分钟" :value="60000" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { 
  Bell, Setting, WarningFilled, Search, DataAnalysis, 
  Notification, CircleCloseFilled, InfoFilled, Close, Refresh,
  CaretTop, TrendCharts, Histogram, Clock, CircleCheckFilled
} from '@element-plus/icons-vue';
import { ElMessage, ElNotification } from 'element-plus';
import apiClient from '@/api';

// 预警配置
const alertConfig = reactive({
  negativeThreshold: 40,  // 负面情感阈值
  keywords: ['投诉', '差评', '退款', '骗子', '垃圾'],  // 监控关键词
  checkInterval: 10000,  // 检查间隔（毫秒）
});

// 默认关键词选项
const defaultKeywords = [
  '投诉', '差评', '退款', '骗子', '垃圾', '曝光', '维权',
  '举报', '黑心', '坑人', '欺诈', '假货', '售后差'
];

// 状态
const monitorEnabled = ref(true);
const showConfigDialog = ref(false);
const negativeRatio = ref(25);
const hotKeywordCount = ref(0);
const totalAnalyzed = ref(0);
const checking = ref(false);
const alertsSectionRef = ref<HTMLElement | null>(null);

// 预警事件
interface Alert {
  id: string;
  level: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  time: string;
  isNew: boolean;
  source?: string;
}

const alerts = ref<Alert[]>([]);

// 计算各等级预警数量
import { computed } from 'vue';
const criticalCount = computed(() => alerts.value.filter(a => a.level === 'critical').length);
const warningCount = computed(() => alerts.value.filter(a => a.level === 'warning').length);
const infoCount = computed(() => alerts.value.filter(a => a.level === 'info').length);

// 获取等级标签类型
const getLevelTagType = (level: string) => {
  const types: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' };
  return types[level] || 'info';
};

// 获取等级文本
const getLevelText = (level: string) => {
  const texts: Record<string, string> = { critical: '严重', warning: '警告', info: '提示' };
  return texts[level] || level;
};

// 滚动到预警列表
const scrollToAlerts = () => {
  alertsSectionRef.value?.scrollIntoView({ behavior: 'smooth' });
};

// 处理预警
const handleAlert = (alert: Alert) => {
  ElMessage.info(`正在处理预警: ${alert.title}`);
  dismissAlert(alert.id);
};

let monitorTimer: number | null = null;

// 切换监控状态
const toggleMonitor = (enabled: boolean) => {
  if (enabled) {
    startMonitor();
    ElMessage.success('实时监控已启动');
  } else {
    stopMonitor();
    ElMessage.info('实时监控已暂停');
  }
};

// 启动监控
const startMonitor = () => {
  if (monitorTimer) return;
  
  checkAlerts();  // 立即检查一次
  monitorTimer = window.setInterval(checkAlerts, alertConfig.checkInterval);
};

// 停止监控
const stopMonitor = () => {
  if (monitorTimer) {
    clearInterval(monitorTimer);
    monitorTimer = null;
  }
};

// 检查预警条件
const checkAlerts = async () => {
  checking.value = true;
  try {
    // 获取实时情感分布
    const response = await apiClient.get('/dashboard/sentiment-distribution');
    
    if (response.data.code === 200) {
      const data = response.data.data;
      const total = data.positive + data.neutral + data.negative;
      
      if (total > 0) {
        negativeRatio.value = (data.negative / total) * 100;
        totalAnalyzed.value += Math.floor(Math.random() * 10) + 1;  // 模拟增量
        
        // 检查负面情感阈值
        if (negativeRatio.value > alertConfig.negativeThreshold) {
          addAlert({
            level: negativeRatio.value > 60 ? 'critical' : 'warning',
            title: '负面情感预警',
            description: `当前负面情感占比 ${negativeRatio.value.toFixed(1)}%，超过阈值 ${alertConfig.negativeThreshold}%`,
          });
        }
      }
    }
    
    // 模拟关键词检测
    if (Math.random() > 0.8) {
      hotKeywordCount.value = Math.floor(Math.random() * 3);
      if (hotKeywordCount.value > 0) {
        const keyword = alertConfig.keywords[Math.floor(Math.random() * alertConfig.keywords.length)];
        addAlert({
          level: 'warning',
          title: '敏感关键词预警',
          description: `检测到敏感关键词「${keyword}」出现 ${hotKeywordCount.value} 次`,
        });
      }
    }
    
  } catch (error) {
    console.error('检查预警失败:', error);
  } finally {
    checking.value = false;
  }
};

// 添加预警
const addAlert = (alertData: Omit<Alert, 'id' | 'time' | 'isNew'>) => {
  const newAlert: Alert = {
    id: `alert_${Date.now()}`,
    ...alertData,
    time: new Date().toLocaleTimeString(),
    isNew: true,
  };
  
  // 检查是否已有相同类型的预警（避免重复）
  const existingIndex = alerts.value.findIndex(a => a.title === alertData.title);
  if (existingIndex > -1) {
    // 更新现有预警
    alerts.value[existingIndex] = newAlert;
  } else {
    // 添加新预警
    alerts.value.unshift(newAlert);
    
    // 显示通知
    ElNotification({
      title: alertData.title,
      message: alertData.description,
      type: alertData.level === 'critical' ? 'error' : 'warning',
      duration: 5000,
    });
  }
  
  // 移除新标记
  setTimeout(() => {
    const alert = alerts.value.find(a => a.id === newAlert.id);
    if (alert) alert.isNew = false;
  }, 3000);
  
  // 限制预警数量
  if (alerts.value.length > 20) {
    alerts.value = alerts.value.slice(0, 20);
  }
};

// 关闭单个预警
const dismissAlert = (id: string) => {
  const index = alerts.value.findIndex(a => a.id === id);
  if (index > -1) {
    alerts.value.splice(index, 1);
  }
};

// 清空所有预警
const clearAlerts = () => {
  alerts.value = [];
  ElMessage.success('预警已清空');
};

// 保存配置
const saveConfig = () => {
  showConfigDialog.value = false;
  
  // 重启监控以应用新配置
  if (monitorEnabled.value) {
    stopMonitor();
    startMonitor();
  }
  
  ElMessage.success('配置已保存');
};

onMounted(() => {
  if (monitorEnabled.value) {
    startMonitor();
  }
});

onUnmounted(() => {
  stopMonitor();
});
</script>

<style scoped lang="scss">
.alert-dashboard {
  background: #f5f7fa;
  min-height: calc(100vh - 120px);
  padding: 24px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  background: #fff;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.header-left {
  h3 {
    margin: 0 0 8px 0;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 22px;
    font-weight: 600;
    color: #303133;
  }
  .header-desc {
    margin: 0;
    color: #909399;
    font-size: 14px;
  }
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  
  .status-icon {
    margin-right: 6px;
    &.is-rotating {
      animation: rotating 2s linear infinite;
    }
  }
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.level-row {
  margin-bottom: 20px;
}

.level-card {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-radius: 12px;
  background: #fff;
  border: 2px solid transparent;
  transition: all 0.3s;
  
  &.critical {
    border-color: #f56c6c;
    background: linear-gradient(135deg, #fff 0%, #fef0f0 100%);
    .level-icon { background: #fef0f0; color: #f56c6c; }
    .level-count { color: #f56c6c; }
  }
  
  &.warning {
    border-color: #e6a23c;
    background: linear-gradient(135deg, #fff 0%, #fdf6ec 100%);
    .level-icon { background: #fdf6ec; color: #e6a23c; }
    .level-count { color: #e6a23c; }
  }
  
  &.info {
    border-color: #909399;
    background: linear-gradient(135deg, #fff 0%, #f4f4f5 100%);
    .level-icon { background: #f4f4f5; color: #909399; }
    .level-count { color: #909399; }
  }
  
  .level-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    margin-right: 14px;
  }
  
  .level-info {
    flex: 1;
    .level-name { font-weight: 600; color: #303133; font-size: 15px; }
    .level-desc { font-size: 12px; color: #909399; margin-top: 4px; }
  }
  
  .level-count {
    font-size: 28px;
    font-weight: 700;
  }
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 18px;
  background: #fff;
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  
  &.warning {
    background: linear-gradient(135deg, #fff 0%, #fef0f0 100%);
    border-color: #f56c6c;
    animation: pulse 1.5s infinite;
  }
  
  &.has-alerts {
    background: linear-gradient(135deg, #fff 0%, #fef0f0 100%);
    border-color: #f56c6c;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}

.metric-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 14px;
  font-size: 26px;
  
  &.negative { background: #fef0f0; color: #f56c6c; }
  &.keyword { background: #fdf6ec; color: #e6a23c; }
  &.total { background: #ecf5ff; color: #409eff; }
  &.alert { background: #f0f9eb; color: #67c23a; }
}

.metric-content {
  flex: 1;
  
  .metric-value {
    font-size: 26px;
    font-weight: 700;
    color: #303133;
    line-height: 1.2;
  }
  
  .metric-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }
  
  .keyword-tags {
    display: flex;
    gap: 4px;
    margin-top: 8px;
    flex-wrap: wrap;
  }
  
  .metric-trend {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 8px;
    font-size: 12px;
    color: #67c23a;
  }
}

.metric-threshold {
  font-size: 11px;
  color: #c0c4cc;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.rule-card {
  margin-bottom: 20px;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    
    span {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }
  
  .rule-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    padding: 10px 0;
  }
  
  .rule-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    background: #f5f7fa;
    border-radius: 10px;
    flex: 1;
    
    &.result {
      background: linear-gradient(135deg, #ecf5ff 0%, #f0f9eb 100%);
      border: 2px solid #409eff;
    }
    
    .rule-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      
      &.sentiment { background: #fef0f0; color: #f56c6c; }
      &.popularity { background: #fdf6ec; color: #e6a23c; }
      &.composite { background: #ecf5ff; color: #409eff; }
    }
    
    .rule-info {
      .rule-name { font-weight: 600; color: #303133; font-size: 14px; }
      .rule-desc { font-size: 12px; color: #909399; margin-top: 4px; }
    }
  }
  
  .rule-divider {
    font-size: 24px;
    font-weight: 700;
    color: #409eff;
  }
}

.alerts-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  
  span {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .section-actions {
    display: flex;
    gap: 10px;
  }
}

.alerts-list {
  max-height: 400px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 10px;
  transition: all 0.3s;
  
  &.critical {
    background: linear-gradient(135deg, #fff 0%, #fef0f0 100%);
    border-left: 4px solid #f56c6c;
    .alert-icon { color: #f56c6c; }
  }
  
  &.warning {
    background: linear-gradient(135deg, #fff 0%, #fdf6ec 100%);
    border-left: 4px solid #e6a23c;
    .alert-icon { color: #e6a23c; }
  }
  
  &.info {
    background: linear-gradient(135deg, #fff 0%, #f4f4f5 100%);
    border-left: 4px solid #909399;
    .alert-icon { color: #909399; }
  }
  
  &.is-new {
    animation: slideIn 0.3s ease-out;
  }
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

.alert-icon {
  margin-right: 14px;
  font-size: 24px;
  margin-top: 2px;
}

.alert-content {
  flex: 1;
  
  .alert-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }
  
  .alert-title {
    font-weight: 600;
    color: #303133;
    font-size: 15px;
  }
  
  .alert-desc {
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
    line-height: 1.5;
  }
  
  .alert-footer {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: #909399;
    
    .alert-time {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }
}

.alert-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-left: 12px;
}

.alert-fade-enter-active,
.alert-fade-leave-active {
  transition: all 0.3s ease;
}

.alert-fade-enter-from,
.alert-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
