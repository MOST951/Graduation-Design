<template>
  <div class="main-layout">
    <!-- ========== 侧边栏 ========== -->
    <aside class="sidebar" :class="{ collapsed: isCollapse }">
      <!-- Logo -->
      <div class="sidebar-logo" @click="router.push('/dashboard')">
        <div class="logo-icon">
          <el-icon :size="20"><TrendCharts /></el-icon>
        </div>
        <transition name="logo-text">
          <span v-show="!isCollapse" class="logo-text">舆情分析</span>
        </transition>
      </div>

      <!-- 导航分组标签 -->
      <div v-show="!isCollapse" class="nav-section">数据处理</div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :router="true"
        :collapse-transition="false"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表板</template>
        </el-menu-item>
        
        <el-menu-item index="/collection">
          <el-icon><Download /></el-icon>
          <template #title>数据采集</template>
        </el-menu-item>
        
        <el-menu-item index="/preprocess">
          <el-icon><Operation /></el-icon>
          <template #title>数据预处理</template>
        </el-menu-item>
        
        <el-menu-item index="/sentiment">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>情感分析</template>
        </el-menu-item>
        
        <el-menu-item index="/tri-dimension">
          <el-icon><Histogram /></el-icon>
          <template #title>三维度排序</template>
        </el-menu-item>

        <template v-if="!isCollapse">
          <div class="nav-section">监控与展示</div>
        </template>
        
        <el-menu-item index="/realtime">
          <el-icon><Monitor /></el-icon>
          <template #title>实时舆情监控</template>
        </el-menu-item>
        
        <el-menu-item index="/pipeline">
          <el-icon><Connection /></el-icon>
          <template #title>流水线管理</template>
        </el-menu-item>
        
        <el-menu-item index="/visualization">
          <el-icon><DataLine /></el-icon>
          <template #title>可视化展示</template>
        </el-menu-item>

        <template v-if="!isCollapse">
          <div class="nav-section">系统</div>
        </template>
        
        <el-menu-item index="/admin">
          <el-icon><Setting /></el-icon>
          <template #title>系统管理</template>
        </el-menu-item>
      </el-menu>

      <!-- 侧边栏底部折叠按钮 -->
      <div class="sidebar-footer">
        <div class="collapse-btn" @click="toggleCollapse">
          <el-icon :size="16">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span v-show="!isCollapse">收起菜单</span>
        </div>
      </div>
    </aside>

    <!-- ========== 主内容区 ========== -->
    <div class="main-container" :class="{ 'sidebar-collapsed': isCollapse }">
      <!-- 顶部导航栏 -->
      <header class="header">
        <div class="header-left">
          <div class="page-title-area">
            <h2 class="page-title">{{ currentTitle }}</h2>
            <el-breadcrumb separator="/" class="breadcrumb">
              <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
        
        <div class="header-right">
          <!-- 通知中心 -->
          <el-popover
            placement="bottom-end"
            :width="400"
            trigger="click"
            popper-class="notification-popover"
          >
            <template #reference>
              <div class="header-icon-btn">
                <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="9">
                  <el-icon :size="18" :class="{ 'bell-ring': unreadCount > 0 }">
                    <Bell />
                  </el-icon>
                </el-badge>
              </div>
            </template>
            
            <div class="notification-panel">
              <div class="notification-header">
                <span class="title">通知中心</span>
                <el-button v-if="unreadCount > 0" type="primary" link size="small" @click="markAllRead">
                  全部已读
                </el-button>
              </div>
              
              <el-tabs v-model="notificationTab" class="notification-tabs">
                <el-tab-pane label="预警" name="alert">
                  <div v-if="alertNotifications.length > 0" class="notification-list">
                    <div 
                      v-for="item in alertNotifications" 
                      :key="item.id" 
                      class="notification-item"
                      :class="{ unread: !item.read, [item.level]: true }"
                      @click="handleNotificationClick(item)"
                    >
                      <div class="notification-dot" :class="item.level"></div>
                      <div class="notification-content">
                        <div class="notification-title">{{ item.title }}</div>
                        <div class="notification-desc">{{ item.description }}</div>
                        <div class="notification-time">{{ item.time }}</div>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="暂无预警通知" :image-size="48" />
                </el-tab-pane>
                
                <el-tab-pane label="系统" name="system">
                  <div v-if="systemNotifications.length > 0" class="notification-list">
                    <div 
                      v-for="item in systemNotifications" 
                      :key="item.id" 
                      class="notification-item"
                      :class="{ unread: !item.read }"
                      @click="handleNotificationClick(item)"
                    >
                      <div class="notification-dot info"></div>
                      <div class="notification-content">
                        <div class="notification-title">{{ item.title }}</div>
                        <div class="notification-desc">{{ item.description }}</div>
                        <div class="notification-time">{{ item.time }}</div>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="暂无系统通知" :image-size="48" />
                </el-tab-pane>
                
                <el-tab-pane label="任务" name="task">
                  <div v-if="taskNotifications.length > 0" class="notification-list">
                    <div 
                      v-for="item in taskNotifications" 
                      :key="item.id" 
                      class="notification-item"
                      :class="{ unread: !item.read }"
                      @click="handleNotificationClick(item)"
                    >
                      <div class="notification-dot" :class="item.status === 'success' ? 'success' : item.status === 'error' ? 'critical' : 'info'"></div>
                      <div class="notification-content">
                        <div class="notification-title">{{ item.title }}</div>
                        <div class="notification-desc">{{ item.description }}</div>
                        <div class="notification-time">{{ item.time }}</div>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="暂无任务通知" :image-size="48" />
                </el-tab-pane>
              </el-tabs>
              
              <div class="notification-footer">
                <el-button type="primary" link @click="goToAlertCenter">
                  查看全部通知
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </el-popover>
          
          <!-- 快捷操作 -->
          <el-dropdown trigger="click" class="quick-actions">
            <div class="header-icon-btn">
              <el-icon :size="18"><Operation /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="quickStartCrawl">
                  <el-icon><Download /></el-icon>
                  快速采集
                </el-dropdown-item>
                <el-dropdown-item @click="quickAnalyze">
                  <el-icon><DataAnalysis /></el-icon>
                  快速分析
                </el-dropdown-item>
                <el-dropdown-item @click="quickExport">
                  <el-icon><Document /></el-icon>
                  导出报告
                </el-dropdown-item>
                <el-dropdown-item divided @click="goToSettings">
                  <el-icon><Setting /></el-icon>
                  系统设置
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <!-- 分隔线 -->
          <div class="header-divider"></div>

          <!-- 用户 -->
          <el-dropdown class="user-dropdown">
            <div class="user-info">
              <el-avatar :size="30" class="user-avatar">
                <el-icon :size="16"><User /></el-icon>
              </el-avatar>
              <div class="user-meta">
                <span class="username">{{ displayName }}</span>
                <span class="user-role">{{ displayRoleEn }}</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item>
                  <el-icon><Setting /></el-icon>
                  系统设置
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      
      <!-- 主内容 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  Odometer, Download, DataAnalysis, ChatDotRound, DataLine,
  Document, Setting, Operation, User, Grid, Fold, Expand,
  Bell, SwitchButton, Monitor, Histogram, PieChart, Connection,
  WarningFilled, Warning, InfoFilled, SuccessFilled, CircleCloseFilled, Loading, ArrowRight,
  TrendCharts,
} from '@element-plus/icons-vue';
import apiClient from '@/api/index';
import { useAuthStore } from '@/store/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const displayName = computed(() => {
  if (authStore.user) {
    return authStore.user.name || authStore.user.username;
  }
  return localStorage.getItem('username') || '用户';
});

