<template>
  <div class="dashboard-container">
    <h2>基础数据看板 (V0.1内测版)</h2>
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="card-title">总用户数</div>
          <div class="card-number">1,284</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="card-title">今日打卡数</div>
          <div class="card-number">342</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="card-title">树洞发帖数</div>
          <div class="card-number">89</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card shadow="hover">
      <div ref="chartRef" style="width: 100%; height: 400px;"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref<HTMLElement | null>(null)

onMounted(() => {
  if (chartRef.value) {
    const myChart = echarts.init(chartRef.value)
    const option = {
      title: { text: '近一周活跃趋势' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
      yAxis: { type: 'value' },
      series: [{ data: [120, 200, 150, 80, 70, 110, 130], type: 'line', smooth: true, itemStyle: { color: '#409EFF' } }]
    }
    myChart.setOption(option)
  }
})
</script>

<style scoped>
.dashboard-container { padding: 20px; }
.card-title { font-size: 14px; color: #666; margin-bottom: 10px; }
.card-number { font-size: 28px; font-weight: bold; color: #333; }
</style>
