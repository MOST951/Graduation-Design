<template>
  <div class="extensions-module">
    <el-tabs v-model="activeTab" class="extensions-tabs">
      <!-- 推荐系统 -->
      <el-tab-pane label="推荐系统" name="recommendation">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card header="推荐配置">
              <el-form label-width="100px">
                <el-form-item label="推荐算法">
                  <el-select v-model="recAlgorithm" style="width: 100%">
                    <el-option label="协同过滤" value="collaborative" />
                    <el-option label="基于内容" value="content" />
                    <el-option label="混合推荐" value="hybrid" />
                  </el-select>
                </el-form-item>
                
                <el-form-item label="推荐数量">
                  <el-input-number v-model="recCount" :min="5" :max="50" style="width: 100%" />
                </el-form-item>
                
                <el-form-item label="相似度阈值">
                  <el-slider v-model="similarityThreshold" :max="100" />
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="handleRecommend" block>
                    生成推荐
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-divider />
              
              <el-statistic title="推荐准确率" :value="recAccuracy" suffix="%">
                <template #prefix>
                  <el-icon><TrendCharts /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>
          
          <el-col :span="16">
            <el-card header="您可能感兴趣的微博">
              <el-timeline>
                <el-timeline-item
                  v-for="item in recommendations"
                  :key="item.id"
                  :timestamp="item.time"
                  placement="top"
                >
                  <el-card shadow="hover">
                    <div class="rec-item">
                      <div class="rec-content">{{ item.content }}</div>
                      <div class="rec-meta">
                        <el-tag size="small">相似度: {{ item.similarity }}%</el-tag>
                        <el-tag size="small" type="success">{{ item.reason }}</el-tag>
                      </div>
                    </div>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
      
      <!-- 流量预测 -->
      <el-tab-pane label="流量预测" name="prediction">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card header="预测配置">
              <el-form label-width="100px">
                <el-form-item label="预测模型">
                  <el-select v-model="predModel" style="width: 100%">
                    <el-option label="KNN" value="knn" />
                    <el-option label="CNN" value="cnn" />
                    <el-option label="LSTM" value="lstm" />
                  </el-select>
                </el-form-item>
                
                <el-form-item label="预测时长">
                  <el-input-number v-model="predHorizon" :min="1" :max="30" style="width: 100%" />
                  <span style="margin-left: 8px">天</span>
                </el-form-item>
                
                <el-form-item label="置信区间">
                  <el-slider v-model="confidenceLevel" :max="99" :min="80" />
                  <span>{{ confidenceLevel }}%</span>
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="handlePredict" block>
                    开始预测
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-divider />
              
              <el-descriptions :column="1" border>
                <el-descriptions-item label="模型准确率">{{ predAccuracy }}%</el-descriptions-item>
                <el-descriptions-item label="训练样本数">{{ trainSamples }}</el-descriptions-item>
                <el-descriptions-item label="预测时间">{{ predTime }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          
          <el-col :span="16">
            <el-card header="流量预测趋势">
              <div ref="predictionChartRef" style="height: 400px"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
      
      <!-- 知识图谱 -->
      <el-tab-pane label="知识图谱" name="knowledge">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card header="图谱搜索">
              <el-input
                v-model="searchEntity"
                placeholder="搜索实体..."
                :prefix-icon="Search"
                @keyup.enter="handleSearchEntity"
              />
              
              <el-divider />
              
              <h4>实体类型</h4>
              <el-checkbox-group v-model="entityTypes">
                <el-checkbox label="person">人物</el-checkbox>
                <el-checkbox label="organization">组织</el-checkbox>
                <el-checkbox label="location">地点</el-checkbox>
                <el-checkbox label="event">事件</el-checkbox>
                <el-checkbox label="concept">概念</el-checkbox>
              </el-checkbox-group>
              
              <el-divider />
              
              <h4>关系类型</h4>
              <el-radio-group v-model="relationType">
                <el-radio label="all">全部</el-radio>
                <el-radio label="direct">直接关系</el-radio>
                <el-radio label="indirect">间接关系</el-radio>
              </el-radio-group>
            </el-card>
          </el-col>
          
          <el-col :span="18">
            <el-card header="知识图谱可视化">
              <div ref="knowledgeChartRef" style="height: 600px"></div>
            </el-card>
          </el-col>
        </el-row>
        
        <!-- 实体详情对话框 -->
        <el-dialog v-model="showEntityDialog" title="实体详情" width="600px">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="实体名称">{{ currentEntity.name }}</el-descriptions-item>
            <el-descriptions-item label="实体类型">{{ currentEntity.type }}</el-descriptions-item>
            <el-descriptions-item label="提及次数">{{ currentEntity.mentions }}</el-descriptions-item>
            <el-descriptions-item label="重要性">{{ currentEntity.importance }}</el-descriptions-item>
          </el-descriptions>
          
          <el-divider />
          
          <h4>关联实体</h4>
          <el-tag
            v-for="related in currentEntity.related"
            :key="related"
            style="margin-right: 8px; margin-bottom: 8px"
          >
            {{ related }}
          </el-tag>
        </el-dialog>
      </el-tab-pane>
      
      <!-- 扩展管理 -->
      <el-tab-pane label="扩展管理" name="management">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-card header="已安装扩展">
              <el-table :data="extensions" style="width: 100%">
                <el-table-column prop="name" label="扩展名称" width="200" />
                <el-table-column prop="version" label="版本" width="100" />
                <el-table-column prop="description" label="描述" />
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-switch
                      v-model="row.enabled"
                      @change="handleToggleExtension(row)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="150">
                  <template #default="{ row }">
                    <el-button size="small" :icon="Setting" @click="handleConfigExtension(row)">
                      配置
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
        
        <!-- 扩展配置对话框 -->
        <el-dialog v-model="showConfigDialog" title="扩展配置" width="600px">
          <el-form :model="extensionConfig" label-width="100px">
            <el-form-item label="扩展名称">
              <el-input v-model="extensionConfig.name" disabled />
            </el-form-item>
            <el-form-item label="API密钥">
              <el-input v-model="extensionConfig.apiKey" type="password" />
            </el-form-item>
            <el-form-item label="请求限制">
              <el-input-number v-model="extensionConfig.rateLimit" :min="1" :max="1000" />
              <span style="margin-left: 8px">次/分钟</span>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showConfigDialog = false">取消</el-button>
            <el-button type="primary" @click="handleSaveConfig">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { Search, TrendCharts, Setting } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';

const activeTab = ref('recommendation');

// 推荐系统
const recAlgorithm = ref('collaborative');
const recCount = ref(10);
const similarityThreshold = ref(70);
const recAccuracy = ref(85.5);

const recommendations = ref([
  {
    id: '1',
    content: '人工智能技术的最新进展令人振奋...',
    time: '2024-12-10 09:00',
    similarity: 92,
    reason: '基于兴趣标签',
  },
  {
    id: '2',
    content: '新能源汽车市场持续增长...',
    time: '2024-12-10 08:30',
    similarity: 88,
    reason: '基于浏览历史',
  },
]);

// 流量预测
const predModel = ref('lstm');
const predHorizon = ref(7);
const confidenceLevel = ref(95);
const predAccuracy = ref(88.5);
const trainSamples = ref(10000);
const predTime = ref('2.5秒');
const predictionChartRef = ref<HTMLElement>();

// 知识图谱
const searchEntity = ref('');
const entityTypes = ref(['person', 'organization']);
const relationType = ref('all');
const showEntityDialog = ref(false);
const knowledgeChartRef = ref<HTMLElement>();

const currentEntity = ref({
  name: '',
  type: '',
  mentions: 0,
  importance: 0,
  related: [],
});

// 扩展管理
const showConfigDialog = ref(false);
const extensions = ref([
  {
    id: '1',
    name: '情感分析增强',
    version: '1.0.0',
    description: '提供更精准的情感分析能力',
    enabled: true,
  },
  {
    id: '2',
    name: '多语言支持',
    version: '1.2.0',
    description: '支持多种语言的情感分析',
    enabled: false,
  },
]);

const extensionConfig = ref({
  name: '',
  apiKey: '',
  rateLimit: 100,
});

const handleRecommend = () => {
  ElMessage.success('推荐生成成功');
};

const handlePredict = () => {
  ElMessage.success('预测任务已启动');
  initPredictionChart();
};

const handleSearchEntity = () => {
  ElMessage.info(`搜索实体: ${searchEntity.value}`);
};

const handleToggleExtension = (extension: any) => {
  ElMessage.success(`扩展 ${extension.name} 已${extension.enabled ? '启用' : '禁用'}`);
};

const handleConfigExtension = (extension: any) => {
  extensionConfig.value.name = extension.name;
  showConfigDialog.value = true;
};

const handleSaveConfig = () => {
  ElMessage.success('配置保存成功');
  showConfigDialog.value = false;
};

const initPredictionChart = () => {
  if (!predictionChartRef.value) return;
  
  const chart = echarts.init(predictionChartRef.value);
  const dates = Array.from({ length: 14 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() + i - 7);
    return date.toLocaleDateString();
  });
  
  chart.setOption({
    title: { text: '流量预测趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史数据', '预测数据', '置信区间'] },
    xAxis: {
      type: 'category',
      data: dates,
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '历史数据',
        type: 'line',
        data: [120, 132, 101, 134, 90, 230, 210],
      },
      {
        name: '预测数据',
        type: 'line',
        data: [null, null, null, null, null, null, null, 220, 240, 260, 280, 300, 320, 340],
        lineStyle: { type: 'dashed' },
      },
    ],
  });
};