const displayRole = computed(() => {
  const role = authStore.user?.role || localStorage.getItem('userRole') || 'user';
  return role === 'admin' ? '管理员' : '普通用户';
});

const displayRoleEn = computed(() => {
  const role = authStore.user?.role || localStorage.getItem('userRole') || 'user';
  return role === 'admin' ? 'Admin' : 'User';
});

const isCollapse = ref(false);
const notificationTab = ref('alert');

// 通知数据
interface Notification {
  id: string;
  title: string;
  description: string;
  time: string;
  read: boolean;
  type: 'alert' | 'system' | 'task';
  level?: 'critical' | 'warning' | 'info';
  status?: 'success' | 'error' | 'running';
  link?: string;
}

const notifications = ref<Notification[]>([
  {
    id: '1',
    title: '负面情感预警',
    description: '检测到负面情感占比超过40%阈值',
    time: '5分钟前',
    read: false,
    type: 'alert',
    level: 'critical',
    link: '/realtime',
  },
  {
    id: '2',
    title: '敏感关键词预警',
    description: '检测到敏感关键词「投诉」出现3次',
    time: '10分钟前',
    read: false,
    type: 'alert',
    level: 'warning',
    link: '/realtime',
  },
  {
    id: '3',
    title: '数据采集完成',
    description: '关键词「人工智能」采集完成，共510条',
    time: '30分钟前',
    read: true,
    type: 'task',
    status: 'success',
    link: '/collection',
  },
  {
    id: '4',
    title: '系统更新',
    description: '情感分析模型已更新至最新版本',
    time: '1小时前',
    read: true,
    type: 'system',
  },
]);

