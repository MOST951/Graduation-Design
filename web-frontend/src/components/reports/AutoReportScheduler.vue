<template>
  <div class="auto-report-scheduler">
    <div class="scheduler-header">
      <h2>自动化报告</h2>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
        创建定时任务
      </el-button>
    </div>
    
    <el-tabs v-model="activeTab">
      <!-- 任务列表 -->
      <el-tab-pane label="任务列表" name="tasks">
        <div class="tasks-toolbar">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务..."
            :prefix-icon="Search"
            clearable
            style="width: 300px"
          />
          
          <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 150px">
            <el-option label="全部" value="" />
            <el-option label="启用" value="enabled" />
            <el-option label="暂停" value="paused" />
            <el-option label="运行中" value="running" />
          </el-select>
          
          <el-select v-model="typeFilter" placeholder="报告类型" clearable style="width: 150px">
            <el-option label="全部" value="" />
            <el-option label="日报" value="daily" />
            <el-option label="周报" value="weekly" />
            <el-option label="月报" value="monthly" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </div>
        
        <el-table :data="filteredTasks" v-loading="isLoading">
          <el-table-column prop="name" label="任务名称" width="200" />
          
          <el-table-column prop="type" label="报告类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getTypeTagType(row.type)">
                {{ getTypeText(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="schedule" label="执行周期" width="150">
            <template #default="{ row }">
              {{ getScheduleText(row.schedule) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="nextRun" label="下次执行" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.nextRun) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="lastRun" label="上次执行" width="180">
            <template #default="{ row }">
              {{ row.lastRun ? formatDateTime(row.lastRun) : '-' }}
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button
                size="small"
                :icon="VideoPlay"
                @click="handleRunTask(row)"
                :disabled="row.status === 'running'"
              >
                立即执行
              </el-button>
              
              <el-button
                v-if="row.status === 'enabled'"
                size="small"
                :icon="VideoPause"
                @click="handlePauseTask(row)"
              >
                暂停
              </el-button>
              
              <el-button
                v-if="row.status === 'paused'"
                size="small"
                :icon="VideoPlay"
                type="success"
                @click="handleResumeTask(row)"
              >
                恢复
              </el-button>
              
              <el-dropdown @command="(cmd) => handleTaskAction(cmd, row)">
                <el-button size="small">
                  更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit" :icon="Edit">编辑</el-dropdown-item>
                    <el-dropdown-item command="logs" :icon="Document">查看日志</el-dropdown-item>
                    <el-dropdown-item command="history" :icon="Clock">执行历史</el-dropdown-item>
                    <el-dropdown-item command="delete" :icon="Delete">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      
      <!-- 执行历史 -->
      <el-tab-pane label="执行历史" name="history">
        <TaskExecutionHistory />
      </el-tab-pane>
      
      <!-- 任务统计 -->
      <el-tab-pane label="统计分析" name="statistics">
        <TaskStatistics />
      </el-tab-pane>
    </el-tabs>
    
    <!-- 创建/编辑任务对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTask ? '编辑任务' : '创建定时任务'"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="taskFormRef"
        :model="taskForm"
        :rules="taskFormRules"
        label-width="120px"
      >
        <el-tabs v-model="activeFormTab">
          <!-- 基本信息 -->
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="任务名称" prop="name">
              <el-input v-model="taskForm.name" placeholder="例如：每日情感分析报告" />
            </el-form-item>
            
            <el-form-item label="描述">
              <el-input
                v-model="taskForm.description"
                type="textarea"
                :rows="3"
                placeholder="任务描述"
              />
            </el-form-item>
            
            <el-form-item label="报告类型" prop="type">
              <el-select v-model="taskForm.type" style="width: 100%">
                <el-option label="日报" value="daily" />
                <el-option label="周报" value="weekly" />
                <el-option label="月报" value="monthly" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="报告模板" prop="templateId">
              <el-select v-model="taskForm.templateId" style="width: 100%">
                <el-option
                  v-for="template in templates"
                  :key="template.id"
                  :label="template.name"
                  :value="template.id"
                />
              </el-select>
            </el-form-item>
          </el-tab-pane>
          
          <!-- 数据源配置 -->
          <el-tab-pane label="数据源" name="datasource">
            <el-form-item label="时间范围">
              <el-radio-group v-model="taskForm.dataSource.timeRangeType">
                <el-radio label="relative">相对时间</el-radio>
                <el-radio label="absolute">绝对时间</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item v-if="taskForm.dataSource.timeRangeType === 'relative'" label="相对范围">
              <el-select v-model="taskForm.dataSource.relativeRange" style="width: 100%">
                <el-option label="最近1天" value="1d" />
                <el-option label="最近7天" value="7d" />
                <el-option label="最近30天" value="30d" />
                <el-option label="最近90天" value="90d" />
                <el-option label="本周" value="thisWeek" />
                <el-option label="上周" value="lastWeek" />
                <el-option label="本月" value="thisMonth" />
                <el-option label="上月" value="lastMonth" />
              </el-select>
            </el-form-item>
            
            <el-form-item v-if="taskForm.dataSource.timeRangeType === 'absolute'" label="时间范围">
              <el-date-picker
                v-model="taskForm.dataSource.absoluteRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item label="关键词">
              <el-select
                v-model="taskForm.dataSource.keywords"
                multiple
                filterable
                allow-create
                placeholder="输入关键词"
                style="width: 100%"
              >
                <el-option
                  v-for="keyword in suggestedKeywords"
                  :key="keyword"
                  :label="keyword"
                  :value="keyword"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="采集任务">
              <el-select
                v-model="taskForm.dataSource.collectionTasks"
                multiple
                placeholder="选择采集任务"
                style="width: 100%"
              >
                <el-option
                  v-for="task in collectionTasks"
                  :key="task.id"
                  :label="task.name"
                  :value="task.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="数据筛选">
              <el-button size="small" :icon="Plus" @click="addFilter">
                添加筛选条件
              </el-button>
              
              <div
                v-for="(filter, index) in taskForm.dataSource.filters"
                :key="index"
                class="filter-item"
              >
                <el-select v-model="filter.field" placeholder="字段" style="width: 150px">
                  <el-option label="情感" value="sentiment" />
                  <el-option label="地区" value="region" />
                  <el-option label="来源" value="source" />
                  <el-option label="用户类型" value="userType" />
                </el-select>
                
                <el-select v-model="filter.operator" placeholder="操作符" style="width: 120px">
                  <el-option label="等于" value="equals" />
                  <el-option label="包含" value="contains" />
                  <el-option label="大于" value="greater" />
                  <el-option label="小于" value="less" />
                </el-select>
                
                <el-input v-model="filter.value" placeholder="值" style="width: 200px" />
                
                <el-button :icon="Delete" @click="removeFilter(index)" />
              </div>
            </el-form-item>
          </el-tab-pane>
          
          <!-- 调度配置 -->
          <el-tab-pane label="调度配置" name="schedule">
            <el-form-item label="执行周期" prop="schedule.frequency">
              <el-radio-group v-model="taskForm.schedule.frequency">
                <el-radio label="daily">每天</el-radio>
                <el-radio label="weekly">每周</el-radio>
                <el-radio label="monthly">每月</el-radio>
                <el-radio label="cron">自定义</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item v-if="taskForm.schedule.frequency === 'daily'" label="执行时间">
              <el-time-picker
                v-model="taskForm.schedule.time"
                format="HH:mm"
                placeholder="选择时间"
              />
            </el-form-item>
            
            <el-form-item v-if="taskForm.schedule.frequency === 'weekly'" label="星期">
              <el-checkbox-group v-model="taskForm.schedule.weekdays">
                <el-checkbox label="1">周一</el-checkbox>
                <el-checkbox label="2">周二</el-checkbox>
                <el-checkbox label="3">周三</el-checkbox>
                <el-checkbox label="4">周四</el-checkbox>
                <el-checkbox label="5">周五</el-checkbox>
                <el-checkbox label="6">周六</el-checkbox>
                <el-checkbox label="7">周日</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item v-if="taskForm.schedule.frequency === 'monthly'" label="日期">
              <el-select v-model="taskForm.schedule.dayOfMonth" placeholder="选择日期">
                <el-option
                  v-for="day in 31"
                  :key="day"
                  :label="`${day}日`"
                  :value="day"
                />
                <el-option label="最后一天" :value="-1" />
              </el-select>
            </el-form-item>
            
            <el-form-item v-if="taskForm.schedule.frequency === 'cron'" label="Cron表达式">
              <el-input
                v-model="taskForm.schedule.cron"
                placeholder="例如：0 9 * * *"
              />
              <div class="form-tip">
                格式：分 时 日 月 周，例如 "0 9 * * *" 表示每天9:00执行
              </div>
            </el-form-item>
            
            <el-divider />
            
            <el-form-item label="触发条件">
              <el-checkbox v-model="taskForm.schedule.enableConditions">
                启用条件触发
              </el-checkbox>
            </el-form-item>
            
            <template v-if="taskForm.schedule.enableConditions">
              <el-form-item label="条件类型">
                <el-select v-model="taskForm.schedule.conditionType" style="width: 100%">
                  <el-option label="数据量达到阈值" value="dataThreshold" />
                  <el-option label="情感变化超过阈值" value="sentimentChange" />
                  <el-option label="特定事件发生" value="event" />
                </el-select>
              </el-form-item>
              
              <el-form-item
                v-if="taskForm.schedule.conditionType === 'dataThreshold'"
                label="数据量阈值"
              >
                <el-input-number
                  v-model="taskForm.schedule.threshold"
                  :min="0"
                  style="width: 200px"
                />
              </el-form-item>
              
              <el-form-item
                v-if="taskForm.schedule.conditionType === 'sentimentChange'"
                label="变化阈值(%)"
              >
                <el-input-number
                  v-model="taskForm.schedule.changeThreshold"
                  :min="0"
                  :max="100"
                  style="width: 200px"
                />
              </el-form-item>
            </template>
          </el-tab-pane>
          
          <!-- 接收人配置 -->
          <el-tab-pane label="接收人" name="recipients">
            <el-form-item label="发送方式">
              <el-checkbox-group v-model="taskForm.delivery.methods">
                <el-checkbox label="email">邮件</el-checkbox>
                <el-checkbox label="system">系统通知</el-checkbox>
                <el-checkbox label="webhook">Webhook</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item
              v-if="taskForm.delivery.methods.includes('email')"
              label="邮箱地址"
            >
              <el-select
                v-model="taskForm.delivery.emails"
                multiple
                filterable
                allow-create
                placeholder="输入邮箱地址"
                style="width: 100%"
              >
                <el-option
                  v-for="email in suggestedEmails"
                  :key="email"
                  :label="email"
                  :value="email"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="用户组">
              <el-select
                v-model="taskForm.delivery.userGroups"
                multiple
                placeholder="选择用户组"
                style="width: 100%"
              >
                <el-option label="管理员" value="admin" />
                <el-option label="分析师" value="analyst" />
                <el-option label="运营" value="operator" />
              </el-select>
            </el-form-item>
            
            <el-form-item
              v-if="taskForm.delivery.methods.includes('webhook')"
              label="Webhook URL"
            >
              <el-input
                v-model="taskForm.delivery.webhookUrl"
                placeholder="https://example.com/webhook"
              />
            </el-form-item>
            
            <el-form-item label="邮件主题">
              <el-input
                v-model="taskForm.delivery.emailSubject"
                placeholder="例如：{{reportType}} - {{reportDate}}"
              />
            </el-form-item>
            
            <el-form-item label="导出格式">
              <el-checkbox-group v-model="taskForm.delivery.formats">
                <el-checkbox label="pdf">PDF</el-checkbox>
                <el-checkbox label="word">Word</el-checkbox>
                <el-checkbox label="excel">Excel</el-checkbox>
                <el-checkbox label="html">HTML</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTask">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 任务日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="任务日志" width="800px">
      <TaskLogs v-if="showLogsDialog" :task-id="selectedTaskId" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Plus, Search, VideoPlay, VideoPause, Edit, Delete, Document,
  Clock, ArrowDown,
} from '@element-plus/icons-vue';
import TaskExecutionHistory from './TaskExecutionHistory.vue';
import TaskStatistics from './TaskStatistics.vue';
import TaskLogs from './TaskLogs.vue';

// State
const activeTab = ref('tasks');
const activeFormTab = ref('basic');
const searchKeyword = ref('');
const statusFilter = ref('');
const typeFilter = ref('');
const isLoading = ref(false);
const showCreateDialog = ref(false);
const showLogsDialog = ref(false);
const editingTask = ref<any>(null);
const selectedTaskId = ref('');

const taskFormRef = ref();

const tasks = ref<any[]>([
  {
    id: 'task-1',
    name: '每日情感分析报告',
    type: 'daily',
    templateId: 'template-1',
    schedule: {
      frequency: 'daily',
      time: '09:00',
    },
    status: 'enabled',
    nextRun: new Date(Date.now() + 86400000).toISOString(),
    lastRun: new Date(Date.now() - 86400000).toISOString(),
    lastStatus: 'success',
  },
]);

const templates = ref<any[]>([
  { id: 'template-1', name: '日报模板' },
  { id: 'template-2', name: '周报模板' },
]);

const collectionTasks = ref<any[]>([
  { id: 'collection-1', name: '微博采集任务1' },
  { id: 'collection-2', name: '微博采集任务2' },
]);

const suggestedKeywords = ref(['人工智能', '机器学习', '深度学习']);
const suggestedEmails = ref(['admin@example.com', 'analyst@example.com']);

const taskForm = ref({
  name: '',
  description: '',
  type: 'daily',
  templateId: '',
  dataSource: {
    timeRangeType: 'relative',
    relativeRange: '1d',
    absoluteRange: [],
    keywords: [],
    collectionTasks: [],
    filters: [],
  },
  schedule: {
    frequency: 'daily',
    time: '09:00',
    weekdays: [],
    dayOfMonth: 1,
    cron: '',
    enableConditions: false,
    conditionType: 'dataThreshold',
    threshold: 1000,
    changeThreshold: 10,
  },
  delivery: {
    methods: ['email'],
    emails: [],
    userGroups: [],
    webhookUrl: '',
    emailSubject: '{{reportType}} - {{reportDate}}',
    formats: ['pdf'],
  },
});

const taskFormRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择报告类型', trigger: 'change' }],
  templateId: [{ required: true, message: '请选择报告模板', trigger: 'change' }],
  'schedule.frequency': [{ required: true, message: '请选择执行周期', trigger: 'change' }],
};

const filteredTasks = computed(() => {
  return tasks.value.filter(task => {
    if (searchKeyword.value && !task.name.includes(searchKeyword.value)) return false;
    if (statusFilter.value && task.status !== statusFilter.value) return false;
    if (typeFilter.value && task.type !== typeFilter.value) return false;
    return true;
  });
});

function getTypeText(type: string) {
  const texts: Record<string, string> = {
    daily: '日报',
    weekly: '周报',
    monthly: '月报',
    custom: '自定义',
  };
  return texts[type] || type;
}

function getTypeTagType(type: string) {
  const types: Record<string, any> = {
    daily: 'primary',
    weekly: 'success',
    monthly: 'warning',
    custom: 'info',
  };
  return types[type] || 'info';
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    enabled: '启用',
    paused: '暂停',
    running: '运行中',
  };
  return texts[status] || status;
}

function getStatusTagType(status: string) {
  const types: Record<string, any> = {
    enabled: 'success',
    paused: 'info',
    running: 'warning',
  };
  return types[status] || 'info';
}

function getScheduleText(schedule: any) {
  const { frequency, time, weekdays, dayOfMonth, cron } = schedule;
  
  if (frequency === 'daily') {
    return `每天 ${time}`;
  } else if (frequency === 'weekly') {
    const days = weekdays.map((d: string) => `周${d}`).join(',');
    return `每周 ${days} ${time}`;
  } else if (frequency === 'monthly') {
    return `每月 ${dayOfMonth}日 ${time}`;
  } else if (frequency === 'cron') {
    return `Cron: ${cron}`;
  }
  
  return '-';
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN');
}

function addFilter() {
  taskForm.value.dataSource.filters.push({
    field: '',
    operator: 'equals',
    value: '',
  });
}

function removeFilter(index: number) {
  taskForm.value.dataSource.filters.splice(index, 1);
}

async function handleRunTask(task: any) {
  try {
    await ElMessageBox.confirm('确定要立即执行此任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info',
    });
    
    task.status = 'running';
    ElMessage.success('任务已开始执行');
    
    // 模拟执行
    setTimeout(() => {
      task.status = 'enabled';
      task.lastRun = new Date().toISOString();
      task.lastStatus = 'success';
      ElMessage.success('任务执行完成');
    }, 3000);
  } catch {
    // 取消
  }
}