const initKnowledgeChart = () => {
  if (!knowledgeChartRef.value) return;
  
  const chart = echarts.init(knowledgeChartRef.value);
  chart.setOption({
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      symbolSize: 60,
      roam: true,
      label: {
        show: true,
        position: 'inside',
      },
      data: [
        { name: '人工智能', category: 'concept', value: 100 },
        { name: '机器学习', category: 'concept', value: 80 },
        { name: '深度学习', category: 'concept', value: 70 },
        { name: 'OpenAI', category: 'organization', value: 90 },
      ],
      links: [
        { source: '人工智能', target: '机器学习' },
        { source: '机器学习', target: '深度学习' },
        { source: 'OpenAI', target: '人工智能' },
      ],
      categories: [
        { name: 'concept' },
        { name: 'organization' },
      ],
      force: {
        repulsion: 200,
      },
    }],
  });
  
  chart.on('click', (params: any) => {
    if (params.dataType === 'node') {
      currentEntity.value = {
        name: params.name,
        type: params.data.category,
        mentions: 156,
        importance: 85,
        related: ['相关实体1', '相关实体2'],
      };
      showEntityDialog.value = true;
    }
  });
};

onMounted(() => {
  nextTick(() => {
    initPredictionChart();
    initKnowledgeChart();
  });
});
</script>

<style scoped lang="scss">
.extensions-module {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.rec-item {
  .rec-content {
    margin-bottom: 12px;
    line-height: 1.6;
  }
  
  .rec-meta {
    display: flex;
    gap: 8px;
  }
}
</style>
