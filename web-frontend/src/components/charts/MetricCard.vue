<template>
  <div class="metric-card" :style="{ '--accent-color': color }">
    <div class="metric-header">
      <el-icon v-if="icon" class="metric-icon" :size="24">
        <component :is="icon" />
      </el-icon>
      <span class="metric-title">{{ title }}</span>
    </div>
    <div class="metric-value">
      {{ value }}<span v-if="unit" class="metric-unit">{{ unit }}</span>
    </div>
    <div v-if="trend !== undefined" class="metric-trend" :class="trendClass">
      <el-icon :size="14">
        <component :is="trend >= 0 ? 'Top' : 'Bottom'" />
      </el-icon>
      <span>{{ Math.abs(trend) }}%</span>
      <span v-if="trendLabel" class="trend-label">{{ trendLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  title?: string;
  value?: string | number;
  unit?: string;
  trend?: number;
  trendLabel?: string;
  icon?: string;
  color?: string;
}>();

const trendClass = computed(() => ({
  positive: (props.trend || 0) >= 0,
  negative: (props.trend || 0) < 0,
}));
</script>

<style scoped>
.metric-card {
  width: 100%;
  height: 100%;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
  border-radius: 8px;
  border-left: 4px solid var(--accent-color, #409EFF);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.metric-icon {
  color: var(--accent-color, #409EFF);
}

.metric-title {
  font-size: 14px;
  color: #909399;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.metric-unit {
  font-size: 14px;
  font-weight: normal;
  color: #909399;
  margin-left: 4px;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 13px;
}

.metric-trend.positive {
  color: #67C23A;
}

.metric-trend.negative {
  color: #F56C6C;
}

.trend-label {
  color: #909399;
  margin-left: 4px;
}
</style>
