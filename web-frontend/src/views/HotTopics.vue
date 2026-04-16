<template>
  <div class="hot-topics-module">
    <!-- 顶部标题和核心创新点说明 -->
    <div class="page-header">
      <h2>热点话题分析</h2>
      <div class="header-badges">
        <el-tag type="success" size="large" effect="dark">
          <el-icon><TrendCharts /></el-icon>
          核心创新点：情感-热度双维度排序
        </el-tag>
        <!-- 连通性状态指示器 -->
        <el-tag 
          :type="connectivityTagType" 
          size="small" 
          effect="plain"
          class="connectivity-tag"
          :loading="connectivityChecking"
          @click="checkConnectivity"
        >
          <el-icon v-if="!connectivityChecking"><Connection /></el-icon>
          {{ connectivityText }} ({{ overallConnectivity.toFixed(0) }}%)
        </el-tag>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- 左侧列：实时热搜和词云 -->
      <el-col :span="12">
        <!-- 实时热搜榜 -->
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>微博实时热搜</span>
              <div class="header-actions">
                <el-button text :icon="Refresh" size="small" :loading="hotSearchLoading" @click="doRefreshHotSearch">
                  刷新
                </el-button>
                <span v-if="lastRefreshTime" class="refresh-time">
                  {{ formatRefreshTime(lastRefreshTime) }}
                </span>
              </div>
            </div>
          </template>
          <el-table :data="hotSearches" :show-header="false" height="350" size="small">
            <el-table-column width="45">
              <template #default="{ $index }">
                <el-tag
                  :type="$index < 3 ? 'danger' : 'info'"
                  size="small"
                  class="rank-tag"
                >
                  {{ $index + 1 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column>
              <template #default="{ row }">
                <div class="hotsearch-item" @click="handleHotSearchClick(row)">
                  <div class="item-title">
                    {{ row.title }}
                    <el-tag v-if="row.isNew" type="danger" size="small">新</el-tag>
                  </div>
                  <div class="item-meta">
                    <span class="heat-value">{{ formatHeat(row.heat) }}</span>
                    <el-tag :type="getSentimentType(row.sentiment)" size="small">
                      {{ getSentimentLabel(row.sentiment) }}
                    </el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column width="50">
              <template #default="{ row }">
                <el-icon :color="row.trend === 'up' ? '#67c23a' : '#f56c6c'" :size="16">
                  <component :is="row.trend === 'up' ? CaretTop : CaretBottom" />
                </el-icon>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 动态词云图 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>话题词云</span>
              <div class="header-actions">
                <el-button-group size="small">
                  <el-button :icon="Refresh" @click="refreshWordcloud">刷新</el-button>
                  <el-button :icon="Download" @click="downloadWordcloud">下载</el-button>
                  <el-button :icon="Setting" @click="showSettings = true">设置</el-button>
                </el-button-group>
              </div>
            </div>
          </template>
          <div ref="wordcloudRef" style="height: 350px"></div>
          <div class="wordcloud-controls">
            <el-select v-model="wordcloudShape" style="width: 100px" size="small" @change="updateWordcloud">
              <el-option label="圆形" value="circle" />
              <el-option label="矩形" value="rect" />
              <el-option label="心形" value="heart" />
              <el-option label="星形" value="star" />
            </el-select>
            <el-color-picker v-model="wordcloudColor" size="small" @change="updateWordcloud" />
            <el-switch v-model="wordcloudAnimation" active-text="动画" size="small" @change="updateWordcloud" />
          </div>
        </el-card>
      </el-col>

      <!-- 右侧列：双维度排序组件（核心创新点） -->
      <el-col :span="12">
        <el-card class="dual-dimension-card">
          <template #header>
            <div class="card-header innovation-header">
              <div class="header-title">
                <el-icon><TrendCharts /></el-icon>
                <span>情感-热度双维度排序</span>
                <el-tag type="success" size="small" effect="plain">核心创新点</el-tag>
              </div>
              <p class="header-desc">
                综合得分 = α × 情感强度 + β × 传播热度，实现舆情话题的智能排序
              </p>
            </div>
          </template>
          <!-- 集成双维度排序组件 -->
          <DualDimensionRanking 
            @config-change="onDualDimensionConfigChange"
            @topic-select="onTopicSelect"
          />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 词云设置对话框 -->
    <el-dialog v-model="showSettings" title="词云设置" width="500px">
      <el-form label-width="100px">
        <el-form-item label="最大词数">
          <el-input-number v-model="wordcloudSettings.maxWords" :min="50" :max="500" />
        </el-form-item>
        <el-form-item label="最小字号">
          <el-input-number v-model="wordcloudSettings.minFontSize" :min="12" :max="30" />
        </el-form-item>
        <el-form-item label="最大字号">
          <el-input-number v-model="wordcloudSettings.maxFontSize" :min="40" :max="120" />
        </el-form-item>
        <el-form-item label="旋转角度">
          <el-slider v-model="wordcloudSettings.rotation" :max="90" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="applySettings">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { ElMessage, ElNotification } from 'element-plus';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import { Refresh, Download, Setting, CaretTop, CaretBottom, TrendCharts, Connection } from '@element-plus/icons-vue';
import { useWeiboStore } from '@/store/weibo';
import { useTopicsStore } from '@/store/topics';
import DualDimensionRanking from '@/components/topics/DualDimensionRanking.vue';
import useConnectivityMonitor from '@/composables/useConnectivityMonitor';
import type { RankedTopic, DualDimensionConfig } from '@/api/topics';

// Store
const weiboStore = useWeiboStore();
const topicsStore = useTopicsStore();

// 连通性监控
const { 
  status: connectivityStatus, 
  checking: connectivityChecking,
  overallConnectivity,
  connectivityTagType,
  connectivityText,
  connectivitySummary,
  checkConnectivity
} = useConnectivityMonitor();

// 从store获取响应式状态
const { hotSearches, lastRefreshTime, isLoading: hotSearchLoading, wordcloudDataFromHotSearch } = storeToRefs(weiboStore);
const { rankedTopics } = storeToRefs(topicsStore);

// 自动刷新定时器
let autoRefreshTimer: number | null = null;

// 加载真实热搜数据（通过store从微博实时爬取）
const loadHotSearch = async () => {
  try {
    await weiboStore.fetchHotSearch();
    
    // 如果成功获取热搜，更新词云数据
    if (hotSearches.value.length > 0) {
      updateWordcloudFromHotSearch();
      
      // 显示成功通知
      ElNotification({
        title: '热搜已更新',
        message: `获取到 ${hotSearches.value.length} 条实时热搜`,
        type: 'success',
        duration: 2000,
      });
    }
  } catch (error: any) {
    console.error('加载热搜失败:', error);
    ElMessage.warning('获取热搜失败: ' + (error.message || '请检查后端服务是否启动'));
  }
};

// 启动自动刷新
const startAutoRefresh = () => {
  // 每60秒自动刷新
  autoRefreshTimer = window.setInterval(() => {
    loadHotSearch();
  }, 60000);
};

// 停止自动刷新
const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
};

// 从热搜更新词云数据（使用store中的计算属性）
const updateWordcloudFromHotSearch = () => {
  if (wordcloudDataFromHotSearch.value.length > 0) {
    // 使用store中计算好的词云数据
    wordcloudData.length = 0;
    wordcloudDataFromHotSearch.value.forEach(item => {
      wordcloudData.push(item);
    });
    updateWordcloud();
  }
};

// 词云配置
const wordcloudRef = ref<HTMLElement>();
const wordcloudShape = ref('circle');
const wordcloudColor = ref('#409EFF');
const wordcloudAnimation = ref(true);
const showSettings = ref(false);

const wordcloudSettings = reactive({
  maxWords: 200,
  minFontSize: 14,
  maxFontSize: 80,
  rotation: 45,
});

let wordcloudChart: echarts.ECharts | null = null;

// 词云数据（响应式数组，从热搜动态生成）
const wordcloudData: { name: string; value: number }[] = reactive([]);

// 工具函数
const formatHeat = (heat: number) => {
  if (heat >= 10000000) return (heat / 10000000).toFixed(1) + '千万';
  if (heat >= 10000) return (heat / 10000).toFixed(1) + '万';
  return heat.toString();
};

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

// 初始化词云
const initWordcloud = () => {
  if (!wordcloudRef.value) return;
  
  wordcloudChart = echarts.init(wordcloudRef.value);
  updateWordcloud();
};

// 更新词云
const updateWordcloud = () => {
  if (!wordcloudChart) return;
  
  const maskImage = new Image();
  const shapes: Record<string, string> = {
    circle: 'circle',
    rect: 'rect',
    star: 'star',
    heart: 'heart',
  };
  
  wordcloudChart.setOption({
    tooltip: {
      show: true,
      formatter: (params: any) => {
        return `${params.name}: ${params.value}`;
      },
    },
    series: [{
      type: 'wordCloud',
      shape: shapes[wordcloudShape.value] || 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      right: null,
      bottom: null,
      sizeRange: [wordcloudSettings.minFontSize, wordcloudSettings.maxFontSize],
      rotationRange: [-wordcloudSettings.rotation, wordcloudSettings.rotation],
      rotationStep: 45,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: wordcloudAnimation.value,
      textStyle: {
        fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
        fontWeight: 'bold',
        color: () => {
          const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'];
          return colors[Math.floor(Math.random() * colors.length)];
        },
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          textShadowBlur: 10,
          textShadowColor: '#333',
        },
      },
      data: wordcloudData,
    }],
  });
  
  // 点击事件
  wordcloudChart.on('click', (params: any) => {
    ElMessage.info(`点击了词语: ${params.name}`);
  });
};

