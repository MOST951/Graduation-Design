import axios, { AxiosError, type AxiosResponse } from 'axios';
import { ElLoading, ElMessage } from 'element-plus';
import { useAuthStore } from '@/store/auth';
import router from '@/router';

// 是否为开发环境
const isDev = import.meta.env.DEV;

// 全局 loading 实例管理（支持并发请求计数）
let loadingInstance: ReturnType<typeof ElLoading.service> | null = null;
let requestCount = 0;

function showLoading() {
  if (requestCount === 0) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: '加载中...',
      background: 'rgba(0, 0, 0, 0.15)',
    });
  }
  requestCount++;
}

function hideLoading() {
  requestCount--;
  if (requestCount <= 0) {
    requestCount = 0;
    loadingInstance?.close();
    loadingInstance = null;
  }
}

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
          break;
        case 403:
          message = serverMsg || '没有权限访问该资源';
          break;
        case 404:
          message = serverMsg || '请求的资源不存在';
          break;
        case 500:
          message = serverMsg || '服务器内部错误';
          break;
        default:
          message = serverMsg || `请求错误 (${status})`;
      }
    } else if (error.request) {
      message = '无法连接到服务器，请检查网络';
    } else {
      message = error.message || '网络错误';
    }

    // 统一弹出错误提示
    ElMessage.error({ message, duration: 3000, showClose: true });

    // 仅在开发环境打印详细错误
    if (isDev) {
      console.error('[API Error]', {
        url: error.config?.url,
        status: error.response?.status,
        message: error.message,
      });
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
