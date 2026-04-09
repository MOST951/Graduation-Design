<template>
  <div class="preprocess-module">
    <div class="preprocess-layout">
      <!-- 左侧操作面板 -->
      <el-card class="operation-panel" header="数据预处理">
        <el-form label-position="top">
          <el-form-item label="清洗规则">
            <el-checkbox-group v-model="cleanRules">
              <el-checkbox label="removeDuplicates">去重</el-checkbox>
              <el-checkbox label="removeSpecial">去特殊符号</el-checkbox>
              <el-checkbox label="removeStopwords">过滤停用词</el-checkbox>
              <el-checkbox label="removeEmoji">去除表情</el-checkbox>
              <el-checkbox label="removeUrl">去除URL</el-checkbox>
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
          
          <el-button type="primary" :loading="processing" block @click="handleProcess">
            <el-icon><Operation /></el-icon>
            开始处理
          </el-button>
          
          <el-progress
            v-if="processing"
            :percentage="progress"
            :status="progress === 100 ? 'success' : undefined"
            style="margin-top: 16px"
          />
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
            <el-row :gutter="16">
              <el-col :span="12">
                <el-card header="处理前">
                  <div class="compare-text">{{ compareOriginal }}</div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card header="处理后">
                  <div class="compare-text">{{ compareProcessed }}</div>
                </el-card>
              </el-col>
            </el-row>
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
                :description="`方法: ${extractMethod.toUpperCase()} | 维度: ${vectorSize || maxFeatures}`"
                type="info"
                :closable="false"
                style="margin-bottom: 16px"
              />
              
              <div class="feature-preview">
                <pre>{{ featureVector }}</pre>
              </div>
              
              <el-divider />
              
              <el-descriptions title="特征统计" :column="2" border>
                <el-descriptions-item label="特征维度">{{ vectorSize || maxFeatures }}</el-descriptions-item>
                <el-descriptions-item label="非零特征">{{ nonZeroFeatures }}</el-descriptions-item>
                <el-descriptions-item label="最大值">{{ maxFeatureValue }}</el-descriptions-item>
                <el-descriptions-item label="最小值">{{ minFeatureValue }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-tab-pane>
          
          <!-- 质量报告 -->
          <el-tab-pane label="质量报告" name="quality">
            <el-card header="数据质量评估">
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
import { ref, computed, onMounted } from 'vue';
import {
  Upload, Operation, TrendCharts, CircleCheck, Select, Connection,
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { createPreprocessTask, getPreprocessTasks, type PreprocessTask } from '@/api/weibo';

const cleanRules = ref(['removeDuplicates', 'removeSpecial']);
const segmentTool = ref('jieba');
const extractMethod = ref('tfidf');
const vectorSize = ref(128);
const maxFeatures = ref(1000);
const processing = ref(false);
const progress = ref(0);
const activePreview = ref('original');
const taskName = ref('');

// 已创建的预处理任务列表
const preprocessTaskList = ref<PreprocessTask[]>([]);

const originalTexts = ref([
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
]);

const compareOriginal = ref('今天天气真好，心情也很不错！😊 #开心 http://example.com');
const compareProcessed = ref('今天 天气 真 好 心情 也 很 不错');

const segmentWords = ref([
  '今天', '天气', '真', '好', '心情', '也', '很', '不错',
  '这个', '产品', '质量', '太', '差', '了', '非常', '失望',
]);

const featureVector = ref({
  method: 'TF-IDF',
  dimension: 1000,
  vector: [0.234, 0.567, 0.123, 0.890, 0.456, '...'],
  sparse: true,
});

const qualityScore = ref(85.5);
const completeness = ref(92);
const accuracy = ref(88);
const consistency = ref(85);

const qualityIssues = ref([
  { type: '重复数据', count: 156, severity: 'medium', description: '发现156条重复记录' },
  { type: '格式不一致', count: 45, severity: 'low', description: '日期格式不统一' },
  { type: '缺失值', count: 23, severity: 'high', description: '部分字段存在缺失' },
]);

const recommendations = ref([
  '建议去除重复数据以提高数据质量',
  '统一日期格式为 YYYY-MM-DD',
  '补充缺失字段或删除不完整记录',
  '增加数据验证规则',
]);

const uniqueWords = computed(() => {
  return new Set(segmentWords.value).size;
});

const avgWordLength = computed(() => {
  const total = segmentWords.value.reduce((sum, word) => sum + word.length, 0);
  return (total / segmentWords.value.length).toFixed(2);
});

const nonZeroFeatures = computed(() => 456);
const maxFeatureValue = computed(() => 0.890);
const minFeatureValue = computed(() => 0.001);

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

// 加载已有的预处理任务
const loadPreprocessTasks = async () => {
  try {
    preprocessTaskList.value = await getPreprocessTasks();
  } catch (error) {
    console.error('加载预处理任务失败:', error);
  }
};

// 处理数据并保存到后端
const handleProcess = async () => {
  processing.value = true;
  progress.value = 0;
  
  // 模拟进度
  const progressTimer = setInterval(() => {
    if (progress.value < 80) {
      progress.value += 10;
    }
  }, 200);
  
  try {
    console.log('开始创建预处理任务...');
    
    // 准备要处理的数据
    const dataToProcess = originalTexts.value.map((text, idx) => ({
      id: `data_${Date.now()}_${idx}`,
      content: text,
      source: 'manual_input',
      keyword: '预处理测试',
      author: `用户${idx + 1}`,
      likes: Math.floor(Math.random() * 100),
      comments: Math.floor(Math.random() * 50),
      shares: Math.floor(Math.random() * 20),
      timestamp: new Date().toISOString(),
    }));
    
    console.log('准备处理的数据:', dataToProcess.length, '条');
    
    // 调用后端API创建预处理任务
    const task = await createPreprocessTask({
      name: taskName.value || `预处理任务_${new Date().toLocaleString('zh-CN')}`,
      data: dataToProcess,
      cleanRules: cleanRules.value,
      segmentTool: segmentTool.value,
    });
    
    console.log('任务创建成功:', task);
    
    clearInterval(progressTimer);
    progress.value = 100;
    
    // 更新任务列表
    await loadPreprocessTasks();
    
    ElMessage.success(`预处理任务创建成功！处理了 ${task.processedCount} 条数据`);
    
    // 更新预览数据
    compareProcessed.value = '数据已清洗并分词处理完成';
    
  } catch (error: any) {
    console.error('处理失败:', error);
    clearInterval(progressTimer);
    ElMessage.error('数据处理失败: ' + (error.message || '未知错误'));
  } finally {
    processing.value = false;
  }
};

// 页面加载时获取已有任务
onMounted(() => {
  loadPreprocessTasks();
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
    background: #409eff;
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
</style>
