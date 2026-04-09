<template>
  <div 
    class="loading-spinner" 
    :class="[`loading-${size}`, { 'loading-overlay': overlay }]"
    :style="{ color: color }"
    role="status"
    :aria-label="ariaLabel"
  >
    <svg class="spinner" viewBox="0 0 50 50">
      <circle
        class="spinner-path"
        cx="25"
        cy="25"
        r="20"
        fill="none"
        stroke="currentColor"
        stroke-width="4"
        stroke-linecap="round"
        stroke-dasharray="31.416"
        stroke-dashoffset="31.416"
      />
    </svg>
    <span v-if="text" class="loading-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
interface Props {
  size?: 'small' | 'medium' | 'large'
  color?: string
  text?: string
  overlay?: boolean
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  color: 'var(--color-primary)',
  text: '',
  overlay: false,
  ariaLabel: 'Loading'
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-bg-overlay);
  z-index: var(--z-index-top);
}

.loading-small .spinner {
  width: 20px;
  height: 20px;
}

.loading-medium .spinner {
  width: 32px;
  height: 32px;
}

.loading-large .spinner {
  width: 48px;
  height: 48px;
}

.spinner {
  animation: spin 1s linear infinite;
}

.spinner-path {
  animation: dash 1.5s ease-in-out infinite;
}

.loading-text {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}
</style>
