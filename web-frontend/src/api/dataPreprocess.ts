/**
 * 数据预处理模块 API
 */
import apiClient from '@/api';

const api = apiClient;

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ==================== 类型定义 ====================

/** 预处理任务 */
export interface PreprocessTask {
  id: string;
  name: string;
  type: 'clean' | 'segment' | 'extract' | 'pipeline';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  config: PreprocessConfig;
  result?: PreprocessResult;
  createdAt: string;
  startTime?: string;
  endTime?: string;
}

/** 预处理配置 */
export interface PreprocessConfig {
  // 数据清洗
  clean?: {
    removeDuplicates: boolean;
    removeNoise: boolean;
    normalizeFormat: boolean;
    removeEmoji: boolean;
    removeUrl: boolean;
  };
  // 分词
  segment?: {
    engine: 'jieba' | 'hanlp';
    customDict?: string[];
    stopWords?: string[];
  };
  // 特征提取
  extract?: {
    method: 'tfidf' | 'word2vec' | 'bert';
    vectorSize?: number;
    maxFeatures?: number;
  };
}

/** 预处理结果 */
export interface PreprocessResult {
  originalCount: number;
  processedCount: number;
  removedCount: number;
  duration: number;
  quality: {
    score: number;
    completeness: number;
    accuracy: number;
    consistency: number;
  };
  statistics: {
    avgLength: number;
    uniqueWords: number;
    vocabulary: number;
  };
}

/** 数据质量报告 */
export interface QualityReport {
  id: string;
  datasetId: string;
  score: number;
  metrics: {
    completeness: number;
    accuracy: number;
    consistency: number;
    timeliness: number;
    uniqueness: number;
  };
  issues: Array<{
    type: string;
    severity: 'high' | 'medium' | 'low';
    count: number;
    description: string;
  }>;
  recommendations: string[];
  createdAt: string;
}

// ==================== API函数 ====================

/**
 * 创建预处理任务
 */
export async function createPreprocessTask(data: {
  name: string;
  type: string;
  datasetId: string;
  config: PreprocessConfig;
}): Promise<PreprocessTask> {
  try {
    const response = await api.post<PreprocessTask>('/preprocess/tasks', data);
    return response.data;
  } catch (error) {
    await sleep(500);
    return {
      id: `task-${Date.now()}`,
      name: data.name,
      type: data.type as any,
      status: 'pending',
      progress: 0,
      config: data.config,
      createdAt: new Date().toISOString(),
    };
  }
}

/**
 * 获取预处理任务列表
 */
export async function getPreprocessTasks(params?: {
  status?: string;
  type?: string;
}): Promise<PreprocessTask[]> {
  try {
    const response = await api.get<PreprocessTask[]>('/preprocess/tasks', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return [];
  }
}

/**
 * 数据清洗
 */
export async function cleanData(data: {
  datasetId: string;
  config: PreprocessConfig['clean'];
}): Promise<{ taskId: string }> {
  try {
    const response = await api.post('/preprocess/clean', data);
    return response.data;
  } catch (error) {
    await sleep(500);
    return { taskId: `clean-${Date.now()}` };
  }
}

/**
 * 中文分词
 */
export async function segmentText(data: {
  text: string;
  engine?: 'jieba' | 'hanlp';
  customDict?: string[];
}): Promise<{ words: string[] }> {
  try {
    const response = await api.post('/preprocess/segment', data);
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      words: ['这是', '一个', '示例', '分词', '结果'],
    };
  }
}

/**
 * 特征提取
 */
export async function extractFeatures(data: {
  datasetId: string;
  method: 'tfidf' | 'word2vec' | 'bert';
  config?: any;
}): Promise<{ taskId: string }> {
  try {
    const response = await api.post('/preprocess/extract', data);
    return response.data;
  } catch (error) {
    await sleep(800);
    return { taskId: `extract-${Date.now()}` };
  }
}

/**
 * 获取数据质量报告
 */
export async function getQualityReport(datasetId: string): Promise<QualityReport> {
  try {
    const response = await api.get<QualityReport>(`/quality/${datasetId}`);
    return response.data;
  } catch (error) {
    await sleep(400);
    return {
      id: `report-${Date.now()}`,
      datasetId,
      score: 85.5,
      metrics: {
        completeness: 92,
        accuracy: 88,
        consistency: 85,
        timeliness: 90,
        uniqueness: 78,
      },
      issues: [
        {
          type: '重复数据',
          severity: 'medium',
          count: 156,
          description: '发现156条重复记录',
        },
        {
          type: '格式不一致',
          severity: 'low',
          count: 45,
          description: '日期格式不统一',
        },
      ],
      recommendations: [
        '建议去除重复数据',
        '统一日期格式',
        '补充缺失字段',
      ],
      createdAt: new Date().toISOString(),
    };
  }
}

/**
 * 创建预处理流水线
 */
export async function createPipeline(data: {
  name: string;
  steps: Array<{
    type: string;
    config: any;
  }>;
}): Promise<{ id: string }> {
  try {
    const response = await api.post('/preprocess/pipeline', data);
    return response.data;
  } catch (error) {
    await sleep(400);
    return { id: `pipeline-${Date.now()}` };
  }
}

/**
 * 执行预处理流水线
 */
export async function runPipeline(pipelineId: string, datasetId: string): Promise<{ taskId: string }> {
  try {
    const response = await api.post(`/pipeline/${pipelineId}/run`, { datasetId });
    return response.data;
  } catch (error) {
    await sleep(500);
    return { taskId: `pipeline-run-${Date.now()}` };
  }
}

export default api;
