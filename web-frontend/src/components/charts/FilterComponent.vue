<template>
  <div class="filter-component">
    <span v-if="label" class="filter-label">{{ label }}</span>
    <el-select
      v-model="selectedValue"
      :placeholder="placeholder"
      :multiple="multiple"
      clearable
      @change="handleChange"
    >
      <el-option
        v-for="option in normalizedOptions"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

const props = defineProps<{
  label?: string;
  options?: string[] | { label: string; value: string }[];
  multiple?: boolean;
  placeholder?: string;
  modelValue?: string | string[];
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | string[]): void;
  (e: 'change', value: string | string[]): void;
}>();

const selectedValue = ref<string | string[]>(props.multiple ? [] : '');

const normalizedOptions = computed(() => {
  if (!props.options) return [];
  return props.options.map(opt => 
    typeof opt === 'string' ? { label: opt, value: opt } : opt
  );
});

watch(() => props.modelValue, (val) => {
  if (val !== undefined) {
    selectedValue.value = val;
  }
}, { immediate: true });

function handleChange(value: string | string[]) {
  emit('update:modelValue', value);
  emit('change', value);
}
</script>

<style scoped>
.filter-component {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 100%;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.el-select {
  flex: 1;
}
</style>
