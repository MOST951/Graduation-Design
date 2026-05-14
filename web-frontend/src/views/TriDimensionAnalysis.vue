<template>
  <div class="tri-dimension-module">
    <!-- 顶部操作栏 -->
    <div class="action-bar">
      <el-button-group>
        <el-button type="primary" :icon="DataAnalysis" @click="runAnalysis" :loading="analyzing">
          开始分析
        </el-button>
        <el-button :icon="Setting" @click="showConfigPanel = true">
          参数配置
        </el-button>
        <el-button :icon="Download" @click="exportData">
          导出数据
        </el-button>
      </el-button-group>
      
      <div class="config-quick">
        <span>预设配置：</span>
        <el-select v-model="selectedConfig" @change="loadPresetConfig" style="width: 150px">
          <el-option label="默认配置" value="default" />
          <el-option label="情感优先" value="sentiment_first" />
          <el-option label="热度优先" value="heat_first" />
        </el-select>
      </div>
    </div>
    
    <el-row :gutter="20" class="main-row">
      <!-- 左侧：三维权重配置面板 -->
      <el-col :span="6" class="sidebar-col">
       <div class="sidebar-sticky">
        <!-- 论文公式卡片 -->
        <el-card shadow="hover" class="formula-card">
          <template #header>
            <div class="card-hdr"><span>热点话题综合排序公式</span><el-tag size="small" type="warning">公式4-7</el-tag></div>
          </template>
          <div class="formula-display">
            <div class="formula-tex">Score = ω₁·N(S) + ω₂·H<sub>norm</sub> + ω₃·γ(t)</div>
            <div class="formula-sub">γ(t) = 2<sup>-Δt/H</sup> , H = {{ config.decay_half_life_hours }}h</div>
          </div>
        </el-card>

        <el-card shadow="hover" class="config-card" style="margin-top: 12px">
          <template #header>
            <div class="card-hdr"><span>三维权重 (ω₁+ω₂+ω₃=1)</span>
              <el-tag :type="weightSum === 1 ? 'success' : 'danger'" size="small">∑={{ weightSum }}</el-tag>
            </div>
          </template>
          <div class="weight-config">
            <div class="weight-item">
              <div class="weight-header">
                <span>ω₁ 情感强度 N(S)</span>
                <el-tag type="primary">{{ (config.sentiment_weight * 100).toFixed(0) }}%</el-tag>
              </div>
              <el-slider v-model="config.sentiment_weight" :min="0" :max="1" :step="0.05" @change="onTriWeightChange('sentiment')" />
            </div>
            <div class="weight-item">
              <div class="weight-header">
                <span>ω₂ 热度 H<sub>norm</sub></span>
                <el-tag type="success">{{ (config.heat_weight * 100).toFixed(0) }}%</el-tag>
              </div>
              <el-slider v-model="config.heat_weight" :min="0" :max="1" :step="0.05" @change="onTriWeightChange('heat')" />
            </div>
            <div class="weight-item">
              <div class="weight-header">
                <span>ω₃ 时效性 γ(t)</span>
                <el-tag type="warning">{{ (config.timeliness_weight * 100).toFixed(0) }}% (自动)</el-tag>
              </div>
              <el-slider v-model="config.timeliness_weight" :min="0" :max="1" :step="0.05" disabled />
              <div class="weight-hint">时效权重 = 1 - 情感 - 热度，自动补足</div>
            </div>
            <!-- 权重可视化条 -->
            <div class="weight-bar">
              <div class="bar-seg sentiment" :style="{width: config.sentiment_weight * 100 + '%'}">ω₁</div>
              <div class="bar-seg heat" :style="{width: config.heat_weight * 100 + '%'}">ω₂</div>
              <div class="bar-seg timeliness" :style="{width: config.timeliness_weight * 100 + '%'}">ω₃</div>
            </div>
          </div>

          <el-divider>互动权重 (λ)</el-divider>
          <el-form label-position="left" label-width="80px" size="small">
            <el-form-item label="λ_r 转发">
              <el-input-number v-model="config.repost_weight" :min="0" :max="10" :step="0.5" />
            </el-form-item>
            <el-form-item label="λ_c 评论">
              <el-input-number v-model="config.comment_weight" :min="0" :max="10" :step="0.5" />
            </el-form-item>
            <el-form-item label="λ_l 点赞">
              <el-input-number v-model="config.like_weight" :min="0" :max="10" :step="0.5" />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" class="config-card" style="margin-top: 12px">
          <template #header>
            <div class="card-hdr"><span>时间衰减 γ(t)</span><el-tag size="small" type="info">公式4-6</el-tag></div>
          </template>
          <el-form label-position="left" label-width="100px" size="small">
            <el-form-item label="启用衰减">
              <el-switch v-model="config.time_decay_enabled" />
            </el-form-item>
            <el-form-item label="H" v-if="config.time_decay_enabled">
              <el-select v-model="config.decay_half_life_hours" @change="onHalfLifeChange" style="width: 100%">
                <el-option label="6h" :value="6" />
                <el-option label="12h" :value="12" />
                <el-option label="24h" :value="24" />
                <el-option label="48h" :value="48" />
              </el-select>
            </el-form-item>
            <div v-if="config.time_decay_enabled" class="decay-preview">
              <div class="decay-label">衰减预览 (γ值)</div>
              <div class="decay-ticks">
                <span v-for="h in [0,6,12,24,48]" :key="h" class="tick">
                  {{ h }}h → {{ Math.pow(2, -h / config.decay_half_life_hours).toFixed(2) }}
                </span>
              </div>
            </div>
            <el-divider>四象限阈值</el-divider>
            <el-form-item label="情感阈值">
              <el-slider v-model="config.sentiment_threshold" :min="0" :max="1" :step="0.05" show-input />
            </el-form-item>
            <el-form-item label="热度阈值">
              <el-slider v-model="config.heat_threshold" :min="0" :max="1" :step="0.05" show-input />
            </el-form-item>
          </el-form>
        </el-card>
       </div>
      </el-col>
      
      <!-- 中间：散点图可视化 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="chart-header">
              <span>热点话题情感-热度分布图</span>
              <el-radio-group v-model="chartMode" size="small">
                <el-radio-button label="wordcloud">词云图</el-radio-button>
                <el-radio-button label="scatter">散点图</el-radio-button>
                <el-radio-button label="heatmap">热力图</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="scatterChartRef" style="height: 500px"></div>
        </el-card>
        
        <!-- 四象限统计 -->
        <el-row :gutter="12" style="margin-top: 16px">
          <el-col :span="6" v-for="(quad, key) in quadrantInfo" :key="key">
            <el-card 
              shadow="hover" 
              class="quadrant-card"
              :style="{ borderTop: `3px solid ${quad.color}` }"
              @click="filterByQuadrant(key)"
            >
              <div class="quadrant-stat">
                <div class="stat-value" :style="{ color: quad.color }">
                  {{ quadrantStats[key]?.count || 0 }}
                </div>
                <div class="stat-label">{{ quad.label }}</div>
                <div class="stat-ratio">
                  {{ ((quadrantStats[key]?.ratio || 0) * 100).toFixed(1) }}%
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
      
      <!-- 右侧：排名列表 -->
      <el-col :span="6" class="sidebar-col">
       <div class="sidebar-sticky">
        <el-card shadow="hover">
          <template #header>
            <div class="rank-header">
              <span>热点话题 Top {{ rankList.length }}</span>
              <el-select v-model="rankFilter" size="small" style="width: 100px">
                <el-option label="全部" value="all" />
                <el-option label="高情感高热" value="high_sentiment_high_heat" />
                <el-option label="高情感低热" value="high_sentiment_low_heat" />
                <el-option label="低情感高热" value="low_sentiment_high_heat" />
                <el-option label="低情感低热" value="low_sentiment_low_heat" />
              </el-select>
            </div>
          </template>
          
          <div v-if="selectedKeyword" class="keyword-filter">
            <span>关键词筛选：</span>
            <el-tag closable type="primary" @close="selectedKeyword = ''">{{ selectedKeyword }}</el-tag>
          </div>
          <div class="rank-list">
            <div 
              v-for="item in filteredRankList" 
              :key="item.id" 
              class="rank-item"
              :class="{ active: selectedItem?.id === item.id }"
              @click="selectItem(item)"
            >
              <div class="rank-badge" :class="getRankClass(item.rank)">
                {{ item.rank }}
              </div>
              <div class="rank-content">
                <div class="rank-text">{{ item.text }}</div>
                <div class="rank-meta">
                  <el-tag :type="getSentimentType(item.sentiment?.polarity)" size="small">
                    {{ getSentimentLabel(item.sentiment?.polarity) }}
                  </el-tag>
                  <span class="score">得分: {{ item.tri_score }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
       </div>
      </el-col>
    </el-row>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="微博详情分析" width="700px">
      <div v-if="selectedItem" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="排名">
            <el-tag type="primary">第 {{ selectedItem.rank }} 名</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="热点综合得分">
            <span class="highlight">{{ selectedItem.tri_score }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="情感极性">
            <el-tag :type="getSentimentType(selectedItem.sentiment?.polarity)">
              {{ getSentimentLabel(selectedItem.sentiment?.polarity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="情感得分">
            {{ selectedItem.sentiment?.score }}
          </el-descriptions-item>
          <el-descriptions-item label="情感强度">
            <el-progress :percentage="selectedItem.sentiment?.intensity || 0" />
          </el-descriptions-item>
          <el-descriptions-item label="四象限">
            <el-tag :color="quadrantInfo[selectedItem.quadrant]?.color" effect="dark">
              {{ quadrantInfo[selectedItem.quadrant]?.label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="热度得分">
            {{ selectedItem.heat?.score }}
          </el-descriptions-item>
          <el-descriptions-item label="时间衰减">
            {{ selectedItem.heat?.time_decay }}
          </el-descriptions-item>
          <el-descriptions-item label="影响力因子">
            {{ selectedItem.heat?.influence }}
          </el-descriptions-item>
          <el-descriptions-item label="互动数据" :span="2">
            转发: {{ selectedItem.interactions?.reposts }} | 
            评论: {{ selectedItem.interactions?.comments }} | 
            点赞: {{ selectedItem.interactions?.likes }}
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider> </el-divider>
        <div class="weibo-text">{{ selectedItem.text }}</div>
        
        <el-divider> </el-divider>
        <div style="text-align: center;">
          <el-button type="primary" @click="showHistoricalRanking" :icon="TrendCharts">
             7 
          </el-button>
        </div>
      </div>
    </el-dialog>
    
    <!--  -->
    <el-dialog v-model="showHistoricalDialog" :title="`  - ${selectedItem?.text?.slice(0, 30)}...`" width="800px">
      <div v-if="selectedItem" class="historical-content">
        <div ref="historicalChartRef" style="height: 400px;"></div>
        <div class="historical-stats">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-statistic title=" " :value="historicalStats.bestRank" />
            </el-col>
            <el-col :span="8">
              <el-statistic title=" " :value="historicalStats.worstRank" />
            </el-col>
            <el-col :span="8">
              <el-statistic title=" " :value="historicalStats.avgRank" :precision="1" />
            </el-col>
          </el-row>
        </div>
      </div>
    </el-dialog>
    
    <!--  -->配置面板抽屉 -->
    <el-drawer v-model="showConfigPanel" title="详细配置" size="400px">
      <el-form label-position="top">
        <el-form-item label="配置名称">
          <el-input v-model="configName" placeholder="输入配置名称" />
        </el-form-item>
        
        <el-divider>情感维度</el-divider>
        <el-form-item label="情感权重">
          <el-slider v-model="config.sentiment_weight" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="使用深度学习">
          <el-switch v-model="config.use_deep_learning" />
        </el-form-item>
        
        <el-divider>热度维度</el-divider>
        <el-form-item label="热度权重">
          <el-slider v-model="config.heat_weight" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>
        
        <el-divider>论文公式 (4-3 ~ 4-7)</el-divider>
        <div class="formula-box">
          <p><strong>公式4-3 情感归一化：</strong></p>
          <code>N(S) = (|S| + 1) / 2</code>
          <p style="margin-top: 8px"><strong>公式4-4 热度得分：</strong></p>
          <code>H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)</code>
          <p style="margin-top: 8px"><strong>公式4-6 时间衰减：</strong></p>
          <code>γ(t) = 2^(-Δt / H),  H = 12h</code>
          <p style="margin-top: 8px"><strong>公式4-7 综合得分：</strong></p>
          <code>Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)</code>
        </div>
      </el-form>
      
      <template #footer>
        <el-button @click="showConfigPanel = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import { DataAnalysis, Setting, Download, TrendCharts } from '@element-plus/icons-vue';
import { SUCCESS, PRIMARY, DANGER, INFO, WARNING } from '@/styles/colors';

import { 
  getHotSearch, 
  apiClient, 
  type HotSearchItem 
} from '@/api/weibo';

// 
const analyzing = ref(false);
const showConfigPanel = ref(false);
const showDetailDialog = ref(false);
const showHistoricalDialog = ref(false);
const selectedConfig = ref('default');
const chartMode = ref('wordcloud');
const rankFilter = ref('all');
const selectedKeyword = ref('');
const configName = ref('');
const selectedItem = ref<any>(null);

// 
const scatterChartRef = ref<HTMLElement>();
const historicalChartRef = ref<HTMLElement>();
let scatterChart: echarts.ECharts | null = null;
let historicalChart: echarts.ECharts | null = null;

// 
const historicalStats = ref({
  bestRank: 0,
  worstRank: 0,
  avgRank: 0
});

// 配置 (论文 ω₁=0.4, ω₂=0.4, ω₃=0.2)
const config = reactive({
  sentiment_weight: 0.4,
  heat_weight: 0.4,
  timeliness_weight: 0.2,
  repost_weight: 1.0,
  comment_weight: 2.0,
  like_weight: 1.0,
  time_decay_enabled: true,
  decay_half_life_hours: 12,
  influence_enabled: true,
  verified_bonus: 1.5,
  sentiment_threshold: 0.5,
  heat_threshold: 0.5,
  use_deep_learning: true,
});

// 四象限信息
const quadrantInfo: Record<string, any> = {
  high_sentiment_high_heat: {
    name: '高情感-高热度',
    label: '重点关注',
    color: DANGER,
  },
  high_sentiment_low_heat: {
    name: '高情感-低热度',
    label: '潜在风险',
    color: WARNING,
  },
  low_sentiment_high_heat: {
    name: '低情感-高热度',
    label: '热门中性',
    color: PRIMARY,
  },
  low_sentiment_low_heat: {
    name: '低情感-低热度',
    label: '一般内容',
    color: INFO,
  },
};

// 数据
const rankList = ref<any[]>([]);
const scatterData = ref<any[]>([]);
const quadrantStats = ref<Record<string, any>>({});

// 计算属性
const filteredRankList = computed(() => {
  let list = rankList.value;
  if (rankFilter.value !== 'all') {
    list = list.filter(item => item.quadrant === rankFilter.value);
  }
  if (selectedKeyword.value) {
    list = list.filter(item => (item.text || '').includes(selectedKeyword.value));
  }
  return list.slice(0, 20);
});

// 三维权重联动 (ω₁+ω₂+ω₃=1)
const weightSum = computed(() => {
  return Number((config.sentiment_weight + config.heat_weight + config.timeliness_weight).toFixed(2));
});

// 时效权重自动补足：用户只调情感与热度，时效=1-情感-热度
const onTriWeightChange = (changed: string) => {
  if (changed === 'sentiment' || changed === 'heat') {
    // 若情感+热度>1，按比例缩放至1
    const sh = config.sentiment_weight + config.heat_weight;
    if (sh > 1) {
      const scale = 1 / sh;
      config.sentiment_weight = Number((config.sentiment_weight * scale).toFixed(2));
      config.heat_weight = Number((config.heat_weight * scale).toFixed(2));
    }
  }
  // 时效权重 = 1 - 情感 - 热度
  config.timeliness_weight = Number(
    Math.max(0, 1 - config.sentiment_weight - config.heat_weight).toFixed(2)
  );
};

// 加载预设配置 (论文 ω₁=0.4, ω₂=0.4, ω₃=0.2)
const loadPresetConfig = () => {
  const presets: Record<string, any> = {
    default: { sentiment_weight: 0.4, heat_weight: 0.4, timeliness_weight: 0.2, repost_weight: 1.0, decay_half_life_hours: 12 },
    sentiment_first: { sentiment_weight: 0.6, heat_weight: 0.25, timeliness_weight: 0.15, decay_half_life_hours: 12 },
    heat_first: { sentiment_weight: 0.25, heat_weight: 0.55, timeliness_weight: 0.2, decay_half_life_hours: 12 },
  };
  
  const preset = presets[selectedConfig.value];
  if (preset) {
    Object.assign(config, preset);
    ElMessage.success(`已加载 ${selectedConfig.value} 配置`);
  }
};

// 运行分析
const runAnalysis = async () => {
  analyzing.value = true;
  
  try {
    ElMessage.info('正在获取实时热搜数据...');
    // 1. 获取真实热搜数据
    const hotList = await getHotSearch();
    
    if (!hotList || hotList.length === 0) {
      throw new Error('未获取到热搜数据');
    }
    
    // 2. 转换为分析格式
    // 热搜数据只有标题和热度值，我们需要基于此构建符合三维度模型的数据结构
    const analysisData = hotList.map((item: HotSearchItem) => {
      // 基于热度值估算互动数据 (仅作演示转换)
      const baseCount = Math.floor(item.hot_value / 100); 
      return {
        id: `hot_${item.rank}`,
        text: item.title, // 热搜词作为文本
        source: '微博热搜',
        created_at: item.crawl_time || new Date().toISOString(),
        // 模拟用户影响力 (排名越靠前，通常影响力越大)
        user: {
          id: 'official',
          screen_name: '微博热搜',
          followers_count: 1000000 + (50 - item.rank) * 10000, 
          verified: true
        },
        // 模拟互动数据
        interactions: {
          reposts: Math.floor(baseCount * 0.2),
          comments: Math.floor(baseCount * 0.3),
          likes: Math.floor(baseCount * 0.5)
        }
      };
    });

    ElMessage.info(`获取到 ${analysisData.length} 条热搜，开始热点话题分析...`);

    // 3. 调用后端热点话题分析接口
    const response = await apiClient.post('/weibo/rank/tri', {
      data: analysisData,
      sentiment_weight: config.sentiment_weight,
      heat_weight: config.heat_weight,
      timeliness_weight: config.decay_half_life_hours ? 0.2 : 0, // 简化参数映射
      top_k: 50
    });
    
    const result = response.data;
    
    if (result.code === 200) {
      rankList.value = result.data.ranked_items;
      
      // 生成散点图数据
      scatterData.value = result.data.ranked_items.map((item: any) => ({
        id: item.id,
        // 映射得分到 0-100 区间用于展示
        x: Math.min(100, Math.max(0, item.heat.score * 100)), 
        y: Math.min(100, Math.max(0, (parseFloat(item.sentiment.score) + 1) * 50)),
        value: parseFloat(item.tri_score) * 100,
        quadrant: item.quadrant,
        text: item.text
      }));
      
      // 重新计算统计信息
      calculateQuadrantStats();
      
      updateScatterChart();
      ElMessage.success('分析完成，结果已保存');
    } else {
      throw new Error(result.message || '后端分析返回错误');
    }
  } catch (error: any) {
    console.error('分析失败详细信息:', {
      message: error.message,
      response: error.response,
      stack: error.stack
    });
    
    let errorMsg = '分析过程出现异常';
    if (error.response) {
      // 请求已发出，但服务器响应状态码不在 2xx 范围内
      errorMsg += `: 服务器错误 ${error.response.status}`;
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      errorMsg += ': 无法连接到服务器，请检查后端是否已启动';
    } else {
      // 在设置请求时发生了一些事情，触发了错误
      errorMsg += `: ${error.message}`;
    }
    
    ElMessage.warning(errorMsg + '，正在加载模拟数据用于展示');
    // 降级：使用模拟数据
    loadMockResults();
  } finally {
    analyzing.value = false;
  }
};

// 计算象限统计
const calculateQuadrantStats = () => {
  const stats: Record<string, any> = {};
  for (const q of Object.keys(quadrantInfo)) {
    const items = rankList.value.filter(r => r.quadrant === q);
    stats[q] = {
      count: items.length,
      ratio: rankList.value.length > 0 ? items.length / rankList.value.length : 0,
    };
  }
  quadrantStats.value = stats;
};

// 生成模拟数据 (已废弃，保留作为参考)
const generateMockData = () => {
  const data = [];
  for (let i = 0; i < 100; i++) {
    data.push({
      id: `${i + 1}`,
      text: `这是第${i + 1}条测试微博内容，用于展示热点话题分析效果...`,
      reposts_count: Math.floor(Math.random() * 10000),
      comments_count: Math.floor(Math.random() * 5000),
      attitudes_count: Math.floor(Math.random() * 20000),
      followers_count: Math.floor(Math.random() * 1000000),
      verified: Math.random() > 0.7,
      verified_type: Math.floor(Math.random() * 4) - 1,
      created_at: new Date(Date.now() - Math.random() * 86400000 * 7).toISOString(),
    });
  }
  return data;
};

// 加载模拟结果
const loadMockResults = () => {
  const mockResults = [];
  for (let i = 0; i < 50; i++) {
    const sentimentScore = Math.random() * 2 - 1;
    const heatScore = Math.random();
    const quadrant = getQuadrant(sentimentScore, heatScore);
    
    mockResults.push({
      id: `${i + 1}`,
      text: `这是第${i + 1}条微博，情感${sentimentScore > 0 ? '正面' : '负面'}，热度${heatScore > 0.5 ? '高' : '低'}`,
      rank: i + 1,
      tri_score: (0.5 * Math.abs(sentimentScore) + 0.5 * heatScore).toFixed(4),
      sentiment: {
        polarity: sentimentScore > 0.2 ? 'positive' : sentimentScore < -0.2 ? 'negative' : 'neutral',
        score: sentimentScore.toFixed(4),
        intensity: (Math.abs(sentimentScore) * 100).toFixed(2),
      },
      heat: {
        score: (heatScore * 10).toFixed(4),
        time_decay: (0.5 + Math.random() * 0.5).toFixed(4),
        influence: (0.5 + Math.random() * 2).toFixed(4),
      },
      quadrant,
      interactions: {
        reposts: Math.floor(Math.random() * 10000),
        comments: Math.floor(Math.random() * 5000),
        likes: Math.floor(Math.random() * 20000),
      },
    });
  }
  
  rankList.value = mockResults;
  
  // 生成散点图数据
  scatterData.value = mockResults.map(item => ({
    id: item.id,
    x: parseFloat(item.heat.score) * 10,
    y: (parseFloat(item.sentiment.score) + 1) * 50,
    value: parseFloat(item.tri_score) * 100,
    quadrant: item.quadrant,
    text: item.text.slice(0, 30),
  }));
  
  // 统计四象限
  const stats: Record<string, any> = {};
  for (const q of Object.keys(quadrantInfo)) {
    const items = mockResults.filter(r => r.quadrant === q);
    stats[q] = {
      count: items.length,
      ratio: items.length / mockResults.length,
    };
  }
  quadrantStats.value = stats;
  
  updateScatterChart();
};

// 获取象限
const getQuadrant = (sentiment: number, heat: number) => {
  const highSentiment = Math.abs(sentiment) >= 0.5;
  const highHeat = heat >= 0.5;
  
  if (highSentiment && highHeat) return 'high_sentiment_high_heat';
  if (highSentiment && !highHeat) return 'high_sentiment_low_heat';
  if (!highSentiment && highHeat) return 'low_sentiment_high_heat';
  return 'low_sentiment_low_heat';
};

// 更新散点图
const updateScatterChart = () => {
  if (!scatterChart) return;
  
  // 清除旧配置
  scatterChart.clear();
  
  if (chartMode.value === 'heatmap') {
    // 热力图模式
    updateHeatmapChart();
  } else if (chartMode.value === 'wordcloud') {
    // 词云图模式
    updateWordcloudChart();
  } else {
    // 散点图模式
    updateScatterMode();
  }
};

// 词云图模式：基于热点话题文本分词词频，颜色映射情感倾向
const CN_STOPWORDS = new Set(['的','了','是','在','和','与','也','就','都','而','及','或','以','对','中','为','上','下','并','等','一','一个','一些','这','那','有','到','被','把','给','从','向','你','我','他','她','它','们','这个','那个','大家','以及','还','又','只','要','会','能','可以','需要','已经','正在','可能','应该','一直','还是','不是','没有','虽然','但是','所以','因为','不过','其实','只是','如果','即使','虽然','除了','关于','针对','按照','根据','通过']);

const tokenize = (text: string): string[] => {
  if (!text) return [];
  // 简单按非中英文字符切分
  const segments = text.split(/[^\u4e00-\u9fa5A-Za-z0-9]+/).filter(Boolean);
  // 滑窗 2-gram 提取中文词（无 jieba 时的退化方案）
  const tokens: string[] = [];
  for (const seg of segments) {
    if (/^[A-Za-z]+$/.test(seg)) {
      if (seg.length >= 2) tokens.push(seg.toLowerCase());
      continue;
    }
    if (seg.length >= 2) {
      // 取 2-gram
      for (let i = 0; i < seg.length - 1; i++) {
        const bg = seg.slice(i, i + 2);
        if (!/[0-9]/.test(bg)) tokens.push(bg);
      }
    }
  }
  return tokens.filter(t => !CN_STOPWORDS.has(t) && t.length >= 2);
};

const updateWordcloudChart = () => {
  if (!scatterChart) return;
  // 词频统计 + 情感倾向加权
  const wordStats: Record<string, { freq: number; sentSum: number; sentCount: number }> = {};
  for (const item of rankList.value) {
    const tokens = tokenize(item.text || '');
    const sentScore = parseFloat(item.sentiment?.score ?? '0') || 0;
    for (const w of tokens) {
      if (!wordStats[w]) wordStats[w] = { freq: 0, sentSum: 0, sentCount: 0 };
      wordStats[w].freq++;
      wordStats[w].sentSum += sentScore;
      wordStats[w].sentCount++;
    }
  }
  const data = Object.entries(wordStats)
    .map(([name, s]) => {
      const avgSent = s.sentCount > 0 ? s.sentSum / s.sentCount : 0;
      // 红负面 / 灰中性 / 绿正面
      let color = '#909399';
      if (avgSent > 0.2) color = '#67c23a';
      else if (avgSent < -0.2) color = '#f56c6c';
      return { name, value: s.freq, textStyle: { color } };
    })
    .sort((a, b) => b.value - a.value)
    .slice(0, 100);

  scatterChart.setOption({
    tooltip: {
      show: true,
      formatter: (p: any) => `<b>${p.name}</b><br/>词频: ${p.value}`,
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [14, 60],
      rotationRange: [-30, 30],
      gridSize: 8,
      drawOutOfBound: false,
      left: 'center',
      top: 'center',
      width: '95%',
      height: '95%',
      data,
    }],
  }, { notMerge: true });
  // 点击词云关键词 → 筛选列表
  scatterChart.off('click');
  scatterChart.on('click', (params: any) => {
    if (params?.name) {
      selectedKeyword.value = params.name;
      ElMessage.success(`已按关键词「${params.name}」筛选热门微博`);
    }
  });
};

// 散点图模式
const updateScatterMode = () => {
  if (!scatterChart) return;
  
  // 按象限分组数据
  const seriesData: Record<string, any[]> = {};
  for (const q of Object.keys(quadrantInfo)) {
    seriesData[q] = [];
  }
  
  for (const item of scatterData.value) {
    if (seriesData[item.quadrant]) {
      seriesData[item.quadrant].push([item.x, item.y, item.value, item.text, item.id]);
    }
  }
  
  const series = Object.entries(quadrantInfo).map(([key, info]) => ({
    name: info.label,
    type: 'scatter',
    symbolSize: (data: any) => Math.max(10, Math.min(30, data[2] / 3)),
    data: seriesData[key],
    itemStyle: { color: info.color },
    emphasis: {
      focus: 'series',
      itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
    },
  }));
  
  scatterChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data;
        return `
          <div style="padding: 8px">
            <div style="font-weight: bold; margin-bottom: 4px">${data[3]}</div>
            <div>热度: ${data[0].toFixed(2)}</div>
            <div>情感: ${data[1].toFixed(2)}</div>
            <div>综合得分: ${data[2].toFixed(2)}</div>
          </div>
        `;
      },
    },
    legend: {
      data: Object.values(quadrantInfo).map(q => q.label),
      bottom: 0,
    },
    grid: { left: '10%', right: '10%', top: '10%', bottom: '15%' },
    xAxis: {
      name: '热度',
      nameLocation: 'middle',
      nameGap: 30,
      min: 0,
      max: 100,
      splitLine: { show: true, lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      name: '情感强度',
      nameLocation: 'middle',
      nameGap: 40,
      min: 0,
      max: 100,
      splitLine: { show: true, lineStyle: { type: 'dashed' } },
    },
    series,
    // 添加四象限分界线
    graphic: [
      {
        type: 'line',
        shape: { x1: '50%', y1: '10%', x2: '50%', y2: '85%' },
        style: { stroke: '#999', lineDash: [5, 5] },
      },
      {
        type: 'line',
        shape: { x1: '10%', y1: '50%', x2: '90%', y2: '50%' },
        style: { stroke: '#999', lineDash: [5, 5] },
      },
    ],
  });
};

// 热力图模式
const updateHeatmapChart = () => {
  if (!scatterChart) return;
  
  // 将散点数据转换为热力图数据（10x10网格）
  const gridSize = 10;
  const heatmapData: number[][] = [];
  
  // 初始化网格
  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      heatmapData.push([i, j, 0]);
    }
  }
  
  // 统计每个网格中的数据点数量和平均得分
  const gridCounts: Record<string, { count: number; totalScore: number }> = {};
  
  for (const item of scatterData.value) {
    const gridX = Math.min(Math.floor(item.x / 10), gridSize - 1);
    const gridY = Math.min(Math.floor(item.y / 10), gridSize - 1);
    const key = `${gridX}-${gridY}`;
    
    if (!gridCounts[key]) {
      gridCounts[key] = { count: 0, totalScore: 0 };
    }
    gridCounts[key].count++;
    gridCounts[key].totalScore += item.value;
  }
  
  // 更新热力图数据
  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      const key = `${i}-${j}`;
      const idx = i * gridSize + j;
      if (gridCounts[key]) {
        // 使用数量和平均得分的组合作为热力值
        heatmapData[idx][2] = gridCounts[key].count * (gridCounts[key].totalScore / gridCounts[key].count);
      }
    }
  }
  
  // 找出最大值用于归一化
  const maxValue = Math.max(...heatmapData.map(d => d[2]), 1);
  
  scatterChart.setOption({
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const data = params.data;
        const xRange = `${data[0] * 10}-${(data[0] + 1) * 10}`;
        const yRange = `${data[1] * 10}-${(data[1] + 1) * 10}`;
        return `
          <div style="padding: 8px">
            <div>热度范围: ${xRange}</div>
            <div>情感范围: ${yRange}</div>
            <div>热力值: ${data[2].toFixed(2)}</div>
          </div>
        `;
      },
    },
    grid: { left: '10%', right: '15%', top: '10%', bottom: '15%' },
    xAxis: {
      type: 'category',
      name: '热度',
      nameLocation: 'middle',
      nameGap: 30,
      data: ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70-80', '80-90', '90-100'],
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      name: '情感强度',
      nameLocation: 'middle',
      nameGap: 50,
      data: ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70-80', '80-90', '90-100'],
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      calculable: true,
      orient: 'vertical',
      right: '2%',
      top: 'center',
      inRange: {
        color: ['#f0f9ff', '#bae6fd', '#7dd3fc', '#38bdf8', '#0ea5e9', '#0284c7', '#0369a1', '#075985', '#0c4a6e'],
      },
    },
    series: [{
      name: '热力分布',
      type: 'heatmap',
      data: heatmapData,
      label: {
        show: true,
        formatter: (params: any) => {
          return params.data[2] > 0 ? Math.round(params.data[2]).toString() : '';
        },
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
    }],
  });
};

