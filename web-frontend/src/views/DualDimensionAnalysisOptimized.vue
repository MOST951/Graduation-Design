<template>
  <div class="dual-dimension-analysis">
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <!-- Header -->
    <div class="analysis-header">
      <div class="header-left">
        <h1 class="page-title">Dual Dimension Ranking</h1>
        <div class="batch-info" v-if="currentBatchId">
          <el-tag type="info" size="large">
            <el-icon><Collection /></el-icon>
            Batch: {{ currentBatchId }}
          </el-tag>
        </div>
      </div>
      
      <div class="header-right">
        <div class="data-status">
          <el-tag 
            :type="getDataStatusType()" 
            size="large"
            :aria-label="`Data status: ${getDataStatusText()}`"
          >
            <el-icon v-if="isLoading" class="rotating"><Loading /></el-icon>
            {{ getDataStatusText() }}
          </el-tag>
        </div>
      </div>
    </div>

    <div id="main-content" class="main-content">
      <!-- Empty State -->
      <div v-if="!hasData && !isLoading" class="empty-state">
        <div class="empty-content">
          <el-icon class="empty-icon"><DataLine /></el-icon>
          <h2 class="empty-title">No Data Available</h2>
          <p class="empty-description">
            Please collect and analyze data first to generate dual dimension rankings
          </p>
          <el-button 
            type="primary" 
            size="large"
            :icon="Guide"
            @click="navigateToCollection"
            class="action-button"
          >
            Go to Collection & Analysis
          </el-button>
        </div>
      </div>

      <!-- Main Content -->
      <div v-else class="analysis-content">
        <el-row :gutter="20">
          <!-- Left Panel: Weight Configuration -->
          <el-col :span="8">
            <el-card shadow="hover" class="weight-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Setting /></el-icon>
                  <span>Weight Configuration</span>
                  <el-button
                    text
                    size="small"
                    @click="recalculateAll"
                    :loading="isRecalculating"
                    :aria-label="'Recalculate all rankings'"
                  >
                    <el-icon><Refresh /></el-icon>
                    Recalculate
                  </el-button>
                </div>
              </template>
              
              <!-- Weight Sliders -->
              <div class="weight-sliders">
                <div class="slider-item">
                  <div class="slider-header">
                    <span class="slider-label">Sentiment Weight (w<sub>1</sub>)</span>
                    <span class="slider-value">{{ weights.sentiment.toFixed(2) }}</span>
                  </div>
                  <el-slider
                    v-model="weights.sentiment"
                    :min="0"
                    :max="1"
                    :step="0.01"
                    :format-tooltip="(val) => val.toFixed(2)"
                    @change="handleWeightChange('sentiment')"
                    class="weight-slider"
                    :aria-label="'Adjust sentiment weight'"
                  />
                </div>
                
                <div class="slider-item">
                  <div class="slider-header">
                    <span class="slider-label">Popularity Weight (w<sub>2</sub>)</span>
                    <span class="slider-value">{{ weights.popularity.toFixed(2) }}</span>
                  </div>
                  <el-slider
                    v-model="weights.popularity"
                    :min="0"
                    :max="1"
                    :step="0.01"
                    :format-tooltip="(val) => val.toFixed(2)"
                    @change="handleWeightChange('popularity')"
                    class="weight-slider"
                    :aria-label="'Adjust popularity weight'"
                  />
                </div>
                
                <div class="slider-item">
                  <div class="slider-header">
                    <span class="slider-label">Timeliness Weight (w<sub>3</sub>)</span>
                    <span class="slider-value">{{ weights.timeliness.toFixed(2) }}</span>
                  </div>
                  <el-slider
                    v-model="weights.timeliness"
                    :min="0"
                    :max="1"
                    :step="0.01"
                    :format-tooltip="(val) => val.toFixed(2)"
                    @change="handleWeightChange('timeliness')"
                    class="weight-slider"
                    :aria-label="'Adjust timeliness weight'"
                  />
                </div>
              </div>
              
              <!-- Weight Formula Card -->
              <WeightFormulaCard
                :weights="weights"
                @update:weights="handleWeightsUpdate"
                @reset="handleResetWeights"
                @equalize="handleEqualizeWeights"
                @optimize="handleOptimizeWeights"
              />
            </el-card>
            
            <!-- Historical Comparison -->
            <el-card shadow="hover" class="history-card" v-if="historicalBatches.length > 0">
              <template #header>
                <div class="card-header">
                  <el-icon><Clock /></el-icon>
                  <span>Historical Comparison</span>
                </div>
              </template>
              
              <div class="history-content">
                <el-select
                  v-model="selectedHistoricalBatch"
                  placeholder="Select batch for comparison"
                  style="width: 100%"
                  @change="handleHistoricalComparison"
                  :aria-label="'Select historical batch for comparison'"
                >
                  <el-option
                    v-for="batch in historicalBatches"
                    :key="batch.id"
                    :label="`${batch.id} (${batch.date})`"
                    :value="batch.id"
                  />
                </el-select>
                
                <div v-if="historicalComparison" class="comparison-results">
                  <div class="comparison-item">
                    <span class="comparison-label">Ranking Correlation:</span>
                    <span class="comparison-value">{{ historicalComparison.correlation.toFixed(3) }}</span>
                  </div>
                  <div class="comparison-item">
                    <span class="comparison-label">Top 10 Overlap:</span>
                    <span class="comparison-value">{{ historicalComparison.overlap }}/10</span>
                  </div>
                  <div class="comparison-item">
                    <span class="comparison-label">Avg Score Change:</span>
                    <span class="comparison-value">{{ historicalComparison.avgChange.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <!-- Middle Panel: Results Table -->
          <el-col :span="10">
            <el-card shadow="hover" class="results-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Table /></el-icon>
                  <span>Ranking Results</span>
                  <div class="results-controls">
                    <el-select
                      v-model="topN"
                      size="small"
                      style="width: 100px"
                      @change="handleTopNChange"
                      :aria-label="'Select top N results'"
                    >
                      <el-option label="Top 10" :value="10" />
                      <el-option label="Top 20" :value="20" />
                      <el-option label="Top 50" :value="50" />
                      <el-option label="Top 100" :value="100" />
                    </el-select>
                    
                    <el-button
                      text
                      size="small"
                      @click="refreshResults"
                      :loading="isRefreshing"
                      :aria-label="'Refresh results'"
                    >
                      <el-icon><Refresh /></el-icon>
                    </el-button>
                    
                    <el-button
                      text
                      size="small"
                      @click="exportResults"
                      :aria-label="'Export results'"
                    >
                      <el-icon><Download /></el-icon>
                    </el-button>
                  </div>
                </div>
              </template>
              
              <!-- Results Table -->
              <el-table
                :data="paginatedResults"
                height="500"
                size="small"
                :default-sort="{ prop: 'compositeScore', order: 'descending' }"
                @sort-change="handleTableSort"
                :aria-label="'Dual dimension ranking results table'"
              >
                <el-table-column type="index" label="Rank" width="60" />
                
                <el-table-column prop="content" label="Weibo Content" min-width="200" show-overflow-tooltip>
                  <template #default="{ row }">
                    <div class="content-cell">
                      <div class="content-text">{{ row.content }}</div>
                      <div class="content-meta">
                        <span class="meta-item">
                          <el-icon><User /></el-icon>
                          {{ row.author }}
                        </span>
                        <span class="meta-item">
                          <el-icon><Clock /></el-icon>
                          {{ formatTime(row.publishTime) }}
                        </span>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                
                <el-table-column prop="sentimentScore" label="Sentiment Score" width="120" sortable>
                  <template #default="{ row }">
                    <ScoreTooltip
                      :title="'Sentiment Score'"
                      :formula="'N(S) = (|S| + 1) / 2'"
                      :steps="sentimentSteps"
                      :range="{ min: 0, max: 1 }"
                      :example="'S = 0.8, N(S) = (0.8 + 1) / 2 = 0.9'"
                    >
                      <div class="score-cell sentiment">
                        <span class="score-value">{{ row.sentimentScore.toFixed(3) }}</span>
                        <div class="score-bar">
                          <div 
                            class="score-fill" 
                            :style="{ width: `${row.sentimentScore * 100}%` }"
                          ></div>
                        </div>
                      </div>
                    </ScoreTooltip>
                  </template>
                </el-table-column>
                
                <el-table-column prop="popularityScore" label="Popularity Score" width="120" sortable>
                  <template #default="{ row }">
                    <ScoreTooltip
                      :title="'Popularity Score'"
                      :formula="'H_norm = H_raw / max(H_raw)'"
                      :steps="popularitySteps"
                      :range="{ min: 0, max: 1 }"
                      :example="'H_raw = log10(1 + 100*1 + 2*50 + 20) = 2.0'"
                    >
                      <div class="score-cell popularity">
                        <span class="score-value">{{ row.popularityScore.toFixed(3) }}</span>
                        <div class="score-bar">
                          <div 
                            class="score-fill" 
                            :style="{ width: `${row.popularityScore * 100}%` }"
                          ></div>
                        </div>
                      </div>
                    </ScoreTooltip>
                  </template>
                </el-table-column>
                
                <el-table-column prop="timelinessScore" label="Timeliness" width="100" sortable>
                  <template #default="{ row }">
                    <ScoreTooltip
                      :title="'Timeliness Score'"
                      :formula="'gamma(t) = 2^(-Delta_t / H), H = 12 hours'"
                      :steps="timelinessSteps"
                      :range="{ min: 0, max: 1 }"
                      :example="'Delta_t = 6h, gamma(t) = 2^(-6/12) = 0.707'"
                    >
                      <div class="score-cell timeliness">
                        <span class="score-value">{{ row.timelinessScore.toFixed(3) }}</span>
                        <div class="score-bar">
                          <div 
                            class="score-fill" 
                            :style="{ width: `${row.timelinessScore * 100}%` }"
                          ></div>
                        </div>
                      </div>
                    </ScoreTooltip>
                  </template>
                </el-table-column>
                
                <el-table-column prop="compositeScore" label="Composite Score" width="120" sortable>
                  <template #default="{ row }">
                    <ScoreTooltip
                      :title="'Composite Score'"
                      :formula="'Score = w1*N(S) + w2*H_norm + w3*gamma(t)'"
                      :steps="compositeSteps"
                      :range="{ min: 0, max: 1 }"
                      :example="'Score = 0.4*0.9 + 0.4*0.8 + 0.2*0.7 = 0.82'"
                    >
                      <div class="score-cell composite">
                        <span class="score-value composite">{{ row.compositeScore.toFixed(3) }}</span>
                        <div class="score-bar">
                          <div 
                            class="score-fill composite" 
                            :style="{ width: `${row.compositeScore * 100}%` }"
                          ></div>
                        </div>
                      </div>
                    </ScoreTooltip>
                  </template>
                </el-table-column>
                
                <el-table-column label="Actions" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      text
                      size="small"
                      @click="viewDetails(row)"
                      :aria-label="'View ranking details'"
                    >
                      <el-icon><View /></el-icon>
                    </el-button>
                    <el-button
                      text
                      size="small"
                      @click="trackRanking(row)"
                      :aria-label="'Track ranking changes'"
                    >
                      <el-icon><Star /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              
              <!-- Table Pagination -->
              <div class="table-pagination">
                <el-pagination
                  v-model:current-page="pagination.page"
                  v-model:page-size="pagination.size"
                  :page-sizes="[10, 20, 50]"
                  :total="totalResults"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="handlePageSizeChange"
                  @current-change="handlePageChange"
                  :aria-label="'Results table pagination'"
                />
              </div>
            </el-card>
          </el-col>
          
          <!-- Right Panel: Visualization -->
          <el-col :span="6">
            <el-card shadow="hover" class="scatter-card">
              <template #header>
                <div class="card-header">
                  <el-icon><ScatterChart /></el-icon>
                  <span>Popularity Distribution</span>
                </div>
              </template>
              
              <div class="scatter-content">
                <div ref="scatterChartRef" class="scatter-chart"></div>
                
                <div class="scatter-legend">
                  <div class="legend-item">
                    <div class="legend-dot high"></div>
                    <span class="legend-label">High Engagement</span>
                  </div>
                  <div class="legend-item">
                    <div class="legend-dot medium"></div>
                    <span class="legend-label">Medium Engagement</span>
                  </div>
                  <div class="legend-item">
                    <div class="legend-dot low"></div>
                    <span class="legend-label">Low Engagement</span>
                  </div>
                </div>
              </div>
            </el-card>
            
            <!-- Statistics Summary -->
            <el-card shadow="hover" class="stats-card">
              <template #header>
                <div class="card-header">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>Statistics Summary</span>
                </div>
              </template>
              
              <div class="stats-content">
                <div class="stat-item">
                  <div class="stat-icon sentiment">
                    <el-icon><Heart /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ stats.avgSentiment.toFixed(3) }}</div>
                    <div class="stat-label">Avg Sentiment</div>
                  </div>
                </div>
                
                <div class="stat-item">
                  <div class="stat-icon popularity">
                    <el-icon><TrendCharts /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ stats.avgPopularity.toFixed(3) }}</div>
                    <div class="stat-label">Avg Popularity</div>
                  </div>
                </div>
                
                <div class="stat-item">
                  <div class="stat-icon timeliness">
                    <el-icon><Clock /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ stats.avgTimeliness.toFixed(3) }}</div>
                    <div class="stat-label">Avg Timeliness</div>
                  </div>
                </div>
                
                <div class="stat-item">
                  <div class="stat-icon composite">
                    <el-icon><Trophy /></el-icon>
                  </div>
                  <div class="stat-content">
                    <div class="stat-value">{{ stats.avgComposite.toFixed(3) }}</div>
                    <div class="stat-label">Avg Composite</div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  Setting, Collection, Clock, Table, Refresh, Download, View, Star,
  ScatterChart, DataAnalysis, Heart, TrendCharts, Trophy, DataLine,
  User, Loading, Guide
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import WeightFormulaCard from '@/components/common/WeightFormulaCard.vue'
import ScoreTooltip from '@/components/common/ScoreTooltip.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface Weights {
  sentiment: number
  popularity: number
  timeliness: number
}

