<template>
  <!--
    四个卡通角色, 眼睛瞳孔实时跟随鼠标方向
    - 4 只眼眶 (白底), 8 个瞳孔 (黑色)
    - mousemove 监听全局, 计算每个瞳孔相对鼠标的方向, 限制在眼眶半径内
  -->
  <div ref="rootRef" class="mascot-eyes" aria-hidden="true">
    <svg
      viewBox="0 0 360 280"
      width="100%"
      height="100%"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- 紫色长方形人 -->
      <rect x="40" y="40" width="100" height="200" rx="50" fill="#5B30E2" />
      <!-- 黑色长方形人 (在后排) -->
      <rect x="170" y="80" width="60" height="160" rx="22" fill="#1F1F1F" />
      <!-- 橙色半圆人 -->
      <path d="M 60 240 a 70 70 0 0 1 140 0 z" fill="#F26B1D" />
      <!-- 黄色拱形人 -->
      <path d="M 230 240 v -80 a 50 50 0 0 1 100 0 v 80 z" fill="#F2B61D" />

      <!-- 眼睛: 白底圆 + 跟随瞳孔 -->
      <!-- 紫人 (左 90,110 / 右 120,110) -->
      <circle cx="90"  cy="110" r="11" fill="#fff" />
      <circle cx="120" cy="110" r="11" fill="#fff" />
      <circle :cx="px(90,110)"  :cy="py(90,110)"  r="5" fill="#1F1F1F" />
      <circle :cx="px(120,110)" :cy="py(120,110)" r="5" fill="#1F1F1F" />

      <!-- 紫人微笑 -->
      <path d="M 95 145 q 10 8 20 0" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" />

      <!-- 黑人 (左 185,140 / 右 215,140) -->
      <circle cx="185" cy="140" r="9" fill="#fff" />
      <circle cx="215" cy="140" r="9" fill="#fff" />
      <circle :cx="px(185,140,4)" :cy="py(185,140,4)" r="4" fill="#1F1F1F" />
      <circle :cx="px(215,140,4)" :cy="py(215,140,4)" r="4" fill="#1F1F1F" />

      <!-- 橙人 (位置较低 110,205 / 145,205) -->
      <circle cx="110" cy="205" r="11" fill="#fff" />
      <circle cx="145" cy="205" r="11" fill="#fff" />
      <circle :cx="px(110,205)" :cy="py(110,205)" r="5" fill="#1F1F1F" />
      <circle :cx="px(145,205)" :cy="py(145,205)" r="5" fill="#1F1F1F" />
      <!-- 橙人笑容 -->
      <path d="M 117 222 q 10 10 20 0" stroke="#1F1F1F" stroke-width="2.5" fill="none" stroke-linecap="round" />

      <!-- 黄人 (267,185 / 297,185) -->
      <circle cx="267" cy="185" r="11" fill="#fff" />
      <circle cx="297" cy="185" r="11" fill="#fff" />
      <circle :cx="px(267,185)" :cy="py(267,185)" r="5" fill="#1F1F1F" />
      <circle :cx="px(297,185)" :cy="py(297,185)" r="5" fill="#1F1F1F" />
      <!-- 黄人嘴 (一字) -->
      <line x1="270" y1="220" x2="294" y2="220" stroke="#1F1F1F" stroke-width="2.5" stroke-linecap="round" />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';

const rootRef = ref<HTMLElement | null>(null);
// 鼠标在 SVG viewBox 坐标系下的位置
const mouseX = ref(180);   // viewBox 中心
const mouseY = ref(140);

// 默认瞳孔最大偏移量 (像素 in viewBox)
const DEFAULT_EYE_R = 11;
const DEFAULT_PUPIL_R = 5;
const DEFAULT_MAX_OFFSET = DEFAULT_EYE_R - DEFAULT_PUPIL_R - 1; // = 5

/**
 * 计算瞳孔相对眼眶中心的 x 坐标
 * @param cx 眼眶圆心 x (viewBox)
 * @param cy 眼眶圆心 y (viewBox)
 * @param maxOffset 最大偏移 (默认 5)
 */
function px(cx: number, cy: number, maxOffset = DEFAULT_MAX_OFFSET): number {
  const dx = mouseX.value - cx;
  const dy = mouseY.value - cy;
  const dist = Math.hypot(dx, dy) || 1;
  const r = Math.min(maxOffset, dist);
  return cx + (dx / dist) * r;
}
function py(cx: number, cy: number, maxOffset = DEFAULT_MAX_OFFSET): number {
  const dx = mouseX.value - cx;
  const dy = mouseY.value - cy;
  const dist = Math.hypot(dx, dy) || 1;
  const r = Math.min(maxOffset, dist);
  return cy + (dy / dist) * r;
}

/**
 * 把屏幕坐标 (clientX/Y) 转成 SVG viewBox 坐标
 * 需要拿到 rootRef 的 bounding rect, 按比例换算
 */
function onMouseMove(e: MouseEvent) {
  const el = rootRef.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return;
  // viewBox = 360x280
  const x = ((e.clientX - rect.left) / rect.width) * 360;
  const y = ((e.clientY - rect.top) / rect.height) * 280;
  mouseX.value = x;
  mouseY.value = y;
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove, { passive: true });
});
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMouseMove);
});
</script>

<style scoped>
.mascot-eyes {
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
  user-select: none;
  pointer-events: none; /* 不挡表单点击 */
}
.mascot-eyes svg {
  display: block;
}
</style>
