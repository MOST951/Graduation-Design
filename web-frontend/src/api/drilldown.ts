/**
 * 数据下钻 API
 */

// ==================== 类型定义 ====================

/** 下钻维度 */
export type DrillDimension = 'time' | 'region' | 'userType' | 'user' | 'topic' | 'sentiment' | 'custom';

/** 下钻条件操作符 */
export type ConditionOperator = 'equals' | 'contains' | 'greater' | 'less' | 'between' | 'in';

/** 下钻条件 */
export interface DrillCondition {
  field: string;
  operator: ConditionOperator;
  value: unknown;
}

/** 下钻级别配置 */
export interface DrillLevel {
  id: string;
  name: string;
  dimension: DrillDimension;
  order: number;
  conditions?: DrillCondition[];
  dataSource?: string;
  chartType?: string;
  aggregation?: 'sum' | 'avg' | 'count' | 'max' | 'min';
  groupBy?: string[];
}

/** 下钻路径配置 */
export interface DrillPath {
  id: string;
  name: string;
  description?: string;
  levels: DrillLevel[];
  isDefault?: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 下钻节点 */
export interface DrillNode {
  id: string;
  levelId: string;
  dimension: DrillDimension;
  label: string;
  value: unknown;
  data: unknown;
  parentId?: string;
  children?: DrillNode[];
  metadata?: Record<string, unknown>;
}

/** 下钻状态 */
export interface DrillState {
  pathId: string;
  currentLevel: number;
  nodes: DrillNode[];
  filters: Record<string, unknown>;
  timestamp: number;
}

/** 下钻历史记录 */
export interface DrillHistory {
  id: string;
  pathId: string;
  states: DrillState[];
  createdAt: string;
  title?: string;
  description?: string;
}

/** 下钻分析结果 */
export interface DrillAnalysis {
  currentLevel: {
    summary: {
      total: number;
      average: number;
      max: number;
      min: number;
      median: number;
    };
    distribution: Array<{ label: string; value: number; percentage: number }>;
    topItems: Array<{ label: string; value: number; rank: number }>;
  };
  comparison?: {
    parentLevel: {
      value: number;
      label: string;
    };
    change: {
      absolute: number;
      percentage: number;
      trend: 'up' | 'down' | 'stable';
    };
  };
  anomalies: Array<{
    label: string;
    value: number;
    expectedValue: number;
    deviation: number;
    severity: 'low' | 'medium' | 'high';
  }>;
  insights: string[];
}

/** 下钻配置 */
export interface DrillDownConfig {
  enableCrossDrill: boolean;
  enableParallelDrill: boolean;
  maxHistorySize: number;
  autoSaveHistory: boolean;
  showBreadcrumb: boolean;
  showAnalysis: boolean;
}

// ==================== 默认配置 ====================

export const defaultDrillConfig: DrillDownConfig = {
  enableCrossDrill: true,
  enableParallelDrill: false,
  maxHistorySize: 50,
  autoSaveHistory: true,
  showBreadcrumb: true,
  showAnalysis: true,
};

// ==================== 预定义下钻路径 ====================

/** 时间下钻路径 */
export const timeHierarchyPath: DrillPath = {
  id: 'time-hierarchy',
  name: '时间层级下钻',
  description: '年→季度→月→周→日→小时',
  isDefault: true,
  levels: [
    {
      id: 'year',
      name: '年',
      dimension: 'time',
      order: 0,
      groupBy: ['year'],
      aggregation: 'sum',
    },
    {
      id: 'quarter',
      name: '季度',
      dimension: 'time',
      order: 1,
      groupBy: ['year', 'quarter'],
      aggregation: 'sum',
    },
    {
      id: 'month',
      name: '月',
      dimension: 'time',
      order: 2,
      groupBy: ['year', 'month'],
      aggregation: 'sum',
    },
    {
      id: 'week',
      name: '周',
      dimension: 'time',
      order: 3,
      groupBy: ['year', 'week'],
      aggregation: 'sum',
    },
    {
      id: 'day',
      name: '日',
      dimension: 'time',
      order: 4,
      groupBy: ['year', 'month', 'day'],
      aggregation: 'sum',
    },
    {
      id: 'hour',
      name: '小时',
      dimension: 'time',
      order: 5,
      groupBy: ['year', 'month', 'day', 'hour'],
      aggregation: 'sum',
    },
  ],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 地域下钻路径 */
export const regionHierarchyPath: DrillPath = {
  id: 'region-hierarchy',
  name: '地域层级下钻',
  description: '国家→省份→城市→区县',
  isDefault: true,
  levels: [
    {
      id: 'country',
      name: '国家',
      dimension: 'region',
      order: 0,
      groupBy: ['country'],
      aggregation: 'sum',
    },
    {
      id: 'province',
      name: '省份',
      dimension: 'region',
      order: 1,
      groupBy: ['country', 'province'],
      aggregation: 'sum',
    },
    {
      id: 'city',
      name: '城市',
      dimension: 'region',
      order: 2,
      groupBy: ['country', 'province', 'city'],
      aggregation: 'sum',
    },
    {
      id: 'district',
      name: '区县',
      dimension: 'region',
      order: 3,
      groupBy: ['country', 'province', 'city', 'district'],
      aggregation: 'sum',
    },
  ],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 用户下钻路径 */
export const userHierarchyPath: DrillPath = {
  id: 'user-hierarchy',
  name: '用户层级下钻',
  description: '用户类型→用户分组→具体用户',
  isDefault: true,
  levels: [
    {
      id: 'userType',
      name: '用户类型',
      dimension: 'userType',
      order: 0,
      groupBy: ['userType'],
      aggregation: 'count',
    },
    {
      id: 'userGroup',
      name: '用户分组',
      dimension: 'userType',
      order: 1,
      groupBy: ['userType', 'userGroup'],
      aggregation: 'count',
    },
    {
      id: 'user',
      name: '具体用户',
      dimension: 'user',
      order: 2,
      groupBy: ['userId'],
      aggregation: 'count',
    },
  ],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 综合下钻路径 */
export const comprehensivePath: DrillPath = {
  id: 'comprehensive',
  name: '综合下钻',
  description: '时间→地域→用户类型→具体用户',
  levels: [
    {
      id: 'time',
      name: '时间',
      dimension: 'time',
      order: 0,
      groupBy: ['year', 'month'],
      aggregation: 'sum',
    },
    {
      id: 'region',
      name: '地域',
      dimension: 'region',
      order: 1,
      groupBy: ['province'],
      aggregation: 'sum',
    },
    {
      id: 'userType',
      name: '用户类型',
      dimension: 'userType',
      order: 2,
      groupBy: ['userType'],
      aggregation: 'count',
    },
    {
      id: 'user',
      name: '具体用户',
      dimension: 'user',
      order: 3,
      groupBy: ['userId'],
      aggregation: 'count',
    },
  ],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const builtInPaths: DrillPath[] = [
  timeHierarchyPath,
  regionHierarchyPath,
  userHierarchyPath,
  comprehensivePath,
];

// ==================== 工具函数 ====================

/**
 * 生成下钻ID
 */
export function generateDrillId(): string {
  return `drill-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * 创建下钻节点
 */
export function createDrillNode(
  levelId: string,
  dimension: DrillDimension,
  label: string,
  value: unknown,
  data: unknown,
  parentId?: string
): DrillNode {
  return {
    id: generateDrillId(),
    levelId,
    dimension,
    label,
    value,
    data,
    parentId,
    metadata: {
      timestamp: Date.now(),
    },
  };
}

/**
 * 计算数据摘要
 */
export function calculateSummary(data: number[]): {
  total: number;
  average: number;
  max: number;
  min: number;
  median: number;
} {
  if (data.length === 0) {
    return { total: 0, average: 0, max: 0, min: 0, median: 0 };
  }
  
  const sorted = [...data].sort((a, b) => a - b);
  const total = data.reduce((sum, val) => sum + val, 0);
  const average = total / data.length;
  const max = sorted[sorted.length - 1];
  const min = sorted[0];
  const median = sorted.length % 2 === 0
    ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
    : sorted[Math.floor(sorted.length / 2)];
  
  return { total, average, max, min, median };
}

/**
 * 检测异常值（使用IQR方法）
 */
export function detectAnomalies(
  data: Array<{ label: string; value: number }>,
  sensitivity: number = 1.5
): Array<{
  label: string;
  value: number;
  expectedValue: number;
  deviation: number;
  severity: 'low' | 'medium' | 'high';
}> {
  if (data.length < 4) return [];
  
  const values = data.map(d => d.value).sort((a, b) => a - b);
  const q1Index = Math.floor(values.length * 0.25);
  const q3Index = Math.floor(values.length * 0.75);
  const q1 = values[q1Index];
  const q3 = values[q3Index];
  const iqr = q3 - q1;
  
  const lowerBound = q1 - sensitivity * iqr;
  const upperBound = q3 + sensitivity * iqr;
  
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  
  return data
    .filter(d => d.value < lowerBound || d.value > upperBound)
    .map(d => {
      const deviation = Math.abs(d.value - mean);
      const deviationPercent = (deviation / mean) * 100;
      
      let severity: 'low' | 'medium' | 'high' = 'low';
      if (deviationPercent > 100) severity = 'high';
      else if (deviationPercent > 50) severity = 'medium';
      
      return {
        label: d.label,
        value: d.value,
        expectedValue: mean,
        deviation,
        severity,
      };
    });
}

/**
 * 计算变化趋势
 */
export function calculateTrend(
  currentValue: number,
  previousValue: number,
  threshold: number = 5
): 'up' | 'down' | 'stable' {
  const changePercent = ((currentValue - previousValue) / previousValue) * 100;
  
  if (Math.abs(changePercent) < threshold) return 'stable';
  return changePercent > 0 ? 'up' : 'down';
}

/**
 * 生成数据洞察
 */
export function generateInsights(analysis: DrillAnalysis): string[] {
  const insights: string[] = [];
  
  // 总量洞察
  if (analysis.currentLevel.summary.total > 0) {
    insights.push(`当前层级共有 ${analysis.currentLevel.summary.total.toLocaleString()} 条数据`);
  }
  
  // 对比洞察
  if (analysis.comparison) {
    const { change } = analysis.comparison;
    if (change.trend === 'up') {
      insights.push(`相比上级增长 ${change.percentage.toFixed(1)}%`);
    } else if (change.trend === 'down') {
      insights.push(`相比上级下降 ${Math.abs(change.percentage).toFixed(1)}%`);
    }
  }
  
  // 异常洞察
  if (analysis.anomalies.length > 0) {
    const highSeverity = analysis.anomalies.filter(a => a.severity === 'high').length;
    if (highSeverity > 0) {
      insights.push(`发现 ${highSeverity} 个高度异常数据点`);
    }
  }
  
  // Top项洞察
  if (analysis.currentLevel.topItems.length > 0) {
    const top = analysis.currentLevel.topItems[0];
    insights.push(`${top.label} 占比最高，达到 ${((top.value / analysis.currentLevel.summary.total) * 100).toFixed(1)}%`);
  }
  
  return insights;
}

/**
 * 构建下钻过滤器
 */
export function buildDrillFilters(nodes: DrillNode[]): Record<string, unknown> {
  const filters: Record<string, unknown> = {};
  
  nodes.forEach(node => {
    const key = `${node.dimension}_${node.levelId}`;
    filters[key] = node.value;
  });
  
  return filters;
}

/**
 * 验证下钻条件
 */
export function validateDrillCondition(condition: DrillCondition, data: Record<string, unknown>): boolean {
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
 * 获取下钻路径描述
 */
export function getPathDescription(path: DrillPath): string {
  const levelNames = path.levels.map(l => l.name).join(' → ');
  return `${path.name}: ${levelNames}`;
}

/**
 * 导出下钻历史
 */
export function exportDrillHistory(history: DrillHistory): Blob {
  const json = JSON.stringify(history, null, 2);
  return new Blob([json], { type: 'application/json' });
}

/**
 * 导入下钻历史
 */
export function importDrillHistory(json: string): DrillHistory {
  return JSON.parse(json) as DrillHistory;
}

/**
 * 格式化下钻路径
 */
export function formatDrillPath(nodes: DrillNode[]): string {
  return nodes.map(n => n.label).join(' > ');
}

/**
 * 获取维度显示名称
 */
export function getDimensionName(dimension: DrillDimension): string {
  const names: Record<DrillDimension, string> = {
    time: '时间',
    region: '地域',
    userType: '用户类型',
    user: '用户',
    topic: '话题',
    sentiment: '情感',
    custom: '自定义',
  };
  return names[dimension] || dimension;
}

/**
 * 获取聚合方式显示名称
 */
export function getAggregationName(aggregation: string): string {
  const names: Record<string, string> = {
    sum: '求和',
    avg: '平均',
    count: '计数',
    max: '最大值',
    min: '最小值',
  };
  return names[aggregation] || aggregation;
}