interface RankingItem {
  id: string
  rank: number
  content: string
  author: string
  publishTime: Date
  sentimentScore: number
  popularityScore: number
  timelinessScore: number
  compositeScore: number
  interactions: {
    reposts: number
    comments: number
    likes: number
  }
}

interface HistoricalBatch {
  id: string
  date: string
  rankings: RankingItem[]
}

interface HistoricalComparison {
  correlation: number
  overlap: number
  avgChange: number
}

interface Statistics {
  avgSentiment: number
  avgPopularity: number
  avgTimeliness: number
  avgComposite: number
}

// Router
const router = useRouter()

// Reactive data
const isLoading = ref(false)
const isRecalculating = ref(false)
const isRefreshing = ref(false)
const hasData = ref(false)
const currentBatchId = ref('')

const weights = ref<Weights>({
  sentiment: 0.4,
  popularity: 0.4,
  timeliness: 0.2
})

const rankings = ref<RankingItem[]>([])
const topN = ref(20)
const pagination = ref({
  page: 1,
  size: 20
})

const historicalBatches = ref<HistoricalBatch[]>([])
const selectedHistoricalBatch = ref('')
const historicalComparison = ref<HistoricalComparison | null>(null)

const stats = ref<Statistics>({
  avgSentiment: 0,
  avgPopularity: 0,
  avgTimeliness: 0,
  avgComposite: 0
})

