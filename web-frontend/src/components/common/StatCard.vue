<template>
  <div class="stat-card" :class="[`stat-card--${type}`]">
    <div class="stat-icon">
      <el-icon :size="32">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="stat-content">
      <div class="stat-title">{{ title }}</div>
      <div class="stat-value">
        {{ value }}
        <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
      </div>
      <div v-if="trend" class="stat-trend" :class="[`trend--${trend.type}`]">
        <el-icon>
          <component :is="trend.type === 'up' ? 'CaretTop' : 'CaretBottom'" />
        </el-icon>
        <span>{{ trend.value }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CaretTop, CaretBottom } from '@element-plus/icons-vue';

interface Props {
  title: string;
  value: string | number;
  suffix?: string;
  icon: any;
  type?: 'primary' | 'success' | 'warning' | 'danger';
  trend?: {
    type: 'up' | 'down';
    value: string;
  };
}

withDefaults(defineProps<Props>(), {
  type: 'primary',
});
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-md;
  background: $bg-white;
  border-radius: $border-radius-base;
  box-shadow: $box-shadow-base;
  transition: $transition-base;
  
  &:hover {
    box-shadow: $box-shadow-light;
    transform: translateY(-2px);
  }
  
  .stat-icon {
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: $border-radius-large;
    flex-shrink: 0;
  }
  
  .stat-content {
    flex: 1;
    
    .stat-title {
      font-size: $font-size-base;
      color: $text-secondary;
      margin-bottom: $spacing-xs;
    }
    
    .stat-value {
      font-size: $font-size-extra-large;
      font-weight: $font-weight-bold;
      color: $text-primary;
      
      .stat-suffix {
        font-size: $font-size-base;
        font-weight: $font-weight-normal;
        color: $text-secondary;
        margin-left: 4px;
      }
    }
    
    .stat-trend {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: $font-size-small;
      margin-top: $spacing-xs;
      
      &.trend--up {
        color: $success-color;
      }
      
      &.trend--down {
        color: $danger-color;
      }
    }
  }
  
  &--primary .stat-icon {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: $bg-white;
  }
  
  &--success .stat-icon {
    background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
    color: $bg-white;
  }
  
  &--warning .stat-icon {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    color: $bg-white;
  }
  
  &--danger .stat-icon {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: $bg-white;
  }
}
</style>
