<template>
  <div ref="chart" style="width: 100%; height: 400px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import * as echarts from 'echarts';

const chart = ref(null);

onMounted(() => {
  const myChart = echarts.init(chart.value);
  myChart.setOption({
    series: [
      {
        type: 'pie',
        data: [
          { value: 335, name: 'Positive' },
          { value: 234, name: 'Negative' },
          { value: 1548, name: 'Neutral' },
        ],
      },
    ],
  });
});
</script>