// 
const onHalfLifeChange = (value: number) => {
  // 
  recalculateTimeDecay();
  ElMessage.info(`  H = ${value}h`);
};

// 
const recalculateTimeDecay = () => {
  if (!config.time_decay_enabled || rankList.value.length === 0) return;
  
  rankList.value.forEach(item => {
    if (item.heat) {
      const now = new Date().getTime();
      const createdAt = new Date(item.created_at).getTime();
      const deltaHours = (now - createdAt) / (1000 * 60 * 60);
      
      // 
      item.heat.time_decay = Math.pow(2, -deltaHours / config.decay_half_life_hours);
      
      // 
      const sentimentNormalized = (Math.abs(parseFloat(item.sentiment?.score || 0)) + 1) / 2;
      const heatNormalized = parseFloat(item.heat?.score || 0);
      const timeDecay = item.heat.time_decay;
      
      item.tri_score = (
        config.sentiment_weight * sentimentNormalized +
        config.heat_weight * heatNormalized +
        config.timeliness_weight * timeDecay
      ).toFixed(4);
    }
  });
  
  // 
  rankList.value.sort((a, b) => parseFloat(b.tri_score) - parseFloat(a.tri_score));
  rankList.value.forEach((item, index) => {
    item.rank = index + 1;
  });
  
  // 
  calculateQuadrantStats();
  updateScatterChart();
};

