/**
 * 数据下钻 Store
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  type DrillPath,
  type DrillLevel,
  type DrillNode,
  type DrillState,
  type DrillHistory,
  type DrillAnalysis,
  type DrillDownConfig,
  builtInPaths,
  defaultDrillConfig,
  generateDrillId,
  createDrillNode,
  calculateSummary,
  detectAnomalies,
  calculateTrend,
  generateInsights,
  buildDrillFilters,
  formatDrillPath,
  exportDrillHistory,
  importDrillHistory,
} from '@/api/drilldown';

// 深拷贝
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

// 本地存储键
const STORAGE_KEY_PATHS = 'drilldown_custom_paths';
const STORAGE_KEY_HISTORY = 'drilldown_history';
const STORAGE_KEY_CONFIG = 'drilldown_config';

export const useDrillDownStore = defineStore('drilldown', () => {
  // ==================== State ====================
  
  /** 内置下钻路径 */
  const builtInDrillPaths = ref<DrillPath[]>(builtInPaths);
  
  /** 自定义下钻路径 */
  const customPaths = ref<DrillPath[]>([]);
  
  /** 当前活跃的下钻路径 */
  const activePath = ref<DrillPath | null>(null);
  
  /** 当前下钻层级 */
  const currentLevel = ref(0);
  
  /** 下钻节点栈 */
  const drillStack = ref<DrillNode[]>([]);
  
  /** 下钻历史记录 */
  const history = ref<DrillHistory[]>([]);
  
  /** 当前历史记录索引 */
  const currentHistoryIndex = ref(-1);
  
  /** 配置 */
  const config = ref<DrillDownConfig>(deepClone(defaultDrillConfig));
  
  /** 当前分析结果 */
  const currentAnalysis = ref<DrillAnalysis | null>(null);
  
  /** 并行下钻会话 */
  const parallelSessions = ref<Map<string, DrillState>>(new Map());
  
  /** 收藏的下钻路径 */
  const favorites = ref<string[]>([]);
  
  /** 是否正在加载 */
  const isLoading = ref(false);
  
  // ==================== Getters ====================
  
  /** 所有下钻路径 */
  const allPaths = computed(() => [...builtInDrillPaths.value, ...customPaths.value]);
  
  /** 当前层级配置 */
  const currentLevelConfig = computed(() => {
    if (!activePath.value || currentLevel.value >= activePath.value.levels.length) {
      return null;
    }
    return activePath.value.levels[currentLevel.value];
  });
  
  /** 是否可以下钻 */
  const canDrillDown = computed(() => {
    return activePath.value && currentLevel.value < activePath.value.levels.length - 1;
  });
  
  /** 是否可以上钻 */
  const canDrillUp = computed(() => {
    return drillStack.value.length > 0;
  });
  
  /** 当前下钻路径描述 */
  const currentPathDescription = computed(() => {
    return formatDrillPath(drillStack.value);
  });
  
  /** 当前过滤器 */
  const currentFilters = computed(() => {
    return buildDrillFilters(drillStack.value);
  });
  
  /** 是否可以撤销 */
  const canUndo = computed(() => {
    return currentHistoryIndex.value > 0;
  });
  
  /** 是否可以重做 */
  const canRedo = computed(() => {
    return currentHistoryIndex.value < history.value.length - 1;
  });
  
  // ==================== Actions ====================
  
  /**
   * 初始化
   */
  function initialize() {
    loadCustomPaths();
    loadHistory();
    loadConfig();
    loadFavorites();
  }
  
  /**
   * 加载自定义路径
   */
  function loadCustomPaths() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_PATHS);
      if (stored) {
        customPaths.value = JSON.parse(stored);
      }
    } catch (error) {
      console.error('加载自定义路径失败:', error);
    }
  }
  
  /**
   * 保存自定义路径
   */
  function saveCustomPaths() {
    try {
      localStorage.setItem(STORAGE_KEY_PATHS, JSON.stringify(customPaths.value));
    } catch (error) {
      console.error('保存自定义路径失败:', error);
    }
  }
  
  /**
   * 加载历史记录
   */
  function loadHistory() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_HISTORY);
      if (stored) {
        history.value = JSON.parse(stored);
      }
    } catch (error) {
      console.error('加载历史记录失败:', error);
    }
  }
  
  /**
   * 保存历史记录
   */
  function saveHistory() {
    try {
      // 限制历史记录数量
      if (history.value.length > config.value.maxHistorySize) {
        history.value = history.value.slice(-config.value.maxHistorySize);
      }
      localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history.value));
    } catch (error) {
      console.error('保存历史记录失败:', error);
    }
  }
  
  /**
   * 加载配置
   */
  function loadConfig() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_CONFIG);
      if (stored) {
        config.value = { ...config.value, ...JSON.parse(stored) };
      }
    } catch (error) {
      console.error('加载配置失败:', error);
    }
  }
  
  /**
   * 保存配置
   */
  function saveConfig() {
    try {
      localStorage.setItem(STORAGE_KEY_CONFIG, JSON.stringify(config.value));
    } catch (error) {
      console.error('保存配置失败:', error);
    }
  }
  
  /**
   * 加载收藏
   */
  function loadFavorites() {
    try {
      const stored = localStorage.getItem('drilldown_favorites');
      if (stored) {
        favorites.value = JSON.parse(stored);
      }
    } catch (error) {
      console.error('加载收藏失败:', error);
    }
  }
  
  /**
   * 保存收藏
   */
  function saveFavorites() {
    try {
      localStorage.setItem('drilldown_favorites', JSON.stringify(favorites.value));
    } catch (error) {
      console.error('保存收藏失败:', error);
    }
  }
  
  /**
   * 开始下钻
   */
  function startDrill(pathId: string) {
    const path = allPaths.value.find(p => p.id === pathId);
    if (!path) {
      throw new Error('下钻路径不存在');
    }
    
    activePath.value = path;
    currentLevel.value = 0;
    drillStack.value = [];
    currentAnalysis.value = null;
    
    // 保存状态
    if (config.value.autoSaveHistory) {
      saveCurrentState();
    }
  }
  
  /**
   * 下钻到下一层级
   */
  function drillDown(node: DrillNode, data?: any) {
    if (!canDrillDown.value || !activePath.value) {
      return;
    }
    
    // 添加节点到栈
    drillStack.value.push(node);
    currentLevel.value++;
    
    // 分析数据
    if (data && config.value.showAnalysis) {
      analyzeCurrentLevel(data);
    }
    
    // 保存状态
    if (config.value.autoSaveHistory) {
      saveCurrentState();
    }
  }
  
  /**
   * 上钻到上一层级
   */
  function drillUp() {
    if (!canDrillUp.value) {
      return;
    }
    
    drillStack.value.pop();
    currentLevel.value--;
    currentAnalysis.value = null;
    
    // 保存状态
    if (config.value.autoSaveHistory) {
      saveCurrentState();
    }
  }
  
  /**
   * 跳转到指定层级
   */
  function jumpToLevel(level: number) {
    if (level < 0 || level > currentLevel.value) {
      return;
    }
    
    const diff = currentLevel.value - level;
    for (let i = 0; i < diff; i++) {
      drillStack.value.pop();
    }
    currentLevel.value = level;
    currentAnalysis.value = null;
    
    // 保存状态
    if (config.value.autoSaveHistory) {
      saveCurrentState();
    }
  }
  
  /**
   * 重置下钻
   */
  function resetDrill() {
    drillStack.value = [];
    currentLevel.value = 0;
    currentAnalysis.value = null;
  }
  
  /**
   * 分析当前层级数据
   */
  function analyzeCurrentLevel(data: any[]) {
    if (!data || data.length === 0) {
      currentAnalysis.value = null;
      return;
    }
    
    // 提取数值数据
    const values = data.map(d => typeof d.value === 'number' ? d.value : 0);
    const summary = calculateSummary(values);
    
    // 计算分布
    const total = summary.total;
    const distribution = data.map(d => ({
      label: d.label || d.name || String(d.value),
      value: typeof d.value === 'number' ? d.value : 0,
      percentage: total > 0 ? (d.value / total) * 100 : 0,
    }));
    
    // Top项
    const topItems = [...distribution]
      .sort((a, b) => b.value - a.value)
      .slice(0, 10)
      .map((item, index) => ({
        ...item,
        rank: index + 1,
      }));
    
    // 检测异常
    const anomalies = detectAnomalies(distribution);
    
    // 对比分析
    let comparison;
    if (drillStack.value.length > 1) {
      const parentNode = drillStack.value[drillStack.value.length - 2];
      const parentValue = typeof parentNode.data === 'number' ? parentNode.data : 0;
      const currentValue = summary.total;
      
      comparison = {
        parentLevel: {
          value: parentValue,
          label: parentNode.label,
        },
        change: {
          absolute: currentValue - parentValue,
          percentage: parentValue > 0 ? ((currentValue - parentValue) / parentValue) * 100 : 0,
          trend: calculateTrend(currentValue, parentValue),
        },
      };
    }
    
    const analysis: DrillAnalysis = {
      currentLevel: {
        summary,
        distribution,
        topItems,
      },
      comparison,
      anomalies,
      insights: [],
    };
    
    // 生成洞察
    analysis.insights = generateInsights(analysis);
    
    currentAnalysis.value = analysis;
  }
  
  /**
   * 保存当前状态
   */
  function saveCurrentState() {
    if (!activePath.value) return;
    
    const state: DrillState = {
      pathId: activePath.value.id,
      currentLevel: currentLevel.value,
      nodes: deepClone(drillStack.value),
      filters: currentFilters.value,
      timestamp: Date.now(),
    };
    
    // 如果是新的历史记录
    if (currentHistoryIndex.value === -1 || 
        currentHistoryIndex.value === history.value.length - 1) {
      const historyItem: DrillHistory = {
        id: generateDrillId(),
        pathId: activePath.value.id,
        states: [state],
        createdAt: new Date().toISOString(),
      };
      history.value.push(historyItem);
      currentHistoryIndex.value = history.value.length - 1;
    } else {
      // 更新现有历史记录
      const currentHistory = history.value[currentHistoryIndex.value];
      currentHistory.states.push(state);
    }
    
    saveHistory();
  }
  
  /**
   * 加载历史状态
   */
  function loadHistoryState(historyId: string, stateIndex: number = -1) {
    const historyItem = history.value.find(h => h.id === historyId);
    if (!historyItem) return;
    
    const index = stateIndex >= 0 ? stateIndex : historyItem.states.length - 1;
    const state = historyItem.states[index];
    
    if (!state) return;
    
    // 恢复状态
    const path = allPaths.value.find(p => p.id === state.pathId);
    if (path) {
      activePath.value = path;
      currentLevel.value = state.currentLevel;
      drillStack.value = deepClone(state.nodes);
    }
  }
  
  /**
   * 撤销
   */
  function undo() {
    if (!canUndo.value) return;
    
    currentHistoryIndex.value--;
    const historyItem = history.value[currentHistoryIndex.value];
    if (historyItem && historyItem.states.length > 0) {
      const state = historyItem.states[historyItem.states.length - 1];
      loadHistoryState(historyItem.id, historyItem.states.length - 1);
    }
  }
  
  /**
   * 重做
   */
  function redo() {
    if (!canRedo.value) return;
    
    currentHistoryIndex.value++;
    const historyItem = history.value[currentHistoryIndex.value];
    if (historyItem && historyItem.states.length > 0) {
      const state = historyItem.states[historyItem.states.length - 1];
      loadHistoryState(historyItem.id, historyItem.states.length - 1);
    }
  }
  
  /**
   * 创建自定义路径
   */
  function createPath(name: string, levels: DrillLevel[]): DrillPath {
    const path: DrillPath = {
      id: generateDrillId(),
      name,
      levels: levels.map((level, index) => ({ ...level, order: index })),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    customPaths.value.push(path);
    saveCustomPaths();
    
    return path;
  }
  
  /**
   * 更新路径
   */
  function updatePath(pathId: string, updates: Partial<DrillPath>) {
    const index = customPaths.value.findIndex(p => p.id === pathId);
    if (index !== -1) {
      customPaths.value[index] = {
        ...customPaths.value[index],
        ...updates,
        updatedAt: new Date().toISOString(),
      };
      saveCustomPaths();
    }
  }
  
  /**
   * 删除路径
   */
  function deletePath(pathId: string) {
    customPaths.value = customPaths.value.filter(p => p.id !== pathId);
    saveCustomPaths();
  }
  
  /**
   * 收藏路径
   */
  function toggleFavorite(pathId: string) {
    const index = favorites.value.indexOf(pathId);
    if (index !== -1) {
      favorites.value.splice(index, 1);
    } else {
      favorites.value.push(pathId);
    }
    saveFavorites();
  }
  
  /**
   * 导出历史记录
   */
  function exportHistory(historyId: string) {
    const historyItem = history.value.find(h => h.id === historyId);
    if (!historyItem) return;
    
    const blob = exportDrillHistory(historyItem);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `drilldown-${historyItem.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  
  /**
   * 导入历史记录
   */
  function importHistory(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const historyItem = importDrillHistory(e.target?.result as string);
          history.value.push(historyItem);
          saveHistory();
          resolve();
        } catch (error) {
          reject(new Error('无效的历史记录文件'));
        }
      };
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.readAsText(file);
    });
  }
  
  /**
   * 清除历史记录
   */
  function clearHistory() {
    history.value = [];
    currentHistoryIndex.value = -1;
    saveHistory();
  }
  
  /**
   * 更新配置
   */
  function updateConfig(updates: Partial<DrillDownConfig>) {
    config.value = { ...config.value, ...updates };
    saveConfig();
  }
  
  /**
   * 创建并行会话
   */
  function createParallelSession(sessionId: string) {
    if (!config.value.enableParallelDrill || !activePath.value) return;
    
    const state: DrillState = {
      pathId: activePath.value.id,
      currentLevel: currentLevel.value,
      nodes: deepClone(drillStack.value),
      filters: currentFilters.value,
      timestamp: Date.now(),
    };
    
    parallelSessions.value.set(sessionId, state);
  }
  
  /**
   * 切换到并行会话
   */
  function switchToSession(sessionId: string) {
    const state = parallelSessions.value.get(sessionId);
    if (!state) return;
    
    const path = allPaths.value.find(p => p.id === state.pathId);
    if (path) {
      activePath.value = path;
      currentLevel.value = state.currentLevel;
      drillStack.value = deepClone(state.nodes);
    }
  }
  
  /**
   * 删除并行会话
   */
  function deleteSession(sessionId: string) {
    parallelSessions.value.delete(sessionId);
  }
  
  return {
    // State
    builtInDrillPaths,
    customPaths,
    activePath,
    currentLevel,
    drillStack,
    history,
    currentHistoryIndex,
    config,
    currentAnalysis,
    parallelSessions,
    favorites,
    isLoading,
    
    // Getters
    allPaths,
    currentLevelConfig,
    canDrillDown,
    canDrillUp,
    currentPathDescription,
    currentFilters,
    canUndo,
    canRedo,
    
    // Actions
    initialize,
    startDrill,
    drillDown,
    drillUp,
    jumpToLevel,
    resetDrill,
    analyzeCurrentLevel,
    saveCurrentState,
    loadHistoryState,
    undo,
    redo,
    createPath,
    updatePath,
    deletePath,
    toggleFavorite,
    exportHistory,
    importHistory,
    clearHistory,
    updateConfig,
    createParallelSession,
    switchToSession,
    deleteSession,
  };
});
