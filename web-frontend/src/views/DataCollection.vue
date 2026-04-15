<template>
  <div class="data-collection-module">
    <!-- 数据流可视化 -->
    <div class="dataflow-pipeline">
      <div class="pipeline-title">
        <el-icon><Connection /></el-icon>
        <span>数据处理流水线</span>
        <el-tag v-if="currentPhase !== 'idle'" :type="getPhaseTagType(currentPhase)" size="small">
          {{ getPhaseLabel(currentPhase) }}
        </el-tag>
      </div>
      <div class="pipeline-stages">
        <div 
          v-for="(stage, index) in pipelineStages" 
          :key="stage.key"
          class="pipeline-stage"
          :class="{ active: stage.status === 'running', completed: stage.status === 'completed', failed: stage.status === 'failed' }"
        >
          <div class="stage-icon">
            <el-icon v-if="stage.status === 'completed'" :color="SUCCESS"><CircleCheck /></el-icon>
            <el-icon v-else-if="stage.status === 'running'" class="rotating" :color="PRIMARY"><Loading /></el-icon>
            <el-icon v-else-if="stage.status === 'failed'" :color="DANGER"><CircleClose /></el-icon>
            <el-icon v-else :color="INFO"><component :is="stage.icon" /></el-icon>
          </div>
          <div class="stage-name">{{ stage.name }}</div>
          <div class="stage-progress" v-if="stage.status === 'running'">
            <el-progress :percentage="stage.progress" :show-text="false" :stroke-width="4" />
          </div>
          <div class="stage-count" v-if="stage.count > 0">{{ stage.count }}</div>
          <div class="stage-arrow" v-if="index < pipelineStages.length - 1">→</div>
        </div>
      </div>
    </div>

    <!-- 顶部操作栏 -->
    <div class="action-bar">
      <el-button-group>
        <el-button type="primary" :icon="VideoPlay" @click="startFullPipeline" :loading="crawlLoading" :disabled="isRunning">
          启动完整流水线
        </el-button>
        <el-button type="success" :icon="VideoPlay" @click="startCrawl" :loading="crawlLoading" :disabled="isRunning">
          仅采集数据
        </el-button>
        <el-button type="danger" :icon="VideoPause" @click="stopCrawl" :disabled="!isRunning">
          停止
        </el-button>
        <el-button :icon="Setting" @click="showConfigDialog = true">
          配置
        </el-button>
      </el-button-group>
      
      <div class="status-info">
        <el-tag :type="isRunning ? 'success' : 'info'" size="large">
          {{ isRunning ? getPhaseLabel(currentPhase) : '空闲' }}
        </el-tag>
        <span class="stats">已采集: <strong>{{ totalCollected }}</strong> 条</span>
      </div>
    </div>
    
    <el-row :gutter="20">
      <!-- 左侧：配置面板 -->
      <el-col :span="8">
        <el-card header="采集配置" shadow="hover">
          <el-form label-position="top" size="default">
            <el-form-item label="Keyword">
              <div class="keyword-input-container">
                <el-tag
                  v-for="(keyword, index) in config.keywords"
                  :key="index"
                  closable
                  @close="removeKeyword(index)"
                  class="keyword-tag"
                >
                  {{ keyword }}
                </el-tag>
                
                <el-input
                  v-if="inputVisible"
                  ref="keywordInput"
                  v-model="inputValue"
                  size="small"
                  class="keyword-input"
                  @keyup.enter="handleInputConfirm"
                  @blur="handleInputConfirm"
                  placeholder="Enter keyword"
                />
                
                <el-button
                  v-else
                  size="small"
                  class="button-new-keyword"
                  @click="showInput"
                >
                  + Add Keyword
                </el-button>
              </div>
              
              <!-- Keyword suggestions -->
              <div class="keyword-suggestions" v-if="!inputVisible && config.keywords.length === 0">
                <span class="suggestion-label">Popular keywords: </span>
                <el-tag
                  v-for="suggestion in defaultKeywords.slice(0, 5)"
                  :key="suggestion"
                  size="small"
                  class="suggestion-tag"
                  @click="addKeyword(suggestion)"
                >
                  {{ suggestion }}
                </el-tag>
              </div>
            </el-form-item>
            
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="config.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item label="数据源">
              <el-checkbox-group v-model="config.dataSources">
                <el-checkbox label="weibo">微博</el-checkbox>
                <el-checkbox label="douyin">抖音</el-checkbox>
                <el-checkbox label="kuaishou">快手</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item label="热搜榜单">
              <el-switch v-model="config.crawlHotSearch" active-text="爬取热搜" />
            </el-form-item>
            
            <el-form-item label="采集数量上限">
              <el-input-number v-model="config.maxCount" :min="100" :max="100000" :step="1000" />
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 反爬策略配置 -->
        <el-card header="反爬策略" shadow="hover" style="margin-top: 20px">
          <el-form label-position="top" size="default">
            <el-form-item label="请求间隔(秒)">
              <el-slider v-model="config.requestInterval" :min="1" :max="10" show-input />
            </el-form-item>
            
            <el-form-item label="IP代理池">
              <el-switch v-model="config.useProxy" active-text="启用代理" />
            </el-form-item>
            
            <el-form-item label="Headers伪装">
              <el-switch v-model="config.randomHeaders" active-text="随机UA" />
            </el-form-item>
            
            <el-form-item label="Cookie配置">
              <el-input
                v-model="config.cookie"
                type="textarea"
                :rows="3"
                placeholder="粘贴微博登录Cookie（可选）"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 中间：实时状态 -->
      <el-col :span="8">
        <el-card header="采集进度" shadow="hover">
          <div class="progress-section">
            <el-progress
              type="dashboard"
              :percentage="crawlProgress"
              :color="progressColors"
              :width="180"
            >
              <template #default="{ percentage }">
                <span class="progress-value">{{ percentage }}%</span>
                <span class="progress-label">完成度</span>
              </template>
            </el-progress>
            
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-value success">{{ stats.success }}</span>
                <span class="stat-label">成功</span>
              </div>
              <div class="stat-item">
                <span class="stat-value danger">{{ stats.failed }}</span>
                <span class="stat-label">失败</span>
              </div>
              <div class="stat-item">
                <span class="stat-value warning">{{ stats.pending }}</span>
                <span class="stat-label">待处理</span>
              </div>
              <div class="stat-item">
                <span class="stat-value info">{{ stats.speed }}/s</span>
                <span class="stat-label">速度</span>
              </div>
            </div>
          </div>
        </el-card>
        
        <!-- 采集速率图表 -->
        <el-card shadow="hover" style="margin-top: 20px">
          <template #header>
            <div class="rate-header">
              <span>采集速率</span>
              <el-tag type="primary" size="small">{{ stats.speed }} 条/s</el-tag>
            </div>
          </template>
          <div ref="rateChartRef" style="height: 160px"></div>
        </el-card>

        <!-- 增量去重统计 -->
        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <div class="rate-header">
              <span>增量采集 &amp; 去重</span>
              <el-switch v-model="advancedConfig.deduplicate" active-text="去重" size="small" />
            </div>
          </template>
          <div class="dedup-stats">
            <div class="dedup-item">
              <div class="dedup-value total">{{ dedupStats.totalFetched }}</div>
              <div class="dedup-label">总获取</div>
            </div>
            <div class="dedup-item">
              <div class="dedup-value dup">{{ dedupStats.duplicates }}</div>
              <div class="dedup-label">重复</div>
            </div>
            <div class="dedup-item">
              <div class="dedup-value unique">{{ dedupStats.unique }}</div>
              <div class="dedup-label">有效新增</div>
            </div>
            <div class="dedup-item">
              <div class="dedup-value rate">{{ dedupStats.dedupRate }}%</div>
              <div class="dedup-label">去重率</div>
            </div>
          </div>
          <el-progress :percentage="dedupStats.dedupRate" :stroke-width="6" :color="WARNING" style="margin-top: 8px" />
        </el-card>

        <!-- 任务列表 -->
        <el-card header="采集任务" shadow="hover" style="margin-top: 16px">
          <el-table :data="tasks" height="200" size="small">
            <el-table-column prop="id" label="任务ID" width="100" />
            <el-table-column prop="keyword" label="关键词" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="数量" width="80" />
          </el-table>
        </el-card>
      </el-col>
      
      <!-- 右侧：实时日志 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="log-header">
              <span>实时日志</span>
              <el-button text size="small" @click="clearLogs">清空</el-button>
            </div>
          </template>
          <el-table 
            :data="logs" 
            max-height="300px" 
            size="small"
            ref="logTable"
            class="log-table"
          >
            <el-table-column prop="time" label="Time" width="80" />
            <el-table-column prop="level" label="Level" width="80">
              <template #default="{ row }">
                <el-tag 
                  :type="getLogLevelType(row.level)" 
                  size="small"
                >
                  {{ row.level.toUpperCase() }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="Message" />
          </el-table>
        </el-card>
        
        <!-- 数据预览 -->
        <el-card header="最新数据预览" shadow="hover" style="margin-top: 20px">
          <div class="preview-list">
            <div v-for="item in previewData" :key="item.id" class="preview-item">
              <div class="preview-header">
                <el-avatar :size="32">{{ item.author?.charAt(0) || 'U' }}</el-avatar>
                <div class="preview-info">
                  <span class="author">{{ item.author || '匿名用户' }}</span>
                  <span class="time">{{ item.time }}</span>
                </div>
              </div>
              <div class="preview-content">{{ item.content }}</div>
              <div class="preview-meta">
                <span><el-icon><ChatDotRound /></el-icon> {{ item.comments || 0 }}</span>
                <span><el-icon><Share /></el-icon> {{ item.shares || 0 }}</span>
                <span><el-icon><Star /></el-icon> {{ item.likes || 0 }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 爬虫配置对话框 -->
    <el-dialog v-model="showConfigDialog" title="高级爬虫配置" width="600px">
      <el-form label-width="120px">
        <el-form-item label="并发线程数">
          <el-input-number v-model="advancedConfig.threads" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="重试次数">
          <el-input-number v-model="advancedConfig.retryTimes" :min="0" :max="5" />
        </el-form-item>
        <el-form-item label="超时时间(秒)">
          <el-input-number v-model="advancedConfig.timeout" :min="5" :max="60" />
        </el-form-item>
        <el-form-item label="数据存储格式">
          <el-radio-group v-model="advancedConfig.saveFormat">
            <el-radio label="json">JSON</el-radio>
            <el-radio label="csv">CSV</el-radio>
            <el-radio label="parquet">Parquet</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="自动去重">
          <el-switch v-model="advancedConfig.deduplicate" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAdvancedConfig">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { ElMessage } from 'element-plus';
import { 
  VideoPlay, VideoPause, Setting, ChatDotRound, Share, Star,
  Connection, CircleCheck, CircleClose, Loading, Download, DataAnalysis, Sort, Monitor
} from '@element-plus/icons-vue';
import { useWeiboStore } from '@/store/weibo';
import { SUCCESS, PRIMARY, DANGER, INFO, WARNING } from '@/styles/colors';
import { 
  getDataflowTaskStatus,
  type DataflowTask
} from '@/api/weibo';

// Store
const weiboStore = useWeiboStore();
const { dataflowTaskId, dataflowTask } = storeToRefs(weiboStore);

// 本地状态
const isRunning = ref(false);
const crawlLoading = ref(false);
const crawlProgress = ref(0);
const totalCollected = ref(0);
const showConfigDialog = ref(false);
const logContainer = ref<HTMLElement>();
const logTable = ref();

// 数据流状态
const currentPhase = ref<'idle' | 'crawl' | 'clean' | 'analyze' | 'rank' | 'done'>('idle');

// 流水线阶段
const pipelineStages = reactive([
  { key: 'crawl', name: '微博爬虫', icon: Download, status: 'pending', progress: 0, count: 0 },
  { key: 'hdfs', name: 'HDFS存储', icon: Monitor, status: 'pending', progress: 0, count: 0 },
  { key: 'clean', name: 'Spark清洗', icon: DataAnalysis, status: 'pending', progress: 0, count: 0 },
  { key: 'analyze', name: '情感分析', icon: ChatDotRound, status: 'pending', progress: 0, count: 0 },
  { key: 'rank', name: '双维度排序', icon: Sort, status: 'pending', progress: 0, count: 0 },
]);

// 配置
const config = reactive({
  keywords: ['人工智能', '新能源'],
  dateRange: null as any,
  dataSources: ['weibo'],
  crawlHotSearch: true,
  maxCount: 10000,
  requestInterval: 3,
  useProxy: false,
  randomHeaders: true,
  cookie: '',
});

const advancedConfig = reactive({
  threads: 3,
  retryTimes: 3,
  timeout: 30,
  saveFormat: 'json',
  deduplicate: true,
});

const defaultKeywords = ['人工智能', '新能源', '科技', '经济', '教育', '健康', '环保'];

const inputVisible = ref(false);
const inputValue = ref('');
const keywordInput = ref();

// 统计数据
const stats = reactive({
  success: 0,
  failed: 0,
  pending: 0,
  speed: 0,
});

// 采集速率图表
const rateChartRef = ref<HTMLElement>();
let rateChart: any = null;
const rateHistory = ref<number[]>(new Array(30).fill(0));
const rateTimeLabels = ref<string[]>(new Array(30).fill(''));
let rateTimer: any = null;

// 去重统计
const dedupStats = reactive({
  totalFetched: 0,
  duplicates: 0,
  unique: 0,
  dedupRate: 0,
});

// 任务列表
const tasks = ref<any[]>([]);

// 日志
const logs = ref<any[]>([]);

// 预览数据
const previewData = ref<any[]>([]);

// 进度条颜色
const progressColors = [
  { color: DANGER, percentage: 20 },
  { color: WARNING, percentage: 40 },
  { color: SUCCESS, percentage: 60 },
  { color: PRIMARY, percentage: 80 },
  { color: '#6f7ad3', percentage: 100 },
];

let crawlTaskId = '';
let statusTimer: any = null;

// 启动完整流水线（数据流连通）- 使用Store
const startFullPipeline = async () => {
  if (config.keywords.length === 0 && !config.crawlHotSearch) {
    ElMessage.warning('请至少输入一个关键词或开启热搜爬取');
    return;
  }
  
  crawlLoading.value = true;
  isRunning.value = true;
  crawlProgress.value = 0;
  currentPhase.value = 'crawl';
  resetPipelineStages();
  
  addLog('info', '🚀 启动完整数据处理流水线...');
  addLog('info', `数据流: 微博爬虫 → HDFS → Spark清洗 → HBase → 双维度排序`);
  addLog('info', `关键词: ${config.keywords.join(', ') || '无'}`);
  
  try {
    // 通过store启动数据流任务
    const result = await weiboStore.startDataflow({
      keywords: config.keywords,
      pages: 3,
      crawlHot: config.crawlHotSearch,
      autoProcess: true,
    });
    
    addLog('success', `流水线任务创建成功: ${result.task_id}`);
    
    // 添加到任务列表
    tasks.value.unshift({
      id: result.task_id.slice(-8),
      keyword: config.keywords.join(', ') || '热搜',
      status: 'running',
      count: 0,
    });
    
    // 开始轮询数据流状态
    startDataflowPolling();
    
  } catch (error: any) {
    addLog('error', `流水线启动失败: ${error.message}`);
    isRunning.value = false;
    currentPhase.value = 'idle';
  } finally {
    crawlLoading.value = false;
  }
};

// 重置流水线阶段状态
const resetPipelineStages = () => {
  pipelineStages.forEach(stage => {
    stage.status = 'pending';
    stage.progress = 0;
    stage.count = 0;
  });
};

// 更新流水线阶段状态
const updatePipelineFromTask = (task: DataflowTask) => {
  // 更新各阶段状态
  const phaseMapping: Record<string, number> = {
    'crawl': 0,
    'hdfs': 1,
    'clean': 2,
    'analyze': 3,
    'rank': 4,
  };
  
  // 根据任务phases更新
  if (task.phases) {
    // 爬虫阶段
    pipelineStages[0].status = task.phases.crawl?.status || 'pending';
    pipelineStages[0].progress = task.phases.crawl?.progress || 0;
    
    // HDFS存储（跟随爬虫阶段）
    if (task.phases.crawl?.status === 'completed') {
      pipelineStages[1].status = 'completed';
      pipelineStages[1].progress = 100;
      pipelineStages[1].count = task.collected;
    } else if (task.phases.crawl?.status === 'running') {
      pipelineStages[1].status = 'running';
      pipelineStages[1].progress = task.phases.crawl?.progress || 0;
    }
    
    // Spark清洗
    pipelineStages[2].status = task.phases.clean?.status || 'pending';
    pipelineStages[2].progress = task.phases.clean?.progress || 0;
    
    // 情感分析
    pipelineStages[3].status = task.phases.analyze?.status || 'pending';
    pipelineStages[3].progress = task.phases.analyze?.progress || 0;
    
    // 双维度排序
    pipelineStages[4].status = task.phases.rank?.status || 'pending';
    pipelineStages[4].progress = task.phases.rank?.progress || 0;
  }
  
  // 更新采集数量
  pipelineStages[0].count = task.collected;
};

// 轮询数据流任务状态
let dataflowTimer: any = null;

const startDataflowPolling = () => {
  dataflowTimer = setInterval(async () => {
    try {
      const status = await getDataflowTaskStatus(dataflowTaskId.value);
      dataflowTask.value = status;
      
      crawlProgress.value = status.progress;
      totalCollected.value = status.collected;
      currentPhase.value = status.phase as any;
      
      // 更新流水线可视化
      updatePipelineFromTask(status);
      
      // 更新任务列表
      if (tasks.value.length > 0) {
        tasks.value[0].count = status.collected;
        tasks.value[0].status = status.status === 'completed' ? 'completed' : 
                                status.status === 'failed' ? 'failed' : 'running';
      }
      
      // 根据阶段添加日志
      if (status.phase === 'clean' && pipelineStages[2].status === 'running') {
        addLog('info', `📊 Spark数据清洗中... ${status.phases?.clean?.progress || 0}%`);
      } else if (status.phase === 'analyze' && pipelineStages[3].status === 'running') {
        addLog('info', `🧠 情感分析中... ${status.phases?.analyze?.progress || 0}%`);
      } else if (status.phase === 'rank' && pipelineStages[4].status === 'running') {
        addLog('info', `📈 双维度排序中... ${status.phases?.rank?.progress || 0}%`);
      }
      
      if (status.status === 'completed') {
        addLog('success', `✅ 完整流水线执行完成！共处理 ${status.collected} 条数据`);
        addLog('success', `数据已写入HBase，可在热点话题页面查看排序结果`);
        isRunning.value = false;
        currentPhase.value = 'done';
        stopDataflowPolling();
      } else if (status.status === 'failed') {
        addLog('error', `❌ 流水线执行失败: ${status.error}`);
        isRunning.value = false;
        currentPhase.value = 'idle';
        stopDataflowPolling();
      }
    } catch (error) {
      console.error('获取数据流状态失败:', error);
    }
  }, 2000);
};

const stopDataflowPolling = () => {
  if (dataflowTimer) {
    clearInterval(dataflowTimer);
    dataflowTimer = null;
  }
};

// 开始采集（仅采集，不触发后续处理）- 使用Store
const startCrawl = async () => {
  if (config.keywords.length === 0 && !config.crawlHotSearch) {
    ElMessage.warning('请至少输入一个关键词或开启热搜爬取');
    return;
  }
  
  crawlLoading.value = true;
  isRunning.value = true;
  crawlProgress.value = 0;
  stats.success = 0;
  stats.failed = 0;
  currentPhase.value = 'crawl';
  resetPipelineStages();
  pipelineStages[0].status = 'running';
  
  addLog('info', '开始数据采集任务（仅采集）...');
  addLog('info', `关键词: ${config.keywords.join(', ') || '无'}`);
  addLog('info', `爬取热搜: ${config.crawlHotSearch ? '是' : '否'}`);
  
  try {
    // 通过store启动采集任务
    const result = await weiboStore.startCollection({
      keywords: config.keywords,
      pages: 3,
      crawlHot: config.crawlHotSearch,
    });
    crawlTaskId = result.task_id;
    addLog('success', `任务创建成功: ${result.task_id}`);
    
    // 添加到任务列表
    tasks.value.unshift({
      id: result.task_id.slice(-8),
      keyword: config.keywords.join(', ') || '热搜',
      status: 'running',
      count: 0,
    });
    
    // 开始轮询状态
    startStatusPolling();
    
  } catch (error: any) {
    addLog('error', `任务创建失败: ${error.message}`);
    isRunning.value = false;
    currentPhase.value = 'idle';
  } finally {
    crawlLoading.value = false;
  }
};

// 停止采集
const stopCrawl = () => {
  isRunning.value = false;
  currentPhase.value = 'idle';
  stopStatusPolling();
  stopDataflowPolling();
  addLog('warn', '任务已停止');
  
  if (tasks.value.length > 0) {
    tasks.value[0].status = 'stopped';
  }
};

// 轮询任务状态 - 使用Store
const startStatusPolling = () => {
  statusTimer = setInterval(async () => {
    try {
      const status = await weiboStore.getTaskStatus(crawlTaskId);
      
      crawlProgress.value = status.progress || 0;
      stats.success = status.collected_count || 0;
      totalCollected.value = status.collected_count || 0;
      
      if (tasks.value.length > 0) {
        tasks.value[0].count = status.collected;
      }
      
      if (status.status === 'completed') {
        addLog('success', `采集完成，共采集 ${status.collected} 条数据`);
        isRunning.value = false;
        stopStatusPolling();
        if (tasks.value.length > 0) {
          tasks.value[0].status = 'completed';
        }
      } else if (status.status === 'failed') {
        addLog('error', `采集失败: ${status.error}`);
        isRunning.value = false;
        stopStatusPolling();
        if (tasks.value.length > 0) {
          tasks.value[0].status = 'failed';
        }
      } else {
        // 模拟实时日志
        if (Math.random() > 0.7) {
          addLog('info', `已采集 ${status.collected} 条数据...`);
        }
      }
    } catch (error) {
      console.error('获取状态失败:', error);
    }
  }, 2000);
};

const stopStatusPolling = () => {
  if (statusTimer) {
    clearInterval(statusTimer);
    statusTimer = null;
  }
};

// 添加日志
const addLog = (level: string, message: string) => {
  const now = new Date();
  logs.value.push({
    time: now.toLocaleTimeString(),
    level,
    message,
  });
  
  // 
  if (logs.value.length > 100) {
    logs.value.shift();
  }
  
  // 
  nextTick(() => {
    if (logTable.value) {
      const tableBody = logTable.value.$el.querySelector('.el-table__body-wrapper');
      if (tableBody) {
        tableBody.scrollTop = tableBody.scrollHeight;
      }
    }
  });
};

// 清空日志
const clearLogs = () => {
  logs.value = [];
};

// 保存高级配置
const saveAdvancedConfig = () => {
  showConfigDialog.value = false;
  ElMessage.success('配置已保存');
};

// 获取状态类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    stopped: 'warning',
  };
  return map[status] || 'info';
};

