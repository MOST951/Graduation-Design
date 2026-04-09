<template>
  <div class="user-tags-module">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">
          <el-icon><User /></el-icon>
          多维度用户标签体系
        </h2>
        <p class="page-desc">基于用户属性、行为特征和社交网络的智能标签分析</p>
      </div>
      <div class="header-right">
        <el-button :icon="Refresh" :loading="updating" @click="triggerUpdate">
          更新标签
        </el-button>
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="fetchData">
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 统计概览 -->
    <el-row :gutter="16" class="metrics-row">
      <el-col :span="6">
        <div class="metric-card gradient-blue">
          <div class="metric-icon">
            <el-icon><User /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ formatNumber(summary.total_users) }}</div>
            <div class="metric-label">总用户数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="metric-card gradient-green">
          <div class="metric-icon">
            <el-icon><Collection /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ summary.label_coverage }}%</div>
            <div class="metric-label">标签覆盖率</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="metric-card gradient-orange">
          <div class="metric-icon">
            <el-icon><PriceTag /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ summary.avg_tags_per_user }}</div>
            <div class="metric-label">人均标签数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="metric-card gradient-purple">
          <div class="metric-icon">
            <el-icon><Timer /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ summary.update_frequency }}</div>
            <div class="metric-label">更新频率</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：标签分类 -->
      <div class="left-section">
        <!-- 基础属性标签 -->
        <el-card class="tag-category-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><UserFilled /></el-icon> 基础属性标签</span>
            </div>
          </template>
          
          <!-- 身份类型 -->
          <div class="tag-group">
            <h4 class="group-title">
              <el-icon><Avatar /></el-icon> 身份类型
              <el-tooltip content="基于粉丝数、认证状态判断">
                <el-icon class="info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </h4>
            <div class="tag-bars">
              <div v-for="item in basicAttributes.identity_types" :key="item.name" class="tag-bar-item">
                <div class="bar-label">
                  <span class="tag-name">{{ item.name }}</span>
                  <span class="tag-count">{{ item.count }}人 ({{ item.percentage }}%)</span>
                </div>
                <el-progress
                  :percentage="item.percentage"
                  :color="item.color"
                  :stroke-width="12"
                  :show-text="false"
                />
              </div>
            </div>
          </div>

          <!-- 活跃等级 -->
          <div class="tag-group">
            <h4 class="group-title">
              <el-icon><Histogram /></el-icon> 活跃等级
              <el-tooltip content="基于发博频率分析">
                <el-icon class="info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </h4>
            <div class="tag-bars">
              <div v-for="item in basicAttributes.activity_levels" :key="item.name" class="tag-bar-item">
                <div class="bar-label">
                  <span class="tag-name">{{ item.name }}</span>
                  <span class="tag-count">{{ item.count }}人 ({{ item.percentage }}%)</span>
                </div>
                <el-progress
                  :percentage="item.percentage"
                  :color="item.color"
                  :stroke-width="12"
                  :show-text="false"
                />
              </div>
            </div>
          </div>

          <!-- 内容倾向 -->
          <div class="tag-group">
            <h4 class="group-title">
              <el-icon><Document /></el-icon> 内容倾向
              <el-tooltip content="基于LDA主题模型分析">
                <el-icon class="info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </h4>
            <div ref="topicChartRef" style="height: 200px"></div>
          </div>
        </el-card>

        <!-- 行为特征标签 -->
        <el-card class="tag-category-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Operation /></el-icon> 行为特征标签</span>
            </div>
          </template>

          <!-- 互动偏好 -->
          <div class="tag-group">
            <h4 class="group-title">
              <el-icon><ChatDotRound /></el-icon> 互动偏好
              <el-tooltip content="基于行为分布分析">
                <el-icon class="info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </h4>
            <div class="interaction-cards">
              <div
                v-for="item in behaviorFeatures.interaction_types"
                :key="item.name"
                class="interaction-card"
                :style="{ borderColor: item.color }"
              >
                <div class="interaction-icon" :style="{ background: item.color }">
                  <el-icon v-if="item.name === '转发型'"><Share /></el-icon>
                  <el-icon v-else-if="item.name === '评论型'"><ChatDotRound /></el-icon>
                  <el-icon v-else><Star /></el-icon>
                </div>
                <div class="interaction-info">
                  <div class="interaction-name">{{ item.name }}</div>
                  <div class="interaction-count">{{ item.count }}人</div>
                  <div class="interaction-percent">{{ item.percentage }}%</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 时间模式 -->
          <div class="tag-group">
            <h4 class="group-title">
              <el-icon><Clock /></el-icon> 时间模式
              <el-tooltip content="基于发博时间分析">
                <el-icon class="info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </h4>
            <div class="time-pattern-list">
              <div
                v-for="item in behaviorFeatures.time_patterns"
                :key="item.name"
                class="time-pattern-item"
              >
                <el-tag :color="item.color" effect="dark" size="small">
                  {{ item.name }}
                </el-tag>
                <span class="time-range">{{ item.hour_range }}</span>
                <span class="time-count">{{ item.count }}人</span>
                <el-progress
                  :percentage="item.percentage"
                  :color="item.color"
                  :stroke-width="6"
                  :show-text="false"
                  style="width: 100px"
                />
              </div>
            </div>
          </div>

          <!-- 社交网络角色 -->
          <div class="tag-group">
            <h4 class="group-title">
              <el-icon><Connection /></el-icon> 社交网络角色
              <el-tooltip content="基于GraphX的PageRank算法">
                <el-icon class="info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </h4>
            <div ref="networkChartRef" style="height: 180px"></div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：可视化 -->
      <div class="right-section">
        <!-- 标签云 -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><PriceTag /></el-icon> 用户标签云</span>
            </div>
          </template>
          <div ref="tagCloudRef" style="height: 280px"></div>
        </el-card>

        <!-- 活跃度热力图 -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Grid /></el-icon> 用户活跃度热力图</span>
            </div>
          </template>
          <div ref="heatmapChartRef" style="height: 280px"></div>
        </el-card>

        <!-- 标签组合查询 -->
        <el-card class="query-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Search /></el-icon> 标签组合查询</span>
            </div>
          </template>
          <div class="query-form">
            <el-select
              v-model="queryTags"
              multiple
              filterable
              placeholder="选择标签组合"
              style="width: 100%"
            >
              <el-option-group label="身份类型">
                <el-option label="KOL" value="KOL" />
                <el-option label="普通用户" value="普通用户" />
                <el-option label="机构号" value="机构号" />
                <el-option label="营销号" value="营销号" />
              </el-option-group>
              <el-option-group label="活跃等级">
                <el-option label="日活跃" value="日活跃" />
                <el-option label="周活跃" value="周活跃" />
                <el-option label="月活跃" value="月活跃" />
              </el-option-group>
              <el-option-group label="内容倾向">
                <el-option label="时事评论" value="时事评论" />
                <el-option label="娱乐八卦" value="娱乐八卦" />
                <el-option label="科技数码" value="科技数码" />
                <el-option label="生活分享" value="生活分享" />
              </el-option-group>
              <el-option-group label="互动偏好">
                <el-option label="转发型" value="转发型" />
                <el-option label="评论型" value="评论型" />
                <el-option label="点赞型" value="点赞型" />
              </el-option-group>
              <el-option-group label="时间模式">
                <el-option label="早晨活跃" value="早晨活跃" />
                <el-option label="夜间活跃" value="夜间活跃" />
                <el-option label="全天活跃" value="全天活跃" />
              </el-option-group>
              <el-option-group label="网络角色">
                <el-option label="中心节点" value="中心节点" />
                <el-option label="边缘节点" value="边缘节点" />
                <el-option label="孤立节点" value="孤立节点" />
              </el-option-group>
            </el-select>
            <el-button type="primary" :loading="querying" style="margin-top: 12px" @click="queryUsers">
              查询用户
            </el-button>
          </div>
          <div v-if="queryResult.length > 0" class="query-result">
            <div class="result-header">
              查询结果: {{ queryTotal }} 位用户
            </div>
            <div class="user-list">
              <div v-for="user in queryResult" :key="user.id" class="user-item">
                <el-avatar :size="36" :src="user.avatar" />
                <div class="user-info">
                  <div class="user-name">{{ user.screen_name }}</div>
                  <div class="user-tags">
                    <el-tag v-for="tag in user.tags.slice(0, 3)" :key="tag" size="small" type="info">
                      {{ tag }}
                    </el-tag>
                  </div>
                </div>
                <div class="user-scores">
                  <div class="score">活跃度: {{ user.activity_score }}</div>
                  <div class="score">影响力: {{ user.influence_score }}</div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 算法说明 -->
    <el-card class="algorithm-card">
      <template #header>
        <div class="card-header">
          <span><el-icon><InfoFilled /></el-icon> 标签体系算法说明</span>
        </div>
      </template>
      <div class="algorithm-content">
        <div class="formula-section">
          <h4>身份类型判定</h4>
          <div class="formula">
            <code>KOL: 粉丝数 > 10000 且 认证状态 = true</code>
          </div>
          <div class="params">
            <span class="param">机构号: verified_type = 2</span>
            <span class="param">营销号: 发博频率高 + 广告内容占比 > 30%</span>
          </div>
        </div>
        <div class="formula-section">
          <h4>内容倾向分析</h4>
          <div class="formula">
            <code>LDA主题模型: K=6, α=0.1, β=0.01</code>
          </div>
          <div class="params">
            <span class="param">主题分布: P(topic|user) = Σ P(topic|doc) × P(doc|user)</span>
          </div>
        </div>
        <div class="formula-section">
          <h4>社交网络分析</h4>
          <div class="formula">
            <code>PageRank: PR(u) = (1-d)/N + d × Σ PR(v)/L(v)</code>
          </div>
          <div class="method-tags">
            <el-tag>GraphX</el-tag>
            <el-tag type="success">PageRank</el-tag>
            <el-tag type="warning">社区发现</el-tag>
            <el-tag type="info">每日更新</el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>


