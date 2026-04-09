<template>
  <div class="system-admin">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header -->
    <div class="admin-header">
      <div class="header-left">
        <h1 class="page-title">System Administration</h1>
        <div class="admin-badge">
          <el-tag type="warning" size="large">
            <el-icon><UserFilled /></el-icon>
            Administrator
          </el-tag>
        </div>
      </div>
      
      <div class="header-right">
        <div class="system-status">
          <el-tag :type="systemStatus.type" size="large">
            <el-icon v-if="systemStatus.icon" :class="{ rotating: systemStatus.rotating }">
              <component :is="systemStatus.icon" />
            </el-icon>
            {{ systemStatus.text }}
          </el-tag>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <el-row :gutter="20">
        <!-- Left Column: Configuration -->
        <el-col :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
          <!-- Spark Configuration -->
          <el-card shadow="hover" class="config-card">
            <template #header>
              <div class="card-header">
                <el-icon><Setting /></el-icon>
                <span>Spark Configuration</span>
                <el-button
                  text
                  size="small"
                  @click="resetSparkConfig"
                  :aria-label="'Reset Spark configuration to defaults'"
                >
                  <el-icon><RefreshRight /></el-icon>
                  Reset
                </el-button>
              </div>
            </template>
            
            <el-form
              :model="sparkConfig"
              :rules="sparkRules"
              ref="sparkFormRef"
              label-position="top"
            >
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Executor Memory" prop="executor_memory">
                    <el-input
                      v-model="sparkConfig.executor_memory"
                      placeholder="e.g., 2g"
                      suffix-icon="MemoryCard"
                    />
                    <div class="form-help">Memory per executor (e.g., 2g, 4g)</div>
                  </el-form-item>
                </el-col>
                
                <el-col :span="12">
                  <el-form-item label="Executor Cores" prop="executor_cores">
                    <el-input-number
                      v-model="sparkConfig.executor_cores"
                      :min="1"
                      :max="8"
                      style="width: 100%"
                    />
                    <div class="form-help">CPU cores per executor</div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Driver Memory" prop="driver_memory">
                    <el-input
                      v-model="sparkConfig.driver_memory"
                      placeholder="e.g., 1g"
                      suffix-icon="MemoryCard"
                    />
                    <div class="form-help">Memory for Spark driver</div>
                  </el-form-item>
                </el-col>
                
                <el-col :span="12">
                  <el-form-item label="Parallelism" prop="parallelism">
                    <el-input-number
                      v-model="sparkConfig.parallelism"
                      :min="1"
                      :max="1000"
                      style="width: 100%"
                    />
                    <div class="form-help">Default parallelism for jobs</div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-form-item>
                <el-button
                  type="primary"
                  @click="saveSparkConfig"
                  :loading="isSavingSpark"
                  :aria-label="'Save Spark configuration'"
                >
                  <el-icon><Check /></el-icon>
                  Save Configuration
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
          
          <!-- Database Configuration -->
          <el-card shadow="hover" class="config-card">
            <DatabaseConnectionConfig />
          </el-card>
        </el-col>
        
        <!-- Right Column: Management -->
        <el-col :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
          <!-- Collection Task Management -->
          <el-card shadow="hover" class="management-card">
            <template #header>
              <div class="card-header">
                <el-icon><Management /></el-icon>
                <span>Collection Task Management</span>
                <el-button
                  text
                  size="small"
                  @click="refreshTasks"
                  :loading="isRefreshingTasks"
                  :aria-label="'Refresh task list'"
                >
                  <el-icon><Refresh /></el-icon>
                  Refresh
                </el-button>
              </div>
            </template>
            
            <el-table
              :data="collectionTasks"
              height="300"
              size="small"
              :aria-label="'Collection tasks table'"
            >
              <el-table-column prop="name" label="Task Name" min-width="150" />
              
              <el-table-column prop="keywords" label="Keywords" min-width="200">
                <template #default="{ row }">
                  <div class="keyword-tags">
                    <el-tag
                      v-for="keyword in row.keywords.slice(0, 3)"
                      :key="keyword"
                      size="small"
                      class="keyword-tag"
                    >
                      {{ keyword }}
                    </el-tag>
                    <span v-if="row.keywords.length > 3" class="more-keywords">
                      +{{ row.keywords.length - 3 }}
                    </span>
                  </div>
                </template>
              </el-table-column>
              
              <el-table-column prop="status" label="Status" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="getTaskStatusType(row.status)"
                    size="small"
                  >
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <el-table-column prop="created_at" label="Created" width="120">
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
              
              <el-table-column label="Actions" width="150">
                <template #default="{ row }">
                  <el-button
                    text
                    size="small"
                    @click="viewTaskLogs(row)"
                    :aria-label="`View logs for task ${row.name}`"
                  >
                    <el-icon><Document /></el-icon>
                    Logs
                  </el-button>
                  <el-button
                    text
                    size="small"
                    type="danger"
                    @click="deleteTask(row)"
                    :disabled="row.status === 'running'"
                    :aria-label="`Delete task ${row.name}`"
                  >
                    <el-icon><Delete /></el-icon>
                    Delete
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
          
          <!-- System Logs -->
          <el-card shadow="hover" class="logs-card">
            <SystemLogViewer />
          </el-card>
        </el-col>
      </el-row>
      
      <!-- User Management Section -->
      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="24">
          <el-card shadow="hover" class="user-management-card">
            <template #header>
              <div class="card-header">
                <el-icon><User /></el-icon>
                <span>User Management</span>
                <el-button
                  type="primary"
                  size="small"
                  @click="showAddUserDialog"
                  :aria-label="'Add new user'"
                >
                  <el-icon><Plus /></el-icon>
                  Add User
                </el-button>
              </div>
            </template>
            
            <el-table
              :data="users"
              size="small"
              :aria-label="'Users management table'"
            >
              <el-table-column prop="username" label="Username" />
              <el-table-column prop="email" label="Email" />
              <el-table-column prop="role" label="Role" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
                    {{ row.role }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="Status" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="last_login" label="Last Login" width="150">
                <template #default="{ row }">
                  {{ formatDateTime(row.last_login) }}
                </template>
              </el-table-column>
              <el-table-column label="Actions" width="200">
                <template #default="{ row }">
                  <el-button
                    text
                    size="small"
                    @click="resetUserPassword(row)"
                    :aria-label="`Reset password for ${row.username}`"
                  >
                    <el-icon><Key /></el-icon>
                    Reset Password
                  </el-button>
                  <el-button
                    text
                    size="small"
                    :type="row.status === 'active' ? 'warning' : 'success'"
                    @click="toggleUserStatus(row)"
                    :disabled="row.username === 'admin'"
                    :aria-label="`${row.status === 'active' ? 'Disable' : 'Enable'} user ${row.username}`"
                  >
                    <el-icon><Switch /></el-icon>
                    {{ row.status === 'active' ? 'Disable' : 'Enable' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- Footer with Version -->
    <div class="admin-footer">
      <div class="version-info">
        <span class="version-label">System Version:</span>
        <span class="version-number">{{ systemVersion }}</span>
      </div>
      <div class="footer-links">
        <el-button text size="small" @click="showSystemInfo">System Info</el-button>
        <el-button text size="small" @click="showAbout">About</el-button>
      </div>
    </div>
    
    <!-- Password Confirmation Dialog -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="Administrator Password Required"
      width="400px"
      :close-on-click-modal="false"
      :aria-label="'Administrator password confirmation dialog'"
    >
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef">
        <el-form-item label="Please enter administrator password" prop="password">
          <el-input
            v-model="passwordForm.password"
            type="password"
            placeholder="Enter password"
            show-password
            :aria-label="'Administrator password input'"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="confirmPassword" :loading="isConfirmingPassword">
            Confirm
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- Add User Dialog -->
    <el-dialog
      v-model="addUserDialogVisible"
      title="Add New User"
      width="500px"
      :aria-label="'Add new user dialog'"
    >
      <el-form :model="newUser" :rules="userRules" ref="newUserFormRef">
        <el-form-item label="Username" prop="username">
          <el-input v-model="newUser.username" placeholder="Enter username" />
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="newUser.email" placeholder="Enter email" />
        </el-form-item>
        <el-form-item label="Role" prop="role">
          <el-select v-model="newUser.role" placeholder="Select role" style="width: 100%">
            <el-option label="User" value="user" />
            <el-option label="Admin" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="newUser.password" type="password" placeholder="Enter password" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="addUserDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="addUser" :loading="isAddingUser">
            Add User
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting, Management, User, UserFilled, Check, RefreshRight, Refresh,
  Document, Delete, Plus, Key, Switch, MemoryCard
} from '@element-plus/icons-vue'
import DatabaseConnectionConfig from '@/components/common/DatabaseConnectionConfig.vue'
import SystemLogViewer from '@/components/common/SystemLogViewer.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface SparkConfig {
  executor_memory: string
  executor_cores: number
  driver_memory: string
  parallelism: number
}

interface CollectionTask {
  id: string
  name: string
  keywords: string[]
  status: 'running' | 'completed' | 'failed' | 'paused'
  created_at: Date
}

interface User {
  id: string
  username: string
  email: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  last_login: Date
}

// Reactive data
const sparkFormRef = ref()
const passwordFormRef = ref()
const newUserFormRef = ref()
const isSavingSpark = ref(false)
const isRefreshingTasks = ref(false)
const isConfirmingPassword = ref(false)
const isAddingUser = ref(false)
const passwordDialogVisible = ref(false)
const addUserDialogVisible = ref(false)
const pendingAction = ref<(() => void) | null>(null)

// Spark configuration
const sparkConfig = ref<SparkConfig>({
  executor_memory: '2g',
  executor_cores: 2,
  driver_memory: '1g',
  parallelism: 100
})

// Password form
const passwordForm = ref({
  password: ''
})

// New user form
const newUser = ref({
  username: '',
  email: '',
  role: 'user',
  password: ''
})

// Data
const collectionTasks = ref<CollectionTask[]>([])
const users = ref<User[]>([])
const systemVersion = ref('1.0.0')

// Computed properties
const systemStatus = computed(() => {
  const runningTasks = collectionTasks.value.filter(task => task.status === 'running').length
  if (runningTasks > 0) {
    return {
      type: 'warning' as const,
      text: `${runningTasks} tasks running`,
      icon: 'Loading',
      rotating: true
    }
  }
  return {
    type: 'success' as const,
    text: 'System normal',
    icon: 'CircleCheck',
    rotating: false
  }
})

// Validation rules
const sparkRules = {
  executor_memory: [
    { required: true, message: 'Please enter executor memory', trigger: 'blur' },
    { pattern: /^\d+[gmGM]$/, message: 'Invalid format (e.g., 2g, 4g)', trigger: 'blur' }
  ],
  executor_cores: [
    { required: true, message: 'Please enter executor cores', trigger: 'blur' },
    { type: 'number', min: 1, max: 8, message: 'Cores must be between 1 and 8', trigger: 'blur' }
  ],
  driver_memory: [
    { required: true, message: 'Please enter driver memory', trigger: 'blur' },
    { pattern: /^\d+[gmGM]$/, message: 'Invalid format (e.g., 1g, 2g)', trigger: 'blur' }
  ],
  parallelism: [
    { required: true, message: 'Please enter parallelism', trigger: 'blur' },
    { type: 'number', min: 1, max: 1000, message: 'Parallelism must be between 1 and 1000', trigger: 'blur' }
  ]
}

const passwordRules = {
  password: [
    { required: true, message: 'Please enter administrator password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ]
}

const userRules = {
  username: [
    { required: true, message: 'Please enter username', trigger: 'blur' },
    { min: 3, max: 20, message: 'Username must be 3-20 characters', trigger: 'blur' }
  ],
  email: [
    { required: true, message: 'Please enter email', trigger: 'blur' },
    { type: 'email', message: 'Please enter valid email', trigger: 'blur' }
  ],
  role: [
    { required: true, message: 'Please select role', trigger: 'change' }
  ],
  password: [
    { required: true, message: 'Please enter password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ]
}

// Methods
const formatDate = (date: Date) => {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric'
  })
}

const formatDateTime = (date: Date) => {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getTaskStatusType = (status: string) => {
  const typeMap = {
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'paused': 'info'
  }
  return typeMap[status as keyof typeof typeMap] || 'info'
}

// Spark configuration methods
const saveSparkConfig = async () => {
  try {
    await sparkFormRef.value.validate()
    
    // Show password confirmation
    pendingAction.value = async () => {
      isSavingSpark.value = true
      
      try {
        await withErrorHandling(
          async () => {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000))
            
            ElMessage.success('Spark configuration saved successfully')
          },
          'Save Spark Configuration',
          { showLoading: false }
        )
      } finally {
        isSavingSpark.value = false
        pendingAction.value = null
      }
    }
    
    passwordDialogVisible.value = true
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

const resetSparkConfig = () => {
  sparkConfig.value = {
    executor_memory: '2g',
    executor_cores: 2,
    driver_memory: '1g',
    parallelism: 100
  }
  ElMessage.info('Spark configuration reset to defaults')
}

// Collection task methods
const refreshTasks = async () => {
  isRefreshingTasks.value = true
  
  try {
    await withErrorHandling(
      async () => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // Generate mock tasks
        collectionTasks.value = [
          {
            id: 'task_1',
            name: 'AI Technology Monitoring',
            keywords: ['AI', 'Machine Learning', 'Deep Learning'],
            status: 'running',
            created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
          },
          {
            id: 'task_2',
            name: 'Financial News Collection',
            keywords: ['Finance', 'Stock', 'Investment'],
            status: 'completed',
            created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000)
          },
          {
            id: 'task_3',
            name: 'Entertainment Trends',
            keywords: ['Movie', 'Music', 'Celebrity'],
            status: 'failed',
            created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
          }
        ]
        
        ElMessage.success('Tasks refreshed successfully')
      },
      'Refresh Tasks',
      { showLoading: false }
    )
  } finally {
    isRefreshingTasks.value = false
  }
}

const viewTaskLogs = (task: CollectionTask) => {
  ElMessage.info(`Viewing logs for task: ${task.name}`)
  // Implement log viewing logic
}

const deleteTask = async (task: CollectionTask) => {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete task "${task.name}"? This action cannot be undone and will remove all associated data and logs.`,
      'Delete Task',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
        dangerouslyUseHTMLString: true
      }
    )
    
    // Show password confirmation for sensitive operation
    pendingAction.value = async () => {
      const index = collectionTasks.value.findIndex(t => t.id === task.id)
      if (index > -1) {
        collectionTasks.value.splice(index, 1)
        ElMessage.success(`Task "${task.name}" deleted successfully`)
      }
      pendingAction.value = null
    }
    
    passwordDialogVisible.value = true
  } catch {
    // User cancelled
  }
}

// User management methods
const showAddUserDialog = () => {
  newUser.value = {
    username: '',
    email: '',
    role: 'user',
    password: ''
  }
  addUserDialogVisible.value = true
}

const addUser = async () => {
  try {
    await newUserFormRef.value.validate()
    
    isAddingUser.value = true
    
    try {
      await withErrorHandling(
        async () => {
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 1000))
          
          const newUserData: User = {
            id: `user_${Date.now()}`,
            username: newUser.value.username,
            email: newUser.value.email,
            role: newUser.value.role as 'user' | 'admin',
            status: 'active',
            last_login: new Date()
          }
          
          users.value.push(newUserData)
          
          ElMessage.success(`User "${newUser.value.username}" added successfully`)
          addUserDialogVisible.value = false
        },
        'Add User',
        { showLoading: false }
      )
    } finally {
      isAddingUser.value = false
    }
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

const resetUserPassword = async (user: User) => {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to reset password for user "${user.username}"? The user will receive a temporary password via email.`,
      'Reset Password',
      {
        confirmButtonText: 'Reset',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    // Show password confirmation for sensitive operation
    pendingAction.value = async () => {
      ElMessage.success(`Password reset for user "${user.username}"`)
      pendingAction.value = null
    }
    
    passwordDialogVisible.value = true
  } catch {
    // User cancelled
  }
}

const toggleUserStatus = async (user: User) => {
  const action = user.status === 'active' ? 'disable' : 'enable'
  
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to ${action} user "${user.username}"? ${action === 'disable' ? 'The user will not be able to access the system.' : 'The user will regain access to the system.'}`,
      `${action.charAt(0).toUpperCase() + action.slice(1)} User`,
      {
        confirmButtonText: action.charAt(0).toUpperCase() + action.slice(1),
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    // Show password confirmation for sensitive operation
    pendingAction.value = async () => {
      user.status = user.status === 'active' ? 'disabled' : 'active'
      ElMessage.success(`User "${user.username}" ${action}d successfully`)
      pendingAction.value = null
    }
    
    passwordDialogVisible.value = true
  } catch {
    // User cancelled
  }
}

// Password confirmation
const confirmPassword = async () => {
  try {
    await passwordFormRef.value.validate()
    
    isConfirmingPassword.value = true
    
    try {
      await withErrorHandling(
        async () => {
          // Simulate password verification
          await new Promise(resolve => setTimeout(resolve, 500))
          
          // Simple mock verification (in real app, this would be server-side)
          if (passwordForm.value.password === 'admin123') {
            if (pendingAction.value) {
              await pendingAction.value()
            }
            passwordDialogVisible.value = false
            passwordForm.value.password = ''
          } else {
            ElMessage.error('Invalid administrator password')
          }
        },
        'Password Confirmation',
        { showLoading: false }
      )
    } finally {
      isConfirmingPassword.value = false
    }
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

// System info methods
const showSystemInfo = () => {
  ElMessage.info('System information dialog would open here')
}

const showAbout = () => {
  ElMessage.info('About dialog would open here')
}

// Lifecycle
onMounted(async () => {
  // Load initial data
  await refreshTasks()
  
  // Load users
  users.value = [
    {
      id: 'user_1',
      username: 'admin',
      email: 'admin@example.com',
      role: 'admin',
      status: 'active',
      last_login: new Date()
    },
    {
      id: 'user_2',
      username: 'operator',
      email: 'operator@example.com',
      role: 'user',
      status: 'active',
      last_login: new Date(Date.now() - 2 * 60 * 60 * 1000)
    }
  ]
  
  // Load system version (in real app, this would come from package.json)
  systemVersion.value = '1.0.0'
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})
</script>

<style scoped>
.system-admin {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-extra-large);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.admin-badge {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.system-status {
  display: flex;
  align-items: center;
}

.main-content {
  flex: 1;
  margin-bottom: var(--spacing-lg);
}

.config-card,
.management-card,
.logs-card,
.user-management-card {
  margin-bottom: var(--spacing-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-semibold);
}

.form-help {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.keyword-tag {
  font-size: var(--font-size-tiny);
}

.more-keywords {
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.admin-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-base);
  margin-top: auto;
}

.version-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.version-label {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

.version-number {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: 'Courier New', monospace;
}

.footer-links {
  display: flex;
  gap: var(--spacing-sm);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

/* Animations */
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.rotating {
  animation: rotate 2s linear infinite;
}

/* Responsive */
@media (max-width: 1280px) {
  .admin-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .admin-footer {
    flex-direction: column;
    gap: var(--spacing-md);
    align-items: stretch;
  }
}

@media (max-width: 768px) {
  .system-admin {
    padding: var(--spacing-md);
  }
  
  .admin-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }
  
  .keyword-tags {
    justify-content: center;
  }
  
  .footer-links {
    justify-content: center;
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .config-card,
  .management-card,
  .logs-card,
  .user-management-card {
    border-width: 2px;
  }
}
</style>