const getLogLevelType = (level: string) => {
  const map: Record<string, any> = { error: 'danger', warning: 'warning', info: 'success', debug: 'info' };
  return map[level.toLowerCase()] || 'info';
};

const loadPreviewData = () => {
  fetchPreviewData([]);
};

const fetchPreviewData = async (hotList: any[]) => {
  try {
    previewData.value = hotList.slice(0, 5).map((item: any, index: number) => ({
      id: index,
      author: '微博热搜',
      content: item.title,
      time: '刚刚',
      comments: Math.floor(Math.random() * 1000),
      shares: Math.floor(Math.random() * 500),
      likes: item.heat || Math.floor(Math.random() * 10000),
    }));
  } catch (error) {
    previewData.value = [
      { id: 1, author: '用户A', content: '这是一条测试微博内容...', time: '5分钟前', comments: 123, shares: 45, likes: 678 },
      { id: 2, author: '用户B', content: '今天天气真好，适合出门...', time: '10分钟前', comments: 89, shares: 23, likes: 456 },
    ];
  }
};

// 获取阶段标签
const getPhaseLabel = (phase: string) => {
  const labels: Record<string, string> = {
    'idle': '空闲',
    'crawl': '数据采集中',
    'clean': 'Spark清洗中',
    'analyze': '情感分析中',
    'rank': '双维度排序中',
    'done': '已完成',
  };
  return labels[phase] || phase;
};