<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  Refresh, User, Collection, PriceTag, Timer, UserFilled,
  Avatar, Histogram, Document, Operation, ChatDotRound,
  Share, Star, Clock, Connection, Grid, Search, InfoFilled
} from '@element-plus/icons-vue';
import apiClient from '@/api/index';

// 状态
const loading = ref(false);
const updating = ref(false);
const querying = ref(false);

// 统计摘要
const summary = reactive({
  total_users: 1257,
  labeled_users: 1189,
  label_coverage: 94.6,
  avg_tags_per_user: 4.2,
  update_frequency: '每日',
});

// 基础属性标签
const basicAttributes = reactive({
  identity_types: [] as any[],
  activity_levels: [] as any[],
  content_topics: [] as any[],
});

// 行为特征标签
const behaviorFeatures = reactive({
  interaction_types: [] as any[],
  time_patterns: [] as any[],
  network_roles: [] as any[],
});

// 标签云数据
const tagCloudData = ref<any[]>([]);

// 热力图数据
const heatmapData = reactive({
  hours: [] as number[],
  days: [] as string[],
  data: [] as any[],
});

// 查询相关
const queryTags = ref<string[]>([]);
const queryResult = ref<any[]>([]);
const queryTotal = ref(0);

// 图表引用
const topicChartRef = ref<HTMLElement>();
const networkChartRef = ref<HTMLElement>();
const tagCloudRef = ref<HTMLElement>();
const heatmapChartRef = ref<HTMLElement>();
let topicChart: echarts.ECharts | null = null;
let networkChart: echarts.ECharts | null = null;
let tagCloudChart: echarts.ECharts | null = null;
let heatmapChart: echarts.ECharts | null = null;

