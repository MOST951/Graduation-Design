<template>
  <div class="container-component" :class="{ 'show-border': showBorder }">
    <div v-if="showHeader && title" class="container-header">
      {{ title }}
    </div>
    <div class="container-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  showBorder?: boolean;
  showHeader?: boolean;
}>();
</script>

<style scoped>
.container-component {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
}

.container-component.show-border {
  border: 1px solid #e4e7ed;
}

.container-header {
  padding: 12px 16px;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
}

.container-content {
  flex: 1;
  padding: 16px;
  overflow: auto;
}
</style>