// 获取阶段标签类型
const getPhaseTagType = (phase: string) => {
  const types: Record<string, string> = {
    'idle': 'info',
    'crawl': 'primary',
    'clean': 'warning',
    'analyze': 'success',
    'rank': 'danger',
    'done': 'success',
  };
  return types[phase] || 'info';
};

// 采集速率图表
const initRateChart = () => {
  if (!rateChartRef.value) return;
  const echarts = (window as any).__echarts || null;
  if (!echarts) {
    import('echarts').then(mod => {
      (window as any).__echarts = mod;
      _buildRateChart(mod);
    });
  } else {
    _buildRateChart(echarts);
  }
};

const _buildRateChart = (echarts: any) => {
  if (!rateChartRef.value) return;
  rateChart = echarts.init(rateChartRef.value);
  rateChart.setOption({
    grid: { left: 40, right: 10, top: 10, bottom: 24 },
    xAxis: { type: 'category', data: rateTimeLabels.value, show: false },
    yAxis: { type: 'value', min: 0, splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
      type: 'line',
      data: rateHistory.value,
      smooth: true,
      symbol: 'none',
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(22,93,255,0.3)' }, { offset: 1, color: 'rgba(22,93,255,0.02)' }] } },
      lineStyle: { color: PRIMARY, width: 2 },
    }],
  });
};

