<template>
  <div class="admin-module">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>系统管理</h2>
      <p class="subtitle">管理用户权限、任务日志及系统配置</p>
    </div>
    
    <el-tabs v-model="activeTab" class="admin-tabs" @tab-change="handleTabChange">
      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <div class="tab-header">
          <div class="header-left">
            <el-input v-model="userSearch" placeholder="搜索用户名、姓名、邮箱..." :prefix-icon="Search" clearable style="width: 300px" @input="handleUserSearch" />
            <el-select v-model="userStatusFilter" placeholder="状态" clearable style="width: 120px" @change="handleUserFilter">
              <el-option label="全部" value="" />
              <el-option label="正常" value="active" />
              <el-option label="禁用" value="disabled" />
            </el-select>
            <el-select v-model="userRoleFilter" placeholder="角色" clearable style="width: 150px" @change="handleUserFilter">
              <el-option label="管理员" value="admin" />
              <el-option label="普通用户" value="user" />
            </el-select>
          </div>
          <div class="header-right">
            <el-button :icon="Refresh" @click="refreshUsers">刷新</el-button>
            <el-button type="primary" :icon="Plus" @click="handleAddUser">添加用户</el-button>
          </div>
        </div>
        
        <!-- 用户统计卡片 -->
        <el-row :gutter="16" class="stats-row">
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-icon total"><el-icon><User /></el-icon></div>
              <div class="stat-info">
                <div class="stat-value">{{ adminStore.userTotal }}</div>
                <div class="stat-label">总用户数</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-icon active"><el-icon><CircleCheck /></el-icon></div>
              <div class="stat-info">
                <div class="stat-value">{{ adminStore.activeUsers.length }}</div>
                <div class="stat-label">正常用户</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-icon disabled"><el-icon><CircleClose /></el-icon></div>
              <div class="stat-info">
                <div class="stat-value">{{ adminStore.disabledUsers.length }}</div>
                <div class="stat-label">禁用用户</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-icon roles"><el-icon><UserFilled /></el-icon></div>
              <div class="stat-info">
                <div class="stat-value">{{ adminStore.roles.length }}</div>
                <div class="stat-label">角色数量</div>
              </div>
            </div>
          </el-col>
        </el-row>
        
        <!-- 用户表格 -->
        <el-table v-loading="adminStore.isLoadingUsers" :data="filteredUsers" stripe @selection-change="handleUserSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column label="用户" min-width="220">
            <template #default="{ row }">
              <div class="user-cell">
                <el-avatar :size="40" :src="row.avatar">{{ row.name?.[0] || row.username?.[0] }}</el-avatar>
                <div class="user-info"><div class="username">{{ row.username }}</div><div class="name">{{ row.name }}</div></div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="180" />
          <el-table-column label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="getUserRoleType(row)" size="small">
                {{ getUserRoleText(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getUserStatusType(row.status)" size="small">{{ getUserStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最后登录" width="170">
            <template #default="{ row }">
              <span v-if="row.lastLoginAt">{{ formatDateTime(row.lastLoginAt) }}</span>
              <span v-else class="text-muted">从未登录</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" :icon="Edit" @click="handleEditUser(row)">编辑</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => handleUserAction(cmd, row)">
                <el-button size="small">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="row.status === 'active'" command="disable" :icon="Lock">禁用</el-dropdown-item>
                    <el-dropdown-item v-else command="enable" :icon="Unlock">启用</el-dropdown-item>
                    <el-dropdown-item command="reset-password" :icon="Key">重置密码</el-dropdown-item>
                    <el-dropdown-item command="delete" :icon="Delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 批量操作栏 -->
        <transition name="slide-up">
          <div v-if="selectedUsers.length > 0" class="batch-actions">
            <span class="selected-count">已选择 {{ selectedUsers.length }} 项</span>
            <el-button size="small" @click="handleBatchEnable">批量启用</el-button>
            <el-button size="small" @click="handleBatchDisable">批量禁用</el-button>
            <el-button size="small" type="danger" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </transition>
        
        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination v-model:current-page="userPage" v-model:page-size="userPageSize" :total="adminStore.userTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="handleUserPageSizeChange" @current-change="handleUserPageChange" />
        </div>
        
        <!-- 用户编辑对话框 -->
        <el-dialog v-model="showUserDialog" :title="editingUser ? '编辑用户' : '添加用户'" width="600px" destroy-on-close>
          <el-form ref="userFormRef" :model="userForm" :rules="userFormRules" label-width="100px">
            <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="!!editingUser" placeholder="请输入用户名" /></el-form-item>
            <el-form-item v-if="!editingUser" label="密码" prop="password"><el-input v-model="userForm.password" type="password" show-password placeholder="请输入密码" /></el-form-item>
            <el-form-item label="姓名" prop="name"><el-input v-model="userForm.name" placeholder="请输入姓名" /></el-form-item>
            <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" placeholder="请输入邮箱" /></el-form-item>
            <el-form-item label="电话" prop="phone"><el-input v-model="userForm.phone" placeholder="请输入电话" /></el-form-item>
            <el-form-item label="角色" prop="role">
              <el-radio-group v-model="userForm.role">
                <el-radio value="admin">
                  <el-tag type="danger" size="small">管理员</el-tag>
                  <span style="margin-left: 8px; color: #86909C; font-size: 12px">拥有全部权限</span>
                </el-radio>
                <el-radio value="user">
                  <el-tag type="info" size="small">普通用户</el-tag>
                  <span style="margin-left: 8px; color: #86909C; font-size: 12px">仅查看和分析权限</span>
                </el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showUserDialog = false">取消</el-button>
            <el-button type="primary" :loading="isSaving" @click="handleSaveUser">保存</el-button>
          </template>
        </el-dialog>
        
        <!-- 重置密码对话框 -->
        <el-dialog v-model="showResetPasswordDialog" title="重置密码" width="400px">
          <el-form :model="resetPasswordForm" label-width="80px">
            <el-form-item label="新密码"><el-input v-model="resetPasswordForm.password" type="password" show-password placeholder="留空则自动生成" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showResetPasswordDialog = false">取消</el-button>
            <el-button type="primary" @click="handleConfirmResetPassword">确认重置</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
      
      <!-- 任务日志 -->
      <el-tab-pane label="任务日志" name="logs">
        <div class="tab-header">
          <div class="header-left">
            <el-date-picker v-model="logDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="handleLogFilter" />
            <el-select v-model="logTypeFilter" placeholder="任务类型" clearable style="width: 150px" @change="handleLogFilter">
              <el-option label="全部" value="" />
              <el-option label="数据采集" value="collection" />
              <el-option label="数据预处理" value="preprocess" />
              <el-option label="情感分析" value="analysis" />
              <el-option label="Spark任务" value="spark" />
              <el-option label="报告导出" value="export" />
            </el-select>
            <el-select v-model="logStatusFilter" placeholder="任务状态" clearable style="width: 120px" @change="handleLogFilter">
              <el-option label="全部" value="" />
              <el-option label="等待中" value="pending" />
              <el-option label="运行中" value="running" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
            </el-select>
          </div>
          <div class="header-right">
            <el-button :icon="Refresh" @click="refreshLogs">刷新</el-button>
          </div>
        </div>
        
        <!-- 任务统计卡片 -->
        <el-row :gutter="16" class="stats-row">
          <el-col :span="6"><div class="stat-card"><div class="stat-icon total"><el-icon><Document /></el-icon></div><div class="stat-info"><div class="stat-value">{{ adminStore.taskLogTotal }}</div><div class="stat-label">总任务数</div></div></div></el-col>
          <el-col :span="6"><div class="stat-card"><div class="stat-icon running"><el-icon><Loading /></el-icon></div><div class="stat-info"><div class="stat-value">{{ adminStore.runningTasks.length }}</div><div class="stat-label">运行中</div></div></div></el-col>
          <el-col :span="6"><div class="stat-card"><div class="stat-icon active"><el-icon><SuccessFilled /></el-icon></div><div class="stat-info"><div class="stat-value">{{ successTaskCount }}</div><div class="stat-label">成功</div></div></div></el-col>
          <el-col :span="6"><div class="stat-card"><div class="stat-icon disabled"><el-icon><CircleCloseFilled /></el-icon></div><div class="stat-info"><div class="stat-value">{{ adminStore.failedTasks.length }}</div><div class="stat-label">失败</div></div></div></el-col>
        </el-row>
        
        <!-- 任务日志表格 -->
        <el-table v-loading="adminStore.isLoadingLogs" :data="adminStore.taskLogs" stripe style="cursor: pointer" @row-click="handleViewTaskLog">
          <el-table-column prop="taskName" label="任务名称" min-width="200">
            <template #default="{ row }">
              <div class="task-name-cell">
                <el-icon :class="getTaskTypeClass(row.taskType)"><component :is="getTaskTypeIcon(row.taskType)" /></el-icon>
                <span>{{ row.taskName }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="任务类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="getTaskTypeTagType(row.taskType)">{{ getTaskTypeText(row.taskType) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getTaskStatusType(row.status)" size="small">
                <el-icon v-if="row.status === 'running'" class="is-loading"><Loading /></el-icon>
                {{ getTaskStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="150">
            <template #default="{ row }">
              <el-progress v-if="row.status === 'running' || row.status === 'success'" :percentage="row.progress || 0" :status="row.status === 'success' ? 'success' : undefined" :stroke-width="6" />
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="startTime" label="开始时间" width="170" />
          <el-table-column prop="duration" label="耗时" width="100"><template #default="{ row }">{{ row.duration || '-' }}</template></el-table-column>
          <el-table-column prop="executor" label="执行者" width="100" />
          <el-table-column label="资源消耗" width="150">
            <template #default="{ row }">
              <div v-if="row.resourceUsage" class="resource-usage"><span>CPU: {{ row.resourceUsage.cpu }}%</span></div>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button size="small" :icon="View" @click.stop="handleViewTaskLog(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination v-model:current-page="logPage" v-model:page-size="logPageSize" :total="adminStore.taskLogTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" />
        </div>
        
        <!-- 任务日志详情对话框 -->
        <el-dialog v-model="showLogDialog" title="任务日志详情" width="900px" destroy-on-close>
          <div v-if="currentTaskLog" class="task-log-detail">
            <div class="detail-section">
              <h4>基本信息</h4>
              <el-descriptions :column="3" border>
                <el-descriptions-item label="任务名称">{{ currentTaskLog.taskName }}</el-descriptions-item>
                <el-descriptions-item label="任务类型"><el-tag size="small" :type="getTaskTypeTagType(currentTaskLog.taskType)">{{ getTaskTypeText(currentTaskLog.taskType) }}</el-tag></el-descriptions-item>
                <el-descriptions-item label="状态"><el-tag :type="getTaskStatusType(currentTaskLog.status)" size="small">{{ getTaskStatusText(currentTaskLog.status) }}</el-tag></el-descriptions-item>
                <el-descriptions-item label="开始时间">{{ currentTaskLog.startTime }}</el-descriptions-item>
                <el-descriptions-item label="结束时间">{{ currentTaskLog.endTime || '-' }}</el-descriptions-item>
                <el-descriptions-item label="耗时">{{ currentTaskLog.duration || '-' }}</el-descriptions-item>
                <el-descriptions-item label="执行者">{{ currentTaskLog.executor || '-' }}</el-descriptions-item>
                <el-descriptions-item label="进度" :span="2"><el-progress :percentage="currentTaskLog.progress || 0" :status="currentTaskLog.status === 'success' ? 'success' : currentTaskLog.status === 'failed' ? 'exception' : undefined" /></el-descriptions-item>
              </el-descriptions>
            </div>
            <div v-if="currentTaskLog.resourceUsage" class="detail-section">
              <h4>资源消耗</h4>
              <el-row :gutter="20">
                <el-col :span="8"><div class="resource-card"><div class="resource-label">CPU使用率</div><el-progress type="dashboard" :percentage="currentTaskLog.resourceUsage.cpu" :width="100" /></div></el-col>
                <el-col :span="8"><div class="resource-card"><div class="resource-label">内存使用</div><div class="resource-value">{{ formatBytes(currentTaskLog.resourceUsage.memory * 1024 * 1024) }}</div></div></el-col>
                <el-col :span="8"><div class="resource-card"><div class="resource-label">磁盘IO</div><div class="resource-value">{{ formatBytes(currentTaskLog.resourceUsage.disk * 1024 * 1024) }}</div></div></el-col>
              </el-row>
            </div>
            <div v-if="currentTaskLog.steps && currentTaskLog.steps.length > 0" class="detail-section">
              <h4>执行步骤</h4>
              <el-timeline>
                <el-timeline-item v-for="step in currentTaskLog.steps" :key="step.id" :type="getStepTimelineType(step.status)" :hollow="step.status === 'pending'" :timestamp="step.startTime" placement="top">
                  <div class="step-content">
                    <div class="step-header"><span class="step-name">{{ step.name }}</span><el-tag :type="getTaskStatusType(step.status)" size="small">{{ getTaskStatusText(step.status) }}</el-tag></div>
                    <div v-if="step.message" class="step-message">{{ step.message }}</div>
                    <div v-if="step.details" class="step-details"><pre>{{ step.details }}</pre></div>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
            <div v-if="currentTaskLog.errorMessage" class="detail-section error-section">
              <h4>错误信息</h4>
              <el-alert type="error" :closable="false" show-icon>{{ currentTaskLog.errorMessage }}</el-alert>
            </div>
          </div>
        </el-dialog>
      </el-tab-pane>
      
      <!-- 系统设置 -->
      <el-tab-pane label="系统设置" name="settings">
        <el-row :gutter="24">
          <el-col :span="16">
            <!-- Spark配置卡片 -->
            <el-card class="settings-card">
              <template #header><div class="card-header"><span>Spark伪集群配置</span><el-tag size="small" type="info">核心配置</el-tag></div></template>
              <el-form :model="sparkConfigForm" label-width="160px">
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="Master地址"><el-input v-model="sparkConfigForm.master" placeholder="local[*]" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="应用名称"><el-input v-model="sparkConfigForm.appName" placeholder="WeiboSentimentAnalysis" /></el-form-item></el-col>
                </el-row>
                <el-divider content-position="left">Executor配置</el-divider>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="Executor内存"><el-input v-model="sparkConfigForm.executorMemory" placeholder="4g"><template #append>GB</template></el-input></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="Executor核心数"><el-input-number v-model="sparkConfigForm.executorCores" :min="1" :max="32" /></el-form-item></el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="Driver内存"><el-input v-model="sparkConfigForm.driverMemory" placeholder="2g"><template #append>GB</template></el-input></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="Driver核心数"><el-input-number v-model="sparkConfigForm.driverCores" :min="1" :max="16" /></el-form-item></el-col>
                </el-row>
                <el-divider content-position="left">并行度配置</el-divider>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="默认分区数"><el-input-number v-model="sparkConfigForm.partitions" :min="1" :max="10000" :step="10" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="Shuffle分区数"><el-input-number v-model="sparkConfigForm.shufflePartitions" :min="1" :max="10000" :step="10" /></el-form-item></el-col>
                </el-row>
                <el-divider content-position="left">动态资源分配</el-divider>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="启用动态分配"><el-switch v-model="sparkConfigForm.dynamicAllocation" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="最大重试次数"><el-input-number v-model="sparkConfigForm.maxRetries" :min="0" :max="10" /></el-form-item></el-col>
                </el-row>
                <el-row v-if="sparkConfigForm.dynamicAllocation" :gutter="20">
                  <el-col :span="12"><el-form-item label="最小Executor数"><el-input-number v-model="sparkConfigForm.minExecutors" :min="1" :max="100" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="最大Executor数"><el-input-number v-model="sparkConfigForm.maxExecutors" :min="1" :max="1000" /></el-form-item></el-col>
                </el-row>
                <el-form-item>
                  <el-button type="primary" :loading="isSavingConfig" @click="handleSaveSparkConfig">保存Spark配置</el-button>
                  <el-button @click="handleResetSparkConfig">重置为默认</el-button>
                  <el-button v-if="sparkRestartRequired" type="warning" @click="showSparkRestartDialog = true">
                    <el-icon><Warning /></el-icon> 
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
            
            <!-- 邮件配置卡片 -->
            <el-card class="settings-card" style="margin-top: 20px">
              <template #header><div class="card-header"><span>邮件服务器配置</span></div></template>
              <el-form :model="emailConfigForm" label-width="120px">
                <el-row :gutter="20">
                  <el-col :span="16"><el-form-item label="SMTP服务器"><el-input v-model="emailConfigForm.host" placeholder="smtp.example.com" /></el-form-item></el-col>
                  <el-col :span="8"><el-form-item label="端口"><el-input-number v-model="emailConfigForm.port" :min="1" :max="65535" style="width: 100%" /></el-form-item></el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="用户名"><el-input v-model="emailConfigForm.username" placeholder="noreply@example.com" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="密码"><el-input v-model="emailConfigForm.password" :type="showEmailPassword ? 'text' : 'password'" show-password placeholder="请输入密码" :readonly="emailConfigForm.password === '******'" /></el-form-item></el-col>
                </el-row>
                <el-form-item label="启用SSL"><el-switch v-model="emailConfigForm.ssl" /></el-form-item>
                <el-form-item><el-button type="primary" :loading="isSavingConfig" @click="handleSaveEmailConfig">保存邮件配置</el-button><el-button @click="handleTestEmail">发送测试邮件</el-button></el-form-item>
              </el-form>
            </el-card>
            
            <!-- 系统参数卡片 -->
            <el-card class="settings-card" style="margin-top: 20px">
              <template #header><div class="card-header"><span>系统参数配置</span></div></template>
              <el-form :model="systemParamsForm" label-width="140px">
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="会话超时时间"><el-input-number v-model="systemParamsForm.sessionTimeout" :min="5" :max="1440" /><span class="form-hint">分钟</span></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="数据保留天数"><el-input-number v-model="systemParamsForm.dataRetention" :min="1" :max="365" /><span class="form-hint">天</span></el-form-item></el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="启用调试模式"><el-switch v-model="systemParamsForm.debugMode" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="启用操作审计"><el-switch v-model="systemParamsForm.auditEnabled" /></el-form-item></el-col>
                </el-row>
                <el-form-item><el-button type="primary" :loading="isSavingConfig" @click="handleSaveSystemParams">保存系统参数</el-button></el-form-item>
              </el-form>
            </el-card>
          </el-col>
          
          <!-- 右侧系统状态 -->
          <el-col :span="8">
            <el-card class="status-card">
              <template #header><div class="card-header"><span>系统状态</span><el-button size="small" :icon="Refresh" circle @click="refreshSystemMetrics" /></div></template>
              <div v-if="adminStore.systemMetrics" class="system-metrics">
                <div class="metric-item"><div class="metric-label">CPU使用率</div><el-progress :percentage="Math.round(adminStore.systemMetrics.cpu.usage)" :status="adminStore.systemMetrics.cpu.usage > 80 ? 'exception' : adminStore.systemMetrics.cpu.usage > 60 ? 'warning' : 'success'" /></div>
                <div class="metric-item"><div class="metric-label">内存使用</div><el-progress :percentage="Math.round(adminStore.systemMetrics.memory.usage)" :status="adminStore.systemMetrics.memory.usage > 80 ? 'exception' : adminStore.systemMetrics.memory.usage > 60 ? 'warning' : 'success'" /><div class="metric-detail">{{ formatBytes(adminStore.systemMetrics.memory.used * 1024 * 1024) }} / {{ formatBytes(adminStore.systemMetrics.memory.total * 1024 * 1024) }}</div></div>
                <div class="metric-item"><div class="metric-label">磁盘使用</div><el-progress :percentage="Math.round(adminStore.systemMetrics.disk.usage)" :status="adminStore.systemMetrics.disk.usage > 80 ? 'exception' : adminStore.systemMetrics.disk.usage > 60 ? 'warning' : 'success'" /><div class="metric-detail">{{ formatBytes(adminStore.systemMetrics.disk.used * 1024 * 1024) }} / {{ formatBytes(adminStore.systemMetrics.disk.total * 1024 * 1024) }}</div></div>
                <el-divider />
                <div class="metric-item"><div class="metric-label">在线用户</div><div class="metric-value">{{ adminStore.systemMetrics.application.onlineUsers }}</div></div>
                <div class="metric-item"><div class="metric-label">请求/分钟</div><div class="metric-value">{{ adminStore.systemMetrics.application.requestsPerMinute }}</div></div>
                <div class="metric-item"><div class="metric-label">平均响应时间</div><div class="metric-value">{{ adminStore.systemMetrics.application.avgResponseTime.toFixed(2) }} ms</div></div>
                <div class="metric-item"><div class="metric-label">错误率</div><div class="metric-value" :class="{ 'text-danger': adminStore.systemMetrics.application.errorRate > 1 }">{{ adminStore.systemMetrics.application.errorRate.toFixed(2) }}%</div></div>
              </div>
              <el-skeleton v-else :rows="8" animated />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
      
      <!-- 系统运行日志 -->
      <el-tab-pane label="系统日志" name="syslog">
        <div class="tab-header">
          <div class="header-left">
            <el-select v-model="sysLogLevel" placeholder="日志级别" style="width: 140px" @change="fetchSystemLogs">
              <el-option label="全部" value="ALL" />
              <el-option label="ERROR" value="ERROR" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="INFO" value="INFO" />
              <el-option label="DEBUG" value="DEBUG" />
            </el-select>
            <el-input-number v-model="sysLogLimit" :min="20" :max="500" :step="20" @change="fetchSystemLogs" />
          </div>
          <div class="header-right">
            <el-button :icon="Refresh" :loading="loadingSysLogs" @click="fetchSystemLogs">刷新</el-button>
          </div>
        </div>

        <el-card shadow="hover" style="margin-top: 12px">
          <div v-loading="loadingSysLogs" class="sys-log-list">
            <div v-if="systemLogs.length === 0" class="no-logs">暂无日志记录</div>
            <div v-for="(log, idx) in systemLogs" :key="idx" class="sys-log-item" :class="'log-' + log.level.toLowerCase()">
              <el-tag :type="getLogLevelType(log.level)" size="small" class="log-level-tag">{{ log.level }}</el-tag>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 权限管理 -->
      <el-tab-pane label="权限说明" name="permissions">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card class="role-card">
              <template #header>
                <div class="card-header">
                  <el-tag type="danger" size="large">管理员</el-tag>
                  <span style="margin-left: 12px; font-weight: 500">Admin</span>
                </div>
              </template>
              <div class="role-description">
                <p class="role-intro">系统管理员拥有全部功能权限，负责系统的整体管理和维护。</p>
                <el-divider content-position="left">权限列表</el-divider>
                <div class="permission-list">
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>数据采集管理</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>数据预处理</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>情感分析</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>热点话题分析</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>报告生成与导出</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>用户管理</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>系统配置</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>任务日志查看</span></div>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <el-col :span="12">
            <el-card class="role-card">
              <template #header>
                <div class="card-header">
                  <el-tag type="info" size="large">普通用户</el-tag>
                  <span style="margin-left: 12px; font-weight: 500">User</span>
                </div>
              </template>
              <div class="role-description">
                <p class="role-intro">普通用户可以查看数据和分析结果，但无法进行系统管理操作。</p>
                <el-divider content-position="left">权限列表</el-divider>
                <div class="permission-list">
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>查看数据采集结果</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>查看预处理数据</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>查看情感分析结果</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>查看热点话题</span></div>
                  <div class="permission-item"><el-icon :color="SUCCESS"><CircleCheck /></el-icon><span>查看报告</span></div>
                  <div class="permission-item"><el-icon :color="INFO"><CircleClose /></el-icon><span class="disabled">用户管理</span></div>
                  <div class="permission-item"><el-icon :color="INFO"><CircleClose /></el-icon><span class="disabled">系统配置</span></div>
                  <div class="permission-item"><el-icon :color="INFO"><CircleClose /></el-icon><span class="disabled">任务日志查看</span></div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
        
        <el-card style="margin-top: 20px">
          <template #header><div class="card-header"><span>角色说明</span></div></template>
          <el-alert type="info" :closable="false" show-icon>
            <template #title>
              本系统采用简化的双角色权限模型，适用于本科毕业设计项目。管理员负责系统管理，普通用户负责数据查看和分析。
            </template>
          </el-alert>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- Spark restart confirmation dialog -->
    <el-dialog v-model="showSparkRestartDialog" title="Spark cluster restart" width="500px">
      <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 20px">
        <template #title>
          Spark configuration has been changed. Restarting the Spark cluster is required for changes to take effect.
        </template>
      </el-alert>
      
      <div class="restart-warning">
        <h4>Warning: This operation will:</h4>
        <ul>
          <li>Stop all running Spark jobs</li>
          <li>Terminate the Spark master and workers</li>
          <li>Restart the cluster with new configuration</li>
          <li>Take approximately 2-3 minutes to complete</li>
        </ul>
        <p style="color: #f56c6c; margin-top: 10px;">
          <strong>Do not perform this operation during active data processing!</strong>
        </p>
      </div>
      
      <template #footer>
        <el-button @click="showSparkRestartDialog = false">Cancel</el-button>
        <el-button type="danger" :loading="isRestartingSpark" @click="handleRestartSparkCluster">
          <el-icon><Warning /></el-icon>
          Restart Spark Cluster
        </el-button>
      </template>
    </el-dialog>

    <!-- Real-time log controls -->
    <div v-if="activeTab === 'syslog'" class="real-time-controls">
      <el-switch
        v-model="isRealTimeLogsEnabled" active-text="Real-time logs" 
        inactive-text="Static logs" @change="toggleRealTimeLogs"
      />
      <el-button v-if="isRealTimeLogsEnabled" size="small" @click="clearRealTimeLogs">
        <el-icon><Delete /></el-icon> Clear
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import {
  Search, Plus, Edit, Delete, View, Refresh, Lock, Unlock, Key, ArrowDown,
  User, UserFilled, CircleCheck, CircleClose, Document, Loading, SuccessFilled, CircleCloseFilled,
  Download, DataAnalysis, Operation, Connection, Warning,
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus';
import { useAdminStore, type TaskLog } from '@/store/admin';
import { SUCCESS, INFO } from '@/styles/colors';
import { useReconnectingEventSource } from '@/composables/useReconnect';

const adminStore = useAdminStore();

// ==================== 基础状态 ====================
const activeTab = ref('users');
const isSaving = ref(false);
const isSavingConfig = ref(false);

// ==================== 用户管理状态 ====================
const userSearch = ref('');
const userStatusFilter = ref('');
const userRoleFilter = ref('');
const userPage = ref(1);
const userPageSize = ref(10);
const selectedUsers = ref<any[]>([]);
const showUserDialog = ref(false);
const showResetPasswordDialog = ref(false);
const editingUser = ref<any>(null);
const resetPasswordUserId = ref('');
const userFormRef = ref<FormInstance>();

const userForm = ref({
  username: '',
  password: '',
  name: '',
  email: '',
  phone: '',
  role: 'user' as 'admin' | 'user',
});

const userFormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }],
};

const resetPasswordForm = ref({ password: '' });

// ==================== 任务日志状态 ====================
const logDateRange = ref<string[]>([]);
const logTypeFilter = ref('');
const logStatusFilter = ref('');
const logPage = ref(1);
const logPageSize = ref(10);
const showLogDialog = ref(false);
const currentTaskLog = ref<TaskLog | null>(null);

const successTaskCount = computed(() => adminStore.taskLogs.filter(t => t.status === 'success').length);

// ==================== 系统设置状态 ====================
const sparkConfigForm = ref({
  master: 'local[*]',
  appName: 'WeiboSentimentAnalysis',
  executorMemory: '4',
  executorCores: 2,
  driverMemory: '2',
  driverCores: 1,
  partitions: 200,
  shufflePartitions: 200,
  maxRetries: 3,
  dynamicAllocation: false,
  minExecutors: 1,
  maxExecutors: 10,
});

const emailConfigForm = ref({
  host: 'smtp.example.com',
  port: 465,
  username: 'noreply@example.com',
  password: '',
  ssl: true,
});

const systemParamsForm = ref({
  sessionTimeout: 30,
  dataRetention: 90,
  debugMode: false,
  auditEnabled: true,
});

// ==================== 系统日志状态 ====================
const sysLogLevel = ref('ALL');
const sysLogLimit = ref(100);
const loadingSysLogs = ref(false);
const systemLogs = ref<{ message: string; level: string }[]>([]);

// ==================== 权限管理状态 ====================
const selectedUserId = ref('');
const selectedRoleIds = ref<string[]>([]);
const showRoleDialog = ref(false);
const editingRole = ref<any>(null);
const roleForm = ref({ name: '', code: '', description: '' });

// ==================== Spark重启、密码显示、WebSocket日志状态 ====================
const sparkRestartRequired = ref(false);
const showSparkRestartDialog = ref(false);
const showEmailPassword = ref(false);
const isRestartingSpark = ref(false);
const realTimeLogs = ref<{ message: string; level: string; timestamp: string }[]>([]);
const isRealTimeLogsEnabled = ref(false);

// ==================== 计算属性 ====================
const filteredUsers = computed(() => {
  let result = adminStore.users;
  if (userSearch.value) {
    const keyword = userSearch.value.toLowerCase();
    result = result.filter(u => 
      u.username.toLowerCase().includes(keyword) ||
      u.name.toLowerCase().includes(keyword) ||
      u.email.toLowerCase().includes(keyword)
    );
  }
  if (userStatusFilter.value) {
    result = result.filter(u => u.status === userStatusFilter.value);
  }
  if (userRoleFilter.value) {
    result = result.filter(u => u.roles.some(r => r.id === userRoleFilter.value));
  }
  return result;
});

// ==================== 工具函数 ====================
const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
};

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getUserStatusType = (status: string) => {
  const types: Record<string, any> = { active: 'success', disabled: 'danger', inactive: 'warning' };
  return types[status] || 'info';
};

const getUserStatusText = (status: string) => {
  const texts: Record<string, string> = { active: '正常', disabled: '禁用', inactive: '未激活' };
  return texts[status] || status;
};

const getRoleTagType = (code: string) => {
  const types: Record<string, any> = { admin: 'danger', analyst: 'warning', user: 'info' };
  return types[code] || '';
};

// 判断用户是否为管理员
const isUserAdmin = (user: any): boolean => {
  // 优先检查 role 字段（简化后的角色系统）
  if (user.role) {
    return user.role === 'admin';
  }
  // 兼容 roles 数组（原有角色系统）
  if (user.roles && Array.isArray(user.roles)) {
    return user.roles.some((r: any) => r.code === 'admin' || r.name === '系统管理员');
  }
  return false;
};

const getUserRoleType = (user: any) => {
  return isUserAdmin(user) ? 'danger' : 'info';
};

const getUserRoleText = (user: any) => {
  return isUserAdmin(user) ? '管理员' : '普通用户';
};

const getTaskStatusType = (status: string) => {
  const types: Record<string, any> = { success: 'success', failed: 'danger', running: 'warning', pending: 'info', cancelled: 'info' };
  return types[status] || 'info';
};

const getTaskStatusText = (status: string) => {
  const texts: Record<string, string> = { success: '成功', failed: '失败', running: '运行中', pending: '等待中', cancelled: '已取消' };
  return texts[status] || status;
};

const getTaskTypeText = (type: string) => {
  const texts: Record<string, string> = { collection: '数据采集', preprocess: '数据预处理', analysis: '情感分析', spark: 'Spark任务', export: '报告导出' };
  return texts[type] || type;
};

const getTaskTypeTagType = (type: string) => {
  const types: Record<string, any> = { collection: '', preprocess: 'warning', analysis: 'success', spark: 'danger', export: 'info' };
  return types[type] || '';
};

const getTaskTypeIcon = (type: string) => {
  const icons: Record<string, any> = { collection: Download, preprocess: Operation, analysis: DataAnalysis, spark: Connection, export: Document };
  return icons[type] || Document;
};

const getTaskTypeClass = (type: string) => `task-icon-${type}`;

const getStepTimelineType = (status: string) => {
  const types: Record<string, any> = { success: 'success', failed: 'danger', running: 'warning', pending: 'info' };
  return types[status] || 'info';
};

const getLogLevelType = (level: string) => {
  const map: Record<string, any> = { ERROR: 'danger', WARNING: 'warning', INFO: 'success', DEBUG: 'info' };
  return map[level] || 'info';
};

// ==================== 系统日志操作 ====================
const fetchSystemLogs = async () => {
  loadingSysLogs.value = true;
  try {
    const { default: apiClient } = await import('@/api/index');
    const res = await apiClient.get('/admin/logs', {
      params: { level: sysLogLevel.value, limit: sysLogLimit.value }
    });
    if (res.data.code === 200) {
      systemLogs.value = res.data.data.logs || [];
    }
  } catch (e) {
    systemLogs.value = [
      { message: `${new Date().toISOString()} - 系统运行正常`, level: 'INFO' },
      { message: `${new Date().toISOString()} - Flask服务运行在端口5000`, level: 'INFO' },
    ];
  } finally {
    loadingSysLogs.value = false;
  }
};

// ==================== Tab切换 ====================
const handleTabChange = (tab: string) => {
  if (tab === 'logs') {
    adminStore.fetchTaskLogs();
  } else if (tab === 'settings') {
    adminStore.fetchSystemMetrics();
  } else if (tab === 'permissions') {
    adminStore.fetchPermissions();
  } else if (tab === 'syslog') {
    fetchSystemLogs();
  }
};

// ==================== 用户管理操作 ====================
const refreshUsers = () => adminStore.fetchUsers();

const handleUserSearch = () => { /* 前端过滤，无需额外操作 */ };
const handleUserFilter = () => { /* 前端过滤，无需额外操作 */ };

const handleUserSelectionChange = (selection: any[]) => { selectedUsers.value = selection; };

const handleUserPageChange = (page: number) => { userPage.value = page; };
const handleUserPageSizeChange = (size: number) => { userPageSize.value = size; };

const handleAddUser = () => {
  editingUser.value = null;
  userForm.value = { username: '', password: '', name: '', email: '', phone: '', role: 'user' };
  showUserDialog.value = true;
};

const handleEditUser = (user: any) => {
  editingUser.value = user;
  userForm.value = {
    username: user.username,
    password: '',
    name: user.name,
    email: user.email,
    phone: user.phone || '',
    role: user.role || 'user',
  };
  showUserDialog.value = true;
};

const handleSaveUser = async () => {
  try {
    isSaving.value = true;
    if (editingUser.value) {
      await adminStore.modifyUser(editingUser.value.id, userForm.value);
      ElMessage.success('用户更新成功');
    } else {
      await adminStore.addUser(userForm.value as any);
      ElMessage.success('用户创建成功');
    }
    showUserDialog.value = false;
  } catch (e) {
    ElMessage.error('操作失败');
  } finally {
    isSaving.value = false;
  }
};

const handleUserAction = async (command: string, user: any) => {
  switch (command) {
    case 'enable':
      await adminStore.changeUserStatus(user.id, 'active');
      ElMessage.success('用户已启用');
      break;
    case 'disable':
      await adminStore.changeUserStatus(user.id, 'disabled');
      ElMessage.success('用户已禁用');
      break;
    case 'reset-password':
      resetPasswordUserId.value = user.id;
      resetPasswordForm.value.password = '';
      showResetPasswordDialog.value = true;
      break;
    case 'delete':
      await ElMessageBox.confirm('确定要删除此用户吗？此操作不可恢复。', '删除确认', { type: 'warning' });
      await adminStore.removeUser(user.id);
      ElMessage.success('用户已删除');
      break;
  }
};

const handleConfirmResetPassword = async () => {
  const result = await adminStore.resetUserPassword(resetPasswordUserId.value, resetPasswordForm.value.password || undefined);
  ElMessage.success(`密码已重置为: ${result.password}`);
  showResetPasswordDialog.value = false;
};

const handleBatchEnable = async () => {
  const ids = selectedUsers.value.map(u => u.id);
  await adminStore.batchChangeUserStatus(ids, 'active');
  selectedUsers.value = [];
  ElMessage.success('批量启用成功');
};

const handleBatchDisable = async () => {
  const ids = selectedUsers.value.map(u => u.id);
  await adminStore.batchChangeUserStatus(ids, 'disabled');
  selectedUsers.value = [];
  ElMessage.success('批量禁用成功');
};

const handleBatchDelete = async () => {
  await ElMessageBox.confirm(`确定要删除选中的 ${selectedUsers.value.length} 个用户吗？`, '批量删除', { type: 'warning' });
  const ids = selectedUsers.value.map(u => u.id);
  await adminStore.batchRemoveUsers(ids);
  selectedUsers.value = [];
  ElMessage.success('批量删除成功');
};

// ==================== 任务日志操作 ====================
const refreshLogs = () => adminStore.fetchTaskLogs({ taskType: logTypeFilter.value, status: logStatusFilter.value });

const handleLogFilter = () => {
  adminStore.fetchTaskLogs({ taskType: logTypeFilter.value, status: logStatusFilter.value });
};

const handleViewTaskLog = (row: TaskLog) => {
  currentTaskLog.value = row;
  showLogDialog.value = true;
};
const refreshSystemMetrics = () => adminStore.fetchSystemMetrics();

const handleSaveSparkConfig = async () => {
  try {
    isSavingConfig.value = true;
    
    // Call API to save Spark config
    const { default: apiClient } = await import('@/api/index');
    const res = await apiClient.put('/admin/config/spark', sparkConfigForm.value);
    
    if (res.data.code === 200) {
      ElMessage.success('Spark configuration saved successfully');
      
      // Show restart warning if required
      if (res.data.data?.requires_restart) {
        sparkRestartRequired.value = true;
        ElMessage.warning('Spark cluster restart required for changes to take effect');
      }
    }
  } catch (error) {
    ElMessage.error('Failed to save Spark configuration');
    console.error('Spark config save error:', error);
  } finally {
    isSavingConfig.value = false;
  }
};

const handleRestartSparkCluster = async () => {
  try {
    isRestartingSpark.value = true;
    
    // Call API to restart Spark cluster
    const { default: apiClient } = await import('@/api/index');
    const res = await apiClient.post('/admin/spark/restart', { confirm: true });
    
    if (res.data.code === 200) {
      ElMessage.success('Spark cluster restart initiated');
      showSparkRestartDialog.value = false;
      sparkRestartRequired.value = false;
      
      // Poll for restart completion
      const checkRestartStatus = async () => {
        try {
          const statusRes = await apiClient.get('/admin/system/metrics');
          if (statusRes.data.code === 200) {
            ElMessage.success('Spark cluster restarted successfully');
          }
        } catch (error) {
          // Restart still in progress
          setTimeout(checkRestartStatus, 10000); // Check every 10 seconds
        }
      };
      
      setTimeout(checkRestartStatus, 30000); // Start checking after 30 seconds
    }
  } catch (error) {
    ElMessage.error('Failed to restart Spark cluster');
    console.error('Spark restart error:', error);
  } finally {
    isRestartingSpark.value = false;
  }
};

const handleResetSparkConfig = () => {
  sparkConfigForm.value = {
    master: 'local[*]',
    appName: 'WeiboSentimentAnalysis',
    executorMemory: '4',
    executorCores: 2,
    driverMemory: '2',
    driverCores: 1,
    partitions: 200,
    shufflePartitions: 200,
    maxRetries: 3,
    dynamicAllocation: false,
    minExecutors: 1,
    maxExecutors: 10,
  };
  ElMessage.info('Reset to default configuration');
};

const handleSaveEmailConfig = async () => {
  try {
    isSavingConfig.value = true;
    
    // Mask password if it's the masked value
    const configData = { ...emailConfigForm.value };
    if (configData.password === '******') {
      delete configData.password; // Don't send masked password
    }
    
    const { default: apiClient } = await import('@/api/index');
    const res = await apiClient.put('/admin/config/email', configData);
    
    if (res.data.code === 200) {
      ElMessage.success('Email configuration saved successfully');
    }
  } catch (error) {
    ElMessage.error('Failed to save email configuration');
    console.error('Email config save error:', error);
  } finally {
    isSavingConfig.value = false;
  }
};

const handleTestEmail = async () => {
  try {
    const { default: apiClient } = await import('@/api/index');
    const res = await apiClient.post('/admin/config/email/test', {
      to: 'test@example.com',
      subject: 'Test Email from Weibo Sentiment System',
      message: 'This is a test email to verify email configuration.'
    });
    
    if (res.data.code === 200) {
      ElMessage.success('Test email sent successfully');
    }
  } catch (error) {
    ElMessage.error('Failed to send test email');
    console.error('Test email error:', error);
  }
};

const handleSaveSystemParams = async () => {
  try {
    isSavingConfig.value = true;
    
    const { default: apiClient } = await import('@/api/index');
    const res = await apiClient.put('/admin/config/system', systemParamsForm.value);
    
    if (res.data.code === 200) {
      ElMessage.success('System parameters saved successfully');
    }
  } catch (error) {
    ElMessage.error('Failed to save system parameters');
    console.error('System params save error:', error);
  } finally {
    isSavingConfig.value = false;
  }
};

// ==================== SSE real-time logs (auto-reconnect) ====================
let sseControl: ReturnType<typeof useReconnectingEventSource> | null = null;

const toggleRealTimeLogs = (enabled: boolean) => {
  if (enabled) {
    startRealTimeLogs();
  } else {
    stopRealTimeLogs();
  }
};

const startRealTimeLogs = () => {
  // 使用 composable 创建带自动重连的 SSE 连接
  sseControl = useReconnectingEventSource('/api/admin/logs/stream', {
    immediate: true,
    maxAttempts: 5,
    initialDelay: 2000,
    onParsedMessage: (logData) => {
      const log = logData as { message: string; level: string; timestamp: string };
      realTimeLogs.value.unshift(log);
      if (realTimeLogs.value.length > 100) {
        realTimeLogs.value = realTimeLogs.value.slice(0, 100);
      }
    },
    onStatusChange: (status) => {
      if (status === 'connected') {
        ElMessage.success('实时日志已连接');
      } else if (status === 'reconnecting') {
        ElMessage.warning('实时日志连接断开，正在重连…');
      }
    },
    onError: () => {
      console.error('[SSE] 实时日志连接错误');
    },
  });
};

const stopRealTimeLogs = () => {
  if (sseControl) {
    sseControl.disconnect();
    sseControl = null;
  }
  ElMessage.info('实时日志已关闭');
};

const clearRealTimeLogs = () => {
  realTimeLogs.value = [];
  ElMessage.info('Real-time logs cleared');
};

// ==================== Configuration loading ====================
const loadConfigurations = async () => {
  try {
    const { default: apiClient } = await import('@/api/index');
    
    // Load Spark config
    const sparkRes = await apiClient.get('/admin/config/spark');
    if (sparkRes.data.code === 200) {
      Object.assign(sparkConfigForm.value, sparkRes.data.data);
    }
    
    // Load email config (password will be masked)
    const emailRes = await apiClient.get('/admin/config/email');
    if (emailRes.data.code === 200) {
      Object.assign(emailConfigForm.value, emailRes.data.data);
    }
    
    // Load system params
    const systemRes = await apiClient.get('/admin/config/system');
    if (systemRes.data.code === 200) {
      Object.assign(systemParamsForm.value, systemRes.data.data);
    }
  } catch (error) {
    console.error('Error loading configurations:', error);
  }
};
// ==================== 权限管理操作 ====================
const handleAddRole = () => {
  editingRole.value = null;
  roleForm.value = { name: '', code: '', description: '' };
  showRoleDialog.value = true;
};

const handleEditRole = (role: any) => {
  editingRole.value = role;
  roleForm.value = { name: role.name, code: role.code, description: role.description };
  showRoleDialog.value = true;
};

const handleDeleteRole = async (role: any) => {
  await ElMessageBox.confirm(`确定要删除角色"${role.name}"吗？`, '删除确认', { type: 'warning' });
  await adminStore.removeRole(role.id);
  ElMessage.success('角色已删除');
};

const handleSaveRole = async () => {
  if (editingRole.value) {
    await adminStore.modifyRole(editingRole.value.id, roleForm.value);
    ElMessage.success('角色更新成功');
  } else {
    await adminStore.addRole({ ...roleForm.value, permissions: [] });
    ElMessage.success('角色创建成功');
  }
  showRoleDialog.value = false;
};

const handleAssignRoles = async () => {
  if (!selectedUserId.value) return;
  await adminStore.assignRoles(selectedUserId.value, selectedRoleIds.value);
  ElMessage.success('角色分配成功');
};

// 监听选中用户变化，更新角色选择
watch(selectedUserId, (userId) => {
  if (userId) {
    const user = adminStore.users.find(u => u.id === userId);
    if (user) {
      selectedRoleIds.value = user.roles.map(r => r.id);
    }
  } else {
    selectedRoleIds.value = [];
  }
});

// ==================== 初始化 ====================
onMounted(async () => {
  await Promise.all([
    adminStore.fetchUsers(),
    adminStore.fetchRoles(),
    adminStore.fetchTaskLogs(),
    loadConfigurations(),
  ]);
});

// ==================== 
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.admin-module {
  padding: $spacing-lg;
  background: $bg-page;
  min-height: calc(100vh - 120px);
}

.page-header {
  margin-bottom: $spacing-lg;
  h2 { margin: 0 0 $spacing-xs 0; font-size: 24px; font-weight: $font-weight-semibold; color: $text-primary; }
  .subtitle { margin: 0; color: $text-secondary; font-size: $font-size-base; }
}

.admin-tabs {
  background: $bg-white;
  border-radius: $border-radius-base;
  padding: $spacing-md;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  .header-left { display: flex; gap: $spacing-sm; align-items: center; }
  .header-right { display: flex; gap: $spacing-sm; }
}

.stats-row {
  margin-bottom: $spacing-md;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-base;
  padding: $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: $border-radius-medium;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    &.total { background: rgba($primary-color, 0.08); color: $primary-color; }
    &.active { background: rgba($success-color, 0.1); color: $success-color; }
    &.disabled { background: rgba($danger-color, 0.08); color: $danger-color; }
    &.roles { background: rgba($warning-color, 0.1); color: $warning-color; }
    &.running { background: rgba($warning-color, 0.1); color: $warning-color; }
  }
  .stat-info {
    .stat-value { font-size: $font-size-hero; font-weight: $font-weight-semibold; color: $text-primary; line-height: 1.2; }
    .stat-label { font-size: $font-size-base; color: $text-secondary; margin-top: $spacing-xxs; }
  }
}

.user-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  .user-info {
    .username { font-weight: $font-weight-medium; color: $text-primary; }
    .name { font-size: $font-size-extra-small; color: $text-secondary; }
  }
}

.batch-actions {
  position: fixed;
  bottom: $spacing-lg;
  left: 50%;
  transform: translateX(-50%);
  padding: $spacing-sm $spacing-lg;
  background: $bg-white;
  border-radius: $border-radius-base;
  box-shadow: $shadow-lg;
  display: flex;
  align-items: center;
  gap: $spacing-base;
  z-index: $z-index-top;
  .selected-count { font-weight: $font-weight-medium; color: $primary-color; }
}

.pagination-wrapper {
  margin-top: $spacing-md;
  display: flex;
  justify-content: flex-end;
}

.text-muted { color: $text-secondary; }
.text-danger { color: $danger-color; }

.task-name-cell {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  .el-icon { font-size: 18px; }
  .task-icon-collection { color: $primary-color; }
  .task-icon-preprocess { color: $warning-color; }
  .task-icon-analysis { color: $success-color; }
  .task-icon-spark { color: $danger-color; }
  .task-icon-export { color: $info-color; }
}

.resource-usage {
  font-size: $font-size-extra-small;
  color: $text-regular;
  span { display: block; }
}

.task-log-detail {
  .detail-section {
    margin-bottom: $spacing-lg;
    h4 { margin: 0 0 $spacing-base 0; font-size: $font-size-large; font-weight: $font-weight-medium; color: $text-primary; border-left: 3px solid $primary-color; padding-left: $spacing-sm; }
    &.error-section h4 { border-left-color: $danger-color; }
  }
  .resource-card {
    text-align: center;
    padding: $spacing-md;
    background: $bg-page;
    border-radius: $border-radius-base;
    .resource-label { font-size: $font-size-base; color: $text-secondary; margin-bottom: $spacing-sm; }
    .resource-value { font-size: 24px; font-weight: $font-weight-semibold; color: $text-primary; }
  }
  .step-content {
    .step-header { display: flex; align-items: center; gap: $spacing-sm; margin-bottom: $spacing-xs; }
    .step-name { font-weight: $font-weight-medium; color: $text-primary; }
    .step-message { font-size: $font-size-small; color: $text-regular; }
    .step-details {
      margin-top: $spacing-xs;
      pre { margin: 0; padding: $spacing-sm; background: #1e1e1e; color: #d4d4d4; border-radius: $border-radius-small; font-size: $font-size-extra-small; overflow-x: auto; }
    }
  }
}

.settings-card, .status-card {
  border-radius: $border-radius-base;
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: $font-weight-medium;
  }
}

.form-hint {
  margin-left: $spacing-xs;
  color: $text-secondary;
  font-size: $font-size-small;
}

.system-metrics {
  .metric-item {
    margin-bottom: $spacing-base;
    .metric-label { font-size: $font-size-base; color: $text-regular; margin-bottom: $spacing-xs; }
    .metric-value { font-size: $font-size-extra-large; font-weight: $font-weight-semibold; color: $text-primary; }
    .metric-detail { font-size: $font-size-extra-small; color: $text-secondary; margin-top: $spacing-xxs; }
  }
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-card {
  .role-description {
    .role-intro {
      margin: 0 0 $spacing-base;
      color: $text-regular;
      font-size: $font-size-base;
      line-height: 1.6;
    }
  }
  
  .permission-list {
    .permission-item {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      padding: $spacing-sm 0;
      border-bottom: 1px solid $border-light;
      
      &:last-child {
        border-bottom: none;
      }
      
      span {
        font-size: $font-size-base;
        color: $text-primary;
        
        &.disabled {
          color: $text-placeholder;
          text-decoration: line-through;
        }
      }
    }
  }
}

.sys-log-list {
  max-height: 500px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: $font-size-extra-small;

  .no-logs {
    text-align: center;
    color: $text-secondary;
    padding: 40px 0;
  }

  .sys-log-item {
    display: flex;
    align-items: flex-start;
    gap: $spacing-xs;
    padding: 6px $spacing-xs;
    border-bottom: 1px solid $border-lighter;
    line-height: 1.5;

    .log-level-tag {
      flex-shrink: 0;
      min-width: 64px;
      text-align: center;
    }

    .log-message {
      word-break: break-all;
      color: $text-regular;
    }

    &.log-error .log-message { color: $danger-color; }
    &.log-warning .log-message { color: $warning-color; }
    &.log-debug .log-message { color: $text-secondary; }
  }
}

.slide-up-enter-active, .slide-up-leave-active {
  transition: all 0.3s ease;
}
.slide-up-enter-from, .slide-up-leave-to {
  transform: translateX(-50%) translateY(100%);
  opacity: 0;
}

:deep(.el-tabs__header) {
  margin-bottom: 20px;
}

:deep(.el-card__header) {
  padding: $spacing-base $spacing-md;
  border-bottom: 1px solid $border-base;
}

:deep(.is-loading) {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.restart-warning {
  h4 {
    margin: 0 0 $spacing-sm 0;
    color: $warning-color;
    font-size: $font-size-medium;
  }
  
  ul {
    margin: $spacing-sm 0;
    padding-left: $spacing-lg;
    
    li {
      margin-bottom: $spacing-xs;
      color: $text-regular;
      font-size: $font-size-small;
    }
  }
}

.real-time-controls {
  position: fixed;
  top: 120px;
  right: 20px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-base;
  background: $bg-white;
  border-radius: $border-radius-base;
  box-shadow: $shadow-lg;
  border: 1px solid $border-base;
}
</style>