// Refs
const scatterChartRef = ref()

// Debounce timer
let recalculateTimer: NodeJS.Timeout | null = null

// Constants
const sentimentSteps = [
  { text: 'Extract raw sentiment score S from analysis' },
  { text: 'Apply normalization: N(S) = (|S| + 1) / 2' },
  { text: 'Result ranges from 0 (negative) to 1 (positive)' }
]

const popularitySteps = [
  { text: 'Calculate raw popularity: H_raw = log10(1 + R + 2C + L)' },
  { text: 'Normalize: H_norm = H_raw / max(H_raw)' },
  { text: 'R=reposts, C=comments, L=likes' }
]

const timelinessSteps = [
  { text: 'Calculate time decay: gamma(t) = 2^(-Delta_t / H)' },
  { text: 'H = 12 hours half-life period' },
  { text: 'Newer posts get higher timeliness scores' }
]

const compositeSteps = [
  { text: 'Apply weight formula: Score = w1*N(S) + w2*H_norm + w3*gamma(t)' },
  { text: 'Weights sum to 1.0 (w1 + w2 + w3 = 1)' },
  { text: 'Final composite score determines ranking' }
]

// Computed properties
const getDataStatusText = () => {
  if (isLoading.value) return 'Loading...'
  if (!hasData.value) return 'No Data'
  return `${rankings.value.length} Items`
}

