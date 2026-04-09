<template>
  <div class="spark-monitor">
    <el-card shadow="hover">
      <template #header>
        <div class="header">
          <span><el-icon><Cpu /></el-icon> Spark集群监控</span>
          <el-tag :type="sparkStatus === 'running' ? 'success' : 'danger'" size="small">
            {{ sparkStatus === 'running' ? '运行中' : '已停止' }}
          </el-tag>
        </div>
      </template>
      
      <el-row :gutter="16">
        <!-- 资源使用 -->
        <el-col :span="8">
          <div class="resource-card">
            <div class="resource-title">CPU使用率</div>
            <el-progress 
              type="dashboard" 
              :percentage="cpuUsage" 
              :color="getProgressColor(cpuUsage)"
              :width="100"
            />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="resource-card">
            <div class="resource-title">内存使用</div>
            <el-progress 
              type="dashboard" 
              :percentage="memoryUsage" 
              :color="getProgressColor(memoryUsage)"
              :width="100"
            >
              <template #default>
                <span class="progress-text">{{ usedMemory }}/{{ totalMemory }}GB</span>
              </template>
            </el-progress>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="resource-card">
            <div class="resource-title">存储使用</div>
            <el-progress 
              type="dashboard" 
              :percentage="storageUsage" 
              :color="getProgressColor(storageUsage)"
              :width="100"
            />
          </div>
        </el-col>
      </el-row>
      
      <el-divider />
      
      <!-- 作业统计 -->
      <el-row :gutter="16">
        <el-col :span="6" v-for="stat in jobStats" :key="stat.key">
          <div class="stat-item" :class="stat.key">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </el-col>
      </el-row>
      
      <el-divider />
      
      <!-- 性能指标 -->
      <div class="performance-metrics">
        <div class="metric-row">
          <span class="metric-label">吞吐量</span>
          <span class="metric-value">{{ throughput }} 条/秒</span>
        </div>
        <div class="metric-row">
          <span class="metric-label">平均延迟</span>
          <span class="metric-value">{{ latency }} ms</span>
        </div>
        <div class="metric-row">
          <span class="metric-label">Shuffle读取</span>
          <span class="metric-value">{{ shuffleRead }} MB</span>
        </div>
        <div class="metric-row">
          <span class="metric-label">Shuffle写入</span>
          <span class="metric-value">{{ shuffleWrite }} MB</span>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="actions">
        <el-button size="small" @click="openSparkUI">
          <el-icon><Link /></el-icon> Spark UI
        </el-button>
        <el-button size="small" @click="refreshMetrics" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { Cpu, Link, Refresh } from '@element-plus/icons-vue';

const sparkStatus = ref('running');
const loading = ref(false);

// 资源使用
const cpuUsage = ref(45);
const memoryUsage = ref(62);
const storageUsage = ref(38);
const usedMemory = ref(1.2);
const totalMemory = ref(2);

// 性能指标
const throughput = ref(3500);
const latency = ref(25);
const shuffleRead = ref(256);
const shuffleWrite = ref(189);

// 作业统计
const jobStats = ref([
  { key: 'total', label: '总作业数', value: 156 },
  { key: 'running', label: '运行中', value: 3 },
  { key: 'succeeded', label: '已完成', value: 148 },
  { key: 'failed', label: '失败', value: 5 },
]);

let refreshTimer: number | null = null;

const getProgressColor = (percentage: number) => {
  if (percentage < 60) return '#67C23A';
  if (percentage < 80) return '#E6A23C';
  return '#F56C6C';
};

const refreshMetrics = async () => {
  loading.value = true;
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500));
    
    cpuUsage.value = Math.floor(Math.random() * 60 + 20);
    memoryUsage.value = Math.floor(Math.random() * 40 + 40);
    storageUsage.value = Math.floor(Math.random() * 50 + 20);
    throughput.value = Math.floor(Math.random() * 3000 + 2000);
    latency.value = Math.floor(Math.random() * 30 + 10);
  } finally {
    loading.value = false;
  }
};

const openSparkUI = () => {
  window.open('http://localhost:4040', '_blank');
};

onMounted(() => {
  refreshTimer = window.setInterval(refreshMetrics, 10000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped lang="scss">
.spark-monitor {
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .resource-card {
    text-align: center;
    
    .resource-title {
      font-size: 14px;
      color: #606266;
      margin-bottom: 12px;
    }
    
    .progress-text {
      font-size: 12px;
      color: #606266;
    }
  }
  
  .stat-item {
    text-align: center;
    padding: 12px;
    border-radius: 8px;
    background: #f5f7fa;
    
    &.total { border-left: 3px solid #409EFF; }
    &.running { border-left: 3px solid #E6A23C; }
    &.succeeded { border-left: 3px solid #67C23A; }
    &.failed { border-left: 3px solid #F56C6C; }
    
    .stat-value {
      font-size: 24px;
      font-weight: bold;
      color: #303133;
    }
    
    .stat-label {
      font-size: 12px;
      color: #909399;
      margin-top: 4px;
    }
  }
  
  .performance-metrics {
    .metric-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #ebeef5;
      
      &:last-child {
        border-bottom: none;
      }
      
      .metric-label {
        color: #606266;
      }
      
      .metric-value {
        font-weight: 500;
        color: #303133;
      }
    }
  }
  
  .actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
  }
}
</style>
