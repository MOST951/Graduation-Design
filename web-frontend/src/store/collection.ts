/**
 * 数据采集模块 Store
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  batchDeleteTasks,
  startTask,
  stopTask,
  pauseTask,
  resumeTask,
  retryTask,
  getTaskLogs,
  getTaskStats,
  getGlobalStats,
  connectRealtimeData,
  exportTaskData,
  downloadExportFile,
  clearTaskData,
  type Task,
  type TaskConfig,
  type TaskStatus,
  type TaskLog,
  type TaskStats,
  type TaskListParams,
  type LogQueryParams,
  type ExportFormat,
} from '@/api/collection';

// 防抖函数
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number): T {
  let timer: number | null = null;
  return ((...args: any[]) => {
    if (timer) clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delay);
  }) as T;
}

// 实时数据类型
interface RealtimeData {
  progress: number;
  collected: number;
  failed: number;
  speed: number;
  successRate: number;
  platformDistribution: { platform: string; count: number }[];
  recentLogs: TaskLog[];
  recentData: any[];
}

// 统计信息类型
interface Statistics {
  totalTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  totalCollected: number;
  successRate: number;
  dailyStats: { date: string; success: number; failed: number }[];
  platformStats: { platform: string; count: number }[];
  durationStats: { range: string; count: number }[];
}

export const useCollectionStore = defineStore('collection', () => {
  // ==================== State ====================
  
  /** 任务列表 */
  const tasks = ref<Task[]>([]);
  
  /** 任务总数 */
  const totalTasks = ref(0);
  
  /** 当前选中任务 */
  const currentTask = ref<Task | null>(null);
  
  /** 任务日志 */
  const taskLogs = ref<TaskLog[]>([]);
  
  /** 日志总数 */
  const totalLogs = ref(0);
  
  /** 实时数据 */
  const realtimeData = ref<RealtimeData>({
    progress: 0,
    collected: 0,
    failed: 0,
    speed: 0,
    successRate: 0,
    platformDistribution: [],
    recentLogs: [],
    recentData: [],
  });
  
  /** 统计信息 */
  const statistics = ref<Statistics>({
    totalTasks: 0,
    runningTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    totalCollected: 0,
    successRate: 0,
    dailyStats: [],
    platformStats: [],
    durationStats: [],
  });
  
  /** 加载状态 */
  const isLoading = ref(false);
  
  /** 日志加载状态 */
  const isLoadingLogs = ref(false);
  
  /** 统计加载状态 */
  const isLoadingStats = ref(false);
  
  /** WebSocket 连接状态 */
  const wsConnected = ref(false);
  
  /** WebSocket 关闭函数 */
  let wsDisconnect: (() => void) | null = null;
  
  /** 当前订阅的任务ID */
  const subscribedTaskId = ref<number | null>(null);

  // ==================== Getters ====================
  
  /** 运行中任务 */
  const activeTasks = computed(() => 
    tasks.value.filter(t => t.status === 'running')
  );
  
  /** 等待中任务 */
  const waitingTasks = computed(() => 
    tasks.value.filter(t => t.status === 'waiting')
  );
  
  /** 已完成任务 */
  const completedTasks = computed(() => 
    tasks.value.filter(t => t.status === 'completed')
  );
  
  /** 失败任务 */
  const failedTasks = computed(() => 
    tasks.value.filter(t => t.status === 'failed')
  );
  
  /** 暂停任务 */
  const pausedTasks = computed(() => 
    tasks.value.filter(t => t.status === 'paused')
  );
  
  /** 任务统计信息 */
  const taskStats = computed(() => ({
    total: tasks.value.length,
    running: activeTasks.value.length,
    waiting: waitingTasks.value.length,
    completed: completedTasks.value.length,
    failed: failedTasks.value.length,
    paused: pausedTasks.value.length,
    totalCollected: tasks.value.reduce((sum, t) => sum + t.collectedCount, 0),
    totalFailed: tasks.value.reduce((sum, t) => sum + t.failedCount, 0),
  }));
  
  /** 按状态分组的任务 */
  const groupedTasks = computed(() => ({
    running: activeTasks.value,
    waiting: waitingTasks.value,
    completed: completedTasks.value,
    failed: failedTasks.value,
    paused: pausedTasks.value,
  }));
  
  /** 任务队列（等待中 + 运行中） */
  const taskQueue = computed(() => [
    ...activeTasks.value,
    ...waitingTasks.value,
  ]);

  // ==================== Actions ====================
  
  /**
   * 获取任务列表
   */
  async function fetchTasks(params: TaskListParams = {}) {
    isLoading.value = true;
    try {
      const response = await getTasks(params);
      tasks.value = response.list;
      totalTasks.value = response.total;
      return response;
    } catch (error) {
      console.error('获取任务列表失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 获取单个任务详情
   */
  async function fetchTask(id: number) {
    isLoading.value = true;
    try {
      const task = await getTask(id);
      currentTask.value = task;
      
      // 更新列表中的任务
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index] = task;
      }
      
      return task;
    } catch (error) {
      console.error('获取任务详情失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 创建新任务
   */
  async function createNewTask(taskData: TaskConfig) {
    isLoading.value = true;
    try {
      const newTask = await createTask(taskData);
      tasks.value.unshift(newTask);
      totalTasks.value++;
      return newTask;
    } catch (error) {
      console.error('创建任务失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 更新任务
   */
  async function updateExistingTask(id: number, data: Partial<TaskConfig>) {
    try {
      const updatedTask = await updateTask(id, data);
      
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      
      if (currentTask.value?.id === id) {
        currentTask.value = updatedTask;
      }
      
      return updatedTask;
    } catch (error) {
      console.error('更新任务失败:', error);
      throw error;
    }
  }
  
  /**
   * 删除任务
   */
  async function removeTask(id: number) {
    try {
      await deleteTask(id);
      tasks.value = tasks.value.filter(t => t.id !== id);
      totalTasks.value--;
      
      if (currentTask.value?.id === id) {
        currentTask.value = null;
      }
    } catch (error) {
      console.error('删除任务失败:', error);
      throw error;
    }
  }
  
  /**
   * 批量删除任务
   */
  async function removeTasks(ids: number[]) {
    try {
      await batchDeleteTasks(ids);
      tasks.value = tasks.value.filter(t => !ids.includes(t.id));
      totalTasks.value -= ids.length;
      
      if (currentTask.value && ids.includes(currentTask.value.id)) {
        currentTask.value = null;
      }
    } catch (error) {
      console.error('批量删除任务失败:', error);
      throw error;
    }
  }
  
  /**
   * 更新任务状态
   */
  async function updateTaskStatus(id: number, status: TaskStatus) {
    try {
      let updatedTask: Task;
      
      switch (status) {
        case 'running':
          updatedTask = await startTask(id);
          break;
        case 'paused':
          updatedTask = await pauseTask(id);
          break;
        case 'waiting':
          updatedTask = await resumeTask(id);
          break;
        default:
          updatedTask = await stopTask(id);
      }
      
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      
      if (currentTask.value?.id === id) {
        currentTask.value = updatedTask;
      }
      
      return updatedTask;
    } catch (error) {
      console.error('更新任务状态失败:', error);
      throw error;
    }
  }
  
  /**
   * 启动任务
   */
  async function startTaskById(id: number) {
    return updateTaskStatus(id, 'running');
  }
  
  /**
   * 停止任务
   */
  async function stopTaskById(id: number) {
    try {
      const updatedTask = await stopTask(id);
      
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      
      return updatedTask;
    } catch (error) {
      console.error('停止任务失败:', error);
      throw error;
    }
  }
  
  /**
   * 暂停任务
   */
  async function pauseTaskById(id: number) {
    return updateTaskStatus(id, 'paused');
  }
  
  /**
   * 恢复任务
   */
  async function resumeTaskById(id: number) {
    try {
      const updatedTask = await resumeTask(id);
      
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      
      return updatedTask;
    } catch (error) {
      console.error('恢复任务失败:', error);
      throw error;
    }
  }
  
  /**
   * 重试失败任务
   */
  async function retryTaskById(id: number) {
    try {
      const updatedTask = await retryTask(id);
      
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      
      return updatedTask;
    } catch (error) {
      console.error('重试任务失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取任务日志
   */
  async function fetchTaskLogs(id: number, params: LogQueryParams = {}) {
    isLoadingLogs.value = true;
    try {
      const response = await getTaskLogs(id, params);
      taskLogs.value = response.list;
      totalLogs.value = response.total;
      return response;
    } catch (error) {
      console.error('获取任务日志失败:', error);
      throw error;
    } finally {
      isLoadingLogs.value = false;
    }
  }
  
  /**
   * 获取任务统计
   */
  async function fetchTaskStats(id: number) {
    try {
      return await getTaskStats(id);
    } catch (error) {
      console.error('获取任务统计失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取全局统计
   */
  async function fetchGlobalStats(params: { startDate?: string; endDate?: string } = {}) {
    isLoadingStats.value = true;
    try {
      const stats = await getGlobalStats(params);
      statistics.value = stats;
      return stats;
    } catch (error) {
      console.error('获取全局统计失败:', error);
      throw error;
    } finally {
      isLoadingStats.value = false;
    }
  }
  
  /**
   * 订阅实时数据（防抖更新）
   */
  const updateRealtimeData = debounce((data: Partial<RealtimeData>) => {
    Object.assign(realtimeData.value, data);
  }, 100);
  
  /**
   * 订阅实时数据
   */
  function subscribeToRealtime(taskId: number | null = null) {
    // 先取消之前的订阅
    unsubscribeFromRealtime();
    
    subscribedTaskId.value = taskId;
    
    wsDisconnect = connectRealtimeData(
      taskId,
      (data) => {
        wsConnected.value = true;
        
        // 根据消息类型处理
        switch (data.type) {
          case 'progress':
            updateRealtimeData({
              progress: data.progress,
              collected: data.collected,
              failed: data.failed,
              speed: data.speed,
              successRate: data.successRate,
            });
            break;
            
          case 'platform':
            updateRealtimeData({
              platformDistribution: data.platforms,
            });
            break;
            
          case 'log':
            const newLog: TaskLog = {
              id: Date.now(),
              taskId: taskId || 0,
              level: data.level,
              message: data.message,
              timestamp: new Date().toISOString(),
            };
            realtimeData.value.recentLogs = [
              newLog,
              ...realtimeData.value.recentLogs.slice(0, 99),
            ];
            break;
            
          case 'data':
            realtimeData.value.recentData = [
              data.item,
              ...realtimeData.value.recentData.slice(0, 9),
            ];
            break;
            
          case 'taskUpdate':
            // 更新任务列表中的任务状态
            const index = tasks.value.findIndex(t => t.id === data.task.id);
            if (index !== -1) {
              tasks.value[index] = { ...tasks.value[index], ...data.task };
            }
            break;
        }
      },
      (error) => {
        wsConnected.value = false;
        console.error('WebSocket 错误:', error);
      }
    );
  }
  
  /**
   * 取消订阅实时数据
   */
  function unsubscribeFromRealtime() {
    if (wsDisconnect) {
      wsDisconnect();
      wsDisconnect = null;
    }
    wsConnected.value = false;
    subscribedTaskId.value = null;
  }
  
  /**
   * 导出数据
   */
  async function exportData(options: {
    taskId: number;
    format: ExportFormat;
    fields?: string[];
    startDate?: string;
    endDate?: string;
  }) {
    try {
      const blob = await exportTaskData(options.taskId, options.format, {
        fields: options.fields,
        startDate: options.startDate,
        endDate: options.endDate,
      });
      
      const task = tasks.value.find(t => t.id === options.taskId);
      const filename = `${task?.name || 'task'}_${new Date().toISOString().slice(0, 10)}.${options.format}`;
      
      downloadExportFile(blob, filename);
    } catch (error) {
      console.error('导出数据失败:', error);
      throw error;
    }
  }
  
  /**
   * 清空任务数据
   */
  async function clearData(taskId: number) {
    try {
      await clearTaskData(taskId);
      
      // 更新任务的采集数量
      const index = tasks.value.findIndex(t => t.id === taskId);
      if (index !== -1) {
        tasks.value[index].collectedCount = 0;
        tasks.value[index].failedCount = 0;
      }
    } catch (error) {
      console.error('清空数据失败:', error);
      throw error;
    }
  }
  
  /**
   * 选中任务
   */
  function selectTask(task: Task | null) {
    currentTask.value = task;
  }
  
  /**
   * 清空日志
   */
  function clearLogs() {
    taskLogs.value = [];
    totalLogs.value = 0;
    realtimeData.value.recentLogs = [];
  }
  
  /**
   * 重置实时数据
   */
  function resetRealtimeData() {
    realtimeData.value = {
      progress: 0,
      collected: 0,
      failed: 0,
      speed: 0,
      successRate: 0,
      platformDistribution: [],
      recentLogs: [],
      recentData: [],
    };
  }
  
  /**
   * 重置 Store
   */
  function $reset() {
    unsubscribeFromRealtime();
    tasks.value = [];
    totalTasks.value = 0;
    currentTask.value = null;
    taskLogs.value = [];
    totalLogs.value = 0;
    resetRealtimeData();
    statistics.value = {
      totalTasks: 0,
      runningTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      totalCollected: 0,
      successRate: 0,
      dailyStats: [],
      platformStats: [],
      durationStats: [],
    };
    isLoading.value = false;
    isLoadingLogs.value = false;
    isLoadingStats.value = false;
  }

  return {
    // State
    tasks,
    totalTasks,
    currentTask,
    taskLogs,
    totalLogs,
    realtimeData,
    statistics,
    isLoading,
    isLoadingLogs,
    isLoadingStats,
    wsConnected,
    subscribedTaskId,
    
    // Getters
    activeTasks,
    waitingTasks,
    completedTasks,
    failedTasks,
    pausedTasks,
    taskStats,
    groupedTasks,
    taskQueue,
    
    // Actions
    fetchTasks,
    fetchTask,
    createNewTask,
    updateExistingTask,
    removeTask,
    removeTasks,
    updateTaskStatus,
    startTaskById,
    stopTaskById,
    pauseTaskById,
    resumeTaskById,
    retryTaskById,
    fetchTaskLogs,
    fetchTaskStats,
    fetchGlobalStats,
    subscribeToRealtime,
    unsubscribeFromRealtime,
    exportData,
    clearData,
    selectTask,
    clearLogs,
    resetRealtimeData,
    $reset,
  };
});
