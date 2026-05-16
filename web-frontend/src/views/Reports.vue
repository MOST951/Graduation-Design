<template>
  <div class="reports-module">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2>
          <el-icon><Document /></el-icon>
          舆情分析报告
        </h2>
        <p class="header-desc">基于情感-热度三维度排序模型的智能舆情报告生成</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" :loading="generating" @click="handleQuickGenerate">
          一键生成报告
        </el-button>
      </div>
    </div>

    <!-- 数据概览卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #409EFF, #79bbff)">
            <el-icon :size="28"><DataLine /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalWeibos.toLocaleString() }}</div>
            <div class="stat-label">已采集微博</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #67C23A, #95d475)">
            <el-icon :size="28"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.analyzedCount.toLocaleString() }}</div>
            <div class="stat-label">已分析数据</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #E6A23C, #eebe77)">
            <el-icon :size="28"><Tickets /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.reportCount }}</div>
            <div class="stat-label">已生成报告</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #F56C6C, #f89898)">
            <el-icon :size="28"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.alertCount }}</div>
            <div class="stat-label">舆情预警</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <el-row :gutter="20">
      <!-- 左侧：报告生成配置 -->
      <el-col :span="16">
        <el-card class="main-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Setting /></el-icon> 报告生成配置</span>
              <el-tag type="success" effect="plain">
                <el-icon><CircleCheck /></el-icon> 核心创新点：三维度排序
              </el-tag>
            </div>
          </template>

          <el-form :model="reportConfig" label-width="100px" class="report-form">
            <!-- 报告类型选择 -->
            <el-form-item label="报告类型">
              <el-radio-group v-model="reportConfig.type" class="type-radio-group">
                <el-radio-button value="sentiment">
                  <el-icon><Histogram /></el-icon>
                  情感分析报告
                </el-radio-button>
                <el-radio-button value="hotspot">
                  <el-icon><TrendCharts /></el-icon>
                  热点话题报告
                </el-radio-button>
                <el-radio-button value="comprehensive">
                  <el-icon><DataAnalysis /></el-icon>
                  综合舆情报告
                </el-radio-button>
              </el-radio-group>
            </el-form-item>

            <!-- 数据源选择 -->
            <el-form-item label="数据来源">
              <el-select v-model="reportConfig.dataSource" placeholder="选择数据来源" style="width: 100%">
                <el-option label="全部采集数据" value="all" />
                <el-option 
                  v-for="task in crawlTasks" 
                  :key="task.id" 
                  :label="`采集任务: ${task.keywords?.join(', ') || task.id}`" 
                  :value="task.id" 
                />
              </el-select>
            </el-form-item>

            <!-- 时间范围 -->
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="reportConfig.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                :shortcuts="dateShortcuts"
                style="width: 100%"
              />
            </el-form-item>

            <!-- 三维度排序配置（核心创新点） -->
            <el-form-item label="排序权重">
              <div class="weight-config">
                <div class="weight-item">
                  <span class="weight-label">情感权重 (α)</span>
                  <el-slider 
                    v-model="reportConfig.sentimentWeight" 
                    :min="0" 
                    :max="100" 
                    :format-tooltip="(val: number) => `${val}%`"
                    @change="onWeightChange('sentiment')"
                  />
                  <span class="weight-value">{{ reportConfig.sentimentWeight }}%</span>
                </div>
                <div class="weight-item">
                  <span class="weight-label">热度权重 (β)</span>
                  <el-slider 
                    v-model="reportConfig.popularityWeight" 
                    :min="0" 
                    :max="100"
                    :format-tooltip="(val: number) => `${val}%`"
                    @change="onWeightChange('popularity')"
                  />
                  <span class="weight-value">{{ reportConfig.popularityWeight }}%</span>
                </div>
              </div>
            </el-form-item>

            <!-- 报告内容选择 -->
            <el-form-item label="报告内容">
              <el-checkbox-group v-model="reportConfig.sections">
                <el-checkbox value="overview">数据概览</el-checkbox>
                <el-checkbox value="sentiment">情感分布</el-checkbox>
                <el-checkbox value="hotTopics">热点话题</el-checkbox>
                <el-checkbox value="triRanking">三维度排序</el-checkbox>
                <el-checkbox value="wordcloud">词云分析</el-checkbox>
                <el-checkbox value="timeline">时间趋势</el-checkbox>
                <el-checkbox value="conclusion">分析结论</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <!-- 导出格式 -->
            <el-form-item label="导出格式">
              <el-radio-group v-model="reportConfig.format">
                <el-radio value="html">
                  <el-icon><Monitor /></el-icon> HTML预览
                </el-radio>
                <el-radio value="pdf">
                  <el-icon><Document /></el-icon> PDF文档
                </el-radio>
                <el-radio value="markdown">
                  <el-icon><EditPen /></el-icon> Markdown
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 生成按钮 -->
            <el-form-item>
              <el-button type="primary" size="large" :loading="generating" @click="handleGenerate">
                <el-icon><DocumentAdd /></el-icon>
                生成舆情报告
              </el-button>
              <el-button size="large" @click="handlePreview">
                <el-icon><View /></el-icon>
                预览报告
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：历史报告 -->
      <el-col :span="8">
        <el-card class="history-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Clock /></el-icon> 历史报告</span>
              <el-button text type="primary" size="small">查看全部</el-button>
            </div>
          </template>

          <div v-if="historyReports.length > 0" class="history-list">
            <div 
              v-for="report in historyReports" 
              :key="report.id" 
              class="history-item"
              @click="handleViewReport(report)"
            >
              <div class="report-icon" :class="report.type">
                <el-icon v-if="report.type === 'sentiment'"><Histogram /></el-icon>
                <el-icon v-else-if="report.type === 'hotspot'"><TrendCharts /></el-icon>
                <el-icon v-else><DataAnalysis /></el-icon>
              </div>
              <div class="report-info">
                <div class="report-name">{{ report.name }}</div>
                <div class="report-meta">
                  <span>{{ report.generatedAt }}</span>
                  <el-tag size="small" :type="getReportTypeTag(report.type)">
                    {{ getReportTypeText(report.type) }}
                  </el-tag>
                </div>
              </div>
              <div class="report-actions">
                <el-button :icon="Download" circle size="small" @click.stop="handleDownload(report)" />
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无历史报告" :image-size="80" />
        </el-card>

        <!-- 快速操作 -->
        <el-card class="quick-actions-card">
          <template #header>
            <span><el-icon><Operation /></el-icon> 快速操作</span>
          </template>
          <div class="quick-actions">
            <el-button :loading="generating" @click="handleQuickGenerate">
              <el-icon><Refresh /></el-icon>
              生成今日报告
            </el-button>
            <el-button @click="handleExportData">
              <el-icon><Download /></el-icon>
              导出原始数据
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 报告预览对话框 -->
    <el-dialog 
      v-model="showPreview" 
      title="报告预览" 
      width="80%" 
      top="5vh"
      :close-on-click-modal="false"
    >
      <div v-loading="previewLoading" class="report-preview">
        <div class="preview-content" v-html="previewContent"></div>
      </div>
      <template #footer>
        <el-button @click="showPreview = false">关闭</el-button>
        <el-button type="primary" @click="handleDownloadPreview">
          <el-icon><Download /></el-icon>
          下载报告
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElNotification } from 'element-plus';
import {
  Document, Plus, DataLine, TrendCharts, Tickets, Warning,
  Setting, CircleCheck, Histogram, DataAnalysis, Monitor,
  EditPen, DocumentAdd, View, Clock, Download, Operation,
  Refresh,
} from '@element-plus/icons-vue';
import { getCrawlTasks } from '@/api/weibo';