const getDataStatusType = () => {
  if (isLoading.value) return 'warning'
  if (!hasData.value) return 'info'
  return 'success'
}

const totalResults = computed(() => {
  return Math.min(rankings.value.length, topN.value)
})

const paginatedResults = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.size
  const end = start + pagination.value.size
  return rankings.value.slice(start, end)
})

// Methods
const navigateToCollection = () => {
  router.push('/data-collection')
}

const handleWeightChange = (type: keyof Weights) => {
  // Debounce recalculation
  if (recalculateTimer) {
    clearTimeout(recalculateTimer)
  }
  
  recalculateTimer = setTimeout(() => {
    recalculateRankings()
  }, 500) // 500ms debounce
}

const handleWeightsUpdate = (newWeights: Weights) => {
  weights.value = newWeights
  recalculateRankings()
}

const handleResetWeights = () => {
  weights.value = {
    sentiment: 0.4,
    popularity: 0.4,
    timeliness: 0.2
  }
  recalculateRankings()
}

const handleEqualizeWeights = () => {
  weights.value = {
    sentiment: 0.33,
    popularity: 0.33,
    timeliness: 0.34
  }
  recalculateRankings()
}

const handleOptimizeWeights = () => {
  weights.value = {
    sentiment: 0.45,
    popularity: 0.35,
    timeliness: 0.20
  }
  recalculateRankings()
}

