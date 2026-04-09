<template>
  <el-card class="monitor-card">
    <template #header>
      <div class="card-header">
        <span>实时监控</span>
        <el-button
          :type="isMonitoring ? 'danger' : 'success'"
          size="small"
          @click="toggleMonitoring"
        >
          {{ isMonitoring ? '停止监控' : '开始监控' }}
        </el-button>
      </div>
    </template>
    
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-statistic title="已采集数据" :value="stats.collected">
          <template #prefix>
            <el-icon color="#67c23a"><DocumentCopy /></el-icon>
          </template>
          <template #suffix>条</template>
        </el-statistic>
      </el-col>
      
      <el-col :span="6">
        <el-statistic title="失败数" :value="stats.failed">
          <template #prefix>
            <el-icon color="#f56c6c"><CircleClose /></el-icon>
          </template>
          <template #suffix>条</template>
        </el-statistic>
      </el-col>
      
      <el-col :span="6">
        <el-statistic title="成功率" :value="stats.successRate" :precision="2">
          <template #prefix>
            <el-icon color="#409eff"><TrendCharts /></el-icon>
          </template>
          <template #suffix>%</template>
        </el-statistic>
      </el-col>
      
      <el-col :span="6">
        <el-statistic title="采集速度" :value="stats.speed">
          <template #prefix>
            <el-icon color="#e6a23c"><Timer /></el-icon>
          </template>
          <template #suffix>条/分</template>
        </el-statistic>
      </el-col>
    </el-row>
    
    <!-- 进度条 -->
    <div class="progress-section">
      <div class="progress-header">
        <span>采集进度</span>
        <span class="progress-text">{{ stats.collected }} / {{ stats.total }}</span>
      </div>
      <el-progress
        :percentage="progressPercentage"
        :stroke-width="20"
        :status="progressStatus"
      >
        <template #default="{ percentage }">
          <span class="percentage-text">{{ percentage }}%</span>
        </template>
      </el-progress>
    </div>
    
    <!-- 实时日志 -->
    <div class="log-section">
      <div class="log-header">
        <span>实时日志</span>
        <div class="log-actions">
          <el-switch
            v-model="autoScroll"
            active-text="自动滚动"
            size="small"
          />
          <el-button size="small" @click="clearLogs">清空日志</el-button>
        </div>
      </div>
      
      <el-scrollbar ref="scrollbarRef" class="log-scrollbar" :height="logHeight">
        <div class="log-content">
          <div
            v-for="(log, index) in logs"
            :key="index"
            :class="['log-item', `log-${log.level}`]"
          >
            <span class="log-time">{{ log.time }}</span>
            <el-tag :type="getLogType(log.level)" size="small">
              {{ log.level.toUpperCase() }}
            </el-tag>
            <span class="log-message">{{ log.message }}</span>
          </div>
          
          <div v-if="logs.length === 0" class="log-empty">
            暂无日志信息
          </div>
        </div>
      </el-scrollbar>
    </div>
    
    <!-- 数据预览 -->
    <div class="preview-section">
      <div class="preview-header">
        <span>最新采集数据预览</span>
        <el-button size="small" @click="refreshPreview">刷新</el-button>
      </div>
      
      <el-table :data="previewData" max-height="300">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="content" label="内容" min-width="300">
          <template #default="{ row }">
            <el-tooltip :content="row.content" placement="top">
              <div class="text-ellipsis">{{ row.content }}</div>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="采集时间" width="160" />
      </el-table>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import {
  DocumentCopy, CircleClose, TrendCharts, Timer,
} from '@element-plus/icons-vue';

const isMonitoring = ref(false);
const autoScroll = ref(true);
const scrollbarRef = ref();
const logHeight = ref('400px');

const stats = ref({
  collected: 0,
  failed: 0,
  total: 10000,
  speed: 0,
  successRate: 0,
});

const logs = ref<Array<{
  time: string;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
}>>([]);

const previewData = ref<Array<{
  id: string;
  content: string;
  source: string;
  time: string;
}>>([]);

let monitorTimer: number | null = null;
let logTimer: number | null = null;

const progressPercentage = computed(() => {
  if (stats.value.total === 0) return 0;
  return Math.min(100, Math.round((stats.value.collected / stats.value.total) * 100));
});

const progressStatus = computed(() => {
  if (progressPercentage.value === 100) return 'success';
  if (stats.value.failed > stats.value.collected * 0.1) return 'exception';
  return undefined;
});

