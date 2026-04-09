/**
 * 可视化模块 API
 */
import apiClient from '@/api';
import { PRIMARY, SUCCESS, WARNING, DANGER } from '@/styles/colors';

const api = apiClient;

// ==================== 类型定义 ====================

/** 组件类型 */
export type ComponentType = 
  | 'bar-chart' | 'line-chart' | 'pie-chart' | 'scatter-chart' | 'heatmap-chart' | 'map-chart' | 'radar-chart' | 'gauge-chart'
  | 'title' | 'text-box' | 'metric-card'
  | 'filter' | 'date-picker' | 'dropdown' | 'search-box'
  | 'container' | 'row-layout' | 'column-layout' | 'tabs';

/** 组件分类 */
export type ComponentCategory = 'chart' | 'text' | 'control' | 'layout';

/** 组件定义 */
export interface ComponentDefinition {
  type: ComponentType;
  category: ComponentCategory;
  name: string;
  icon: string;
  description: string;
  defaultWidth: number;
  defaultHeight: number;
  minWidth: number;
  minHeight: number;
  defaultProps: Record<string, any>;
}

/** 画布组件实例 */
export interface CanvasComponent {
  id: string;
  type: ComponentType;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
  locked: boolean;
  visible: boolean;
  props: Record<string, any>;
  dataBinding?: DataBinding;
  styles: ComponentStyles;
  animations?: AnimationConfig;
  events?: EventConfig[];
}

/** 数据绑定配置 */
export interface DataBinding {
  sourceType: 'api' | 'static' | 'variable';
  source: string;
  refreshInterval?: number;
  params?: Record<string, any>;
  transform?: string;
}

/** 组件样式 */
export interface ComponentStyles {
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;
  borderRadius?: number;
  borderStyle?: 'solid' | 'dashed' | 'dotted' | 'none';
  padding?: number | [number, number, number, number];
  margin?: number | [number, number, number, number];
  boxShadow?: string;
  opacity?: number;
  fontFamily?: string;
  fontSize?: number;
  fontWeight?: string;
  color?: string;
  textAlign?: 'left' | 'center' | 'right';
}

/** 动画配置 */
export interface AnimationConfig {
  enabled: boolean;
  type: 'fade' | 'slide' | 'scale' | 'bounce';
  duration: number;
  delay: number;
  easing: string;
}

/** 事件配置 */
export interface EventConfig {
  trigger: 'click' | 'hover' | 'change' | 'load';
  action: 'navigate' | 'filter' | 'refresh' | 'custom';
  target?: string;
  params?: Record<string, any>;
}

/** 布局配置 */
export interface LayoutConfig {
  id: string;
  name: string;
  description?: string;
  thumbnail?: string;
  canvasWidth: number;
  canvasHeight: number;
  gridSize: number;
  snapToGrid: boolean;
  showGrid: boolean;
  backgroundColor: string;
  components: CanvasComponent[];
  createdAt: string;
  updatedAt: string;
  isTemplate?: boolean;
}

/** 历史记录项 */
export interface HistoryItem {
  id: string;
  action: 'add' | 'remove' | 'update' | 'move' | 'resize' | 'batch';
  timestamp: number;
  components: CanvasComponent[];
  description: string;
}

// ==================== 组件库定义 ====================