// 计算属性
const alertNotifications = computed(() => notifications.value.filter(n => n.type === 'alert'));
const systemNotifications = computed(() => notifications.value.filter(n => n.type === 'system'));
const taskNotifications = computed(() => notifications.value.filter(n => n.type === 'task'));
const unreadCount = computed(() => notifications.value.filter(n => !n.read).length);

const activeMenu = computed(() => route.path);

const currentTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': '仪表板',
    '/collection': '数据采集',
    '/preprocess': '数据预处理',
    '/sentiment': '情感分析',
    '/tri-dimension': '三维度分析',
    '/topics': '热点话题分析',
    '/behavior': '用户行为分析',
    '/realtime': '实时舆情监控',
    '/visualization': '数据可视化',
    '/advanced-visualization': '高级可视化',
    '/reports': '报告生成',
    '/admin': '系统管理',
    '/extensions': '扩展功能',
  };
  return titles[route.path] || '首页';
});

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value;
};

const handleLogout = () => {
  authStore.logout();
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('username');
  localStorage.removeItem('userRole');
  localStorage.removeItem('accessToken');
  localStorage.removeItem('userEmail');
  router.push('/login');
};

// 通知相关方法
const markAllRead = () => {
  notifications.value.forEach(n => n.read = true);
  ElMessage.success('已全部标记为已读');
};

const handleNotificationClick = (item: Notification) => {
  item.read = true;
  if (item.link) {
    router.push(item.link);
  }
};

const goToAlertCenter = () => {
  router.push('/realtime');
};

// 快捷操作
const quickStartCrawl = () => {
  router.push('/collection');
  ElMessage.info('正在跳转到数据采集页面...');
};

const quickAnalyze = () => {
  router.push('/sentiment');
  ElMessage.info('正在跳转到情感分析页面...');
};

const quickExport = () => {
  router.push('/reports');
  ElMessage.info('正在跳转到报告生成页面...');
};

const goToSettings = () => {
  router.push('/admin');
};

// 定时检查预警
let alertCheckInterval: number | null = null;

const checkAlerts = async () => {
  try {
    const response = await apiClient.get('/dashboard/sentiment-distribution');
    if (response.data.code === 200) {
      const data = response.data.data;
      const total = data.positive + data.neutral + data.negative;
      if (total > 0) {
        const negativeRatio = (data.negative / total) * 100;
        if (negativeRatio > 40) {
          // 添加新预警通知
          const existingAlert = notifications.value.find(n => n.title === '负面情感预警' && !n.read);
          if (!existingAlert) {
            notifications.value.unshift({
              id: `alert_${Date.now()}`,
              title: '负面情感预警',
              description: `当前负面情感占比 ${negativeRatio.toFixed(1)}%，超过40%阈值`,
              time: '刚刚',
              read: false,
              type: 'alert',
              level: negativeRatio > 60 ? 'critical' : 'warning',
              link: '/realtime',
            });
          }
        }
      }
    }
  } catch (error) {
    // 静默处理错误
  }
};

onMounted(() => {
  // 启动预警检查（每60秒检查一次）
  checkAlerts();
  alertCheckInterval = window.setInterval(checkAlerts, 60000);
});

onUnmounted(() => {
  if (alertCheckInterval) {
    clearInterval(alertCheckInterval);
  }
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

// ============================================================
//  Layout v2 — Modern Sidebar + Header
// ============================================================

.main-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

// ==================== 侧边栏 ====================
.sidebar {
  width: $sidebar-width;
  min-width: $sidebar-width;
  height: 100vh;
  background: $sidebar-bg;
  display: flex;
  flex-direction: column;
  transition: width 0.3s $ease-smooth, min-width 0.3s $ease-smooth;
  overflow: hidden;
  z-index: 100;

  &.collapsed {
    width: $sidebar-width-collapsed;
    min-width: $sidebar-width-collapsed;

    .sidebar-logo { justify-content: center; padding: 0; }
    .nav-section { display: none; }
  }
}

.sidebar-logo {
  height: $header-height;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  cursor: pointer;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .logo-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, $primary-color, #6C5CE7);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    flex-shrink: 0;
  }

  .logo-text {
    font-size: 16px;
    font-weight: $font-weight-bold;
    color: #fff;
    white-space: nowrap;
    letter-spacing: 0.5px;
  }
}

.logo-text-enter-active,
.logo-text-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.logo-text-enter-from,
.logo-text-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

.nav-section {
  padding: 20px 20px 6px;
  font-size: 11px;
  font-weight: $font-weight-semibold;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  user-select: none;
}

.sidebar-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 8px;

  &::-webkit-scrollbar { width: 0; }

  :deep(.el-menu-item) {
    height: 40px;
    line-height: 40px;
    margin: 2px 0;
    border-radius: 8px;
    color: $sidebar-text;
    font-size: 13px;
    font-weight: $font-weight-medium;
    transition: all 0.2s $ease-smooth;

    .el-icon {
      font-size: 18px;
      width: 18px;
    }

    &:hover {
      background: $sidebar-bg-hover;
      color: $sidebar-text-active;
    }

    &.is-active {
      background: $sidebar-bg-active;
      color: $sidebar-text-active;

      .el-icon { color: $primary-light; }
    }
  }

  // 折叠态居中
  :deep(.el-menu--collapse .el-menu-item) {
    padding: 0 !important;
    justify-content: center;
  }
}

