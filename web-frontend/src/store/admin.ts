/**
 * 系统管理 Store
 * 管理用户、角色、任务日志、系统配置等状态
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  type User,
  type Role,
  type SystemConfig,
  type SystemMetrics,
  type SystemLog,
  type AuditLog,
  type Backup,
  type UserStatus,
  getUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  batchDeleteUsers,
  resetPassword,
  updateUserStatus,
  batchUpdateUserStatus,
  getUserStatistics,
  getRoles,
  getRole,
  createRole,
  updateRole,
  deleteRole,
  getPermissionTree,
  assignUserRole,
  getSystemConfig,
  updateSystemConfig,
  getSystemMetrics,
  getSystemLogs,
  getAuditLogs,
  getBackupList,
  createBackup,
  restoreBackup,
  deleteBackup,
  testEmailConfig,
} from '@/api/admin';

/** 任务日志类型 */
export interface TaskLog {
  id: string;
  taskName: string;
  taskType: 'collection' | 'preprocess' | 'analysis' | 'export' | 'spark';
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  startTime: string;
  endTime?: string;
  duration?: string;
  progress?: number;
  executor?: string;
  resourceUsage?: {
    cpu: number;
    memory: number;
    disk: number;
  };
  steps?: TaskStep[];
  errorMessage?: string;
}

/** 任务执行步骤 */
export interface TaskStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  startTime?: string;
  endTime?: string;
  message?: string;
  details?: string;
}

/** Spark 配置 */
export interface SparkConfig {
  master: string;
  appName: string;
  executorMemory: string;
  executorCores: number;
  driverMemory: string;
  driverCores: number;
  partitions: number;
  maxRetries: number;
  shufflePartitions: number;
  dynamicAllocation: boolean;
  minExecutors: number;
  maxExecutors: number;
}

