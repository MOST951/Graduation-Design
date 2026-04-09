<template>
  <div class="text-box" :style="textStyle">
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  text?: string;
  align?: 'left' | 'center' | 'right';
}>();

const textStyle = computed(() => ({
  textAlign: props.align || 'left',
}));
</script>

<style scoped>
.text-box {
  width: 100%;
  height: 100%;
  padding: 8px;
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  overflow: auto;
}
</style>