const updateRateChart = () => {
  const speed = stats.speed;
  rateHistory.value.push(speed);
  if (rateHistory.value.length > 30) rateHistory.value.shift();
  const now = new Date().toLocaleTimeString().slice(0, 5);
  rateTimeLabels.value.push(now);
  if (rateTimeLabels.value.length > 30) rateTimeLabels.value.shift();
  if (rateChart) {
    rateChart.setOption({ xAxis: { data: rateTimeLabels.value }, series: [{ data: rateHistory.value }] });
  }
};

const startRateTracking = () => {
  rateTimer = setInterval(() => {
    // Simulate speed based on collection state
    if (isRunning.value) {
      stats.speed = Math.floor(Math.random() * 8 + 2);
      // Simulate dedup
      const batchSize = stats.speed;
      const dups = Math.floor(batchSize * (Math.random() * 0.3));
      dedupStats.totalFetched += batchSize;
      dedupStats.duplicates += dups;
      dedupStats.unique = dedupStats.totalFetched - dedupStats.duplicates;
      dedupStats.dedupRate = dedupStats.totalFetched > 0 ? Math.round(dedupStats.duplicates / dedupStats.totalFetched * 100) : 0;
    } else {
      stats.speed = 0;
    }
    updateRateChart();
  }, 2000);
};

