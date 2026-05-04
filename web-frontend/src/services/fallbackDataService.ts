/**
 * 降级数据服务
 * 当后端API不可用时提供模拟数据，确保前端功能正常
 */

export interface HotSearchItem {
  rank: number;
  title: string;
  hotValue: number;
  label: string;
  url: string;
  sentiment?: string;
  sentimentScore?: number;
  isNew?: boolean;
  trend?: 'up' | 'down' | 'stable';
}

export interface RankedTopic {
  topic_id: number;
  name: string;
  keywords: string[];
  composite_score: number;
  sentiment_avg: number;
  popularity_score: number;
  rank: number;
  trend: 'up' | 'down' | 'stable';
  post_count: number;
}

export interface WordCloudItem {
  name: string;
  value: number;
  sentiment?: string;
}

export class FallbackDataService {
  private static errorCounts: Record<string, number> = {};

  /**
   * 记录API错误
   */
  static recordError(apiName: string): void {
    this.errorCounts[apiName] = (this.errorCounts[apiName] || 0) + 1;
    console.warn(`[FallbackDataService] ${apiName} 错误次数: ${this.errorCounts[apiName]}`);
  }

  /**
   * 重置错误计数
   */
  static resetErrorCount(apiName: string): void {
    this.errorCounts[apiName] = 0;
  }

  /**
   * 判断是否应该使用模拟数据
   */
  static shouldUseFallback(apiName: string): boolean {
    return (this.errorCounts[apiName] || 0) >= 2;
  }

  /**
   * 模拟热搜数据
   */
  static getMockHotSearches(): HotSearchItem[] {
    const now = new Date();
    return [
      { rank: 1, title: "微博舆情分析系统演示", hotValue: 9876543, label: "爆", url: "#", sentiment: "positive", trend: "up", isNew: true },
      { rank: 2, title: "情感-热度三维度排序算法", hotValue: 8765432, label: "热", url: "#", sentiment: "positive", trend: "up" },
      { rank: 3, title: "ChineseBERT情感分析模型", hotValue: 7654321, label: "新", url: "#", sentiment: "neutral", trend: "stable" },
      { rank: 4, title: "Spark大数据实时处理", hotValue: 6543210, label: "热", url: "#", sentiment: "positive", trend: "up" },
      { rank: 5, title: "毕业设计项目展示", hotValue: 5432109, label: "荐", url: "#", sentiment: "positive", trend: "stable" },
      { rank: 6, title: "前端Vue3架构优化", hotValue: 4321098, label: "热", url: "#", sentiment: "neutral", trend: "down" },
      { rank: 7, title: "HBase分布式存储", hotValue: 3210987, label: "新", url: "#", sentiment: "neutral", trend: "stable" },
      { rank: 8, title: "数据可视化ECharts", hotValue: 2109876, label: "热", url: "#", sentiment: "positive", trend: "up" },
      { rank: 9, title: "全链路数据处理流程", hotValue: 1098765, label: "荐", url: "#", sentiment: "neutral", trend: "stable" },
      { rank: 10, title: "实时监控预警系统", hotValue: 987654, label: "新", url: "#", sentiment: "positive", trend: "up" },
    ];
  }

