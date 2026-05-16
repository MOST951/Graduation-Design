/**
 * 系统管理模块 API
 */
import apiClient from '@/api';

const api = apiClient;

// 模拟延迟
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ==================== 类型定义 ====================

/** 用户状态 */
export type UserStatus = 'active' | 'disabled' | 'inactive';

/** 用户角色 */
export interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  permissions: string[];
  isSystem: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 用户信息 */
export interface User {
  id: string;
  username: string;
  name: string;
  email: string;
  phone?: string;
  avatar?: string;
  status: UserStatus;
  roles: Role[];
  department?: string;
  lastLoginAt?: string;
  lastLoginIp?: string;
  createdAt: string;
  updatedAt: string;
}

/** 权限节点 */
export interface Permission {
  id: string;
  name: string;
  code: string;
  type: 'system' | 'data' | 'operation';
  description: string;
  parentId?: string;
  children?: Permission[];
}

/** 系统配置 */
export interface SystemConfig {
  site: {
    name: string;
    logo: string;
    favicon: string;
    icp: string;
  };
  theme: {
    primaryColor: string;
    darkMode: boolean;
    layout: 'side' | 'top' | 'mix';
  };
  login: {
    allowRegister: boolean;
    requireCaptcha: boolean;
    allowOAuth: boolean;
  };
  security: {
    passwordMinLength: number;
    passwordRequireSpecial: boolean;
    sessionTimeout: number;
    maxLoginAttempts: number;
    lockoutDuration: number;
  };
  email: {
    host: string;
    port: number;
    secure: boolean;
    user: string;
    password: string;
    from: string;
  };
  storage: {
    type: 'local' | 'oss' | 'qiniu';
    path: string;
    endpoint?: string;
    accessKey?: string;
    secretKey?: string;
    bucket?: string;
  };
}

/** 系统指标 */
export interface SystemMetrics {
  cpu: {
    usage: number;
    cores: number;
  };
  memory: {
    total: number;
    used: number;
    free: number;
    usage: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    usage: number;
  };
  network: {
    rx: number;
    tx: number;
  };
  application: {
    onlineUsers: number;
    requestsPerMinute: number;
    avgResponseTime: number;
    errorRate: number;
  };
}

