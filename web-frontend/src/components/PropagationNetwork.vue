<template>
  <div class="propagation-network">
    <div class="network-header">
      <h3>
        <el-icon><Share /></el-icon>
        微博传播路径网络图
      </h3>
      <div class="header-actions">
        <el-button type="primary" :icon="Refresh" @click="loadNetwork" :loading="loading">
          刷新数据
        </el-button>
        <el-select v-model="maxNodes" style="width: 120px" @change="loadNetwork">
          <el-option label="30个节点" :value="30" />
          <el-option label="50个节点" :value="50" />
          <el-option label="80个节点" :value="80" />
        </el-select>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div class="network-stats" v-if="stats">
      <el-tag type="danger">原创博主: {{ stats.source_count }}</el-tag>
      <el-tag type="primary">总节点: {{ stats.total_nodes }}</el-tag>
      <el-tag type="success">传播链接: {{ stats.total_links }}</el-tag>
    </div>
    
    <!-- 图例 -->
    <div class="network-legend">
      <span class="legend-item">
        <span class="legend-dot" style="background: #e74c3c"></span>原创博主
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: #3498db"></span>一级传播
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: #2ecc71"></span>二级传播
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: #9b59b6"></span>三级传播
      </span>
    </div>
    
    <!-- 网络图容器 -->
    <div ref="chartRef" class="network-chart" v-loading="loading"></div>
    
    <!-- 节点详情弹窗 -->
    <el-dialog v-model="showNodeDetail" title="用户详情" width="400px">
      <div v-if="selectedNode" class="node-detail">
        <p><strong>用户名:</strong> {{ selectedNode.name }}</p>
        <p><strong>粉丝数:</strong> {{ selectedNode.value }}</p>
        <p><strong>传播层级:</strong> {{ getCategoryName(selectedNode.category) }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { Share, Refresh } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';

// 响应式数据
const chartRef = ref<HTMLElement | null>(null);
const loading = ref(false);
const maxNodes = ref(50);
const stats = ref<any>(null);
const showNodeDetail = ref(false);
const selectedNode = ref<any>(null);

let chartInstance: echarts.ECharts | null = null;

// 加载网络数据
const loadNetwork = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/api/propagation/network', {
      params: { max_nodes: maxNodes.value }
    });
    
    if (response.data.code === 200) {
      const { network, stats: networkStats } = response.data.data;
      stats.value = networkStats;
      renderChart(network);
      ElMessage.success('传播网络加载成功');
    } else {
      ElMessage.error(response.data.message || '加载失败');
    }
  } catch (error: any) {
    console.error('加载传播网络失败:', error);
    ElMessage.error('加载传播网络失败，请检查后端服务');
    // 使用演示数据
    renderDemoChart();
  } finally {
    loading.value = false;
  }
};

// 渲染图表
const renderChart = (network: any) => {
  if (!chartRef.value) return;
  
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }
  
  const option: echarts.EChartsOption = {
    title: {
      text: '',
      subtext: '节点大小表示用户影响力，点击节点查看详情',
      left: 'center',
      textStyle: { fontSize: 16 }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `<strong>${params.data.name}</strong><br/>
                  粉丝数: ${params.data.value || 0}<br/>
                  ${params.data.tooltip || ''}`;
        }
        return '';
      }
    },
    legend: {
      show: false
    },
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        name: '传播网络',
        type: 'graph',
        layout: 'force',
        data: network.nodes,
        links: network.links,
        categories: network.categories,
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 10
        },
        labelLayout: {
          hideOverlap: true
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3,
          opacity: 0.6
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4
          }
        },
        force: {
          repulsion: 200,
          gravity: 0.1,
          edgeLength: [50, 150],
          layoutAnimation: true
        }
      }
    ]
  };
  
  chartInstance.setOption(option);
  
  // 点击事件
  chartInstance.off('click');
  chartInstance.on('click', (params: any) => {
    if (params.dataType === 'node') {
      selectedNode.value = params.data;
      showNodeDetail.value = true;
    }
  });
};

// 演示数据（后端不可用时使用）
const renderDemoChart = () => {
  const demoNetwork = {
    nodes: [
      { id: '1', name: '科技博主A', symbolSize: 50, category: 0, value: 50000, itemStyle: { color: '#e74c3c' } },
      { id: '2', name: '用户101', symbolSize: 30, category: 1, value: 5000, itemStyle: { color: '#3498db' } },
      { id: '3', name: '用户102', symbolSize: 28, category: 1, value: 3000, itemStyle: { color: '#3498db' } },
      { id: '4', name: '用户103', symbolSize: 25, category: 1, value: 2000, itemStyle: { color: '#3498db' } },
      { id: '5', name: '用户201', symbolSize: 20, category: 2, value: 800, itemStyle: { color: '#2ecc71' } },
      { id: '6', name: '用户202', symbolSize: 18, category: 2, value: 500, itemStyle: { color: '#2ecc71' } },
      { id: '7', name: '用户203', symbolSize: 22, category: 2, value: 1200, itemStyle: { color: '#2ecc71' } },
      { id: '8', name: '用户301', symbolSize: 15, category: 3, value: 200, itemStyle: { color: '#9b59b6' } },
    ],
    links: [
      { source: '1', target: '2' },
      { source: '1', target: '3' },
      { source: '1', target: '4' },
      { source: '2', target: '5' },
      { source: '2', target: '6' },
      { source: '3', target: '7' },
      { source: '5', target: '8' },
    ],
    categories: [
      { name: '原创博主' },
      { name: '一级传播' },
      { name: '二级传播' },
      { name: '三级传播' },
    ]
  };
  
  stats.value = { source_count: 1, total_nodes: 8, total_links: 7 };
  renderChart(demoNetwork);
};

// 获取类别名称
const getCategoryName = (category: number) => {
  const names = ['原创博主', '一级传播', '二级传播', '三级传播'];
  return names[category] || '未知';
};

// 窗口大小变化时重绘
const handleResize = () => {
  chartInstance?.resize();
};

onMounted(() => {
  loadNetwork();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.propagation-network {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.network-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.network-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.network-stats {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.network-legend {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.network-chart {
  width: 100%;
  height: 500px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.node-detail p {
  margin: 10px 0;
  font-size: 14px;
}
</style>
