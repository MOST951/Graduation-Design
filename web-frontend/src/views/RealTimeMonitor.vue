<template>
  <div class="monitor-page">
    <!-- ============ 1. 顶部预警栏 ============ -->
    <div class="alert-bar" :class="`level-${stats.alert.level}`">
      <span class="alert-icon">{{ alertIcon }}</span>
      <span class="alert-text">{{ stats.alert.message }}</span>
      <span class="alert-meta">负面比例 {{ (stats.alert.negative_ratio * 100).toFixed(1) }}%</span>
      <span class="alert-time">{{ formatTime(stats.timestamp) }}</span>
      <el-switch
        v-model="desktopNotify"
        active-text="桌面通知"
        size="small"
        style="margin-left: auto"
        @change="onNotifyToggle"
      />
    </div>

    <!-- ============ 2. 中部：情感环形图 + 关键词排行榜 ============ -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-hdr">
              <span>最近一小时情感分布</span>
              <el-tag size="small" type="info">总计 {{ stats.sentiment_distribution.total }} 条</el-tag>
            </div>
          </template>
          <div ref="donutRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-hdr">
              <span>热门关键词 Top 10</span>
              <el-tag size="small" type="warning">{{ stats.keyword_ranking.length }}</el-tag>
            </div>
          </template>
          <div class="keyword-ranking">
            <div
              v-for="(kw, idx) in stats.keyword_ranking"
              :key="kw.keyword"
              class="kw-row"
            >
              <span class="kw-rank" :class="rankClass(idx + 1)">{{ idx + 1 }}</span>
              <span class="kw-name">#{{ kw.keyword }}</span>
              <el-progress
                :percentage="Math.round((kw.count / maxKeywordCount) * 100)"
                :show-text="false"
                :stroke-width="8"
                class="kw-bar"
              />
              <span class="kw-count">{{ kw.count }}</span>
            </div>
            <el-empty
              v-if="stats.keyword_ranking.length === 0"
              description="暂无关键词数据"
              :image-size="60"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 3. 系统状态卡片 ============ -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="6">
        <el-card shadow="hover" class="status-card status-collect">
          <div class="status-label">采集任务</div>
          <div class="status-main">{{ stats.system_status.crawler_tasks.active }}</div>
          <div class="status-sub">
            活跃 ·
            <el-tag size="small" type="success" effect="plain">完成 {{ stats.system_status.crawler_tasks.completed }}</el-tag>
            <el-tag size="small" type="danger" effect="plain">失败 {{ stats.system_status.crawler_tasks.failed }}</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card status-spark">
          <div class="status-label">Spark 作业</div>
          <div class="spark-tags">
            <el-tag size="small" type="warning">等待 {{ stats.system_status.spark_jobs.pending }}</el-tag>
            <el-tag size="small" type="primary">运行 {{ stats.system_status.spark_jobs.running }}</el-tag>
            <el-tag size="small" type="success">完成 {{ stats.system_status.spark_jobs.completed }}</el-tag>
            <el-tag size="small" type="danger" v-if="stats.system_status.spark_jobs.failed > 0">失败 {{ stats.system_status.spark_jobs.failed }}</el-tag>
          </div>
          <div class="status-sub" style="margin-top: 8px">无需登录 Spark UI</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card status-pending">
          <div class="status-label">未处理数据量</div>
          <div class="status-main">{{ stats.system_status.unprocessed_count }}</div>
          <div class="status-sub">条待分析</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card status-online">
          <div class="status-label">订阅关键词</div>
          <div class="status-main">{{ subscribedKeywords.length }}</div>
          <div class="kw-manage">
            <el-tag
              v-for="kw in subscribedKeywords"
              :key="kw"
              closable
              size="small"
              style="margin: 2px"
              @close="removeKeyword(kw)"
            >{{ kw }}</el-tag>
          </div>
          <div class="kw-add" style="margin-top: 8px; display: flex; gap: 4px">
            <el-input
              v-model="newKeyword"
              placeholder="输入关键词"
              size="small"
              style="flex:1"
              @keyup.enter="addKeyword"
            />
            <el-button size="small" type="primary" @click="addKeyword">添加</el-button>
          </div>
          <div class="status-sub" style="margin-top: 4px">SSE 客户端 {{ stats.system_status.sse_clients }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 4. 预警历史表格 ============ -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>
        <div class="card-hdr">
          <span>预警历史</span>
          <el-tag size="small">{{ stats.alert_history.length }} 条</el-tag>
        </div>
      </template>
      <el-table
        :data="stats.alert_history"
        stripe
        size="small"
        max-height="320"
        empty-text="暂无预警记录"
      >
        <el-table-column prop="triggered_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.triggered_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="rule_name" label="预警规则" width="160" />
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.level === 'critical' ? 'danger' : 'warning'"
              size="small"
              effect="dark"
            >
              {{ row.level === 'critical' ? '严重' : '警告' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="实际值" width="100">
          <template #default="{ row }">
            {{ typeof row.value === 'number' ? row.value.toFixed(3) : row.value }}
          </template>
        </el-table-column>
        <el-table-column prop="threshold" label="阈值" width="100">
          <template #default="{ row }">
            {{ typeof row.threshold === 'number' ? row.threshold.toFixed(2) : row.threshold }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="描述" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import apiClient from '@/api/index';

// ========= 状态 =========
const stats = reactive({
  sentiment_distribution: { positive: 0, negative: 0, neutral: 0, total: 0 },
  alert: {
    level: 'normal' as 'normal' | 'warning' | 'high' | 'critical',
    color: '#67c23a',
    message: '正在加载实时舆情数据…',
    negative_ratio: 0,
    thresholds: { yellow: 0.30, orange: 0.45, red: 0.60 },
  },
  keyword_ranking: [] as Array<{ keyword: string; count: number }>,
  system_status: {
    spark_jobs: { pending: 0, running: 0, completed: 0, failed: 0 },
    crawler_tasks: { active: 0, completed: 0, failed: 0 },
    unprocessed_count: 0,
    sse_clients: 0,
    subscribed_keywords: 0,
  },
  alert_history: [] as any[],
  timestamp: new Date().toISOString(),
});

const desktopNotify = ref(false);
const donutRef = ref<HTMLElement>();
let donutChart: echarts.ECharts | null = null;
let pollTimer: ReturnType<typeof setInterval> | null = null;
let lastAlertLevel = 'normal';

// ========= 关键词订阅管理 =========
const subscribedKeywords = ref<string[]>([]);
const newKeyword = ref('');

const fetchKeywords = async () => {
  try {
    const res = await apiClient.get('/monitor/keywords');
    if (res.data?.code === 200) subscribedKeywords.value = res.data.data || [];
  } catch { /* ignore */ }
};

const addKeyword = async () => {
  const kw = newKeyword.value.trim();
  if (!kw) return;
  try {
    const res = await apiClient.post('/monitor/keywords', { keyword: kw });
    if (res.data?.code === 200) {
      subscribedKeywords.value = res.data.data || [];
      newKeyword.value = '';
      ElMessage.success(`已订阅: ${kw}`);
    }
  } catch (e: any) {
    ElMessage.error('添加失败: ' + (e?.message || '未知错误'));
  }
};

const removeKeyword = async (kw: string) => {
  try {
    const res = await apiClient.delete('/monitor/keywords', { data: { keyword: kw } });
    if (res.data?.code === 200) {
      subscribedKeywords.value = res.data.data || [];
      ElMessage.success(`已取消订阅: ${kw}`);
    }
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e?.message || '未知错误'));
  }
};

// ========= 计算属性 =========
const maxKeywordCount = computed(() =>
  Math.max(1, ...stats.keyword_ranking.map(k => k.count))
);
const alertIcon = computed(() => {
  switch (stats.alert.level) {
    case 'critical': return '🔴';
    case 'high':     return '🟠';
    case 'warning':  return '🟡';
    default:         return '🟢';
  }
});
const rankClass = (rank: number) => {
  if (rank === 1) return 'gold';
  if (rank === 2) return 'silver';
  if (rank === 3) return 'bronze';
  return 'normal';
};

// ========= 工具 =========
const formatTime = (iso?: string) => {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  } catch {
    return iso;
  }
};

// ========= 环形图 =========
const renderDonut = () => {
  if (!donutChart || !donutRef.value) return;
  const sd = stats.sentiment_distribution;
  donutChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      name: '情感分布',
      type: 'pie',
      radius: ['45%', '70%'],
      avoidLabelOverlap: false,
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 12 },
      labelLine: { show: true },
      data: [
        { value: sd.positive, name: '正面', itemStyle: { color: '#67c23a' } },
        { value: sd.neutral,  name: '中性', itemStyle: { color: '#909399' } },
        { value: sd.negative, name: '负面', itemStyle: { color: '#f56c6c' } },
      ],
    }],
  });
};

