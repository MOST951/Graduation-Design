<template>
  <div class="sentiment-analysis-module">
    <!-- 顶部控制栏 -->
    <div class="control-bar">
      <el-form :inline="true" class="control-form">
        <el-form-item label="模型选择">
          <el-select v-model="model" style="width: 150px">
            <el-option label="SVM" value="svm" />
            <el-option label="LSTM" value="lstm" />
            <el-option label="BERT" value="bert" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="情感粒度">
          <el-radio-group v-model="granularity">
            <el-radio-button label="binary">二分类</el-radio-button>
            <el-radio-button label="ternary">三分类</el-radio-button>
            <el-radio-button label="fine">细粒度</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 280px"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" :icon="DataAnalysis" :loading="analyzing" @click="handleAnalyze">
            开始分析
          </el-button>
          <el-button :icon="Download" @click="handleExport">导出</el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 卡片网格主内容区 -->
    <div class="card-grid">
      <!-- 第一行 -->
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card header="情感分布" class="chart-card">
            <div ref="pieChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card header="趋势分析" class="chart-card">
            <div ref="trendChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card header="强度分析" class="chart-card">
            <div ref="heatmapChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 第二行 -->
      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card header="详细结果" class="table-card">
            <el-table :data="resultData" height="300" @row-click="handleRowClick">
              <el-table-column prop="content" label="内容" show-overflow-tooltip />
              <el-table-column prop="sentiment" label="情感" width="100">
                <template #default="{ row }">
                  <el-tag :type="getSentimentType(row.sentiment)" size="small">
                    {{ row.sentiment }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="confidence" label="置信度" width="100">
                <template #default="{ row }">
                  <el-progress :percentage="row.confidence" :show-text="false" />
                  <span style="font-size: 12px">{{ row.confidence }}%</span>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="totalCount"
              layout="prev, pager, next"
              small
              style="margin-top: 12px; text-align: right"
            />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card header="模型评估" class="metric-card">
            <div class="metric-item">
              <el-statistic title="准确率" :value="metrics.accuracy" suffix="%" />
            </div>
            <div class="metric-item">
              <el-statistic title="召回率" :value="metrics.recall" suffix="%" />
            </div>
            <div class="metric-item">
              <el-statistic title="F1分数" :value="metrics.f1Score" suffix="%" />
            </div>
            <el-divider />
            <div class="confusion-matrix">
              <div class="matrix-title">混淆矩阵</div>
              <el-table :data="confusionMatrix" size="small" :show-header="false">
                <el-table-column prop="label" width="60" />
                <el-table-column prop="positive" align="center" />
                <el-table-column prop="negative" align="center" />
              </el-table>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card header="样本标注" class="annotation-card">
            <el-alert
              title="标注进度"
              :description="`已标注: ${annotated} / ${totalSamples}`"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            />
            <el-button type="primary" :icon="Edit" block @click="showAnnotationDialog = true">
              快速标注
            </el-button>
            <el-button :icon="Upload" block @click="handleBatchAnnotation">
              批量标注
            </el-button>
            <el-button :icon="Download" block @click="handleExportAnnotations">
              导出标注
            </el-button>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 底部状态栏 -->
    <div class="status-bar">
      <span>总计：{{ totalCount }}条</span>
      <el-divider direction="vertical" />
      <span>正面：{{ positiveRate }}%</span>
      <el-divider direction="vertical" />
      <span>中性：{{ neutralRate }}%</span>
      <el-divider direction="vertical" />
      <span>负面：{{ negativeRate }}%</span>
      <el-divider direction="vertical" />
      <span>分析时间：{{ analysisTime }}s</span>
    </div>
    
    <!-- 标注对话框 -->
    <el-dialog v-model="showAnnotationDialog" title="快速标注" width="600px">
      <div v-if="currentSample" class="annotation-content">
        <el-alert :title="currentSample.content" type="info" :closable="false" />
        <el-radio-group v-model="annotationLabel" style="margin-top: 16px">
          <el-radio label="positive">正面</el-radio>
          <el-radio label="neutral">中性</el-radio>
          <el-radio label="negative">负面</el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="showAnnotationDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveAnnotation">保存</el-button>
        <el-button type="success" @click="handleNextSample">下一条</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { DataAnalysis, Download, Edit, Upload } from '@element-plus/icons-vue';
import { initChart, getPieChartOption, getLineChartOption } from '@/utils/echarts-config';

// 控制栏状态
const model = ref('bert');
const granularity = ref('ternary');
const dateRange = ref<[Date, Date] | null>(null);
const analyzing = ref(false);

// 分页
const currentPage = ref(1);
const pageSize = ref(10);
const totalCount = ref(1000);

// 分析结果数据
const resultData = ref([
  { id: 1, content: '这个产品真的太棒了，用了之后效果非常好！', sentiment: '正面', confidence: 92 },
  { id: 2, content: '服务态度很差，等了半天都没人理', sentiment: '负面', confidence: 88 },
  { id: 3, content: '今天天气不错，出去逛了逛街', sentiment: '中性', confidence: 75 },
  { id: 4, content: '新功能上线了，体验还可以', sentiment: '正面', confidence: 78 },
  { id: 5, content: '价格太贵了，性价比不高', sentiment: '负面', confidence: 85 },
]);

// 模型评估指标
const metrics = ref({
  accuracy: 88.5,
  recall: 85.2,
  f1Score: 86.8,
});

// 混淆矩阵
const confusionMatrix = ref([
  { label: '正面', positive: 850, negative: 50 },
  { label: '负面', positive: 100, negative: 800 },
]);

// 标注相关
const showAnnotationDialog = ref(false);
const annotated = ref(450);
const totalSamples = ref(1000);
const currentSample = ref({ content: '这是一个待标注的样本文本' });
const annotationLabel = ref('positive');

// 图表引用
const pieChartRef = ref<HTMLElement>();
const trendChartRef = ref<HTMLElement>();
const heatmapChartRef = ref<HTMLElement>();
let pieChart: echarts.ECharts | null = null;
let trendChart: echarts.ECharts | null = null;
let heatmapChart: echarts.ECharts | null = null;

// 计算属性
const positiveRate = computed(() => {
  const positive = resultData.value.filter(d => d.sentiment === '正面').length;
  return ((positive / resultData.value.length) * 100).toFixed(1);
});

const neutralRate = computed(() => {
  const neutral = resultData.value.filter(d => d.sentiment === '中性').length;
  return ((neutral / resultData.value.length) * 100).toFixed(1);
});

const negativeRate = computed(() => {
  const negative = resultData.value.filter(d => d.sentiment === '负面').length;
  return ((negative / resultData.value.length) * 100).toFixed(1);
});

const analysisTime = computed(() => '3.2');

// 工具函数
const getSentimentType = (sentiment: string) => {
  const map: Record<string, any> = {
    '正面': 'success',
    '中性': 'info',
    '负面': 'danger',
  };
  return map[sentiment] || 'info';
};

// 初始化图表
const initCharts = () => {
  nextTick(() => {
    // 情感分布饼图
    if (pieChartRef.value) {
      pieChart = echarts.init(pieChartRef.value);
      pieChart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 10 },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: { show: true, formatter: '{b}\n{d}%' },
          data: [
            { value: 45, name: '正面', itemStyle: { color: '#67c23a' } },
            { value: 31, name: '中性', itemStyle: { color: '#909399' } },
            { value: 24, name: '负面', itemStyle: { color: '#f56c6c' } },
          ],
        }],
      });
    }
    
    // 趋势分析折线图
    if (trendChartRef.value) {
      trendChart = echarts.init(trendChartRef.value);
      trendChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['正面', '中性', '负面'], bottom: 0 },
        xAxis: {
          type: 'category',
          data: ['12/04', '12/05', '12/06', '12/07', '12/08', '12/09', '12/10'],
        },
        yAxis: { type: 'value' },
        series: [
          { name: '正面', type: 'line', smooth: true, data: [320, 450, 380, 520, 480, 550, 620], itemStyle: { color: '#67c23a' } },
          { name: '中性', type: 'line', smooth: true, data: [220, 280, 250, 310, 290, 320, 350], itemStyle: { color: '#909399' } },
          { name: '负面', type: 'line', smooth: true, data: [150, 180, 220, 160, 190, 170, 200], itemStyle: { color: '#f56c6c' } },
        ],
      });
    }
    
    // 强度分析热力图
    if (heatmapChartRef.value) {
      heatmapChart = echarts.init(heatmapChartRef.value);
      heatmapChart.setOption({
        tooltip: { position: 'top' },
        grid: { height: '50%', top: '10%' },
        xAxis: {
          type: 'category',
          data: ['强烈正面', '正面', '弱正面', '中性', '弱负面', '负面', '强烈负面'],
          splitArea: { show: true },
        },
        yAxis: {
          type: 'category',
          data: ['微博', '微信', '抖音'],
          splitArea: { show: true },
        },
        visualMap: {
          min: 0,
          max: 100,
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '15%',
        },
        series: [{
          type: 'heatmap',
          data: [
            [0, 0, 50], [1, 0, 80], [2, 0, 30], [3, 0, 60], [4, 0, 20], [5, 0, 40], [6, 0, 10],
            [0, 1, 45], [1, 1, 75], [2, 1, 35], [3, 1, 55], [4, 1, 25], [5, 1, 45], [6, 1, 15],
            [0, 2, 40], [1, 2, 70], [2, 2, 40], [3, 2, 50], [4, 2, 30], [5, 2, 50], [6, 2, 20],
          ],
          label: { show: true },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        }],
      });
    }
  });
};

