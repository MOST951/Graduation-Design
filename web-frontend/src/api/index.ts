import axios, { AxiosError, type AxiosResponse } from 'axios';
import { useAuthStore } from '@/store/auth';

// 是否为开发环境
const isDev = import.meta.env.DEV;

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
    const authStore = useAuthStore();
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`;
    }
    return config;
  },
  error => {
    if (isDev) console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    // 统一错误处理
    let message = '请求失败';
    
    if (error.response) {
      const status = error.response.status;
      switch (status) {
        case 401:
          message = '登录已过期，请重新登录';
          // 可以在这里触发登出逻辑
          break;
        case 403:
          message = '没有权限访问该资源';
          break;
        case 404:
          message = '请求的资源不存在';
          break;
        case 500:
          message = '服务器内部错误';
          break;
        default:
          message = `请求错误 (${status})`;
      }
    } else if (error.request) {
      message = '无法连接到服务器，请检查网络';
    }
    
    // 仅在开发环境打印错误
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
