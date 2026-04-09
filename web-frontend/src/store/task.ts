import { defineStore } from 'pinia';

export interface Task {
  id: number;
  name: string;
  keywords: string[];
  status: 'running' | 'waiting' | 'completed' | 'failed';
  progress: number;
  createdAt: string;
  updatedAt: string;
}

interface TaskState {
  tasks: Task[];
  loading: boolean;
  total: number;
  currentPage: number;
  pageSize: number;
  searchKeyword: string;
  statusFilter: string;
  sortField: string;
  sortOrder: 'ascending' | 'descending' | null;
}

export const useTaskStore = defineStore('task', {
  state: (): TaskState => ({
    tasks: [],
    loading: false,
    total: 0,
    currentPage: 1,
    pageSize: 10,
    searchKeyword: '',
    statusFilter: '',
    sortField: '',
    sortOrder: null,
  }),

  getters: {
    filteredTasks(state): Task[] {
      let result = [...state.tasks];
      
      // 关键词搜索
      if (state.searchKeyword) {
        const keyword = state.searchKeyword.toLowerCase();
        result = result.filter(task => 
          task.name.toLowerCase().includes(keyword) ||
          task.keywords.some(k => k.toLowerCase().includes(keyword))
        );
      }
      
      // 状态筛选
      if (state.statusFilter) {
        result = result.filter(task => task.status === state.statusFilter);
      }
      
      // 排序
      if (state.sortField && state.sortOrder) {
        result.sort((a, b) => {
          const aVal = a[state.sortField as keyof Task];
          const bVal = b[state.sortField as keyof Task];
          const order = state.sortOrder === 'ascending' ? 1 : -1;
          if (aVal < bVal) return -1 * order;
          if (aVal > bVal) return 1 * order;
          return 0;
        });
      }
      
      return result;
    },
  },

  actions: {
    async fetchTasks() {
      this.loading = true;
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // 模拟数据
        this.tasks = [
          { id: 1, name: '热点话题监控', keywords: ['热搜', '头条', '热门'], status: 'running', progress: 65, createdAt: '2025-12-09 10:00:00', updatedAt: '2025-12-09 15:30:00' },
          { id: 2, name: '品牌舆情分析', keywords: ['品牌名', '产品名'], status: 'completed', progress: 100, createdAt: '2025-12-08 09:00:00', updatedAt: '2025-12-08 18:00:00' },
          { id: 3, name: '竞品监控任务', keywords: ['竞品A', '竞品B', '竞品C', '竞品D'], status: 'waiting', progress: 0, createdAt: '2025-12-09 14:00:00', updatedAt: '2025-12-09 14:00:00' },
          { id: 4, name: '用户反馈收集', keywords: ['反馈', '建议', '投诉'], status: 'failed', progress: 32, createdAt: '2025-12-07 08:00:00', updatedAt: '2025-12-07 12:00:00' },
          { id: 5, name: '行业动态追踪', keywords: ['行业', '趋势'], status: 'running', progress: 45, createdAt: '2025-12-09 11:00:00', updatedAt: '2025-12-09 16:00:00' },
          { id: 6, name: '社会热点分析', keywords: ['社会', '民生', '政策'], status: 'completed', progress: 100, createdAt: '2025-12-06 10:00:00', updatedAt: '2025-12-06 20:00:00' },
          { id: 7, name: '娱乐八卦监控', keywords: ['明星', '娱乐', '八卦'], status: 'running', progress: 78, createdAt: '2025-12-09 08:00:00', updatedAt: '2025-12-09 17:00:00' },
          { id: 8, name: '科技资讯采集', keywords: ['科技', 'AI', '互联网'], status: 'waiting', progress: 0, createdAt: '2025-12-09 16:00:00', updatedAt: '2025-12-09 16:00:00' },
        ];
        this.total = this.tasks.length;
      } finally {
        this.loading = false;
      }
    },

    async createTask(task: Partial<Task>) {
      this.loading = true;
      try {
        await new Promise(resolve => setTimeout(resolve, 300));
        const newTask: Task = {
          id: Date.now(),
          name: task.name || '新任务',
          keywords: task.keywords || [],
          status: 'waiting',
          progress: 0,
          createdAt: new Date().toLocaleString(),
          updatedAt: new Date().toLocaleString(),
        };
        this.tasks.unshift(newTask);
        this.total++;
        return newTask;
      } finally {
        this.loading = false;
      }
    },

    async updateTask(id: number, updates: Partial<Task>) {
      const index = this.tasks.findIndex(t => t.id === id);
      if (index !== -1) {
        this.tasks[index] = { ...this.tasks[index], ...updates, updatedAt: new Date().toLocaleString() };
      }
    },

    async deleteTask(id: number) {
      this.tasks = this.tasks.filter(t => t.id !== id);
      this.total--;
    },

    async deleteTasks(ids: number[]) {
      this.tasks = this.tasks.filter(t => !ids.includes(t.id));
      this.total -= ids.length;
    },

    async startTask(id: number) {
      await this.updateTask(id, { status: 'running' });
    },

    async pauseTask(id: number) {
      await this.updateTask(id, { status: 'waiting' });
    },

    setSearchKeyword(keyword: string) {
      this.searchKeyword = keyword;
    },

    setStatusFilter(status: string) {
      this.statusFilter = status;
    },

    setSort(field: string, order: 'ascending' | 'descending' | null) {
      this.sortField = field;
      this.sortOrder = order;
    },

    setPage(page: number) {
      this.currentPage = page;
    },

    setPageSize(size: number) {
      this.pageSize = size;
      this.currentPage = 1;
    },
  },
});
