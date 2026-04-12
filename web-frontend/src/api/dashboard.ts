/**
 * 仪表盘模块 API
 */
import apiClient from './index';
import { PRIMARY, SUCCESS, WARNING, DANGER } from '@/styles/colors';

// ==================== 类型定义 ====================

/** 概览卡片 */
export interface OverviewCard {
  title: string;
  value: string | number;
  icon: string;
  color: string;
  trend: string;
  trendIcon: string;
  trendClass: 'positive' | 'negative' | 'neutral';
}

/** 情感分布 */
export interface SentimentDistribution {
  positive: number;
  negative: number;
  neutral: number;
}

/** 趋势数据 */
export interface TrendData {
  dates: string[];
  positive: number[];
  negative: number[];
  neutral?: number[];
}

/** 仪表盘整体数据 */
export interface DashboardData {
  overviewCards: OverviewCard[];
  sentimentDistribution: SentimentDistribution;
  trendData: TrendData;
}

/** 仪表盘查询参数 */
export interface DashboardParams {
  period: string;
  dateRange: Date[];
}

// ==================== API 函数 ====================

/**
 * 获取仪表盘核心数据
 */
export async function getDashboardData(params: DashboardParams): Promise<DashboardData> {
  try {
    const response = await apiClient.get('/dashboard/overview', {
      params: {
        period: params.period,
        start_date: params.dateRange[0]?.toISOString(),
        end_date: params.dateRange[1]?.toISOString(),
      },
    });
    return response.data.data;
  } catch {
    // 后端不可用时返回模拟数据
    return {
      overviewCards: [
        { title: '总分析量', value: '2,543,128', icon: 'DataAnalysis', color: PRIMARY, trend: '+15.2%', trendIcon: 'Top', trendClass: 'positive' },
        { title: '正面情感', value: '1,890,331', icon: 'Sunny', color: SUCCESS, trend: '+12.8%', trendIcon: 'Top', trendClass: 'positive' },
        { title: '负面情感', value: '312,450', icon: 'Cloudy', color: DANGER, trend: '-2.1%', trendIcon: 'Bottom', trendClass: 'negative' },
        { title: '实时任务数', value: '25', icon: 'Clock', color: WARNING, trend: '+3', trendIcon: 'Top', trendClass: 'positive' },
      ],
      sentimentDistribution: { positive: 1890331, negative: 312450, neutral: 340347 },
      trendData: {
        dates: ['2023-12-01', '2023-12-02', '2023-12-03', '2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07'],
        positive: [1200, 1320, 1010, 1340, 900, 2300, 2100],
        negative: [220, 182, 191, 234, 290, 330, 310],
      },
    };
  }
}

/**
 * 获取趋势数据
 */
export async function getTrendData(params: { dateRange: Date[] }): Promise<TrendData> {
  try {
    const response = await apiClient.get('/dashboard/trend', {
      params: {
        start_date: params.dateRange[0]?.toISOString(),
        end_date: params.dateRange[1]?.toISOString(),
      },
    });
    return response.data.data;
  } catch {
    return {
      dates: [],
      positive: [],
      negative: [],
    };
  }
}

export default {
  getDashboardData,
  getTrendData,
};
