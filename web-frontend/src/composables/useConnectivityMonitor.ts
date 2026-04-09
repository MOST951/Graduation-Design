/**
 * 数据连通性监控 Composable
 * 用于监控前端与后端API的连通状态
 * 增强版：包含详细诊断信息和降级提示
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';

export interface EndpointStatus {
  name: string;
  url: string;
  connected: boolean;
  latency: number;
  lastError?: string;
  usingFallback?: boolean;
}

export interface ConnectivityStatus {
  hotSearch: EndpointStatus;
  topics: EndpointStatus;
  sentiment: EndpointStatus;
  collection: EndpointStatus;
  dataflow: EndpointStatus;
  spark: EndpointStatus;
  lastCheck: Date | null;
  errorMessages: Record<string, string>;
}

const defaultEndpoint = (name: string, url: string): EndpointStatus => ({
  name,
  url,
  connected: false,
  latency: 0,
});

export function useConnectivityMonitor() {
  const status = ref<ConnectivityStatus>({
    hotSearch: defaultEndpoint('热搜数据', '/api/analysis/hot-search/live'),
    topics: defaultEndpoint('话题排序', '/api/topics/ranked'),
    sentiment: defaultEndpoint('情感分析', '/api/sentiment/analyze'),
    collection: defaultEndpoint('数据采集', '/api/weibo/crawl/start'),
    dataflow: defaultEndpoint('数据流', '/api/weibo/dataflow/overview'),
    spark: defaultEndpoint('Spark状态', '/api/weibo/spark/info'),
    lastCheck: null,
    errorMessages: {},
  });

  const checking = ref(false);
  let intervalId: ReturnType<typeof setInterval> | null = null;

  // 测试单个端点
  const testEndpoint = async (
    name: string,
    url: string,
    method: 'GET' | 'POST' = 'GET',
    data?: any
  ): Promise<EndpointStatus> => {
    const startTime = Date.now();
    try {
      const options: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
      };
      if (data && method === 'POST') {
        options.body = JSON.stringify(data);
      }

      const response = await fetch(url, options);
      const latency = Date.now() - startTime;

      return {
        name,
        url,
        connected: response.ok,
        latency,
        lastError: response.ok ? undefined : `HTTP ${response.status}`,
        usingFallback: false,
      };
    } catch (error: any) {
      return {
        name,
        url,
        connected: false,
        latency: Date.now() - startTime,
        lastError: error.message || '网络错误',
        usingFallback: true,
      };
    }
  };

  // 检查所有连通性
  const checkConnectivity = async () => {
    if (checking.value) return;
    
    checking.value = true;
    status.value.errorMessages = {};
    console.log('[ConnectivityMonitor] 开始检查数据连通性...');

    try {
      const [hotSearch, topics, sentiment, collection, dataflow, spark] = await Promise.all([
        testEndpoint('热搜数据', '/api/analysis/hot-search/live'),
        testEndpoint('话题排序', '/api/topics/ranked'),
        testEndpoint('情感分析', '/api/sentiment/analyze', 'POST', { text: '测试' }),
        testEndpoint('数据采集', '/api/weibo/crawl/tasks'),
        testEndpoint('数据流', '/api/weibo/dataflow/overview'),
        testEndpoint('Spark状态', '/api/weibo/spark/info'),
      ]);

      // 更新状态
      status.value.hotSearch = hotSearch;
      status.value.topics = topics;
      status.value.sentiment = sentiment;
      status.value.collection = collection;
      status.value.dataflow = dataflow;
      status.value.spark = spark;
      status.value.lastCheck = new Date();

      // 记录错误信息
      if (!hotSearch.connected) status.value.errorMessages.hotSearch = hotSearch.lastError || '未知错误';
      if (!topics.connected) status.value.errorMessages.topics = topics.lastError || '未知错误';
      if (!sentiment.connected) status.value.errorMessages.sentiment = sentiment.lastError || '未知错误';
      if (!collection.connected) status.value.errorMessages.collection = collection.lastError || '未知错误';
      if (!dataflow.connected) status.value.errorMessages.dataflow = dataflow.lastError || '未知错误';
      if (!spark.connected) status.value.errorMessages.spark = spark.lastError || '未知错误';

      console.log('[ConnectivityMonitor] 检查完成:', {
        hotSearch: hotSearch.connected,
        topics: topics.connected,
        sentiment: sentiment.connected,
        collection: collection.connected,
        dataflow: dataflow.connected,
        spark: spark.connected,
      });
    } catch (error) {
      console.error('[ConnectivityMonitor] 检查失败:', error);
    } finally {
      checking.value = false;
    }
  };

  // 计算总体连通性百分比
  const overallConnectivity = computed(() => {
    const endpoints = [
      status.value.hotSearch,
      status.value.topics,
      status.value.sentiment,
      status.value.collection,
      status.value.dataflow,
      status.value.spark,
    ];
    const connected = endpoints.filter(e => e.connected).length;
    return Math.round((connected / endpoints.length) * 100);
  });

  // 获取连通性状态标签类型
  const connectivityTagType = computed(() => {
    const percentage = overallConnectivity.value;
    if (percentage >= 80) return 'success';
    if (percentage >= 50) return 'warning';
    return 'danger';
  });

  // 获取连通性状态文本
  const connectivityText = computed(() => {
    const percentage = overallConnectivity.value;
    if (percentage >= 100) return '全部连通';
    if (percentage >= 80) return '大部分连通';
    if (percentage >= 50) return '部分连通';
    if (percentage > 0) return '连通性差';
    return '使用模拟数据';
  });

  // 获取连通性摘要
  const connectivitySummary = computed(() => {
    const endpoints = [
      status.value.hotSearch,
      status.value.topics,
      status.value.sentiment,
      status.value.collection,
      status.value.dataflow,
      status.value.spark,
    ];
    const connected = endpoints.filter(e => e.connected).length;
    return {
      connected,
      total: endpoints.length,
      percentage: overallConnectivity.value,
      lastCheck: status.value.lastCheck,
    };
  });

  // 启动定时检查
  const startMonitoring = (intervalMs: number = 2 * 60 * 1000) => {
    // 立即检查一次
    checkConnectivity();

    // 设置定时检查
    if (intervalId) {
      clearInterval(intervalId);
    }
    intervalId = setInterval(checkConnectivity, intervalMs);
    console.log(`[ConnectivityMonitor] 启动监控，间隔 ${intervalMs / 1000} 秒`);
  };

  // 停止监控
  const stopMonitoring = () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
      console.log('[ConnectivityMonitor] 停止监控');
    }
  };

  // 生命周期
  onMounted(() => {
    startMonitoring();
  });

  onUnmounted(() => {
    stopMonitoring();
  });

  return {
    status,
    checking,
    checkConnectivity,
    overallConnectivity,
    connectivityTagType,
    connectivityText,
    connectivitySummary,
    startMonitoring,
    stopMonitoring,
  };
}

export default useConnectivityMonitor;