// 双维度排序配置变更事件处理
const onDualDimensionConfigChange = (config: DualDimensionConfig) => {
  ElMessage.success(`配置已更新: 情感权重=${(config.sentiment_weight * 100).toFixed(0)}%, 热度权重=${(config.popularity_weight * 100).toFixed(0)}%`);
};

// 话题选择事件处理
const onTopicSelect = (topic: RankedTopic) => {
  ElMessage.info(`选择话题: ${topic.name}`);
  // 可以在这里添加更多交互逻辑，如显示话题详情
};

const refreshWordcloud = () => {
  ElMessage.success('词云已刷新');
  initWordcloud();
};

const downloadWordcloud = () => {
  if (!wordcloudChart) return;
  const url = wordcloudChart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff',
  });
  const link = document.createElement('a');
  link.href = url;
  link.download = '词云图.png';
  link.click();
  ElMessage.success('词云图已下载');
};

const doRefreshHotSearch = async () => {
  try {
    // 通过store强制刷新（重新从微博爬取）
    await weiboStore.forceRefreshHotSearch();
    updateWordcloudFromHotSearch();
    ElMessage.success('热搜已刷新');
  } catch (error: any) {
    console.error('刷新热搜失败:', error);
    ElMessage.warning('刷新失败: ' + (error.message || '请检查后端服务'));
  }
};

