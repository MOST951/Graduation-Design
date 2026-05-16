<template>
  <div class="visualization-dashboard">
    <!-- 顶部控制栏 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h2>数据可视化</h2>
        <el-radio-group v-model="currentDashboard" size="small" @change="handleDashboardChange">
          <el-radio-button label="overview">舆情概览</el-radio-button>
          <el-radio-button label="sentiment">情感分析</el-radio-button>
          <el-radio-button label="topics">热点话题</el-radio-button>
          <el-radio-button label="users">用户画像</el-radio-button>
          <el-radio-button label="realtime">实时监控</el-radio-button>
          <el-radio-button label="propagation">传播路径</el-radio-button>
        </el-radio-group>
      </div>
      <div class="header-right">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          value-format="YYYY-MM-DD"
          :shortcuts="dateShortcuts"
          @change="handleDateChange"
        />
        <el-button :icon="Refresh" size="small" :loading="isLoading" @click="refreshData">刷新</el-button>
        <el-button :icon="FullScreen" size="small" :type="isFullscreen ? 'primary' : 'default'" @click="toggleFullscreen">
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </el-button>
        <el-dropdown @command="handleExport">
          <el-button size="small">
            导出 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="dashboard">导出仪表盘</el-dropdown-item>
              <el-dropdown-item command="png">导出为图片</el-dropdown-item>
              <el-dropdown-item command="excel">导出数据</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 舆情概览仪表盘 -->
    <div v-if="currentDashboard === 'overview'" class="dashboard-content">
      <!-- 核心指标卡片 -->
      <el-row :gutter="16" class="metric-row">
        <el-col :span="6">
          <div class="metric-card primary">
            <div class="metric-icon"><el-icon><Document /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ formatNumber(overviewData.totalPosts) }}</div>
              <div class="metric-label">微博总量</div>
              <div class="metric-trend" :class="overviewData.postsTrend >= 0 ? 'up' : 'down'">
                <el-icon><component :is="overviewData.postsTrend >= 0 ? 'CaretTop' : 'CaretBottom'" /></el-icon>
                {{ Math.abs(overviewData.postsTrend) }}%
              </div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card success">
            <div class="metric-icon"><el-icon><CircleCheck /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ overviewData.positiveRate }}%</div>
              <div class="metric-label">正面情感占比</div>
              <div class="metric-trend up"><el-icon><CaretTop /></el-icon>{{ overviewData.positiveTrend }}%</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card danger">
            <div class="metric-icon"><el-icon><CircleClose /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ overviewData.negativeRate }}%</div>
              <div class="metric-label">负面情感占比</div>
              <div class="metric-trend down"><el-icon><CaretBottom /></el-icon>{{ overviewData.negativeTrend }}%</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card warning">
            <div class="metric-icon"><el-icon><Warning /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ overviewData.hotTopics }}</div>
              <div class="metric-label">热点话题数</div>
              <div class="metric-trend up"><el-icon><CaretTop /></el-icon>{{ overviewData.topicsTrend }}%</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 图表区域 -->
      <el-row :gutter="16">
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>舆情趋势分析</span>
                <el-radio-group v-model="trendTimeRange" size="small">
                  <el-radio-button label="7d">7天</el-radio-button>
                  <el-radio-button label="30d">30天</el-radio-button>
                  <el-radio-button label="90d">90天</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div ref="trendChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>情感分布</span></template>
            <div ref="sentimentPieRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>热门话题TOP10</span></template>
            <div ref="topicsBarRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>地域分布</span></template>
            <div ref="regionMapRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 微观层面：数据明细表格 -->
      <el-card style="margin-top: 16px" class="chart-card">
        <template #header>
          <div class="card-header">
            <span>数据明细（微观分析）</span>
            <div style="display:flex;gap:8px;align-items:center">
              <el-input v-model="detailKeyword" placeholder="搜索内容关键词" size="small" style="width:180px" clearable @keyup.enter="loadWeiboDetail(1)" @clear="loadWeiboDetail(1)" />
              <el-select v-model="detailSentimentFilter" placeholder="情感筛选" size="small" style="width:120px" clearable @change="loadWeiboDetail(1)">
                <el-option label="正面" value="positive" />
                <el-option label="中性" value="neutral" />
                <el-option label="负面" value="negative" />
              </el-select>
              <el-button size="small" type="primary" @click="loadWeiboDetail(1)">查询</el-button>
            </div>
          </div>
        </template>
        <el-table :data="detailList" size="small" max-height="420" stripe highlight-current-row @row-click="showWeiboDetailDialog" style="cursor:pointer">
          <el-table-column prop="weibo_id" label="ID" width="110" show-overflow-tooltip />
          <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
          <el-table-column prop="user_name" label="用户" width="100" show-overflow-tooltip />
          <el-table-column prop="sentiment_class" label="情感" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.sentiment_class === 'positive' ? 'success' : row.sentiment_class === 'negative' ? 'danger' : 'info'" size="small">
                {{ row.sentiment_class === 'positive' ? '正面' : row.sentiment_class === 'negative' ? '负面' : '中性' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hybrid_score" label="情感分数" width="90" align="center">
            <template #default="{ row }">{{ row.hybrid_score != null ? Number(row.hybrid_score).toFixed(3) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="composite_score" label="综合得分" width="90" align="center">
            <template #default="{ row }">{{ row.composite_score != null ? Number(row.composite_score).toFixed(4) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="reposts_count" label="转发" width="70" align="center" />
          <el-table-column prop="comments_count" label="评论" width="70" align="center" />
          <el-table-column prop="attitudes_count" label="点赞" width="70" align="center" />
          <el-table-column prop="created_at" label="发布时间" width="160" show-overflow-tooltip />
        </el-table>
        <div style="display:flex;justify-content:flex-end;margin-top:12px">
          <el-pagination
            v-model:current-page="detailPage"
            :page-size="detailPageSize"
            :total="detailTotal"
            layout="total, prev, pager, next"
            small
            @current-change="loadWeiboDetail"
          />
        </div>
      </el-card>
    </div>

    <!-- 情感分析仪表盘 -->
    <div v-else-if="currentDashboard === 'sentiment'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>情感极性分布</span></template>
            <div ref="sentimentDonutRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>情感趋势对比</span>
                <el-checkbox-group v-model="sentimentTypes" size="small">
                  <el-checkbox label="positive">正面</el-checkbox>
                  <el-checkbox label="negative">负面</el-checkbox>
                  <el-checkbox label="neutral">中性</el-checkbox>
                </el-checkbox-group>
              </div>
            </template>
            <div ref="sentimentTrendRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>情感强度分布</span></template>
            <div ref="intensityHistogramRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>情感-互动关系</span></template>
            <div ref="sentimentScatterRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header><span>情感词云</span></template>
            <div ref="sentimentWordCloudRef" class="chart-container" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 热点话题仪表盘 -->
    <div v-else-if="currentDashboard === 'topics'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>话题热度排行</span></template>
            <div ref="topicRankRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>话题词云</span></template>
            <div ref="topicWordCloudRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header><span>话题热度趋势</span></template>
            <div ref="topicTrendRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>话题情感构成</span></template>
            <div ref="topicSentimentRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header><span>话题传播时间线</span></template>
            <div ref="topicTimelineRef" class="chart-container" style="height: 250px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 用户画像仪表盘 -->
    <div v-else-if="currentDashboard === 'users'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>用户活跃度分布</span></template>
            <div ref="userActivityRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>用户认证类型</span></template>
            <div ref="userVerifyRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>粉丝数分布</span></template>
            <div ref="userFollowersRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>用户发布时段分析</span></template>
            <div ref="userTimeHeatmapRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header><span>用户影响力雷达图</span></template>
            <div ref="userInfluenceRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card class="chart-card">
            <template #header><span>用户地域分布</span></template>
            <div ref="userRegionRef" class="chart-container" style="height: 350px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 传播路径仪表盘 -->
    <div v-else-if="currentDashboard === 'propagation'" class="dashboard-content">
      <el-row :gutter="16">
        <el-col :span="18">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>微博传播路径图</span>
                <div style="display:flex;gap:8px;align-items:center">
                  <el-input v-model="propagationTopic" size="small" placeholder="输入话题关键词" style="width:180px" clearable @keyup.enter="updatePropagationChart" @clear="updatePropagationChart" />
                  <el-switch v-model="showNickname" active-text="昵称" inactive-text="" size="small" style="margin:0 4px" @change="updatePropagationChart" />
                  <el-button size="small" @click="exportChart('propagation', 'png')">PNG</el-button>
                  <el-button size="small" @click="exportChart('propagation', 'pdf')">PDF</el-button>
                </div>
              </div>
            </template>
            <div ref="propagationGraphRef" class="chart-container" style="height: 500px"></div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="chart-card">
            <template #header><span>传播统计</span></template>
            <div class="prop-stats">
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.totalNodes }}</div><div class="prop-lbl">涉及用户</div></div>
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.totalEdges }}</div><div class="prop-lbl">转发链路</div></div>
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.maxDepth }}</div><div class="prop-lbl">最大深度</div></div>
              <div class="prop-stat-item"><div class="prop-val">{{ propagationStats.avgRepost }}</div><div class="prop-lbl">平均转发</div></div>
            </div>
          </el-card>
          <el-card class="chart-card" style="margin-top:16px">
            <template #header><span>关键传播节点</span></template>
            <div class="key-nodes">
              <div v-for="node in keyPropagationNodes" :key="node.name" class="key-node-item">
                <el-avatar :size="32">{{ node.name.charAt(0) }}</el-avatar>
                <div class="key-node-info">
                  <div class="key-node-name">{{ node.name }}</div>
                  <div class="key-node-meta">转发 {{ node.reposts }} | 粉丝 {{ node.followers }}</div>
                </div>
              </div>
            </div>
          </el-card>
          <el-card class="chart-card" style="margin-top:16px">
            <template #header><span>图例</span></template>
            <div class="graph-legend">
              <div class="legend-row"><span class="legend-circle" :style="{background: DANGER}"></span> 原始发布者</div>
              <div class="legend-row"><span class="legend-circle" :style="{background: WARNING}"></span> 认证用户 (大V)</div>
              <div class="legend-row"><span class="legend-circle" :style="{background: PRIMARY}"></span> 普通用户</div>
              <div class="legend-row"><span class="legend-line"></span> 转发关系</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 实时监控仪表盘 -->
    <div v-else-if="currentDashboard === 'realtime'" class="dashboard-content">
      <el-row :gutter="16" class="metric-row">
        <el-col :span="6">
          <div class="metric-card realtime">
            <div class="metric-icon pulse"><el-icon><Connection /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.currentRate }}</div>
              <div class="metric-label">当前采集速率/分钟</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card realtime">
            <div class="metric-icon"><el-icon><Timer /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.todayTotal }}</div>
              <div class="metric-label">今日采集总量</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card realtime">
            <div class="metric-icon"><el-icon><DataAnalysis /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.analyzedCount }}</div>
              <div class="metric-label">已分析数量</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card" :class="realtimeData.alertCount > 0 ? 'danger' : 'success'">
            <div class="metric-icon"><el-icon><Bell /></el-icon></div>
            <div class="metric-info">
              <div class="metric-value">{{ realtimeData.alertCount }}</div>
              <div class="metric-label">预警数量</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="16">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>实时数据流</span>
                <el-tag :type="isStreaming ? 'success' : 'info'" size="small">
                  {{ isStreaming ? '实时更新中' : '已暂停' }}
                </el-tag>
                <el-switch v-model="isStreaming" size="small" style="margin-left: 12px" />
              </div>
            </template>
            <div ref="realtimeLineRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="chart-card">
            <template #header><span>实时情感分布</span></template>
            <div ref="realtimePieRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="24">
          <el-card>
            <template #header><span>最新微博动态</span></template>
            <el-table :data="latestPosts" max-height="300" size="small">
              <el-table-column prop="time" label="时间" width="100" />
              <el-table-column prop="content" label="内容" show-overflow-tooltip />
              <el-table-column prop="sentiment" label="情感" width="80">
                <template #default="{ row }">
                  <el-tag :type="getSentimentTagType(row.sentiment)" size="small">{{ row.sentiment }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="likes" label="点赞" width="80" />
              <el-table-column prop="reposts" label="转发" width="80" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 微博详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="微博详情与分析结果" width="640px" destroy-on-close>
      <template v-if="selectedWeibo">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="微博ID" :span="2">{{ selectedWeibo.weibo_id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ selectedWeibo.user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发布时间">{{ selectedWeibo.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="内容" :span="2">
            <div style="white-space:pre-wrap;max-height:200px;overflow-y:auto;line-height:1.6">{{ selectedWeibo.content }}</div>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">情感分析</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="情感类别">
            <el-tag :type="selectedWeibo.sentiment_class === 'positive' ? 'success' : selectedWeibo.sentiment_class === 'negative' ? 'danger' : 'info'" size="small">
              {{ selectedWeibo.sentiment_class === 'positive' ? '正面' : selectedWeibo.sentiment_class === 'negative' ? '负面' : '中性' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="情感分数">{{ selectedWeibo.hybrid_score != null ? Number(selectedWeibo.hybrid_score).toFixed(4) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ selectedWeibo.confidence != null ? (Number(selectedWeibo.confidence) * 100).toFixed(1) + '%' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="分析方法">{{ selectedWeibo.analysis_method || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理耗时">{{ selectedWeibo.processing_time_ms != null ? selectedWeibo.processing_time_ms + 'ms' : '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">三维度排序</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="综合得分">{{ selectedWeibo.composite_score != null ? Number(selectedWeibo.composite_score).toFixed(4) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="排名">{{ selectedWeibo.ranking_position || '-' }}</el-descriptions-item>
          <el-descriptions-item label="热度分数">{{ selectedWeibo.popularity_score != null ? Number(selectedWeibo.popularity_score).toFixed(4) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="时间衰减">{{ selectedWeibo.time_decay != null ? Number(selectedWeibo.time_decay).toFixed(4) : '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">互动数据</el-divider>
        <el-row :gutter="16" style="text-align:center">
          <el-col :span="8">
            <el-statistic title="转发" :value="selectedWeibo.reposts_count || 0" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="评论" :value="selectedWeibo.comments_count || 0" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="点赞" :value="selectedWeibo.attitudes_count || 0" />
          </el-col>
        </el-row>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import {
  Refresh, ArrowDown, Document, CircleCheck, CircleClose, Warning,
  CaretTop, CaretBottom, Connection, Timer, DataAnalysis, Bell, FullScreen,
} from '@element-plus/icons-vue';
import { SUCCESS, PRIMARY, PRIMARY_LIGHT, DANGER, INFO, WARNING } from '@/styles/colors';
import apiClient from '@/api/index';

// ==================== 状态定义 ====================
const currentDashboard = ref('overview');
const dateRange = ref<string[]>([]);
const isLoading = ref(false);
const trendTimeRange = ref('7d');
const sentimentTypes = ref(['positive', 'negative', 'neutral']);
const isStreaming = ref(true);
const isFullscreen = ref(false);
const selectedSentiment = ref<string | null>(null);
const propagationLoading = ref(false);
const hotWeiboList = ref([
  { id: 1, title: ' ', content: '...', reposts: 5000, likes: 12000 },
  { id: 2, title: ' ', content: '...', reposts: 3200, likes: 8900 },
  { id: 3, title: ' ', content: '...', reposts: 2800, likes: 7600 },
]);

// 微观层面：数据明细
const detailList = ref<any[]>([]);
const detailPage = ref(1);
const detailPageSize = 15;
const detailTotal = ref(0);
const detailKeyword = ref('');
const detailSentimentFilter = ref('');
const detailDialogVisible = ref(false);
const selectedWeibo = ref<any>(null);

const loadWeiboDetail = async (page: number = 1) => {
  detailPage.value = page;
  try {
    const res = await apiClient.get('/dashboard/weibo-detail', {
      params: {
        page,
        page_size: detailPageSize,
        keyword: detailKeyword.value || undefined,
        sentiment: detailSentimentFilter.value || undefined,
      },
    });
    if (res.data?.code === 200) {
      detailList.value = res.data.data.items || [];
      detailTotal.value = res.data.data.total || 0;
    }
  } catch (e) {
    console.warn('[Viz] 加载数据明细失败', e);
  }
};

const showWeiboDetailDialog = (row: any) => {
  selectedWeibo.value = row;
  detailDialogVisible.value = true;
};

// 传播路径
const propagationGraphRef = ref<HTMLElement>();
const propagationTopic = ref('科技创新');
const showNickname = ref(true);
const propagationStats = ref({ totalNodes: 42, totalEdges: 56, maxDepth: 5, avgRepost: 3.2 });
const keyPropagationNodes = ref([
  { name: '科技媒体', reposts: 1280, followers: '520万' },
  { name: '行业大V', reposts: 890, followers: '320万' },
  { name: '热搜用户', reposts: 560, followers: '180万' },
  { name: '普通达人', reposts: 340, followers: '45万' },
]);

// 图表引用
const trendChartRef = ref<HTMLElement>();
const sentimentPieRef = ref<HTMLElement>();
const topicsBarRef = ref<HTMLElement>();
const regionMapRef = ref<HTMLElement>();
const sentimentDonutRef = ref<HTMLElement>();
const sentimentTrendRef = ref<HTMLElement>();
const intensityHistogramRef = ref<HTMLElement>();
const sentimentScatterRef = ref<HTMLElement>();
const sentimentWordCloudRef = ref<HTMLElement>();
const topicRankRef = ref<HTMLElement>();
const topicWordCloudRef = ref<HTMLElement>();
const topicTrendRef = ref<HTMLElement>();
const topicSentimentRef = ref<HTMLElement>();
const topicTimelineRef = ref<HTMLElement>();
const userActivityRef = ref<HTMLElement>();
const userVerifyRef = ref<HTMLElement>();
const userFollowersRef = ref<HTMLElement>();
const userTimeHeatmapRef = ref<HTMLElement>();
const userInfluenceRef = ref<HTMLElement>();
const userRegionRef = ref<HTMLElement>();
const realtimeLineRef = ref<HTMLElement>();
const realtimePieRef = ref<HTMLElement>();

// 图表实例
const charts: echarts.ECharts[] = [];

// 数据
const overviewData = ref({
  totalPosts: 0,
  postsTrend: 0,
  positiveRate: 0,
  positiveTrend: 0,
  negativeRate: 0,
  negativeTrend: 0,
  hotTopics: 0,
  topicsTrend: 0,
});

// 后端拉取的真实数据缓存
const backendTrend = ref<{ dates: string[]; positive: number[]; neutral: number[]; negative: number[] } | null>(null);
const backendHotTopics = ref<{ name: string; heat: number; trend: string }[]>([]);
const backendSentiment = ref<{ positive: number; neutral: number; negative: number; raw_counts: any; total_records: number } | null>(null);
const backendUserProfile = ref<{
  activity: { name: string; value: number }[];
  verifiedType: { name: string; value: number }[];
  fansDistribution: { labels: string[]; values: number[] };
  postHours: { labels: string[]; values: number[] };
  influence: { indicators: { name: string; max: number }[]; values: number[] };
} | null>(null);
const backendExtras = ref<{
  keywordDistribution: { labels: string[]; values: number[] };
  intensityHistogram: { labels: string[]; values: number[] };
  sentimentScatter: number[][];
  topicHourly: { labels: string[]; values: number[] };
  topicDailyTrend: { dates: string[]; series: { name: string; data: number[] }[] };
  keywordSentiment: { name: string; value: number; sentiment: string }[];
} | null>(null);
const backendRealtime = ref<{
  metrics: { ratePerMin: number; todayTotal: number; analyzedTotal: number; alertCount: number };
  timeline: { labels: string[]; collected: number[]; analyzed: number[] };
  sentiment: { positive: number; neutral: number; negative: number; positive_pct: number; neutral_pct: number; negative_pct: number };
} | null>(null);

const realtimeData = ref({
  currentRate: 156,
  todayTotal: 23456,
  analyzedCount: 22890,
  alertCount: 3,
});

const latestPosts = ref([
  { time: '10:32:15', content: '今天天气真好，心情也很棒！#美好生活#', sentiment: '正面', likes: 128, reposts: 23 },
  { time: '10:31:58', content: '这个产品质量太差了，完全不值这个价格', sentiment: '负面', likes: 56, reposts: 12 },
  { time: '10:31:42', content: '刚看完这部电影，剧情一般般吧', sentiment: '中性', likes: 34, reposts: 5 },
  { time: '10:31:25', content: '强烈推荐这家餐厅，味道超级棒！', sentiment: '正面', likes: 89, reposts: 18 },
  { time: '10:31:08', content: '等了一个小时还没送到，差评！', sentiment: '负面', likes: 45, reposts: 8 },
]);

// 日期快捷选项
const dateShortcuts = [
  { text: '最近7天', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 7); return [start, end]; } },
  { text: '最近30天', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 30); return [start, end]; } },
  { text: '最近90天', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 90); return [start, end]; } },
];

// ==================== 工具函数 ====================
const formatNumber = (num: number) => num.toLocaleString();

const getSentimentTagType = (sentiment: string) => {
  const types: Record<string, any> = { '正面': 'success', '负面': 'danger', '中性': 'info' };
  return types[sentiment] || 'info';
};

// ==================== 图表初始化 ====================
const initChart = (el: HTMLElement | undefined, option: echarts.EChartsOption) => {
  if (!el) return null;
  const chart = echarts.init(el);
  chart.setOption(option);
  charts.push(chart);
  return chart;
};

const initOverviewCharts = () => {
  // 舆情趋势图 — 优先使用后端数据
  const trend = backendTrend.value;
  const tDates = trend?.dates || generateDates(7);
  const tPos = trend?.positive || generateRandomData(7, 400, 600);
  const tNeg = trend?.negative || generateRandomData(7, 150, 250);
  const tNeu = trend?.neutral || generateRandomData(7, 300, 450);
  const tTotal = tPos.map((v: number, i: number) => v + tNeg[i] + tNeu[i]);

  initChart(trendChartRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['微博数量', '正面', '负面', '中性'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: tDates },
    yAxis: { type: 'value' },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 5 },
    ],
    series: [
      { name: '微博数量', type: 'line', smooth: true, data: tTotal, areaStyle: { opacity: 0.08 } },
      { name: '正面', type: 'line', smooth: true, data: tPos, lineStyle: { color: SUCCESS }, itemStyle: { color: SUCCESS } },
      { name: '负面', type: 'line', smooth: true, data: tNeg, lineStyle: { color: DANGER }, itemStyle: { color: DANGER } },
      { name: '中性', type: 'line', smooth: true, data: tNeu, lineStyle: { color: INFO }, itemStyle: { color: INFO } },
    ],
  });

  // 情感分布饼图 — 使用后端真实分布
  const sd = backendSentiment.value;
  const piePosVal = sd?.raw_counts?.positive ?? sd?.positive ?? 45;
  const pieNegVal = sd?.raw_counts?.negative ?? sd?.negative ?? 19;
  const pieNeuVal = sd?.raw_counts?.neutral ?? sd?.neutral ?? 36;
  initChart(sentimentPieRef.value, {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: [
        { value: piePosVal, name: '正面', itemStyle: { color: SUCCESS } },
        { value: pieNegVal, name: '负面', itemStyle: { color: DANGER } },
        { value: pieNeuVal, name: '中性', itemStyle: { color: INFO } },
      ],
    }],
  });

  // 热门话题柱状图 — 使用后端真实热搜
  const ht = backendHotTopics.value.length > 0 ? backendHotTopics.value.slice(0, 10) : [
    { name: '话题加载中', heat: 0 },
  ];
  const topicNames = ht.map(t => `#${t.name}#`).reverse();
  const topicHeats = ht.map(t => t.heat).reverse();
  initChart(topicsBarRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: topicNames },
    series: [{
      type: 'bar',
      data: topicHeats,
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: PRIMARY }, { offset: 1, color: SUCCESS }]), borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  });

  // 关键词分布 (替代地域分布: 数据库 location 字段无数据, 改用 keyword 真实聚合)
  const kd = backendExtras.value?.keywordDistribution;
  initChart(regionMapRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: kd?.labels || ['暂无数据'], axisLabel: { rotate: 30, interval: 0, fontSize: 10 } },
    yAxis: { type: 'value', name: '微博数' },
    dataZoom: [{ type: 'inside' }],
    series: [{
      type: 'bar',
      data: kd?.values || [0],
      itemStyle: { color: PRIMARY, borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top' },
    }],
  });
};

