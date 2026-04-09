<template>
  <div class="search-box">
    <el-input
      v-model="searchValue"
      :placeholder="placeholder"
      clearable
      @keyup.enter="handleSearch"
    >
      <template v-if="showButton" #append>
        <el-button :icon="Search" @click="handleSearch" />
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Search } from '@element-plus/icons-vue';

const props = defineProps<{
  placeholder?: string;
  showButton?: boolean;
  modelValue?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'search', value: string): void;
}>();

const searchValue = ref('');

watch(() => props.modelValue, (val) => {
  if (val !== undefined) {
    searchValue.value = val;
  }
}, { immediate: true });

watch(searchValue, (val) => {
  emit('update:modelValue', val);
});

function handleSearch() {
  emit('search', searchValue.value);
}
</script>

<style scoped>
.search-box {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
}

.el-input {
  width: 100%;
}
</style>