// 
const showInput = () => {
  inputVisible.value = true;
  nextTick(() => {
    keywordInput.value?.focus();
  });
};

const handleInputConfirm = () => {
  if (inputValue.value && config.keywords.indexOf(inputValue.value) === -1) {
    config.keywords.push(inputValue.value);
    addLog('info', `Added keyword: ${inputValue.value}`);
  }
  inputVisible.value = false;
  inputValue.value = '';
};

const removeKeyword = (index: number) => {
  const removed = config.keywords.splice(index, 1)[0];
  addLog('info', `Removed keyword: ${removed}`);
};

const addKeyword = (keyword: string) => {
  if (config.keywords.indexOf(keyword) === -1) {
    config.keywords.push(keyword);
    addLog('info', `Added suggested keyword: ${keyword}`);
  }
};

onMounted(() => {
  addLog('info', 'Data collection module ready');
  addLog('info', 'Supports complete data flow: Weibo crawler -> HDFS -> Spark cleaning -> HBase -> dual dimension ranking');
  loadPreviewData();
  nextTick(() => {
    initRateChart();
    startRateTracking();
  });
  // ... (rest of the code remains the same)
  window.addEventListener('resize', () => rateChart?.resize());
});

onUnmounted(() => {
  stopStatusPolling();
  stopDataflowPolling();
  if (rateTimer) clearInterval(rateTimer);
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.data-collection-module {
  padding: $spacing-md;
}

// 数据流可视化样式
.dataflow-pipeline {
  background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
  border-radius: $border-radius-large;
  padding: $spacing-md;
  margin-bottom: $spacing-md;
  color: #fff;
}

.pipeline-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-large;
  font-weight: $font-weight-semibold;
  margin-bottom: $spacing-md;
  
  .el-icon {
    font-size: $font-size-extra-large;
  }
}

.pipeline-stages {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
}

.pipeline-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  position: relative;
  padding: $spacing-base $spacing-sm;
  background: rgba(255, 255, 255, 0.1);
  border-radius: $border-radius-base;
  transition: $transition-base;
  
  &.active {
    background: rgba(255, 255, 255, 0.25);
    transform: scale(1.05);
    box-shadow: $shadow-md;
  }
  
  &.completed {
    background: rgba($success-color, 0.3);
  }
  
  &.failed {
    background: rgba($danger-color, 0.3);
  }
}