const initSentimentCharts = () => {
  // 情感极性环形图 — 使用后端真实数据
  const sd = backendSentiment.value;
  const donutPos = sd?.raw_counts?.positive ?? 45200;
  const donutNeg = sd?.raw_counts?.negative ?? 18600;
  const donutNeu = sd?.raw_counts?.neutral ?? 36200;
  initChart(sentimentDonutRef.value, {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [{
      type: 'pie',
      radius: ['35%', '60%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10 },
      label: { show: true, formatter: '{b}: {d}%' },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      data: [
        { value: donutPos, name: '正面', itemStyle: { color: SUCCESS } },
        { value: donutNeg, name: '负面', itemStyle: { color: DANGER } },
        { value: donutNeu, name: '中性', itemStyle: { color: INFO } },
      ],
    }],
  });

  // 情感趋势对比 — 优先后端趋势
  const trend = backendTrend.value;
  const stDates = trend?.dates || generateDates(14);
  const stPos = trend?.positive || generateRandomData(14, 400, 600);
  const stNeg = trend?.negative || generateRandomData(14, 150, 250);
  const stNeu = trend?.neutral || generateRandomData(14, 300, 450);
  initChart(sentimentTrendRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['正面', '负面', '中性'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: stDates },
    yAxis: { type: 'value', name: '数量' },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 5 },
    ],
    series: [
      { name: '正面', type: 'line', smooth: true, data: stPos, lineStyle: { color: SUCCESS }, itemStyle: { color: SUCCESS }, areaStyle: { color: 'rgba(0, 180, 42, 0.1)' } },
      { name: '负面', type: 'line', smooth: true, data: stNeg, lineStyle: { color: DANGER }, itemStyle: { color: DANGER }, areaStyle: { color: 'rgba(245, 63, 63, 0.1)' } },
      { name: '中性', type: 'line', smooth: true, data: stNeu, lineStyle: { color: INFO }, itemStyle: { color: INFO }, areaStyle: { color: 'rgba(134, 144, 156, 0.1)' } },
    ],
  });

  // 情感强度分布 (真实 sentiment_analysis_results.intensity 分桶)
  const ih = backendExtras.value?.intensityHistogram;
  const intensityColors = ['#c45656', DANGER, '#fab6b6', INFO, '#b3e19d', SUCCESS, '#529b2e'];
  initChart(intensityHistogramRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ih?.labels || ['极负面', '负面', '轻微负面', '中性', '轻微正面', '正面', '极正面'], axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '数量' },
    series: [{
      type: 'bar',
      data: (ih?.values || [2100, 5800, 8900, 36200, 12300, 18500, 5200]).map((v, i) => ({ value: v, itemStyle: { color: intensityColors[i] || PRIMARY } })),
      barWidth: '60%',
    }],
  });

  // 情感-互动散点图 (真实 JOIN 数据)
  const scatter = backendExtras.value?.sentimentScatter || generateScatterData(100);
  initChart(sentimentScatterRef.value, {
    tooltip: { trigger: 'item', formatter: (params: any) => `情感分数: ${params.value[0]}<br/>互动量: ${params.value[1]}` },
    xAxis: { type: 'value', name: '情感分数', min: -1, max: 1 },
    yAxis: { type: 'value', name: '互动量' },
    series: [{
      type: 'scatter',
      symbolSize: 10,
      data: scatter,
      itemStyle: { color: (params: any) => params.value[0] > 0.3 ? SUCCESS : params.value[0] < -0.3 ? DANGER : INFO },
    }],
  });

  // 关键词+主导情感 (替代情感词云: 用真实 keyword 出现次数 + sentiment_analysis_results 主导情感)
  const ks = backendExtras.value?.keywordSentiment || [];
  const sentColor = (s: string) => s === 'positive' ? SUCCESS : s === 'negative' ? DANGER : INFO;
  initChart(sentimentWordCloudRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: any) => `${p[0].name}<br/>出现次数: ${p[0].value}<br/>主导情感: ${ks[p[0].dataIndex]?.sentiment || '-'}` },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: ks.length ? ks.map((k: any) => k.name) : ['暂无数据'], axisLabel: { rotate: 30, interval: 0, fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: ks.length ? ks.map((k: any) => ({ value: k.value, itemStyle: { color: sentColor(k.sentiment) } })) : [0],
    }],
  });
};

