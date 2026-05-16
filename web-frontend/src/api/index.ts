import axios, { AxiosError, type AxiosResponse } from 'axios';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '@/store/auth';
import router from '@/router';

// 是否为开发环境
const isDev = import.meta.env.DEV;

// 注: 已移除全局 ElLoading 蒙层
// 原因: 全局 loading 用 requestCount 计数, 任何慢/挂起的请求都会让 "加载中..." 永不消失,
// 锁死整个 UI (如 PipelineManager 多个并发请求中只要 1 个慢就触发).
// 改为各组件自行用 v-loading / loading ref 管理局部 loading.
function showLoading() { /* no-op */ }
function hideLoading() { /* no-op */ }

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    // 显示全局 loading
    showLoading();

    const authStore = useAuthStore();
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`;
    }
    if (authStore.user?.role) {
      config.headers['X-User-Role'] = authStore.user.role;
    }
    return config;
  },
  error => {
    hideLoading();
    if (isDev) console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 关闭 loading
    hideLoading();
    return response;
  },
  (error: AxiosError<{ message?: string }>) => {
    // 关闭 loading
    hideLoading();

    // 统一错误处理
    let message = '请求失败';

    if (error.response) {
      const status = error.response.status;
      // 优先使用后端返回的错误信息
      const serverMsg = error.response.data?.message;

      switch (status) {
        case 401:
          message = serverMsg || '登录已过期，请重新登录';
          // 清除登录状态并跳转到登录页
          {
            const authStore = useAuthStore();
            authStore.logout();
            router.replace({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } });
          }
          // 仅401显示提示
          ElMessage.warning({ message, duration: 3000, showClose: true });
          break;
        case 403:
          message = serverMsg || '没有权限访问该资源';
          ElMessage.warning({ message, duration: 3000, showClose: true });
          break;
        case 404:
        case 500:
        case 502:
        case 503:
        default:
          // 静默处理：不弹全局错误，由各组件自行决定提示
          if (isDev) {
            console.debug(`[API ${status}] ${error.config?.url} — 静默处理`);
          }
          break;
      }
    } else if (error.request) {
      // 网络不可达 — 静默处理，不弹红色错误
      if (isDev) {
        console.debug('[API] 网络不可达:', error.config?.url);
      }
    } else {
      if (isDev) {
        console.debug('[API] 请求配置错误:', error.message);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// 导出通用请求方法
export const request = {
  get: <T = any>(url: string, params?: object) => 
    apiClient.get<T>(url, { params }).then(res => res.data),
  
  post: <T = any>(url: string, data?: object) => 
    apiClient.post<T>(url, data).then(res => res.data),
  
  put: <T = any>(url: string, data?: object) => 
    apiClient.put<T>(url, data).then(res => res.data),
  
  delete: <T = any>(url: string) => 
    apiClient.delete<T>(url).then(res => res.data),
};
