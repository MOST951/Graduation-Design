/**
 * 报告生成模块 API
 */
import apiClient from '@/api';

const api = apiClient;

// 模拟延迟
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ==================== 类型定义 ====================

/** 报告模板类型 */
export type TemplateType = 'daily' | 'weekly' | 'monthly' | 'special' | 'custom';

/** 报告组件类型 */
export type ReportComponentType = 
  | 'cover' | 'toc' | 'summary' | 'chart' | 'table' | 'text' 
  | 'image' | 'divider' | 'pagebreak' | 'header' | 'footer';

/** 导出格式 */
export type ExportFormat = 'pdf' | 'word' | 'excel' | 'html' | 'markdown';

/** 报告模板 */
export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  type: TemplateType;
  thumbnail?: string;
  structure: ReportStructure;
  variables: TemplateVariable[];
  styles: TemplateStyles;
  isDefault: boolean;
  isPublic: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  usageCount: number;
  tags: string[];
}

/** 报告结构 */
export interface ReportStructure {
  pages: ReportPage[];
  layout: {
    pageSize: 'A4' | 'A3' | 'Letter';
    orientation: 'portrait' | 'landscape';
    margins: { top: number; right: number; bottom: number; left: number };
  };
}

/** 报告页面 */
export interface ReportPage {
  id: string;
  name: string;
  components: ReportComponent[];
  order: number;
}

/** 报告组件 */
export interface ReportComponent {
  id: string;
  type: ReportComponentType;
  name: string;
  config: Record<string, any>;
  position: { x: number; y: number };
  size: { width: number; height: number };
  styles?: Record<string, any>;
  dataBinding?: string;
  conditions?: ComponentCondition[];
}

/** 组件条件 */
export interface ComponentCondition {
  field: string;
  operator: 'equals' | 'contains' | 'greater' | 'less';
  value: unknown;
  action: 'show' | 'hide' | 'highlight';
}

/** 模板变量 */
export interface TemplateVariable {
  name: string;
  label: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'array' | 'object';
  defaultValue?: string | number | boolean | null;
  required: boolean;
  description?: string;
  options?: Array<{ label: string; value: string | number | boolean }>;
}

/** 模板样式 */
export interface TemplateStyles {
  colors: {
    primary: string;
    secondary: string;
    text: string;
    background: string;
  };
  fonts: {
    title: string;
    heading: string;
    body: string;
    code: string;
  };
  spacing: {
    section: number;
    paragraph: number;
    line: number;
  };
}

/** 报告实例 */
export interface Report {
  id: string;
  templateId: string;
  name: string;
  description?: string;
  data: Record<string, any>;
  generatedAt: string;
  generatedBy: string;
  status: 'draft' | 'generating' | 'completed' | 'failed';
  exportedFormats: ExportFormat[];
  fileUrls: Record<ExportFormat, string>;
  metadata: {
    dataRange?: { start: string; end: string };
    filters?: Record<string, any>;
    version: number;
  };
}

/** 报告生成配置 */
export interface ReportGenerateConfig {
  templateId: string;
  name: string;
  variables: Record<string, any>;
  dataRange?: { start: string; end: string };
  filters?: Record<string, any>;
  exportFormats?: ExportFormat[];
  schedule?: {
    enabled: boolean;
    frequency: 'daily' | 'weekly' | 'monthly';
    time: string;
    recipients?: string[];
  };
}

// ==================== 模板管理 ====================

/**
 * 获取模板列表
 */
export async function getTemplates(params?: {
  type?: TemplateType;
  keyword?: string;
  tags?: string[];
  page?: number;
  pageSize?: number;
}): Promise<{ list: ReportTemplate[]; total: number }> {
  try {
    const response = await api.get<{ list: ReportTemplate[]; total: number }>('/reports/templates', { params });
    return response.data;
  } catch (error) {
    // 模拟数据
    await sleep(300);
    return {
      list: mockTemplates.filter(t => {
        if (params?.type && t.type !== params.type) return false;
        if (params?.keyword && !t.name.includes(params.keyword)) return false;
        if (params?.tags && !params.tags.some(tag => t.tags.includes(tag))) return false;
        return true;
      }),
      total: mockTemplates.length,
    };
  }
}

/**
 * 获取模板详情
 */