const initTopicsCharts = () => {
  // 话题热度排行 — 使用后端真实热搜
  const htRank = backendHotTopics.value.length > 0 ? backendHotTopics.value.slice(0, 8) : [
    { name: '话题加载中', heat: 0 },
  ];
  const rankColors = [DANGER, WARNING, WARNING, PRIMARY, PRIMARY, PRIMARY, SUCCESS, SUCCESS];
  initChart(topicRankRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: htRank.map(t => `#${t.name}#`).reverse() },
    series: [{
      type: 'bar',
      data: htRank.map(t => t.heat).reverse(),
      itemStyle: { color: (params: any) => rankColors[params.dataIndex] || PRIMARY, borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  });

  // 话题词云（饼图展示）— 使用后端真实热搜
  const htCloud = backendHotTopics.value.length > 0 ? backendHotTopics.value.slice(0, 6) : [
    { name: '话题加载中', heat: 1 },
  ];
  initChart(topicWordCloudRef.value, {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '70%',
      data: htCloud.map(t => ({ value: t.heat, name: t.name })),
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
    }],
  });

  // 话题热度趋势 — 使用后端趋势日期
  const topicTrendDates = backendTrend.value?.dates || generateDates(7);
  const top3 = backendHotTopics.value.slice(0, 3);
  const topicTrendNames = top3.length > 0 ? top3.map(t => t.name) : ['话题1', '话题2', '话题3'];
  initChart(topicTrendRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: topicTrendNames, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: topicTrendDates },
    yAxis: { type: 'value' },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 5 },
    ],
    series: (() => {
      const dt = backendExtras.value?.topicDailyTrend;
      if (dt?.dates?.length && dt.series?.length) {
        return dt.series.map(s => ({ name: s.name, type: 'line', smooth: true, data: s.data }));
      }
      return topicTrendNames.map((name, idx) => ({
        name,
        type: 'line',
        smooth: true,
        data: generateRandomData(topicTrendDates.length, (3 - idx) * 300, (4 - idx) * 400),
      }));
    })(),
  });

  // 话题情感构成 — 优先后端真实分布
  const bs = backendSentiment.value;
  const sentData = bs ? [
    { value: bs.positive || 0, name: '正面', itemStyle: { color: SUCCESS } },
    { value: bs.neutral  || 0, name: '中性', itemStyle: { color: INFO } },
    { value: bs.negative || 0, name: '负面', itemStyle: { color: DANGER } },
  ] : [
    { value: 52, name: '正面', itemStyle: { color: SUCCESS } },
    { value: 28, name: '中性', itemStyle: { color: INFO } },
    { value: 20, name: '负面', itemStyle: { color: DANGER } },
  ];
  initChart(topicSentimentRef.value, {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{ type: 'pie', radius: '60%', data: sentData }],
  });

  // 话题传播时间线 (真实 24h 发文量)
  const th = backendExtras.value?.topicHourly;
  initChart(topicTimelineRef.value, {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: th?.labels || ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'], axisLabel: { interval: 1 } },
    yAxis: { type: 'value', name: '发文量' },
    series: [{
      type: 'line',
      smooth: true,
      data: th?.values || [120, 80, 45, 60, 350, 680, 520, 450, 380, 620, 780, 450],
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(22, 93, 255, 0.5)' }, { offset: 1, color: 'rgba(22, 93, 255, 0.1)' }]) },
      lineStyle: { color: PRIMARY, width: 2 },
      itemStyle: { color: PRIMARY },
    }],
  });
};

