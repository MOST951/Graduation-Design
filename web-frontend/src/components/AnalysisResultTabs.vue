<template>
  <div class="analysis-result-tabs">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: 微博情感列表 -->
      <el-tab-pane label="微博情感列表" name="list">
        <div class="tab-toolbar">
          <div class="toolbar-left">
            <el-select v-model="listFilter.sentiment" placeholder="情感筛选" clearable style="width: 120px;">
              <el-option label="全部" value="" />
              <el-option label="正面" value="positive" />
              <el-option label="中性" value="neutral" />
              <el-option label="负面" value="negative" />
            </el-select>
            <el-select v-model="listFilter.confidence" placeholder="置信度" clearable style="width: 120px;">
              <el-option label="全部" value="" />
              <el-option label="高 (≥90%)" value="high" />
              <el-option label="中 (70-90%)" value="medium" />
              <el-option label="低 (<70%)" value="low" />
            </el-select>
            <el-input v-model="listFilter.keyword" placeholder="搜索内容" clearable style="width: 200px;">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </div>
          <div class="toolbar-right">
            <el-button size="small" :disabled="selectedRows.length === 0" @click="handleBatchMark">
              <el-icon><Star /></el-icon> 批量标记
            </el-button>
            <el-button size="small" type="primary" @click="handleExportList">
              <el-icon><Download /></el-icon> 导出
            </el-button>
          </div>
        </div>

        <el-table
          :data="filteredListData"
          style="width: 100%"
          max-height="500"
          @selection-change="handleSelectionChange"
          @sort-change="handleSortChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="id" label="ID" width="80" sortable />
          <el-table-column prop="content" label="内容" min-width="300">
            <template #default="{ row }">
              <el-tooltip :content="row.content" placement="top" :show-after="500">
                <span class="content-cell">{{ truncate(row.content, 50) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="sentiment" label="情感" width="100" sortable>
            <template #default="{ row }">
              <el-tag :type="getSentimentType(row.sentiment)" size="small">{{ row.sentimentLabel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="120" sortable>
            <template #default="{ row }">
              <el-progress :percentage="row.confidence" :stroke-width="6" :color="getConfidenceColor(row.confidence)">
                <span class="confidence-text">{{ row.confidence }}%</span>
              </el-progress>
            </template>
          </el-table-column>
          <el-table-column prop="intensity" label="强度" width="100" sortable>
            <template #default="{ row }">
              <el-rate v-model="row.intensity" disabled :max="5" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="150" sortable />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
              <el-button type="warning" link size="small" @click="markSample(row)">标记</el-button>
              <el-button type="success" link size="small" @click="exportRow(row)">导出</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="listPagination.page"
            v-model:page-size="listPagination.size"
            :total="listData.length"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </el-tab-pane>

      <!-- Tab 2: 样本标注 -->
      <el-tab-pane label="样本标注" name="annotation">
        <div class="annotation-container">
          <!-- 左侧：未标注样本列表 -->
          <div class="annotation-left">
            <div class="annotation-header">
              <span>未标注样本</span>
              <el-tag type="info">{{ unlabeledSamples.length }} 条待标注</el-tag>
            </div>
            <el-scrollbar height="450px">
              <div
                v-for="(sample, index) in unlabeledSamples"
                :key="sample.id"
                :class="['sample-item', { active: currentSampleIndex === index }]"
                @click="selectSample(index)"
              >
                <div class="sample-index">#{{ index + 1 }}</div>
                <div class="sample-content">{{ truncate(sample.content, 60) }}</div>
                <div class="sample-meta">
                  <span>{{ sample.source }}</span>
                  <span>{{ sample.time }}</span>
                </div>
              </div>
            </el-scrollbar>
          </div>

          <!-- 右侧：标注面板 -->
          <div class="annotation-right">
            <div class="annotation-header">
              <span>标注面板</span>
              <el-tag>{{ labeledCount }} / {{ totalSamples }} 已标注</el-tag>
            </div>

            <div v-if="currentSample" class="annotation-panel">
              <div class="current-content">
                <div class="content-label">当前样本内容：</div>
                <div class="content-text">{{ currentSample.content }}</div>
              </div>

              <div class="label-section">
                <div class="label-title">选择情感标签：</div>
                <div class="label-buttons">
                  <el-button
                    v-for="label in sentimentLabels"
                    :key="label.value"
                    :type="selectedLabel === label.value ? 'primary' : 'default'"
                    :class="['label-btn', label.class]"
                    @click="selectedLabel = label.value"
                  >
                    <el-icon><component :is="label.icon" /></el-icon>
                    {{ label.name }}
                  </el-button>
                </div>
              </div>

              <div class="intensity-section">
                <div class="label-title">情感强度：</div>
                <el-slider v-model="selectedIntensity" :min="1" :max="5" :step="1" show-stops :marks="intensityMarks" />
              </div>

              <div class="note-section">
                <div class="label-title">备注（可选）：</div>
                <el-input v-model="annotationNote" type="textarea" :rows="2" placeholder="添加标注备注..." />
              </div>

              <div class="annotation-actions">
                <el-button @click="skipSample">
                  <el-icon><Right /></el-icon> 跳过
                </el-button>
                <el-button type="primary" :disabled="!selectedLabel" @click="submitAnnotation">
                  <el-icon><Check /></el-icon> 提交标注
                </el-button>
              </div>
            </div>

            <el-empty v-else description="请从左侧选择样本" />

            <div class="annotation-footer">
              <el-button type="success" @click="exportAnnotations">
                <el-icon><Download /></el-icon> 导出标注数据
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 模型评估 -->
      <el-tab-pane label="模型评估" name="evaluation">
        <el-row :gutter="20">
          <!-- 混淆矩阵 -->
          <el-col :span="12">
            <el-card shadow="hover">
              <template #header>混淆矩阵</template>
              <div id="confusion-matrix" style="width: 100%; height: 300px;"></div>
            </el-card>
          </el-col>

          <!-- 评估指标 -->
          <el-col :span="12">
            <el-card shadow="hover">
              <template #header>评估指标</template>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-value">{{ evaluationMetrics.accuracy }}%</div>
                  <div class="metric-label">准确率 (Accuracy)</div>
                  <el-progress :percentage="evaluationMetrics.accuracy" :stroke-width="8" :show-text="false" color="#67c23a" />
                </div>
                <div class="metric-item">
                  <div class="metric-value">{{ evaluationMetrics.precision }}%</div>
                  <div class="metric-label">精确率 (Precision)</div>
                  <el-progress :percentage="evaluationMetrics.precision" :stroke-width="8" :show-text="false" color="#409eff" />
                </div>
                <div class="metric-item">
                  <div class="metric-value">{{ evaluationMetrics.recall }}%</div>
                  <div class="metric-label">召回率 (Recall)</div>
                  <el-progress :percentage="evaluationMetrics.recall" :stroke-width="8" :show-text="false" color="#e6a23c" />
                </div>
                <div class="metric-item">
                  <div class="metric-value">{{ evaluationMetrics.f1 }}%</div>
                  <div class="metric-label">F1 分数</div>
                  <el-progress :percentage="evaluationMetrics.f1" :stroke-width="8" :show-text="false" color="#f56c6c" />
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
          <!-- 分类报告 -->
          <el-col :span="12">
            <el-card shadow="hover">
              <template #header>分类报告</template>
              <el-table :data="classificationReport" size="small">
                <el-table-column prop="class" label="类别" width="100" />
                <el-table-column prop="precision" label="精确率" width="100">
                  <template #default="{ row }">{{ row.precision }}%</template>
                </el-table-column>
                <el-table-column prop="recall" label="召回率" width="100">
                  <template #default="{ row }">{{ row.recall }}%</template>
                </el-table-column>
                <el-table-column prop="f1" label="F1" width="100">
                  <template #default="{ row }">{{ row.f1 }}%</template>
                </el-table-column>
                <el-table-column prop="support" label="样本数" width="100" />
              </el-table>
            </el-card>
          </el-col>

          <!-- ROC曲线 -->
          <el-col :span="12">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>ROC 曲线</span>
                  <el-tag type="success" size="small">AUC: {{ evaluationMetrics.auc }}</el-tag>
                </div>
              </template>
              <div id="roc-curve" style="width: 100%; height: 280px;"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 4: 错误分析 -->
      <el-tab-pane label="错误分析" name="errors">
        <el-row :gutter="20">
          <!-- 错误类型统计 -->
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>错误类型分布</template>
              <div id="error-type-chart" style="width: 100%; height: 250px;"></div>
              <div class="error-stats">
                <div class="error-stat-item">
                  <span class="stat-label">假阳性 (FP)</span>
                  <span class="stat-value text-warning">{{ errorStats.falsePositive }}</span>
                </div>
                <div class="error-stat-item">
                  <span class="stat-label">假阴性 (FN)</span>
                  <span class="stat-value text-danger">{{ errorStats.falseNegative }}</span>
                </div>
                <div class="error-stat-item">
                  <span class="stat-label">错误率</span>
                  <span class="stat-value">{{ errorStats.errorRate }}%</span>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 特征重要性 -->
          <el-col :span="16">
            <el-card shadow="hover">
              <template #header>特征重要性分析</template>
              <div id="feature-importance" style="width: 100%; height: 300px;"></div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 错误样本列表 -->
        <el-card shadow="hover" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <span>错误分类样本</span>
              <el-radio-group v-model="errorFilter" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="fp">假阳性</el-radio-button>
                <el-radio-button label="fn">假阴性</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-table :data="filteredErrorSamples" max-height="300">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="content" label="内容" min-width="300">
              <template #default="{ row }">
                <el-tooltip :content="row.content" placement="top">
                  <span>{{ truncate(row.content, 50) }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="trueLabel" label="真实标签" width="100">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.trueLabel)" size="small">{{ row.trueLabelText }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="predictedLabel" label="预测标签" width="100">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.predictedLabel)" size="small">{{ row.predictedLabelText }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="errorType" label="错误类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.errorType === 'FP' ? 'warning' : 'danger'" size="small">{{ row.errorType }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="{ row }">{{ row.confidence }}%</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="analyzeError(row)">分析</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="微博详情" width="600px">
      <div v-if="detailData" class="detail-dialog">
        <div class="detail-content">{{ detailData.content }}</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="情感标签">
            <el-tag :type="getSentimentType(detailData.sentiment)">{{ detailData.sentimentLabel }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ detailData.confidence }}%</el-descriptions-item>
          <el-descriptions-item label="情感强度">
            <el-rate v-model="detailData.intensity" disabled :max="5" />
          </el-descriptions-item>
          <el-descriptions-item label="情感得分">{{ detailData.score?.toFixed(3) }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ detailData.source }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ detailData.time }}</el-descriptions-item>
          <el-descriptions-item label="关键词" :span="2">
            <el-tag v-for="kw in detailData.keywords" :key="kw" size="small" style="margin-right: 5px;">{{ kw }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { Search, Star, Download, Right, Check, Sunny, Cloudy, MostlyCloudy } from '@element-plus/icons-vue';

// Tab 状态
const activeTab = ref('list');

// ==================== Tab 1: 微博情感列表 ====================
const listFilter = reactive({
  sentiment: '',
  confidence: '',
  keyword: '',
});

const listPagination = reactive({
  page: 1,
  size: 10,
});

const selectedRows = ref<any[]>([]);
const sortConfig = reactive({ prop: '', order: '' });

// 模拟数据
const listData = ref(Array.from({ length: 50 }, (_, i) => ({
  id: 1001 + i,
  content: [
    '这个产品真的太棒了，用了之后效果非常好，强烈推荐！',
    '服务态度一般，等了很久才有人回复',
    '价格有点贵，但质量确实不错',
    '太失望了，完全不是想象中的样子',
    '物流很快，包装也很精美，好评！',
    '一般般吧，没有特别惊艳的感觉',
    '客服态度很好，问题解决得很及时',
    '质量有问题，用了两天就坏了',
  ][i % 8],
  sentiment: ['positive', 'neutral', 'positive', 'negative', 'positive', 'neutral', 'positive', 'negative'][i % 8],
  sentimentLabel: ['正面', '中性', '正面', '负面', '正面', '中性', '正面', '负面'][i % 8],
  confidence: Math.floor(Math.random() * 30 + 70),
  intensity: Math.floor(Math.random() * 4 + 1),
  score: (Math.random() * 2 - 1),
  time: `2025-12-${String(10 - Math.floor(i / 10)).padStart(2, '0')} ${String(Math.floor(Math.random() * 24)).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
  source: ['微博', '微信', '抖音'][i % 3],
  keywords: ['产品', '服务', '质量', '价格'].slice(0, Math.floor(Math.random() * 3 + 1)),
})));

const filteredListData = computed(() => {
  let data = [...listData.value];
  
  if (listFilter.sentiment) {
    data = data.filter(d => d.sentiment === listFilter.sentiment);
  }
  if (listFilter.confidence) {
    if (listFilter.confidence === 'high') data = data.filter(d => d.confidence >= 90);
    else if (listFilter.confidence === 'medium') data = data.filter(d => d.confidence >= 70 && d.confidence < 90);
    else data = data.filter(d => d.confidence < 70);
  }
  if (listFilter.keyword) {
    data = data.filter(d => d.content.includes(listFilter.keyword));
  }
  
  if (sortConfig.prop && sortConfig.order) {
    data.sort((a: any, b: any) => {
      const order = sortConfig.order === 'ascending' ? 1 : -1;
      return (a[sortConfig.prop] > b[sortConfig.prop] ? 1 : -1) * order;
    });
  }
  
  const start = (listPagination.page - 1) * listPagination.size;
  return data.slice(start, start + listPagination.size);
});

// ==================== Tab 2: 样本标注 ====================
const unlabeledSamples = ref(Array.from({ length: 20 }, (_, i) => ({
  id: 2001 + i,
  content: [
    '今天心情特别好，阳光明媚！',
    '这个功能太难用了，完全不知道怎么操作',
    '刚收到货，还没拆开，期待中',
    '售后服务真的很差劲，投诉都没人管',
    '性价比很高，推荐购买',
  ][i % 5],
  source: ['微博', '微信', '抖音'][i % 3],
  time: `2025-12-10 ${String(i + 1).padStart(2, '0')}:00`,
})));

const currentSampleIndex = ref(0);
const currentSample = computed(() => unlabeledSamples.value[currentSampleIndex.value]);
const selectedLabel = ref('');
const selectedIntensity = ref(3);
const annotationNote = ref('');
const labeledCount = ref(0);
const totalSamples = computed(() => unlabeledSamples.value.length + labeledCount.value);

const sentimentLabels = [
  { value: 'positive', name: '正面', icon: 'Sunny', class: 'positive' },
  { value: 'neutral', name: '中性', icon: 'Cloudy', class: 'neutral' },
  { value: 'negative', name: '负面', icon: 'MostlyCloudy', class: 'negative' },
];

const intensityMarks = { 1: '弱', 2: '', 3: '中', 4: '', 5: '强' };

// ==================== Tab 3: 模型评估 ====================
const evaluationMetrics = reactive({
  accuracy: 92.5,
  precision: 91.2,
  recall: 89.8,
  f1: 90.5,
  auc: 0.95,
});

const classificationReport = ref([
  { class: '正面', precision: 93.2, recall: 91.5, f1: 92.3, support: 1520 },
  { class: '中性', precision: 88.5, recall: 86.2, f1: 87.3, support: 980 },
  { class: '负面', precision: 91.8, recall: 91.7, f1: 91.7, support: 750 },
  { class: '加权平均', precision: 91.2, recall: 89.8, f1: 90.5, support: 3250 },
]);

// ==================== Tab 4: 错误分析 ====================
const errorFilter = ref('all');
const errorStats = reactive({
  falsePositive: 125,
  falseNegative: 98,
  errorRate: 6.9,
});

const errorSamples = ref(Array.from({ length: 30 }, (_, i) => ({
  id: 3001 + i,
  content: [
    '这个还行吧，没什么特别的感觉',
    '不太满意，但也不是很差',
    '挺好的，就是有点小问题',
  ][i % 3],
  trueLabel: ['positive', 'negative', 'neutral'][i % 3],
  trueLabelText: ['正面', '负面', '中性'][i % 3],
  predictedLabel: ['neutral', 'neutral', 'positive'][i % 3],
  predictedLabelText: ['中性', '中性', '正面'][i % 3],
  errorType: i % 2 === 0 ? 'FP' : 'FN',
  confidence: Math.floor(Math.random() * 20 + 60),
})));

const filteredErrorSamples = computed(() => {
  if (errorFilter.value === 'all') return errorSamples.value;
  return errorSamples.value.filter(s => s.errorType === errorFilter.value.toUpperCase());
});

// ==================== 弹窗 ====================
const detailDialogVisible = ref(false);
const detailData = ref<any>(null);

// ==================== 图表 ====================
let confusionMatrix: echarts.ECharts | null = null;
let rocCurve: echarts.ECharts | null = null;
let errorTypeChart: echarts.ECharts | null = null;
let featureImportance: echarts.ECharts | null = null;

function initConfusionMatrix() {
  const dom = document.getElementById('confusion-matrix');
  if (!dom) return;

  confusionMatrix = echarts.init(dom);
  const labels = ['正面', '中性', '负面'];
  const data = [
    [1390, 85, 45],
    [70, 845, 65],
    [35, 50, 665],
  ];

  const heatmapData: [number, number, number][] = [];
  data.forEach((row, i) => {
    row.forEach((val, j) => {
      heatmapData.push([j, i, val]);
    });
  });

  confusionMatrix.setOption({
    tooltip: { formatter: (params: any) => `预测: ${labels[params.data[0]]}<br/>实际: ${labels[params.data[1]]}<br/>数量: ${params.data[2]}` },
    grid: { left: '15%', right: '10%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: labels, name: '预测', nameLocation: 'center', nameGap: 30 },
    yAxis: { type: 'category', data: labels, name: '实际', nameLocation: 'center', nameGap: 40 },
    visualMap: { min: 0, max: 1500, calculable: true, orient: 'vertical', right: 0, top: 'center', inRange: { color: ['#f5f5f5', '#67c23a'] } },
    series: [{
      type: 'heatmap',
      data: heatmapData,
      label: { show: true, fontSize: 14, fontWeight: 'bold' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
    }],
  });
}

function initRocCurve() {
  const dom = document.getElementById('roc-curve');
  if (!dom) return;

  rocCurve = echarts.init(dom);
  const rocData = [[0, 0], [0.05, 0.4], [0.1, 0.6], [0.15, 0.72], [0.2, 0.8], [0.3, 0.88], [0.4, 0.92], [0.6, 0.96], [0.8, 0.98], [1, 1]];

  rocCurve.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'value', name: 'FPR', min: 0, max: 1 },
    yAxis: { type: 'value', name: 'TPR', min: 0, max: 1 },
    series: [
      { type: 'line', data: rocData, smooth: true, areaStyle: { color: 'rgba(64, 158, 255, 0.2)' }, itemStyle: { color: '#409eff' } },
      { type: 'line', data: [[0, 0], [1, 1]], lineStyle: { type: 'dashed', color: '#909399' }, symbol: 'none' },
    ],
  });
}

function initErrorTypeChart() {
  const dom = document.getElementById('error-type-chart');
  if (!dom) return;

  errorTypeChart = echarts.init(dom);
  errorTypeChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: errorStats.falsePositive, name: '假阳性 (FP)', itemStyle: { color: '#e6a23c' } },
        { value: errorStats.falseNegative, name: '假阴性 (FN)', itemStyle: { color: '#f56c6c' } },
      ],
      label: { formatter: '{b}\n{c} ({d}%)' },
    }],
  });
}

function initFeatureImportance() {
  const dom = document.getElementById('feature-importance');
  if (!dom) return;

  featureImportance = echarts.init(dom);
  const features = ['情感词', '否定词', '程度副词', '表情符号', '句子长度', '标点符号', '主题词', '用户特征'];
  const importance = [0.28, 0.22, 0.15, 0.12, 0.08, 0.06, 0.05, 0.04];

  featureImportance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '20%', right: '10%', top: '10%', bottom: '10%' },
    xAxis: { type: 'value', name: '重要性', max: 0.35 },
    yAxis: { type: 'category', data: features.reverse() },
    series: [{
      type: 'bar',
      data: importance.reverse().map((v, i) => ({ value: v, itemStyle: { color: `hsl(${200 - i * 20}, 70%, 50%)` } })),
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  });
}

// ==================== 方法 ====================
function truncate(text: string, length: number) {
  return text.length > length ? text.slice(0, length) + '...' : text;
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger', '正面': 'success', '中性': 'info', '负面': 'danger' };
  return map[sentiment] || 'info';
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 90) return '#67c23a';
  if (confidence >= 70) return '#e6a23c';
  return '#f56c6c';
}

function handleSelectionChange(rows: any[]) {
  selectedRows.value = rows;
}

function handleSortChange({ prop, order }: any) {
  sortConfig.prop = prop;
  sortConfig.order = order;
}

function showDetail(row: any) {
  detailData.value = row;
  detailDialogVisible.value = true;
}

function markSample(row: any) {
  activeTab.value = 'annotation';
  ElMessage.info(`已跳转到标注页面，请标注样本 #${row.id}`);
}

function exportRow(row: any) {
  ElMessage.success(`已导出样本 #${row.id}`);
}

function handleBatchMark() {
  ElMessage.info(`已选择 ${selectedRows.value.length} 条样本进行批量标记`);
}

function handleExportList() {
  ElMessage.success('正在导出列表数据...');
}

function selectSample(index: number) {
  currentSampleIndex.value = index;
  selectedLabel.value = '';
  selectedIntensity.value = 3;
  annotationNote.value = '';
}

function submitAnnotation() {
  if (!selectedLabel.value) return;
  
  unlabeledSamples.value.splice(currentSampleIndex.value, 1);
  labeledCount.value++;
  
  if (currentSampleIndex.value >= unlabeledSamples.value.length) {
    currentSampleIndex.value = Math.max(0, unlabeledSamples.value.length - 1);
  }
  
  selectedLabel.value = '';
  selectedIntensity.value = 3;
  annotationNote.value = '';
  
  ElMessage.success('标注已提交');
}

function skipSample() {
  if (currentSampleIndex.value < unlabeledSamples.value.length - 1) {
    currentSampleIndex.value++;
  } else {
    currentSampleIndex.value = 0;
  }
  selectedLabel.value = '';
}

function exportAnnotations() {
  ElMessage.success(`已导出 ${labeledCount.value} 条标注数据`);
}

function analyzeError(row: any) {
  ElMessage.info(`分析错误样本 #${row.id}`);
}

// 监听 Tab 切换
watch(activeTab, (tab) => {
  nextTick(() => {
    if (tab === 'evaluation') {
      initConfusionMatrix();
      initRocCurve();
    } else if (tab === 'errors') {
      initErrorTypeChart();
      initFeatureImportance();
    }
  });
});

// 生命周期
onMounted(() => {
  if (activeTab.value === 'evaluation') {
    nextTick(() => {
      initConfusionMatrix();
      initRocCurve();
    });
  }
});
</script>

<style scoped>
.analysis-result-tabs {
  background: #fff;
  border-radius: 8px;
}

/* 工具栏 */
.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.toolbar-left, .toolbar-right {
  display: flex;
  gap: 10px;
}

/* 表格 */
.content-cell {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.confidence-text {
  font-size: 12px;
}

.pagination-wrapper {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}

/* 标注界面 */
.annotation-container {
  display: flex;
  gap: 20px;
  min-height: 500px;
}

.annotation-left {
  width: 350px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.annotation-right {
  flex: 1;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.annotation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #f5f7fa;
  font-weight: bold;
}

.sample-item {
  padding: 12px 15px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;
}
.sample-item:hover {
  background: #f5f7fa;
}
.sample-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.sample-index {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.sample-content {
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
}

.sample-meta {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.annotation-panel {
  flex: 1;
  padding: 20px;
}

.current-content {
  margin-bottom: 20px;
}

.content-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.content-text {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  line-height: 1.8;
  font-size: 14px;
}

.label-section, .intensity-section, .note-section {
  margin-bottom: 20px;
}

.label-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 10px;
}

.label-buttons {
  display: flex;
  gap: 10px;
}

.label-btn {
  flex: 1;
}
.label-btn.positive:hover { border-color: #67c23a; color: #67c23a; }
.label-btn.neutral:hover { border-color: #909399; color: #909399; }
.label-btn.negative:hover { border-color: #f56c6c; color: #f56c6c; }

.annotation-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.annotation-footer {
  padding: 15px;
  border-top: 1px solid #ebeef5;
  text-align: center;
}

/* 评估指标 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  padding: 10px;
}

.metric-item {
  text-align: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.metric-item .metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.metric-item .metric-label {
  font-size: 12px;
  color: #909399;
  margin: 8px 0;
}

/* 错误统计 */
.error-stats {
  display: flex;
  justify-content: space-around;
  padding: 15px 0;
  border-top: 1px solid #ebeef5;
}

.error-stat-item {
  text-align: center;
}

.error-stat-item .stat-label {
  font-size: 12px;
  color: #909399;
}

.error-stat-item .stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 详情弹窗 */
.detail-dialog .detail-content {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 15px;
  line-height: 1.8;
}
</style>
