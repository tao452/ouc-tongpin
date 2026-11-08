<template>
  <div class="heatmap-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">校园情绪热力图与趋势</h2>
      <span class="page-subtitle">各时段情绪打卡热度分布</span>
    </div>

    <!-- 图表卡片 -->
    <el-card class="chart-card" shadow="never">
      <div ref="chartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref(null)
let chart = null

// 生成 mock 数据：[x轴索引, y轴索引, 热度值]
const generateMockData = () => {
  const data = []
  for (let x = 0; x < 7; x++) {
    for (let y = 0; y < 4; y++) {
      // 随机热度 0-100，模拟情绪打卡量
      const value = Math.round(Math.random() * 100)
      data.push([x, y, value])
    }
  }
  return data
}

const getOption = () => ({
  tooltip: {
    position: 'top',
    formatter: (p) => {
      const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      const hours = ['8点', '12点', '16点', '20点']
      return `${days[p.data[0]]} ${hours[p.data[1]]}：热度 ${p.data[2]}`
    }
  },
  grid: { left: 70, right: 90, top: 30, bottom: 40 },
  xAxis: {
    type: 'category',
    data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    splitArea: { show: true }
  },
  yAxis: {
    type: 'category',
    data: ['8点', '12点', '16点', '20点'],
    splitArea: { show: true }
  },
  visualMap: {
    min: 0,
    max: 100,
    calculable: true,
    orient: 'vertical',
    right: 10,
    top: 'center',
    // 从浅蓝渐变到深红
    inRange: {
      color: ['#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#f4a582', '#d73027', '#a50026']
    },
    text: ['高', '低']
  },
  series: [
    {
      name: '情绪热度',
      type: 'heatmap',
      data: generateMockData(),
      label: { show: true, fontSize: 11, color: '#333' },
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.4)' }
      }
    }
  ]
})

const handleResize = () => chart?.resize()

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption())
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.heatmap-page {
  padding: 4px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.page-subtitle {
  font-size: 13px;
  color: #909399;
}

.chart-card {
  border-radius: 10px;
}

/* 关键：图表容器必须给明确高度 */
.chart-container {
  height: 420px;
  width: 100%;
}
</style>