  /**
   * 模拟三维度排序话题数据
   */
  static getMockRankedTopics(): RankedTopic[] {
    return [
      {
        topic_id: 1,
        name: "情感-热度三维度排序",
        keywords: ["情感分析", "热度排序", "综合得分", "创新算法"],
        composite_score: 0.923,
        sentiment_avg: 0.85,
        popularity_score: 0.912,
        rank: 1,
        trend: "up",
        post_count: 15234
      },
      {
        topic_id: 2,
        name: "ChineseBERT模型应用",
        keywords: ["BERT", "中文NLP", "深度学习", "情感识别"],
        composite_score: 0.876,
        sentiment_avg: 0.78,
        popularity_score: 0.845,
        rank: 2,
        trend: "up",
        post_count: 12456
      },
      {
        topic_id: 3,
        name: "Spark实时数据处理",
        keywords: ["Spark", "大数据", "实时计算", "分布式"],
        composite_score: 0.812,
        sentiment_avg: 0.72,
        popularity_score: 0.798,
        rank: 3,
        trend: "stable",
        post_count: 9876
      },
      {
        topic_id: 4,
        name: "Vue3前端架构",
        keywords: ["Vue3", "TypeScript", "Pinia", "组件化"],
        composite_score: 0.765,
        sentiment_avg: 0.68,
        popularity_score: 0.732,
        rank: 4,
        trend: "up",
        post_count: 7654
      },
      {
        topic_id: 5,
        name: "舆情监控预警",
        keywords: ["实时监控", "预警机制", "舆情分析", "风险识别"],
        composite_score: 0.721,
        sentiment_avg: 0.65,
        popularity_score: 0.689,
        rank: 5,
        trend: "down",
        post_count: 5432
      },
      {
        topic_id: 6,
        name: "数据可视化展示",
        keywords: ["ECharts", "图表", "可视化", "交互"],
        composite_score: 0.698,
        sentiment_avg: 0.62,
        popularity_score: 0.654,
        rank: 6,
        trend: "stable",
        post_count: 4321
      },
      {
        topic_id: 7,
        name: "HBase存储方案",
        keywords: ["HBase", "NoSQL", "列存储", "海量数据"],
        composite_score: 0.654,
        sentiment_avg: 0.58,
        popularity_score: 0.612,
        rank: 7,
        trend: "stable",
        post_count: 3210
      },
      {
        topic_id: 8,
        name: "Flask后端服务",
        keywords: ["Flask", "Python", "RESTful", "API"],
        composite_score: 0.612,
        sentiment_avg: 0.55,
        popularity_score: 0.578,
        rank: 8,
        trend: "up",
        post_count: 2109
      }
    ];
  }

  /**
   * 模拟词云数据
   */
  static getMockWordcloudData(): WordCloudItem[] {
    return [
      { name: "情感分析", value: 100, sentiment: "positive" },
      { name: "热度排序", value: 95, sentiment: "positive" },
      { name: "微博数据", value: 90, sentiment: "neutral" },
      { name: "Spark处理", value: 85, sentiment: "positive" },
      { name: "实时监控", value: 80, sentiment: "neutral" },
      { name: "数据可视化", value: 75, sentiment: "positive" },
      { name: "毕业设计", value: 70, sentiment: "positive" },
      { name: "前端架构", value: 65, sentiment: "neutral" },
      { name: "后端API", value: 60, sentiment: "neutral" },
      { name: "深度学习", value: 55, sentiment: "positive" },
      { name: "BERT模型", value: 52, sentiment: "positive" },
      { name: "分布式", value: 48, sentiment: "neutral" },
      { name: "HBase", value: 45, sentiment: "neutral" },
      { name: "Vue3", value: 42, sentiment: "positive" },
      { name: "TypeScript", value: 40, sentiment: "neutral" },
    ];
  }

  /**
   * 模拟情感分析结果
   */
  static getMockSentimentResult(text: string): {
    text: string;
    sentiment: string;
    score: number;
    confidence: number;
    method: string;
  } {
    // 简单规则判断
    const positiveWords = ['好', '喜欢', '优秀', '棒', '赞', '感谢', '开心', '成功'];
    const negativeWords = ['差', '讨厌', '糟糕', '失败', '难过', '问题', '错误'];

    let sentiment = 'neutral';
    let score = 0;

    for (const word of positiveWords) {
      if (text.includes(word)) {
        sentiment = 'positive';
        score += 0.2;
      }
    }

    for (const word of negativeWords) {
      if (text.includes(word)) {
        sentiment = 'negative';
        score -= 0.2;
      }
    }

    score = Math.max(-1, Math.min(1, score));

    return {
      text,
      sentiment,
      score: Math.round(score * 100) / 100,
      confidence: 0.75 + Math.random() * 0.2,
      method: 'rule-based (fallback)'
    };
  }

  /**
   * 模拟三维度配置
   */
  static getMockTriDimensionConfig() {
    return {
      sentiment_weight: 0.6,
      popularity_weight: 0.4,
      time_decay_hours: 24
    };
  }

  /**
   * 模拟数据流概览
   */
  static getMockDataflowOverview() {
    return {
      crawl_stats: {
        total: 12,
        completed: 11,
        running: 1,
        failed: 0
      },
      data_stats: {
        total_weibos: 156789,
        analyzed: 145678,
        pending: 11111
      },
      last_update: new Date().toISOString()
    };
  }

  /**
   * 模拟Spark信息
   */
  static getMockSparkInfo() {
    return {
      spark_available: true,
      mode: 'pseudo-distributed',
      master_url: 'local[*]',
      spark_version: '3.0.0',
      executors: 4,
      memory_per_executor: '2g'
    };
  }
}

export default FallbackDataService;