export const useAdminStore = defineStore('admin', () => {
  // ==================== State ====================
  
  // 用户管理
  const users = ref<User[]>([]);
  const currentUser = ref<User | null>(null);
  const userTotal = ref(0);
  const userStatistics = ref<{
    total: number;
    active: number;
    disabled: number;
    inactive: number;
    growthTrend: Array<{ date: string; count: number }>;
    roleDistribution: Array<{ role: string; count: number }>;
    activityRate: number;
  } | null>(null);
  
  // 角色权限
  const roles = ref<Role[]>([]);
  const permissions = ref<any[]>([]);
  
  // 任务日志
  const taskLogs = ref<TaskLog[]>([]);
  const taskLogTotal = ref(0);
  const currentTaskLog = ref<TaskLog | null>(null);
  
  // 系统日志
  const systemLogs = ref<SystemLog[]>([]);
  const systemLogTotal = ref(0);
  const auditLogs = ref<AuditLog[]>([]);
  const auditLogTotal = ref(0);
  
  // 系统配置
  const systemConfig = ref<SystemConfig | null>(null);
  const sparkConfig = ref<SparkConfig>({
    master: 'local[*]',
    appName: 'WeiboSentimentAnalysis',
    executorMemory: '4g',
    executorCores: 2,
    driverMemory: '2g',
    driverCores: 1,
    partitions: 200,
    maxRetries: 3,
    shufflePartitions: 200,
    dynamicAllocation: false,
    minExecutors: 1,
    maxExecutors: 10,
  });
  
  // 系统监控
  const systemMetrics = ref<SystemMetrics | null>(null);
  
  // 备份
  const backups = ref<Backup[]>([]);
  const backupTotal = ref(0);
  
  // 加载状态
  const isLoading = ref(false);
  const isLoadingUsers = ref(false);
  const isLoadingLogs = ref(false);
  const isLoadingConfig = ref(false);
  
  // ==================== Getters ====================
  
  const activeUsers = computed(() => {
    return users.value.filter(u => u.status === 'active');
  });
  
  const disabledUsers = computed(() => {
    return users.value.filter(u => u.status === 'disabled');
  });
  
  const usersByRole = computed(() => {
    const grouped: Record<string, User[]> = {};
    users.value.forEach(user => {
      user.roles.forEach(role => {
        if (!grouped[role.name]) {
          grouped[role.name] = [];
        }
        grouped[role.name].push(user);
      });
    });
    return grouped;
  });
  
  const runningTasks = computed(() => {
    return taskLogs.value.filter(t => t.status === 'running');
  });
  
  const failedTasks = computed(() => {
    return taskLogs.value.filter(t => t.status === 'failed');
  });
  
  const tasksByType = computed(() => {
    const grouped: Record<string, TaskLog[]> = {};
    taskLogs.value.forEach(task => {
      if (!grouped[task.taskType]) {
        grouped[task.taskType] = [];
      }
      grouped[task.taskType].push(task);
    });
    return grouped;
  });
  
  // ==================== Actions ====================
  
  // ---------- 用户管理 ----------
  
  async function fetchUsers(params?: {
    page?: number;
    pageSize?: number;
    keyword?: string;
    status?: UserStatus;
    roleId?: string;
  }) {
    isLoadingUsers.value = true;
    try {
      const { list, total } = await getUsers(params);
      users.value = list;
      userTotal.value = total;
    } finally {
      isLoadingUsers.value = false;
    }
  }
  
  async function fetchUser(id: string) {
    isLoading.value = true;
    try {
      currentUser.value = await getUser(id);
    } finally {
      isLoading.value = false;
    }
  }
  
  async function addUser(data: {
    username: string;
    password: string;
    name: string;
    email: string;
    phone?: string;
    roleIds: string[];
  }) {
    const user = await createUser(data);
    users.value.unshift(user);
    userTotal.value++;
    return user;
  }
  
  async function modifyUser(id: string, data: Partial<User>) {
    const updated = await updateUser(id, data);
    const index = users.value.findIndex(u => u.id === id);
    if (index !== -1) {
      users.value[index] = updated;
    }
    return updated;
  }
  
  async function removeUser(id: string) {
    await deleteUser(id);
    users.value = users.value.filter(u => u.id !== id);
    userTotal.value--;
  }
  
  async function batchRemoveUsers(ids: string[]) {
    await batchDeleteUsers(ids);
    users.value = users.value.filter(u => !ids.includes(u.id));
    userTotal.value -= ids.length;
  }
  
  async function changeUserStatus(id: string, status: UserStatus) {
    await updateUserStatus(id, status);
    const user = users.value.find(u => u.id === id);
    if (user) {
      user.status = status;
    }
  }
  
  async function batchChangeUserStatus(ids: string[], status: UserStatus) {
    await batchUpdateUserStatus(ids, status);
    users.value.forEach(user => {
      if (ids.includes(user.id)) {
        user.status = status;
      }
    });
  }
  
  async function resetUserPassword(id: string, newPassword?: string) {
    return await resetPassword(id, newPassword);
  }
  
  async function fetchUserStatistics() {
    userStatistics.value = await getUserStatistics();
  }
  
  // ---------- 角色权限 ----------
  
  async function fetchRoles() {
    isLoading.value = true;
    try {
      roles.value = await getRoles();
    } finally {
      isLoading.value = false;
    }
  }
  
  async function addRole(data: {
    name: string;
    code: string;
    description: string;
    permissions: string[];
  }) {
    const role = await createRole(data);
    roles.value.push(role);
    return role;
  }
  
  async function modifyRole(id: string, data: Partial<Role>) {
    const updated = await updateRole(id, data);
    const index = roles.value.findIndex(r => r.id === id);
    if (index !== -1) {
      roles.value[index] = updated;
    }
    return updated;
  }
  
  async function removeRole(id: string) {
    await deleteRole(id);
    roles.value = roles.value.filter(r => r.id !== id);
  }
  
  async function fetchPermissions() {
    permissions.value = await getPermissionTree();
  }
  
  async function assignRoles(userId: string, roleIds: string[]) {
    await assignUserRole(userId, roleIds);
    const user = users.value.find(u => u.id === userId);
    if (user) {
      user.roles = roles.value.filter(r => roleIds.includes(r.id));
    }
  }
  
  // ---------- 任务日志 ----------
  
  async function fetchTaskLogs(params?: {
    page?: number;
    pageSize?: number;
    taskType?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
  }) {
    isLoadingLogs.value = true;
    try {
      const apiClient = (await import('@/api')).default;
      const query: Record<string, any> = {};
      if (params?.taskType) query.taskType = params.taskType;
      if (params?.status) query.status = params.status;
      if (params?.startDate) query.startDate = params.startDate;
      if (params?.endDate) query.endDate = params.endDate;

      const resp = await apiClient.get<any>('/admin/tasks', { params: query });
      const body = resp.data;
      const list: TaskLog[] = Array.isArray(body?.data) ? body.data : (Array.isArray(body) ? body : []);
      taskLogs.value = list;
      taskLogTotal.value = body?.total ?? list.length;
    } catch (e) {
      console.error('fetchTaskLogs failed', e);
      taskLogs.value = [];
      taskLogTotal.value = 0;
    } finally {
      isLoadingLogs.value = false;
    }
  }
  
  async function fetchTaskLogDetail(id: string) {
    isLoading.value = true;
    try {
      await new Promise(resolve => setTimeout(resolve, 200));
      currentTaskLog.value = taskLogs.value.find(t => t.id === id) || null;
    } finally {
      isLoading.value = false;
    }
  }
  
  // ---------- 系统日志 ----------
  
  async function fetchSystemLogs(params?: {
    level?: 'info' | 'warn' | 'error';
    module?: string;
    keyword?: string;
    startDate?: string;
    endDate?: string;
    page?: number;
    pageSize?: number;
  }) {
    isLoadingLogs.value = true;
    try {
      const { list, total } = await getSystemLogs(params);
      systemLogs.value = list;
      systemLogTotal.value = total;
    } finally {
      isLoadingLogs.value = false;
    }
  }
  
  async function fetchAuditLogs(params?: {
    userId?: string;
    action?: string;
    resource?: string;
    startDate?: string;
    endDate?: string;
    page?: number;
    pageSize?: number;
  }) {
    isLoadingLogs.value = true;
    try {
      const { list, total } = await getAuditLogs(params);
      auditLogs.value = list;
      auditLogTotal.value = total;
    } finally {
      isLoadingLogs.value = false;
    }
  }
  
  // ---------- 系统配置 ----------
  
  async function fetchSystemConfig() {
    isLoadingConfig.value = true;
    try {
      systemConfig.value = await getSystemConfig();
    } finally {
      isLoadingConfig.value = false;
    }
  }
  
  async function saveSystemConfig(data: Partial<SystemConfig>) {
    systemConfig.value = await updateSystemConfig(data);
  }
  
  async function saveSparkConfig(config: SparkConfig) {
    // 模拟保存 Spark 配置
    await new Promise(resolve => setTimeout(resolve, 300));
    sparkConfig.value = { ...config };
  }
  
  async function testEmail(data: {
    host: string;
    port: number;
    user: string;
    password: string;
    to: string;
  }) {
    return await testEmailConfig(data);
  }
  
  // ---------- 系统监控 ----------
  
  async function fetchSystemMetrics() {
    systemMetrics.value = await getSystemMetrics();
  }
  
  // ---------- 备份管理 ----------
  
  async function fetchBackups(params?: {
    type?: 'full' | 'incremental';
    status?: string;
    page?: number;
    pageSize?: number;
  }) {
    isLoading.value = true;
    try {
      const { list, total } = await getBackupList(params);
      backups.value = list;
      backupTotal.value = total;
    } finally {
      isLoading.value = false;
    }
  }
  
  async function createNewBackup(data: {
    name: string;
    type: 'full' | 'incremental';
    description?: string;
  }) {
    return await createBackup(data);
  }
  
  async function restoreFromBackup(id: string) {
    return await restoreBackup(id);
  }
  
  async function removeBackup(id: string) {
    await deleteBackup(id);
    backups.value = backups.value.filter(b => b.id !== id);
    backupTotal.value--;
  }
  
  // ---------- 初始化 ----------
  
  async function initialize() {
    await Promise.all([
      fetchUsers(),
      fetchRoles(),
      fetchTaskLogs(),
      fetchSystemConfig(),
    ]);
  }
  
  return {
    // State
    users,
    currentUser,
    userTotal,
    userStatistics,
    roles,
    permissions,
    taskLogs,
    taskLogTotal,
    currentTaskLog,
    systemLogs,
    systemLogTotal,
    auditLogs,
    auditLogTotal,
    systemConfig,
    sparkConfig,
    systemMetrics,
    backups,
    backupTotal,
    isLoading,
    isLoadingUsers,
    isLoadingLogs,
    isLoadingConfig,
    
    // Getters
    activeUsers,
    disabledUsers,
    usersByRole,
    runningTasks,
    failedTasks,
    tasksByType,
    
    // Actions - 用户管理
    fetchUsers,
    fetchUser,
    addUser,
    modifyUser,
    removeUser,
    batchRemoveUsers,
    changeUserStatus,
    batchChangeUserStatus,
    resetUserPassword,
    fetchUserStatistics,
    
    // Actions - 角色权限
    fetchRoles,
    addRole,
    modifyRole,
    removeRole,
    fetchPermissions,
    assignRoles,
    
    // Actions - 任务日志
    fetchTaskLogs,
    fetchTaskLogDetail,
    
    // Actions - 系统日志
    fetchSystemLogs,
    fetchAuditLogs,
    
    // Actions - 系统配置
    fetchSystemConfig,
    saveSystemConfig,
    saveSparkConfig,
    testEmail,
    
    // Actions - 系统监控
    fetchSystemMetrics,
    
    // Actions - 备份管理
    fetchBackups,
    createNewBackup,
    restoreFromBackup,
    removeBackup,
    
    // Actions - 初始化
    initialize,
  };
});