const getLogType = (level: string) => {
  const types: Record<string, any> = {
    info: 'info',
    warn: 'warning',
    error: 'danger',
    success: 'success',
  };
  return types[level] || 'info';
};

const toggleMonitoring = () => {
  isMonitoring.value = !isMonitoring.value;
  
  if (isMonitoring.value) {
    startMonitoring();
  } else {
    stopMonitoring();
  }
};

const startMonitoring = () => {
  addLog('info', '开始监控数据采集任务');
  
  // 模拟数据采集
  monitorTimer = window.setInterval(() => {
    const increment = Math.floor(Math.random() * 50) + 10;
    stats.value.collected += increment;
    stats.value.failed += Math.floor(Math.random() * 3);
    stats.value.speed = Math.floor(Math.random() * 100) + 50;
    stats.value.successRate = ((stats.value.collected / (stats.value.collected + stats.value.failed)) * 100);
    
    if (stats.value.collected >= stats.value.total) {
      stats.value.collected = stats.value.total;
      stopMonitoring();
      addLog('success', '数据采集任务完成');
    }
  }, 2000);
  
  // 模拟日志生成
  logTimer = window.setInterval(() => {
    const messages = [
      '正在采集微博数据...',
      '成功获取用户信息',
      '正在解析评论数据',
      '数据保存成功',
      '检测到反爬限制，切换代理',
    ];
    const message = messages[Math.floor(Math.random() * messages.length)];
    addLog('info', message);
    
    // 随机添加一些警告和错误
    if (Math.random() > 0.9) {
      addLog('warn', '请求频率过高，降低采集速度');
    }
    if (Math.random() > 0.95) {
      addLog('error', '网络连接超时，正在重试...');
    }
  }, 3000);
  
  // 更新预览数据
  updatePreviewData();
};

const stopMonitoring = () => {
  isMonitoring.value = false;
  if (monitorTimer) {
    clearInterval(monitorTimer);
    monitorTimer = null;
  }
  if (logTimer) {
    clearInterval(logTimer);
    logTimer = null;
  }
  addLog('info', '停止监控');
};

const addLog = (level: 'info' | 'warn' | 'error' | 'success', message: string) => {
  const time = new Date().toLocaleTimeString();
  logs.value.push({ time, level, message });
  
  // 限制日志数量
  if (logs.value.length > 100) {
    logs.value.shift();
  }
  
  // 自动滚动到底部
  if (autoScroll.value) {
    nextTick(() => {
      scrollbarRef.value?.setScrollTop(9999);
    });
  }
};

const clearLogs = () => {
  logs.value = [];
};

const refreshPreview = () => {
  updatePreviewData();
};

const updatePreviewData = () => {
  const sources = ['微博', '微信', '抖音', '知乎'];
  const contents = [
    '今天天气真好，心情也很不错！',
    '这个产品质量太差了，非常失望...',
    '刚刚看了一部电影，剧情很精彩！',
    '周末准备去旅游，期待ing~',
    '工作压力好大，需要放松一下',
  ];
  
  previewData.value = Array.from({ length: 5 }, (_, i) => ({
    id: `${Date.now()}-${i}`,
    content: contents[Math.floor(Math.random() * contents.length)],
    source: sources[Math.floor(Math.random() * sources.length)],
    time: new Date().toLocaleString(),
  }));
};

onMounted(() => {
  // 初始化一些日志
  addLog('info', '监控系统已就绪');
});

onUnmounted(() => {
  stopMonitoring();
});
</script>

<style scoped lang="scss">
.monitor-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-row {
  margin-bottom: 24px;
}

.progress-section {
  margin-bottom: 24px;
  
  .progress-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    font-size: 14px;
    color: #606266;
    
    .progress-text {
      font-weight: bold;
      color: #409eff;
    }
  }
  
  .percentage-text {
    font-size: 14px;
    font-weight: bold;
  }
}

.log-section {
  margin-bottom: 24px;
  
  .log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .log-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }
  
  .log-scrollbar {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
  }
  
  .log-content {
    padding: 12px;
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
  }
  
  .log-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    line-height: 1.6;
    
    .log-time {
      color: #909399;
      flex-shrink: 0;
    }
    
    .log-message {
      flex: 1;
    }
  }
  
  .log-empty {
    text-align: center;
    color: #909399;
    padding: 40px 0;
  }
}

.preview-section {
  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