const recalculateRankings = async () => {
  isRecalculating.value = true
  
  try {
    await withErrorHandling(
      async () => {
        // Recalculate composite scores
        rankings.value.forEach(item => {
          item.compositeScore = calculateCompositeScore(item)
        })
        
        // Re-sort rankings
        rankings.value.sort((a, b) => b.compositeScore - a.compositeScore)
        
        // Update ranks
        rankings.value.forEach((item, index) => {
          item.rank = index + 1
        })
        
        // Update statistics
        updateStatistics()
        
        // Update scatter chart
        updateScatterChart()
        
        ElMessage.success('Rankings recalculated successfully')
      },
      'Ranking Recalculation',
      { showLoading: false }
    )
  } finally {
    isRecalculating.value = false
  }
}

const calculateCompositeScore = (item: RankingItem): number => {
  return (
    weights.value.sentiment * item.sentimentScore +
    weights.value.popularity * item.popularityScore +
    weights.value.timeliness * item.timelinessScore
  )
}

const calculateSentimentScore = (rawScore: number): number => {
  return (Math.abs(rawScore) + 1) / 2
}

const calculatePopularityScore = (interactions: { reposts: number; comments: number; likes: number }): number => {
  const rawScore = Math.log10(1 + interactions.reposts + 2 * interactions.comments + interactions.likes)
  // Normalize (simplified - in real implementation would use max across dataset)
  const maxRawScore = 5.0
  return Math.min(rawScore / maxRawScore, 1)
}