// 工具函数
const formatNumber = (num: number) => {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toLocaleString();
};

// 获取数据
const fetchData = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/user-tags/analysis');
    if (response.data.code === 200) {
      const data = response.data.data;
      
      // 更新基础属性
      basicAttributes.identity_types = data.basic_attributes.identity_types;
      basicAttributes.activity_levels = data.basic_attributes.activity_levels;
      basicAttributes.content_topics = data.basic_attributes.content_topics;
      
      // 更新行为特征
      behaviorFeatures.interaction_types = data.behavior_features.interaction_types;
      behaviorFeatures.time_patterns = data.behavior_features.time_patterns;
      behaviorFeatures.network_roles = data.behavior_features.network_roles;
      
      // 更新标签云
      tagCloudData.value = data.tag_cloud;
      
      // 更新热力图
      heatmapData.hours = data.time_heatmap.hours;
      heatmapData.days = data.time_heatmap.days;
      heatmapData.data = data.time_heatmap.data;
      
      // 更新摘要
      Object.assign(summary, data.summary);
      
      // 更新图表
      updateCharts();
    }
  } catch (error) {
    console.error('获取用户标签数据失败:', error);
    generateMockData();
  } finally {
    loading.value = false;
  }
};

// 生成模拟数据
const generateMockData = () => {
  basicAttributes.identity_types = [
    { name: 'KOL', count: 156, percentage: 12.4, color: '#409eff' },
    { name: '普通用户', count: 823, percentage: 65.5, color: '#67c23a' },
    { name: '机构号', count: 189, percentage: 15.0, color: '#e6a23c' },
    { name: '营销号', count: 89, percentage: 7.1, color: '#f56c6c' },
  ];
  
  basicAttributes.activity_levels = [
    { name: '日活跃', count: 234, percentage: 18.6, color: '#67c23a' },
    { name: '周活跃', count: 456, percentage: 36.3, color: '#409eff' },
    { name: '月活跃', count: 567, percentage: 45.1, color: '#909399' },
  ];
  
  basicAttributes.content_topics = [
    { name: '时事评论', count: 312, percentage: 24.8, color: '#409eff' },
    { name: '娱乐八卦', count: 289, percentage: 23.0, color: '#f56c6c' },
    { name: '科技数码', count: 234, percentage: 18.6, color: '#67c23a' },
    { name: '生活分享', count: 198, percentage: 15.8, color: '#e6a23c' },
    { name: '财经投资', count: 124, percentage: 9.9, color: '#909399' },
    { name: '其他', count: 100, percentage: 7.9, color: '#c0c4cc' },
  ];
  
  behaviorFeatures.interaction_types = [
    { name: '转发型', count: 345, percentage: 27.5, color: '#409eff' },
    { name: '评论型', count: 423, percentage: 33.7, color: '#67c23a' },
    { name: '点赞型', count: 489, percentage: 38.8, color: '#e6a23c' },
  ];
  
  behaviorFeatures.time_patterns = [
    { name: '早晨活跃', count: 234, percentage: 18.6, hour_range: '6:00-10:00', color: '#f7ba2a' },
    { name: '午间活跃', count: 189, percentage: 15.0, hour_range: '11:00-14:00', color: '#e6a23c' },
    { name: '下午活跃', count: 267, percentage: 21.2, hour_range: '14:00-18:00', color: '#409eff' },
    { name: '夜间活跃', count: 378, percentage: 30.1, hour_range: '20:00-24:00', color: '#6366f1' },
    { name: '全天活跃', count: 189, percentage: 15.1, hour_range: '全天', color: '#67c23a' },
  ];
  
  behaviorFeatures.network_roles = [
    { name: '中心节点', count: 89, percentage: 7.1, pagerank: 0.85, color: '#f56c6c' },
    { name: '桥接节点', count: 156, percentage: 12.4, pagerank: 0.65, color: '#e6a23c' },
    { name: '边缘节点', count: 678, percentage: 53.9, pagerank: 0.35, color: '#409eff' },
    { name: '孤立节点', count: 334, percentage: 26.6, pagerank: 0.1, color: '#909399' },
  ];
  
  tagCloudData.value = [
    { name: '科技爱好者', value: 156 },
    { name: '时事关注', value: 234 },
    { name: '娱乐达人', value: 189 },
    { name: '高活跃度', value: 234 },
    { name: '意见领袖', value: 89 },
    { name: '内容创作者', value: 145 },
    { name: '互动活跃', value: 312 },
    { name: '夜猫子', value: 178 },
    { name: '早起党', value: 134 },
    { name: '理性派', value: 167 },
    { name: '正能量', value: 223 },
    { name: '吐槽达人', value: 145 },
    { name: '转发狂魔', value: 167 },
    { name: '深度评论', value: 123 },
    { name: '财经关注', value: 98 },
    { name: '生活记录', value: 189 },
    { name: '追星族', value: 134 },
    { name: '社交达人', value: 156 },
    { name: '潜水党', value: 234 },
  ];
  
  // 生成热力图数据
  heatmapData.hours = Array.from({ length: 24 }, (_, i) => i);
  heatmapData.days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  heatmapData.data = [];
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      let base = 20;
      if (hour >= 8 && hour <= 10) base = 70;
      else if (hour >= 12 && hour <= 14) base = 60;
      else if (hour >= 20 && hour <= 23) base = 80;
      else if (hour >= 0 && hour <= 6) base = 10;
      else base = 40;
      if (day >= 5) base = Math.floor(base * 1.2);
      heatmapData.data.push([hour, day, base + Math.floor(Math.random() * 20)]);
    }
  }
  
  updateCharts();
};