.stage-icon {
  font-size: $font-size-hero;
  margin-bottom: $spacing-xs;
  
  .rotating {
    animation: rotate 1s linear infinite;
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.stage-name {
  font-size: $font-size-extra-small;
  text-align: center;
  margin-bottom: 5px;
}

.stage-progress {
  width: 80%;
  margin-top: 5px;
  
  :deep(.el-progress-bar__outer) {
    background: rgba(255, 255, 255, 0.3);
  }
  
  :deep(.el-progress-bar__inner) {
    background: #fff;
  }
}

.stage-count {
  font-size: $font-size-tiny;
  opacity: 0.8;
  margin-top: 5px;
}

.stage-arrow {
  position: absolute;
  right: -15px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  opacity: 0.6;
  z-index: 1;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  padding: $spacing-base;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
}

.status-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  
  .stats {
    font-size: $font-size-base;
    color: $text-regular;
    
    strong {
      color: $primary-color;
      font-size: 18px;
    }
  }
}

.progress-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

.progress-value {
  display: block;
  font-size: $font-size-hero;
  font-weight: $font-weight-bold;
  color: $primary-color;
}

.progress-label {
  display: block;
  font-size: $font-size-extra-small;
  color: $text-secondary;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-base;
  margin-top: $spacing-md;
  width: 100%;
}

.stat-item {
  text-align: center;
  
  .stat-value {
    display: block;
    font-size: 24px;
    font-weight: bold;
    
    &.success { color: $success-color; }
    &.danger { color: $danger-color; }
    &.warning { color: $warning-color; }
    &.info { color: $info-color; }
  }
  
  .stat-label {
    font-size: $font-size-extra-small;
    color: $text-secondary;
  }
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.keyword-input-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  
  .keyword-tag {
    margin: 4px 0;
  }
  
  .keyword-input {
    width: 120px;
    margin: 4px 0;
  }
  
  .button-new-keyword {
    margin: 4px 0;
  }
}

.keyword-suggestions {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  
  .suggestion-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
  
  .suggestion-tag {
    cursor: pointer;
    margin: 2px;
    
    &:hover {
      background-color: var(--el-color-primary-light-9);
    }
  }
}

.log-container {
  height: 300px;
  overflow-y: auto;
  overflow-y: auto;
  font-family: 'Consolas', monospace;
  font-size: $font-size-extra-small;
  background: #1e1e1e;
  border-radius: $border-radius-small;
  padding: $spacing-sm;
}

.log-item {
  padding: 4px 0;
  border-bottom: 1px solid #333;
  
  &.info { color: $info-color; }
  &.success { color: $success-color; }
  &.warn { color: $warning-color; }
  &.error { color: $danger-color; }
  
  .log-time {
    color: $text-regular;
    margin-right: $spacing-xs;
  }
  
  .log-level {
    margin-right: 8px;
    font-weight: bold;
  }
}

.preview-list {
  max-height: 280px;
  overflow-y: auto;
}

.preview-item {
  padding: $spacing-sm;
  border-bottom: 1px solid $border-base;
  
  &:last-child {
    border-bottom: none;
  }
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.preview-info {
  display: flex;
  flex-direction: column;
  
  .author {
    font-weight: $font-weight-medium;
    color: $text-primary;
  }
  
  .time {
    font-size: $font-size-extra-small;
    color: $text-secondary;
  }
}

.preview-content {
  font-size: $font-size-base;
  color: $text-regular;
  line-height: 1.5;
  margin-bottom: $spacing-xs;
}

.preview-meta {
  display: flex;
  gap: $spacing-base;
  font-size: $font-size-extra-small;
  color: $text-secondary;
  
  span {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.rate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: $font-weight-semibold;
}

.dedup-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  text-align: center;

  .dedup-item {
    .dedup-value {
      font-size: 20px;
      font-weight: 700;
      line-height: 1.3;

      &.total { color: $primary-color; }
      &.dup { color: $danger-color; }
      &.unique { color: $success-color; }
      &.rate { color: $warning-color; }
    }

    .dedup-label {
      font-size: $font-size-tiny;
      color: $text-secondary;
    }
  }
}
</style>
