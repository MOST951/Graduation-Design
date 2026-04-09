<template>
  <div class="dropdown-component">
    <span v-if="label" class="dropdown-label">{{ label }}</span>
    <el-select
      v-model="selectedValue"
      :placeholder="placeholder"
      clearable
      @change="handleChange"
    >
      <el-option
        v-for="option in options"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  label?: string;
  options?: { label: string; value: string }[];
  placeholder?: string;
  modelValue?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'change', value: string): void;
}>();

const selectedValue = ref('');

watch(() => props.modelValue, (val) => {
  if (val !== undefined) {
    selectedValue.value = val;
  }
}, { immediate: true });

function handleChange(value: string) {
  emit('update:modelValue', value);
  emit('change', value);
}
</script>

<style scoped>
.dropdown-component {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 100%;
}

.dropdown-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.el-select {
  flex: 1;
}
</style>