export const componentLibrary: ComponentDefinition[] = [
  // 图表组件
  {
    type: 'bar-chart',
    category: 'chart',
    name: '柱状图',
    icon: 'Histogram',
    description: '用于展示分类数据的对比',
    defaultWidth: 400,
    defaultHeight: 300,
    minWidth: 200,
    minHeight: 150,
    defaultProps: {
      title: '柱状图',
      xAxisData: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      seriesData: [120, 200, 150, 80, 70, 110, 130],
      showLegend: true,
      colorScheme: 'default',
    },
  },
  {
    type: 'line-chart',
    category: 'chart',
    name: '折线图',
    icon: 'TrendCharts',
    description: '用于展示数据随时间变化的趋势',
    defaultWidth: 400,
    defaultHeight: 300,
    minWidth: 200,
    minHeight: 150,
    defaultProps: {
      title: '折线图',
      xAxisData: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      seriesData: [820, 932, 901, 934, 1290, 1330, 1320],
      smooth: true,
      showArea: false,
      showLegend: true,
    },
  },
  {
    type: 'pie-chart',
    category: 'chart',
    name: '饼图',
    icon: 'PieChart',
    description: '用于展示数据的占比分布',
    defaultWidth: 350,
    defaultHeight: 300,
    minWidth: 200,
    minHeight: 200,
    defaultProps: {
      title: '饼图',
      data: [
        { name: '正面', value: 60 },
        { name: '负面', value: 25 },
        { name: '中性', value: 15 },
      ],
      showLabel: true,
      roseType: false,
    },
  },
  {
    type: 'scatter-chart',
    category: 'chart',
    name: '散点图',
    icon: 'Coordinate',
    description: '用于展示数据的分布和相关性',
    defaultWidth: 400,
    defaultHeight: 300,
    minWidth: 200,
    minHeight: 200,
    defaultProps: {
      title: '散点图',
      data: [[10.0, 8.04], [8.07, 6.95], [13.0, 7.58], [9.05, 8.81], [11.0, 8.33]],
      symbolSize: 10,
    },
  },
  {
    type: 'heatmap-chart',
    category: 'chart',
    name: '热力图',
    icon: 'Grid',
    description: '用于展示数据的密度分布',
    defaultWidth: 400,
    defaultHeight: 300,
    minWidth: 250,
    minHeight: 200,
    defaultProps: {
      title: '热力图',
      xAxisData: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
      yAxisData: ['Morning', 'Afternoon', 'Evening'],
      data: [[0, 0, 5], [0, 1, 1], [0, 2, 0], [1, 0, 3], [1, 1, 4]],
    },
  },
  {
    type: 'map-chart',
    category: 'chart',
    name: '地图',
    icon: 'MapLocation',
    description: '用于展示地理数据分布',
    defaultWidth: 500,
    defaultHeight: 400,
    minWidth: 300,
    minHeight: 250,
    defaultProps: {
      title: '地图',
      mapType: 'china',
      data: [
        { name: '北京', value: 100 },
        { name: '上海', value: 80 },
        { name: '广州', value: 60 },
      ],
    },
  },
  {
    type: 'radar-chart',
    category: 'chart',
    name: '雷达图',
    icon: 'Aim',
    description: '用于多维数据对比分析',
    defaultWidth: 350,
    defaultHeight: 300,
    minWidth: 200,
    minHeight: 200,
    defaultProps: {
      title: '雷达图',
      indicator: [
        { name: '销售', max: 100 },
        { name: '管理', max: 100 },
        { name: '技术', max: 100 },
        { name: '客服', max: 100 },
        { name: '研发', max: 100 },
      ],
      data: [80, 70, 90, 60, 85],
    },
  },
  {
    type: 'gauge-chart',
    category: 'chart',
    name: '仪表盘',
    icon: 'Odometer',
    description: '用于展示单一指标的完成度',
    defaultWidth: 300,
    defaultHeight: 250,
    minWidth: 150,
    minHeight: 150,
    defaultProps: {
      title: '完成率',
      value: 75,
      min: 0,
      max: 100,
      unit: '%',
    },
  },
  
  // 文本组件
  {
    type: 'title',
    category: 'text',
    name: '标题',
    icon: 'Document',
    description: '用于展示标题文字',
    defaultWidth: 300,
    defaultHeight: 60,
    minWidth: 100,
    minHeight: 40,
    defaultProps: {
      text: '标题文本',
      level: 1,
      align: 'center',
    },
  },
  {
    type: 'text-box',
    category: 'text',
    name: '文本框',
    icon: 'EditPen',
    description: '用于展示多行文本内容',
    defaultWidth: 300,
    defaultHeight: 100,
    minWidth: 100,
    minHeight: 50,
    defaultProps: {
      text: '这是一段文本内容，可以用于展示说明信息。',
      align: 'left',
    },
  },
  {
    type: 'metric-card',
    category: 'text',
    name: '指标卡',
    icon: 'DataLine',
    description: '用于展示关键指标数据',
    defaultWidth: 200,
    defaultHeight: 120,
    minWidth: 120,
    minHeight: 80,
    defaultProps: {
      title: '总数据量',
      value: '12,345',
      unit: '条',
      trend: 12.5,
      trendLabel: '较昨日',
      icon: 'DataAnalysis',
      color: PRIMARY,
    },
  },
  
  // 控件组件
  {
    type: 'filter',
    category: 'control',
    name: '筛选器',
    icon: 'Filter',
    description: '用于数据筛选',
    defaultWidth: 250,
    defaultHeight: 50,
    minWidth: 150,
    minHeight: 40,
    defaultProps: {
      label: '筛选条件',
      options: ['选项1', '选项2', '选项3'],
      multiple: false,
      placeholder: '请选择',
    },
  },
  {
    type: 'date-picker',
    category: 'control',
    name: '日期选择器',
    icon: 'Calendar',
    description: '用于选择日期范围',
    defaultWidth: 300,
    defaultHeight: 50,
    minWidth: 200,
    minHeight: 40,
    defaultProps: {
      label: '日期范围',
      type: 'daterange',
      format: 'YYYY-MM-DD',
      placeholder: '请选择日期',
    },
  },
  {
    type: 'dropdown',
    category: 'control',
    name: '下拉框',
    icon: 'ArrowDown',
    description: '用于选择单个选项',
    defaultWidth: 200,
    defaultHeight: 50,
    minWidth: 120,
    minHeight: 40,
    defaultProps: {
      label: '选择项',
      options: [
        { label: '选项1', value: '1' },
        { label: '选项2', value: '2' },
        { label: '选项3', value: '3' },
      ],
      placeholder: '请选择',
    },
  },
  {
    type: 'search-box',
    category: 'control',
    name: '搜索框',
    icon: 'Search',
    description: '用于关键词搜索',
    defaultWidth: 250,
    defaultHeight: 50,
    minWidth: 150,
    minHeight: 40,
    defaultProps: {
      placeholder: '请输入搜索关键词',
      showButton: true,
    },
  },
  
  // 布局组件
  {
    type: 'container',
    category: 'layout',
    name: '容器',
    icon: 'Box',
    description: '用于包裹其他组件',
    defaultWidth: 400,
    defaultHeight: 300,
    minWidth: 100,
    minHeight: 100,
    defaultProps: {
      title: '',
      showBorder: true,
      showHeader: false,
    },
  },
  {
    type: 'row-layout',
    category: 'layout',
    name: '行布局',
    icon: 'More',
    description: '水平排列子组件',
    defaultWidth: 600,
    defaultHeight: 150,
    minWidth: 200,
    minHeight: 80,
    defaultProps: {
      gap: 16,
      justify: 'flex-start',
      align: 'stretch',
    },
  },
  {
    type: 'column-layout',
    category: 'layout',
    name: '列布局',
    icon: 'MoreFilled',
    description: '垂直排列子组件',
    defaultWidth: 300,
    defaultHeight: 400,
    minWidth: 150,
    minHeight: 200,
    defaultProps: {
      gap: 16,
      justify: 'flex-start',
      align: 'stretch',
    },
  },
  {
    type: 'tabs',
    category: 'layout',
    name: '标签页',
    icon: 'Menu',
    description: '多标签页切换展示',
    defaultWidth: 500,
    defaultHeight: 350,
    minWidth: 300,
    minHeight: 200,
    defaultProps: {
      tabs: [
        { label: '标签1', key: 'tab1' },
        { label: '标签2', key: 'tab2' },
      ],
      activeTab: 'tab1',
    },
  },
];