const calculateTimelinessScore = (publishTime: Date): number => {
  const now = Date.now()
  const deltaHours = (now - publishTime.getTime()) / (1000 * 60 * 60)
  const halfLife = 12 // hours
  return Math.pow(2, -deltaHours / halfLife)
}

const updateStatistics = () => {
  if (rankings.value.length === 0) return
  
  const topItems = rankings.value.slice(0, topN.value)
  
  stats.value = {
    avgSentiment: topItems.reduce((sum, item) => sum + item.sentimentScore, 0) / topItems.length,
    avgPopularity: topItems.reduce((sum, item) => sum + item.popularityScore, 0) / topItems.length,
    avgTimeliness: topItems.reduce((sum, item) => sum + item.timelinessScore, 0) / topItems.length,
    avgComposite: topItems.reduce((sum, item) => sum + item.compositeScore, 0) / topItems.length
  }
}

const updateScatterChart = () => {
  if (!scatterChartRef.value || rankings.value.length === 0) return
  
  const chart = echarts.init(scatterChartRef.value)
  
  const data = rankings.value.slice(0, topN.value).map(item => [
    item.popularityScore,
    item.sentimentScore,
    item.timelinessScore * 20, // Scale for bubble size
    item.content.substring(0, 20) + '...'
  ])
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const [x, y, z, content] = params.data
        return `
          <div style="padding: 8px;">
            <div style="font-weight: bold; margin-bottom: 4px;">${content}</div>
            <div>Popularity: ${x.toFixed(3)}</div>
            <div>Sentiment: ${y.toFixed(3)}</div>
            <div>Timeliness: ${(z / 20).toFixed(3)}</div>
          </div>
        `
      }
    },
    xAxis: {
      type: 'value',
      name: 'Popularity Score',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: (value: number) => value.toFixed(2)
      }
    },
    yAxis: {
      type: 'value',
      name: 'Sentiment Score',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: (value: number) => value.toFixed(2)
      }
    },
    visualMap: {
      show: false,
      dimension: 2,
      min: 0,
      max: 20,
      inRange: {
        colorLightness: [0.5, 0.8]
      }
    },
    series: [{
      type: 'scatter',
      data: data,
      symbolSize: (data: any) => data[2],
      itemStyle: {
        color: (params: any) => {
          const [, , ,] = params.data
          if (params.data[2] > 15) return '#ff7d00' // High engagement
          if (params.data[2] > 10) return '#165dff' // Medium engagement
          return '#86909c' // Low engagement
        }
      }
    }]
  }
  
  chart.setOption(option)
  
  // Handle resize
  const handleResize = () => chart.resize()
  window.addEventListener('resize', handleResize)
}

const handleTopNChange = () => {
  pagination.value.page = 1
  updateStatistics()
  updateScatterChart()
}

const handleTableSort = ({ prop, order }: { prop: string; order: string }) => {
  rankings.value.sort((a, b) => {
    const aValue = a[prop as keyof RankingItem]
    const bValue = b[prop as keyof RankingItem]
    
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return order === 'ascending' ? aValue - bValue : bValue - aValue
    }
    
    return 0
  })
  
  // Update ranks
  rankings.value.forEach((item, index) => {
    item.rank = index + 1
  })
}

const handlePageSizeChange = (size: number) => {
  pagination.value.size = size
  pagination.value.page = 1
}

const handlePageChange = (page: number) => {
  pagination.value.page = page
}

const refreshResults = async () => {
  isRefreshing.value = true
  
  try {
    await withErrorHandling(
      async () => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success('Results refreshed')
      },
      'Refresh Results',
      { showLoading: false }
    )
  } finally {
    isRefreshing.value = false
  }
}

