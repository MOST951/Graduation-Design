<template>
  <div class="report-history">
    <div class="history-header">
      <h2>报告历史</h2>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="handleRefresh">刷新</el-button>
        <el-button :icon="Download" @click="handleBatchDownload" :disabled="!selectedReports.length">
          批量下载
        </el-button>
        <el-button :icon="Delete" type="danger" @click="handleBatchDelete" :disabled="!selectedReports.length">
          批量删除
        </el-button>
      </div>
    </div>
    
    <div class="history-filters">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索报告..."
        :prefix-icon="Search"
        clearable
        style="width: 300px"
      />
      
      <el-select v-model="typeFilter" placeholder="报告类型" clearable style="width: 150px">
        <el-option label="全部" value="" />
        <el-option label="日报" value="daily" />
        <el-option label="周报" value="weekly" />
        <el-option label="月报" value="monthly" />
        <el-option label="专项" value="special" />
      </el-select>
      
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width="150px">
        <el-option label="全部" value="" />
        <el-option label="草稿" value="draft" />
        <el-option label="已完成" value="completed" />
        <el-option label="已分享" value="shared" />
      </el-select>
      
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="width: 300px"
      />
    </div>
    
    <el-table
      :data="filteredReports"
      v-loading="isLoading"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      
      <el-table-column prop="name" label="报告名称" width="250">
        <template #default="{ row }">
          <div class="report-name">
            <el-icon><Document /></el-icon>
            <span @click="handleViewReport(row)" class="clickable">{{ row.name }}</span>
            <el-tag v-if="row.hasVersions" size="small" type="info">
              v{{ row.currentVersion }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="getTypeTagType(row.type)">
            {{ getTypeText(row.type) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="generatedAt" label="生成时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.generatedAt) }}
        </template>
      </el-table-column>
      
      <el-table-column prop="generatedBy" label="创建人" width="120" />
      
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="size" label="大小" width="100">
        <template #default="{ row }">
          {{ formatFileSize(row.size) }}
        </template>
      </el-table-column>
      
      <el-table-column prop="views" label="查看次数" width="100" />
      
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :icon="View" @click="handleViewReport(row)">
            预览
          </el-button>
          
          <el-dropdown @command="(cmd) => handleAction(cmd, row)">
            <el-button size="small">
              更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="download" :icon="Download">
                  下载
                </el-dropdown-item>
                <el-dropdown-item command="share" :icon="Share">
                  分享
                </el-dropdown-item>
                <el-dropdown-item command="versions" :icon="Clock">
                  版本历史
                </el-dropdown-item>
                <el-dropdown-item command="edit" :icon="Edit">
                  编辑
                </el-dropdown-item>
                <el-dropdown-item command="duplicate" :icon="CopyDocument">
                  复制
                </el-dropdown-item>
                <el-dropdown-item command="delete" :icon="Delete">
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handlePageChange"
      @current-change="handlePageChange"
    />
    
    <!-- 报告预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="currentReport?.name"
      width="90%"
      fullscreen
    >
      <ReportViewer
        v-if="showPreviewDialog && currentReport"
        :report-id="currentReport.id"
      />
    </el-dialog>
    
    <!-- 版本历史对话框 -->
    <el-dialog
      v-model="showVersionsDialog"
      title="版本历史"
      width="900px"
    >
      <ReportVersions
        v-if="showVersionsDialog && currentReport"
        :report-id="currentReport.id"
        @restore="handleRestoreVersion"
      />
    </el-dialog>
    
    <!-- 分享对话框 -->
    <el-dialog
      v-model="showShareDialog"
      title="分享报告"
      width="600px"
    >
      <ReportShare
        v-if="showShareDialog && currentReport"
        :report-id="currentReport.id"
        @shared="handleShared"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Refresh, Download, Delete, Search, Document, View, Share,
  Clock, Edit, CopyDocument, ArrowDown,
} from '@element-plus/icons-vue';
import ReportViewer from './ReportViewer.vue';
import ReportVersions from './ReportVersions.vue';
import ReportShare from './ReportShare.vue';

// State
const searchKeyword = ref('');
const typeFilter = ref('');
const statusFilter = ref('');
const dateRange = ref([]);
const isLoading = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const selectedReports = ref<any[]>([]);
const showPreviewDialog = ref(false);
const showVersionsDialog = ref(false);
const showShareDialog = ref(false);
const currentReport = ref<any>(null);

const reports = ref([
  {
    id: 'report-1',
    name: '2024年度情感分析报告',
    type: 'monthly',
    generatedAt: '2024-12-01T09:00:00Z',
    generatedBy: '张三',
    status: 'completed',
    size: 2048576,
    views: 156,
    hasVersions: true,
    currentVersion: 3,
    templateId: 'template-1',
  },
  {
    id: 'report-2',
    name: '每日情感分析报告 - 12月10日',
    type: 'daily',
    generatedAt: '2024-12-10T09:00:00Z',
    generatedBy: '系统',
    status: 'completed',
    size: 512000,
    views: 45,
    hasVersions: false,
    currentVersion: 1,
    templateId: 'template-1',
  },
]);

const filteredReports = computed(() => {
  return reports.value.filter(report => {
    if (searchKeyword.value && !report.name.includes(searchKeyword.value)) return false;
    if (typeFilter.value && report.type !== typeFilter.value) return false;
    if (statusFilter.value && report.status !== statusFilter.value) return false;
    
    if (dateRange.value && dateRange.value.length === 2) {
      const reportDate = new Date(report.generatedAt);
      const [start, end] = dateRange.value;
      if (reportDate < start || reportDate > end) return false;
    }
    
    return true;
  });
});

function getTypeText(type: string) {
  const texts: Record<string, string> = {
    daily: '日报',
    weekly: '周报',
    monthly: '月报',
    special: '专项',
  };
  return texts[type] || type;
}

function getTypeTagType(type: string) {
  const types: Record<string, any> = {
    daily: 'primary',
    weekly: 'success',
    monthly: 'warning',
    special: 'info',
  };
  return types[type] || 'info';
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    draft: '草稿',
    completed: '已完成',
    shared: '已分享',
  };
  return texts[status] || status;
}

function getStatusTagType(status: string) {
  const types: Record<string, any> = {
    draft: 'info',
    completed: 'success',
    shared: 'warning',
  };
  return types[status] || 'info';
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN');
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function handleSelectionChange(selection: any[]) {
  selectedReports.value = selection;
}

function handleRefresh() {
  isLoading.value = true;
  setTimeout(() => {
    isLoading.value = false;
    ElMessage.success('刷新成功');
  }, 500);
}

async function handleBatchDownload() {
  ElMessage.info(`正在下载 ${selectedReports.value.length} 个报告...`);
  // 实现批量下载逻辑
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedReports.value.length} 个报告吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    selectedReports.value.forEach(report => {
      const index = reports.value.indexOf(report);
      if (index !== -1) {
        reports.value.splice(index, 1);
      }
    });
    
    selectedReports.value = [];
    ElMessage.success('删除成功');
  } catch {
    // 取消
  }
}

