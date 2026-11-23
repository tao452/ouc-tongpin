
const { request } = require('../../utils/request.js')
const {
  EMOTIONS,
  normalizeRange,
  getWindowRange,
  buildAnalysis
} = require('../../utils/emotion-analysis.js')

Page({
  data: {
    totalDays: 0,
    continuousDays: 0,
    records: [],
    loading: false,
    error: false,

    // 情绪分析：近 7 / 近 30 天滚动窗口，口径见 docs/requirements/情绪曲线与分布-验收口径-v1.md
    rangeDays: 7,
    windowFrom: '',
    windowTo: '',
    trendData: [],
    distributionData: [],
    analysisTotal: 0,
    missingDays: 0,
    analysisError: false
  },

  onLoad() {
    this._skipFirstShow = true
    this.loadRecords()
  },

  onShow() {
    if (this._skipFirstShow) { this._skipFirstShow = false; return }
    this.loadRecords()
  },

  onUnload() {
    this._requestId = (this._requestId || 0) + 1
  },

  // 加载打卡记录：按当前窗口请求，不再用 from=2000-01-01 拉全量后本地截窗
  loadRecords() {
    const requestId = this._requestId = (this._requestId || 0) + 1

    const rangeDays = normalizeRange(this.data.rangeDays)
    const { from, to } = getWindowRange(rangeDays, new Date())

    this.setData({
      loading: true,
      records: [],
      totalDays: 0,
      continuousDays: 0,
      trendData: [],
      distributionData: [],
      analysisTotal: 0,
      missingDays: 0,
      error: false,
      analysisError: false,
      windowFrom: from,
      windowTo: to
    })

    return request({
      url: `/api/emotions/checkins?from=${from}&to=${to}`,
      method: 'GET',
      showLoading: false,
      showError: false
    })
      .then((data) => {
        if (requestId !== this._requestId) return
        const payload = data || {}
        const items = Array.isArray(payload.items) ? payload.items : []

        const emotionLabels = {}
        EMOTIONS.forEach((item) => {
          emotionLabels[item.code] = item.label
        })

        // 整理窗口内的历史记录
        const records = items.map((item) => {
          const emotionText = emotionLabels[item.emotion] || '情绪打卡'
          const intensity = Number(item.intensity)
          const intensityText =
            Number.isFinite(intensity) && intensity >= 1 && intensity <= 5
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

        // 契约 total 是本次区间条数，不是历史累计；streakDays 才是全局连续天数
        const analysis = buildAnalysis(items, rangeDays, new Date())

        this.setData({
          totalDays: Number(payload.total) || 0,
          continuousDays: Number(payload.streakDays) || 0,
          records,
          rangeDays: analysis.rangeDays,
          trendData: analysis.trendData,
          distributionData: analysis.distributionData,
          analysisTotal: analysis.analysisTotal,
          missingDays: analysis.missingDays,
          analysisError: false
        }, () => {
          if (analysis.hasData) this.drawTrendChart()
        })
      })
      .catch(() => {
        if (requestId !== this._requestId) return

        // 请求失败显示错误态 + 重试，不把失败静默当成「0 条记录」
        this.setData({ error: true, analysisError: true })

        wx.showToast({
          title: '记录加载失败',
          icon: 'none'
        })
      })
      .finally(() => {
        if (requestId === this._requestId) this.setData({ loading: false })
      })
  },

  // 切换近 7 天 / 近 30 天：必须按新窗口重新请求，不能复用上一次的 items
  changeRange(e) {
    const rangeDays = normalizeRange(Number(e.currentTarget.dataset.range))
    if (rangeDays === this.data.rangeDays) return

    this.setData({
      rangeDays,
      trendData: [],
      distributionData: [],
      analysisTotal: 0,
      missingDays: 0
    }, () => {
      this.loadRecords()
    })
  },

  // 绘制情绪强度折线图：纵轴固定 1–5，断签处留空断开、不补 0
  drawTrendChart() {
    const { trendData, analysisTotal } = this.data

    if (!analysisTotal || !trendData.length) return

    const ctx = wx.createCanvasContext('emotionTrendCanvas', this)

    const width = 345
    const left = 32
    const right = width - 10
    const top = 15
    const bottom = 145

    const chartWidth = right - left
    const chartHeight = bottom - top

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

    const getX = (index) => {
      if (trendData.length === 1) return left + chartWidth / 2
      return left + (index / (trendData.length - 1)) * chartWidth
    }

    const getY = (value) => bottom - ((value - 1) / 4) * chartHeight

    // 分段绘制：intensity 为 null 的日期直接断开，避免把「没记录」画成强度 0
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
      segment.push({ x: getX(index), y: getY(item.intensity) })
    })
    drawSegment()

    // 数据点按当天情绪着色（六种情绪固定色）
    trendData.forEach((item, index) => {
      if (item.intensity === null) return

      const x = getX(index)
      const y = getY(item.intensity)
      const emotion = EMOTIONS.find(
        (emotionItem) => emotionItem.code === item.emotion
      )
      const pointColor = emotion ? emotion.color : '#4a69bd'

      ctx.beginPath()
      ctx.arc(x, y, 5, 0, Math.PI * 2)
      ctx.setFillStyle(pointColor)
      ctx.fill()

      ctx.setStrokeStyle('#ffffff')
      ctx.setLineWidth(2)
      ctx.stroke()
    })

    const step = Math.max(1, Math.ceil(trendData.length / 6))

    ctx.setFontSize(9)
    ctx.setFillStyle('#98a2b3')

    trendData.forEach((item, index) => {
      if (index % step !== 0 && index !== trendData.length - 1) return
      ctx.fillText(item.label, getX(index) - 10, 165)
    })

    ctx.draw()
  },

  // 历史记录日期格式化
  formatRecordDate(dateString) {
    const parts = String(dateString).slice(0, 10).split('-')
    if (parts.length !== 3) return dateString
    return `${Number(parts[1])}月${Number(parts[2])}日`
  },

  // 重新加载
  retryLoad() {
    this.loadRecords()
  }
})