// 
const showHistoricalRanking = () => {
  if (!selectedItem.value) return;
  
  showHistoricalDialog.value = true;
  
  // 
  setTimeout(() => {
    updateHistoricalChart();
  }, 100);
};

// 
const updateHistoricalChart = () => {
  if (!historicalChartRef.value || !selectedItem.value) return;
  
  if (!historicalChart) {
    historicalChart = echarts.init(historicalChartRef.value);
  }
  
  // 
  const historicalData = generateHistoricalData(selectedItem.value);
  
  // 
  historicalStats.value = {
    bestRank: Math.min(...historicalData.map(d => d.rank)),
    worstRank: Math.max(...historicalData.map(d => d.rank)),
    avgRank: historicalData.reduce((sum, d) => sum + d.rank, 0) / historicalData.length
  };
  
  // 
  const option = {
    title: {
      text: ' 7 ',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0];
        return `
          <div style="padding: 8px">
            <div> : ${data.data[0]}</div>
            <div> : ${data.data[1]}</div>
            <div> : ${data.data[2]}</div>
          </div>
        `;
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      top: '15%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: historicalData.map(d => d.date),
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: ' ',
      inverse: true, // 
      min: 1,
      max: Math.max(...historicalData.map(d => d.rank)) + 5
    },
    series: [{
      name: ' ',
      type: 'line',
      data: historicalData.map(d => d.rank),
      smooth: true,
      lineStyle: {
        width: 3,
        color: '#0ea5e9'
      },
      itemStyle: {
        color: '#0ea5e9',
        borderWidth: 2,
        borderColor: '#fff'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(14, 165, 233, 0.3)'
          }, {
            offset: 1, color: 'rgba(14, 165, 233, 0.05)'
          }]
        }
      }
    }]
  };

  historicalChart.setOption(option);

  historicalChart.on('click', (params: any) => {
    if (params.data) {
      const id = params.data[4];
      const item = rankList.value.find((r: any) => r.id === id);
      if (item) {
        selectItem(item);
      }
    }
  });
};