function handleViewReport(report: any) {
  currentReport.value = report;
  showPreviewDialog.value = true;
  
  // 增加查看次数
  report.views++;
}

function handleAction(command: string, report: any) {
  currentReport.value = report;
  
  switch (command) {
    case 'download':
      handleDownload(report);
      break;
    case 'share':
      showShareDialog.value = true;
      break;
    case 'versions':
      showVersionsDialog.value = true;
      break;
    case 'edit':
      handleEdit(report);
      break;
    case 'duplicate':
      handleDuplicate(report);
      break;
    case 'delete':
      handleDelete(report);
      break;
  }
}

function handleDownload(report: any) {
  ElMessage.success(`正在下载: ${report.name}`);
  // 实现下载逻辑
}

function handleEdit(report: any) {
  // 跳转到编辑器
  ElMessage.info('跳转到编辑器');
}

function handleDuplicate(report: any) {
  const newReport = {
    ...report,
    id: `report-${Date.now()}`,
    name: `${report.name} - 副本`,
    generatedAt: new Date().toISOString(),
    views: 0,
    currentVersion: 1,
  };
  
  reports.value.unshift(newReport);
  ElMessage.success('复制成功');
}

async function handleDelete(report: any) {
  try {
    await ElMessageBox.confirm('确定要删除此报告吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    
    const index = reports.value.indexOf(report);
    if (index !== -1) {
      reports.value.splice(index, 1);
    }
    
    ElMessage.success('删除成功');
  } catch {
    // 取消
  }
}

function handleRestoreVersion(versionId: string) {
  ElMessage.success('版本已恢复');
  showVersionsDialog.value = false;
}

function handleShared(shareInfo: any) {
  ElMessage.success('分享链接已生成');
  showShareDialog.value = false;
}

function handlePageChange() {
  // 加载数据
}

onMounted(() => {
  // 加载报告列表
});
</script>

<style scoped lang="scss">
.report-history {
  padding: 24px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  
  h2 {
    margin: 0;
    font-size: 20px;
  }
  
  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.history-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.report-name {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .clickable {
    cursor: pointer;
    color: #409EFF;
    
    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
