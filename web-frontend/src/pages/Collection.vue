<template>
  <div class="collection-module">
    <!-- 三栏式仪表板布局 -->
    <div class="collection-layout">
      <!-- 左侧任务列表 -->
      <aside class="left-panel">
        <el-button type="primary" size="large" @click="handleCreate" class="create-btn" block>
          <el-icon><Plus /></el-icon>
          新建采集任务
        </el-button>
        
        <div class="task-search">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务..."
            :prefix-icon="Search"
            clearable
            @input="handleSearch"
          />
        </div>
        
        <div class="status-filter">
          <el-select v-model="statusFilter" placeholder="状态筛选" @change="handleStatusFilter">
            <el-option label="全部" value="" />
            <el-option label="运行中" value="running" />
            <el-option label="等待中" value="waiting" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </div>
        
        <div class="task-list">
          <div
            v-for="task in paginatedTasks"
            :key="task.id"
            class="task-card"
            :class="{ active: selectedTaskId === task.id }"
            @click="selectTask(task)"
          >
            <div class="task-header">
              <span class="task-name">{{ task.name }}</span>
              <el-tag :type="getStatusType(task.status)" size="small">
                {{ getStatusText(task.status) }}
              </el-tag>
            </div>
            <div class="task-keywords">
              <el-icon><PriceTag /></el-icon>
              {{ task.keywords.slice(0, 3).join(', ') }}
            </div>
            <el-progress
              v-if="task.status === 'running'"
              :percentage="task.progress"
              :stroke-width="6"
              :show-text="false"
            />
            <div class="task-actions">
              <el-button
                v-if="task.status === 'running'"
                type="warning"
                size="small"
                @click.stop="handlePause(task)"
              >
                暂停
              </el-button>
              <el-button
                v-else-if="task.status !== 'completed'"
                type="success"
                size="small"
                @click.stop="handleStart(task)"
              >
                启动
              </el-button>
              <el-button size="small" @click.stop="handleEdit(task)">编辑</el-button>
            </div>
          </div>
        </div>
      </aside>
      
      <!-- 中间实时监控区 -->
      <main class="center-panel">
        <div class="monitor-header">
          <h3>实时监控仪表板</h3>
        </div>
        
        <!-- 进度指标 -->
        <div class="progress-metrics">
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-chart">
                  <div ref="progressChartRef" style="width: 120px; height: 120px"></div>
                </div>
                <div class="metric-info">
                  <div class="metric-label">总进度</div>
                  <div class="metric-value">{{ currentProgress }}%</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <StatCard
                title="采集速度"
                :value="collectionSpeed"
                suffix="条/分"
                :icon="Timer"
                type="success"
              />
            </el-col>
            <el-col :span="6">
              <StatCard
                title="成功率"
                :value="successRate"
                suffix="%"
                :icon="CircleCheck"
                type="primary"
              />
            </el-col>
            <el-col :span="6">
              <StatCard
                title="预估剩余"
                :value="estimatedTime"
                suffix="分钟"
                :icon="Clock"
                type="warning"
              />
            </el-col>
          </el-row>
        </div>
        
        <!-- 实时数据流 -->
        <div class="data-flow">
          <el-row :gutter="16">
            <el-col :span="16">
              <el-card header="采集趋势">
                <div ref="trendChartRef" style="height: 300px"></div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card header="平台分布">
                <div ref="platformChartRef" style="height: 300px"></div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </main>
      
      <!-- 右侧配置快速入口 -->
      <aside class="right-panel">
        <el-card header="常用配置" class="config-card">
          <div class="config-item" @click="showKeywordManager = true">
            <el-icon><PriceTag /></el-icon>
            <span>关键词管理</span>
          </div>
          <div class="config-item" @click="showProxySettings = true">
            <el-icon><Connection /></el-icon>
            <span>代理设置</span>
          </div>
          <div class="config-item" @click="showSchedule = true">
            <el-icon><Calendar /></el-icon>
            <span>时间计划</span>
          </div>
        </el-card>
        
        <el-card header="最近活动" class="activity-card">
          <el-timeline>
            <el-timeline-item
              v-for="activity in recentActivities"
              :key="activity.id"
              :timestamp="activity.time"
              size="small"
            >
              {{ activity.content }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
        
        <el-card header="系统通知" class="notification-card">
          <el-alert
            v-for="notification in notifications"
            :key="notification.id"
            :title="notification.title"
            :type="notification.type"
            :closable="false"
            show-icon
            class="notification-item"
          />
        </el-card>
      </aside>
    </div>
    
    <!-- 原有对话框保留 -->
    <el-row :gutter="16" class="toolbar" style="display: none">
      <el-col :span="12">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon> 新建任务
        </el-button>
        <el-button type="danger" :disabled="selectedIds.length === 0" @click="handleBatchDelete">
          <el-icon><Delete /></el-icon> 批量删除
        </el-button>
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon> 刷新列表
        </el-button>
      </el-col>
      <el-col :span="12" class="search-area">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 120px; margin-right: 10px;" @change="handleStatusFilter">
          <el-option label="运行中" value="running" />
          <el-option label="等待中" value="waiting" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-input v-model="searchKeyword" placeholder="搜索关键词/任务名" style="width: 220px;" clearable @input="handleSearch">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </el-col>
    </el-row>

    <!-- 任务列表表格 -->
    <el-table
      v-loading="taskStore.loading"
      :data="paginatedTasks"
      style="width: 100%"
      @selection-change="handleSelectionChange"
      @sort-change="handleSortChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="id" label="任务ID" width="90" sortable="custom" />
      <el-table-column prop="name" label="任务名称" min-width="150" sortable="custom">
        <template #default="{ row }">
          <el-link type="primary" @click="handleEdit(row)">{{ row.name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="keywords" label="关键词" min-width="180">
        <template #default="{ row }">
          <el-tooltip v-if="row.keywords.length > 2" :content="row.keywords.join(', ')" placement="top">
            <span>{{ row.keywords.slice(0, 2).join(', ') }}...</span>
          </el-tooltip>
          <span v-else>{{ row.keywords.join(', ') }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="150">
        <template #default="{ row }">
          <el-progress 
            v-if="row.status === 'running'" 
            :percentage="row.progress" 
            :stroke-width="8"
            :status="row.progress === 100 ? 'success' : ''"
          />
          <span v-else-if="row.status === 'completed'">已完成</span>
          <span v-else-if="row.status === 'failed'" class="text-danger">失败于 {{ row.progress }}%</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" width="170" sortable="custom" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button 
            v-if="row.status === 'running'" 
            type="warning" 
            size="small" 
            @click="handlePause(row)"
          >暂停</el-button>
          <el-button 
            v-else-if="row.status !== 'completed'" 
            type="success" 
            size="small" 
            @click="handleStart(row)"
          >启动</el-button>
          <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          <el-button size="small" @click="handleViewLog(row)">日志</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页组件 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="taskStore.filteredTasks.length"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 新建/编辑任务对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新建任务'" width="500px">
      <el-form :model="taskForm" label-width="80px">
        <el-form-item label="任务名称">
          <el-input v-model="taskForm.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-select
            v-model="taskForm.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词后回车添加"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 日志对话框 -->
    <el-dialog v-model="logDialogVisible" title="任务日志" width="600px">
      <div class="log-content">
        <pre>{{ logContent }}</pre>
      </div>
    </el-dialog>

    <!-- 爬虫配置对话框 -->
    <CrawlerConfigDialog
      v-model="crawlerDialogVisible"
      :edit-data="crawlerEditData"
      @save="handleCrawlerSave"
    />

    <!-- 任务统计图表区域 -->
    <div class="statistics-section">
      <h3 class="section-header">任务统计</h3>
      <TaskStatistics />
    </div>

    <!-- 实时监控区域 -->
    <div class="monitor-section">
      <h3 class="section-header">实时监控</h3>
      <RealtimeMonitor />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Delete, Refresh, Search } from '@element-plus/icons-vue';
import { useTaskStore, type Task } from '@/store/task';
import CrawlerConfigDialog from '@/components/CrawlerConfigDialog.vue';
import RealtimeMonitor from '@/components/RealtimeMonitor.vue';
import TaskStatistics from '@/components/TaskStatistics.vue';

const taskStore = useTaskStore();

// 搜索和筛选
const searchKeyword = ref('');
const statusFilter = ref('');

// 分页
const currentPage = ref(1);
const pageSize = ref(10);

// 选中项
const selectedIds = ref<number[]>([]);

// 对话框
const dialogVisible = ref(false);
const isEdit = ref(false);
const editingId = ref<number | null>(null);
const taskForm = ref({ name: '', keywords: [] as string[] });

// 日志对话框
const logDialogVisible = ref(false);
const logContent = ref('');

// 爬虫配置对话框
const crawlerDialogVisible = ref(false);
const crawlerEditData = ref<any>(null);

// 计算分页后的数据
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return taskStore.filteredTasks.slice(start, end);
});

// 状态映射
function getStatusType(status: string) {
  const map: Record<string, string> = {
    running: 'success',
    waiting: 'warning',
    completed: 'info',
    failed: 'danger',
  };
  return map[status] || 'info';
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    running: '运行中',
    waiting: '等待中',
    completed: '已完成',
    failed: '失败',
  };
  return map[status] || status;
}