// 选择项目
const selectItem = (item: any) => {
  selectedItem.value = item;
  showDetailDialog.value = true;
};

// 按象限筛选
const filterByQuadrant = (quadrant: string) => {
  rankFilter.value = quadrant;
};

// 保存配置
const saveConfig = () => {
  showConfigPanel.value = false;
  ElMessage.success('配置已保存');
};

// 导出数据
const exportData = () => {
  try {
    // 
    import('xlsx').then((XLSX) => {
      const wb = XLSX.utils.book_new();
      
      // 
      const exportData = rankList.value.map(item => ({
        '排名': item.rank,
        '内容': item.text,
        '情感': getSentimentLabel(item.sentiment?.polarity),
        '情感得分': item.sentiment?.score,
        '热度得分': item.heat?.score,
        '综合得分': item.tri_score,
        '象限': quadrantInfo[item.quadrant]?.label,
        '转发': item.interactions?.reposts,
        '评论': item.interactions?.comments,
        '点赞': item.interactions?.likes,
        '时间': item.created_at
      }));
      
      // 
      const ws = XLSX.utils.json_to_sheet(exportData);
      XLSX.utils.book_append_sheet(wb, ws, ' ');
      
      // 
      const fileName = `_${new Date().toISOString().slice(0, 10)}.xlsx`;
      XLSX.writeFile(wb, fileName);
      
      ElMessage.success(` ${fileName}`);
    }).catch(error => {
      console.error('Excel export failed:', error);
      ElMessage.warning('Excel , CSV');
      exportCSV();
    });
  } catch (error) {
    console.error('Export failed:', error);
    ElMessage.warning(' , CSV');
    exportCSV();
  }
};