// ========= 桌面通知 =========
const onNotifyToggle = async (val: boolean) => {
  if (val && 'Notification' in window) {
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') {
      desktopNotify.value = false;
      ElMessage.warning('浏览器通知权限被拒绝');
    } else {
      ElMessage.success('桌面通知已启用');
    }
  }
};

const triggerBrowserNotification = (level: string, message: string) => {
  if (!desktopNotify.value) return;
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const titleMap: Record<string, string> = {
    warning: '⚠️ 黄色预警',
    high:    '🟠 高级预警',
    critical:'🚨 严重预警',
  };
  new Notification(titleMap[level] || '舆情预警', {
    body: message,
    icon: '/favicon.ico',
    tag: `monitor-${level}`,
  });
};

// ========= 5 秒轮询 =========
const fetchStatistics = async () => {
  try {
    const res = await apiClient.get('/monitor/statistics');
    if (res.data?.code === 200 && res.data.data) {
      Object.assign(stats, res.data.data);
      // 等级升高时弹通知
      const order = ['normal', 'warning', 'high', 'critical'];
      if (order.indexOf(stats.alert.level) > order.indexOf(lastAlertLevel)
          && stats.alert.level !== 'normal') {
        triggerBrowserNotification(stats.alert.level, stats.alert.message);
      }
      lastAlertLevel = stats.alert.level;
      renderDonut();
    }
  } catch (e: any) {
    console.warn('[Monitor] 获取统计数据失败', e?.message);
  }
};