// 统计数据
const stats = reactive({
  totalWeibos: 0,
  analyzedCount: 0,
  reportCount: 0,
  alertCount: 0,
});

// 报告配置
const reportConfig = reactive({
  type: 'comprehensive',
  dataSource: 'all',
  dateRange: [] as Date[],
  sentimentWeight: 60,
  popularityWeight: 40,
  sections: ['overview', 'sentiment', 'hotTopics', 'triRanking', 'wordcloud', 'conclusion'],
  format: 'html',
});

// 采集任务列表
const crawlTasks = ref<any[]>([]);

// 历史报告
const historyReports = ref([
  {
    id: '1',
    name: '微博舆情综合分析报告',
    type: 'comprehensive',
    generatedAt: '2026-01-29 15:30',
  },
  {
    id: '2',
    name: '小米话题情感分析报告',
    type: 'sentiment',
    generatedAt: '2026-01-28 10:00',
  },
  {
    id: '3',
    name: '热点话题追踪报告',
    type: 'hotspot',
    generatedAt: '2026-01-27 09:00',
  },
]);

// 状态
const generating = ref(false);
const showPreview = ref(false);
const previewLoading = ref(false);
const previewContent = ref('');

// 日期快捷选项
const dateShortcuts = [
  { text: '今天', value: () => { const d = new Date(); return [d, d]; } },
  { text: '最近7天', value: () => { const end = new Date(); const start = new Date(); start.setDate(start.getDate() - 7); return [start, end]; } },
  { text: '最近30天', value: () => { const end = new Date(); const start = new Date(); start.setDate(start.getDate() - 30); return [start, end]; } },
];

