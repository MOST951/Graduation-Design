/**
 * API请求组合式函数
 * ==================
 * 提供统一的API请求处理，包含加载状态、错误处理和Toast通知
 * 
 * 用于答辩演示时提供友好的用户反馈
 */

import { ref, type Ref } from 'vue';
import { ElMessage, ElNotification } from 'element-plus';
import apiClient from '@/api';

// API响应类型
interface ApiResponse<T = any> {
  code: number;
  success: boolean;
  message: string;
  data: T;
  details?: any;
}

// 请求选项
interface RequestOptions {
  showLoading?: boolean;       // 是否显示加载提示
  showSuccess?: boolean;       // 是否显示成功提示
  showError?: boolean;         // 是否显示错误提示
  successMessage?: string;     // 自定义成功消息
  errorMessage?: string;       // 自定义错误消息
  loadingMessage?: string;     // 自定义加载消息
}

// 默认选项
const defaultOptions: RequestOptions = {
  showLoading: true,
  showSuccess: true,
  showError: true,
  loadingMessage: '处理中...',
};

/**
 * API请求组合式函数
 */
export function useApiRequest<T = any>() {
  const loading: Ref<boolean> = ref(false);
  const error: Ref<string | null> = ref(null);
  const data: Ref<T | null> = ref(null);

  /**
   * 执行GET请求
   */
  const get = async (
    url: string,
    params?: object,
    options: RequestOptions = {}
  ): Promise<T | null> => {
    return execute('get', url, params, options);
  };

  /**
   * 执行POST请求
   */
  const post = async (
    url: string,
    body?: object,
    options: RequestOptions = {}
  ): Promise<T | null> => {
    return execute('post', url, body, options);
  };

  /**
   * 执行请求
   */
  const execute = async (
    method: 'get' | 'post' | 'put' | 'delete',
    url: string,
    payload?: object,
    options: RequestOptions = {}
  ): Promise<T | null> => {
    const opts = { ...defaultOptions, ...options };
    
    loading.value = true;
    error.value = null;
    
    // 显示加载提示
    let loadingInstance: any = null;
    if (opts.showLoading) {
      loadingInstance = ElMessage({
        message: opts.loadingMessage,
        type: 'info',
        duration: 0,
        showClose: true,
      });
    }

    try {
      let response;
      
      if (method === 'get') {
        response = await apiClient.get<ApiResponse<T>>(url, { params: payload });
      } else if (method === 'post') {
        response = await apiClient.post<ApiResponse<T>>(url, payload);
      } else if (method === 'put') {
        response = await apiClient.put<ApiResponse<T>>(url, payload);
      } else {
        response = await apiClient.delete<ApiResponse<T>>(url);
      }

      const result = response.data;
      
      // 关闭加载提示
      if (loadingInstance) {
        loadingInstance.close();
      }

      // 检查业务状态码
      if (result.code === 200 || result.success) {
        data.value = result.data;
        
        // 显示成功提示
        if (opts.showSuccess) {
          ElMessage({
            message: opts.successMessage || result.message || '操作成功',
            type: 'success',
            duration: 2000,
          });
        }
        
        return result.data;
      } else {
        // 业务错误
        throw new Error(result.message || '操作失败');
      }
    } catch (err: any) {
      // 关闭加载提示
      if (loadingInstance) {
        loadingInstance.close();
      }

      // 获取错误消息
      const errorMsg = getErrorMessage(err, opts.errorMessage);
      error.value = errorMsg;

      // 显示错误提示
      if (opts.showError) {
        ElNotification({
          title: '操作失败',
          message: errorMsg,
          type: 'error',
          duration: 4000,
        });
      }

      console.error('[API Error]', err);
      return null;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 重置状态
   */
  const reset = () => {
    loading.value = false;
    error.value = null;
    data.value = null;
  };

  return {
    loading,
    error,
    data,
    get,
    post,
    execute,
    reset,
  };
}

/**
 * 获取友好的错误消息
 */
function getErrorMessage(err: any, customMessage?: string): string {
  if (customMessage) {
    return customMessage;
  }

  // 从响应中获取错误消息
  if (err.response?.data?.message) {
    return err.response.data.message;
  }

  // 网络错误
  if (err.message === 'Network Error') {
    return '网络连接失败，请检查后端服务是否启动';
  }

  // 超时错误
  if (err.code === 'ECONNABORTED') {
    return '请求超时，请稍后重试';
  }

  // HTTP状态码错误
  if (err.response) {
    const status = err.response.status;
    const statusMessages: Record<number, string> = {
      400: '请求参数错误',
      401: '登录已过期，请重新登录',
      403: '没有权限执行此操作',
      404: '请求的资源不存在',
      500: '服务器内部错误，请稍后重试',
      502: '网关错误，请检查服务状态',
      503: '服务暂时不可用',
    };
    return statusMessages[status] || `请求错误 (${status})`;
  }

  // 默认错误消息
  return err.message || '未知错误，请稍后重试';
}

/**
 * 快捷方法：显示成功通知
 */
export function showSuccess(message: string, title: string = '成功') {
  ElNotification({
    title,
    message,
    type: 'success',
    duration: 3000,
  });
}

/**
 * 快捷方法：显示错误通知
 */
export function showError(message: string, title: string = '错误') {
  ElNotification({
    title,
    message,
    type: 'error',
    duration: 4000,
  });
}

/**
 * 快捷方法：显示警告通知
 */
export function showWarning(message: string, title: string = '警告') {
  ElNotification({
    title,
    message,
    type: 'warning',
    duration: 3500,
  });
}

/**
 * 快捷方法：显示信息通知
 */
export function showInfo(message: string, title: string = '提示') {
  ElNotification({
    title,
    message,
    type: 'info',
    duration: 3000,
  });
}

export default useApiRequest;
