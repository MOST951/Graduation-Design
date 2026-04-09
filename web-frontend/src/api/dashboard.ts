// api/dashboard.ts

// 模拟API延迟
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 获取仪表盘核心数据
 */
export async function getDashboardData(params: { period: string; dateRange: Date[] }) {
  await sleep(500); // 模拟网络延迟

  console.log('Fetching dashboard data with params:', params);

  // 模拟后端返回的数据结构
  return {
    overviewCards: [
      {
        title: '总分析量',
        value: '2,543,128',
        icon: 'el-icon-data-analysis',
        color: '#409EFF',
        trend: '+15.2%',
        trendIcon: 'el-icon-top',
        trendClass: 'positive'
      },
      {
        title: '正面情感',
        value: '1,890,331',
        icon: 'el-icon-sunny',
        color: '#67C23A',
        trend: '+12.8%',
        trendIcon: 'el-icon-top',
        trendClass: 'positive'
      },
      {
        title: '负面情感',
        value: '312,450',
        icon: 'el-icon-cloudy',
        color: '#F56C6C',
        trend: '-2.1%',
        trendIcon: 'el-icon-bottom',
        trendClass: 'negative'
      },
      {
        title: '实时任务数',
        value: '25',
        icon: 'el-icon-time',
        color: '#E6A23C',
        trend: '+3',
        trendIcon: 'el-icon-top',
        trendClass: 'positive'
      }
    ],
    sentimentDistribution: {
      positive: 1890331,
      negative: 312450,
      neutral: 340347
    },
    trendData: {
      dates: ['2023-12-01', '2023-12-02', '2023-12-03', '2023-12-04', '2023-12-05', '2023-12-06', '2023-12-07'],
      positive: [1200, 1320, 1010, 1340, 900, 2300, 2100],
      negative: [220, 182, 191, 234, 290, 330, 310]
    }
  };
}

/**
 * 注意：在实际项目中，getRealtimeStream会通过WebSocket实现，这里仅作示意。
 * WebSocket连接逻辑已移至组件内部。
 */
export function getRealtimeStream() {
  // 此函数在新的实现中不再需要，因为WebSocket连接在组件中直接处理。
}

/**
 * 获取趋势数据（在新的实现中，此逻辑合并到getDashboardData中）
 */
export async function getTrendData(params: { dateRange: Date[] }) {
  // 此函数在新的实现中不再需要
}