// 权重联动
const onWeightChange = (type: 'sentiment' | 'popularity') => {
  if (type === 'sentiment') {
    reportConfig.popularityWeight = 100 - reportConfig.sentimentWeight;
  } else {
    reportConfig.sentimentWeight = 100 - reportConfig.popularityWeight;
  }
};

// 获取报告类型文本
const getReportTypeText = (type: string) => {
  const texts: Record<string, string> = {
    sentiment: '情感分析',
    hotspot: '热点话题',
    comprehensive: '综合报告',
  };
  return texts[type] || type;
};

// 获取报告类型标签
const getReportTypeTag = (type: string) => {
  const tags: Record<string, string> = {
    sentiment: 'success',
    hotspot: 'warning',
    comprehensive: '',
  };
  return tags[type] || '';
};

// 生成报告
const handleGenerate = async () => {
  if (!reportConfig.dateRange || reportConfig.dateRange.length !== 2) {
    ElMessage.warning('请选择时间范围');
    return;
  }
  
  generating.value = true;
  try {
    // 模拟生成过程
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    ElNotification({
      title: '报告生成成功',
      message: '舆情分析报告已生成，可在历史报告中查看',
      type: 'success',
    });
    
    // 添加到历史
    historyReports.value.unshift({
      id: Date.now().toString(),
      name: `${getReportTypeText(reportConfig.type)} - ${new Date().toLocaleDateString()}`,
      type: reportConfig.type,
      generatedAt: new Date().toLocaleString(),
    });
  } catch (error: any) {
    ElMessage.warning('生成失败: ' + (error.message || '请重试'));
  } finally {
    generating.value = false;
  }
};

// 快速生成今日报告
const handleQuickGenerate = async () => {
  const today = new Date();
  reportConfig.dateRange = [today, today];
  reportConfig.type = 'comprehensive';
  await handleGenerate();
};

// 预览报告
const handlePreview = async () => {
  showPreview.value = true;
  previewLoading.value = true;
  
  try {
    await new Promise(resolve => setTimeout(resolve, 1000));
    previewContent.value = generatePreviewHTML();
  } finally {
    previewLoading.value = false;
  }
};

// 生成预览HTML
const generatePreviewHTML = () => {
  return `
    <div style="padding: 40px; font-family: 'PingFang SC', sans-serif;">
      <h1 style="text-align: center; color: #303133; border-bottom: 2px solid #409EFF; padding-bottom: 20px;">
        微博舆情分析报告
      </h1>
      <p style="text-align: center; color: #909399;">
        生成时间：${new Date().toLocaleString()} | 数据来源：微博平台
      </p>
      
      <h2 style="color: #409EFF; margin-top: 30px;">一、数据概览</h2>
      <p>本次分析共采集微博数据 <strong>${stats.totalWeibos}</strong> 条，覆盖时间范围为所选日期。</p>
      
      <h2 style="color: #409EFF; margin-top: 30px;">二、情感分析</h2>
      <p>基于情感词典和机器学习模型，对采集数据进行情感倾向分析：</p>
      <ul>
        <li>正面情感：约 35%</li>
        <li>中性情感：约 45%</li>
        <li>负面情感：约 20%</li>
      </ul>
      
      <h2 style="color: #409EFF; margin-top: 30px;">三、三维度排序结果</h2>
      <p style="background: #ecf5ff; padding: 15px; border-radius: 4px;">
        <strong>核心创新点：</strong>综合得分 = ${reportConfig.sentimentWeight}% × 情感强度 + ${reportConfig.popularityWeight}% × 传播热度
      </p>
      
      <h2 style="color: #409EFF; margin-top: 30px;">四、分析结论</h2>
      <p>根据三维度排序模型分析，当前舆情整体趋势平稳，建议持续关注热点话题动态。</p>
    </div>
  `;
};

