<template>
  <div ref="chart" style="width: 100%; height: 400px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import * as echarts from 'echarts';
import 'echarts-wordcloud';

const chart = ref(null);

onMounted(() => {
  const myChart = echarts.init(chart.value);
  myChart.setOption({
    series: [
      {
        type: 'wordCloud',
        data: [
          { name: 'Weibo', value: 100 },
          { name: 'Sentiment', value: 80 },
          { name: 'Analysis', value: 70 },
          { name: 'Positive', value: 60 },
          { name: 'Negative', value: 50 },
        ],
      },
    ],
  });
});
</script>
