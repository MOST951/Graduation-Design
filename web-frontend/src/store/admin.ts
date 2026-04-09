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
      // 模拟任务日志数据
      await new Promise(resolve => setTimeout(resolve, 300));
      
      const mockLogs: TaskLog[] = [
        {
          id: 'task-1',
          taskName: '微博热点数据采集',
          taskType: 'collection',
          status: 'success',
          startTime: '2024-12-10 09:00:00',
          endTime: '2024-12-10 09:05:30',
          duration: '5分30秒',
          progress: 100,
          executor: 'admin',
          resourceUsage: { cpu: 45, memory: 2048, disk: 512 },
          steps: [
            { id: 's1', name: '初始化爬虫', status: 'success', startTime: '09:00:00', endTime: '09:00:05', message: '爬虫初始化完成' },
            { id: 's2', name: '获取热点列表', status: 'success', startTime: '09:00:05', endTime: '09:01:00', message: '获取50条热点' },
            { id: 's3', name: '采集微博数据', status: 'success', startTime: '09:01:00', endTime: '09:04:30', message: '采集12580条微博' },
            { id: 's4', name: '数据存储', status: 'success', startTime: '09:04:30', endTime: '09:05:30', message: '存储完成' },
          ],
        },
        {
          id: 'task-2',
          taskName: 'Spark情感分析任务',
          taskType: 'spark',
          status: 'running',
          startTime: '2024-12-10 09:30:00',
          progress: 65,
          executor: 'system',
          resourceUsage: { cpu: 78, memory: 8192, disk: 1024 },
          steps: [
            { id: 's1', name: 'Spark初始化', status: 'success', startTime: '09:30:00', endTime: '09:30:15', message: 'SparkContext创建成功' },
            { id: 's2', name: '数据加载', status: 'success', startTime: '09:30:15', endTime: '09:31:00', message: '加载125800条数据' },
            { id: 's3', name: '情感分析处理', status: 'running', startTime: '09:31:00', message: '正在处理中...' },
            { id: 's4', name: '结果汇总', status: 'pending' },
          ],
        },
        {
          id: 'task-3',
          taskName: '数据预处理任务',
          taskType: 'preprocess',
          status: 'failed',
          startTime: '2024-12-10 08:00:00',
          endTime: '2024-12-10 08:02:15',
          duration: '2分15秒',
          progress: 35,
          executor: 'admin',
          resourceUsage: { cpu: 25, memory: 1024, disk: 256 },
          errorMessage: '内存不足，无法完成数据清洗操作',
          steps: [
            { id: 's1', name: '数据加载', status: 'success', startTime: '08:00:00', endTime: '08:00:30', message: '加载完成' },
            { id: 's2', name: '文本清洗', status: 'failed', startTime: '08:00:30', endTime: '08:02:15', message: '内存溢出', details: 'java.lang.OutOfMemoryError: Java heap space' },
          ],
        },
        {
          id: 'task-4',
          taskName: '分析报告导出',
          taskType: 'export',
          status: 'success',
          startTime: '2024-12-10 07:30:00',
          endTime: '2024-12-10 07:31:00',
          duration: '1分钟',
          progress: 100,
          executor: 'analyst',
          resourceUsage: { cpu: 15, memory: 512, disk: 128 },
        },
        {
          id: 'task-5',
          taskName: '定时数据采集',
          taskType: 'collection',
          status: 'pending',
          startTime: '2024-12-10 10:00:00',
          progress: 0,
          executor: 'scheduler',
        },
      ];
      
      // 根据参数过滤
      let filtered = [...mockLogs];
      if (params?.taskType) {
        filtered = filtered.filter(t => t.taskType === params.taskType);
      }
      if (params?.status) {
        filtered = filtered.filter(t => t.status === params.status);
      }
      
      taskLogs.value = filtered;
      taskLogTotal.value = filtered.length;
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
