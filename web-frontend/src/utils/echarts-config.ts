/**
 * ECharts 配置和主题
 */
import * as echarts from 'echarts';
import { PRIMARY, TEXT_PRIMARY, TEXT_REGULAR, BORDER_BASE } from '@/styles/colors';

// Vintage 配色方案
export const vintageColors = [
  '#d87c7c',
  '#919e8b',
  '#d7ab82',
  '#6e7074',
  '#61a0a8',
  '#efa18d',
  '#787464',
  '#cc7e63',
  '#724e58',
  '#4b565b',
];

// 通用图表配置
export const commonChartOptions = {
  color: vintageColors,
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
    fontSize: 14,
    color: TEXT_PRIMARY,
  },
  title: {
    textStyle: {
      fontSize: 18,
      fontWeight: 500,
      color: TEXT_PRIMARY,
    },
    subtextStyle: {
      fontSize: 14,
      color: TEXT_REGULAR,
    },
  },
  legend: {
    textStyle: {
      fontSize: 14,
      color: TEXT_REGULAR,
    },
    icon: 'roundRect',
  },
  tooltip: {
    backgroundColor: 'rgba(50, 50, 50, 0.9)',
    borderColor: '#333',
    borderWidth: 0,
    textStyle: {
      color: '#fff',
      fontSize: 14,
    },
    axisPointer: {
      lineStyle: {
        color: PRIMARY,
      },
      crossStyle: {
        color: PRIMARY,
      },
    },
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '10%',
    containLabel: true,
  },
  xAxis: {
    axisLine: {
      lineStyle: {
        color: '#DCDFE6',
      },
    },
    axisLabel: {
      color: TEXT_REGULAR,
      fontSize: 12,
    },
    splitLine: {
      lineStyle: {
        color: BORDER_BASE,
      },
    },
  },
  yAxis: {
    axisLine: {
      lineStyle: {
        color: '#DCDFE6',
      },
    },
    axisLabel: {
      color: TEXT_REGULAR,
      fontSize: 12,
    },
    splitLine: {
      lineStyle: {
        color: BORDER_BASE,
      },
    },
  },
};

// 柱状图配置
export function getBarChartOption(data: any) {
  return {
    ...commonChartOptions,
    series: [{
      type: 'bar',
      data: data,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.3)',
        },
      },
    }],
  };
}

// 折线图配置
export function getLineChartOption(data: any) {
  return {
    ...commonChartOptions,
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      lineStyle: {
        width: 3,
      },
      areaStyle: {
        opacity: 0.3,
      },
      emphasis: {
        focus: 'series',
      },
    }],
  };
}

// 饼图配置
export function getPieChartOption(data: any) {
  return {
    ...commonChartOptions,
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        show: true,
        fontSize: 14,
        color: TEXT_REGULAR,
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold',
        },
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.3)',
        },
      },
      data: data,
    }],
  };
}

// 初始化图表
export function initChart(el: HTMLElement, option: any) {
  const chart = echarts.init(el);
  chart.setOption(option);
  
  // 响应式
  window.addEventListener('resize', () => {
    chart.resize();
  });
  
  return chart;
}

// 图表自适应
export function resizeChart(chart: echarts.ECharts) {
  chart.resize();
}

// 销毁图表
export function disposeChart(chart: echarts.ECharts) {
  chart.dispose();
}