function handlePauseTask(task: any) {
  task.status = 'paused';
  ElMessage.success('任务已暂停');
}

function handleResumeTask(task: any) {
  task.status = 'enabled';
  ElMessage.success('任务已恢复');
}

function handleTaskAction(command: string, task: any) {
  switch (command) {
    case 'edit':
      editingTask.value = task;
      Object.assign(taskForm.value, task);
      showCreateDialog.value = true;
      break;
    case 'logs':
      selectedTaskId.value = task.id;
      showLogsDialog.value = true;
      break;
    case 'history':
      // 查看执行历史
      break;
    case 'delete':
      handleDeleteTask(task);
      break;
  }
}

async function handleDeleteTask(task: any) {
  try {
    await ElMessageBox.confirm('确定要删除此任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    
    const index = tasks.value.indexOf(task);
    if (index !== -1) {
      tasks.value.splice(index, 1);
    }
    
    ElMessage.success('删除成功');
  } catch {
    // 取消
  }
}

async function handleSaveTask() {
  try {
    await taskFormRef.value.validate();
    
    if (editingTask.value) {
      // 更新任务
      Object.assign(editingTask.value, taskForm.value);
      ElMessage.success('任务已更新');
    } else {
      // 创建新任务
      tasks.value.push({
        id: `task-${Date.now()}`,
        ...taskForm.value,
        status: 'enabled',
        nextRun: new Date(Date.now() + 86400000).toISOString(),
        lastRun: null,
        lastStatus: null,
      });
      ElMessage.success('任务已创建');
    }
    
    showCreateDialog.value = false;
    editingTask.value = null;
  } catch {
    ElMessage.error('请检查表单填写');
  }
}

onMounted(() => {
  // 加载任务列表
});
</script>

<style scoped lang="scss">
.auto-report-scheduler {
  padding: 24px;
}

.scheduler-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  
  h2 {
    margin: 0;
    font-size: 20px;
  }
}

.tasks-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
</style>
