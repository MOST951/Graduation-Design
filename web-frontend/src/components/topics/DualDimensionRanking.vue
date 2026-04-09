<template>
  <div class="dual-dimension-ranking">
    <!-- 标题和配置 -->
    <div class="ranking-header">
      <h3>
        <el-icon><TrendCharts /></el-icon>
        情感-热度双维度排序
      </h3>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="loadRankedTopics" :loading="loading" size="small">
          刷新
        </el-button>
        <el-button :icon="Setting" @click="showConfigDialog = true" size="small">
          配置
        </el-button>
      </div>
    </div>

    <!-- 公式说明 -->
    <div class="formula-info">
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          <span class="formula">
            综合得分 = {{ (config.sentiment_weight * 100).toFixed(0) }}% × 情感强度 + 
            {{ (config.popularity_weight * 100).toFixed(0) }}% × 传播热度
          </span>
        </template>
      </el-alert>
    </div>

    <!-- 排序结果表格 -->
    <el-table 
      :data="rankedTopics" 
      v-loading="loading"
      stripe
      highlight-current-row
      @row-click="handleRowClick"
    >
      <el-table-column label="排名" width="70" align="center">
        <template #default="{ row }">
          <el-tag 
            :type="row.rank <= 3 ? 'danger' : row.rank <= 5 ? 'warning' : 'info'"
            size="large"
            class="rank-badge"
          >
            {{ row.rank }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="话题" min-width="200">
        <template #default="{ row }">
          <div class="topic-cell">
            <span class="topic-name">{{ row.name }}</span>
            <div class="topic-keywords">
              <el-tag 
                v-for="kw in (row.keywords || []).slice(0, 3)" 
                :key="kw" 
                size="small" 
                type="info"
              >
                {{ kw }}
              </el-tag>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="综合得分" width="120" align="center" sortable prop="composite_score">
        <template #default="{ row }">
          <div class="score-cell">
            <span class="score-value">{{ row.composite_score.toFixed(4) }}</span>
            <el-progress 
              :percentage="row.composite_score * 100" 
              :show-text="false"
              :stroke-width="6"
              :color="getScoreColor(row.composite_score)"
            />
          </div>
        </template>
      </el-table-column>

      <el-table-column label="情感强度" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="getSentimentType(row.sentiment_avg)" size="small">
            {{ getSentimentLabel(row.sentiment_avg) }}
          </el-tag>
          <div class="sentiment-score">{{ row.sentiment_avg.toFixed(2) }}</div>
        </template>
      </el-table-column>

      <el-table-column label="传播热度" width="110" align="center">
        <template #default="{ row }">
          <div class="popularity-cell">
            <span>{{ row.popularity_score.toFixed(4) }}</span>
            <el-icon :color="getTrendColor(row.trend)">
              <component :is="getTrendIcon(row.trend)" />
            </el-icon>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="微博数" width="90" align="center" prop="post_count">
        <template #default="{ row }">
          {{ formatCount(row.post_count) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 可视化图表 -->
    <div class="charts-section">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card header="得分分布" shadow="hover">
            <div ref="scatterChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card header="Top 5 对比" shadow="hover">
            <div ref="barChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 配置对话框 -->
    <el-dialog v-model="showConfigDialog" title="双维度排序配置" width="500px">
      <el-form label-width="120px">
        <el-form-item label="情感权重">
          <el-slider 
            v-model="configForm.sentiment_weight" 
            :min="0" 
            :max="1" 
            :step="0.1"
            :format-tooltip="(val: number) => `${(val * 100).toFixed(0)}%`"
            @change="onWeightChange('sentiment')"
          />
          <span class="weight-value">{{ (configForm.sentiment_weight * 100).toFixed(0) }}%</span>
        </el-form-item>
        <el-form-item label="热度权重">
          <el-slider 
            v-model="configForm.popularity_weight" 
            :min="0" 
            :max="1" 
            :step="0.1"
            :format-tooltip="(val: number) => `${(val * 100).toFixed(0)}%`"
            @change="onWeightChange('popularity')"
          />
          <span class="weight-value">{{ (configForm.popularity_weight * 100).toFixed(0) }}%</span>
        </el-form-item>
        <el-form-item label="时间衰减(小时)">
          <el-input-number 
            v-model="configForm.time_decay_hours" 
            :min="1" 
            :max="168"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { Refresh, Setting, TrendCharts, CaretTop, CaretBottom, Minus } from '@element-plus/icons-vue';
import { useTopicsStore } from '@/store/topics';
import type { RankedTopic, DualDimensionConfig } from '@/api/topics';

// Props
const props = withDefaults(defineProps<{
  autoLoad?: boolean;
}>(), {
  autoLoad: true,
});

// Emits
const emit = defineEmits<{
  (e: 'config-change', config: DualDimensionConfig): void;
  (e: 'topic-select', topic: RankedTopic): void;
}>();

// Store
const topicsStore = useTopicsStore();
const { rankedTopics, dualDimensionConfig, isLoadingRankedTopics, isSavingConfig } = storeToRefs(topicsStore);

// 本地状态
const showConfigDialog = ref(false);

// 配置表单（用于编辑）
const configForm = reactive<DualDimensionConfig>({
  sentiment_weight: 0.6,
  popularity_weight: 0.4,
  time_decay_hours: 24
});

// 计算属性
const loading = computed(() => isLoadingRankedTopics.value);
const saving = computed(() => isSavingConfig.value);
const config = computed(() => dualDimensionConfig.value);

// 图表引用
const scatterChartRef = ref<HTMLElement>();
const barChartRef = ref<HTMLElement>();
let scatterChart: echarts.ECharts | null = null;
let barChart: echarts.ECharts | null = null;

// 加载排序后的话题
const loadRankedTopics = async () => {
  try {
    await topicsStore.fetchRankedTopics();
    updateCharts();
    ElMessage.success(`加载了 ${rankedTopics.value.length} 个话题`);
  } catch (error: any) {
    console.error('加载话题失败:', error);
    ElMessage.error('加载失败: ' + (error.message || '请检查后端服务'));
  }
};

// 加载配置
const loadConfig = async () => {
  try {
    await topicsStore.fetchDualDimensionConfig();
    // 同步到表单
    Object.assign(configForm, dualDimensionConfig.value);
  } catch (error) {
    console.warn('加载配置失败，使用默认值');
  }
};

// 保存配置
const saveConfig = async () => {
  try {
    await topicsStore.saveDualDimensionConfig(configForm);
    showConfigDialog.value = false;
    ElMessage.success('配置已保存');
    emit('config-change', dualDimensionConfig.value);
    updateCharts();
  } catch (error: any) {
    ElMessage.error('保存失败: ' + error.message);
  }
};

// 权重联动（确保和为1）
const onWeightChange = (type: 'sentiment' | 'popularity') => {
  if (type === 'sentiment') {
    configForm.popularity_weight = Math.round((1 - configForm.sentiment_weight) * 10) / 10;
  } else {
    configForm.sentiment_weight = Math.round((1 - configForm.popularity_weight) * 10) / 10;
  }
};

// 工具函数
const getSentimentType = (score: number) => {
  if (score > 0.3) return 'success';
  if (score < -0.3) return 'danger';
  return 'info';
};

const getSentimentLabel = (score: number) => {
  if (score > 0.3) return '正面';
  if (score < -0.3) return '负面';
  return '中性';
};

const getScoreColor = (score: number) => {
  if (score > 0.7) return '#67C23A';
  if (score > 0.4) return '#E6A23C';
  return '#909399';
};

const getTrendColor = (trend: string) => {
  if (trend === 'up') return '#67C23A';
  if (trend === 'down') return '#F56C6C';
  return '#909399';
};

const getTrendIcon = (trend: string) => {
  if (trend === 'up') return CaretTop;
  if (trend === 'down') return CaretBottom;
  return Minus;
};

const formatCount = (count: number) => {
  if (count >= 10000) return (count / 10000).toFixed(1) + '万';
  return count.toString();
};

const handleRowClick = (row: RankedTopic) => {
  emit('topic-select', row);
  ElMessage.info(`查看话题: ${row.name}`);
};

// 初始化图表
const initCharts = () => {
  if (scatterChartRef.value) {
    scatterChart = echarts.init(scatterChartRef.value);
  }
  if (barChartRef.value) {
    barChart = echarts.init(barChartRef.value);
  }
};

// 更新图表
const updateCharts = () => {
  if (!rankedTopics.value.length) return;

  // 散点图：情感 vs 热度
  if (scatterChart) {
    const scatterData = rankedTopics.value.map(t => ({
      name: t.name,
      value: [Math.abs(t.sentiment_avg), t.popularity_score, t.composite_score],
      itemStyle: {
        color: t.sentiment_avg > 0 ? '#67C23A' : t.sentiment_avg < 0 ? '#F56C6C' : '#909399'
      }
    }));

    scatterChart.setOption({
      tooltip: {
        formatter: (params: any) => {
          const d = params.data;
          return `${d.name}<br/>情感强度: ${d.value[0].toFixed(2)}<br/>传播热度: ${d.value[1].toFixed(4)}<br/>综合得分: ${d.value[2].toFixed(4)}`;
        }
      },
      xAxis: {
        name: '情感强度',
        type: 'value',
        max: 1
      },
      yAxis: {
        name: '传播热度',
        type: 'value',
        max: 1
      },
      series: [{
        type: 'scatter',
        symbolSize: (data: number[]) => Math.max(10, data[2] * 50),
        data: scatterData
      }]
    });
  }

  // 柱状图：Top 5 对比
  if (barChart) {
    const top5 = rankedTopics.value.slice(0, 5);
    
    barChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: ['情感贡献', '热度贡献']
      },
      xAxis: {
        type: 'category',
        data: top5.map(t => t.name),
        axisLabel: {
          rotate: 15,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        max: 1
      },
      series: [
        {
          name: '情感贡献',
          type: 'bar',
          stack: 'total',
          data: top5.map(t => (Math.abs(t.sentiment_avg) * config.sentiment_weight).toFixed(4)),
          itemStyle: { color: '#409EFF' }
        },
        {
          name: '热度贡献',
          type: 'bar',
          stack: 'total',
          data: top5.map(t => (t.popularity_score * config.popularity_weight).toFixed(4)),
          itemStyle: { color: '#67C23A' }
        }
      ]
    });
  }
};

// 生命周期
onMounted(async () => {
  await loadConfig();
  initCharts();
  
  if (props.autoLoad) {
    await loadRankedTopics();
  }
  
  window.addEventListener('resize', () => {
    scatterChart?.resize();
    barChart?.resize();
  });
});

// 监听配置变化
watch(dualDimensionConfig, () => {
  updateCharts();
}, { deep: true });

// 监听排序结果变化
watch(rankedTopics, () => {
  updateCharts();
}, { deep: true });
</script>

<style scoped lang="scss">
.dual-dimension-ranking {
  padding: 20px;

  .ranking-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      font-size: 18px;
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
  }

  .formula-info {
    margin-bottom: 16px;

    .formula {
      font-family: 'Courier New', monospace;
      font-weight: 500;
    }
  }

  .rank-badge {
    font-size: 16px;
    font-weight: bold;
  }

  .topic-cell {
    .topic-name {
      font-weight: 500;
      display: block;
      margin-bottom: 4px;
    }

    .topic-keywords {
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
    }
  }

  .score-cell {
    .score-value {
      font-weight: bold;
      display: block;
      margin-bottom: 4px;
    }
  }

  .sentiment-score {
    font-size: 12px;
    color: #909399;
    margin-top: 2px;
  }

  .popularity-cell {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  .charts-section {
    margin-top: 24px;
  }

  .weight-value {
    margin-left: 12px;
    font-weight: bold;
    color: #409EFF;
  }
}
</style>
