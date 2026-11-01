<template>
  <div class="data-board">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col v-for="item in stats" :key="item.title" :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-body">
            <div class="stat-icon" :style="{ background: item.bg }">
              <el-icon :size="26" color="#fff">
                <component :is="item.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-title">{{ item.title }}</div>
              <div class="stat-value">{{ item.value.toLocaleString() }}</div>
              <div class="stat-sub">{{ item.sub }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域：左右各一半 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <span class="chart-title">近 7 天情绪打卡趋势</span>
          </template>
          <div ref="trendRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <span class="chart-title">校园情绪分布</span>
          </template>
          <div ref="pieRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { User, Position, ChatDotRound, Warning } from '@element-plus/icons-vue'

/* ---------------- mock 假数据（写死） ---------------- */

// 顶部统计卡片
const stats = ref([
  {
    title: '今日活跃用户',
    value: 1286,
    sub: '较昨日 +12.5%',
    icon: User,
    bg: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  {
    title: '今日打卡次数',
    value: 3421,
    sub: '较昨日 +8.2%',
    icon: Position,
    bg: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  },
  {
    title: '树洞发帖数',
    value: 186,
    sub: '较昨日 +3.4%',
    icon: ChatDotRound,
    bg: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
  },
  {
    title: '危机干预工单数',
    value: 12,
    sub: '其中高危 3 单 · 待处理',
    icon: Warning,
    bg: 'linear-gradient(135deg, #ff5858 0%, #f09819 100%)'
  }
])

// 近 7 天打卡趋势
const trendOption = {
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 20, top: 40, bottom: 30 },
  xAxis: {
    type: 'category',
    data: ['10-26', '10-27', '10-28', '10-29', '10-30', '10-31', '11-01'],
    boundaryGap: false
  },
  yAxis: { type: 'value', name: '打卡次数' },
  series: [
    {
      name: '打卡次数',
      type: 'line',
      smooth: true,
      data: [2860, 3120, 3350, 2980, 3540, 3210, 3421],
      lineStyle: { width: 3, color: '#409EFF' },
      itemStyle: { color: '#409EFF' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
        ])
      }
    }
  ]
}

// 校园情绪分布饼图
const pieOption = {
  color: ['#67C23A', '#409EFF', '#E6A23C', '#909399'],
  tooltip: { trigger: 'item', formatter: '{b}: {c} 人 ({d}%)' },
  legend: { bottom: 0, left: 'center' },
  series: [
    {
      name: '情绪分布',
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      label: { show: true, formatter: '{b}\n{d}%' },
      emphasis: {
        itemStyle: { shadowBlur: 12, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.25)' },
        label: { show: true, fontWeight: 'bold' }
      },
      data: [
        { value: 592, name: '开心' },
        { value: 399, name: '平静' },
        { value: 193, name: '焦虑' },
        { value: 102, name: '抑郁' }
      ]
    }
  ]
}

/* ---------------- ECharts 初始化 / 销毁 ---------------- */

const trendRef = ref(null)
const pieRef = ref(null)
let trendChart = null
let pieChart = null

const handleResize = () => {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  trendChart = echarts.init(trendRef.value)
  trendChart.setOption(trendOption)

  pieChart = echarts.init(pieRef.value)
  pieChart.setOption(pieOption)

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.data-board {
  padding: 4px;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  margin-bottom: 16px;
  border-radius: 10px;
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
}

.stat-body {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-title {
  font-size: 13px;
  color: #909399;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
  line-height: 1.3;
}

.stat-sub {
  font-size: 12px;
  color: #67c23a;
}

.chart-card {
  border-radius: 10px;
}

.chart-card :deep(.el-card__header) {
  font-weight: 600;
}

.chart-container {
  /* 关键：图表容器必须给固定高度 */
  height: 340px;
  width: 100%;
}
</style>