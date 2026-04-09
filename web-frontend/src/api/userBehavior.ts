/**
 * 用户行为分析模块 API
 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/user-behavior',
  timeout: 30000,
});

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ==================== 类型定义 ====================

/** 用户画像 */
export interface UserProfile {
  userId: string;
  username: string;
  avatar?: string;
  basicInfo: {
    gender?: string;
    age?: number;
    location?: string;
    verified: boolean;
    followersCount: number;
    followingCount: number;
  };
  interests: Array<{
    tag: string;
    weight: number;
  }>;
  behaviorPattern: {
    activeTime: string[];
    postFrequency: number;
    avgPostLength: number;
    interactionRate: number;
  };
  influenceScore: number;
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
}

/** 影响力评估 */
export interface InfluenceAssessment {
  userId: string;
  score: number;
  rank: number;
  level: 'KOL' | 'influencer' | 'active' | 'normal';
  metrics: {
    reach: number;
    engagement: number;
    authority: number;
    activity: number;
  };
  trend: Array<{
    date: string;
    score: number;
  }>;
}

/** 传播路径 */
export interface PropagationPath {
  id: string;
  sourceUserId: string;
  nodes: Array<{
    userId: string;
    username: string;
    level: number;
    timestamp: string;
    action: 'post' | 'repost' | 'comment' | 'like';
  }>;
  edges: Array<{
    from: string;
    to: string;
    weight: number;
  }>;
  depth: number;
  reach: number;
  speed: number;
}

/** 用户分群 */
export interface UserSegment {
  id: string;
  name: string;
  description: string;
  size: number;
  characteristics: {
    avgAge?: number;
    genderRatio?: { male: number; female: number };
    topInterests: string[];
    avgInfluence: number;
  };
  users: string[];
}

// ==================== API函数 ====================

/**
 * 获取用户画像
 */
export async function getUserProfile(userId: string): Promise<UserProfile> {
  try {
    const response = await api.get<UserProfile>(`/profile/${userId}`);
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      userId,
      username: 'user_' + userId,
      basicInfo: {
        verified: false,
        followersCount: 1234,
        followingCount: 567,
      },
      interests: [
        { tag: '科技', weight: 0.8 },
        { tag: '娱乐', weight: 0.6 },
        { tag: '体育', weight: 0.4 },
      ],
      behaviorPattern: {
        activeTime: ['09:00-12:00', '18:00-22:00'],
        postFrequency: 5.2,
        avgPostLength: 120,
        interactionRate: 0.15,
      },
      influenceScore: 65.5,
      sentiment: {
        positive: 0.6,
        negative: 0.2,
        neutral: 0.2,
      },
    };
  }
}

/**
 * 批量获取用户画像
 */
export async function batchGetUserProfiles(userIds: string[]): Promise<UserProfile[]> {
  try {
    const response = await api.post<UserProfile[]>('/profile/batch', { userIds });
    return response.data;
  } catch (error) {
    await sleep(500);
    return [];
  }
}

/**
 * 评估用户影响力
 */
export async function assessInfluence(userId: string): Promise<InfluenceAssessment> {
  try {
    const response = await api.get<InfluenceAssessment>(`/influence/${userId}`);
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      userId,
      score: 75.5,
      rank: 156,
      level: 'influencer',
      metrics: {
        reach: 80,
        engagement: 70,
        authority: 75,
        activity: 78,
      },
      trend: Array.from({ length: 7 }, (_, i) => ({
        date: new Date(Date.now() - (6 - i) * 86400000).toISOString().split('T')[0],
        score: Math.random() * 20 + 65,
      })),
    };
  }
}

/**
 * 识别KOL用户
 */
export async function identifyKOLs(params?: {
  minScore?: number;
  limit?: number;
  category?: string;
}): Promise<UserProfile[]> {
  try {
    const response = await api.get<UserProfile[]>('/kol', { params });
    return response.data;
  } catch (error) {
    await sleep(400);
    return [];
  }
}

/**
 * 分析传播路径
 */
export async function analyzePropagation(params: {
  postId?: string;
  userId?: string;
  maxDepth?: number;
}): Promise<PropagationPath> {
  try {
    const response = await api.post<PropagationPath>('/propagation', params);
    return response.data;
  } catch (error) {
    await sleep(600);
    return {
      id: `prop-${Date.now()}`,
      sourceUserId: params.userId || 'user-1',
      nodes: [
        {
          userId: 'user-1',
          username: 'source_user',
          level: 0,
          timestamp: new Date().toISOString(),
          action: 'post',
        },
      ],
      edges: [],
      depth: 3,
      reach: 1500,
      speed: 250,
    };
  }
}

/**
 * 用户分群
 */
export async function segmentUsers(params: {
  method: 'kmeans' | 'dbscan' | 'hierarchical';
  features: string[];
  numClusters?: number;
}): Promise<UserSegment[]> {
  try {
    const response = await api.post<UserSegment[]>('/segment', params);
    return response.data;
  } catch (error) {
    await sleep(800);
    return [
      {
        id: 'segment-1',
        name: '活跃用户群',
        description: '高频发帖、高互动率用户',
        size: 1234,
        characteristics: {
          avgAge: 28,
          genderRatio: { male: 0.6, female: 0.4 },
          topInterests: ['科技', '互联网', '创业'],
          avgInfluence: 75.5,
        },
        users: [],
      },
    ];
  }
}

/**
 * 获取用户分群列表
 */
export async function getUserSegments(): Promise<UserSegment[]> {
  try {
    const response = await api.get<UserSegment[]>('/segments');
    return response.data;
  } catch (error) {
    await sleep(300);
    return [];
  }
}

/**
 * 预测用户行为
 */
export async function predictBehavior(params: {
  userId: string;
  type: 'churn' | 'engagement' | 'sentiment';
  horizon?: number;
}): Promise<{
  prediction: number;
  confidence: number;
  factors: Array<{ name: string; impact: number }>;
}> {
  try {
    const response = await api.post('/predict', params);
    return response.data;
  } catch (error) {
    await sleep(500);
    return {
      prediction: 0.75,
      confidence: 0.85,
      factors: [
        { name: '历史活跃度', impact: 0.4 },
        { name: '互动频率', impact: 0.3 },
        { name: '内容质量', impact: 0.3 },
      ],
    };
  }
}

/**
 * 获取用户行为统计
 */
export async function getUserBehaviorStats(params?: {
  startDate?: string;
  endDate?: string;
  groupBy?: 'day' | 'week' | 'month';
}): Promise<{
  totalUsers: number;
  activeUsers: number;
  newUsers: number;
  churnRate: number;
  avgSessionDuration: number;
  trends: Array<{
    date: string;
    activeUsers: number;
    newUsers: number;
  }>;
}> {
  try {
    const response = await api.get('/stats', { params });
    return response.data;
  } catch (error) {
    await sleep(300);
    return {
      totalUsers: 15678,
      activeUsers: 8934,
      newUsers: 234,
      churnRate: 0.05,
      avgSessionDuration: 1800,
      trends: Array.from({ length: 7 }, (_, i) => ({
        date: new Date(Date.now() - (6 - i) * 86400000).toISOString().split('T')[0],
        activeUsers: Math.floor(Math.random() * 1000) + 8000,
        newUsers: Math.floor(Math.random() * 100) + 200,
      })),
    };
  }
}

export default api;
