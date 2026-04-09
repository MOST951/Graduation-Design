<template>
  <div class="word-cloud-panel">
    <!-- 配置面板 -->
    <div v-show="showConfig" class="config-panel">
      <div class="config-header">
        <span>词云配置</span>
        <el-button text size="small" @click="resetConfig">重置</el-button>
      </div>

      <el-form label-position="top" size="small">
        <!-- 词云形状 -->
        <el-form-item label="词云形状">
          <el-select v-model="config.shape" style="width: 100%;">
            <el-option label="圆形" value="circle" />
            <el-option label="心形" value="cardioid" />
            <el-option label="菱形" value="diamond" />
            <el-option label="三角形" value="triangle" />
            <el-option label="五角星" value="star" />
            <el-option label="矩形" value="square" />
          </el-select>
        </el-form-item>

        <!-- 颜色方案 -->
        <el-form-item label="颜色方案">
          <el-select v-model="config.colorScheme" style="width: 100%;">
            <el-option label="彩虹色" value="rainbow" />
            <el-option label="蓝色渐变" value="blue" />
            <el-option label="红色渐变" value="red" />
            <el-option label="绿色渐变" value="green" />
            <el-option label="情感分类" value="sentiment" />
            <el-option label="随机色" value="random" />
          </el-select>
        </el-form-item>

        <!-- 字体设置 -->
        <el-form-item label="字体设置">
          <el-select v-model="config.fontFamily" style="width: 100%; margin-bottom: 8px;">
            <el-option label="微软雅黑" value="Microsoft YaHei" />
            <el-option label="黑体" value="SimHei" />
            <el-option label="宋体" value="SimSun" />
            <el-option label="楷体" value="KaiTi" />
          </el-select>
          <div class="font-size-config">
            <span>字号范围：</span>
            <el-input-number v-model="config.minFontSize" :min="10" :max="30" size="small" />
            <span>-</span>
            <el-input-number v-model="config.maxFontSize" :min="30" :max="100" size="small" />
          </div>
        </el-form-item>

        <!-- 旋转角度 -->
        <el-form-item label="旋转角度范围">
          <el-slider
            v-model="config.rotationRange"
            range
            :min="-90"
            :max="90"
            :marks="rotationMarks"
          />
        </el-form-item>

        <!-- 动画效果 -->
        <el-form-item label="动画效果">
          <div class="animation-config">
            <el-switch v-model="config.enableAnimation" />
            <el-slider
              v-if="config.enableAnimation"
              v-model="config.animationSpeed"
              :min="1"
              :max="10"
              :format-tooltip="(val: number) => `速度: ${val}`"
              style="flex: 1; margin-left: 15px;"
            />
          </div>
        </el-form-item>

        <!-- 词数限制 -->
        <el-form-item label="显示词数">
          <el-slider v-model="config.wordCount" :min="20" :max="200" :step="10" show-input />
        </el-form-item>
      </el-form>
    </div>

    <!-- 词云展示区域 -->
    <div class="cloud-container">
      <!-- 工具栏 -->
      <div class="cloud-toolbar">
        <div class="toolbar-left">
          <el-button-group size="small">
            <el-button :type="viewMode === 'single' ? 'primary' : ''" @click="viewMode = 'single'">
              单视图
            </el-button>
            <el-button :type="viewMode === 'compare' ? 'primary' : ''" @click="viewMode = 'compare'">
              对比视图
            </el-button>
            <el-button :type="viewMode === 'timeline' ? 'primary' : ''" @click="viewMode = 'timeline'">
              时间序列
            </el-button>
          </el-button-group>
        </div>
        <div class="toolbar-right">
          <el-button size="small" @click="showConfig = !showConfig">
            <el-icon><Setting /></el-icon>
            {{ showConfig ? '隐藏配置' : '显示配置' }}
          </el-button>
          <el-button size="small" @click="refreshCloud">
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button size="small" @click="exportCloud">
            <el-icon><Download /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 单视图模式 -->
      <div v-show="viewMode === 'single'" class="single-view">
        <div id="word-cloud-main" ref="cloudRef" class="cloud-chart"></div>
      </div>

      <!-- 对比视图模式 -->
      <div v-show="viewMode === 'compare'" class="compare-view">
        <div class="compare-item">
          <div class="compare-header">
            <el-date-picker v-model="compareDate1" type="date" placeholder="选择日期" size="small" />
          </div>
          <div id="word-cloud-compare1" class="cloud-chart"></div>
        </div>
        <div class="compare-divider"></div>
        <div class="compare-item">
          <div class="compare-header">
            <el-date-picker v-model="compareDate2" type="date" placeholder="选择日期" size="small" />
          </div>
          <div id="word-cloud-compare2" class="cloud-chart"></div>
        </div>
      </div>

      <!-- 时间序列模式 -->
      <div v-show="viewMode === 'timeline'" class="timeline-view">
        <div id="word-cloud-timeline" class="cloud-chart"></div>
        <div class="timeline-controls">
          <el-button :icon="isPlaying ? 'VideoPause' : 'VideoPlay'" circle size="small" @click="togglePlay" />
          <el-slider
            v-model="timelineIndex"
            :min="0"
            :max="timelineData.length - 1"
            :format-tooltip="formatTimelineTooltip"
            style="flex: 1; margin: 0 15px;"
            @change="handleTimelineChange"
          />
          <span class="timeline-label">{{ currentTimeLabel }}</span>
        </div>
      </div>

      <!-- 词语详情悬浮框 -->
      <div v-show="tooltipVisible" class="word-tooltip" :style="tooltipStyle">
        <div class="tooltip-word">{{ tooltipData.word }}</div>
        <div class="tooltip-stats">
          <div class="stat-row">
            <span class="stat-label">权重</span>
            <span class="stat-value">{{ tooltipData.weight }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">出现次数</span>
            <span class="stat-value">{{ tooltipData.count }}次</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">情感倾向</span>
            <el-tag :type="getSentimentType(tooltipData.sentiment)" size="small">
              {{ tooltipData.sentimentLabel }}
            </el-tag>
          </div>
          <div class="stat-row">
            <span class="stat-label">热度趋势</span>
            <span :class="['trend', tooltipData.trend > 0 ? 'up' : 'down']">
              {{ tooltipData.trend > 0 ? '↑' : '↓' }} {{ Math.abs(tooltipData.trend) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div v-show="contextMenuVisible" class="context-menu" :style="contextMenuStyle">
      <div class="menu-item" @click="viewRelatedWeibo">
        <el-icon><Document /></el-icon>
        查看相关微博
      </div>
      <div class="menu-item" @click="addToMonitor">
        <el-icon><Plus /></el-icon>
        设为监控关键词
      </div>
      <div class="menu-item" @click="excludeWord">
        <el-icon><Close /></el-icon>
        排除该词
      </div>
      <div class="menu-item" @click="copyWord">
        <el-icon><CopyDocument /></el-icon>
        复制词语
      </div>
    </div>

    <!-- 相关微博弹窗 -->
    <el-dialog v-model="relatedWeiboVisible" :title="selectedWord + ' 相关微博'" width="700px">
      <el-table :data="relatedWeibos" max-height="400">
        <el-table-column prop="content" label="内容" min-width="300">
          <template #default="{ row }">
            <span v-html="highlightWord(row.content, selectedWord)"></span>
          </template>
        </el-table-column>
        <el-table-column prop="sentiment" label="情感" width="80">
          <template #default="{ row }">
            <el-tag :type="getSentimentType(row.sentiment)" size="small">{{ row.sentimentLabel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="150" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import { Setting, Refresh, Download, Document, Plus, Close, CopyDocument } from '@element-plus/icons-vue';

// Props & Emits
const props = defineProps<{
  words?: { name: string; value: number; sentiment?: string }[];
}>();

const emit = defineEmits<{
  (e: 'word-click', word: string): void;
  (e: 'word-select', word: string): void;
  (e: 'add-monitor', word: string): void;
}>();

// 配置
const showConfig = ref(false);
const config = reactive({
  shape: 'circle',
  colorScheme: 'rainbow',
  fontFamily: 'Microsoft YaHei',
  minFontSize: 14,
  maxFontSize: 60,
  rotationRange: [-45, 45] as [number, number],
  enableAnimation: true,
  animationSpeed: 5,
  wordCount: 100,
});

const rotationMarks = { '-90': '-90°', '0': '0°', '90': '90°' };

// 视图模式
const viewMode = ref<'single' | 'compare' | 'timeline'>('single');
const compareDate1 = ref(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000));
const compareDate2 = ref(new Date());

// 时间序列
const timelineIndex = ref(0);
const isPlaying = ref(false);
const timelineData = ref([
  { date: '12/04', words: generateMockWords() },
  { date: '12/05', words: generateMockWords() },
  { date: '12/06', words: generateMockWords() },
  { date: '12/07', words: generateMockWords() },
  { date: '12/08', words: generateMockWords() },
  { date: '12/09', words: generateMockWords() },
  { date: '12/10', words: generateMockWords() },
]);
let playTimer: number | null = null;

const currentTimeLabel = computed(() => timelineData.value[timelineIndex.value]?.date || '');

// 悬浮提示
const tooltipVisible = ref(false);
const tooltipStyle = ref({ left: '0px', top: '0px' });
const tooltipData = reactive({
  word: '',
  weight: 0,
  count: 0,
  sentiment: 'neutral',
  sentimentLabel: '中性',
  trend: 0,
});

// 右键菜单
const contextMenuVisible = ref(false);
const contextMenuStyle = ref({ left: '0px', top: '0px' });
const selectedWord = ref('');

// 相关微博
const relatedWeiboVisible = ref(false);
const relatedWeibos = ref<any[]>([]);

// 图表实例
const cloudRef = ref<HTMLElement>();
let mainChart: echarts.ECharts | null = null;
let compareChart1: echarts.ECharts | null = null;
let compareChart2: echarts.ECharts | null = null;
let timelineChart: echarts.ECharts | null = null;

// 生成模拟词语数据
function generateMockWords() {
  const baseWords = [
    '热搜', '话题', '微博', '评论', '转发', '点赞', '关注', '粉丝',
    '新闻', '娱乐', '科技', '财经', '体育', '游戏', '美食', '旅游',
    '时尚', '健康', '教育', '汽车', '房产', '职场', '情感', '生活',
    '电影', '音乐', '综艺', '明星', '网红', '直播', '短视频', '社交',
  ];
  
  return baseWords.map(word => ({
    name: word,
    value: Math.floor(Math.random() * 1000 + 100),
    sentiment: ['positive', 'neutral', 'negative'][Math.floor(Math.random() * 3)],
    count: Math.floor(Math.random() * 5000 + 500),
    trend: Math.floor(Math.random() * 40 - 20),
  }));
}

// 获取颜色方案
function getColorFunction() {
  const schemes: Record<string, (word: any) => string> = {
    rainbow: () => `hsl(${Math.random() * 360}, 70%, 50%)`,
    blue: (word: any) => {
      const ratio = word.value / 1000;
      return `hsl(210, ${50 + ratio * 50}%, ${30 + ratio * 30}%)`;
    },
    red: (word: any) => {
      const ratio = word.value / 1000;
      return `hsl(0, ${50 + ratio * 50}%, ${40 + ratio * 30}%)`;
    },
    green: (word: any) => {
      const ratio = word.value / 1000;
      return `hsl(120, ${50 + ratio * 50}%, ${30 + ratio * 30}%)`;
    },
    sentiment: (word: any) => {
      if (word.sentiment === 'positive') return '#67c23a';
      if (word.sentiment === 'negative') return '#f56c6c';
      return '#909399';
    },
    random: () => `hsl(${Math.random() * 360}, ${50 + Math.random() * 30}%, ${40 + Math.random() * 20}%)`,
  };
  return schemes[config.colorScheme] || schemes.rainbow;
}

// 获取形状函数
function getShapeMask() {
  const shapes: Record<string, string | ((theta: number) => number)> = {
    circle: 'circle',
    cardioid: 'cardioid',
    diamond: 'diamond',
    triangle: 'triangle-forward',
    star: 'star',
    square: 'square',
  };
  return shapes[config.shape] || 'circle';
}

// 初始化词云图表
function initWordCloud(domId: string, words: any[]) {
  const dom = document.getElementById(domId);
  if (!dom) return null;

  const chart = echarts.init(dom);
  const colorFn = getColorFunction();

  chart.setOption({
    series: [{
      type: 'wordCloud',
      shape: getShapeMask(),
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [config.minFontSize, config.maxFontSize],
      rotationRange: config.rotationRange,
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: config.enableAnimation,
      textStyle: {
        fontFamily: config.fontFamily,
        fontWeight: 'bold',
        color: (params: any) => colorFn(params.data),
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          textShadowBlur: 10,
          textShadowColor: '#333',
        },
      },
      data: words.slice(0, config.wordCount).map(w => ({
        ...w,
        textStyle: { color: colorFn(w) },
      })),
    }],
  });

  // 绑定事件
  chart.on('mouseover', (params: any) => {
    showTooltip(params);
  });

  chart.on('mouseout', () => {
    tooltipVisible.value = false;
  });

  chart.on('click', (params: any) => {
    selectedWord.value = params.name;
    emit('word-click', params.name);
  });

  chart.getZr().on('contextmenu', (e: any) => {
    e.event.preventDefault();
  });

  chart.on('contextmenu', (params: any) => {
    showContextMenu(params);
  });

  return chart;
}

// 显示悬浮提示
function showTooltip(params: any) {
  const data = params.data;
  tooltipData.word = data.name;
  tooltipData.weight = data.value;
  tooltipData.count = data.count || Math.floor(data.value * 5);
  tooltipData.sentiment = data.sentiment || 'neutral';
  tooltipData.sentimentLabel = { positive: '正面', neutral: '中性', negative: '负面' }[data.sentiment] || '中性';
  tooltipData.trend = data.trend || Math.floor(Math.random() * 40 - 20);

  const event = params.event?.event;
  if (event) {
    tooltipStyle.value = {
      left: event.clientX + 15 + 'px',
      top: event.clientY + 15 + 'px',
    };
  }
  tooltipVisible.value = true;
}

// 显示右键菜单
function showContextMenu(params: any) {
  selectedWord.value = params.name;
  const event = params.event?.event;
  if (event) {
    contextMenuStyle.value = {
      left: event.clientX + 'px',
      top: event.clientY + 'px',
    };
  }
  contextMenuVisible.value = true;
}

// 隐藏右键菜单
function hideContextMenu() {
  contextMenuVisible.value = false;
}

// 右键菜单操作
function viewRelatedWeibo() {
  hideContextMenu();
  relatedWeibos.value = Array.from({ length: 10 }, (_, i) => ({
    id: i + 1,
    content: `这是一条包含"${selectedWord.value}"的微博内容示例，用于展示相关微博功能。`,
    sentiment: ['positive', 'neutral', 'negative'][i % 3],
    sentimentLabel: ['正面', '中性', '负面'][i % 3],
    time: `2025-12-10 ${String(10 + i).padStart(2, '0')}:00`,
  }));
  relatedWeiboVisible.value = true;
}

function addToMonitor() {
  hideContextMenu();
  emit('add-monitor', selectedWord.value);
  ElMessage.success(`已将"${selectedWord.value}"添加到监控关键词`);
}

function excludeWord() {
  hideContextMenu();
  ElMessage.info(`已排除"${selectedWord.value}"`);
  // 重新渲染词云，排除该词
  refreshCloud();
}

function copyWord() {
  hideContextMenu();
  navigator.clipboard.writeText(selectedWord.value);
  ElMessage.success('已复制到剪贴板');
}

// 高亮词语
function highlightWord(content: string, word: string) {
  const regex = new RegExp(`(${word})`, 'gi');
  return content.replace(regex, '<span class="highlight">$1</span>');
}

// 刷新词云
function refreshCloud() {
  const words = props.words || generateMockWords();
  
  if (viewMode.value === 'single') {
    mainChart?.dispose();
    mainChart = initWordCloud('word-cloud-main', words);
  } else if (viewMode.value === 'compare') {
    compareChart1?.dispose();
    compareChart2?.dispose();
    compareChart1 = initWordCloud('word-cloud-compare1', generateMockWords());
    compareChart2 = initWordCloud('word-cloud-compare2', generateMockWords());
  } else {
    timelineChart?.dispose();
    timelineChart = initWordCloud('word-cloud-timeline', timelineData.value[timelineIndex.value].words);
  }
}

// 导出词云
function exportCloud() {
  const chart = mainChart || compareChart1 || timelineChart;
  if (chart) {
    const url = chart.getDataURL({ type: 'png', pixelRatio: 2 });
    const link = document.createElement('a');
    link.href = url;
    link.download = `wordcloud_${new Date().toISOString().slice(0, 10)}.png`;
    link.click();
    ElMessage.success('词云图片已导出');
  }
}

// 重置配置
function resetConfig() {
  config.shape = 'circle';
  config.colorScheme = 'rainbow';
  config.fontFamily = 'Microsoft YaHei';
  config.minFontSize = 14;
  config.maxFontSize = 60;
  config.rotationRange = [-45, 45];
  config.enableAnimation = true;
  config.animationSpeed = 5;
  config.wordCount = 100;
  refreshCloud();
}

// 时间序列控制
function togglePlay() {
  isPlaying.value = !isPlaying.value;
  if (isPlaying.value) {
    playTimer = window.setInterval(() => {
      timelineIndex.value = (timelineIndex.value + 1) % timelineData.value.length;
    }, 2000 / config.animationSpeed);
  } else {
    if (playTimer) {
      clearInterval(playTimer);
      playTimer = null;
    }
  }
}

function handleTimelineChange() {
  if (timelineChart) {
    const words = timelineData.value[timelineIndex.value].words;
    timelineChart.setOption({
      series: [{ data: words.slice(0, config.wordCount) }],
    });
  }
}

function formatTimelineTooltip(index: number) {
  return timelineData.value[index]?.date || '';
}

function getSentimentType(sentiment: string) {
  const map: Record<string, string> = { positive: 'success', neutral: 'info', negative: 'danger' };
  return map[sentiment] || 'info';
}

// 监听配置变化
watch(config, () => {
  refreshCloud();
}, { deep: true });

// 监听视图模式变化
watch(viewMode, () => {
  nextTick(() => {
    refreshCloud();
  });
});

// 监听外部词语数据变化
watch(() => props.words, () => {
  refreshCloud();
});

// 点击其他区域关闭菜单
function handleDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest('.context-menu')) {
    hideContextMenu();
  }
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    refreshCloud();
  });
  document.addEventListener('click', handleDocumentClick);
  window.addEventListener('resize', () => {
    mainChart?.resize();
    compareChart1?.resize();
    compareChart2?.resize();
    timelineChart?.resize();
  });
});