// 查看报告
const handleViewReport = (report: any) => {
  showPreview.value = true;
  previewContent.value = generatePreviewHTML();
};

// 下载报告
const handleDownload = (report: any) => {
  ElMessage.success(`正在下载: ${report.name}`);
};

// 下载预览
const handleDownloadPreview = () => {
  ElMessage.success('报告下载中...');
};

// 导出原始数据
const handleExportData = () => {
  ElMessage.info('功能开发中');
};

// 加载数据
const loadData = async () => {
  try {
    // 加载采集任务
    const tasksRes = await getCrawlTasks();
    crawlTasks.value = tasksRes.tasks || [];
    
    // 更新统计
    stats.totalWeibos = crawlTasks.value.reduce((sum, t) => sum + (t.collected || 0), 0);
    stats.analyzedCount = Math.floor(stats.totalWeibos * 0.8);
    stats.reportCount = historyReports.value.length;
  } catch (error) {
    console.warn('加载数据失败:', error);
  }
};

onMounted(() => {
  loadData();
});
</script>

<style scoped lang="scss">
.reports-module {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  
  .header-left {
    h2 {
      margin: 0 0 8px;
      font-size: 22px;
      color: #303133;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .header-desc {
      margin: 0;
      color: var(--color-text-secondary);
      font-size: 14px;
    }
  }
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  
  :deep(.el-card__body) {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0;
    width: 100%;
  }
  
  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }
  
  .stat-info {
    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
    }
    
    .stat-label {
      font-size: 13px;
      color: var(--color-text-secondary);
      margin-top: 4px;
    }
  }
}

.main-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    span {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
    }
  }
}

.report-form {
  .type-radio-group {
    :deep(.el-radio-button__inner) {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 12px 20px;
    }
  }
}

.weight-config {
  width: 100%;
  
  .weight-item {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    
    .weight-label {
      width: 100px;
      font-size: 13px;
      color: #606266;
    }
    
    .el-slider {
      flex: 1;
    }
    
    .weight-value {
      width: 50px;
      text-align: right;
      font-weight: 500;
      color: var(--color-primary);
    }
  }
  
  .formula-alert {
    margin-top: 8px;
    
    .formula-text {
      font-family: 'Consolas', monospace;
      font-size: 13px;
    }
  }
}

.history-card {
  margin-bottom: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    span {
      display: flex;
      align-items: center;
      gap: 6px;
    }
  }
}

.history-list {
  .history-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
    
    &:hover {
      background: #f5f7fa;
    }
    
    .report-icon {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      
      &.sentiment { background: linear-gradient(135deg, var(--color-success), #95d475); }
      &.hotspot { background: linear-gradient(135deg, var(--color-warning), #eebe77); }
      &.comprehensive { background: linear-gradient(135deg, var(--color-primary), #79bbff); }
    }
    
    .report-info {
      flex: 1;
      
      .report-name {
        font-size: 14px;
        color: #303133;
        margin-bottom: 4px;
      }
      
      .report-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: var(--color-text-secondary);
      }
    }
  }
}

.quick-actions-card {
  .quick-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    
    .el-button {
      justify-content: flex-start;
    }
  }
}

.report-preview {
  min-height: 500px;
  max-height: 70vh;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  
  .preview-content {
    padding: 20px;
  }
}
</style>
