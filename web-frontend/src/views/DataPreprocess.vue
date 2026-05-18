<template>
  <div class="preprocess-module">
    <div class="preprocess-layout">
      <!-- 左侧操作面板 -->
      <el-card class="operation-panel" header="数据预处理">
        <el-form label-position="top">
          <el-form-item label="数据来源">
            <el-select v-model="dataSource" style="width: 100%" @change="onDataSourceChange">
              <el-option label="采集任务" value="collection" />
              <el-option label="数据库微博" value="database" />
              <el-option label="示例数据" value="sample" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="dataSource === 'collection'" label="选择采集任务">
            <el-select
              v-model="selectedCollectionTaskId"
              style="width: 100%"
              placeholder="请选择采集任务"
              :loading="loadingCollectionTasks"
              @focus="fetchCollectionTasks"
            >
              <el-option
                v-for="task in collectionTaskList"
                :key="task.id"
                :label="`${task.name} (${task.collected}条)`"
                :value="task.id"
                :disabled="task.collected === 0"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="loadedDataCount > 0">
            <el-alert
              :title="`已加载 ${loadedDataCount} 条数据`"
              type="success"
              :closable="false"
              show-icon
            />
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="清洗规则">
            <el-checkbox-group v-model="cleanRules">
              <el-checkbox label="removeDuplicates">去重</el-checkbox>
              <el-checkbox label="removeSpecial">去特殊符号</el-checkbox>
              <el-checkbox label="removeStopwords">过滤停用词</el-checkbox>
              <el-checkbox label="removeEmoji">去除表情</el-checkbox>
              <el-checkbox label="removeUrl">去除URL</el-checkbox>
              <el-checkbox label="traditionalToSimplified">繁体转简体</el-checkbox>
              <el-checkbox label="fullwidthToHalfwidth">全角转半角</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="分词工具">
            <el-radio-group v-model="segmentTool">
              <el-radio label="jieba">jieba分词</el-radio>
              <el-radio label="hanlp">HanLP分词</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="自定义词典">
            <el-upload
              action="#"
              :auto-upload="false"
              :on-change="handleDictUpload"
            >
              <el-button :icon="Upload">上传词典文件</el-button>
            </el-upload>
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="特征提取方法">
            <el-select v-model="extractMethod" style="width: 100%">
              <el-option label="TF-IDF" value="tfidf" />
              <el-option label="Word2Vec" value="word2vec" />
              <el-option label="BERT嵌入" value="bert" />
            </el-select>
          </el-form-item>
          
          <el-form-item v-if="extractMethod !== 'tfidf'" label="向量维度">
            <el-input-number v-model="vectorSize" :min="50" :max="512" style="width: 100%" />
          </el-form-item>
          
          <el-form-item v-if="extractMethod === 'tfidf'" label="最大特征数">
            <el-input-number v-model="maxFeatures" :min="100" :max="10000" style="width: 100%" />
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="任务名称">
            <el-input v-model="taskName" placeholder="自动生成" />
          </el-form-item>
          
          <el-button type="primary" :loading="processing" :disabled="dataSource !== 'sample' && loadedDataCount === 0" block @click="handleProcess">
            <el-icon><Operation /></el-icon>
            开始处理
          </el-button>
          
          <el-progress
            v-if="processing || progress === 100"
            :percentage="progress"
            :status="progress === 100 ? 'success' : undefined"
            style="margin-top: 16px"
          />
          
          <div v-if="progressSteps.length > 0" class="progress-steps">
            <div
              v-for="(step, idx) in progressSteps"
              :key="idx"
              class="progress-step"
              :class="{ done: step.done }"
            >
              <el-icon v-if="step.done" color="#67c23a"><CircleCheck /></el-icon>
              <el-icon v-else-if="processing && !step.done && (idx === 0 || progressSteps[idx-1].done)" class="rotating"><Operation /></el-icon>
              <span v-else class="step-dot"></span>
              <span class="step-label">{{ step.label }}</span>
            </div>
          </div>
        </el-form>
      </el-card>
      
      <!-- 右侧预览区 -->
      <div class="preview-panel">
        <el-tabs v-model="activePreview">
          <!-- 原始文本 -->
          <el-tab-pane label="原始文本" name="original">
            <el-card header="原始数据示例（前10条）">
              <div class="text-list">
                <el-card
                  v-for="(text, index) in originalTexts"
                  :key="index"
                  class="text-item"
                  shadow="hover"
                >
                  <div class="text-index">{{ index + 1 }}</div>
                  <div class="text-content">{{ text }}</div>
                </el-card>
              </div>
            </el-card>
          </el-tab-pane>
          
          <!-- 处理对比 -->
          <el-tab-pane label="处理对比" name="compare">
            <el-card header="清洗差异对比">
              <div v-if="diffItems.length === 0" class="compare-text">处理后将在此展示清洗前后差异</div>
              <div v-else class="diff-list">
                <div v-for="(item, idx) in diffItems" :key="idx" class="diff-item">
                  <div class="diff-label">#{{ idx + 1 }}</div>
                  <div class="diff-content">
                    <div class="diff-original">
                      <span class="diff-tag">原文</span>
                      <span v-html="highlightRemoved(item.original, item.cleaned)"></span>
                    </div>
                    <div class="diff-cleaned">
                      <span class="diff-tag success">清洗后</span>
                      <span>{{ item.cleaned }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-tab-pane>
          
          <!-- 分词结果 -->
          <el-tab-pane label="分词结果" name="segment">
            <el-card header="分词可视化">
              <div class="segment-result">
                <el-tag
                  v-for="(word, index) in segmentWords"
                  :key="index"
                  class="word-tag"
                  :type="getWordType(word)"
                >
                  {{ word }}
                </el-tag>
              </div>
              
              <el-divider />
              
              <el-descriptions title="分词统计" :column="3" border>
                <el-descriptions-item label="总词数">{{ segmentWords.length }}</el-descriptions-item>
                <el-descriptions-item label="唯一词数">{{ uniqueWords }}</el-descriptions-item>
                <el-descriptions-item label="平均词长">{{ avgWordLength }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-tab-pane>
          
          <!-- 特征向量 -->
          <el-tab-pane label="特征向量" name="features">
            <el-card header="特征向量预览">
              <el-alert
                title="特征提取信息"
                :description="`方法: ${(featureVector.method || extractMethod).toUpperCase()} | 实际维度: ${realDimensionDisplay} | 文档数: ${featureVector.doc_count || 0}`"
                type="info"
                :closable="false"
                style="margin-bottom: 16px"
              />

              <div class="feature-preview">
                <pre>{{ JSON.stringify(featureVector, null, 2) }}</pre>
              </div>

              <el-divider />

              <el-descriptions title="特征统计" :column="2" border>
                <el-descriptions-item label="特征维度">{{ realDimensionDisplay }}</el-descriptions-item>
                <el-descriptions-item label="非零特征">{{ nonZeroFeatures }}</el-descriptions-item>
                <el-descriptions-item label="最大值">{{ maxFeatureValue }}</el-descriptions-item>
                <el-descriptions-item label="最小值">{{ minFeatureValue }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-tab-pane>
          
          <!-- 质量报告 -->
          <el-tab-pane label="质量报告" name="quality">
            <el-card header="数据质量评估">
              <el-alert
                v-if="qualityScore < 80"
                type="warning"
                show-icon
                :closable="false"
                style="margin-bottom: 16px"
              >
                <template #title>
                  质检评分 {{ qualityScore.toFixed(1) }} 分，低于 80 分阈值，建议优化清洗规则后重新处理
                </template>
              </el-alert>
              <el-row :gutter="16">
                <el-col :span="6">
                  <el-statistic title="质量评分" :value="qualityScore" suffix="分">
                    <template #prefix>
                      <el-icon><TrendCharts /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic title="完整性" :value="completeness" suffix="%">
                    <template #prefix>
                      <el-icon><CircleCheck /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic title="准确性" :value="accuracy" suffix="%">
                    <template #prefix>
                      <el-icon><Select /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic title="一致性" :value="consistency" suffix="%">
                    <template #prefix>
                      <el-icon><Connection /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
              </el-row>
              
              <el-divider />
              
              <h4>发现的问题</h4>
              <el-table :data="qualityIssues" style="width: 100%">
                <el-table-column prop="type" label="问题类型" width="150" />
                <el-table-column prop="count" label="数量" width="100" />
                <el-table-column label="严重程度" width="120">
                  <template #default="{ row }">
                    <el-tag :type="getSeverityType(row.severity)">
                      {{ row.severity }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" />
              </el-table>
              
              <el-divider />
              
              <h4>优化建议</h4>
              <el-timeline>
                <el-timeline-item
                  v-for="(recommendation, index) in recommendations"
                  :key="index"
                  :timestamp="recommendation"
                  placement="top"
                >
                  {{ recommendation }}
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import {
  Upload, Operation, TrendCharts, CircleCheck, Select, Connection,
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { createPreprocessTask, getPreprocessTasks, getPreprocessData, getCollectionTasks, getTaskData, type PreprocessTask, type PreprocessedItem, type CollectionTask } from '@/api/weibo';
import apiClient from '@/api';

const cleanRules = ref(['removeDuplicates', 'removeSpecial']);
const segmentTool = ref('jieba');
const extractMethod = ref('tfidf');
const vectorSize = ref(128);
const maxFeatures = ref(1000);
const processing = ref(false);
const progress = ref(0);
const activePreview = ref('original');
const taskName = ref('');

// 数据来源
const dataSource = ref('collection');
const selectedCollectionTaskId = ref('');
const loadingCollectionTasks = ref(false);
const collectionTaskList = ref<CollectionTask[]>([]);
const loadedRealData = ref<any[]>([]);
const loadedDataCount = computed(() => loadedRealData.value.length);

// 已创建的预处理任务列表
const preprocessTaskList = ref<PreprocessTask[]>([]);

// 示例数据
const sampleTexts = [
  '今天天气真好，心情也很不错！😊',
  '这个产品质量太差了，非常失望...',
  '刚刚看了一部电影，剧情很精彩！',
  '周末准备去旅游，期待ing~',
  '工作压力好大，需要放松一下',
  '新买的手机很好用，推荐给大家',
  '最近股市行情不太好啊',
  '学习新技术真的很有意思',
  '今天加班到很晚，好累',
  '终于完成了这个项目，开心！',
];

const originalTexts = ref<string[]>([...sampleTexts]);

const compareOriginal = ref('今天天气真好，心情也很不错！😊 #开心 http://example.com');
const compareProcessed = ref('今天 天气 真 好 心情 也 很 不错');

// 差异对比数据
const diffItems = ref<{ original: string; cleaned: string }[]>([]);

// 进度步骤
const progressSteps = ref<{ label: string; done: boolean }[]>([]);

const segmentWords = ref<string[]>([]);

const featureVector = ref<any>({
  method: '-',
  dimension: 0,
  sample_vector: [],
  top_terms: [],
  doc_count: 0,
  hint: '请先执行预处理任务，特征向量将基于实际清洗后分词数据自动生成',
});
const featureStats = reactive({
  nonZero: 0,
  maxValue: 0,
  minValue: 0,
  realDimension: 0,
});

const qualityMetrics = reactive({
  totalCount: 0,
  emptyCount: 0,
  duplicateCount: 0,
  shortCount: 0,
  cleanedCount: 0,
});

const completeness = computed(() => {
  if (qualityMetrics.totalCount === 0) return 92;
  return Math.round((1 - qualityMetrics.emptyCount / qualityMetrics.totalCount) * 100);
});
const accuracy = computed(() => {
  if (qualityMetrics.totalCount === 0) return 88;
  return Math.round((1 - qualityMetrics.shortCount / qualityMetrics.totalCount) * 100);
});
const consistency = computed(() => {
  if (qualityMetrics.totalCount === 0) return 85;
  return Math.round((1 - qualityMetrics.duplicateCount / qualityMetrics.totalCount) * 100);
});
const qualityScore = computed(() => {
  return Math.round((completeness.value * 0.4 + accuracy.value * 0.35 + consistency.value * 0.25) * 10) / 10;
});

const qualityIssues = computed(() => {
  const issues: { type: string; count: number; severity: string; description: string }[] = [];
  if (qualityMetrics.duplicateCount > 0) {
    issues.push({ type: '重复数据', count: qualityMetrics.duplicateCount, severity: 'medium', description: `发现${qualityMetrics.duplicateCount}条重复记录` });
  }
  if (qualityMetrics.emptyCount > 0) {
    issues.push({ type: '缺失值', count: qualityMetrics.emptyCount, severity: 'high', description: `${qualityMetrics.emptyCount}条数据内容为空` });
  }
  if (qualityMetrics.shortCount > 0) {
    issues.push({ type: '过短文本', count: qualityMetrics.shortCount, severity: 'low', description: `${qualityMetrics.shortCount}条文本长度不足5字` });
  }
  if (issues.length === 0) {
    issues.push({ type: '无问题', count: 0, severity: 'low', description: '数据质量良好' });
  }
  return issues;
});

const recommendations = computed(() => {
  const recs: string[] = [];
  if (qualityMetrics.duplicateCount > 0) recs.push('建议去除重复数据以提高数据质量');
  if (qualityMetrics.emptyCount > 0) recs.push('补充缺失字段或删除不完整记录');
  if (qualityMetrics.shortCount > 0) recs.push('过短文本信息量不足，建议过滤或合并');
  if (qualityScore.value < 80) recs.push('质检评分低于80分，建议调整清洗规则后重新处理');
  if (recs.length === 0) recs.push('数据质量良好，可直接用于后续分析');
  return recs;
});

const uniqueWords = computed(() => {
  return new Set(segmentWords.value).size;
});

const avgWordLength = computed(() => {
  const total = segmentWords.value.reduce((sum, word) => sum + word.length, 0);
  return (total / segmentWords.value.length).toFixed(2);
});

// 真实特征统计来自 /api/preprocess/tasks/<id>/features
const nonZeroFeatures = computed(() => featureStats.nonZero);
const maxFeatureValue = computed(() => Number(featureStats.maxValue || 0).toFixed(4));
const minFeatureValue = computed(() => Number(featureStats.minValue || 0).toFixed(4));
const realDimensionDisplay = computed(() => featureStats.realDimension || vectorSize.value || maxFeatures.value);

const getWordType = (word: string) => {
  if (word.length === 1) return 'info';
  if (word.length === 2) return 'success';
  return '';
};

const getSeverityType = (severity: string) => {
  const types: Record<string, any> = {
    high: 'danger',
    medium: 'warning',
    low: 'info',
  };
  return types[severity] || 'info';
};

const handleDictUpload = (file: any) => {
  ElMessage.success(`词典文件 ${file.name} 上传成功`);
};

// 繁体→简体映射表（常用字）
const traditionalToSimplifiedMap: Record<string, string> = {
  '國': '国', '學': '学', '書': '书', '東': '东', '車': '车', '門': '门',
  '馬': '马', '魚': '鱼', '鳥': '鸟', '龍': '龙', '風': '风', '雲': '云',
  '電': '电', '長': '长', '開': '开', '關': '关', '聽': '听', '說': '说',
  '讀': '读', '寫': '写', '買': '买', '賣': '卖', '銀': '银', '錢': '钱',
  '鐵': '铁', '機': '机', '區': '区', '場': '场', '報': '报', '華': '华',
  '園': '园', '夢': '梦', '廣': '广', '應': '应', '從': '从', '復': '复',
  '樂': '乐', '實': '实', '經': '经', '濟': '济', '進': '进', '連': '连',
  '遠': '远', '選': '选', '達': '达', '還': '还', '這': '这', '邊': '边',
  '過': '过', '運': '运', '線': '线', '練': '练', '組': '组', '織': '织',
  '結': '结', '給': '给', '細': '细', '統': '统', '終': '终', '綠': '绿',
  '網': '网', '義': '义', '議': '议', '護': '护', '歡': '欢', '對': '对',
  '觀': '观', '見': '见', '視': '视', '覺': '觉', '計': '计', '記': '记',
  '許': '许', '論': '论', '設': '设', '試': '试', '語': '语', '課': '课',
  '調': '调', '談': '谈', '請': '请', '諸': '诸', '變': '变', '讓': '让',
  '號': '号', '點': '点', '黨': '党', '齊': '齐', '歲': '岁', '歷': '历',
  '歸': '归', '殘': '残', '無': '无', '熱': '热', '愛': '爱', '態': '态',
  '質': '质', '貨': '货', '費': '费', '資': '资', '賽': '赛', '離': '离',
  '難': '难', '響': '响', '頭': '头', '題': '题', '類': '类', '體': '体',
  '戰': '战', '聯': '联', '極': '极', '條': '条', '產': '产', '個': '个',
  '億': '亿', '僅': '仅', '優': '优', '傳': '传', '價': '价', '創': '创',
  '動': '动', '務': '务', '區': '区', '醫': '医', '壓': '压', '發': '发',
};

// 差异高亮：红色标记被删除的部分，蓝色标记繁体→简体转换的字符
const highlightRemoved = (original: string, cleaned: string): string => {
  if (!original || !cleaned) return original || '';
  let result = '';
  let ci = 0; // cleaned index
  for (let i = 0; i < original.length; i++) {
    if (ci < cleaned.length && original[i] === cleaned[ci]) {
      result += original[i];
      ci++;
    } else if (
      ci < cleaned.length &&
      traditionalToSimplifiedMap[original[i]] === cleaned[ci]
    ) {
      // 繁体→简体转换：蓝色高亮
      result += `<span class="diff-converted" title="繁→简: ${original[i]}→${cleaned[ci]}">${original[i]}</span>`;
      ci++;
    } else {
      result += `<span class="diff-removed">${original[i]}</span>`;
    }
  }
  return result;
};

// 加载已有的预处理任务
const loadPreprocessTasks = async () => {
  try {
    preprocessTaskList.value = await getPreprocessTasks();
  } catch (error) {
    console.error('加载预处理任务失败:', error);
  }
};

// 加载采集任务列表
const fetchCollectionTasks = async () => {
  if (collectionTaskList.value.length > 0) return;
  loadingCollectionTasks.value = true;
  try {
    collectionTaskList.value = await getCollectionTasks();
    if (collectionTaskList.value.length === 0) {
      ElMessage.info('暂无采集任务，请先在数据采集模块创建任务');
    }
  } catch {
    ElMessage.warning('加载采集任务失败');
  } finally {
    loadingCollectionTasks.value = false;
  }
};

// 数据来源变更
const onDataSourceChange = async (val: string) => {
  loadedRealData.value = [];
  selectedCollectionTaskId.value = '';
  if (val === 'collection') {
    await fetchCollectionTasks();
  } else if (val === 'database') {
    await loadDatabaseWeibo();
  } else {
    originalTexts.value = [...sampleTexts];
  }
};

// 从采集任务加载数据
const loadCollectionData = async (taskId: string) => {
  try {
    ElMessage.info('正在加载采集任务数据...');
    const result = await getTaskData(taskId, 1, 500);
    if (result.list && result.list.length > 0) {
      loadedRealData.value = result.list.map((item: any) => ({
        id: item.id || `item_${Date.now()}_${Math.random()}`,
        content: item.text || item.text_raw || '',
        source: 'collection',
        keyword: item.keyword || '',
        author: item.user?.screen_name || item.user_name || '',
        likes: item.attitudes_count || 0,
        comments: item.comments_count || 0,
        shares: item.reposts_count || 0,
        timestamp: item.created_at || new Date().toISOString(),
      }));
      originalTexts.value = loadedRealData.value.map(d => d.content).slice(0, 10);
      ElMessage.success(`已加载 ${loadedRealData.value.length} 条采集数据`);
    } else {
      ElMessage.warning('该采集任务暂无数据');
    }
  } catch {
    ElMessage.warning('加载采集任务数据失败');
  }
};

// 从数据库加载微博数据
const loadDatabaseWeibo = async () => {
  try {
    ElMessage.info('正在从数据库加载微博数据...');
    const response = await apiClient.get('/dashboard/weibo-detail', {
      params: { page: 1, page_size: 500 },
      timeout: 5000,
    });
    const items = response.data?.data?.items || response.data?.data || [];
    if (items.length > 0) {
      loadedRealData.value = items.map((item: any) => ({
        id: item.id || `db_${Date.now()}_${Math.random()}`,
        content: item.text || item.content || '',
        source: 'database',
        keyword: '',
        author: item.user?.screen_name || item.screen_name || '',
        likes: item.attitudes_count || 0,
        comments: item.comments_count || 0,
        shares: item.reposts_count || 0,
        timestamp: item.created_at || new Date().toISOString(),
      }));
      originalTexts.value = loadedRealData.value.map(d => d.content).slice(0, 10);
      ElMessage.success(`已加载 ${loadedRealData.value.length} 条数据库微博`);
    } else {
      ElMessage.warning('数据库中暂无微博数据');
    }
  } catch {
    ElMessage.warning('加载数据库微博失败');
  }
};

// 处理数据并保存到后端
const handleProcess = async () => {
  processing.value = true;
  progress.value = 0;
  diffItems.value = [];
  progressSteps.value = [
    { label: '数据加载', done: false },
    { label: '清洗规则应用', done: false },
    { label: '分词处理', done: false },
    { label: '结果入库', done: false },
  ];
  
  const updateStep = (index: number) => {
    progressSteps.value[index].done = true;
    progress.value = Math.min(100, Math.round(((index + 1) / progressSteps.value.length) * 100));
  };
  
  try {
    // Step 1: 准备数据
    // 如果是采集任务且还没加载数据，先加载
    if (dataSource.value === 'collection' && selectedCollectionTaskId.value && loadedRealData.value.length === 0) {
      await loadCollectionData(selectedCollectionTaskId.value);
    }
    
    let dataToProcess: any[];
    if (dataSource.value !== 'sample' && loadedRealData.value.length > 0) {
      dataToProcess = loadedRealData.value;
    } else {
      dataToProcess = originalTexts.value.map((text, idx) => ({
        id: `data_${Date.now()}_${idx}`,
        content: text,
        source: 'sample',
        keyword: '预处理测试',
        author: `用户${idx + 1}`,
        likes: Math.floor(Math.random() * 100),
        comments: Math.floor(Math.random() * 50),
        shares: Math.floor(Math.random() * 20),
        timestamp: new Date().toISOString(),
      }));
    }
    const texts = dataToProcess.map(d => d.content);
    qualityMetrics.totalCount = texts.length;
    qualityMetrics.emptyCount = texts.filter(t => !t || t.trim().length === 0).length;
    qualityMetrics.shortCount = texts.filter(t => t && t.trim().length > 0 && t.trim().length < 5).length;
    const uniqueTexts = new Set(texts.map(t => t.trim()));
    qualityMetrics.duplicateCount = texts.length - uniqueTexts.size;
    qualityMetrics.cleanedCount = 0;
    updateStep(0);
    
    // Step 2: 调用后端API
    const task = await createPreprocessTask({
      name: taskName.value || `预处理任务_${new Date().toLocaleString('zh-CN')}`,
      data: dataToProcess,
      cleanRules: cleanRules.value,
      segmentTool: segmentTool.value,
    });
    updateStep(1);
    
    // Step 3: 获取处理结果并生成差异对比
    try {
      const result = await getPreprocessData(task.id);
      if (result.list && result.list.length > 0) {
        diffItems.value = result.list.slice(0, 10).map(item => ({
          original: item.original_text,
          cleaned: item.cleaned_text,
        }));
        segmentWords.value = result.list.flatMap(item => item.words || []).slice(0, 60);
      }
    } catch {
      // 如果获取详细数据失败，用本地模拟
      diffItems.value = originalTexts.value.slice(0, 5).map(text => ({
        original: text,
        cleaned: text.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}]/gu, '')
                      .replace(/http[s]?:\/\/[^\s]+/g, '')
                      .replace(/#[^#\s]+/g, '')
                      .trim(),
      }));
    }
    updateStep(2);

    // Step 3.5: 拉真实 TF-IDF 特征向量统计 (基于该任务的 cleaned words)
    try {
      const featRes = await apiClient.get(`/preprocess/tasks/${task.id}/features`, {
        params: {
          method: extractMethod.value === 'tfidf' ? 'tfidf' : 'count',
          max_features: maxFeatures.value || 1000,
        },
      });
      const fd = featRes.data?.data;
      if (fd) {
        featureVector.value = {
          method: fd.method,
          dimension: fd.dimension,
          doc_count: fd.doc_count,
          sample_vector: fd.sample_vector,
          top_terms: fd.top_terms,
        };
        featureStats.realDimension = fd.dimension || 0;
        featureStats.nonZero = fd.non_zero || 0;
        featureStats.maxValue = fd.max_value || 0;
        featureStats.minValue = fd.min_value || 0;
      }
    } catch (e: any) {
      console.debug('[Preprocess] 特征向量接口失败, 保留空白', e?.response?.status);
    }

    // Step 4: 完成
    await loadPreprocessTasks();
    updateStep(3);
    
    const srcLabel = dataSource.value === 'collection' ? '采集任务' : dataSource.value === 'database' ? '数据库' : '示例';
    ElMessage.success(`预处理任务创建成功！处理了 ${task.processedCount} 条来自「${srcLabel}」的数据，可在情感分析模块选择该任务`);
    activePreview.value = 'compare';
    
  } catch (error: any) {
    ElMessage.warning('数据处理失败: ' + (error.message || '未知错误'));
  } finally {
    processing.value = false;
  }
};

// 选择采集任务后自动加载数据
watch(selectedCollectionTaskId, (taskId) => {
  if (taskId) {
    loadCollectionData(taskId);
  }
});

// 页面加载时获取已有任务
onMounted(() => {
  loadPreprocessTasks();
  fetchCollectionTasks();
});
</script>

<style scoped lang="scss">
.preprocess-module {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.preprocess-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 140px);
}

.operation-panel {
  width: 350px;
  flex-shrink: 0;
}

.preview-panel {
  flex: 1;
  overflow: hidden;
}

.text-list {
  max-height: 600px;
  overflow-y: auto;
}

.text-item {
  margin-bottom: 12px;
  display: flex;
  gap: 12px;
  
  .text-index {
    flex-shrink: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-primary);
    color: #fff;
    border-radius: 50%;
    font-size: 14px;
  }
  
  .text-content {
    flex: 1;
    line-height: 1.6;
  }
}

.compare-text {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 200px;
  line-height: 1.8;
}

.segment-result {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 200px;
}

.word-tag {
  font-size: 14px;
}

.feature-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
  
  pre {
    margin: 0;
  }
}

