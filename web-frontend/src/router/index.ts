/**
 * 路由配置
 * 论文8个核心功能模块的路由定义
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/store/auth';

const routes: RouteRecordRaw[] = [
  // 登录页
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  
  // 注册页
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', requiresAuth: false }
  },
  
  // 忘记密码页
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPassword.vue'),
    meta: { title: '找回密码', requiresAuth: false }
  },
  
  // 主应用
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      // 仪表板（首页）
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表板', icon: 'Odometer' }
      },
      
      // 1. 数据采集模块
      {
        path: 'collection',
        name: 'Collection',
        component: () => import('@/views/DataCollection.vue'),
        meta: { title: '数据采集', icon: 'Download' }
      },
      
      // 2. 数据预处理模块
      {
        path: 'preprocess',
        name: 'DataPreprocess',
        component: () => import('@/views/DataPreprocessEnhanced.vue'),
        meta: { title: '数据预处理', icon: 'Operation' }
      },
      
      // 3. 情感分析模块
      {
        path: 'sentiment',
        name: 'SentimentAnalysis',
        component: () => import('@/views/SentimentAnalysis.vue'),
        meta: { title: '情感分析', icon: 'DataAnalysis' }
      },
      
      // 4. 双维度排序模块（创新点）
      {
        path: 'dual-dimension',
        name: 'DualDimensionAnalysis',
        component: () => import('@/views/DualDimensionAnalysis.vue'),
        meta: { title: '双维度排序', icon: 'Histogram' }
      },
      
      // 5. 实时舆情监控模块
      {
        path: 'realtime',
        name: 'RealTimeMonitor',
        component: () => import('@/views/RealTimeMonitor.vue'),
        meta: { title: '实时舆情监控', icon: 'Monitor' }
      },
      
      // 6. 数据流水线管理模块
      {
        path: 'pipeline',
        name: 'PipelineManager',
        component: () => import('@/views/PipelineManager.vue'),
        meta: { title: '流水线管理', icon: 'Connection' }
      },
      
      // 7. 可视化展示模块
      {
        path: 'visualization',
        name: 'Visualization',
        component: () => import('@/views/VisualizationDashboard.vue'),
        meta: { title: '可视化展示', icon: 'DataLine' }
      },
      
      // 8. 系统管理模块
      {
        path: 'admin',
        name: 'SystemAdmin',
        component: () => import('@/views/SystemAdmin.vue'),
        meta: { title: '系统管理', icon: 'Setting', requiresAdmin: true }
      },
    ],
  },
  
  // 404页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  
  // 设置页面标题
  document.title = `${to.meta.title || '微博舆情分析系统'}`;
  
  // 不需要认证的页面
  if (to.meta.requiresAuth === false) {
    next();
    return;
  }
  
  // 检查登录状态
  if (!authStore.isAuthenticated) {
    next('/login');
    return;
  }
  
  // 检查管理员权限
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next('/dashboard');
    return;
  }
  
  next();
});

export default router;
