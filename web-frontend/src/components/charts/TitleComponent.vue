<template>
  <div class="title-component" :style="titleStyle">
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  text?: string;
  level?: 1 | 2 | 3 | 4;
  align?: 'left' | 'center' | 'right';
}>();

const fontSizes: Record<number, string> = {
  1: '28px',
  2: '24px',
  3: '20px',
  4: '16px',
};

const titleStyle = computed(() => ({
  fontSize: fontSizes[props.level || 1],
  textAlign: props.align || 'center',
  fontWeight: props.level === 1 ? 'bold' : props.level === 2 ? '600' : '500',
}));
</script>

<style scoped>
.title-component {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #303133;
  line-height: 1.4;
  word-break: break-word;
}
</style>