// 事件处理函数
const handleAnalyze = () => {
  analyzing.value = true;
  ElMessage.info('开始分析...');
  
  setTimeout(() => {
    analyzing.value = false;
    ElMessage.success('分析完成！');
    initCharts();
  }, 2000);
};

const handleExport = () => {
  ElMessage.success('正在导出报告...');
};

const handleRowClick = (row: any) => {
  ElMessage.info(`查看详情: ${row.content}`);
};

const handleBatchAnnotation = () => {
  ElMessage.info('批量标注功能');
};

const handleExportAnnotations = () => {
  ElMessage.success('导出标注数据');
};

const handleSaveAnnotation = () => {
  ElMessage.success('标注已保存');
  showAnnotationDialog.value = false;
};

const handleNextSample = () => {
  ElMessage.info('加载下一条样本');
};

// 生命周期
onMounted(() => {
  initCharts();
  
  window.addEventListener('resize', () => {
    pieChart?.resize();
    trendChart?.resize();
    heatmapChart?.resize();
  });
});

onUnmounted(() => {
  pieChart?.dispose();
  trendChart?.dispose();
  heatmapChart?.dispose();
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.sentiment-analysis-module {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
}

.control-bar {
  background: $bg-white;
  padding: $spacing-sm $spacing-md;
  border-radius: $border-radius-base;
  margin-bottom: $spacing-sm;
  box-shadow: $box-shadow-base;
  
  .control-form {
    :deep(.el-form-item) {
      margin-bottom: 0;
    }
  }
}

.card-grid {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  
  .chart-card,
  .table-card,
  .metric-card,
  .annotation-card {
    height: 100%;
    box-shadow: $box-shadow-base;
    transition: $transition-base;
    
    &:hover {
      box-shadow: $box-shadow-light;
    }
  }
  
  .metric-card {
    .metric-item {
      margin-bottom: $spacing-sm;
      
      &:last-of-type {
        margin-bottom: 0;
      }
    }
    
    .confusion-matrix {
      .matrix-title {
        font-size: $font-size-base;
        font-weight: $font-weight-medium;
        margin-bottom: $spacing-xs;
        color: $text-primary;
      }
    }
  }
  
  .annotation-card {
    :deep(.el-button) {
      margin-bottom: $spacing-xs;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

.status-bar {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-white;
  margin-top: $spacing-sm;
  border-radius: $border-radius-base;
  box-shadow: $box-shadow-base;
  font-size: $font-size-base;
  color: $text-regular;
  flex-shrink: 0;
  
  span {
    padding: 0 $spacing-xs;
  }
}

.annotation-content {
  :deep(.el-alert) {
    margin-bottom: $spacing-sm;
  }
}

// 响应式
@media (max-width: 1200px) {
  .card-grid {
    :deep(.el-col) {
      margin-bottom: $spacing-sm;
    }
  }
}
</style>