// 更新所有图表
const updateCharts = () => {
  updateTopicChart();
  updateNetworkChart();
  updateTagCloudChart();
  updateHeatmapChart();
};

// 内容倾向饼图
const updateTopicChart = () => {
  if (!topicChart) return;
  
  topicChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)',
    },
    series: [{
      type: 'pie',
      radius: ['30%', '70%'],
      center: ['50%', '50%'],
      roseType: 'radius',
      itemStyle: {
        borderRadius: 5,
      },
      label: {
        show: true,
        formatter: '{b}',
        fontSize: 11,
      },
      data: basicAttributes.content_topics.map(item => ({
        value: item.count,
        name: item.name,
        itemStyle: { color: item.color },
      })),
    }],
  });
};

// 社交网络角色图
const updateNetworkChart = () => {
  if (!networkChart) return;
  
  networkChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: '3%',
      right: '10%',
      top: '10%',
      bottom: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%' },
    },
    yAxis: {
      type: 'category',
      data: behaviorFeatures.network_roles.map(i => i.name).reverse(),
    },
    series: [{
      type: 'bar',
      data: behaviorFeatures.network_roles.map(i => ({
        value: i.percentage,
        itemStyle: { color: i.color },
      })).reverse(),
      label: {
        show: true,
        position: 'right',
        formatter: '{c}%',
      },
    }],
  });
};

