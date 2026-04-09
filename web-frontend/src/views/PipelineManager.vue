<template>
  <div class="pipeline-module">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2><el-icon><Connection /></el-icon> 数据流水线管理</h2>
        <p class="subtitle">全流程执行：采集 → 清洗 → 情感分析 → 双维度排序 → 入库</p>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="VideoPlay" @click="runPipeline('sync')" :loading="running" :disabled="running">
          同步执行
        </el-button>
        <el-button type="success" :icon="VideoPlay" @click="runPipeline('async')" :loading="running" :disabled="running">
          异步执行
        </el-button>
        <el-button :icon="Refresh" @click="refreshStatus" :loading="refreshing">刷新状态</el-button>
      </div>
    </div>

    <!-- 流水线阶段可视化 -->
    <el-card class="pipeline-visual-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span><el-icon><Connection /></el-icon> 流水线阶段</span>
          <el-tag v-if="pipelineStatus.running" type="success" effect="dark">
            <el-icon class="rotating"><Loading /></el-icon> 运行中
          </el-tag>
          <el-tag v-else-if="lastResult" type="info">已完成</el-tag>
          <el-tag v-else type="warning">空闲</el-tag>
        </div>
      </template>
      <div class="pipeline-stages">
        <div v-for="(stage, idx) in stages" :key="stage.key" class="stage-item" :class="stage.status">
          <div class="stage-icon-wrapper">
            <el-icon v-if="stage.status === 'completed'" :color="SUCCESS" :size="28"><CircleCheck /></el-icon>
            <el-icon v-else-if="stage.status === 'running'" class="rotating" :color="PRIMARY" :size="28"><Loading /></el-icon>
            <el-icon v-else-if="stage.status === 'failed'" :color="DANGER" :size="28"><CircleClose /></el-icon>
            <el-icon v-else :color="INFO" :size="28"><component :is="stage.icon" /></el-icon>
          </div>
          <div class="stage-label">{{ stage.name }}</div>
          <div class="stage-detail" v-if="stage.count !== undefined && stage.count > 0">
            {{ stage.count }} 条
          </div>
          <div class="stage-detail" v-if="stage.time">{{ stage.time }}ms</div>
          <div class="stage-arrow" v-if="idx < stages.length - 1">
            <el-icon><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 参数配置 + 状态信息 -->
    <el-row :gutter="20" style="margin-top: 16px">
      <!-- 参数配置 -->
      <el-col :span="8">
        <el-card header="执行参数" shadow="hover" class="config-card">
          <el-form label-position="top" size="default">
            <el-form-item label="最大处理条数">
              <el-input-number v-model="pipelineConfig.limit" :min="10" :max="5000" :step="50" style="width: 100%" />
            </el-form-item>
            <el-form-item label="关键词预设">
              <el-select v-model="pipelineConfig.preset" placeholder="选择预设" style="width: 100%">
                <el-option label="默认配置" value="default" />
                <el-option label="情感优先" value="sentiment_first" />
                <el-option label="热度优先" value="heat_first" />
              </el-select>
            </el-form-item>
            <el-form-item label="断点续跑">
              <el-switch v-model="pipelineConfig.resume" active-text="启用" inactive-text="禁用" />
              <div class="form-tip">某阶段失败后，从该阶段重试</div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 数据库统计 -->
        <el-card header="数据库统计" shadow="hover" class="config-card" style="margin-top: 16px">
          <div class="db-stats" v-loading="loadingStats">
            <div class="db-stat-row" v-for="item in dbStats" :key="item.table">
              <span class="stat-table">{{ item.label }}</span>
              <el-tag :type="item.count > 0 ? 'success' : 'info'" size="small">{{ item.count }} 条</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 运行状态 -->
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><DataLine /></el-icon> 当前状态</span>
            </div>
          </template>
          <el-descriptions :column="2" border size="default">
            <el-descriptions-item label="运行状态">
              <el-tag :type="pipelineStatus.running ? 'success' : 'info'">
                {{ pipelineStatus.running ? '运行中' : '空闲' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="当前阶段">
              {{ pipelineStatus.current_stage || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="已处理条数">
              {{ pipelineStatus.processed_count ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="总耗时">
              {{ pipelineStatus.total_time ? pipelineStatus.total_time + 'ms' : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="BERT可用">
              <el-tag :type="pipelineStatus.bert_available ? 'success' : 'warning'" size="small">
                {{ pipelineStatus.bert_available ? '是' : '否（仅词典）' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="批次ID">
              <span class="batch-id">{{ pipelineStatus.batch_id || '-' }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 最新排序结果 -->
        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span><el-icon><Histogram /></el-icon> 最新双维度排序结果 TOP20</span>
              <el-button size="small" :icon="Refresh" @click="loadRanking" :loading="loadingRanking">刷新</el-button>
            </div>
          </template>
          <el-table :data="rankingData" v-loading="loadingRanking" stripe size="small" max-height="400">
            <el-table-column label="排名" width="60" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.ranking_position <= 3" type="danger" size="small" effect="dark">{{ row.ranking_position }}</el-tag>
                <span v-else>{{ row.ranking_position }}</span>
              </template>
            </el-table-column>
            <el-table-column label="微博内容" min-width="250" show-overflow-tooltip>
              <template #default="{ row }">
                <span>{{ row.content || row.weibo_id }}</span>
              </template>
            </el-table-column>
            <el-table-column label="综合得分" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="primary">{{ (row.composite_score ?? row.final_score ?? 0).toFixed(3) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="情感强度" width="90" align="center">
              <template #default="{ row }">
                {{ (row.sentiment_intensity ?? 0).toFixed(3) }}
              </template>
            </el-table-column>
            <el-table-column label="热度" width="90" align="center">
              <template #default="{ row }">
                {{ (row.heat_normalized ?? row.popularity_normalized ?? 0).toFixed(3) }}
              </template>
            </el-table-column>
            <el-table-column label="时效性" width="90" align="center">
              <template #default="{ row }">
                {{ (row.timeliness_score ?? 0).toFixed(3) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 历史运行记录 -->
        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span><el-icon><Document /></el-icon> 历史运行记录</span>
            </div>
          </template>
          <el-table :data="historyRecords" stripe size="small" max-height="300">
            <el-table-column prop="batch_id" label="批次ID" width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
                  {{ row.status === 'completed' ? '完成' : row.status === 'failed' ? '失败' : '运行中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="processed" label="处理条数" width="90" align="center" />
            <el-table-column prop="duration" label="耗时" width="90" align="center">
              <template #default="{ row }">{{ row.duration ? row.duration + 'ms' : '-' }}</template>
            </el-table-column>
            <el-table-column prop="time" label="执行时间" width="170" />
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button v-if="row.status === 'failed'" size="small" type="warning" @click="retryFromStage(row)">
                  断点续跑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Connection, VideoPlay, Refresh, Loading, CircleCheck, CircleClose,
  ArrowRight, Download, Operation, DataAnalysis, Histogram, DataLine,
  Document, TrendCharts,
} from '@element-plus/icons-vue';
import apiClient from '@/api/index';
import { SUCCESS, PRIMARY, DANGER, INFO } from '@/styles/colors';

// 流水线阶段定义
const stages = ref([
  { key: 'collect', name: '数据采集', icon: 'Download', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'clean', name: '数据清洗', icon: 'Operation', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'sentiment', name: '情感分析', icon: 'DataAnalysis', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'ranking', name: '双维度排序', icon: 'Histogram', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'store', name: '结果入库', icon: 'Document', status: 'idle', count: undefined as number | undefined, time: '' },
]);

const running = ref(false);
const refreshing = ref(false);
const loadingStats = ref(false);
const loadingRanking = ref(false);
const lastResult = ref<any>(null);

const pipelineConfig = reactive({
  limit: 500,
  preset: 'default',
  resume: false,
});

const pipelineStatus = reactive({
  running: false,
  current_stage: '',
  processed_count: 0,
  total_time: 0,
  bert_available: false,
  batch_id: '',
});

const dbStats = ref([
  { table: 'weibo_core_data', label: '微博原始数据', count: 0 },
  { table: 'sentiment_analysis_results', label: '情感分析结果', count: 0 },
  { table: 'dual_dimension_ranking', label: '双维度排序', count: 0 },
  { table: 'crawl_batch_log', label: '采集批次日志', count: 0 },
]);

const rankingData = ref<any[]>([]);
const historyRecords = ref<any[]>([]);

let pollTimer: number | null = null;

// 执行流水线
const runPipeline = async (mode: 'sync' | 'async') => {
  running.value = true;
  resetStages();

  try {
    const url = mode === 'sync' ? '/pipeline/run' : '/pipeline/run-async';
    const response = await apiClient.post(url, {
      limit: pipelineConfig.limit,
      preset: pipelineConfig.preset,
    });

    if (response.data.code === 200) {
      const data = response.data.data;
      lastResult.value = data;

      if (mode === 'async') {
        ElMessage.success('流水线已在后台启动');
        startPolling();
      } else {
        ElMessage.success(`流水线执行完成，处理 ${data.total_processed ?? 0} 条`);
        updateStagesFromResult(data);
        await loadDatabaseStats();
        await loadRanking();
        addHistoryRecord(data);
      }
    } else {
      ElMessage.error(response.data.message || '执行失败');
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '流水线执行失败');
  } finally {
    if (!pollTimer) running.value = false;
  }
};

// 刷新状态
const refreshStatus = async () => {
  refreshing.value = true;
  try {
    const response = await apiClient.get('/pipeline/status');
    if (response.data.code === 200) {
      const data = response.data.data;
      Object.assign(pipelineStatus, {
        running: data.running ?? false,
        current_stage: data.current_stage ?? '',
        processed_count: data.processed_count ?? 0,
        total_time: data.total_time_ms ?? 0,
        bert_available: data.bert_available ?? false,
        batch_id: data.batch_id ?? '',
      });

      if (!data.running && pollTimer) {
        stopPolling();
        running.value = false;
        await loadRanking();
      }
    }
  } catch (e) {
    // silent
  } finally {
    refreshing.value = false;
  }
};

// 加载数据库统计
const loadDatabaseStats = async () => {
  loadingStats.value = true;
  try {
    const response = await apiClient.get('/pipeline/stats');
    if (response.data.code === 200) {
      const data = response.data.data;
      if (data.tables) {
        dbStats.value.forEach(item => {
          const tableInfo = data.tables[item.table];
          if (tableInfo) item.count = tableInfo.row_count ?? tableInfo.count ?? 0;
        });
      } else if (data.table_stats) {
        dbStats.value.forEach(item => {
          if (data.table_stats[item.table] !== undefined) {
            item.count = data.table_stats[item.table];
          }
        });
      }
    }
  } catch (e) {
    // silent
  } finally {
    loadingStats.value = false;
  }
};

// 加载排序结果
const loadRanking = async () => {
  loadingRanking.value = true;
  try {
    const response = await apiClient.get('/pipeline/ranking', { params: { limit: 20 } });
    if (response.data.code === 200) {
      rankingData.value = response.data.data.items || [];
    }
  } catch (e) {
    // silent
  } finally {
    loadingRanking.value = false;
  }
};

// 断点续跑
const retryFromStage = (record: any) => {
  ElMessage.info(`从阶段 "${record.failed_stage || '情感分析'}" 重试...`);
  runPipeline('async');
};

// 更新阶段状态
const updateStagesFromResult = (data: any) => {
  stages.value.forEach(s => {
    s.status = 'completed';
  });
  if (data.stages) {
    Object.entries(data.stages).forEach(([key, val]: [string, any]) => {
      const stage = stages.value.find(s => s.key === key);
      if (stage) {
        stage.count = val.count ?? val.processed;
        stage.time = val.time_ms ?? val.duration;
        stage.status = val.status ?? 'completed';
      }
    });
  }
  if (data.total_processed !== undefined) {
    const sentimentStage = stages.value.find(s => s.key === 'sentiment');
    if (sentimentStage && !sentimentStage.count) sentimentStage.count = data.total_processed;
  }
};

const resetStages = () => {
  stages.value.forEach(s => {
    s.status = 'idle';
    s.count = undefined;
    s.time = '';
  });
};

const addHistoryRecord = (data: any) => {
  historyRecords.value.unshift({
    batch_id: data.batch_id || `batch_${Date.now()}`,
    status: data.status ?? 'completed',
    processed: data.total_processed ?? 0,
    duration: data.total_time_ms ?? data.elapsed_ms ?? 0,
    time: new Date().toLocaleString('zh-CN'),
    failed_stage: data.failed_stage,
  });
};

// 轮询
const startPolling = () => {
  if (pollTimer) return;
  pollTimer = window.setInterval(() => {
    refreshStatus();
  }, 3000);
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

onMounted(async () => {
  await Promise.all([refreshStatus(), loadDatabaseStats(), loadRanking()]);
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.pipeline-module {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-md;

  h2 {
    margin: 0;
    font-size: $font-size-extra-large;
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }

  .subtitle {
    color: $text-secondary;
    font-size: $font-size-small;
    margin: $spacing-xxs 0 0;
  }
}

.pipeline-visual-card {
  .pipeline-stages {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-xs;
    padding: $spacing-md 0;
  }

  .stage-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    min-width: 90px;

    .stage-icon-wrapper {
      width: 56px;
      height: 56px;
      border-radius: $border-radius-circle;
      display: flex;
      align-items: center;
      justify-content: center;
      background: $bg-page;
      border: 2px solid $border-base;
      transition: $transition-base;
    }

    &.completed .stage-icon-wrapper {
      background: rgba($success-color, 0.08);
      border-color: $success-color;
    }

    &.running .stage-icon-wrapper {
      background: rgba($primary-color, 0.06);
      border-color: $primary-color;
      box-shadow: $shadow-primary;
    }

    &.failed .stage-icon-wrapper {
      background: rgba($danger-color, 0.06);
      border-color: $danger-color;
    }

    .stage-label {
      margin-top: $spacing-xs;
      font-size: $font-size-small;
      color: $text-regular;
      font-weight: $font-weight-medium;
    }

    .stage-detail {
      font-size: $font-size-tiny;
      color: $text-secondary;
      margin-top: 2px;
    }

    .stage-arrow {
      position: absolute;
      right: -20px;
      top: 20px;
      color: $text-placeholder;
      font-size: 18px;
    }
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  span {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
  }
}

.config-card {
  .form-tip {
    font-size: $font-size-extra-small;
    color: $text-secondary;
    margin-top: $spacing-xxs;
  }
}

.db-stats {
  .db-stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $spacing-xs 0;
    border-bottom: 1px solid $border-light;

    &:last-child {
      border-bottom: none;
    }

    .stat-table {
      font-size: $font-size-small;
      color: $text-regular;
    }
  }
}

.batch-id {
  font-family: monospace;
  font-size: $font-size-extra-small;
  color: $text-secondary;
}

.rotating {
  animation: rotating 1.5s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
