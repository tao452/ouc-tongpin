
const { request } = require('../../utils/request.js')

Page({
  data: {
    totalDays: 0,
    continuousDays: 0,
    records: [],
    loading: false,
    error: false
  },

  onLoad() {
    this.loadRecords()
  },

  onShow() {
    // 从其他页面返回时刷新记录
    this.loadRecords()
  },

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

        const emotionLabels = {
          HAPPY: '开心',
          CALM: '平静',
          ANXIOUS: '焦虑',
          LONELY: '孤独',
          IRRITABLE: '烦躁',
          DOWN: '低落'
        }

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

        this.setData({
          totalDays: Number(data.total) || 0,
          continuousDays: Number(data.streakDays) || 0,
          records
        })
      })
      .catch((err) => {
        console.error('获取打卡记录失败：', err)
        this.setData({
          error: true
        })

        wx.showToast({
          title: '记录加载失败',
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({
          loading: false
        })
      })
  },

  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  },

  formatRecordDate(dateString) {
    const parts = dateString.split('-')

    if (parts.length !== 3) return dateString

    return `${Number(parts[1])}月${Number(parts[2])}日`
  },

  retryLoad() {
    this.loadRecords()
  }
})
