<template>
  <div class="pipeline-module">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2><el-icon><Connection /></el-icon> 数据流水线管理</h2>
        <p class="subtitle">全流程执行：采集 → 清洗 → 情感分析 → 三维度排序 → 入库</p>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="VideoPlay" :loading="running" :disabled="running || paused" @click="runPipeline('sync')">
          同步执行
        </el-button>
        <el-button type="success" :icon="VideoPlay" :loading="running" :disabled="running || paused" @click="runPipeline('async')">
          异步执行
        </el-button>
        <el-button v-if="running && !paused" type="warning" :icon="VideoPause" @click="pausePipeline">
          暂停
        </el-button>
        <el-button v-if="paused" type="success" :icon="VideoPlay" :disabled="terminated" @click="resumePipeline">
          恢复
        </el-button>
        <el-button v-if="running || paused" type="danger" :disabled="terminated" @click="terminatePipeline">
          终止
        </el-button>
        <el-button :icon="Refresh" :loading="refreshing" @click="refreshStatus">刷新状态</el-button>
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
          <div v-if="stage.count !== undefined && stage.count > 0" class="stage-detail">
            {{ stage.count }} 条
          </div>
          <div v-if="stage.time" class="stage-detail">{{ stage.time }}ms</div>
          <div v-if="idx < stages.length - 1" class="stage-arrow">
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
            <el-form-item label="定时调度">
              <el-switch v-model="pipelineConfig.scheduling_enabled" active-text="启用" inactive-text="禁用" />
            </el-form-item>
            <el-form-item v-if="pipelineConfig.scheduling_enabled" label="Cron 表达式">
              <el-input 
                v-model="pipelineConfig.cron_expression" 
                placeholder="0 2 * * *"
                style="width: 100%"
              >
                <template #append>
                  <el-button size="small" @click="showCronHelper = true">
                    <el-icon><Setting /></el-icon>
                  </el-button>
                </template>
              </el-input>
              <div class="form-tip">例如：0 2 * * * 表示每天凌晨2点执行</div>
            </el-form-item>
            <el-form-item label="高级配置">
              <el-switch v-model="pipelineConfig.advanced_mode" active-text="启用" inactive-text="禁用" />
            </el-form-item>
            <el-form-item v-if="pipelineConfig.advanced_mode" label="配置编辑器">
              <el-select v-model="configEditorMode" size="small" style="width: 100px; margin-right: 8px">
                <el-option label="JSON" value="json" />
                <el-option label="YAML" value="yaml" />
              </el-select>
              <el-button size="small" @click="showAdvancedConfig = true">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 数据库统计 -->
        <el-card header="数据库统计" shadow="hover" class="config-card" style="margin-top: 16px">
          <div v-loading="loadingStats" class="db-stats">
            <div v-for="item in dbStats" :key="item.table" class="db-stat-row">
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
              <span><el-icon><Histogram /></el-icon> 最新三维度排序结果 TOP20</span>
              <el-button size="small" :icon="Refresh" :loading="loadingRanking" @click="loadRanking">刷新</el-button>
            </div>
          </template>
          <el-table v-loading="loadingRanking" :data="rankingData" stripe size="small" max-height="400">
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
                <el-tag type="primary">{{ Number(row.composite_score ?? row.final_score ?? 0).toFixed(3) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="情感强度" width="90" align="center">
              <template #default="{ row }">
                {{ Number(row.sentiment_score ?? row.sentiment_intensity ?? 0).toFixed(3) }}
              </template>
            </el-table-column>
            <el-table-column label="热度" width="90" align="center">
              <template #default="{ row }">
                {{ Number(row.popularity_score ?? row.heat_normalized ?? 0).toFixed(3) }}
              </template>
            </el-table-column>
            <el-table-column label="时效性" width="90" align="center">
              <template #default="{ row }">
                {{ Number(row.time_decay ?? row.timeliness_score ?? 0).toFixed(3) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 历史运行记录 -->
        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span><el-icon><Document /></el-icon> 历史运行记录</span>
              <div style="display:flex;align-items:center;gap:8px">
                <el-tag type="info" size="small">{{ historyRecords.length }} 条</el-tag>
                <el-button size="small" type="danger" plain :disabled="historyRecords.length === 0" @click="clearHistory">
                  清理历史
                </el-button>
              </div>
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
    
    <!-- Cron  -->
    <el-dialog v-model="showCronHelper" title="Cron " width="600px">
      <div class="cron-helper">
        <el-tabs type="card">
          <el-tab-pane label=" " name="presets">
            <div class="cron-presets">
              <el-button 
                v-for="preset in cronPresets" 
                :key="preset.name"
                style="margin: 4px"
                @click="pipelineConfig.cron_expression = preset.expression; showCronHelper = false"
              >
                {{ preset.name }}
                <div style="font-size: 11px; color: #666; margin-top: 2px">{{ preset.expression }}</div>
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label=" " name="builder">
            <el-form label-position="top">
              <el-form-item label=" ">
                <el-radio-group v-model="cronBuilder.minute">
                  <el-radio label="*"> </el-radio>
                  <el-radio label="0">0</el-radio>
                  <el-radio label="15">15</el-radio>
                  <el-radio label="30">30</el-radio>
                  <el-radio label="45">45</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label=" ">
                <el-radio-group v-model="cronBuilder.hour">
                  <el-radio label="*"> </el-radio>
                  <el-radio label="0">0</el-radio>
                  <el-radio label="2">2</el-radio>
                  <el-radio label="6">6</el-radio>
                  <el-radio label="12">12</el-radio>
                  <el-radio label="18">18</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label=" ">
                <el-radio-group v-model="cronBuilder.day">
                  <el-radio label="*"> </el-radio>
                  <el-radio label="1">1</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label=" ">
                <el-radio-group v-model="cronBuilder.month">
                  <el-radio label="*"> </el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label=" ">
                <el-radio-group v-model="cronBuilder.weekday">
                  <el-radio label="*"> </el-radio>
                  <el-radio label="1"> </el-radio>
                  <el-radio label="2"> </el-radio>
                  <el-radio label="3"> </el-radio>
                  <el-radio label="4"> </el-radio>
                  <el-radio label="5"> </el-radio>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <div style="margin-top: 16px; padding: 12px; background: #f5f5f5; border-radius: 4px">
              <strong> : </strong>{{ generatedCron }}
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <el-button @click="showCronHelper = false"> </el-button>
        <el-button type="primary" @click="pipelineConfig.cron_expression = generatedCron; showCronHelper = false">
        </el-button>
      </template>
    </el-dialog>
    
    <!--  -->
    <el-dialog v-model="showAdvancedConfig" :title="` `" width="800px">
      <div class="advanced-config-editor">
        <el-tabs v-model="configEditorTab">
          <el-tab-pane label="Spark " name="spark">
            <el-input 
              v-model="advancedConfig.spark_config"
              type="textarea"
              :rows="12"
              :placeholder="configEditorMode === 'json' ? jsonSparkPlaceholder : yamlSparkPlaceholder"
              style="font-family: 'Courier New', monospace"
            />
          </el-tab-pane>
          <el-tab-pane label=" " name="cleaning">
            <el-input 
              v-model="advancedConfig.cleaning_rules"
              type="textarea"
              :rows="12"
              :placeholder="configEditorMode === 'json' ? jsonCleaningPlaceholder : yamlCleaningPlaceholder"
              style="font-family: 'Courier New', monospace"
            />
          </el-tab-pane>
          <el-tab-pane label=" " name="custom">
            <el-input 
              v-model="advancedConfig.custom_params"
              type="textarea"
              :rows="12"
              placeholder=" "
              style="font-family: 'Courier New', monospace"
            />
          </el-tab-pane>
        </el-tabs>
        
        <div style="margin-top: 16px">
          <el-button :loading="validatingConfig" @click="validateConfig">
            <el-icon><Check /></el-icon> 
          </el-button>
          <el-button style="margin-left: 8px" @click="resetConfig">
            <el-icon><RefreshLeft /></el-icon> 
          </el-button>
          <el-button style="margin-left: 8px" @click="loadDefaultConfig">
            <el-icon><Download /></el-icon> 
          </el-button>
        </div>
        
        <div v-if="configValidationResult" style="margin-top: 12px">
          <el-alert 
            :type="configValidationResult.valid ? 'success' : 'error'" 
            :title="configValidationResult.message"
            :closable="false"
            show-icon
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="showAdvancedConfig = false"> </el-button>
        <el-button type="primary" :loading="savingConfig" @click="saveAdvancedConfig">
        </el-button>
      </template>
    </el-dialog>
    
    <!-- WebSocket  -->
    <div v-if="wsStatus.connected" class="websocket-indicator">
      <el-icon color="#67c23a"><Connection /></el-icon>
      <span style="margin-left: 4px; font-size: 12px"> </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Connection, VideoPlay, VideoPause, Refresh, Loading, CircleCheck, CircleClose,
  ArrowRight, Download, Operation, DataAnalysis, Histogram, DataLine,
  Document, TrendCharts, Setting, Edit, Check, RefreshLeft,
} from '@element-plus/icons-vue';
import apiClient from '@/api/index';
import { SUCCESS, PRIMARY, DANGER, INFO } from '@/styles/colors';

// 流水线阶段定义
const stages = ref([
  { key: 'collect', name: '数据采集', icon: 'Download', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'clean', name: '数据清洗', icon: 'Operation', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'sentiment', name: '情感分析', icon: 'DataAnalysis', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'ranking', name: '三维度排序', icon: 'Histogram', status: 'idle', count: undefined as number | undefined, time: '' },
  { key: 'store', name: '结果入库', icon: 'Document', status: 'idle', count: undefined as number | undefined, time: '' },
]);

const running = ref(false);
const paused = ref(false);
const terminated = ref(false);
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

// 缓存恢复
const PIPELINE_CACHE_KEY = 'pipeline_manager_cache';
const restorePipelineCache = () => {
  try {
    const cached = localStorage.getItem(PIPELINE_CACHE_KEY);
    if (cached) return JSON.parse(cached);
  } catch { /* ignore */ }
  return null;
};
const cachedPipeline = restorePipelineCache();

const dbStats = ref(cachedPipeline?.dbStats || [
  { table: 'weibo_core_data', label: '微博原始数据', count: 0 },
  { table: 'sentiment_analysis_results', label: '情感分析结果', count: 0 },
  { table: 'tri_dimension_ranking', label: '三维度排序', count: 0 },
  { table: 'crawl_batch_log', label: '采集批次日志', count: 0 },
]);

const rankingData = ref<any[]>(cachedPipeline?.rankingData || []);
const historyRecords = ref<any[]>(cachedPipeline?.historyRecords || []);

const savePipelineCache = () => {
  try {
    localStorage.setItem(PIPELINE_CACHE_KEY, JSON.stringify({
      dbStats: dbStats.value,
      rankingData: rankingData.value,
      historyRecords: historyRecords.value,
      timestamp: Date.now()
    }));
  } catch { /* quota exceeded */ }
};

// 
const showCronHelper = ref(false);
const showAdvancedConfig = ref(false);
const configEditorMode = ref('json');
const configEditorTab = ref('spark');
const savingConfig = ref(false);
const validatingConfig = ref(false);

const cronBuilder = reactive({
  minute: '0',
  hour: '2',
  day: '*',
  month: '*',
  weekday: '*'
});

const cronPresets = ref([
  { name: ' ', expression: '0 2 * * *' },
  { name: ' ', expression: '0 */6 * * *' },
  { name: ' ', expression: '0 0 * * 1' },
  { name: ' ', expression: '0 0 1 * *' },
  { name: ' ', expression: '*/30 * * * *' },
  { name: ' ', expression: '0 */2 * * 1-5' }
]);

const advancedConfig = reactive({
  spark_config: '',
  cleaning_rules: '',
  custom_params: ''
});

const configValidationResult = ref<any>(null);

// WebSocket 
const wsStatus = reactive({
  connected: false,
  reconnecting: false,
  retryCount: 0
});

let websocket: WebSocket | null = null;
let wsReconnectTimer: number | null = null;
let pollTimer: number | null = null;

// 执行流水线
// resumeOpts 由 retryFromStage 传入，可含 resume_from / batch_id 表示从指定阶段重跑
const runPipeline = async (mode: 'sync' | 'async', resumeOpts?: { resume_from?: string; batch_id?: string }) => {
  running.value = true;
  terminated.value = false;
  if (!resumeOpts?.resume_from) {
    resetStages();
  }

  try {
    const url = mode === 'sync' ? '/pipeline/run' : '/pipeline/run-async';
    const response = await apiClient.post(url, {
      limit: pipelineConfig.limit,
      preset: pipelineConfig.preset,
      resume_from: resumeOpts?.resume_from,
      batch_id: resumeOpts?.batch_id,
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
      ElMessage.warning(response.data.message || '执行失败');
    }
  } catch (error: any) {
    ElMessage.warning(error.response?.data?.message || '流水线执行失败');
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
      } else {
        // 直接从扁平字段映射（API返回 weibo_core_data: 150 等）
        dbStats.value.forEach(item => {
          if (data[item.table] !== undefined) {
            item.count = data[item.table];
          }
        });
      }
      savePipelineCache();
    }
  } catch (e: any) {
    console.debug(`[Pipeline] stats 请求失败 (${e.response?.status || 'network'})，使用缓存数据`);
  } finally {
    loadingStats.value = false;
  }
};

// 加载历史运行记录（从 crawl_batch_log）— 直接调 /pipeline/history，不再多查一次 stats
const loadHistory = async () => {
  try {
    const batchResp = await apiClient.get('/pipeline/history', { params: { limit: 50 } });
    if (batchResp.data.code === 200 && Array.isArray(batchResp.data.data)) {
      historyRecords.value = batchResp.data.data.map((b: any) => ({
        batch_id: b.batch_id,
        status: b.status || 'completed',
        processed: b.total_weibos || b.success_count || 0,
        duration: 0,
        time: b.end_time || b.created_at || '',
      }));
      savePipelineCache();
    }
  } catch (e: any) {
    console.debug(`[Pipeline] history 请求失败 (${e.response?.status || 'network'})，使用缓存数据`);
  }
};

// 加载排序结果
const loadRanking = async () => {
  loadingRanking.value = true;
  try {
    const response = await apiClient.get('/pipeline/ranking', { params: { limit: 20 } });
    if (response.data.code === 200) {
      rankingData.value = response.data.data.items || [];
      savePipelineCache();
    }
  } catch (e: any) {
    console.debug(`[Pipeline] ranking 请求失败 (${e.response?.status || 'network'})，使用缓存数据`);
  } finally {
    loadingRanking.value = false;
  }
};

// 断点续跑——指定从哪个阶段重跑，仅在启用「断点续跑」开关时生效
const retryFromStage = (record: any) => {
  if (!pipelineConfig.resume) {
    ElMessage.warning('请先启用「断点续跑」开关');
    return;
  }
  const stageKey = record.failed_stage || record.stage || 'sentiment';
  const batchId = record.batch_id || lastResult.value?.batch_id;
  ElMessage.info(`从阶段 「${stageKey}」 断点续跑中…`);
  runPipeline('async', { resume_from: stageKey, batch_id: batchId });
};

// 暂停流水线
const pausePipeline = async () => {
  try {
    await apiClient.post('/pipeline/pause');
    paused.value = true;
    stopPolling();
    ElMessage.warning('流水线已暂停');
  } catch {
    paused.value = true;
    stopPolling();
    ElMessage.warning('流水线已暂停（前端模拟）');
  }
};

// 恢复流水线
const resumePipeline = async () => {
  if (terminated.value) return;
  try {
    await apiClient.post('/pipeline/resume');
    paused.value = false;
    startPolling();
    ElMessage.success('流水线已恢复');
  } catch {
    paused.value = false;
    startPolling();
    ElMessage.success('流水线已恢复（前端模拟）');
  }
};

// 终止流水线（不可恢复，保留已完成阶段结果）
const terminatePipeline = async () => {
  try {
    await apiClient.post('/pipeline/stop');
  } catch {
    // silent
  }
  terminated.value = true;
  running.value = false;
  paused.value = false;
  stopPolling();
  ElMessage.error('流水线已终止，已完成阶段结果已保留');
};

// 清理历史批次（调用后端 DELETE API）
const clearHistory = async () => {
  const count = historyRecords.value.length;
  try {
    await apiClient.delete('/pipeline/history');
  } catch {
    // 后端接口不可用时仅清理前端
  }
  historyRecords.value = [];
  savePipelineCache();
  ElMessage.success(`已清理 ${count} 条历史记录`);
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

const generatedCron = computed(() => {
  return `${cronBuilder.minute} ${cronBuilder.hour} ${cronBuilder.day} ${cronBuilder.month} ${cronBuilder.weekday}`;
});

// 
const jsonSparkPlaceholder = `{
  "spark.app.name": "weibo-sentiment-pipeline",
  "spark.executor.memory": "2g",
  "spark.executor.cores": "2",
  "spark.sql.shuffle.partitions": "200",
  "spark.default.parallelism": "100"
}`;

const yamlSparkPlaceholder = `spark:
  app.name: "weibo-sentiment-pipeline"
  executor.memory: "2g"
  executor.cores: "2"
  sql.shuffle.partitions: 200
  default.parallelism: 100`;

const jsonCleaningPlaceholder = `{
  "remove_duplicates": true,
  "min_content_length": 10,
  "max_content_length": 500,
  "filter_keywords": ["spam", "ad"],
  "language_detection": true
}`;

const yamlCleaningPlaceholder = `remove_duplicates: true
min_content_length: 10
max_content_length: 500
filter_keywords:
  - "spam"
  - "ad"
language_detection: true`;

// WebSocket 
const connectWebSocket = () => {
  if (websocket) {
    websocket.close();
  }

  try {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/pipeline`;
    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      wsStatus.connected = true;
      wsStatus.reconnecting = false;
      wsStatus.retryCount = 0;
      
      // 
      stopPolling();
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      wsStatus.connected = false;
      
      // 
      if (wsStatus.retryCount < 5) {
        wsStatus.reconnecting = true;
        wsStatus.retryCount++;
        
        const delay = Math.min(1000 * Math.pow(2, wsStatus.retryCount - 1), 30000);
        wsReconnectTimer = window.setTimeout(() => {
          connectWebSocket();
        }, delay);
      } else {
        // 
        startPolling();
      }
    };

    websocket.onerror = () => {
      // WebSocket连接失败时静默处理，onclose回调会负责重连逻辑
    };

  } catch (error) {
    console.error('Failed to connect WebSocket:', error);
    // 
    startPolling();
  }
};

const disconnectWebSocket = () => {
  if (websocket) {
    websocket.close();
    websocket = null;
  }
  
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
  
  wsStatus.connected = false;
  wsStatus.reconnecting = false;
  wsStatus.retryCount = 0;
};

const handleWebSocketMessage = (data: any) => {
  if (data.type === 'pipeline_status') {
    Object.assign(pipelineStatus, data.status);
    
    if (data.status.current_stage) {
      const stage = stages.value.find(s => s.key === data.status.current_stage);
      if (stage) {
        stage.status = 'running';
      }
    }
    
    if (data.status.status === 'completed') {
      stages.value.forEach(s => s.status = 'completed');
      running.value = false;
      loadRanking();
      loadDatabaseStats();
    } else if (data.status.status === 'failed') {
      running.value = false;
      ElMessage.warning(`Pipeline failed: ${data.status.error || 'Unknown error'}`);
    }
  } else if (data.type === 'stage_progress') {
    const stage = stages.value.find(s => s.key === data.stage);
    if (stage) {
      stage.count = data.processed_count;
      stage.status = 'running';
    }
  }
};

// 
const validateConfig = async () => {
  validatingConfig.value = true;
  try {
    const configData = {
      spark_config: configEditorMode.value === 'json' ? 
        JSON.parse(advancedConfig.spark_config || '{}') : 
        advancedConfig.spark_config,
      cleaning_rules: configEditorMode.value === 'json' ? 
        JSON.parse(advancedConfig.cleaning_rules || '{}') : 
        advancedConfig.cleaning_rules,
      custom_params: configEditorMode.value === 'json' ? 
        JSON.parse(advancedConfig.custom_params || '{}') : 
        advancedConfig.custom_params
    };

    const response = await apiClient.post('/pipeline/validate-config', configData);
    if (response.data.code === 200) {
      configValidationResult.value = {
        valid: true,
        message: ' '
      };
    } else {
      configValidationResult.value = {
        valid: false,
        message: response.data.message || ' '
      };
    }
  } catch (error: any) {
    configValidationResult.value = {
      valid: false,
      message: error.response?.data?.message || ' '
    };
  } finally {
    validatingConfig.value = false;
  }
};

const saveAdvancedConfig = async () => {
  savingConfig.value = true;
  try {
    const configData = {
      spark_config: advancedConfig.spark_config,
      cleaning_rules: advancedConfig.cleaning_rules,
      custom_params: advancedConfig.custom_params,
      format: configEditorMode.value
    };

    const response = await apiClient.post('/pipeline/save-config', configData);
    if (response.data.code === 200) {
      ElMessage.success(' ');
      showAdvancedConfig.value = false;
    } else {
      ElMessage.warning(response.data.message || ' ');
    }
  } catch (error: any) {
    ElMessage.warning(error.response?.data?.message || ' ');
  } finally {
    savingConfig.value = false;
  }
};

const resetConfig = () => {
  advancedConfig.spark_config = '';
  advancedConfig.cleaning_rules = '';
  advancedConfig.custom_params = '';
  configValidationResult.value = null;
};

const loadDefaultConfig = async () => {
  try {
    const response = await apiClient.get('/pipeline/default-config');
    if (response.data.code === 200) {
      const config = response.data.data;
      advancedConfig.spark_config = JSON.stringify(config.spark_config || {}, null, 2);
      advancedConfig.cleaning_rules = JSON.stringify(config.cleaning_rules || {}, null, 2);
      advancedConfig.custom_params = JSON.stringify(config.custom_params || {}, null, 2);
      ElMessage.success(' ');
    }
  } catch (error: any) {
    ElMessage.warning(' ');
  }
};

onMounted(() => {
  // 先用 localStorage 缓存渲染初始 UI (在 setup 阶段已填入 dbStats/rankingData/historyRecords),
  // 再后台并发刷新 — 避免首屏阻塞 (论文 3.x 性能要求: 前端响应 <3s).
  refreshStatus();
  loadDatabaseStats();
  loadRanking();
  loadHistory();
  connectWebSocket();
});

onUnmounted(() => {
  stopPolling();
  disconnectWebSocket();
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
