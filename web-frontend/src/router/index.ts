/**
 * 路由配置
 * 论文8个核心功能模块的路由定义
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { defineAsyncComponent } from 'vue';
import { useAuthStore } from '@/store/auth';

// ====================  ====================

// 
const Login = defineAsyncComponent(() => import('@/views/Login.vue'));
const Register = defineAsyncComponent(() => import('@/views/Register.vue'));
const MainLayout = defineAsyncComponent(() => import('@/layouts/MainLayout.vue'));

// 
const Dashboard = defineAsyncComponent(() => import('@/views/Dashboard.vue'));
const DataCollection = defineAsyncComponent(() => import('@/views/DataCollection.vue'));
const DataPreprocessEnhanced = defineAsyncComponent(() => import('@/views/DataPreprocessEnhanced.vue'));
const SentimentAnalysis = defineAsyncComponent(() => import('@/views/SentimentAnalysis.vue'));
const TriDimensionAnalysis = defineAsyncComponent(() => import('@/views/TriDimensionAnalysis.vue'));
const RealTimeMonitor = defineAsyncComponent(() => import('@/views/RealTimeMonitor.vue'));
const PipelineManager = defineAsyncComponent(() => import('@/views/PipelineManager.vue'));
const VisualizationDashboard = defineAsyncComponent(() => import('@/views/VisualizationDashboard.vue'));
const SystemAdmin = defineAsyncComponent(() => import('@/views/SystemAdmin.vue'));

// 
const NotFound = defineAsyncComponent(() => import('@/pages/NotFound.vue'));

const routes: RouteRecordRaw[] = [
  // 
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: 'login', requiresAuth: false }
  },
  
  // 
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { title: 'register', requiresAuth: false }
  },
  
  // 
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      // 
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: 'dashboard', icon: 'Odometer', keepAlive: true }
      },
      
      // 1. 
      {
        path: 'collection',
        name: 'Collection',
        component: DataCollection,
        meta: { title: 'data collection', icon: 'Download', keepAlive: true }
      },
      
      // 2. 
      {
        path: 'preprocess',
        name: 'DataPreprocess',
        component: DataPreprocessEnhanced,
        meta: { title: 'data preprocessing', icon: 'Operation', keepAlive: true }
      },
      
      // 3. 
      {
        path: 'sentiment',
        name: 'SentimentAnalysis',
        component: SentimentAnalysis,
        meta: { title: 'sentiment analysis', icon: 'DataAnalysis', keepAlive: true }
      },
      
      // 4. 
      {
        path: 'tri-dimension',
        name: 'TriDimensionAnalysis',
        component: TriDimensionAnalysis,
        meta: { title: 'tri dimension ranking', icon: 'Histogram', keepAlive: true }
      },
      
      // 5. 
      {
        path: 'realtime',
        name: 'RealTimeMonitor',
        component: RealTimeMonitor,
        meta: { title: 'realtime monitoring', icon: 'Monitor', keepAlive: true }
      },
      
      // 6. 
      {
        path: 'pipeline',
        name: 'PipelineManager',
        component: PipelineManager,
        meta: { title: 'pipeline management', icon: 'Connection', keepAlive: true }
      },
      
      // 7. 
      {
        path: 'visualization',
        name: 'Visualization',
        component: VisualizationDashboard,
        meta: { title: 'visualization dashboard', icon: 'DataLine', keepAlive: true }
      },
      
      // 8. 
      {
        path: 'admin',
        name: 'SystemAdmin',
        component: SystemAdmin,
        meta: { title: 'system management', icon: 'Setting', requiresAdmin: true, keepAlive: true }
      },
    ],
  },
  
  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: { title: 'page not found' }
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
