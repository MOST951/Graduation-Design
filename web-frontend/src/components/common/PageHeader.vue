<template>
  <div class="page-header">
    <div class="header-content">
      <div class="header-left">
        <h2 class="page-title">{{ title }}</h2>
        <p v-if="description" class="page-description">{{ description }}</p>
      </div>
      <div v-if="$slots.extra" class="header-right">
        <slot name="extra"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string;
  description?: string;
}

defineProps<Props>();
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.page-header {
  background: $bg-white;
  padding: $spacing-md;
  margin-bottom: $spacing-md;
  border-radius: $border-radius-base;
  box-shadow: $box-shadow-base;
  
  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .header-left {
    flex: 1;
    
    .page-title {
      font-size: $font-size-large;
      font-weight: $font-weight-medium;
      color: $text-primary;
      margin: 0 0 $spacing-xs 0;
    }
    
    .page-description {
      font-size: $font-size-base;
      color: $text-secondary;
      margin: 0;
    }
  }
  
  .header-right {
    flex-shrink: 0;
    margin-left: $spacing-md;
  }
}
</style>