// ==================== API 函数 ====================

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// 模拟存储
let layouts: LayoutConfig[] = [];
let templates: LayoutConfig[] = [
  {
    id: 'template-1',
    name: '情感分析仪表盘',
    description: '包含情感分布、趋势图等常用图表',
    canvasWidth: 1920,
    canvasHeight: 1080,
    gridSize: 20,
    snapToGrid: true,
    showGrid: true,
    backgroundColor: '#f5f7fa',
    components: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    isTemplate: true,
  },
  {
    id: 'template-2',
    name: '实时监控大屏',
    description: '适用于大屏展示的实时数据监控',
    canvasWidth: 1920,
    canvasHeight: 1080,
    gridSize: 20,
    snapToGrid: true,
    showGrid: true,
    backgroundColor: '#0d1b2a',
    components: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    isTemplate: true,
  },
];

/**
 * 获取组件库
 */
export async function getComponentLibrary(): Promise<ComponentDefinition[]> {
  await sleep(100);
  return componentLibrary;
}

/**
 * 获取布局列表
 */
export async function getLayouts(): Promise<LayoutConfig[]> {
  await sleep(300);
  return layouts;
}

/**
 * 获取单个布局
 */
export async function getLayout(id: string): Promise<LayoutConfig | null> {
  await sleep(200);
  return layouts.find(l => l.id === id) || null;
}