export async function getTemplateById(id: string): Promise<ReportTemplate> {
  try {
    const response = await api.get<ReportTemplate>(`/templates/${id}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    const template = mockTemplates.find(t => t.id === id);
    if (!template) throw new Error('模板不存在');
    return template;
  }
}

/**
 * 创建模板
 */
export async function createTemplate(data: Partial<ReportTemplate>): Promise<ReportTemplate> {
  try {
    const response = await api.post<ReportTemplate>('/reports/templates', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    const now = new Date().toISOString();
    return {
      id: `template-${Date.now()}`,
      name: data.name || '未命名模板',
      description: data.description || '',
      type: data.type || 'custom',
      structure: data.structure || defaultStructure,
      variables: data.variables || [],
      styles: data.styles || defaultStyles,
      isDefault: false,
      isPublic: false,
      createdBy: 'current-user',
      createdAt: now,
      updatedAt: now,
      usageCount: 0,
      tags: data.tags || [],
    };
  }
}

/**
 * 更新模板
 */
export async function updateTemplate(id: string, data: Partial<ReportTemplate>): Promise<ReportTemplate> {
  try {
    const response = await api.put<ReportTemplate>(`/templates/${id}`, data);
    return response.data;
  } catch (error) {
    await sleep(300);
    const template = await getTemplateById(id);
    return {
      ...template,
      ...data,
      updatedAt: new Date().toISOString(),
    };
  }
}

/**
 * 删除模板
 */
export async function deleteTemplate(id: string): Promise<void> {
  try {
    await api.delete(`/templates/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 复制模板
 */
export async function cloneTemplate(id: string, newName?: string): Promise<ReportTemplate> {
  try {
    const response = await api.post<ReportTemplate>(`/templates/${id}/clone`, { name: newName });
    return response.data;
  } catch (error) {
    await sleep(300);
    const original = await getTemplateById(id);
    const now = new Date().toISOString();
    return {
      ...original,
      id: `template-${Date.now()}`,
      name: newName || `${original.name} - 副本`,
      isDefault: false,
      createdAt: now,
      updatedAt: now,
      usageCount: 0,
    };
  }
}

/**
 * 设置默认模板
 */
export async function setDefaultTemplate(id: string, type: TemplateType): Promise<void> {
  try {
    await api.post(`/templates/${id}/set-default`, { type });
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 导出模板
 */
export async function exportTemplate(id: string): Promise<Blob> {
  try {
    const response = await api.get(`/templates/${id}/export`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    await sleep(300);
    const template = await getTemplateById(id);
    const json = JSON.stringify(template, null, 2);
    return new Blob([json], { type: 'application/json' });
  }
}

/**
 * 导入模板
 */
export async function importTemplate(file: File): Promise<ReportTemplate> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<ReportTemplate>('/reports/templates/import', formData);
    return response.data;
  } catch (error) {
    await sleep(400);
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const template = JSON.parse(e.target?.result as string);
          template.id = `template-${Date.now()}`;
          template.createdAt = new Date().toISOString();
          template.updatedAt = new Date().toISOString();
          resolve(template);
        } catch {
          reject(new Error('无效的模板文件'));
        }
      };
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.readAsText(file);
    });
  }
}

/**
 * 分享模板
 */
export async function shareTemplate(id: string, options?: {
  expireTime?: number;
  password?: string;
}): Promise<{ url: string; code: string }> {
  try {
    const response = await api.post<{ url: string; code: string }>(`/templates/${id}/share`, options);
    return response.data;
  } catch (error) {
    await sleep(200);
    const code = Math.random().toString(36).substring(2, 8).toUpperCase();
    return {
      url: `${window.location.origin}/reports/templates/shared/${id}?code=${code}`,
      code,
    };
  }
}

// ==================== 报告生成 ====================

/**
 * 生成报告
 */
export async function generateReport(config: ReportGenerateConfig): Promise<Report> {
  try {
    const response = await api.post<Report>('/reports/generate', config);
    return response.data;
  } catch (error) {
    await sleep(1000);
    const now = new Date().toISOString();
    return {
      id: `report-${Date.now()}`,
      templateId: config.templateId,
      name: config.name,
      data: config.variables,
      generatedAt: now,
      generatedBy: 'current-user',
      status: 'completed',
      exportedFormats: config.exportFormats || ['pdf'],
      fileUrls: {
        pdf: `/reports/files/report-${Date.now()}.pdf`,
      },
      metadata: {
        dataRange: config.dataRange,
        filters: config.filters,
        version: 1,
      },
    };
  }
}