const exportResults = () => {
  const data = paginatedResults.value.map(item => ({
    Rank: item.rank,
    Content: item.content,
    Author: item.author,
    'Sentiment Score': item.sentimentScore.toFixed(3),
    'Popularity Score': item.popularityScore.toFixed(3),
    'Timeliness Score': item.timelinessScore.toFixed(3),
    'Composite Score': item.compositeScore.toFixed(3)
  }))
  
  const csv = [
    Object.keys(data[0]).join(','),
    ...data.map(row => Object.values(row).join(','))
  ].join('\n')
  
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `dual_dimension_ranking_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  ElMessage.success('Results exported successfully')
}

const viewDetails = (item: RankingItem) => {
  ElMessage.info(`Viewing details for rank ${item.rank}`)
  // Implement detail view logic
}

const trackRanking = (item: RankingItem) => {
  ElMessage.info(`Tracking ranking changes for: ${item.content.substring(0, 20)}...`)
  // Implement ranking tracking logic
}

const handleHistoricalComparison = (batchId: string) => {
  const batch = historicalBatches.value.find(b => b.id === batchId)
  if (!batch) return
  
  // Calculate comparison metrics
  const currentTop10 = rankings.value.slice(0, 10).map(item => item.id)
  const historicalTop10 = batch.rankings.slice(0, 10).map(item => item.id)
  
  const overlap = currentTop10.filter(id => historicalTop10.includes(id)).length
  
  // Simplified correlation calculation
  const correlation = 0.85 // Placeholder
  
  historicalComparison.value = {
    correlation,
    overlap,
    avgChange: 0.12 // Placeholder
  }
  
  ElMessage.success(`Comparison loaded for batch ${batchId}`)
}

const formatTime = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  
  if (hours < 1) return 'Just now'
  if (hours < 24) return `${hours}h ago`
  if (hours < 24 * 7) return `${Math.floor(hours / 24)}d ago`
  return `${Math.floor(hours / (24 * 7))}w ago`
}

// Load mock data
const loadMockData = async () => {
  isLoading.value = true
  
  try {
    await withErrorHandling(
      async () => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // Generate mock rankings
        const mockRankings: RankingItem[] = []
        
        for (let i = 0; i < 100; i++) {
          const interactions = {
            reposts: Math.floor(Math.random() * 1000),
            comments: Math.floor(Math.random() * 500),
            likes: Math.floor(Math.random() * 2000)
          }
          
          const publishTime = new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000)
          
          mockRankings.push({
            id: `weibo_${i + 1}`,
            rank: i + 1,
            content: `This is sample weibo content #${i + 1} with some interesting text that demonstrates the dual dimension ranking algorithm in action.`,
            author: `user_${i + 1}`,
            publishTime,
            sentimentScore: calculateSentimentScore(Math.random() * 2 - 1),
            popularityScore: calculatePopularityScore(interactions),
            timelinessScore: calculateTimelinessScore(publishTime),
            compositeScore: 0, // Will be calculated
            interactions
          })
        }
        
        // Calculate initial composite scores
        mockRankings.forEach(item => {
          item.compositeScore = calculateCompositeScore(item)
        })
        
        // Sort by composite score
        mockRankings.sort((a, b) => b.compositeScore - a.compositeScore)
        
        // Update ranks
        mockRankings.forEach((item, index) => {
          item.rank = index + 1
        })
        
        rankings.value = mockRankings
        hasData.value = true
        currentBatchId.value = `batch_${Date.now().toISOString().split('T')[0]}`
        
        // Generate historical batches
        historicalBatches.value = [
          {
            id: 'batch_2024-01-15',
            date: '2024-01-15',
            rankings: mockRankings.slice(0, 50).map(item => ({
              ...item,
              compositeScore: item.compositeScore + (Math.random() - 0.5) * 0.2
            }))
          },
          {
            id: 'batch_2024-01-14',
            date: '2024-01-14',
            rankings: mockRankings.slice(0, 50).map(item => ({
              ...item,
              compositeScore: item.compositeScore + (Math.random() - 0.5) * 0.3
            }))
          }
        ]
        
        // Update statistics and chart
        updateStatistics()
        
        await nextTick()
        updateScatterChart()
      },
      'Load Ranking Data',
      { showLoading: false }
    )
  } finally {
    isLoading.value = false
  }
}

