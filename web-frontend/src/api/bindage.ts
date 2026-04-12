/**
 * 图表联动模块 API
 */

// ==================== 类型定义 ====================

/** 联动类型 */
export type LinkageType = 'filter' | 'highlight' | 'drill-down' | 'sync-zoom' | 'sync-selection';

/** 触发条件 */
export type TriggerType = 'click' | 'hover' | 'select' | 'brush' | 'zoom';

/** 联动目标类型 */
export type TargetType = 'specific' | 'all' | 'group';

/** 联动方向 */
export type LinkageDirection = 'one-way' | 'two-way';

/** 联动条件操作符 */
export type ConditionOperator = 'equals' | 'contains' | 'greater' | 'less' | 'between' | 'in';

/** 联动条件 */
export interface LinkageCondition {
  field: string;
  operator: ConditionOperator;
  value: unknown;
  enabled: boolean;
}

/** 联动规则 */
export interface LinkageRule {
  id: string;
  name: string;
  enabled: boolean;
  sourceComponentId: string;
  sourceField?: string;
  targetType: TargetType;
  targetComponentIds: string[];
  targetGroup?: string;
  linkageType: LinkageType;
  triggerType: TriggerType;
  direction: LinkageDirection;
  conditions: LinkageCondition[];
  transform?: string; // 数据转换表达式
  delay?: number; // 延迟触发(ms)
  priority: number; // 优先级
  chainRules?: string[]; // 链式联动的后续规则ID
}

/** 联动事件 */
export interface LinkageEvent {
  id: string;
  ruleId: string;
  sourceComponentId: string;
  triggerType: TriggerType;
  timestamp: number;
  data: unknown;
  affectedComponents: string[];
}

/** 联动状态 */
export interface LinkageState {
  activeRules: string[];
  currentFilters: Record<string, unknown>;
  highlightedData: Record<string, unknown[]>;
  selectedData: Record<string, unknown[]>;
  zoomRange: { start: unknown; end: unknown } | null;
  drillPath: { componentId: string; level: number; data: unknown }[];
}

/** 联动历史记录 */
export interface LinkageHistory {
  id: string;
  event: LinkageEvent;
  previousState: LinkageState;
  newState: LinkageState;
  timestamp: number;
}

/** 联动组 */
export interface LinkageGroup {
  id: string;
  name: string;
  componentIds: string[];
  color: string;
}

/** 联动配置 */
export interface LinkageConfig {
  rules: LinkageRule[];
  groups: LinkageGroup[];
  globalEnabled: boolean;
  maxHistorySize: number;
  defaultDelay: number;
}

// ==================== 默认配置 ====================

export const defaultLinkageConfig: LinkageConfig = {
  rules: [],
  groups: [],
  globalEnabled: true,
  maxHistorySize: 50,
  defaultDelay: 0,
};

export const defaultLinkageState: LinkageState = {
  activeRules: [],
  currentFilters: {},
  highlightedData: {},
  selectedData: {},
  zoomRange: null,
  drillPath: [],
};

// ==================== 工具函数 ====================

/**
 * 生成唯一ID
 */
export function generateLinkageId(): string {
  return `linkage-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * 创建默认联动规则
 */
export function createDefaultRule(sourceComponentId: string): LinkageRule {
  return {
    id: generateLinkageId(),
    name: '新建联动规则',
    enabled: true,
    sourceComponentId,
    targetType: 'all',
    targetComponentIds: [],
    linkageType: 'filter',
    triggerType: 'click',
    direction: 'one-way',
    conditions: [],
    priority: 0,
  };
}

/**
 * 评估联动条件
 */
export function evaluateCondition(condition: LinkageCondition, data: Record<string, unknown>): boolean {
  if (!condition.enabled) return true;
  
  const fieldValue = data[condition.field];
  
  switch (condition.operator) {
    case 'equals':
      return fieldValue === condition.value;
    case 'contains':
      return String(fieldValue).includes(String(condition.value));
    case 'greater':
      return fieldValue > condition.value;
    case 'less':
      return fieldValue < condition.value;
    case 'between':
      return fieldValue >= condition.value[0] && fieldValue <= condition.value[1];
    case 'in':
      return Array.isArray(condition.value) && condition.value.includes(fieldValue);
    default:
      return true;
  }
}

/**
 * 评估所有条件
 */
export function evaluateConditions(conditions: LinkageCondition[], data: Record<string, unknown>): boolean {
  if (conditions.length === 0) return true;
  return conditions.every(c => evaluateCondition(c, data));
}

/**
 * 应用数据转换
 */
export function applyTransform(data: unknown, transform?: string): unknown {
  if (!transform) return data;
  
  try {
    // 简单的转换表达式解析
    // 支持: value, value.field, value * 2, etc.
    const fn = new Function('value', `return ${transform}`);
    return fn(data);
  } catch {
    return data;
  }
}

/**
 * 获取联动类型的显示名称
 */
export function getLinkageTypeName(type: LinkageType): string {
  const names: Record<LinkageType, string> = {
    'filter': '数据筛选',
    'highlight': '高亮显示',
    'drill-down': '下钻分析',
    'sync-zoom': '同步缩放',
    'sync-selection': '同步选择',
  };
  return names[type] || type;
}

/**
 * 获取触发类型的显示名称
 */
export function getTriggerTypeName(type: TriggerType): string {
  const names: Record<TriggerType, string> = {
    'click': '点击',
    'hover': '悬停',
    'select': '选择',
    'brush': '框选',
    'zoom': '缩放',
  };
  return names[type] || type;
}

/**
 * 获取联动方向的显示名称
 */
export function getDirectionName(direction: LinkageDirection): string {
  const names: Record<LinkageDirection, string> = {
    'one-way': '单向联动',
    'two-way': '双向联动',
  };
  return names[direction] || direction;
}

// ==================== 联动类型图标 ====================

export const linkageTypeIcons: Record<LinkageType, string> = {
  'filter': 'Filter',
  'highlight': 'Sunny',
  'drill-down': 'Bottom',
  'sync-zoom': 'FullScreen',
  'sync-selection': 'Select',
};

export const triggerTypeIcons: Record<TriggerType, string> = {
  'click': 'Pointer',
  'hover': 'View',
  'select': 'Select',
  'brush': 'Edit',
  'zoom': 'ZoomIn',
};
