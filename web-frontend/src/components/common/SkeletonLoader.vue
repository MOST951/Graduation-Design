<template>
  <div class="skeleton-loader" :class="variant">
    <!-- Card Skeleton -->
    <template v-if="variant === 'card'">
      <div class="skeleton-card">
        <div class="skeleton-header">
          <div class="skeleton-avatar"></div>
          <div class="skeleton-info">
            <div class="skeleton-title"></div>
            <div class="skeleton-subtitle"></div>
          </div>
        </div>
        <div class="skeleton-content">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
          <div class="skeleton-line"></div>
        </div>
      </div>
    </template>

    <!-- List Skeleton -->
    <template v-else-if="variant === 'list'">
      <div class="skeleton-list">
        <div v-for="i in rows" :key="i" class="skeleton-list-item">
          <div class="skeleton-avatar small"></div>
          <div class="skeleton-info">
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- Table Skeleton -->
    <template v-else-if="variant === 'table'">
      <div class="skeleton-table">
        <div class="skeleton-table-header">
          <div v-for="i in columns" :key="i" class="skeleton-header-cell"></div>
        </div>
        <div v-for="row in rows" :key="row" class="skeleton-table-row">
          <div v-for="col in columns" :key="col" class="skeleton-table-cell"></div>
        </div>
      </div>
    </template>

    <!-- Chart Skeleton -->
    <template v-else-if="variant === 'chart'">
      <div class="skeleton-chart">
        <div class="skeleton-chart-header"></div>
        <div class="skeleton-chart-bars">
          <div v-for="i in 8" :key="i" class="skeleton-bar" :style="{ height: `${Math.random() * 60 + 20}%` }"></div>
        </div>
      </div>
    </template>

    <!-- Default Skeleton -->
    <template v-else>
      <div class="skeleton-default">
        <div v-for="i in rows" :key="i" class="skeleton-line" :class="{ short: i % 3 === 0 }"></div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
interface Props {
  variant?: 'card' | 'list' | 'table' | 'chart' | 'default'
  rows?: number
  columns?: number
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  rows: 3,
  columns: 4
})
</script>

<style scoped>
.skeleton-loader {
  width: 100%;
}

/* Base skeleton animation */
.skeleton-line,
.skeleton-avatar,
.skeleton-title,
.skeleton-subtitle,
.skeleton-header-cell,
.skeleton-table-cell,
.skeleton-bar {
  background: linear-gradient(
    90deg,
    var(--color-border-light) 25%,
    var(--color-border-base) 50%,
    var(--color-border-light) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: var(--border-radius-xs);
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Default skeleton */
.skeleton-default {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton-line {
  height: 16px;
  border-radius: var(--border-radius-xs);
}

.skeleton-line.short {
  width: 60%;
}

/* Card skeleton */
.skeleton-card {
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-lg);
}

.skeleton-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.skeleton-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--border-radius-circle);
}

.skeleton-avatar.small {
  width: 32px;
  height: 32px;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.skeleton-title {
  height: 18px;
  width: 40%;
  border-radius: var(--border-radius-xs);
}

.skeleton-subtitle {
  height: 14px;
  width: 60%;
  border-radius: var(--border-radius-xs);
}

.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* List skeleton */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) 0;
}

/* Table skeleton */
.skeleton-table {
  width: 100%;
}

.skeleton-table-header {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border-light);
}

.skeleton-header-cell {
  height: 16px;
  flex: 1;
  border-radius: var(--border-radius-xs);
}

.skeleton-table-row {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
}

.skeleton-table-cell {
  height: 14px;
  flex: 1;
  border-radius: var(--border-radius-xs);
}

/* Chart skeleton */
.skeleton-chart {
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-lg);
}

.skeleton-chart-header {
  height: 20px;
  width: 30%;
  margin-bottom: var(--spacing-lg);
  border-radius: var(--border-radius-xs);
}

.skeleton-chart-bars {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-xs);
  height: 120px;
}

.skeleton-bar {
  flex: 1;
  min-height: 20px;
  border-radius: var(--border-radius-xs) var(--border-radius-xs) 0 0;
}
</style>