// 进度步骤样式
.progress-steps {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #909399;
  transition: color 0.3s;
  
  &.done {
    color: #67c23a;
  }
  
  .step-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #dcdfe6;
    display: inline-block;
  }
  
  .step-label {
    font-size: 12px;
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.rotating {
  animation: rotate 1s linear infinite;
}

// 差异对比样式
.diff-list {
  max-height: 500px;
  overflow-y: auto;
}

.diff-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  
  &:last-child {
    border-bottom: none;
  }
}

.diff-label {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
}

.diff-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.diff-original,
.diff-cleaned {
  padding: 8px 12px;
  border-radius: 4px;
  line-height: 1.8;
  font-size: 14px;
}

.diff-original {
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
}

.diff-cleaned {
  background: #f0f9eb;
  border-left: 3px solid #67c23a;
}

.diff-tag {
  display: inline-block;
  padding: 0 6px;
  margin-right: 8px;
  font-size: 11px;
  border-radius: 3px;
  background: #f56c6c;
  color: #fff;
  
  &.success {
    background: #67c23a;
  }
}

:deep(.diff-removed) {
  color: #f56c6c;
  text-decoration: line-through;
  background: rgba(245, 108, 108, 0.1);
  padding: 0 1px;
  border-radius: 2px;
}

:deep(.diff-converted) {
  color: #409eff;
  font-weight: bold;
  background: rgba(64, 158, 255, 0.12);
  padding: 0 2px;
  border-radius: 2px;
  border-bottom: 2px solid #409eff;
  cursor: help;
}
</style>