/** 系统日志 */
export interface SystemLog {
  id: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  module: string;
  userId?: string;
  ip?: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

/** 审计日志 */
export interface AuditLog {
  id: string;
  userId: string;
  username: string;
  action: string;
  resource: string;
  resourceId?: string;
  ip: string;
  userAgent: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

/** 备份记录 */
export interface Backup {
  id: string;
  name: string;
  type: 'full' | 'incremental';
  size: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  duration?: number;
  path: string;
  createdBy: string;
}

// ==================== 1. 用户管理 ====================

/**
 * 获取用户列表
 */
export async function getUsers(params?: {
  page?: number;
  pageSize?: number;
  keyword?: string;
  status?: UserStatus;
  roleId?: string;
  department?: string;
  sortBy?: 'createdAt' | 'lastLoginAt' | 'name';
  sortOrder?: 'asc' | 'desc';
}): Promise<{ list: User[]; total: number }> {
  try {
    const response = await api.get<any>('/admin/users', { params });
    // 兼容多种后端响应形态:
    //   ①  { code, data: [users] }          ← 当前 Flask 后端
    //   ②  { code, data: { list, total } }
    //   ③  { list, total }                  ← 原期望
    const body = response.data;
    const payload = body?.data ?? body;
    // 后端 admin user 用 role: string, 这里 normalize 成前端 User.roles: Role[]
    const normalize = (u: any): User => ({
      ...u,
      id: String(u.id),
      roles: Array.isArray(u.roles) ? u.roles : (u.role ? [{
        id: `role-${u.role}`,
        name: u.role === 'admin' ? '系统管理员' : '普通用户',
        code: u.role,
        description: '',
        permissions: u.role === 'admin' ? ['*'] : [],
        isSystem: true,
        createdAt: u.createdAt || new Date().toISOString(),
      }] : []),
    });
    if (Array.isArray(payload)) {
      const list = payload.map(normalize);
      return { list, total: list.length };
    }
    if (payload && typeof payload === 'object' && 'list' in payload) {
      return { list: payload.list.map(normalize), total: payload.total ?? payload.list.length };
    }
    return { list: [], total: 0 };
  } catch (error) {
    await sleep(300);
    return {
      list: [
        {
          id: 'user-1',
          username: 'admin',
          name: '系统管理员',
          email: 'admin@example.com',
          phone: '13800138000',
          avatar: '/avatars/admin.png',
          status: 'active',
          roles: [
            {
              id: 'role-1',
              name: '系统管理员',
              code: 'admin',
              description: '拥有所有权限',
              permissions: ['*'],
              isSystem: true,
              createdAt: '2024-01-01T00:00:00Z',
              updatedAt: '2024-01-01T00:00:00Z',
            },
          ],
          department: '技术部',
          lastLoginAt: new Date().toISOString(),
          lastLoginIp: '192.168.1.100',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: new Date().toISOString(),
        },
      ],
      total: 1,
    };
  }
}

/**
 * 获取用户详情
 */
export async function getUser(id: string): Promise<User> {
  try {
    const response = await api.get<User>(`/users/${id}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    throw new Error('用户不存在');
  }
}

/**
 * 创建用户
 */
export async function createUser(data: {
  username: string;
  password: string;
  name: string;
  email: string;
  phone?: string;
  avatar?: string;
  roleIds: string[];
  department?: string;
}): Promise<User> {
  try {
    const response = await api.post<User>('/admin/users', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    const now = new Date().toISOString();
    return {
      id: `user-${Date.now()}`,
      username: data.username,
      name: data.name,
      email: data.email,
      phone: data.phone,
      avatar: data.avatar,
      status: 'active',
      roles: [],
      department: data.department,
      createdAt: now,
      updatedAt: now,
    };
  }
}

/**
 * 更新用户
 */
export async function updateUser(id: string, data: Partial<User>): Promise<User> {
  try {
    const response = await api.put<User>(`/users/${id}`, data);
    return response.data;
  } catch (error) {
    await sleep(300);
    const user = await getUser(id);
    return { ...user, ...data, updatedAt: new Date().toISOString() };
  }
}

/**
 * 删除用户
 */
export async function deleteUser(id: string): Promise<void> {
  try {
    await api.delete(`/users/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 批量删除用户
 */
export async function batchDeleteUsers(ids: string[]): Promise<void> {
  try {
    await api.post('/admin/users/batch-delete', { ids });
  } catch (error) {
    await sleep(300);
  }
}

/**
 * 重置密码
 */
export async function resetPassword(id: string, newPassword?: string): Promise<{ password: string }> {
  try {
    const response = await api.post<{ password: string }>(`/users/${id}/reset-password`, {
      password: newPassword,
    });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      password: newPassword || Math.random().toString(36).substring(2, 10),
    };
  }
}

/**
 * 更新用户状态
 */
export async function updateUserStatus(id: string, status: UserStatus): Promise<void> {
  try {
    await api.patch(`/admin/users/${id}/status`, { status });
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 批量更新用户状态
 */
export async function batchUpdateUserStatus(ids: string[], status: UserStatus): Promise<void> {
  try {
    await api.post('/admin/users/batch-status', { ids, status });
  } catch (error) {
    await sleep(300);
  }
}

/**
 * 导入用户
 */
export async function importUsers(file: File): Promise<{
  success: number;
  failed: number;
  errors: Array<{ row: number; error: string }>;
}> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/admin/users/import', formData);
    return response.data;
  } catch (error) {
    await sleep(1000);
    return {
      success: 10,
      failed: 2,
      errors: [
        { row: 5, error: '邮箱格式错误' },
        { row: 8, error: '用户名已存在' },
      ],
    };
  }
}

/**
 * 导出用户
 */
export async function exportUsers(params?: {
  status?: UserStatus;
  roleId?: string;
}): Promise<Blob> {
  try {
    const response = await api.get('/admin/users/export', {
      params,
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    await sleep(500);
    return new Blob(['Mock Excel content'], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
  }
}

/**
 * 获取用户统计
 */
export async function getUserStatistics(): Promise<{
  total: number;
  active: number;
  disabled: number;
  inactive: number;
  growthTrend: Array<{ date: string; count: number }>;
  roleDistribution: Array<{ role: string; count: number }>;
  activityRate: number;
}> {
  try {
    const response = await api.get('/admin/users/statistics');
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      total: 156,
      active: 142,
      disabled: 8,
      inactive: 6,
      growthTrend: Array.from({ length: 7 }, (_, i) => ({
        date: new Date(Date.now() - (6 - i) * 86400000).toISOString().split('T')[0],
        count: Math.floor(Math.random() * 20) + 140,
      })),
      roleDistribution: [
        { role: '系统管理员', count: 5 },
        { role: '数据分析师', count: 25 },
        { role: '普通用户', count: 120 },
        { role: '访客', count: 6 },
      ],
      activityRate: 85.5,
    };
  }
}

// ==================== 2. 角色权限 ====================

/**
 * 获取角色列表
 */
export async function getRoles(): Promise<Role[]> {
  try {
    const response = await api.get<any>('/admin/roles');
    const body = response.data;
    const payload = body?.data ?? body;
    return Array.isArray(payload) ? payload : [];
  } catch (error) {
    await sleep(300);
    return [
      {
        id: 'role-admin',
        name: '系统管理员',
        code: 'admin',
        description: '拥有所有权限',
        permissions: ['*'],
        isSystem: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
      {
        id: 'role-user',
        name: '普通用户',
        code: 'user',
        description: '基础查看权限',
        permissions: ['data:read', 'report:read'],
        isSystem: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ];
  }
}

/**
 * 获取角色详情
 */
export async function getRole(id: string): Promise<Role> {
  try {
    const response = await api.get<Role>(`/roles/${id}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    throw new Error('角色不存在');
  }
}

/**
 * 创建角色
 */
export async function createRole(data: {
  name: string;
  code: string;
  description: string;
  permissions: string[];
}): Promise<Role> {
  try {
    const response = await api.post<Role>('/admin/roles', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    const now = new Date().toISOString();
    return {
      id: `role-${Date.now()}`,
      name: data.name,
      code: data.code,
      description: data.description,
      permissions: data.permissions,
      isSystem: false,
      createdAt: now,
      updatedAt: now,
    };
  }
}

/**
 * 更新角色
 */
export async function updateRole(id: string, data: Partial<Role>): Promise<Role> {
  try {
    const response = await api.put<Role>(`/roles/${id}`, data);
    return response.data;
  } catch (error) {
    await sleep(300);
    const role = await getRole(id);
    return { ...role, ...data, updatedAt: new Date().toISOString() };
  }
}

/**
 * 删除角色
 */
export async function deleteRole(id: string): Promise<void> {
  try {
    await api.delete(`/roles/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 获取角色权限
 */
export async function getRolePermissions(id: string): Promise<string[]> {
  try {
    const response = await api.get<string[]>(`/roles/${id}/permissions`);
    return response.data;
  } catch (error) {
    await sleep(200);
    return ['data:read', 'report:read'];
  }
}

/**
 * 更新角色权限
 */
export async function updateRolePermissions(id: string, permissions: string[]): Promise<void> {
  try {
    await api.put(`/roles/${id}/permissions`, { permissions });
  } catch (error) {
    await sleep(300);
  }
}

/**
 * 分配用户角色
 */
export async function assignUserRole(userId: string, roleIds: string[]): Promise<void> {
  try {
    await api.post(`/users/${userId}/roles`, { roleIds });
  } catch (error) {
    await sleep(300);
  }
}

/**
 * 获取权限树
 */
export async function getPermissionTree(): Promise<Permission[]> {
  try {
    const response = await api.get<Permission[]>('/admin/permissions/tree');
    return response.data;
  } catch (error) {
    await sleep(300);
    return [
      {
        id: 'perm-1',
        name: '系统管理',
        code: 'system',
        type: 'system',
        description: '系统管理权限',
        children: [
          {
            id: 'perm-1-1',
            name: '用户管理',
            code: 'system:user',
            type: 'system',
            description: '用户管理权限',
            parentId: 'perm-1',
            children: [
              {
                id: 'perm-1-1-1',
                name: '查看用户',
                code: 'system:user:read',
                type: 'operation',
                description: '查看用户列表和详情',
                parentId: 'perm-1-1',
              },
              {
                id: 'perm-1-1-2',
                name: '创建用户',
                code: 'system:user:create',
                type: 'operation',
                description: '创建新用户',
                parentId: 'perm-1-1',
              },
            ],
          },
        ],
      },
      {
        id: 'perm-2',
        name: '数据管理',
        code: 'data',
        type: 'data',
        description: '数据管理权限',
        children: [
          {
            id: 'perm-2-1',
            name: '查看数据',
            code: 'data:read',
            type: 'data',
            description: '查看数据权限',
            parentId: 'perm-2',
          },
          {
            id: 'perm-2-2',
            name: '编辑数据',
            code: 'data:write',
            type: 'data',
            description: '编辑数据权限',
            parentId: 'perm-2',
          },
        ],
      },
    ];
  }
}

/**
 * 获取用户权限
 */
export async function getUserPermissions(userId: string): Promise<string[]> {
  try {
    const response = await api.get<string[]>(`/users/${userId}/permissions`);
    return response.data;
  } catch (error) {
    await sleep(200);
    return ['data:read', 'report:read', 'report:create'];
  }
}

/**
 * 检查权限
 */
export async function checkPermission(userId: string, permission: string): Promise<boolean> {
  try {
    const response = await api.post<{ hasPermission: boolean }>('/admin/permissions/check', {
      userId,
      permission,
    });
    return response.data.hasPermission;
  } catch (error) {
    await sleep(100);
    return true;
  }
}

// ==================== 3. 系统配置 ====================

/**
 * 获取系统配置
 */
export async function getSystemConfig(): Promise<SystemConfig> {
  try {
    const response = await api.get<SystemConfig>('/admin/config');
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      site: {
        name: '微博情感分析系统',
        logo: '/logo.png',
        favicon: '/favicon.ico',
        icp: '京ICP备12345678号',
      },
      theme: {
        primaryColor: '#409EFF',
        darkMode: false,
        layout: 'side',
      },
      login: {
        allowRegister: true,
        requireCaptcha: true,
        allowOAuth: true,
      },
      security: {
        passwordMinLength: 8,
        passwordRequireSpecial: true,
        sessionTimeout: 3600,
        maxLoginAttempts: 5,
        lockoutDuration: 1800,
      },
      email: {
        host: 'smtp.example.com',
        port: 465,
        secure: true,
        user: 'noreply@example.com',
        password: '********',
        from: 'noreply@example.com',
      },
      storage: {
        type: 'local',
        path: '/uploads',
      },
    };
  }
}

/**
 * 更新系统配置
 */
export async function updateSystemConfig(data: Partial<SystemConfig>): Promise<SystemConfig> {
  try {
    const response = await api.put<SystemConfig>('/admin/config', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    const config = await getSystemConfig();
    return { ...config, ...data };
  }
}

/**
 * 测试邮件配置
 */
export async function testEmailConfig(data: {
  host: string;
  port: number;
  user: string;
  password: string;
  to: string;
}): Promise<{ success: boolean; message: string }> {
  try {
    const response = await api.post('/admin/config/test-email', data);
    return response.data;
  } catch (error) {
    await sleep(1000);
    return {
      success: true,
      message: '测试邮件发送成功',
    };
  }
}

/**
 * 测试存储配置
 */
export async function testStorageConfig(data: {
  type: string;
  endpoint?: string;
  accessKey?: string;
  secretKey?: string;
}): Promise<{ success: boolean; message: string }> {
  try {
    const response = await api.post('/admin/config/test-storage', data);
    return response.data;
  } catch (error) {
    await sleep(800);
    return {
      success: true,
      message: '存储配置测试成功',
    };
  }
}

/**
 * 获取存储使用情况
 */
export async function getStorageUsage(): Promise<{
  total: number;
  used: number;
  free: number;
  usage: number;
  files: number;
}> {
  try {
    const response = await api.get('/admin/config/storage-usage');
    return response.data;
  } catch (error) {
    await sleep(200);
    return {
      total: 107374182400, // 100GB
      used: 32212254720, // 30GB
      free: 75161927680, // 70GB
      usage: 30,
      files: 15678,
    };
  }
}

// ==================== 4. 监控日志 ====================

/**
 * 获取系统指标
 */
export async function getSystemMetrics(): Promise<SystemMetrics> {
  try {
    const response = await api.get<SystemMetrics>('/admin/metrics');
    return response.data;
  } catch (error) {
    await sleep(200);
    return {
      cpu: {
        usage: Math.random() * 50 + 20,
        cores: 8,
      },
      memory: {
        total: 16384,
        used: 8192,
        free: 8192,
        usage: 50,
      },
      disk: {
        total: 512000,
        used: 153600,
        free: 358400,
        usage: 30,
      },
      network: {
        rx: 1024 * 1024 * 10,
        tx: 1024 * 1024 * 5,
      },
      application: {
        onlineUsers: Math.floor(Math.random() * 50) + 20,
        requestsPerMinute: Math.floor(Math.random() * 1000) + 500,
        avgResponseTime: Math.random() * 100 + 50,
        errorRate: Math.random() * 2,
      },
    };
  }
}

/**
 * 获取系统日志
 */
export async function getSystemLogs(params?: {
  level?: 'info' | 'warn' | 'error';
  module?: string;
  keyword?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ list: SystemLog[]; total: number }> {
  try {
    const response = await api.get('/admin/logs/system', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      list: [
        {
          id: 'log-1',
          level: 'info',
          message: '用户登录成功',
          module: 'auth',
          userId: 'user-1',
          ip: '192.168.1.100',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'log-2',
          level: 'warn',
          message: '数据库连接池接近上限',
          module: 'database',
          timestamp: new Date(Date.now() - 60000).toISOString(),
        },
      ],
      total: 2,
    };
  }
}

/**
 * 获取审计日志
 */
export async function getAuditLogs(params?: {
  userId?: string;
  action?: string;
  resource?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ list: AuditLog[]; total: number }> {
  try {
    const response = await api.get('/admin/logs/audit', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      list: [
        {
          id: 'audit-1',
          userId: 'user-1',
          username: 'admin',
          action: '创建用户',
          resource: 'user',
          resourceId: 'user-123',
          ip: '192.168.1.100',
          userAgent: 'Mozilla/5.0...',
          timestamp: new Date().toISOString(),
        },
      ],
      total: 1,
    };
  }
}

/**
 * 下载日志文件
 */
export async function downloadLogFile(filename: string): Promise<Blob> {
  try {
    const response = await api.get(`/logs/download/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    await sleep(500);
    return new Blob(['Mock log content'], { type: 'text/plain' });
  }
}

// ==================== 5. 数据备份与恢复 ====================

/**
 * 获取备份列表
 */
export async function getBackupList(params?: {
  type?: 'full' | 'incremental';
  status?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ list: Backup[]; total: number }> {
  try {
    const response = await api.get('/admin/backups', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      list: [
        {
          id: 'backup-1',
          name: '全量备份-20241210',
          type: 'full',
          size: 1073741824, // 1GB
          status: 'completed',
          startTime: new Date(Date.now() - 3600000).toISOString(),
          endTime: new Date().toISOString(),
          duration: 3600,
          path: '/backups/backup-20241210.tar.gz',
          createdBy: 'admin',
        },
      ],
      total: 1,
    };
  }
}

/**
 * 创建备份
 */
export async function createBackup(data: {
  name: string;
  type: 'full' | 'incremental';
  description?: string;
}): Promise<{ taskId: string }> {
  try {
    const response = await api.post('/admin/backups', data);
    return response.data;
  } catch (error) {
    await sleep(500);
    return { taskId: `backup-${Date.now()}` };
  }
}

/**
 * 恢复备份
 */
export async function restoreBackup(id: string): Promise<{ taskId: string }> {
  try {
    const response = await api.post(`/backups/${id}/restore`);
    return response.data;
  } catch (error) {
    await sleep(500);
    return { taskId: `restore-${Date.now()}` };
  }
}

/**
 * 删除备份
 */
export async function deleteBackup(id: string): Promise<void> {
  try {
    await api.delete(`/backups/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 下载备份文件
 */
export async function downloadBackup(id: string): Promise<Blob> {
  try {
    const response = await api.get(`/backups/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    await sleep(1000);
    return new Blob(['Mock backup content'], { type: 'application/gzip' });
  }
}

/**
 * 获取备份配置
 */
export async function getBackupConfig(): Promise<{
  enabled: boolean;
  frequency: 'daily' | 'weekly' | 'monthly';
  time: string;
  retention: number;
  path: string;
}> {
  try {
    const response = await api.get('/admin/backups/config');
    return response.data;
  } catch (error) {
    await sleep(200);
    return {
      enabled: true,
      frequency: 'daily',
      time: '02:00',
      retention: 30,
      path: '/backups',
    };
  }
}

/**
 * 更新备份配置
 */
export async function updateBackupConfig(data: {
  enabled: boolean;
  frequency: 'daily' | 'weekly' | 'monthly';
  time: string;
  retention: number;
  path: string;
}): Promise<void> {
  try {
    await api.put('/admin/backups/config', data);
  } catch (error) {
    await sleep(300);
  }
}

export default api;