const initUsersCharts = () => {
  const up = backendUserProfile.value;

  // 用户活跃度分布 (后端真实)
  const actData = up?.activity?.length
    ? up.activity.map((it, i) => ({
        value: it.value,
        name: it.name,
        itemStyle: { color: [SUCCESS, PRIMARY, INFO][i] || PRIMARY },
      }))
    : [
        { value: 35, name: '高活跃', itemStyle: { color: SUCCESS } },
        { value: 45, name: '中活跃', itemStyle: { color: PRIMARY } },
        { value: 20, name: '低活跃', itemStyle: { color: INFO } },
      ];
  initChart(userActivityRef.value, {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data: actData }],
  });

  // 用户认证类型 (后端: 认证/普通)
  const vtData = up?.verifiedType?.length
    ? up.verifiedType.map((it, i) => ({
        value: it.value,
        name: it.name,
        itemStyle: { color: [PRIMARY, INFO][i] || INFO },
      }))
    : [
        { value: 15, name: '蓝V认证', itemStyle: { color: PRIMARY } },
        { value: 8, name: '黄V认证', itemStyle: { color: WARNING } },
        { value: 77, name: '普通用户', itemStyle: { color: INFO } },
      ];
  initChart(userVerifyRef.value, {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{ type: 'pie', radius: '60%', data: vtData }],
  });

  // 粉丝数分布 (后端真实分桶)
  const fans = up?.fansDistribution;
  initChart(userFollowersRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: fans?.labels || ['<100', '100-1k', '1k-10k', '10k-100k', '100k-1M', '>1M'] },
    yAxis: { type: 'value', name: '用户数' },
    series: [{
      type: 'bar',
      data: fans?.values || [12500, 35600, 28900, 15200, 5800, 1200],
      itemStyle: { color: PRIMARY, borderRadius: [4, 4, 0, 0] },
    }],
  });

  // 用户发布时段 (后端 24h bar)
  const ph = up?.postHours;
  initChart(userTimeHeatmapRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true },
    xAxis: { type: 'category', data: ph?.labels || Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`), axisLabel: { interval: 1 } },
    yAxis: { type: 'value', name: '发帖量' },
    series: [{
      type: 'bar',
      data: ph?.values || Array.from({ length: 24 }, () => Math.floor(Math.random() * 500)),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: PRIMARY }, { offset: 1, color: SUCCESS }]), borderRadius: [4, 4, 0, 0] },
    }],
  });

  // 用户影响力雷达图 (后端真实, 已归一到 0-100)
  const inf = up?.influence;
  initChart(userInfluenceRef.value, {
    tooltip: {},
    radar: { indicator: inf?.indicators || [{ name: '发帖量', max: 100 }, { name: '互动率', max: 100 }, { name: '粉丝数', max: 100 }, { name: '转发量', max: 100 }, { name: '评论量', max: 100 }, { name: '点赞量', max: 100 }] },
    series: [{
      type: 'radar',
      data: [{
        value: inf?.values || [85, 72, 68, 78, 82, 90],
        name: '平均影响力',
        areaStyle: { color: 'rgba(22, 93, 255, 0.3)' },
        lineStyle: { color: PRIMARY },
        itemStyle: { color: PRIMARY },
      }],
    }],
  });

  // 用户讨论关键词分布 (替代地域分布)
  const kd2 = backendExtras.value?.keywordDistribution;
  initChart(userRegionRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: kd2?.labels || ['暂无数据'], axisLabel: { rotate: 30, interval: 0, fontSize: 10 } },
    yAxis: { type: 'value', name: '讨论数' },
    series: [{
      type: 'bar',
      data: kd2?.values || [0],
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: PRIMARY }, { offset: 1, color: SUCCESS }]), borderRadius: [4, 4, 0, 0] },
    }],
  });
};

const initRealtimeCharts = () => {
  const rt = backendRealtime.value;
  // 实时数据流 (后端近 20 分钟 分钟桶)
  initChart(realtimeLineRef.value, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['采集量', '分析量'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: rt?.timeline?.labels || generateTimeLabels(20) },
    yAxis: { type: 'value' },
    series: [
      { name: '采集量', type: 'line', smooth: true, data: rt?.timeline?.collected || generateRandomData(20, 0, 5), areaStyle: { opacity: 0.3 }, lineStyle: { color: PRIMARY }, itemStyle: { color: PRIMARY } },
      { name: '分析量', type: 'line', smooth: true, data: rt?.timeline?.analyzed  || generateRandomData(20, 0, 5), areaStyle: { opacity: 0.3 }, lineStyle: { color: SUCCESS }, itemStyle: { color: SUCCESS } },
    ],
  });

  // 实时情感分布 (后端 sentiment_analysis_results)
  const sd = rt?.sentiment;
  initChart(realtimePieRef.value, {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: sd ? [
        { value: sd.positive, name: '正面', itemStyle: { color: SUCCESS } },
        { value: sd.neutral,  name: '中性', itemStyle: { color: INFO } },
        { value: sd.negative, name: '负面', itemStyle: { color: DANGER } },
      ] : [
        { value: 48, name: '正面', itemStyle: { color: SUCCESS } },
        { value: 32, name: '中性', itemStyle: { color: INFO } },
        { value: 20, name: '负面', itemStyle: { color: DANGER } },
      ],
    }],
  });
};

// ==================== 传播路径图 ====================
const generatePropagationData = () => {
  const nodes: any[] = [];
  const links: any[] = [];
  const categories = ['原始发布', '认证用户', '普通用户'];

  // Root node
  nodes.push({ id: '0', name: '原始发布者', symbolSize: 50, category: 0, itemStyle: { color: DANGER } });
  let nodeId = 1;

  // Level 1: verified users
  const l1Count = 3 + Math.floor(Math.random() * 3);
  for (let i = 0; i < l1Count; i++) {
    const id = String(nodeId++);
    nodes.push({ id, name: `大V_${i + 1}`, symbolSize: 35, category: 1, itemStyle: { color: WARNING } });
    links.push({ source: '0', target: id });
    // Level 2: regular users from each verified
    const l2Count = 2 + Math.floor(Math.random() * 5);
    for (let j = 0; j < l2Count; j++) {
      const id2 = String(nodeId++);
      nodes.push({ id: id2, name: `用户_${nodeId}`, symbolSize: 15 + Math.floor(Math.random() * 15), category: 2, itemStyle: { color: PRIMARY } });
      links.push({ source: id, target: id2 });
      // Level 3: occasional deeper
      if (Math.random() > 0.6) {
        const id3 = String(nodeId++);
        nodes.push({ id: id3, name: `用户_${nodeId}`, symbolSize: 10 + Math.floor(Math.random() * 10), category: 2, itemStyle: { color: PRIMARY_LIGHT } });
        links.push({ source: id2, target: id3 });
      }
    }
  }

  propagationStats.value = {
    totalNodes: nodes.length,
    totalEdges: links.length,
    maxDepth: 4,
    avgRepost: Number((links.length / l1Count).toFixed(1)),
  };

  return { nodes, links, categories: categories.map(c => ({ name: c })) };
};

const initPropagationChart = () => {
  const { nodes, links, categories } = generatePropagationData();
  initChart(propagationGraphRef.value, {
    tooltip: { formatter: (params: any) => params.dataType === 'node' ? `${params.data.name}<br/>影响力: ${params.data.symbolSize}` : `${params.data.source} → ${params.data.target}` },
    legend: [{ data: categories.map((c: any) => c.name), orient: 'vertical', right: 10, top: 20 }],
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      categories: categories,
      roam: true,
      label: { show: showNickname.value, position: 'right', fontSize: 10 },
      force: { repulsion: 200, gravity: 0.1, edgeLength: [50, 150], layoutAnimation: true },
      lineStyle: { color: 'source', curveness: 0.3, opacity: 0.6 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    }],
  });
};

const updatePropagationChart = () => {
  // Re-init with new random data for selected topic
  if (propagationGraphRef.value) {
    const existing = echarts.getInstanceByDom(propagationGraphRef.value);
    if (existing) existing.dispose();
    // Remove from charts array
    const idx = charts.findIndex(c => c === existing);
    if (idx !== -1) charts.splice(idx, 1);
  }
  initPropagationChart();
};

// ==================== 辅助函数 ====================
const generateDates = (days: number) => {
  const dates = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push(`${d.getMonth() + 1}/${d.getDate()}`);
  }
  return dates;
};

const generateTimeLabels = (count: number) => {
  const labels = [];
  const now = new Date();
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 60000);
    labels.push(`${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`);
  }
  return labels;
};

const generateRandomData = (count: number, min: number, max: number) => {
  return Array.from({ length: count }, () => Math.floor(Math.random() * (max - min) + min));
};

const generateScatterData = (count: number) => {
  return Array.from({ length: count }, () => [
    (Math.random() * 2 - 1).toFixed(2),
    Math.floor(Math.random() * 1000),
  ]);
};

const generateHeatmapData = () => {
  const data = [];
  for (let i = 0; i < 7; i++) {
    for (let j = 0; j < 8; j++) {
      data.push([i, j, Math.floor(Math.random() * 500)]);
    }
  }
  return data;
};

// ==================== 事件处理 ====================
const handleDashboardChange = async () => {
  await nextTick();
  charts.forEach(c => c.dispose());
  charts.length = 0;
  
  switch (currentDashboard.value) {
    case 'overview': initOverviewCharts(); break;
    case 'sentiment': initSentimentCharts(); break;
    case 'topics': initTopicsCharts(); break;
    case 'users': initUsersCharts(); break;
    case 'realtime': initRealtimeCharts(); break;
    case 'propagation': initPropagationChart(); break;
  }
};

const handleDateChange = () => {
  refreshData();
};

const fetchBackendData = async () => {
  const period = dateRange.value?.length === 2 ? 'all' : 'all';
  try {
    const [overviewRes, sentimentRes, trendRes, topicsRes, userProfileRes, extrasRes, realtimeRes] = await Promise.allSettled([
      apiClient.get('/dashboard/overview'),
      apiClient.get('/dashboard/sentiment-distribution', { params: { period } }),
      apiClient.get('/dashboard/trend'),
      apiClient.get('/dashboard/hot-topics'),
      apiClient.get('/dashboard/user-profile'),
      apiClient.get('/dashboard/extras'),
      apiClient.get('/dashboard/realtime-metrics'),
    ]);

    // 概览
    if (overviewRes.status === 'fulfilled' && overviewRes.value.data?.code === 200) {
      const d = overviewRes.value.data.data;
      overviewData.value.totalPosts = d.total_weibos || 0;
      overviewData.value.postsTrend = d.today_weibos ? Math.round(d.today_weibos / Math.max(d.total_weibos, 1) * 100) : 0;
    }

    // 情感分布
    if (sentimentRes.status === 'fulfilled' && sentimentRes.value.data?.code === 200) {
      const d = sentimentRes.value.data.data;
      backendSentiment.value = d;
      overviewData.value.positiveRate = d.positive || 0;
      overviewData.value.positiveTrend = Math.round(d.positive * 0.1);
      overviewData.value.negativeRate = d.negative || 0;
      overviewData.value.negativeTrend = Math.round(d.negative * 0.05);
    }

    // 趋势
    if (trendRes.status === 'fulfilled' && trendRes.value.data?.code === 200) {
      backendTrend.value = trendRes.value.data.data;
    }

    // 热门话题
    if (topicsRes.status === 'fulfilled' && topicsRes.value.data?.code === 200) {
      backendHotTopics.value = topicsRes.value.data.data || [];
      overviewData.value.hotTopics = backendHotTopics.value.length;
      overviewData.value.topicsTrend = backendHotTopics.value.filter(t => t.trend === 'up').length * 10;
    }

    // 用户画像
    if (userProfileRes.status === 'fulfilled' && userProfileRes.value.data?.code === 200) {
      backendUserProfile.value = userProfileRes.value.data.data || null;
    }

    // 补全聚合 (关键词分布/情感强度/散点/时段/话题趋势)
    if (extrasRes.status === 'fulfilled' && extrasRes.value.data?.code === 200) {
      backendExtras.value = extrasRes.value.data.data || null;
    }

    // 实时监控 4 指标 + 时序 + 情感
    if (realtimeRes.status === 'fulfilled' && realtimeRes.value.data?.code === 200) {
      backendRealtime.value = realtimeRes.value.data.data || null;
      const m = backendRealtime.value?.metrics;
      if (m) {
        realtimeData.value.currentRate   = m.ratePerMin;
        realtimeData.value.todayTotal    = m.todayTotal;
        realtimeData.value.analyzedCount = m.analyzedTotal;
        realtimeData.value.alertCount    = m.alertCount;
      }
    }
  } catch (e) {
    console.warn('[Viz] 后端数据拉取失败', e);
  }
};

const refreshData = async () => {
  isLoading.value = true;
  await fetchBackendData();
  handleDashboardChange();
  isLoading.value = false;
  ElMessage.success('数据已刷新');
};

const exportAllChartsPNG = () => {
  if (charts.length === 0) { ElMessage.warning('暂无图表可导出'); return; }
  charts.forEach((chart, idx) => {
    const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
    const link = document.createElement('a');
    link.href = url;
    link.download = `chart_${currentDashboard.value}_${idx + 1}_${Date.now()}.png`;
    link.click();
  });
  ElMessage.success(`已导出 ${charts.length} 张图表图片`);
};

const exportDataAsExcel = async () => {
  try {
    const XLSX: any = await import('xlsx');
    const wb = XLSX.utils.book_new();
    const ts = new Date().toISOString().slice(0, 10);
    let sheetCount = 0;

    // 1) 热点话题
    if (backendHotTopics.value?.length) {
      const rows = backendHotTopics.value.map((t: any, i: number) => ({
        排名: i + 1,
        话题: t.name,
        热度: t.heat,
        趋势: t.trend,
        是否热门: t.isHot ? '是' : '否',
        是否新增: t.isNew ? '是' : '否',
      }));
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), '热点话题');
      sheetCount++;
    }

    // 2) 情感分布
    if (backendSentiment.value) {
      const s = backendSentiment.value;
      const rows = [
        { 情感: '正面', 占比: s.positive || 0 },
        { 情感: '中性', 占比: s.neutral || 0 },
        { 情感: '负面', 占比: s.negative || 0 },
      ];
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), '情感分布');
      sheetCount++;
    }

    // 3) 舆情趋势
    if (backendTrend.value?.dates?.length) {
      const t = backendTrend.value;
      const rows = t.dates.map((d, i) => ({
        日期: d,
        正面: t.positive?.[i] ?? 0,
        中性: t.neutral?.[i] ?? 0,
        负面: t.negative?.[i] ?? 0,
      }));
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), '舆情趋势');
      sheetCount++;
    }

    // 4) 用户画像
    const up = backendUserProfile.value;
    if (up) {
      if (up.activity?.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(up.activity.map(a => ({ 活跃度: a.name, 用户数: a.value }))), '用户活跃度');
        sheetCount++;
      }
      if (up.verifiedType?.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(up.verifiedType.map(v => ({ 类型: v.name, 用户数: v.value }))), '认证类型');
        sheetCount++;
      }
      if (up.fansDistribution?.labels?.length) {
        const rows = up.fansDistribution.labels.map((l, i) => ({ 粉丝区间: l, 用户数: up.fansDistribution.values[i] || 0 }));
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), '粉丝分布');
        sheetCount++;
      }
      if (up.postHours?.labels?.length) {
        const rows = up.postHours.labels.map((l, i) => ({ 时段: l, 发帖量: up.postHours.values[i] || 0 }));
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), '发布时段');
        sheetCount++;
      }
      if (up.influence?.indicators?.length) {
        const rows = up.influence.indicators.map((it, i) => ({ 维度: it.name, 分数: up.influence.values[i] || 0 }));
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), '影响力雷达');
        sheetCount++;
      }
    }

    if (sheetCount === 0) {
      ElMessage.warning('暂无可导出数据，请先刷新');
      return;
    }

    const fileName = `数据可视化_${ts}.xlsx`;
    XLSX.writeFile(wb, fileName);
    ElMessage.success(`已导出 ${sheetCount} 个数据表: ${fileName}`);
  } catch (e: any) {
    console.error(e);
    ElMessage.error(`导出失败: ${e?.message || e}`);
  }
};

const exportChart = (chartName: string, format: string) => {
  let chart: echarts.ECharts | null = null;
  if (chartName === 'propagation' && propagationGraphRef.value) {
    chart = echarts.getInstanceByDom(propagationGraphRef.value) || null;
  }
  if (!chart) { ElMessage.warning('图表未初始化'); return; }
  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
  const link = document.createElement('a');
  link.href = url;
  link.download = `${chartName}_${Date.now()}.png`;
  link.click();
  ElMessage.success(`已导出 ${chartName} 图表`);
};

// ==================== 新增功能 ====================
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
  
  if (isFullscreen.value) {
    document.documentElement.requestFullscreen?.();
    document.body.classList.add('fullscreen-dashboard');
  } else {
    document.exitFullscreen?.();
    document.body.classList.remove('fullscreen-dashboard');
  }
  
  nextTick(() => {
    charts.forEach(c => c.resize());
  });
};

const setupChartLinkage = () => {
  if (sentimentPieRef.value) {
    const chart = echarts.getInstanceByDom(sentimentPieRef.value);
    if (chart) {
      chart.on('click', (params: any) => {
        selectedSentiment.value = params.name;
        filterChartsBySentiment(params.name);
        ElMessage.info(`已选中 ${params.name} 情感`);
      });
    }
  }
};

const filterChartsBySentiment = (sentiment: string) => {
  const trendChart = echarts.getInstanceByDom(trendChartRef.value);
  if (trendChart && sentiment === '正面') {
    const option = trendChart.getOption();
    if (option.series) {
      option.series.forEach((series: any) => {
        if (series.name === '正面') {
          series.emphasis = { focus: 'series' };
          series.lineStyle = { width: 4 };
        } else {
          series.lineStyle = { opacity: 0.3, type: 'dashed' };
        }
      });
      trendChart.setOption(option);
    }
  }
  
  const wordCloudChart = echarts.getInstanceByDom(sentimentWordCloudRef.value);
  if (wordCloudChart) {
    const sentimentWords = {
      '正面': ['好', '棒', '赞', '喜欢', '支持'],
      '中性': ['一般', '还行', '不错', '可以', '还好'],
      '负面': ['不好', '差', '不满', '反对', '不喜欢']
    };
    
    const words = sentimentWords[sentiment as keyof typeof sentimentWords] || [];
    const option = {
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        data: words.map((word, idx) => ({
          name: word,
          value: Math.floor(Math.random() * 100) + 50,
          textStyle: {
            color: sentiment === '正面' ? SUCCESS : sentiment === '负面' ? DANGER : INFO
          }
        }))
      }]
    };
    wordCloudChart.setOption(option);
  }
};

const loadPropagationNetwork = async (weiboId: number) => {
  propagationLoading.value = true;
  
  try {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const { nodes, links, categories } = generatePropagationData();
    
    if (propagationGraphRef.value) {
      const existing = echarts.getInstanceByDom(propagationGraphRef.value);
      if (existing) existing.dispose();
      
      const chart = echarts.init(propagationGraphRef.value);
      chart.setOption({
        tooltip: { 
          formatter: (params: any) => params.dataType === 'node' 
            ? `${params.data.name}<br/>影响力: ${params.data.symbolSize}<br/>转发数: ${params.data.reposts || 0}<br/>粉丝数: ${params.data.followers || 0}`
            : `${params.data.source} → ${params.data.target}` 
        },
        legend: [{ data: categories.map((c: any) => c.name), orient: 'vertical', right: 10, top: 20 }],
        series: [{
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: categories,
          roam: true,
          label: { show: showNickname.value, position: 'right', fontSize: 10 },
          force: { repulsion: 300, gravity: 0.1, edgeLength: [80, 200], layoutAnimation: true },
          lineStyle: { color: 'source', curveness: 0.3, opacity: 0.7, width: 2 },
          emphasis: { 
            focus: 'adjacency', 
            lineStyle: { width: 4 },
            itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0, 0, 0, 0.3)' }
          },
          animationDuration: 1500,
          animationEasing: 'elasticOut'
        }],
      });
      
      charts.push(chart);
    }
    
    ElMessage.success('已加载传播网络');
  } catch (error) {
    ElMessage.warning('加载传播网络失败');
  } finally {
    propagationLoading.value = false;
  }
};

const exportDashboardAsImage = async () => {
  try {
    const { default: html2canvas } = await import('html2canvas');
    
    const dashboard = document.querySelector('.visualization-dashboard') as HTMLElement;
    if (!dashboard) {
      ElMessage.warning('无法找到仪表板元素');
      return;
    }
    
    const canvas = await html2canvas(dashboard, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
      allowTaint: true
    });
    
    const link = document.createElement('a');
    link.href = canvas.toDataURL('image/png');
    link.download = `dashboard_${currentDashboard.value}_${Date.now()}.png`;
    link.click();
    
    ElMessage.success('已导出仪表板图片');
  } catch (error) {
    ElMessage.warning('导出仪表板图片失败');
    exportAllChartsPNG();
  }
};

const handleExport = (type: string) => {
  if (type === 'dashboard') {
    exportDashboardAsImage();
  } else if (type === 'png') {
    exportAllChartsPNG();
  } else if (type === 'excel') {
    exportDataAsExcel();
  }
};

// ==================== 生命周期 ====================
let resizeHandler: () => void;
let realtimeTimer: number;

onMounted(async () => {
  // 先从后端拉取真实数据，再初始化图表
  await fetchBackendData();
  initOverviewCharts();
  loadWeiboDetail(1);
  
  resizeHandler = () => charts.forEach(c => c.resize());
  window.addEventListener('resize', resizeHandler);
  
  setupChartLinkage();
  
  // 实时 tab 下每 15 秒拉一次真实后端数据 (取代之前随机增量)
  realtimeTimer = window.setInterval(async () => {
    if (currentDashboard.value === 'realtime' && isStreaming.value) {
      try {
        const res = await apiClient.get('/dashboard/realtime-metrics');
        if (res.data?.code === 200 && res.data.data) {
          backendRealtime.value = res.data.data;
          const m = res.data.data.metrics;
          realtimeData.value.currentRate   = m.ratePerMin;
          realtimeData.value.todayTotal    = m.todayTotal;
          realtimeData.value.analyzedCount = m.analyzedTotal;
          realtimeData.value.alertCount    = m.alertCount;
          initRealtimeCharts();
        }
      } catch {}
    }
  }, 15000);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler);
  clearInterval(realtimeTimer);
  charts.forEach(c => c.dispose());
});

watch(trendTimeRange, () => {
  if (currentDashboard.value === 'overview') {
    handleDashboardChange();
  }
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.visualization-dashboard {
  padding: $spacing-md;
  background: $bg-page;
  min-height: calc(100vh - 120px);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  padding: $spacing-base $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    h2 { margin: 0; font-size: $font-size-extra-large; font-weight: $font-weight-semibold; }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

.dashboard-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.metric-row {
  margin-bottom: $spacing-base;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: $spacing-base;
  padding: $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  .metric-icon {
    width: 56px;
    height: 56px;
    border-radius: $border-radius-medium;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-hero;
    
    &.pulse {
      animation: pulse 2s infinite;
    }
  }
  
  &.primary .metric-icon { background: rgba($primary-color, 0.08); color: $primary-color; }
  &.success .metric-icon { background: rgba($success-color, 0.1); color: $success-color; }
  &.danger .metric-icon { background: rgba($danger-color, 0.08); color: $danger-color; }
  &.warning .metric-icon { background: rgba($warning-color, 0.1); color: $warning-color; }
  &.realtime .metric-icon { background: rgba($info-color, 0.1); color: $info-color; }
  
  .metric-info {
    flex: 1;
    .metric-value { font-size: $font-size-hero; font-weight: $font-weight-bold; color: $text-primary; line-height: 1.2; }
    .metric-label { font-size: $font-size-base; color: $text-secondary; margin-top: $spacing-xxs; }
    .metric-trend {
      display: inline-flex;
      align-items: center;
      font-size: $font-size-small;
      margin-top: 6px;
      &.up { color: $success-color; }
      &.down { color: $danger-color; }
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.chart-card {
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-xs;
  
  :deep(.el-card__header) {
    padding: $spacing-sm $spacing-base;
    border-bottom: 1px solid $border-light;
    font-weight: $font-weight-medium;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.chart-container {
  height: 300px;
  padding: $spacing-sm;
}

.prop-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-sm;
  text-align: center;

  .prop-stat-item {
    padding: $spacing-sm;
    background: $bg-page;
    border-radius: $border-radius-small;

    .prop-val {
      font-size: 22px;
      font-weight: $font-weight-bold;
      color: $primary-color;
    }

    .prop-lbl {
      font-size: $font-size-tiny;
      color: $text-secondary;
      margin-top: 2px;
    }
  }
}

.key-nodes {
  .key-node-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-xs 0;
    border-bottom: 1px solid $border-light;

    &:last-child { border-bottom: none; }

    .key-node-info {
      .key-node-name { font-weight: $font-weight-medium; font-size: $font-size-small; color: $text-primary; }
      .key-node-meta { font-size: $font-size-tiny; color: $text-secondary; margin-top: 2px; }
    }
  }
}

.graph-legend {
  .legend-row {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: 6px 0;
    font-size: $font-size-small;
    color: $text-regular;
  }

  .legend-circle {
    width: 12px;
    height: 12px;
    border-radius: $border-radius-circle;
    display: inline-block;
  }

  .legend-line {
    width: 24px;
    height: 2px;
    background: $text-placeholder;
    display: inline-block;
  }
}

// 
:global(.fullscreen-dashboard) {
  .visualization-dashboard {
    padding: 0;
    background: #000;
    min-height: 100vh;
    
    .dashboard-header {
      display: none;
    }
    
    .dashboard-content {
      height: 100vh;
      overflow: hidden;
      
      .chart-card {
        height: 50vh;
        margin-bottom: 0;
        
        .chart-container {
          height: 100% !important;
        }
      }
      
      .metric-row {
        .el-col {
          margin-bottom: 0;
        }
      }
    }
  }
  
  // 
  .el-header,
  .el-aside,
  .el-footer {
    display: none !important;
  }
  
  .el-main {
    padding: 0 !important;
    margin: 0 !important;
  }
}

// 
@media (max-width: 768px) {
  .visualization-dashboard {
    padding: $spacing-sm;
    
    .dashboard-header {
      flex-direction: column;
      gap: $spacing-sm;
      
      .header-left {
        flex-direction: column;
        gap: $spacing-sm;
        width: 100%;
        
        h2 {
          font-size: $font-size-large;
        }
        
        .el-radio-group {
          width: 100%;
          overflow-x: auto;
          flex-wrap: nowrap;
        }
      }
      
      .header-right {
        flex-wrap: wrap;
        justify-content: center;
        gap: $spacing-xs;
        
        .el-button,
        .el-dropdown {
          flex: 1;
          min-width: 0;
        }
      }
    }
    
    .dashboard-content {
      .metric-row {
        .el-col {
          margin-bottom: $spacing-sm;
        }
      }
      
      .chart-card {
        margin-bottom: $spacing-sm;
        
        .card-header {
          flex-direction: column;
          gap: $spacing-sm;
          align-items: flex-start;
        }
      }
    }
  }
  
  .metric-card {
    flex-direction: column;
    text-align: center;
    gap: $spacing-sm;
    
    .metric-icon {
      width: 48px;
      height: 48px;
      font-size: $font-size-large;
    }
    
    .metric-info {
      .metric-value {
        font-size: $font-size-large;
      }
      
      .metric-label {
        font-size: $font-size-small;
      }
    }
  }
  
  .chart-container {
    height: 250px !important;
  }
  
  .prop-stats {
    grid-template-columns: 1fr;
  }
  
  .key-nodes {
    .key-node-item {
      flex-direction: column;
      align-items: flex-start;
      gap: $spacing-xs;
    }
  }
}

// 
@media (max-width: 480px) {
  .visualization-dashboard {
    padding: $spacing-xs;
    
    .dashboard-header {
      .header-left {
        h2 {
          font-size: $font-size-medium;
        }
      }
      
      .header-right {
        .el-button {
          font-size: $font-size-tiny;
          padding: 6px 12px;
        }
      }
    }
  }
  
  .metric-card {
    padding: $spacing-sm;
    
    .metric-icon {
      width: 40px;
      height: 40px;
      font-size: $font-size-medium;
    }
    
    .metric-info {
      .metric-value {
        font-size: $font-size-medium;
      }
      
      .metric-label {
        font-size: $font-size-tiny;
      }
    }
  }
  
  .chart-container {
    height: 200px !important;
    padding: $spacing-xs;
  }
}
</style>