// 事件处理
function handleSearch() {
  taskStore.setSearchKeyword(searchKeyword.value);
  currentPage.value = 1;
}

function handleStatusFilter() {
  taskStore.setStatusFilter(statusFilter.value);
  currentPage.value = 1;
}

function handleSelectionChange(selection: Task[]) {
  selectedIds.value = selection.map(t => t.id);
}

function handleSortChange({ prop, order }: { prop: string; order: 'ascending' | 'descending' | null }) {
  taskStore.setSort(prop, order);
}

function handlePageChange(page: number) {
  currentPage.value = page;
}

function handleSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
}

function handleRefresh() {
  taskStore.fetchTasks();
  ElMessage.success('列表已刷新');
}

function handleCreate() {
  crawlerEditData.value = null;
  crawlerDialogVisible.value = true;
}

function handleCrawlerSave(data: any, startNow: boolean) {
  // 将爬虫配置转换为任务
  const keywords = data.keywords.map((k: any) => k.word);
  taskStore.createTask({
    name: data.name,
    keywords: keywords,
  }).then((task) => {
    if (startNow && task) {
      taskStore.startTask(task.id);
    }
  });
}

function handleEdit(row: Task) {
  isEdit.value = true;
  editingId.value = row.id;
  taskForm.value = { name: row.name, keywords: [...row.keywords] };
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!taskForm.value.name) {
    ElMessage.warning('请输入任务名称');
    return;
  }
  
  if (isEdit.value && editingId.value) {
    await taskStore.updateTask(editingId.value, taskForm.value);
    ElMessage.success('任务已更新');
  } else {
    await taskStore.createTask(taskForm.value);
    ElMessage.success('任务已创建');
  }
  dialogVisible.value = false;
}

