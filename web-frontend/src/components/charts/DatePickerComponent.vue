<template>
  <div class="date-picker-component">
    <span v-if="label" class="picker-label">{{ label }}</span>
    <el-date-picker
      v-model="selectedDate"
      :type="type"
      :format="format"
      :placeholder="placeholder"
      :start-placeholder="type === 'daterange' ? '开始日期' : undefined"
      :end-placeholder="type === 'daterange' ? '结束日期' : undefined"
      @change="handleChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  label?: string;
  type?: 'date' | 'daterange' | 'datetime' | 'datetimerange' | 'month' | 'year';
  format?: string;
  placeholder?: string;
  modelValue?: Date | Date[];
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: Date | Date[] | null): void;
  (e: 'change', value: Date | Date[] | null): void;
}>();

const selectedDate = ref<Date | Date[] | null>(null);

watch(() => props.modelValue, (val) => {
  if (val !== undefined) {
    selectedDate.value = val;
  }
}, { immediate: true });

function handleChange(value: Date | Date[] | null) {
  emit('update:modelValue', value);
  emit('change', value);
}
</script>

<style scoped>
.date-picker-component {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 100%;
}

.picker-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.el-date-picker {
  flex: 1;
}
</style>