// 
const exportCSV = () => {
  const headers = [
    '排名', '内容', '情感', '情感得分', '热度得分', '综合得分', 
    '象限', '转发', '评论', '点赞', '时间'
  ];
  
  const rows = rankList.value.map(item => [
    item.rank,
    item.text,
    getSentimentLabel(item.sentiment?.polarity),
    item.sentiment?.score,
    item.heat?.score,
    item.tri_score,
    quadrantInfo[item.quadrant]?.label,
    item.interactions?.reposts,
    item.interactions?.comments,
    item.interactions?.likes,
    item.created_at
  ]);
  
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');
  
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  
  ElMessage.success('CSV ');
};

// 工具函数
const getSentimentType = (polarity: string) => {
  const map: Record<string, string> = {
    positive: 'success',
    neutral: 'info',
    negative: 'danger',
  };
  return map[polarity] || 'info';
};

const getSentimentLabel = (polarity: string) => {
  const map: Record<string, string> = {
    positive: '正面',
    neutral: '中性',
    negative: '负面',
  };
  return map[polarity] || '未知';
};

const getRankClass = (rank: number) => {
  if (rank <= 3) return 'top';
  if (rank <= 10) return 'high';
  return 'normal';
};

// 监听图表模式变化
watch(chartMode, () => {
  updateScatterChart();
});