// ========= 生命周期 =========
onMounted(async () => {
  await nextTick();
  if (donutRef.value) {
    donutChart = echarts.init(donutRef.value);
    window.addEventListener('resize', () => donutChart?.resize());
  }
  await fetchKeywords();
  await fetchStatistics();
  pollTimer = setInterval(fetchStatistics, 5000);
});

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer);
  donutChart?.dispose();
});

watch(() => stats.sentiment_distribution, renderDonut, { deep: true });
</script>

<style scoped lang="scss">
.monitor-page {
  padding: 16px;
}

/* ===== 顶部预警栏 ===== */
.alert-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: background 0.4s;

  &.level-normal   { background: linear-gradient(90deg, #67c23a, #85ce61); }
  &.level-warning  { background: linear-gradient(90deg, #f7ba2a, #f5d76b); color: #5a3e00; }
  &.level-high     { background: linear-gradient(90deg, #e6a23c, #ebb563); }
  &.level-critical {
    background: linear-gradient(90deg, #f56c6c, #f78989);
    animation: pulse 1.4s ease-in-out infinite;
  }

  .alert-icon { font-size: 20px; }
  .alert-text { font-weight: 600; font-size: 15px; }
  .alert-meta { padding: 2px 10px; background: rgba(255,255,255,0.25); border-radius: 12px; font-size: 12px; }
  .alert-time { font-size: 12px; opacity: 0.85; }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 2px 8px rgba(245, 108, 108, 0.4); }
  50%      { box-shadow: 0 4px 20px rgba(245, 108, 108, 0.85); }
}

/* ===== 卡片头 ===== */
.card-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

/* ===== 关键词排行 ===== */
.keyword-ranking {
  max-height: 300px;
  overflow-y: auto;
  padding: 4px 0;
}
.kw-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
  font-size: 13px;
  border-bottom: 1px solid #f0f2f5;

  .kw-rank {
    width: 22px; height: 22px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%;
    font-size: 12px; font-weight: 700;
    color: #fff; background: #909399;
    flex-shrink: 0;

    &.gold   { background: linear-gradient(135deg, #f7ba2a, #f5d76b); }
    &.silver { background: linear-gradient(135deg, #a0a4aa, #c0c4cc); }
    &.bronze { background: linear-gradient(135deg, #cf8a4c, #e6a76c); }
  }
  .kw-name { flex: 1; min-width: 80px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #303133; }
  .kw-bar  { flex: 2; }
  .kw-count { width: 36px; text-align: right; color: #909399; font-size: 12px; }
}

/* ===== 系统状态卡片 ===== */
.status-card {
  height: 116px;
  .status-label { font-size: 13px; color: #909399; margin-bottom: 6px; }
  .status-main  { font-size: 28px; font-weight: 700; color: #303133; line-height: 1.2; }
  .status-sub   { font-size: 12px; color: #909399; margin-top: 4px; display: flex; gap: 6px; align-items: center; }
  .spark-tags   { display: flex; flex-wrap: wrap; gap: 4px; }
}
.status-collect { border-left: 3px solid #409eff; }
.status-spark   { border-left: 3px solid #e6a23c; }
.status-pending { border-left: 3px solid #f56c6c; }
.status-online  { border-left: 3px solid #67c23a; }
</style>