/**
 * 获取报告列表
 */
export async function getReports(params?: {
  templateId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ list: Report[]; total: number }> {
  try {
    const response = await api.get<{ list: Report[]; total: number }>('/reports/reports', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      list: [],
      total: 0,
    };
  }
}

/**
 * 获取报告详情
 */
export async function getReportById(id: string): Promise<Report> {
  try {
    const response = await api.get<Report>(`/reports/${id}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    throw new Error('报告不存在');
  }
}

/**
 * 删除报告
 */
export async function deleteReport(id: string): Promise<void> {
  try {
    await api.delete(`/reports/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 导出报告
 */
export async function exportReport(id: string, format: ExportFormat): Promise<Blob> {
  try {
    const response = await api.get(`/reports/${id}/export/${format}`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    await sleep(800);
    const mimeTypes: Record<ExportFormat, string> = {
      pdf: 'application/pdf',
      word: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      excel: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      html: 'text/html',
      markdown: 'text/markdown',
    };
    return new Blob([`Mock ${format} content`], { type: mimeTypes[format] });
  }
}

/**
 * 预览报告
 */
export async function previewReport(config: ReportGenerateConfig): Promise<string> {
  try {
    const response = await api.post<{ html: string }>('/reports/preview', config);
    return response.data.html;
  } catch (error) {
    await sleep(500);
    return '<html><body><h1>报告预览</h1><p>这是一个模拟的报告预览</p></body></html>';
  }
}

// ==================== 定时报告 ====================

/**
 * 创建定时报告
 */
export async function createScheduledReport(config: ReportGenerateConfig): Promise<{ id: string }> {
  try {
    const response = await api.post<{ id: string }>('/reports/scheduled', config);
    return response.data;
  } catch (error) {
    await sleep(300);
    return { id: `scheduled-${Date.now()}` };
  }
}

/**
 * 获取定时报告列表
 */
export async function getScheduledReports(): Promise<ScheduledReport[]> {
  try {
    const response = await api.get('/reports/scheduled');
    return response.data;
  } catch (error) {
    await sleep(200);
    return [];
  }
}

/**
 * 删除定时报告
 */
export async function deleteScheduledReport(id: string): Promise<void> {
  try {
    await api.delete(`/scheduled/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

// ==================== 模板市场 ====================

/**
 * 获取模板市场列表
 */
export async function getMarketplaceTemplates(params?: {
  category?: string;
  keyword?: string;
  sortBy?: 'popular' | 'recent' | 'rating';
}): Promise<ReportTemplate[]> {
  try {
    const response = await api.get<ReportTemplate[]>('/reports/marketplace', { params });
    return response.data;
  } catch (error) {
    await sleep(400);
    return mockMarketplaceTemplates;
  }
}

/**
 * 安装市场模板
 */
export async function installMarketplaceTemplate(id: string): Promise<ReportTemplate> {
  try {
    const response = await api.post<ReportTemplate>(`/marketplace/${id}/install`);
    return response.data;
  } catch (error) {
    await sleep(500);
    const template = mockMarketplaceTemplates.find(t => t.id === id);
    if (!template) throw new Error('模板不存在');
    return {
      ...template,
      id: `template-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }
}

// ==================== 模拟数据 ====================

const defaultStructure: ReportStructure = {
  pages: [
    {
      id: 'page-1',
      name: '封面',
      order: 0,
      components: [
        {
          id: 'comp-1',
          type: 'cover',
          name: '封面',
          config: {
            title: '{{reportTitle}}',
            subtitle: '{{reportSubtitle}}',
            date: '{{reportDate}}',
          },
          position: { x: 0, y: 0 },
          size: { width: 100, height: 100 },
        },
      ],
    },
  ],
  layout: {
    pageSize: 'A4',
    orientation: 'portrait',
    margins: { top: 20, right: 20, bottom: 20, left: 20 },
  },
};

const defaultStyles: TemplateStyles = {
  colors: {
    primary: '#409EFF',
    secondary: '#909399',
    text: '#303133',
    background: '#FFFFFF',
  },
  fonts: {
    title: 'Arial, sans-serif',
    heading: 'Arial, sans-serif',
    body: 'Arial, sans-serif',
    code: 'Courier New, monospace',
  },
  spacing: {
    section: 24,
    paragraph: 16,
    line: 1.5,
  },
};

const mockTemplates: ReportTemplate[] = [
  {
    id: 'template-1',
    name: '日报模板',
    description: '每日数据分析报告模板',
    type: 'daily',
    thumbnail: '/templates/daily.png',
    structure: defaultStructure,
    variables: [
      {
        name: 'reportDate',
        label: '报告日期',
        type: 'date',
        defaultValue: new Date().toISOString().split('T')[0],
        required: true,
      },
      {
        name: 'reportTitle',
        label: '报告标题',
        type: 'string',
        defaultValue: '每日数据分析报告',
        required: true,
      },
    ],
    styles: defaultStyles,
    isDefault: true,
    isPublic: true,
    createdBy: 'system',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    usageCount: 156,
    tags: ['日报', '数据分析'],
  },
  {
    id: 'template-2',
    name: '周报模板',
    description: '每周数据汇总报告模板',
    type: 'weekly',
    thumbnail: '/templates/weekly.png',
    structure: defaultStructure,
    variables: [],
    styles: defaultStyles,
    isDefault: false,
    isPublic: true,
    createdBy: 'system',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    usageCount: 89,
    tags: ['周报', '汇总'],
  },
  {
    id: 'template-3',
    name: '月报模板',
    description: '每月数据总结报告模板',
    type: 'monthly',
    thumbnail: '/templates/monthly.png',
    structure: defaultStructure,
    variables: [],
    styles: defaultStyles,
    isDefault: false,
    isPublic: true,
    createdBy: 'system',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    usageCount: 45,
    tags: ['月报', '总结'],
  },
];

const mockMarketplaceTemplates: ReportTemplate[] = [
  {
    id: 'market-1',
    name: '专业商务报告',
    description: '适合商务场景的专业报告模板',
    type: 'special',
    thumbnail: '/marketplace/business.png',
    structure: defaultStructure,
    variables: [],
    styles: defaultStyles,
    isDefault: false,
    isPublic: true,
    createdBy: 'marketplace',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    usageCount: 234,
    tags: ['商务', '专业'],
  },
];

// ==================== 新增完整API函数 ====================

// -------------------- 1. 报告管理 --------------------

/**
 * 获取报告列表
 */
export async function getReports(params?: {
  page?: number;
  pageSize?: number;
  keyword?: string;
  type?: TemplateType;
  status?: 'draft' | 'completed' | 'shared';
  startDate?: string;
  endDate?: string;
  sortBy?: 'createdAt' | 'updatedAt' | 'name' | 'views';
  sortOrder?: 'asc' | 'desc';
}): Promise<{ list: Report[]; total: number }> {
  try {
    const response = await api.get<{ list: Report[]; total: number }>('/reports/reports', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    // 模拟数据
    return {
      list: [
        {
          id: 'report-1',
          templateId: 'template-1',
          name: '2024年度情感分析报告',
          description: '年度数据汇总分析',
          data: {},
          generatedAt: new Date().toISOString(),
          generatedBy: '张三',
          status: 'completed',
          exportedFormats: ['pdf', 'word'],
          fileUrls: {
            pdf: '/files/report-1.pdf',
            word: '/files/report-1.docx',
          },
          metadata: {
            dataRange: {
              start: '2024-01-01',
              end: '2024-12-31',
            },
            filters: {},
            version: 1,
          },
          size: 2048576,
          views: 156,
          hasVersions: true,
          currentVersion: 3,
        },
      ],
      total: 1,
    };
  }
}

/**
 * 获取报告详情
 */
export async function getReport(id: string): Promise<Report> {
  try {
    const response = await api.get<Report>(`/reports/${id}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    throw new Error('报告不存在');
  }
}

/**
 * 创建报告
 */
export async function createReport(data: {
  templateId: string;
  name: string;
  description?: string;
  variables: Record<string, any>;
  dataRange?: { start: string; end: string };
  filters?: Record<string, any>;
}): Promise<Report> {
  try {
    const response = await api.post<Report>('/reports/reports', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    const now = new Date().toISOString();
    return {
      id: `report-${Date.now()}`,
      templateId: data.templateId,
      name: data.name,
      description: data.description,
      data: data.variables,
      generatedAt: now,
      generatedBy: 'current-user',
      status: 'draft',
      exportedFormats: [],
      fileUrls: {},
      metadata: {
        dataRange: data.dataRange,
        filters: data.filters,
        version: 1,
      },
    };
  }
}

/**
 * 更新报告
 */
export async function updateReport(id: string, data: Partial<Report>): Promise<Report> {
  try {
    const response = await api.put<Report>(`/reports/${id}`, data);
    return response.data;
  } catch (error) {
    await sleep(300);
    const report = await getReport(id);
    return {
      ...report,
      ...data,
      metadata: {
        ...report.metadata,
        version: report.metadata.version + 1,
      },
    };
  }
}

/**
 * 删除报告
 */
export async function deleteReport(id: string): Promise<void> {
  try {
    await api.delete(`/reports/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 克隆报告
 */
export async function cloneReport(id: string, newName?: string): Promise<Report> {
  try {
    const response = await api.post<Report>(`/reports/${id}/clone`, { name: newName });
    return response.data;
  } catch (error) {
    await sleep(300);
    const original = await getReport(id);
    const now = new Date().toISOString();
    return {
      ...original,
      id: `report-${Date.now()}`,
      name: newName || `${original.name} - 副本`,
      generatedAt: now,
      status: 'draft',
      views: 0,
      metadata: {
        ...original.metadata,
        version: 1,
      },
    };
  }
}

/**
 * 批量删除报告
 */
export async function batchDeleteReports(ids: string[]): Promise<void> {
  try {
    await api.post('/reports/reports/batch-delete', { ids });
  } catch (error) {
    await sleep(300);
  }
}

/**
 * 获取报告预览
 */
export async function getReportPreview(id: string, format: 'html' | 'pdf' = 'html'): Promise<string> {
  try {
    const response = await api.get<{ content: string }>(`/reports/${id}/preview`, {
      params: { format },
    });
    return response.data.content;
  } catch (error) {
    await sleep(500);
    return '<html><body><h1>报告预览</h1><p>这是报告内容...</p></body></html>';
  }
}

// -------------------- 2. 模板管理 (扩展现有函数) --------------------

/**
 * 批量删除模板
 */
export async function batchDeleteTemplates(ids: string[]): Promise<void> {
  try {
    await api.post('/reports/templates/batch-delete', { ids });
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 获取模板使用统计
 */
export async function getTemplateStats(id: string): Promise<{
  usageCount: number;
  lastUsed: string;
  popularityRank: number;
}> {
  try {
    const response = await api.get(`/templates/${id}/stats`);
    return response.data;
  } catch (error) {
    await sleep(200);
    return {
      usageCount: 156,
      lastUsed: new Date().toISOString(),
      popularityRank: 3,
    };
  }
}

/**
 * 搜索模板
 */
export async function searchTemplates(query: string): Promise<ReportTemplate[]> {
  try {
    const response = await api.get<ReportTemplate[]>('/reports/templates/search', {
      params: { q: query },
    });
    return response.data;
  } catch (error) {
    await sleep(300);
    return [];
  }
}

// -------------------- 3. 生成任务 --------------------

/**
 * 获取生成任务列表
 */
export async function getGenerationTasks(params?: {
  status?: 'pending' | 'running' | 'completed' | 'failed';
  page?: number;
  pageSize?: number;
}): Promise<{ list: GenerationTask[]; total: number }> {
  try {
    const response = await api.get<{ list: GenerationTask[]; total: number }>('/reports/tasks', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      list: [
        {
          id: 'task-1',
          reportId: 'report-1',
          templateId: 'template-1',
          name: '生成年度报告',
          status: 'completed',
          progress: 100,
          startTime: new Date(Date.now() - 600000).toISOString(),
          endTime: new Date().toISOString(),
          duration: 600,
          error: null,
          result: {
            reportId: 'report-1',
            fileUrls: {
              pdf: '/files/report-1.pdf',
            },
          },
        },
      ],
      total: 1,
    };
  }
}

/**
 * 获取生成任务详情
 */
export async function getGenerationTask(id: string): Promise<GenerationTask> {
  try {
    const response = await api.get<GenerationTask>(`/tasks/${id}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    throw new Error('任务不存在');
  }
}

/**
 * 创建生成任务
 */
export async function createGenerationTask(data: {
  templateId: string;
  name: string;
  variables: Record<string, any>;
  dataRange?: { start: string; end: string };
  filters?: Record<string, any>;
  exportFormats?: ExportFormat[];
  schedule?: {
    enabled: boolean;
    frequency: 'daily' | 'weekly' | 'monthly';
    time: string;
    recipients?: string[];
  };
}): Promise<GenerationTask> {
  try {
    const response = await api.post<GenerationTask>('/reports/tasks', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    return {
      id: `task-${Date.now()}`,
      reportId: null,
      templateId: data.templateId,
      name: data.name,
      status: 'pending',
      progress: 0,
      startTime: null,
      endTime: null,
      duration: null,
      error: null,
      result: null,
    };
  }
}

/**
 * 更新生成任务
 */
export async function updateGenerationTask(id: string, data: Partial<GenerationTask>): Promise<GenerationTask> {
  try {
    const response = await api.put<GenerationTask>(`/tasks/${id}`, data);
    return response.data;
  } catch (error) {
    await sleep(300);
    const task = await getGenerationTask(id);
    return { ...task, ...data };
  }
}

/**
 * 删除生成任务
 */
export async function deleteGenerationTask(id: string): Promise<void> {
  try {
    await api.delete(`/tasks/${id}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 立即执行生成任务
 */
export async function runGenerationTask(id: string): Promise<{ taskId: string }> {
  try {
    const response = await api.post<{ taskId: string }>(`/tasks/${id}/run`);
    return response.data;
  } catch (error) {
    await sleep(500);
    return { taskId: id };
  }
}

/**
 * 取消生成任务
 */
export async function cancelGenerationTask(id: string): Promise<void> {
  try {
    await api.post(`/tasks/${id}/cancel`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 获取任务日志
 */
export async function getTaskLogs(id: string, params?: {
  level?: 'info' | 'warn' | 'error';
  limit?: number;
}): Promise<TaskLog[]> {
  try {
    const response = await api.get<TaskLog[]>(`/tasks/${id}/logs`, { params });
    return response.data;
  } catch (error) {
    await sleep(200);
    return [
      {
        id: '1',
        taskId: id,
        level: 'info',
        message: '任务开始执行',
        timestamp: new Date().toISOString(),
      },
      {
        id: '2',
        taskId: id,
        level: 'info',
        message: '正在获取数据...',
        timestamp: new Date(Date.now() + 1000).toISOString(),
      },
      {
        id: '3',
        taskId: id,
        level: 'info',
        message: '数据获取完成，共1500条',
        timestamp: new Date(Date.now() + 2000).toISOString(),
      },
    ];
  }
}

// -------------------- 4. 导出功能 --------------------

/**
 * 导出报告
 */
export async function exportReport(
  id: string,
  format: ExportFormat,
  options?: {
    includeData?: boolean;
    watermark?: string;
    password?: string;
  }
): Promise<{ taskId: string }> {
  try {
    const response = await api.post<{ taskId: string }>(`/reports/${id}/export`, {
      format,
      options,
    });
    return response.data;
  } catch (error) {
    await sleep(500);
    return { taskId: `export-${Date.now()}` };
  }
}

/**
 * 批量导出报告
 */
export async function batchExportReports(
  ids: string[],
  format: ExportFormat,
  options?: {
    includeData?: boolean;
    watermark?: string;
    mergeFiles?: boolean;
  }
): Promise<{ taskId: string }> {
  try {
    const response = await api.post<{ taskId: string }>('/reports/reports/batch-export', {
      ids,
      format,
      options,
    });
    return response.data;
  } catch (error) {
    await sleep(800);
    return { taskId: `batch-export-${Date.now()}` };
  }
}

/**
 * 获取导出状态
 */
export async function getExportStatus(taskId: string): Promise<{
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  fileId?: string;
  fileUrl?: string;
  error?: string;
}> {
  try {
    const response = await api.get(`/exports/${taskId}/status`);
    return response.data;
  } catch (error) {
    await sleep(200);
    return {
      status: 'completed',
      progress: 100,
      fileId: `file-${taskId}`,
      fileUrl: `/files/${taskId}.pdf`,
    };
  }
}

/**
 * 下载导出文件
 */
export async function downloadExport(fileId: string): Promise<Blob> {
  try {
    const response = await api.get(`/exports/${fileId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    await sleep(500);
    return new Blob(['Mock file content'], { type: 'application/pdf' });
  }
}

/**
 * 取消导出任务
 */
export async function cancelExport(taskId: string): Promise<void> {
  try {
    await api.post(`/exports/${taskId}/cancel`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 获取导出历史
 */
export async function getExportHistory(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
}): Promise<{ list: ExportHistory[]; total: number }> {
  try {
    const response = await api.get('/reports/exports/history', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      list: [
        {
          id: 'export-1',
          reportId: 'report-1',
          reportName: '年度报告',
          format: 'pdf',
          status: 'completed',
          fileSize: 2048576,
          fileUrl: '/files/export-1.pdf',
          createdAt: new Date().toISOString(),
          completedAt: new Date(Date.now() + 10000).toISOString(),
        },
      ],
      total: 1,
    };
  }
}

// -------------------- 5. 版本管理 --------------------

/**
 * 获取报告版本列表
 */
export async function getReportVersions(reportId: string): Promise<ReportVersion[]> {
  try {
    const response = await api.get<ReportVersion[]>(`/reports/${reportId}/versions`);
    return response.data;
  } catch (error) {
    await sleep(300);
    return [
      {
        id: 'v3',
        reportId,
        version: 3,
        author: '张三',
        createdAt: new Date().toISOString(),
        description: '更新了数据分析部分',
        changes: ['修改图表样式', '添加趋势分析'],
        isCurrent: true,
        tag: '',
        size: 2048576,
        fileUrl: `/files/${reportId}-v3.pdf`,
      },
    ];
  }
}

/**
 * 创建报告版本
 */
export async function createReportVersion(
  reportId: string,
  data: {
    description: string;
    changes: string[];
    tag?: string;
  }
): Promise<ReportVersion> {
  try {
    const response = await api.post<ReportVersion>(`/reports/${reportId}/versions`, data);
    return response.data;
  } catch (error) {
    await sleep(400);
    return {
      id: `v${Date.now()}`,
      reportId,
      version: 1,
      author: 'current-user',
      createdAt: new Date().toISOString(),
      description: data.description,
      changes: data.changes,
      isCurrent: true,
      tag: data.tag || '',
      size: 0,
      fileUrl: '',
    };
  }
}

/**
 * 恢复报告版本
 */
export async function restoreReportVersion(reportId: string, versionId: string): Promise<void> {
  try {
    await api.post(`/reports/${reportId}/versions/${versionId}/restore`);
  } catch (error) {
    await sleep(300);
  }
}

/**
 * 对比报告版本
 */
export async function compareReportVersions(
  reportId: string,
  version1: string,
  version2: string
): Promise<{
  additions: VersionDiffEntry[];
  deletions: VersionDiffEntry[];
  modifications: VersionDiffEntry[];
}> {
  try {
    const response = await api.get(`/reports/${reportId}/versions/compare`, {
      params: { v1: version1, v2: version2 },
    });
    return response.data;
  } catch (error) {
    await sleep(400);
    return {
      additions: [],
      deletions: [],
      modifications: [],
    };
  }
}

// -------------------- 6. 分享与协作 --------------------

/**
 * 分享报告
 */
export async function shareReport(
  reportId: string,
  config: {
    permission: 'view' | 'comment' | 'edit';
    expireType: 'never' | '1d' | '7d' | '30d' | 'custom';
    expireDate?: string;
    requirePassword?: boolean;
    password?: string;
    allowDownload?: boolean;
    users?: string[];
  }
): Promise<{
  shareId: string;
  shareLink: string;
  qrCode: string;
}> {
  try {
    const response = await api.post(`/reports/${reportId}/share`, config);
    return response.data;
  } catch (error) {
    await sleep(300);
    const shareId = Math.random().toString(36).substring(2, 8).toUpperCase();
    return {
      shareId,
      shareLink: `${window.location.origin}/reports/shared/${reportId}?code=${shareId}`,
      qrCode: `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${shareId}`,
    };
  }
}

/**
 * 获取分享信息
 */
export async function getShareInfo(shareId: string): Promise<{
  reportId: string;
  permission: string;
  expireAt: string;
  accessCount: number;
}> {
  try {
    const response = await api.get(`/shares/${shareId}`);
    return response.data;
  } catch (error) {
    await sleep(200);
    throw new Error('分享不存在或已过期');
  }
}

/**
 * 取消分享
 */
export async function cancelShare(shareId: string): Promise<void> {
  try {
    await api.delete(`/shares/${shareId}`);
  } catch (error) {
    await sleep(200);
  }
}

/**
 * 获取报告评论
 */
export async function getReportComments(reportId: string): Promise<ReportComment[]> {
  try {
    const response = await api.get<ReportComment[]>(`/reports/${reportId}/comments`);
    return response.data;
  } catch (error) {
    await sleep(300);
    return [];
  }
}

/**
 * 添加报告评论
 */
export async function addReportComment(
  reportId: string,
  data: {
    content: string;
    parentId?: string;
  }
): Promise<ReportComment> {
  try {
    const response = await api.post<ReportComment>(`/reports/${reportId}/comments`, data);
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      id: `comment-${Date.now()}`,
      reportId,
      author: 'current-user',
      content: data.content,
      createdAt: new Date().toISOString(),
      parentId: data.parentId,
      replies: [],
    };
  }
}

/**
 * 删除报告评论
 */
export async function deleteReportComment(reportId: string, commentId: string): Promise<void> {
  try {
    await api.delete(`/reports/${reportId}/comments/${commentId}`);
  } catch (error) {
    await sleep(200);
  }
}

// -------------------- 7. 统计分析 --------------------

/**
 * 获取报告统计
 */
export async function getReportStatistics(params?: {
  startDate?: string;
  endDate?: string;
}): Promise<{
  totalReports: number;
  totalViews: number;
  totalDownloads: number;
  popularReports: Array<{ id: string; name: string; views: number }>;
  recentReports: Report[];
}> {
  try {
    const response = await api.get('/reports/reports/statistics', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      totalReports: 156,
      totalViews: 3420,
      totalDownloads: 892,
      popularReports: [],
      recentReports: [],
    };
  }
}

/**
 * 获取模板统计
 */
export async function getTemplateStatistics(): Promise<{
  totalTemplates: number;
  totalUsage: number;
  popularTemplates: Array<{ id: string; name: string; usageCount: number }>;
}> {
  try {
    const response = await api.get('/reports/templates/statistics');
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      totalTemplates: 25,
      totalUsage: 1560,
      popularTemplates: [],
    };
  }
}

// ==================== 辅助类型定义 ====================

/** 定时报告 */
export interface ScheduledReport {
  id: string;
  name: string;
  templateId: string;
  config: ReportGenerateConfig;
  schedule: {
    frequency: 'daily' | 'weekly' | 'monthly';
    time: string;
    dayOfWeek?: number;
    dayOfMonth?: number;
  };
  enabled: boolean;
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
}

/** 版本差异条目 */
export interface VersionDiffEntry {
  path: string;
  type: 'component' | 'style' | 'data' | 'config';
  description: string;
  oldValue?: string;
  newValue?: string;
}

export interface GenerationTask {
  id: string;
  reportId: string | null;
  templateId: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startTime: string | null;
  endTime: string | null;
  duration: number | null;
  error: string | null;
  result: {
    reportId: string;
    fileUrls: Record<ExportFormat, string>;
  } | null;
}

export interface TaskLog {
  id: string;
  taskId: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
}

export interface ExportHistory {
  id: string;
  reportId: string;
  reportName: string;
  format: ExportFormat;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  fileSize: number;
  fileUrl: string;
  createdAt: string;
  completedAt: string;
}

export interface ReportVersion {
  id: string;
  reportId: string;
  version: number;
  author: string;
  createdAt: string;
  description: string;
  changes: string[];
  isCurrent: boolean;
  tag: string;
  size: number;
  fileUrl: string;
}

export interface ReportComment {
  id: string;
  reportId: string;
  author: string;
  content: string;
  createdAt: string;
  parentId?: string;
  replies?: ReportComment[];
}

export default api;
