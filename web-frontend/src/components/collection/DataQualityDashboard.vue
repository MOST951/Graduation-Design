<template>
  <div class="data-quality-dashboard">
    <!-- 质量状态概览 -->
    <div class="quality-header" :class="statusClass">
      <div class="status-icon">
        <el-icon v-if="summary.status === 'healthy'" :size="32"><CircleCheck /></el-icon>
        <el-icon v-else-if="summary.status === 'warning'" :size="32"><Warning /></el-icon>
        <el-icon v-else-if="summary.status === 'critical'" :size="32"><CircleClose /></el-icon>
        <el-icon v-else :size="32"><QuestionFilled /></el-icon>
      </div>
      <div class="status-info">
        <h3>数据质量状态</h3>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <div v-if="summary.generated_at" class="status-time">
        更新于: {{ formatTime(summary.generated_at) }}
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" circle @click="loadData" />
    </div>

    <!-- 核心指标卡片 -->
    <el-row :gutter="20" class="metrics-row">
      <el-col :span="6">
        <div class="metric-card success">
          <div class="metric-value">{{ summary.success_rate?.toFixed(1) || '--' }}%</div>
          <div class="metric-label">采集成功率</div>
          <div class="metric-threshold">阈值: {{ (thresholds.success_rate * 100).toFixed(0) }}%</div>
          <el-progress 
            :percentage="summary.success_rate || 0" 
            :stroke-width="6"
            :color="getProgressColor(summary.success_rate, thresholds.success_rate * 100, true)"
          />
        </div>
      </el-col>
      <el-col :span="6">
        <div class="metric-card warning">
          <div class="metric-value">{{ summary.duplicate_rate?.toFixed(1) || '--' }}%</div>
          <div class="metric-label">数据重复率</div>
          <div class="metric-threshold">阈值: {{ (thresholds.duplicate_rate * 100).toFixed(0) }}%</div>
          <el-progress 
            :percentage="summary.duplicate_rate || 0" 
            :stroke-width="6"
            :color="getProgressColor(summary.duplicate_rate, thresholds.duplicate_rate * 100, false)"
          />
        </div>
      </el-col>
      <el-col :span="6">
        <div class="metric-card info">
          <div class="metric-value">{{ summary.total_records || 0 }}</div>
          <div class="metric-label">总记录数</div>
          <div class="metric-sub">已验证数据</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="metric-card" :class="summary.alerts_count > 0 ? 'danger' : 'success'">
          <div class="metric-value">{{ summary.alerts_count || 0 }}</div>
          <div class="metric-label">当前报警</div>
          <div class="metric-sub">{{ summary.alerts_count > 0 ? '需要关注' : '一切正常' }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 报警列表 -->
    <el-card v-if="alerts.length > 0" class="alerts-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><el-icon><Bell /></el-icon> 质量报警</span>
          <el-tag :type="getAlertSeverityType(maxSeverity)" size="small">
            {{ alerts.length }} 条报警
          </el-tag>
        </div>
      </template>
      <div class="alerts-list">
        <div 
          v-for="(alert, index) in alerts" 
          :key="index" 
          class="alert-item"
          :class="alert.severity"
        >
          <el-icon class="alert-icon">
            <WarningFilled v-if="alert.severity === 'critical'" />
            <Warning v-else-if="alert.severity === 'high'" />
            <InfoFilled v-else />
          </el-icon>
          <div class="alert-content">
            <div class="alert-message">{{ alert.message }}</div>
            <div class="alert-meta">
              <span>指标: {{ alert.metric_name }}</span>
              <span>当前值: {{ (alert.current_value * 100).toFixed(1) }}%</span>
              <span>阈值: {{ (alert.threshold * 100).toFixed(1) }}%</span>
            </div>
          </div>
          <el-tag :type="getAlertSeverityType(alert.severity)" size="small">
            {{ getSeverityLabel(alert.severity) }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <!-- 字段完整率 -->
    <el-card v-if="latestReport" class="completeness-card" shadow="hover">
      <template #header>
        <span><el-icon><Document /></el-icon> 字段完整率</span>
      </template>
      <div class="completeness-grid">
        <div 
          v-for="(value, field) in latestReport.metrics.field_completeness" 
          :key="field"
          class="completeness-item"
        >
          <div class="field-name">{{ field }}</div>
          <el-progress 
            :percentage="value" 
            :stroke-width="10"
            :color="getCompletenessColor(value)"
          />
        </div>
      </div>
    </el-card>

    <!-- 错误统计和日志 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="errors-card" shadow="hover">
          <template #header>
            <span><el-icon><PieChart /></el-icon> 错误类型分布</span>
          </template>
          <div v-if="latestReport && Object.keys(latestReport.metrics.error_counts).length > 0">
            <div 
              v-for="(count, type) in latestReport.metrics.error_counts" 
              :key="type"
              class="error-type-item"
            >
              <span class="error-type">{{ getErrorTypeLabel(type) }}</span>
              <el-progress 
                :percentage="getErrorPercentage(count)" 
                :format="() => count + '次'"
                :stroke-width="12"
                color="#F56C6C"
              />
            </div>
          </div>
          <el-empty v-else description="暂无错误记录" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="log-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><List /></el-icon> 最近错误日志</span>
              <el-button text size="small" @click="showAllErrors = true">查看全部</el-button>
            </div>
          </template>
          <div class="error-log-list">
            <div 
              v-for="(log, index) in recentErrors.slice(0, 5)" 
              :key="index"
              class="error-log-item"
            >
              <div class="log-time">{{ formatTime(log.timestamp) }}</div>
              <div class="log-preview">{{ log.data_preview || '无预览' }}</div>
              <div class="log-errors">
                <el-tag 
                  v-for="(err, i) in log.errors.slice(0, 2)" 
                  :key="i" 
                  type="danger" 
                  size="small"
                >
                  {{ err.error_type }}
                </el-tag>
              </div>
            </div>
            <el-empty v-if="recentErrors.length === 0" description="暂无错误日志" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 改进建议 -->
    <el-card v-if="latestReport?.recommendations?.length" class="recommendations-card" shadow="hover">
      <template #header>
        <span><el-icon><Opportunity /></el-icon> 改进建议</span>
      </template>
      <ul class="recommendations-list">
        <li v-for="(rec, index) in latestReport.recommendations" :key="index">
          {{ rec }}
        </li>
      </ul>
    </el-card>

    <!-- 错误日志详情对话框 -->
    <el-dialog v-model="showAllErrors" title="错误日志详情" width="800px">
      <el-table :data="recentErrors" max-height="400">
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
        </el-table-column>
        <el-table-column prop="data_id" label="数据ID" width="120" />
        <el-table-column prop="data_preview" label="数据预览" show-overflow-tooltip />
        <el-table-column label="错误" width="200">
          <template #default="{ row }">
            <el-tag 
              v-for="(err, i) in row.errors" 
              :key="i" 
              type="danger" 
              size="small"
              style="margin: 2px;"
            >
              {{ err.field_name }}: {{ err.error_type }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { 
  CircleCheck, CircleClose, Warning, QuestionFilled, Refresh, Bell,
  WarningFilled, InfoFilled, Document, PieChart, List, Opportunity
} from '@element-plus/icons-vue';
import { 
  getDataQuality, getQualityAlerts,
  type DataQualitySummary, type QualityAlert, type QualityReport, type ErrorLogEntry
} from '@/api/weibo';

// 状态
const loading = ref(false);
const summary = ref<DataQualitySummary>({
  status: 'no_data',
  message: '暂无数据'
});
const alerts = ref<QualityAlert[]>([]);
const recentErrors = ref<ErrorLogEntry[]>([]);
const thresholds = ref<Record<string, number>>({
  success_rate: 0.8,
  duplicate_rate: 0.3,
  field_completeness: 0.7,
});
const latestReport = ref<QualityReport | null>(null);
const showAllErrors = ref(false);

// 计算属性
const statusClass = computed(() => {
  switch (summary.value.status) {
    case 'healthy': return 'status-healthy';
    case 'warning': return 'status-warning';
    case 'critical': return 'status-critical';
    default: return 'status-unknown';
  }
});

const statusText = computed(() => {
  switch (summary.value.status) {
    case 'healthy': return '数据质量良好';
    case 'warning': return '存在质量问题';
    case 'critical': return '质量严重异常';
    case 'no_data': return '暂无质量数据';
    default: return '状态未知';
  }
});

const maxSeverity = computed(() => {
  if (alerts.value.some(a => a.severity === 'critical')) return 'critical';
  if (alerts.value.some(a => a.severity === 'high')) return 'high';
  if (alerts.value.some(a => a.severity === 'medium')) return 'medium';
  return 'low';
});

// 方法
const loadData = async () => {
  loading.value = true;
  try {
    const data = await getDataQuality();
    summary.value = data.summary;
    recentErrors.value = data.recent_errors;
    thresholds.value = data.thresholds;
    
    if (data.recent_reports.length > 0) {
      latestReport.value = data.recent_reports[data.recent_reports.length - 1];
      alerts.value = latestReport.value?.alerts || [];
    }
  } catch (error) {
    console.error('加载数据质量失败:', error);
  } finally {
    loading.value = false;
  }
};

const formatTime = (time: string) => {
  if (!time) return '--';
  const date = new Date(time);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getProgressColor = (value: number | undefined, threshold: number, higherIsBetter: boolean) => {
  if (value === undefined) return '#909399';
  if (higherIsBetter) {
    return value >= threshold ? '#67C23A' : value >= threshold * 0.8 ? '#E6A23C' : '#F56C6C';
  } else {
    return value <= threshold ? '#67C23A' : value <= threshold * 1.5 ? '#E6A23C' : '#F56C6C';
  }
};

const getCompletenessColor = (value: number) => {
  if (value >= 90) return '#67C23A';
  if (value >= 70) return '#E6A23C';
  return '#F56C6C';
};

const getAlertSeverityType = (severity: string) => {
  switch (severity) {
    case 'critical': return 'danger';
    case 'high': return 'warning';
    case 'medium': return 'info';
    default: return 'info';
  }
};

const getSeverityLabel = (severity: string) => {
  switch (severity) {
    case 'critical': return '严重';
    case 'high': return '高';
    case 'medium': return '中';
    default: return '低';
  }
};

const getErrorTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    required: '必填字段缺失',
    type: '类型错误',
    min_value: '值过小',
    max_value: '值过大',
    min_length: '长度过短',
    max_length: '长度过长',
    pattern: '格式不匹配',
    future_timestamp: '未来时间戳',
    custom: '自定义验证失败',
  };
  return labels[type] || type;
};

const getErrorPercentage = (count: number) => {
  if (!latestReport.value) return 0;
  const total = Object.values(latestReport.value.metrics.error_counts).reduce((a, b) => a + b, 0);
  return total > 0 ? Math.round((count / total) * 100) : 0;
};

onMounted(() => {
  loadData();
});
</script>

<style scoped lang="scss">
.data-quality-dashboard {
  padding: 20px;
}

.quality-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  color: #fff;
  
  &.status-healthy {
    background: linear-gradient(135deg, #67C23A 0%, #5daf34 100%);
  }
  
  &.status-warning {
    background: linear-gradient(135deg, #E6A23C 0%, #d4912e 100%);
  }
  
  &.status-critical {
    background: linear-gradient(135deg, #F56C6C 0%, #e45656 100%);
  }
  
  &.status-unknown {
    background: linear-gradient(135deg, #909399 0%, #7d8187 100%);
  }
  
  .status-icon {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    padding: 12px;
  }
  
  .status-info {
    flex: 1;
    
    h3 {
      margin: 0 0 5px 0;
      font-size: 18px;
    }
    
    .status-text {
      font-size: 14px;
      opacity: 0.9;
    }
  }
  
  .status-time {
    font-size: 12px;
    opacity: 0.8;
  }
}

.metrics-row {
  margin-bottom: 20px;
}

.metric-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border-left: 4px solid;
  
  &.success { border-color: #67C23A; }
  &.warning { border-color: #E6A23C; }
  &.danger { border-color: #F56C6C; }
  &.info { border-color: #409EFF; }
  
  .metric-value {
    font-size: 32px;
    font-weight: bold;
    color: #303133;
  }
  
  .metric-label {
    font-size: 14px;
    color: #606266;
    margin: 8px 0;
  }
  
  .metric-threshold, .metric-sub {
    font-size: 12px;
    color: #909399;
    margin-bottom: 10px;
  }
}

.alerts-card {
  margin-bottom: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.alerts-list {
  .alert-item {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 10px;
    
    &.critical { background: #fef0f0; }
    &.high { background: #fdf6ec; }
    &.medium { background: #f4f4f5; }
    &.low { background: #f0f9eb; }
    
    .alert-icon {
      font-size: 24px;
    }
    
    &.critical .alert-icon { color: #F56C6C; }
    &.high .alert-icon { color: #E6A23C; }
    
    .alert-content {
      flex: 1;
      
      .alert-message {
        font-weight: 500;
        margin-bottom: 5px;
      }
      
      .alert-meta {
        font-size: 12px;
        color: #909399;
        
        span {
          margin-right: 15px;
        }
      }
    }
  }
}

.completeness-card, .errors-card, .log-card, .recommendations-card {
  margin-bottom: 20px;
}

.completeness-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  
  .completeness-item {
    .field-name {
      font-size: 13px;
      color: #606266;
      margin-bottom: 8px;
    }
  }
}

.error-type-item {
  margin-bottom: 15px;
  
  .error-type {
    font-size: 13px;
    color: #606266;
    display: block;
    margin-bottom: 5px;
  }
}

.error-log-list {
  .error-log-item {
    padding: 10px;
    border-bottom: 1px solid #ebeef5;
    
    &:last-child {
      border-bottom: none;
    }
    
    .log-time {
      font-size: 12px;
      color: #909399;
    }
    
    .log-preview {
      font-size: 13px;
      color: #606266;
      margin: 5px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    
    .log-errors {
      .el-tag {
        margin-right: 5px;
      }
    }
  }
}

.recommendations-list {
  margin: 0;
  padding-left: 20px;
  
  li {
    padding: 8px 0;
    color: #606266;
    line-height: 1.6;
  }
}
</style>