// 初始化散点图
const initChart = () => {
  if (scatterChartRef.value) {
    scatterChart = echarts.init(scatterChartRef.value);
  }
};

// 生命周期
onMounted(() => {
  initChart();
  loadMockResults();
  
  window.addEventListener('resize', () => {
    scatterChart?.resize();
  });
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.tri-dimension-module {
  padding: $spacing-md;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-md;
  padding: $spacing-base;
  background: $bg-white;
  border-radius: $border-radius-base;
  border: 1px solid $border-base;
  box-shadow: $shadow-sm;
}

.config-quick {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  color: $text-regular;
}

.config-card {
  :deep(.el-card__body) {
    padding: 16px;
  }
}

.weight-config {
  .weight-item {
    margin-bottom: 20px;
    
    .weight-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-size: 14px;
    }
  }
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.weight-hint {
  font-size: 11px;
  color: $text-secondary;
  margin-top: 4px;
  font-style: italic;
}

.keyword-filter {
  padding: 8px 12px;
  border-bottom: 1px solid $border-base;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: $text-secondary;
}

.quadrant-card {
  cursor: pointer;
  transition: transform 0.2s;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  .quadrant-stat {
    text-align: center;
    
    .stat-value {
      font-size: $font-size-hero;
      font-weight: $font-weight-bold;
    }
    
    .stat-label {
      font-size: $font-size-extra-small;
      color: $text-secondary;
      margin: $spacing-xxs 0;
    }
    
    .stat-ratio {
      font-size: $font-size-base;
      color: $text-regular;
    }
  }
}

.rank-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rank-list {
  max-height: 600px;
  overflow-y: auto;
}

.rank-item {
  display: flex;
  gap: $spacing-sm;
  padding: $spacing-sm;
  border-bottom: 1px solid $border-base;
  cursor: pointer;
  transition: $transition-fast;
  
  &:hover, &.active {
    background: $bg-hover;
  }
  
  .rank-badge {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: $font-weight-bold;
    color: #fff;
    background: $info-color;
    flex-shrink: 0;
    
    &.top {
      background: linear-gradient(135deg, $warning-color, $danger-color);
    }
    
    &.high {
      background: $primary-color;
    }
  }
  
  .rank-content {
    flex: 1;
    min-width: 0;
    
    .rank-text {
      font-size: $font-size-small;
      color: $text-primary;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-bottom: 6px;
    }
    
    .rank-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .score {
        font-size: $font-size-extra-small;
        color: $text-secondary;
      }
    }
  }
}

.detail-content {
  .highlight {
    font-size: 18px;
    font-weight: $font-weight-bold;
    color: $primary-color;
  }
  
  .weibo-text {
    padding: $spacing-base;
    background: $bg-page;
    border-radius: $border-radius-small;
    line-height: 1.8;
    color: $text-primary;
  }
}

.formula-box {
  padding: $spacing-base;
  background: $bg-page;
  border-radius: $border-radius-small;
  
  code {
    display: block;
    padding: $spacing-xs;
    background: $bg-white;
    border-radius: $border-radius-small;
    font-family: 'Consolas', monospace;
    color: $primary-color;
  }
}

.card-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: $font-weight-semibold;
}