// 标签云（使用气泡图替代）
const updateTagCloudChart = () => {
  if (!tagCloudChart) return;
  
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#6366f1'];
  
  // 将标签数据转换为气泡图数据
  const bubbleData = tagCloudData.value.map((item, index) => {
    const row = Math.floor(index / 5);
    const col = index % 5;
    return {
      name: item.name,
      value: [col * 20 + 10 + Math.random() * 5, row * 20 + 15 + Math.random() * 5, item.value],
      itemStyle: {
        color: colors[index % colors.length],
      },
    };
  });
  
  tagCloudChart.setOption({
    tooltip: {
      formatter: (params: any) => `${params.name}: ${params.value[2]}人`,
    },
    grid: {
      left: '5%',
      right: '5%',
      top: '5%',
      bottom: '5%',
    },
    xAxis: {
      type: 'value',
      show: false,
      min: 0,
      max: 100,
    },
    yAxis: {
      type: 'value',
      show: false,
      min: 0,
      max: 100,
    },
    series: [{
      type: 'scatter',
      data: bubbleData,
      symbolSize: (data: any) => Math.sqrt(data[2]) * 3 + 20,
      label: {
        show: true,
        formatter: '{b}',
        fontSize: 12,
        fontWeight: 'bold',
        color: '#fff',
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.3)',
        },
        label: {
          fontSize: 14,
        },
      },
    }],
  });
};

