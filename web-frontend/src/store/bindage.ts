/**
 * 图表联动 Store
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  type LinkageRule,
  type LinkageEvent,
  type LinkageState,
  type LinkageHistory,
  type LinkageGroup,
  type LinkageConfig,
  type LinkageType,
  type TriggerType,
  defaultLinkageConfig,
  defaultLinkageState,
  generateLinkageId,
  createDefaultRule,
  evaluateConditions,
  applyTransform,
} from '@/api/bindage';

// 深拷贝
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

export const useLinkageStore = defineStore('bindage', () => {
  // ==================== State ====================
  
  /** 联动配置 */
  const config = ref<LinkageConfig>(deepClone(defaultLinkageConfig));
  
  /** 当前联动状态 */
  const state = ref<LinkageState>(deepClone(defaultLinkageState));
  
  /** 联动历史记录 */
  const history = ref<LinkageHistory[]>([]);
  
  /** 历史记录索引 */
  const historyIndex = ref(-1);
  
  /** 临时禁用的规则 */
  const temporarilyDisabledRules = ref<Set<string>>(new Set());
  
  /** 正在预览的规则 */
  const previewingRule = ref<LinkageRule | null>(null);
  
  /** 联动事件队列 */
  const eventQueue = ref<LinkageEvent[]>([]);
  
  /** 是否正在处理事件 */
  const isProcessing = ref(false);
  
  /** 事件监听器 */
  const eventListeners = ref<Map<string, ((event: LinkageEvent) => void)[]>>(new Map());
  
  // ==================== Getters ====================
  
  /** 所有规则 */
  const rules = computed(() => config.value.rules);
  
  /** 启用的规则 */
  const enabledRules = computed(() => 
    config.value.rules.filter(r => 
      r.enabled && 
      config.value.globalEnabled && 
      !temporarilyDisabledRules.value.has(r.id)
    )
  );
  
  /** 所有联动组 */
  const groups = computed(() => config.value.groups);
  
  /** 按源组件分组的规则 */
  const rulesBySource = computed(() => {
    const map = new Map<string, LinkageRule[]>();
    config.value.rules.forEach(rule => {
      const list = map.get(rule.sourceComponentId) || [];
      list.push(rule);
      map.set(rule.sourceComponentId, list);
    });
    return map;
  });
  
  /** 按目标组件分组的规则 */
  const rulesByTarget = computed(() => {
    const map = new Map<string, LinkageRule[]>();
    config.value.rules.forEach(rule => {
      if (rule.targetType === 'specific') {
        rule.targetComponentIds.forEach(targetId => {
          const list = map.get(targetId) || [];
          list.push(rule);
          map.set(targetId, list);
        });
      }
    });
    return map;
  });
  
  /** 当前活跃的筛选器 */
  const activeFilters = computed(() => state.value.currentFilters);
  
  /** 当前高亮的数据 */
  const highlightedData = computed(() => state.value.highlightedData);
  
  /** 当前选中的数据 */
  const selectedData = computed(() => state.value.selectedData);
  
  /** 下钻路径 */
  const drillPath = computed(() => state.value.drillPath);
  
  /** 是否可以撤销 */
  const canUndo = computed(() => historyIndex.value > 0);
  
  /** 是否可以重做 */
  const canRedo = computed(() => historyIndex.value < history.value.length - 1);
  
  // ==================== Actions ====================
  
  /**
   * 添加联动规则
   */
  function addRule(sourceComponentId: string): LinkageRule {
    const rule = createDefaultRule(sourceComponentId);
    config.value.rules.push(rule);
    return rule;
  }
  
  /**
   * 更新联动规则
   */
  function updateRule(ruleId: string, updates: Partial<LinkageRule>) {
    const index = config.value.rules.findIndex(r => r.id === ruleId);
    if (index !== -1) {
      config.value.rules[index] = { ...config.value.rules[index], ...updates };
    }
  }
  
  /**
   * 删除联动规则
   */
  function removeRule(ruleId: string) {
    config.value.rules = config.value.rules.filter(r => r.id !== ruleId);
    // 同时删除链式联动中的引用
    config.value.rules.forEach(rule => {
      if (rule.chainRules) {
        rule.chainRules = rule.chainRules.filter(id => id !== ruleId);
      }
    });
  }
  
  /**
   * 复制联动规则
   */
  function duplicateRule(ruleId: string): LinkageRule | null {
    const rule = config.value.rules.find(r => r.id === ruleId);
    if (!rule) return null;
    
    const newRule: LinkageRule = {
      ...deepClone(rule),
      id: generateLinkageId(),
      name: `${rule.name} (副本)`,
    };
    config.value.rules.push(newRule);
    return newRule;
  }
  
  /**
   * 启用/禁用规则
   */
  function toggleRule(ruleId: string) {
    const rule = config.value.rules.find(r => r.id === ruleId);
    if (rule) {
      rule.enabled = !rule.enabled;
    }
  }
  
  /**
   * 临时禁用规则
   */
  function temporarilyDisableRule(ruleId: string) {
    temporarilyDisabledRules.value.add(ruleId);
  }
  
  /**
   * 恢复临时禁用的规则
   */
  function restoreTemporarilyDisabledRule(ruleId: string) {
    temporarilyDisabledRules.value.delete(ruleId);
  }
  
  /**
   * 恢复所有临时禁用的规则
   */
  function restoreAllTemporarilyDisabled() {
    temporarilyDisabledRules.value.clear();
  }
  
  /**
   * 添加联动组
   */
  function addGroup(name: string, componentIds: string[] = []): LinkageGroup {
    const group: LinkageGroup = {
      id: generateLinkageId(),
      name,
      componentIds,
      color: `hsl(${Math.random() * 360}, 70%, 50%)`,
    };
    config.value.groups.push(group);
    return group;
  }
  
  /**
   * 更新联动组
   */
  function updateGroup(groupId: string, updates: Partial<LinkageGroup>) {
    const index = config.value.groups.findIndex(g => g.id === groupId);
    if (index !== -1) {
      config.value.groups[index] = { ...config.value.groups[index], ...updates };
    }
  }
  
  /**
   * 删除联动组
   */
  function removeGroup(groupId: string) {
    config.value.groups = config.value.groups.filter(g => g.id !== groupId);
  }
  
  /**
   * 触发联动事件
   */
  function triggerLinkage(
    sourceComponentId: string,
    triggerType: TriggerType,
    data: any
  ) {
    if (!config.value.globalEnabled) return;
    
    // 查找匹配的规则
    const matchingRules = enabledRules.value.filter(rule => 
      rule.sourceComponentId === sourceComponentId &&
      rule.triggerType === triggerType &&
      evaluateConditions(rule.conditions, data)
    );
    
    if (matchingRules.length === 0) return;
    
    // 按优先级排序
    matchingRules.sort((a, b) => b.priority - a.priority);
    
    // 创建事件
    matchingRules.forEach(rule => {
      const event: LinkageEvent = {
        id: generateLinkageId(),
        ruleId: rule.id,
        sourceComponentId,
        triggerType,
        timestamp: Date.now(),
        data: applyTransform(data, rule.transform),
        affectedComponents: getAffectedComponents(rule),
      };
      
      // 添加到事件队列
      if (rule.delay && rule.delay > 0) {
        setTimeout(() => processEvent(event, rule), rule.delay);
      } else {
        processEvent(event, rule);
      }
    });
  }
  
  /**
   * 获取受影响的组件
   */
  function getAffectedComponents(rule: LinkageRule): string[] {
    switch (rule.targetType) {
      case 'specific':
        return rule.targetComponentIds;
      case 'group':
        const group = config.value.groups.find(g => g.id === rule.targetGroup);
        return group?.componentIds || [];
      case 'all':
        // 返回所有组件ID（需要从外部获取）
        return [];
      default:
        return [];
    }
  }
  
  /**
   * 处理联动事件
   */
  function processEvent(event: LinkageEvent, rule: LinkageRule) {
    const previousState = deepClone(state.value);
    
    // 根据联动类型处理
    switch (rule.linkageType) {
      case 'filter':
        applyFilter(event, rule);
        break;
      case 'highlight':
        applyHighlight(event, rule);
        break;
      case 'drill-down':
        applyDrillDown(event, rule);
        break;
      case 'sync-zoom':
        applySyncZoom(event, rule);
        break;
      case 'sync-selection':
        applySyncSelection(event, rule);
        break;
    }
    
    // 记录历史
    saveHistory(event, previousState);
    
    // 通知监听器
    notifyListeners(event);
    
    // 处理链式联动
    if (rule.chainRules && rule.chainRules.length > 0) {
      rule.chainRules.forEach(chainRuleId => {
        const chainRule = config.value.rules.find(r => r.id === chainRuleId);
        if (chainRule && chainRule.enabled) {
          const chainEvent: LinkageEvent = {
            id: generateLinkageId(),
            ruleId: chainRule.id,
            sourceComponentId: event.sourceComponentId,
            triggerType: event.triggerType,
            timestamp: Date.now(),
            data: event.data,
            affectedComponents: getAffectedComponents(chainRule),
          };
          processEvent(chainEvent, chainRule);
        }
      });
    }
    
    // 处理双向联动
    if (rule.direction === 'two-way') {
      // 反向触发
      event.affectedComponents.forEach(targetId => {
        const reverseRules = enabledRules.value.filter(r =>
          r.sourceComponentId === targetId &&
          r.targetComponentIds.includes(rule.sourceComponentId) &&
          r.direction === 'two-way'
        );
        // 避免无限循环，不再处理反向规则
      });
    }
  }
  
  /**
   * 应用筛选联动
   */
  function applyFilter(event: LinkageEvent, rule: LinkageRule) {
    const filterKey = `${rule.id}_${rule.sourceField || 'default'}`;
    state.value.currentFilters[filterKey] = {
      ruleId: rule.id,
      sourceComponentId: event.sourceComponentId,
      field: rule.sourceField,
      value: event.data,
      affectedComponents: event.affectedComponents,
    };
    state.value.activeRules = [...new Set([...state.value.activeRules, rule.id])];
  }
  
  /**
   * 应用高亮联动
   */
  function applyHighlight(event: LinkageEvent, rule: LinkageRule) {
    event.affectedComponents.forEach(componentId => {
      state.value.highlightedData[componentId] = [event.data];
    });
    state.value.activeRules = [...new Set([...state.value.activeRules, rule.id])];
  }
  
  /**
   * 应用下钻联动
   */
  function applyDrillDown(event: LinkageEvent, rule: LinkageRule) {
    const currentLevel = state.value.drillPath.length;
    state.value.drillPath.push({
      componentId: event.sourceComponentId,
      level: currentLevel + 1,
      data: event.data,
    });
    state.value.activeRules = [...new Set([...state.value.activeRules, rule.id])];
  }
  
  /**
   * 应用同步缩放联动
   */
  function applySyncZoom(event: LinkageEvent, rule: LinkageRule) {
    state.value.zoomRange = {
      start: event.data.start,
      end: event.data.end,
    };
    state.value.activeRules = [...new Set([...state.value.activeRules, rule.id])];
  }
  
  /**
   * 应用同步选择联动
   */
  function applySyncSelection(event: LinkageEvent, rule: LinkageRule) {
    event.affectedComponents.forEach(componentId => {
      state.value.selectedData[componentId] = Array.isArray(event.data) 
        ? event.data 
        : [event.data];
    });
    state.value.activeRules = [...new Set([...state.value.activeRules, rule.id])];
  }
  
  /**
   * 清除筛选
   */
  function clearFilter(filterKey?: string) {
    if (filterKey) {
      delete state.value.currentFilters[filterKey];
    } else {
      state.value.currentFilters = {};
    }
  }
  
  /**
   * 清除高亮
   */
  function clearHighlight(componentId?: string) {
    if (componentId) {
      delete state.value.highlightedData[componentId];
    } else {
      state.value.highlightedData = {};
    }
  }
  
  /**
   * 清除选择
   */
  function clearSelection(componentId?: string) {
    if (componentId) {
      delete state.value.selectedData[componentId];
    } else {
      state.value.selectedData = {};
    }
  }
  
  /**
   * 返回上一级下钻
   */
  function drillUp() {
    if (state.value.drillPath.length > 0) {
      state.value.drillPath.pop();
    }
  }
  
  /**
   * 重置下钻
   */
  function resetDrill() {
    state.value.drillPath = [];
  }
  
  /**
   * 重置所有联动状态
   */
  function resetState() {
    state.value = deepClone(defaultLinkageState);
  }
  
  /**
   * 保存历史记录
   */
  function saveHistory(event: LinkageEvent, previousState: LinkageState) {
    // 删除当前索引之后的历史
    if (historyIndex.value < history.value.length - 1) {
      history.value = history.value.slice(0, historyIndex.value + 1);
    }
    
    const historyItem: LinkageHistory = {
      id: generateLinkageId(),
      event,
      previousState,
      newState: deepClone(state.value),
      timestamp: Date.now(),
    };
    
    history.value.push(historyItem);
    
    // 限制历史记录数量
    if (history.value.length > config.value.maxHistorySize) {
      history.value.shift();
    } else {
      historyIndex.value++;
    }
  }
  
  /**
   * 撤销
   */
  function undo() {
    if (!canUndo.value) return;
    
    historyIndex.value--;
    state.value = deepClone(history.value[historyIndex.value].previousState);
  }
  
  /**
   * 重做
   */
  function redo() {
    if (!canRedo.value) return;
    
    historyIndex.value++;
    state.value = deepClone(history.value[historyIndex.value].newState);
  }
  
  /**
   * 添加事件监听器
   */
  function addEventListener(componentId: string, callback: (event: LinkageEvent) => void) {
    const listeners = eventListeners.value.get(componentId) || [];
    listeners.push(callback);
    eventListeners.value.set(componentId, listeners);
  }
  
  /**
   * 移除事件监听器
   */
  function removeEventListener(componentId: string, callback: (event: LinkageEvent) => void) {
    const listeners = eventListeners.value.get(componentId) || [];
    const index = listeners.indexOf(callback);
    if (index !== -1) {
      listeners.splice(index, 1);
      eventListeners.value.set(componentId, listeners);
    }
  }
  
  /**
   * 通知监听器
   */
  function notifyListeners(event: LinkageEvent) {
    event.affectedComponents.forEach(componentId => {
      const listeners = eventListeners.value.get(componentId) || [];
      listeners.forEach(callback => callback(event));
    });
    
    // 通知全局监听器
    const globalListeners = eventListeners.value.get('*') || [];
    globalListeners.forEach(callback => callback(event));
  }
  
  /**
   * 开始预览规则
   */
  function startPreview(rule: LinkageRule) {
    previewingRule.value = rule;
  }
  
  /**
   * 停止预览规则
   */
  function stopPreview() {
    previewingRule.value = null;
  }
  
  /**
   * 获取组件的联动关系
   */
  function getComponentLinkages(componentId: string) {
    const asSource = config.value.rules.filter(r => r.sourceComponentId === componentId);
    const asTarget = config.value.rules.filter(r => 
      r.targetType === 'specific' && r.targetComponentIds.includes(componentId)
    );
    const inGroups = config.value.groups.filter(g => g.componentIds.includes(componentId));
    
    return { asSource, asTarget, inGroups };
  }
  
  /**
   * 导出配置
   */
  function exportConfig(): string {
    return JSON.stringify(config.value, null, 2);
  }
  
  /**
   * 导入配置
   */
  function importConfig(jsonString: string) {
    try {
      const imported = JSON.parse(jsonString) as LinkageConfig;
      config.value = imported;
    } catch (error) {
      console.error('导入配置失败:', error);
      throw new Error('无效的配置格式');
    }
  }
  
  /**
   * 重置配置
   */
  function resetConfig() {
    config.value = deepClone(defaultLinkageConfig);
    resetState();
    history.value = [];
    historyIndex.value = -1;
  }
  
  /**
   * 设置全局启用状态
   */
  function setGlobalEnabled(enabled: boolean) {
    config.value.globalEnabled = enabled;
    if (!enabled) {
      resetState();
    }
  }

  return {
    // State
    config,
    state,
    history,
    historyIndex,
    temporarilyDisabledRules,
    previewingRule,
    eventQueue,
    isProcessing,
    
    // Getters
    rules,
    enabledRules,
    groups,
    rulesBySource,
    rulesByTarget,
    activeFilters,
    highlightedData,
    selectedData,
    drillPath,
    canUndo,
    canRedo,
    
    // Actions
    addRule,
    updateRule,
    removeRule,
    duplicateRule,
    toggleRule,
    temporarilyDisableRule,
    restoreTemporarilyDisabledRule,
    restoreAllTemporarilyDisabled,
    addGroup,
    updateGroup,
    removeGroup,
    triggerLinkage,
    getAffectedComponents,
    clearFilter,
    clearHighlight,
    clearSelection,
    drillUp,
    resetDrill,
    resetState,
    undo,
    redo,
    addEventListener,
    removeEventListener,
    startPreview,
    stopPreview,
    getComponentLinkages,
    exportConfig,
    importConfig,
    resetConfig,
    setGlobalEnabled,
  };
});