/**
 * 保存布局
 */
export async function saveLayout(layout: LayoutConfig): Promise<LayoutConfig> {
  await sleep(300);
  const index = layouts.findIndex(l => l.id === layout.id);
  const now = new Date().toISOString();
  
  if (index !== -1) {
    layouts[index] = { ...layout, updatedAt: now };
    return layouts[index];
  } else {
    const newLayout = {
      ...layout,
      id: layout.id || `layout-${Date.now()}`,
      createdAt: now,
      updatedAt: now,
    };
    layouts.push(newLayout);
    return newLayout;
  }
}

/**
 * 删除布局
 */
export async function deleteLayout(id: string): Promise<void> {
  await sleep(200);
  layouts = layouts.filter(l => l.id !== id);
}

/**
 * 获取模板列表
 */
export async function getTemplates(): Promise<LayoutConfig[]> {
  await sleep(200);
  return templates;
}

/**
 * 保存为模板
 */
export async function saveAsTemplate(layout: LayoutConfig, name: string, description?: string): Promise<LayoutConfig> {
  await sleep(300);
  const template: LayoutConfig = {
    ...layout,
    id: `template-${Date.now()}`,
    name,
    description,
    isTemplate: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  templates.push(template);
  return template;
}

/**
 * 从模板创建布局
 */
export async function createFromTemplate(templateId: string): Promise<LayoutConfig> {
  await sleep(200);
  const template = templates.find(t => t.id === templateId);
  if (!template) {
    throw new Error('模板不存在');
  }
  
  const now = new Date().toISOString();
  return {
    ...template,
    id: `layout-${Date.now()}`,
    name: `${template.name} - 副本`,
    isTemplate: false,
    createdAt: now,
    updatedAt: now,
    components: template.components.map(c => ({
      ...c,
      id: `${c.id}-${Date.now()}`,
    })),
  };
}

/**
 * 导出布局为JSON
 */
export async function exportLayout(layout: LayoutConfig): Promise<Blob> {
  await sleep(100);
  const json = JSON.stringify(layout, null, 2);
  return new Blob([json], { type: 'application/json' });
}

/**
 * 导出布局为图片
 */
export async function exportAsImage(canvasElement: HTMLElement): Promise<Blob> {
  // 实际项目中使用 html2canvas 等库
  await sleep(500);
  throw new Error('需要安装 html2canvas 库');
}

/**
 * 获取数据源列表
 */
export async function getDataSources(): Promise<{ id: string; name: string; type: string }[]> {
  await sleep(200);
  return [
    { id: 'ds-1', name: '情感分析结果', type: 'api' },
    { id: 'ds-2', name: '热点话题数据', type: 'api' },
    { id: 'ds-3', name: '用户统计数据', type: 'api' },
    { id: 'ds-4', name: '实时采集数据', type: 'websocket' },
  ];
}

/**
 * 获取数据源数据
 */
export async function fetchDataSourceData(sourceId: string, params?: Record<string, any>): Promise<any> {
  await sleep(300);
  // 模拟返回数据
  return {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    values: [120, 200, 150, 80, 70, 110, 130],
  };
}

/**
 * 生成分享链接
 */
export async function generateShareLink(layoutId: string, options?: { 
  expireTime?: number; 
  password?: string;
}): Promise<{ url: string; code: string }> {
  await sleep(200);
  const code = Math.random().toString(36).substring(2, 8).toUpperCase();
  return {
    url: `${window.location.origin}/share/${layoutId}?code=${code}`,
    code,
  };
}

// ==================== 新增API函数 ====================

/**
 * 加载布局
 */
export async function loadLayout(id: string): Promise<LayoutConfig> {
  try {
    const response = await api.get<LayoutConfig>(`/layouts/${id}`);
    return response.data;
  } catch (error) {
    // 从本地存储加载
    await sleep(200);
    const stored = localStorage.getItem(`layout_${id}`);
    if (stored) {
      return JSON.parse(stored);
    }
    throw new Error('布局不存在');
  }
}

/**
 * 克隆布局
 */
export async function cloneLayout(id: string, newName?: string): Promise<LayoutConfig> {
  try {
    const response = await api.post<LayoutConfig>(`/layouts/${id}/clone`, { name: newName });
    return response.data;
  } catch (error) {
    // 模拟克隆
    await sleep(300);
    const original = await loadLayout(id);
    const now = new Date().toISOString();
    return {
      ...original,
      id: `layout-${Date.now()}`,
      name: newName || `${original.name} - 副本`,
      createdAt: now,
      updatedAt: now,
      components: original.components.map(c => ({
        ...c,
        id: `${c.type}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      })),
    };
  }
}

// -------------------- 2. 数据接口 --------------------

/**
 * 获取图表数据
 */
export async function getChartData(params: {
  chartType: string;
  dataSource?: string;
  filters?: Record<string, any>;
  dateRange?: { start: string; end: string };
  aggregation?: 'sum' | 'avg' | 'count' | 'max' | 'min';
  groupBy?: string[];
  limit?: number;
}): Promise<any> {
  try {
    const response = await api.post('/visualization/data/chart', params);
    return response.data;
  } catch (error) {
    // 模拟数据
    await sleep(400);
    
    // 根据图表类型返回不同的模拟数据
    switch (params.chartType) {
      case 'bar-chart':
      case 'line-chart':
        return {
          xAxis: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
          series: [
            {
              name: '数据1',
              data: [120, 200, 150, 80, 70, 110, 130],
            },
          ],
        };
      
      case 'pie-chart':
        return {
          data: [
            { name: '正面', value: 335 },
            { name: '负面', value: 234 },
            { name: '中性', value: 548 },
          ],
        };
      
      case 'scatter-chart':
        return {
          data: Array.from({ length: 50 }, () => [
            Math.random() * 100,
            Math.random() * 100,
          ]),
        };
      
      case 'heatmap-chart':
        return {
          xAxis: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
          yAxis: ['Morning', 'Afternoon', 'Evening'],
          data: Array.from({ length: 15 }, (_, i) => [
            i % 5,
            Math.floor(i / 5),
            Math.floor(Math.random() * 10),
          ]),
        };
      
      default:
        return { data: [] };
    }
  }
}

/**
 * 获取下钻数据
 */
export async function getDrillDownData(params: {
  path: string[];
  level: number;
  filters: Record<string, any>;
  parentValue?: any;
}): Promise<any> {
  try {
    const response = await api.post('/visualization/data/drilldown', params);
    return response.data;
  } catch (error) {
    // 模拟下钻数据
    await sleep(300);
    
    const mockData: Record<string, any> = {
      0: [
        { name: '2024', value: 1200 },
        { name: '2023', value: 1000 },
        { name: '2022', value: 800 },
      ],
      1: [
        { name: 'Q1', value: 300 },
        { name: 'Q2', value: 350 },
        { name: 'Q3', value: 280 },
        { name: 'Q4', value: 270 },
      ],
      2: [
        { name: '1月', value: 100 },
        { name: '2月', value: 95 },
        { name: '3月', value: 105 },
      ],
    };
    
    return mockData[params.level] || [];
  }
}

/**
 * 获取联动数据
 */
export async function getLinkedData(params: {
  sourceChart: string;
  selection: any;
  targetCharts: string[];
  linkageType: 'filter' | 'highlight' | 'drill-down';
}): Promise<Record<string, any>> {
  try {
    const response = await api.post('/visualization/data/linked', params);
    return response.data;
  } catch (error) {
    // 模拟联动数据
    await sleep(250);
    
    const result: Record<string, any> = {};
    params.targetCharts.forEach(chartId => {
      result[chartId] = {
        data: Array.from({ length: 10 }, (_, i) => ({
          name: `Item ${i + 1}`,
          value: Math.floor(Math.random() * 100),
        })),
        highlightIndices: params.linkageType === 'highlight' ? [0, 2, 5] : undefined,
      };
    });
    
    return result;
  }
}

// -------------------- 3. 主题管理 --------------------

/**
 * 获取主题列表
 */
export async function getThemes(params?: {
  type?: 'builtin' | 'custom' | 'all';
}): Promise<any[]> {
  try {
    const response = await api.get('/visualization/themes', { params });
    return response.data;
  } catch (error) {
    // 返回模拟主题
    await sleep(200);
    return [
      {
        id: 'light',
        name: '明亮主题',
        type: 'builtin',
        colors: {
          primary: PRIMARY,
          success: SUCCESS,
          warning: WARNING,
          danger: DANGER,
        },
      },
      {
        id: 'dark',
        name: '暗黑主题',
        type: 'builtin',
        colors: {
          primary: PRIMARY,
          success: SUCCESS,
          warning: WARNING,
          danger: DANGER,
        },
      },
    ];
  }
}

/**
 * 保存主题
 */
export async function saveTheme(data: {
  id?: string;
  name: string;
  colors: Record<string, string>;
  fonts?: Record<string, any>;
  spacing?: Record<string, number>;
}): Promise<any> {
  try {
    const response = await api.post('/visualization/themes', data);
    return response.data;
  } catch (error) {
    // 模拟保存
    await sleep(300);
    return {
      ...data,
      id: data.id || `theme-${Date.now()}`,
      type: 'custom',
      createdAt: new Date().toISOString(),
    };
  }
}

/**
 * 应用主题
 */
export async function applyTheme(themeId: string, scope?: {
  global?: boolean;
  componentIds?: string[];
}): Promise<void> {
  try {
    await api.post(`/themes/${themeId}/apply`, scope);
  } catch (error) {
    // 模拟应用
    await sleep(200);
    localStorage.setItem('current_theme', themeId);
  }
}

/**
 * 删除主题
 */
export async function deleteTheme(id: string): Promise<void> {
  try {
    await api.delete(`/themes/${id}`);
  } catch (error) {
    await sleep(200);
    localStorage.removeItem(`theme_${id}`);
  }
}

// -------------------- 4. 导出功能 --------------------

/**
 * 导出格式定义
 */
export interface ExportFormat {
  id: string;
  name: string;
  extension: string;
  mimeType: string;
  description: string;
  supportsChart: boolean;
  supportsDashboard: boolean;
}

/**
 * 获取支持的导出格式
 */
export async function getExportFormats(): Promise<ExportFormat[]> {
  await sleep(100);
  return [
    {
      id: 'png',
      name: 'PNG图片',
      extension: 'png',
      mimeType: 'image/png',
      description: '高质量位图格式',
      supportsChart: true,
      supportsDashboard: true,
    },
    {
      id: 'jpg',
      name: 'JPG图片',
      extension: 'jpg',
      mimeType: 'image/jpeg',
      description: '压缩位图格式',
      supportsChart: true,
      supportsDashboard: true,
    },
    {
      id: 'svg',
      name: 'SVG矢量图',
      extension: 'svg',
      mimeType: 'image/svg+xml',
      description: '可缩放矢量图形',
      supportsChart: true,
      supportsDashboard: false,
    },
    {
      id: 'pdf',
      name: 'PDF文档',
      extension: 'pdf',
      mimeType: 'application/pdf',
      description: '便携式文档格式',
      supportsChart: true,
      supportsDashboard: true,
    },
    {
      id: 'excel',
      name: 'Excel表格',
      extension: 'xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      description: '导出数据到Excel',
      supportsChart: true,
      supportsDashboard: true,
    },
    {
      id: 'json',
      name: 'JSON数据',
      extension: 'json',
      mimeType: 'application/json',
      description: '导出原始数据',
      supportsChart: true,
      supportsDashboard: true,
    },
  ];
}

/**
 * 导出图表
 */
export async function exportChart(params: {
  chartId: string;
  format: string;
  options?: {
    width?: number;
    height?: number;
    quality?: number;
    backgroundColor?: string;
    includeData?: boolean;
  };
}): Promise<Blob> {
  try {
    const response = await api.post('/visualization/export/chart', params, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    // 模拟导出
    await sleep(500);
    
    const format = await getExportFormats();
    const selectedFormat = format.find(f => f.id === params.format);
    
    if (!selectedFormat) {
      throw new Error('不支持的导出格式');
    }
    
    // 创建模拟数据
    const content = params.format === 'json' 
      ? JSON.stringify({ chartId: params.chartId, data: [] }, null, 2)
      : `Mock ${selectedFormat.name} content`;
    
    return new Blob([content], { type: selectedFormat.mimeType });
  }
}

/**
 * 导出仪表盘
 */
export async function exportDashboard(params: {
  layoutId: string;
  format: string;
  options?: {
    width?: number;
    height?: number;
    quality?: number;
    includeData?: boolean;
    pageSize?: 'A4' | 'A3' | 'Letter';
    orientation?: 'portrait' | 'landscape';
  };
}): Promise<Blob> {
  try {
    const response = await api.post('/visualization/export/dashboard', params, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    // 模拟导出
    await sleep(800);
    
    const formats = await getExportFormats();
    const selectedFormat = formats.find(f => f.id === params.format);
    
    if (!selectedFormat) {
      throw new Error('不支持的导出格式');
    }
    
    // 创建模拟数据
    const content = params.format === 'json'
      ? JSON.stringify({ layoutId: params.layoutId, components: [] }, null, 2)
      : `Mock Dashboard ${selectedFormat.name} content`;
    
    return new Blob([content], { type: selectedFormat.mimeType });
  }
}

/**
 * 批量导出
 */
export async function batchExport(params: {
  items: Array<{ id: string; type: 'chart' | 'dashboard' }>;
  format: string;
  options?: any;
}): Promise<Blob> {
  try {
    const response = await api.post('/visualization/export/batch', params, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    // 模拟批量导出（返回ZIP）
    await sleep(1000);
    return new Blob(['Mock ZIP content'], { type: 'application/zip' });
  }
}

/**
 * 导出为图片（使用html2canvas）
 */
export async function exportAsImageAdvanced(
  element: HTMLElement,
  options?: {
    format?: 'png' | 'jpg';
    quality?: number;
    scale?: number;
    backgroundColor?: string;
  }
): Promise<Blob> {
  // 实际项目中需要安装 html2canvas
  // import html2canvas from 'html2canvas';
  
  await sleep(500);
  
  // 模拟实现
  const canvas = document.createElement('canvas');
  canvas.width = options?.scale ? element.offsetWidth * options.scale : element.offsetWidth;
  canvas.height = options?.scale ? element.offsetHeight * options.scale : element.offsetHeight;
  
  const ctx = canvas.getContext('2d');
  if (ctx && options?.backgroundColor) {
    ctx.fillStyle = options.backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  
  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => resolve(blob || new Blob()),
      options?.format === 'jpg' ? 'image/jpeg' : 'image/png',
      options?.quality || 0.92
    );
  });
}

/**
 * 下载文件
 */
export function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