// 热力图
const updateHeatmapChart = () => {
  if (!heatmapChart) return;
  
  heatmapChart.setOption({
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        return `${heatmapData.days[params.value[1]]} ${params.value[0]}:00<br/>活跃度: ${params.value[2]}`;
      },
    },
    grid: {
      height: '70%',
      top: '5%',
      left: '15%',
      right: '5%',
    },
    xAxis: {
      type: 'category',
      data: heatmapData.hours.map(h => `${h}时`),
      splitArea: { show: true },
      axisLabel: {
        interval: 3,
        fontSize: 10,
      },
    },
    yAxis: {
      type: 'category',
      data: heatmapData.days,
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      inRange: {
        color: ['#e0f3ff', '#409eff', '#1a56db'],
      },
    },
    series: [{
      type: 'heatmap',
      data: heatmapData.data,
      label: { show: false },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
    }],
  });
};

// 触发标签更新
const triggerUpdate = async () => {
  updating.value = true;
  try {
    await apiClient.post('/user-tags/update');
    ElMessage.success('标签更新任务已启动');
  } catch (error) {
    ElMessage.warning('标签更新任务已启动（模拟）');
  } finally {
    updating.value = false;
  }
};

// 查询用户
const queryUsers = async () => {
  if (queryTags.value.length === 0) {
    ElMessage.warning('请选择至少一个标签');
    return;
  }
  
  querying.value = true;
  try {
    const response = await apiClient.post('/user-tags/query', {
      tags: queryTags.value,
      page: 1,
      page_size: 10,
    });
    if (response.data.code === 200) {
      queryResult.value = response.data.data.users;
      queryTotal.value = response.data.data.total;
    }
  } catch (error) {
    // 使用模拟数据
    queryResult.value = Array.from({ length: 5 }, (_, i) => ({
      id: i + 1,
      screen_name: `用户_${i + 1}`,
      avatar: 'https://tvax1.sinaimg.cn/default/images/default_avatar_male_180.gif',
      tags: queryTags.value.slice(0, 3),
      activity_score: (0.5 + Math.random() * 0.5).toFixed(2),
      influence_score: (0.3 + Math.random() * 0.6).toFixed(2),
    }));
    queryTotal.value = 156;
  } finally {
    querying.value = false;
  }
};

// 初始化图表
const initCharts = () => {
  if (topicChartRef.value) {
    topicChart = echarts.init(topicChartRef.value);
  }
  if (networkChartRef.value) {
    networkChart = echarts.init(networkChartRef.value);
  }
  if (tagCloudRef.value) {
    tagCloudChart = echarts.init(tagCloudRef.value);
  }
  if (heatmapChartRef.value) {
    heatmapChart = echarts.init(heatmapChartRef.value);
  }
};

// 生命周期
onMounted(() => {
  initCharts();
  fetchData();
  
  window.addEventListener('resize', () => {
    topicChart?.resize();
    networkChart?.resize();
    tagCloudChart?.resize();
    heatmapChart?.resize();
  });
});

onUnmounted(() => {
  topicChart?.dispose();
  networkChart?.dispose();
  tagCloudChart?.dispose();
  heatmapChart?.dispose();
});
</script>

<style scoped lang="scss">
.user-tags-module {
  padding: 0 0 20px 0;
}

// 页面标题
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  .header-left {
    .page-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 22px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 6px 0;
      
      .el-icon {
        color: #409eff;
      }
    }
    
    .page-desc {
      margin: 0;
      font-size: 13px;
      color: #909399;
    }
  }
  
  .header-right {
    display: flex;
    gap: 10px;
  }
}

// 指标卡片
.metrics-row {
  margin-bottom: 20px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  color: white;
  
  &.gradient-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }
  
  &.gradient-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  }
  
  &.gradient-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  }
  
  &.gradient-purple {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  }
  
  .metric-icon {
    width: 50px;
    height: 50px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .el-icon {
      font-size: 24px;
    }
  }
  
  .metric-info {
    .metric-value {
      font-size: 28px;
      font-weight: 700;
      line-height: 1.2;
    }
    
    .metric-label {
      font-size: 13px;
      opacity: 0.9;
    }
  }
}