.formula-card {
  border-radius: $border-radius-base;
  border-left: 4px solid $warning-color;

  .formula-display {
    text-align: center;
    padding: $spacing-xs 0;

    .formula-tex {
      font-size: 17px;
      font-weight: $font-weight-semibold;
      font-family: 'Times New Roman', serif;
      color: $text-primary;
    }

    .formula-sub {
      margin-top: 6px;
      font-size: $font-size-small;
      color: $text-secondary;
      font-family: 'Times New Roman', serif;
    }
  }
}

.weight-bar {
  display: flex;
  height: 24px;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 12px;

  .bar-seg {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 600;
    color: #fff;
    transition: width 0.3s ease;
    min-width: 0;
    overflow: hidden;

    &.sentiment { background: $primary-color; }
    &.heat { background: $success-color; }
    &.timeliness { background: $warning-color; }
  }
}

.decay-preview {
  padding: $spacing-sm;
  background: $bg-page;
  border-radius: $border-radius-small;
  margin-top: $spacing-xs;

  .decay-label {
    font-size: $font-size-extra-small;
    color: $text-secondary;
    margin-bottom: 6px;
  }

  .decay-ticks {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;

    .tick {
      font-size: $font-size-tiny;
      padding: 2px 6px;
      background: $bg-white;
      border-radius: $border-radius-small;
      border: 1px solid $border-base;
      color: $text-regular;
      font-family: 'Consolas', monospace;
    }
  }
}

// 论文 3.x: 优化排版 — 让左右两侧"配置/排名"较短的列在用户向下滚动时跟随,
// 避免出现大片空白，参考 DataPreprocessEnhanced 的方案
.main-row {
  align-items: flex-start;
}
.sidebar-col {
  // 论文 3.x: 侧栏在视口内独立滚动，不撑高整页（消除主内容下方留白）
  .sidebar-sticky {
    position: sticky;
    top: $spacing-base;
    max-height: calc(100vh - 110px);
    overflow-y: auto;
    padding-right: 4px;
    &::-webkit-scrollbar { width: 6px; }
    &::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.15);
      border-radius: 3px;
    }
    &::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.25); }
  }
}
</style>
