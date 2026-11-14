
const { request } = require('../../utils/request.js')

const EMOTIONS = [
  { code: 'HAPPY', label: '开心', color: '#FFD93D' },
  { code: 'CALM', label: '平静', color: '#95E1D3' },
  { code: 'ANXIOUS', label: '焦虑', color: '#FF9F68' },
  { code: 'LONELY', label: '孤独', color: '#A6B1E1' },
  { code: 'IRRITABLE', label: '烦躁', color: '#FF6B6B' },
  { code: 'DOWN', label: '低落', color: '#6C7A89' }
]

Page({
  data: {
    totalDays: 0,
    continuousDays: 0,
    records: [],
    loading: false,
    error: false,

    // 情绪分析
    rangeDays: 7,
    trendData: [],
    distributionData: [],
    analysisTotal: 0
  },

  onLoad() {
    this.loadRecords()
  },

  onShow() {
    this.loadRecords()
  },

  // 加载打卡记录
  loadRecords() {
    if (this.data.loading) return

    const today = new Date()
    const to = this.formatDate(today)
    const from = '2000-01-01'

    this.setData({
      loading: true,
      error: false
    })

    request({
      url: `/api/emotions/checkins?from=${from}&to=${to}`,
      method: 'GET',
      showLoading: false
    })
      .then((data) => {
        const items = Array.isArray(data.items) ? data.items : []

        const emotionLabels = {}
        EMOTIONS.forEach((item) => {
          emotionLabels[item.code] = item.label
        })

        // 整理历史记录
        const records = items.map((item) => {
          const emotionText =
            emotionLabels[item.emotion] || '情绪打卡'

          const intensity = Number(item.intensity)

          const intensityText =
            Number.isFinite(intensity) &&
            intensity >= 1 &&
            intensity <= 5
              ? `强度 ${intensity}/5`
              : '强度未记录'

          const note = item.note ? ` · ${item.note}` : ''

          return {
            id: item.id,
            date: item.checkinDate
              ? this.formatRecordDate(item.checkinDate)
              : '日期未知',
            status: '已完成',
            summary: `${emotionText} · ${intensityText}${note}`
          }
        })

        this.setData({
          totalDays: Number(data.total) || 0,
          continuousDays: Number(data.streakDays) || 0,
          records
        })

        this.buildAnalysis(items)
      })
      .catch((err) => {
        console.error('获取打卡记录失败：', err)

        this.setData({ error: true })

        wx.showToast({
          title: '记录加载失败',
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  // 切换近一周 / 近一月
  changeRange(e) {
    const rangeDays = Number(e.currentTarget.dataset.range)

    if (rangeDays !== 7 && rangeDays !== 30) return

    this.setData({ rangeDays }, () => {
      if (this._checkinItems) {
        this.buildAnalysis(this._checkinItems)
      }
    })
  },

  // 计算情绪趋势和情绪分布
  buildAnalysis(items) {
    this._checkinItems = items

    const rangeDays = this.data.rangeDays
    const today = new Date()
    const dailyData = {}
    const trendData = []

    // 初始化最近 N 天的数据
    for (let i = rangeDays - 1; i >= 0; i--) {
      const date = new Date(
        today.getFullYear(),
        today.getMonth(),
        today.getDate() - i
      )

      const dateString = this.formatDate(date)

      dailyData[dateString] = {
        totalIntensity: 0,
        count: 0,
        emotion: null
      }

      trendData.push({
        date: dateString,
        label: `${date.getMonth() + 1}/${date.getDate()}`,
        intensity: null,
        emotion: null
      })
    }

    // 初始化六种情绪的统计
    const emotionCounts = {}

    EMOTIONS.forEach((item) => {
      emotionCounts[item.code] = 0
    })

    // 统计打卡数据
    items.forEach((item) => {
      const date = item.checkinDate

      if (!date || !dailyData[date]) return

      const emotion = item.emotion
      const intensity = Number(item.intensity)

      // 统计情绪出现次数
      if (
        Object.prototype.hasOwnProperty.call(
          emotionCounts,
          emotion
        )
      ) {
        emotionCounts[emotion]++

        // 同一天有多条记录时，采用最后遍历到的情绪
        dailyData[date].emotion = emotion
      }

      // 统计情绪强度
      if (
        Number.isFinite(intensity) &&
        intensity >= 1 &&
        intensity <= 5
      ) {
        dailyData[date].totalIntensity += intensity
        dailyData[date].count++
      }
    })

    // 计算每天的平均情绪强度
    trendData.forEach((item) => {
      const daily = dailyData[item.date]

      if (daily.count > 0) {
        item.intensity = Number(
          (daily.totalIntensity / daily.count).toFixed(1)
        )
      }

      item.emotion = daily.emotion
    })

    // 计算情绪分布
    const analysisTotal = Object.values(emotionCounts).reduce(
      (sum, count) => sum + count,
      0
    )

    const distributionData = EMOTIONS.map((emotion) => {
      const count = emotionCounts[emotion.code]

      return {
        code: emotion.code,
        label: emotion.label,
        color: emotion.color,
        count,
        percent: analysisTotal > 0
          ? Math.round((count / analysisTotal) * 100)
          : 0
      }
    })

    this.setData(
      {
        trendData,
        distributionData,
        analysisTotal
      },
      () => {
        this.drawTrendChart()
      }
    )
  },

  // 绘制情绪强度折线图
  drawTrendChart() {
    const { trendData, analysisTotal } = this.data

    if (!analysisTotal || !trendData.length) return

    const ctx = wx.createCanvasContext(
      'emotionTrendCanvas',
      this
    )

    const width = 345
    const left = 32
    const right = width - 10
    const top = 15
    const bottom = 145

    const chartWidth = right - left
    const chartHeight = bottom - top

    // 绘制背景网格和纵轴刻度
    ctx.setFontSize(10)
    ctx.setLineWidth(1)

    for (let i = 1; i <= 5; i++) {
      const y = bottom - ((i - 1) / 4) * chartHeight

      ctx.setStrokeStyle('#edf0f4')
      ctx.beginPath()
      ctx.moveTo(left, y)
      ctx.lineTo(right, y)
      ctx.stroke()

      ctx.setFillStyle('#98a2b3')
      ctx.fillText(String(i), 10, y + 3)
    }

    // 计算横坐标
    const getX = (index) => {
      if (trendData.length === 1) {
        return left + chartWidth / 2
      }

      return left +
        (index / (trendData.length - 1)) * chartWidth
    }

    // 计算纵坐标
    const getY = (value) => {
      return bottom - ((value - 1) / 4) * chartHeight
    }

    // 绘制蓝色趋势折线
    // 没有打卡的日期不连接，避免产生错误趋势
    let segment = []

    const drawSegment = () => {
      if (segment.length === 0) return

      ctx.beginPath()
      ctx.moveTo(segment[0].x, segment[0].y)

      for (let i = 1; i < segment.length; i++) {
        ctx.lineTo(segment[i].x, segment[i].y)
      }

      ctx.stroke()
      segment = []
    }

    ctx.setStrokeStyle('#4a69bd')
    ctx.setLineWidth(2)

    trendData.forEach((item, index) => {
      if (item.intensity === null) {
        drawSegment()
        return
      }

      segment.push({
        x: getX(index),
        y: getY(item.intensity)
      })
    })

    drawSegment()

    // 绘制不同情绪颜色的数据点
    trendData.forEach((item, index) => {
      if (item.intensity === null) return

      const x = getX(index)
      const y = getY(item.intensity)

      const emotion = EMOTIONS.find(
        (emotionItem) => emotionItem.code === item.emotion
      )

      // 根据当天情绪决定数据点颜色
      const pointColor = emotion
        ? emotion.color
        : '#4a69bd'

      // 白色描边，让数据点更加清晰
      ctx.beginPath()
      ctx.arc(x, y, 5, 0, Math.PI * 2)
      ctx.setFillStyle(pointColor)
      ctx.fill()

      ctx.setStrokeStyle('#ffffff')
      ctx.setLineWidth(2)
      ctx.stroke()
    })

    // 绘制日期标签，避免过于密集
    const step = Math.max(
      1,
      Math.ceil(trendData.length / 6)
    )

    ctx.setFontSize(9)
    ctx.setFillStyle('#98a2b3')

    trendData.forEach((item, index) => {
      if (
        index % step !== 0 &&
        index !== trendData.length - 1
      ) {
        return
      }

      const x = getX(index)
      ctx.fillText(item.label, x - 10, 165)
    })

    ctx.draw()
  },

  // 日期格式化
  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  },

  // 历史记录日期格式化
  formatRecordDate(dateString) {
    const parts = dateString.split('-')

    if (parts.length !== 3) return dateString

    return `${Number(parts[1])}月${Number(parts[2])}日`
  },

  // 重新加载
  retryLoad() {
    this.loadRecords()
  }
})