const handleHotSearchClick = (item: any) => {
  ElMessage.info(`查看热搜: ${item.title}`);
};

const applySettings = () => {
  updateWordcloud();
  showSettings.value = false;
  ElMessage.success('设置已应用');
};

// 格式化刷新时间
const formatRefreshTime = (timeStr: string) => {
  if (!timeStr) return '';
  try {
    const date = new Date(timeStr);
    return `更新于 ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return '';
  }
};

// 生命周期
onMounted(async () => {
  initWordcloud();
  
  // 启动后端热搜服务
  try {
    await weiboStore.startHotSearch(60);
  } catch (e) {
    console.warn('启动热搜服务失败，将直接获取数据');
  }
  
  // 加载真实热搜数据
  await loadHotSearch();
  
  // 启动前端自动刷新
  startAutoRefresh();
  
  window.addEventListener('resize', () => {
    wordcloudChart?.resize();
  });
});

onUnmounted(() => {
  // 停止自动刷新
  stopAutoRefresh();
  
  wordcloudChart?.dispose();
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.hot-topics-module {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
    font-size: 22px;
    color: #303133;
  }
  
  .header-badges {
    display: flex;
    align-items: center;
    gap: 12px;
    
    :deep(.el-tag) {
      font-size: 14px;
      padding: 8px 16px;
      
      .el-icon {
        margin-right: 6px;
      }
    }
    
    .connectivity-tag {
      cursor: pointer;
      font-size: 12px;
      padding: 4px 10px;
      
      &:hover {
        opacity: 0.8;
      }
    }
  }
}

.mb-4 {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .refresh-time {
    font-size: 12px;
    color: var(--color-text-secondary);
  }
}

.innovation-header {
  flex-direction: column;
  align-items: flex-start;
  
  .header-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: bold;
    
    .el-icon {
      color: var(--color-success);
    }
  }
  
  .header-desc {
    margin: 8px 0 0;
    font-size: 13px;
    color: var(--color-text-secondary);
    font-weight: normal;
  }
}

.dual-dimension-card {
  :deep(.el-card__body) {
    padding: 0;
  }
}

.wordcloud-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  padding-top: 12px;
  margin-top: 12px;
  border-top: 1px solid #ebeef5;
  gap: 12px;
}

.topic-list {
  max-height: 500px;
  overflow-y: auto;
}

.topic-item {
  padding: $spacing-sm;
  margin-bottom: $spacing-xs;
  border-radius: $border-radius-base;
  cursor: pointer;
  transition: $transition-fast;
  border: 1px solid transparent;
  
  &:hover {
    background: $bg-hover;
    border-color: $primary-color;
  }
  
  &.active {
    background: rgba(64, 158, 255, 0.1);
    border-color: $primary-color;
  }
  
  .topic-name {
    margin-bottom: $spacing-xs;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }
  
  .topic-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: $spacing-xs;
    font-size: $font-size-small;
    color: $text-secondary;
  }
}

.hotsearch-header {
  margin-bottom: $spacing-sm;
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .refresh-time {
    font-size: 12px;
    color: var(--color-text-secondary);
  }
}

.hotsearch-item {
  cursor: pointer;
  padding: $spacing-xs 0;
  
  .item-title {
    font-size: $font-size-base;
    color: $text-primary;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
    
    &:hover {
      color: $primary-color;
    }
  }
  
  .item-meta {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-small;
    
    .heat-value {
      color: $text-secondary;
    }
  }
}

.rank-tag {
  font-weight: $font-weight-bold;
}

// 响应式
@media (max-width: 1400px) {
  .left-panel,
  .right-panel {
    width: 25%;
  }
}

@media (max-width: 1200px) {
  .topics-layout {
    flex-direction: column;
  }
  
  .left-panel,
  .right-panel,
  .center-panel {
    width: 100%;
    height: auto;
  }
}
</style>

<style scoped>
.hot-topics-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 15px;
}

/* 卡片样式 */
.wordcloud-card,
.hotsearch-card,
.monitor-card,
.modeling-card,
.spread-card,
.prediction-card,
.topics-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.header-filters {
  display: flex;
  gap: 10px;
}

/* 热搜列表 */
.hotsearch-list {
  padding: 0 10px;
}

.hotsearch-item {
  display: flex;
  align-items: flex-start;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;
}

.hotsearch-item:hover {
  background: #f5f7fa;
}

.hotsearch-item:last-child {
  border-bottom: none;
}

.rank {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  margin-right: 12px;
  background: var(--color-text-secondary);
  color: #fff;
}

.rank-1 { background: var(--color-danger); }
.rank-2 { background: var(--color-warning); }
.rank-3 { background: #f4e04d; color: #333; }

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.heat {
  color: var(--color-text-secondary);
}

/* 话题表格 */
.topic-name {
  cursor: pointer;
}

.topic-name:hover {
  color: var(--color-primary);
}

.topic-keywords {
  margin-top: 5px;
  display: flex;
  gap: 5px;
}

.heat-cell {
  display: flex;
  flex-direction: column;
}

.heat-value {
  font-weight: 500;
}

.heat-trend {
  font-size: 12px;
}

.heat-trend.up { color: var(--color-success); }
.heat-trend.down { color: var(--color-danger); }

.pagination-wrapper {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}

/* 话题详情 */
.topic-detail,
.word-detail {
  padding: 10px 0;
}

.detail-section {
  margin-top: 20px;
}

.detail-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.opinions-list {
  max-height: 300px;
  overflow-y: auto;
}

.opinion-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
}

.opinion-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  margin-bottom: 8px;
}

.opinion-meta {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 词语详情 */
.sentiment-bars {
  padding: 10px 0;
}

.bar-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.bar-label {
  width: 40px;
  font-size: 13px;
  color: #606266;
}

.bar-item :deep(.el-progress) {
  flex: 1;
}

.related-words {
  padding: 10px 0;
}

.text-success { color: var(--color-success); }
.text-danger { color: var(--color-danger); }
</style>