// Watch for changes
watch(topN, () => {
  pagination.value.page = 1
})

// Lifecycle
onMounted(async () => {
  await loadMockData()
  
  // Set up keyboard navigation
  AccessibilityHelper.setupKeyboardNavigation(document.body, {
    orientation: 'vertical',
    loop: true
  })
})
</script>

<style scoped>
.dual-dimension-analysis {
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  min-height: 100vh;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-extra-large);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.batch-info {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.data-status {
  display: flex;
  align-items: center;
}

.main-content {
  margin-top: var(--spacing-lg);
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.empty-content {
  text-align: center;
  max-width: 400px;
}

.empty-icon {
  font-size: 64px;
  color: var(--color-text-placeholder);
  margin-bottom: var(--spacing-lg);
}

.empty-title {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-description {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
  line-height: 1.6;
}

.action-button {
  padding: var(--spacing-md) var(--spacing-xl);
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-semibold);
}

.weight-card,
.history-card,
.results-card,
.scatter-card,
.stats-card {
  margin-bottom: var(--spacing-lg);
}

.weight-sliders {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.slider-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slider-label {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.slider-value {
  font-family: 'Courier New', monospace;
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary);
  min-width: 50px;
  text-align: right;
}

.weight-slider {
  margin: var(--spacing-sm) 0;
}

.history-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.comparison-results {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

.comparison-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-small);
}

.comparison-label {
  color: var(--color-text-secondary);
}

.comparison-value {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.results-controls {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.content-cell {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.content-text {
  line-height: 1.4;
  word-break: break-word;
}

.content-meta {
  display: flex;
  gap: var(--spacing-sm);
  font-size: var(--font-size-tiny);
  color: var(--color-text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xxs);
}

.score-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.score-value {
  font-family: 'Courier New', monospace;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-small);
  min-width: 45px;
  text-align: right;
}

.score-value.composite {
  color: var(--color-primary);
}

.score-bar {
  width: 40px;
  height: 4px;
  background: var(--color-border-light);
  border-radius: var(--border-radius-round);
  overflow: hidden;
}

.score-fill {
  height: 100%;
  background: var(--color-success);
  transition: var(--transition-fast);
}

.score-fill.composite {
  background: var(--color-primary);
}

.table-pagination {
  margin-top: var(--spacing-md);
  display: flex;
  justify-content: center;
}

.scatter-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.scatter-chart {
  height: 300px;
}

.scatter-legend {
  display: flex;
  justify-content: center;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-small);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--border-radius-circle);
}

.legend-dot.high {
  background: #ff7d00;
}

.legend-dot.medium {
  background: #165dff;
}

.legend-dot.low {
  background: #86909c;
}

.stats-content {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--border-radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.sentiment {
  background: var(--color-success);
}

.stat-icon.popularity {
  background: var(--color-primary);
}

.stat-icon.timeliness {
  background: var(--color-warning);
}

.stat-icon.composite {
  background: var(--color-info);
}

.stat-content {
  flex: 1;
}

.stat-content .stat-value {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.stat-content .stat-label {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
}

/* Animations */
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.rotating {
  animation: rotate 2s linear infinite;
}

/* Responsive design */
@media (max-width: 1280px) {
  .analysis-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-left,
  .header-right {
    justify-content: center;
  }
  
  .stats-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dual-dimension-analysis {
    padding: var(--spacing-md);
  }
  
  .analysis-header {
    padding: var(--spacing-md);
  }
  
  .page-title {
    font-size: var(--font-size-large);
  }
  
  .results-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .content-meta {
    flex-direction: column;
    gap: var(--spacing-xxs);
  }
  
  .scatter-legend {
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-sm);
  }
  
  .comparison-results {
    gap: var(--spacing-xs);
  }
  
  .comparison-item {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-xxs);
  }
}

/* Focus styles for accessibility */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .weight-card,
  .history-card,
  .results-card,
  .scatter-card,
  .stats-card {
    border-width: 2px;
  }
}
</style>