.sidebar-footer {
  flex-shrink: 0;
  padding: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  color: $sidebar-text;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;

  &:hover {
    background: $sidebar-bg-hover;
    color: $sidebar-text-active;
  }
}

// ==================== 主容器 ====================
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: $bg-page;
  transition: margin-left 0.3s $ease-smooth;
}

// ==================== 头部 ====================
.header {
  height: $header-height;
  min-height: $header-height;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.page-title-area {
  .page-title {
    font-size: 16px;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: 0;
    line-height: 1.3;
  }

  .breadcrumb {
    margin-top: 2px;

    :deep(.el-breadcrumb__inner) {
      font-size: 12px;
      color: $text-secondary;
    }
    :deep(.el-breadcrumb__separator) {
      font-size: 12px;
      color: $text-placeholder;
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  color: $text-regular;
  transition: all 0.2s $ease-smooth;

  &:hover {
    background: $bg-hover;
    color: $primary-color;
  }
}

.bell-ring {
  animation: bellRing 2s ease-in-out infinite;
  color: $primary-color;
}

@keyframes bellRing {
  0%, 80%, 100% { transform: rotate(0); }
  85% { transform: rotate(8deg); }
  90% { transform: rotate(-8deg); }
  95% { transform: rotate(4deg); }
}

.header-divider {
  width: 1px;
  height: 24px;
  background: $border-light;
  margin: 0 8px;
}

.user-dropdown {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;

  &:hover {
    background: $bg-hover;
  }
}

.user-avatar {
  background: linear-gradient(135deg, $primary-color, #6C5CE7);
  color: #fff;
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;

  .username {
    font-size: 13px;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  .user-role {
    font-size: 11px;
    color: $text-secondary;
  }
}

// ==================== 通知面板 ====================
.notification-panel {
  .notification-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 12px;
    border-bottom: 1px solid $border-light;
    margin-bottom: 8px;

    .title {
      font-size: 15px;
      font-weight: $font-weight-semibold;
      color: $text-primary;
    }
  }

  .notification-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 8px;
    }
  }

  .notification-list {
    max-height: 340px;
    overflow-y: auto;
  }

  .notification-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 12px;
    margin-bottom: 4px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
    background: $bg-hover;

    &:hover { background: $primary-bg; }

    &.unread {
      background: $bg-white;
      box-shadow: $shadow-xs;

      .notification-title { font-weight: $font-weight-semibold; }
    }
  }

  .notification-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
    background: $info-color;

    &.critical { background: $danger-color; }
    &.warning  { background: $warning-color; }
    &.success  { background: $success-color; }
    &.info     { background: $primary-color; }
  }

  .notification-content {
    flex: 1;
    min-width: 0;

    .notification-title {
      font-size: 13px;
      color: $text-primary;
      margin-bottom: 2px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .notification-desc {
      font-size: 12px;
      color: $text-secondary;
      margin-bottom: 4px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .notification-time {
      font-size: 11px;
      color: $text-placeholder;
    }
  }

  .notification-footer {
    padding-top: 10px;
    border-top: 1px solid $border-light;
    text-align: center;
  }
}

// ==================== 主内容 ====================
.main-content {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  overflow-x: hidden;
}

// ==================== 页面过渡 ====================
.page-fade-enter-active {
  transition: opacity 0.25s $ease-smooth, transform 0.25s $ease-smooth;
}
.page-fade-leave-active {
  transition: opacity 0.15s $ease-smooth;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
}
</style>
