<template>
  <router-view v-slot="{ Component }">
    <transition name="app-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.app-fade-enter-active {
  transition: opacity 0.3s cubic-bezier(0.23, 1, 0.32, 1),
              transform 0.3s cubic-bezier(0.23, 1, 0.32, 1);
}
.app-fade-leave-active {
  transition: opacity 0.18s ease-out;
}
.app-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.app-fade-leave-to {
  opacity: 0;
}
</style>