onUnmounted(() => {
  mainChart?.dispose();
  compareChart1?.dispose();
  compareChart2?.dispose();
  timelineChart?.dispose();
  if (playTimer) clearInterval(playTimer);
  document.removeEventListener('click', handleDocumentClick);
});
</script>

<style scoped>
.word-cloud-panel {
  display: flex;
  gap: 15px;
  height: 100%;
}

/* 配置面板 */
.config-panel {
  width: 280px;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow-y: auto;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
  font-weight: bold;
}

.font-size-config {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #606266;
}

.animation-config {
  display: flex;
  align-items: center;
}

/* 词云容器 */
.cloud-container {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  position: relative;
}

.cloud-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.toolbar-left, .toolbar-right {
  display: flex;
  gap: 10px;
}

.cloud-chart {
  flex: 1;
  min-height: 400px;
}

/* 单视图 */
.single-view {
  flex: 1;
  display: flex;
}

/* 对比视图 */
.compare-view {
  flex: 1;
  display: flex;
  gap: 10px;
}

.compare-item {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.compare-header {
  margin-bottom: 10px;
  text-align: center;
}

.compare-divider {
  width: 2px;
  background: #ebeef5;
}

/* 时间序列视图 */
.timeline-view {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.timeline-controls {
  display: flex;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-top: 10px;
}

.timeline-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  min-width: 60px;
  text-align: right;
}

/* 悬浮提示 */
.word-tooltip {
  position: fixed;
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 180px;
}

.tooltip-word {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.trend.up { color: #67c23a; }
.trend.down { color: #f56c6c; }

/* 右键菜单 */
.context-menu {
  position: fixed;
  background: #fff;
  border-radius: 8px;
  padding: 8px 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1001;
  min-width: 160px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: background 0.2s;
}

.menu-item:hover {
  background: #f5f7fa;
  color: #409eff;
}

/* 高亮词语 */
:deep(.highlight) {
  color: #409eff;
  font-weight: bold;
  background: #ecf5ff;
  padding: 0 2px;
  border-radius: 2px;
}
</style>