async function handleDelete(row: Task) {
  await ElMessageBox.confirm(`确定删除任务 "${row.name}" 吗？`, '确认删除', { type: 'warning' });
  await taskStore.deleteTask(row.id);
  ElMessage.success('任务已删除');
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个任务吗？`, '确认删除', { type: 'warning' });
  await taskStore.deleteTasks(selectedIds.value);
  selectedIds.value = [];
  ElMessage.success('任务已批量删除');
}

async function handleStart(row: Task) {
  await taskStore.startTask(row.id);
  ElMessage.success(`任务 "${row.name}" 已启动`);
}

async function handlePause(row: Task) {
  await taskStore.pauseTask(row.id);
  ElMessage.success(`任务 "${row.name}" 已暂停`);
}

function handleViewLog(row: Task) {
  logContent.value = `[${row.createdAt}] 任务创建: ${row.name}
[${row.createdAt}] 关键词配置: ${row.keywords.join(', ')}
[${row.updatedAt}] 状态更新: ${getStatusText(row.status)}
${row.status === 'running' ? `[${new Date().toLocaleString()}] 当前进度: ${row.progress}%` : ''}
${row.status === 'failed' ? `[${row.updatedAt}] 错误: 网络连接超时，请检查配置后重试` : ''}
${row.status === 'completed' ? `[${row.updatedAt}] 任务完成，共采集数据 ${Math.floor(Math.random() * 10000)} 条` : ''}`;
  logDialogVisible.value = true;
}

// 初始化
onMounted(() => {
  taskStore.fetchTasks();
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.collection-module {
  height: calc(100vh - 120px);
  overflow: hidden;
}

.collection-layout {
  display: flex;
  gap: $spacing-sm;
  height: 100%;
}

// 左侧任务列表
.left-panel {
  width: 30%;
  background: $bg-white;
  border-radius: $border-radius-base;
  padding: $spacing-md;
  overflow-y: auto;
  box-shadow: $box-shadow-base;
  
  .create-btn {
    margin-bottom: $spacing-sm;
    height: 48px;
    font-size: $font-size-medium;
  }
  
  .task-search {
    margin-bottom: $spacing-sm;
  }
  
  .status-filter {
    margin-bottom: $spacing-md;
    
    :deep(.el-select) {
      width: 100%;
    }
  }
  
  .task-list {
    .task-card {
      padding: $spacing-sm;
      margin-bottom: $spacing-xs;
      border: 1px solid $border-lighter;
      border-radius: $border-radius-base;
      cursor: pointer;
      transition: $transition-fast;
      
      &:hover {
        border-color: $primary-color;
        box-shadow: $box-shadow-light;
      }
      
      &.active {
        border-color: $primary-color;
        background: rgba(64, 158, 255, 0.05);
      }
      
      .task-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: $spacing-xs;
        
        .task-name {
          font-weight: $font-weight-medium;
          color: $text-primary;
        }
      }
      
      .task-keywords {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: $font-size-small;
        color: $text-secondary;
        margin-bottom: $spacing-xs;
      }
      
      .task-actions {
        display: flex;
        gap: $spacing-xs;
        margin-top: $spacing-xs;
      }
    }
  }
}

// 中间监控区
.center-panel {
  flex: 1;
  overflow-y: auto;
  
  .monitor-header {
    background: $bg-white;
    padding: $spacing-md;
    border-radius: $border-radius-base;
    margin-bottom: $spacing-sm;
    box-shadow: $box-shadow-base;
    
    h3 {
      margin: 0;
      font-size: $font-size-large;
      color: $text-primary;
    }
  }
  
  .progress-metrics {
    margin-bottom: $spacing-sm;
    
    .metric-card {
      background: $bg-white;
      padding: $spacing-md;
      border-radius: $border-radius-base;
      box-shadow: $box-shadow-base;
      text-align: center;
      
      .metric-chart {
        margin: 0 auto $spacing-sm;
      }
      
      .metric-label {
        font-size: $font-size-base;
        color: $text-secondary;
        margin-bottom: 4px;
      }
      
      .metric-value {
        font-size: $font-size-extra-large;
        font-weight: $font-weight-bold;
        color: $primary-color;
      }
    }
  }
  
  .data-flow {
    :deep(.el-card) {
      box-shadow: $box-shadow-base;
    }
  }
}

// 右侧配置面板
.right-panel {
  width: 20%;
  overflow-y: auto;
  
  .config-card,
  .activity-card,
  .notification-card {
    margin-bottom: $spacing-sm;
    box-shadow: $box-shadow-base;
    
    .config-item {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      padding: $spacing-sm;
      border-radius: $border-radius-base;
      cursor: pointer;
      transition: $transition-fast;
      
      &:hover {
        background: $bg-hover;
        color: $primary-color;
      }
    }
  }
  
  .notification-item {
    margin-bottom: $spacing-xs;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
}

.collection-container {
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
  display: none;
}
.toolbar {
  margin-bottom: 20px;
}
.search-area {
  display: flex;
  justify-content: flex-end;
}
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.text-danger {
  color: #f56c6c;
}
.log-content {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}
.log-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.statistics-section,
.monitor-section {
  margin-top: 20px;
}
.section-header {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #409eff;
}
</style>