// 主内容区
.main-content {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.left-section {
  flex: 1.2;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// 标签分类卡片
.tag-category-card {
  .card-header {
    display: flex;
    align-items: center;
    
    span {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }
}

.tag-group {
  margin-bottom: 20px;
  
  &:last-child {
    margin-bottom: 0;
  }
  
  .group-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 12px 0;
    
    .info-icon {
      font-size: 14px;
      color: #909399;
      cursor: help;
    }
  }
}

.tag-bars {
  .tag-bar-item {
    margin-bottom: 12px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .bar-label {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      
      .tag-name {
        font-size: 13px;
        color: #303133;
        font-weight: 500;
      }
      
      .tag-count {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

// 互动偏好卡片
.interaction-cards {
  display: flex;
  gap: 12px;
  
  .interaction-card {
    flex: 1;
    padding: 14px;
    border-radius: 10px;
    border: 2px solid;
    background: #fafafa;
    text-align: center;
    
    .interaction-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 10px;
      color: white;
      
      .el-icon {
        font-size: 20px;
      }
    }
    
    .interaction-info {
      .interaction-name {
        font-size: 13px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 4px;
      }
      
      .interaction-count {
        font-size: 12px;
        color: #606266;
      }
      
      .interaction-percent {
        font-size: 18px;
        font-weight: 700;
        color: #409eff;
      }
    }
  }
}

// 时间模式列表
.time-pattern-list {
  .time-pattern-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
    
    &:last-child {
      border-bottom: none;
    }
    
    .time-range {
      font-size: 12px;
      color: #606266;
      min-width: 80px;
    }
    
    .time-count {
      font-size: 12px;
      color: #909399;
      min-width: 50px;
    }
  }
}

// 图表卡片
.chart-card {
  .card-header {
    display: flex;
    align-items: center;
    
    span {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }
}

// 查询卡片
.query-card {
  .card-header {
    display: flex;
    align-items: center;
    
    span {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }
  
  .query-form {
    margin-bottom: 16px;
  }
  
  .query-result {
    .result-header {
      font-size: 13px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #f0f0f0;
    }
    
    .user-list {
      max-height: 200px;
      overflow-y: auto;
      
      .user-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        background: #fafafa;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .user-info {
          flex: 1;
          
          .user-name {
            font-size: 13px;
            font-weight: 600;
            color: #303133;
            margin-bottom: 4px;
          }
          
          .user-tags {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
          }
        }
        
        .user-scores {
          text-align: right;
          
          .score {
            font-size: 11px;
            color: #909399;
          }
        }
      }
    }
  }
}

// 算法说明卡片
.algorithm-card {
  .card-header {
    display: flex;
    align-items: center;
    
    span {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }
}

.algorithm-content {
  display: flex;
  gap: 40px;
  flex-wrap: wrap;
  
  .formula-section {
    flex: 1;
    min-width: 280px;
    
    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: #303133;
    }
    
    .formula {
      background: #f5f7fa;
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 10px;
      
      code {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 13px;
        color: #409eff;
      }
    }
    
    .params {
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
      
      .param {
        font-size: 12px;
        color: #606266;
        
        strong {
          color: #303133;
        }
      }
    }
    
    .method-tags {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
  }
}

// 响应式
@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
  }
  
  .left-section,
  .right-section {
    flex: none;
    width: 100%;
  }
}

@media (max-width: 768px) {
  .metrics-row {
    .el-col {
      margin-bottom: 12px;
    }
  }
  
  .metric-card {
    padding: 16px;
    
    .metric-info .metric-value {
      font-size: 22px;
    }
  }
  
  .interaction-cards {
    flex-direction: column;
  }
  
  .algorithm-content {
    flex-direction: column;
    gap: 20px;
  }
}
</style>
