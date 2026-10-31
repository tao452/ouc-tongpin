const { request } = require('../../utils/request.js')

const WEEK = ['日', '一', '二', '三', '四', '五', '六']
const EMOTION_COLOR = {
  HAPPY: '#FFD93D',
  CALM: '#95E1D3',
  ANXIOUS: '#FF9F68',
  LONELY: '#A6B1E1',
  IRRITABLE: '#FF6B6B',
  DOWN: '#6C7A89'
}

Page({
  data: {
    week: WEEK,
    cells: [],
    year: 0,
    month: 0,
    checkedDates: {},
    streakDays: 0,
    total: 0,
    remindOn: false,
    remindTime: '21:00'
  },

  onLoad() {
    const now = new Date()
    this.setData({ year: now.getFullYear(), month: now.getMonth() + 1 })
    this.loadRemind()
    this.loadCheckins()
  },

  loadCheckins() {
    const { year, month } = this.data
    const mm = String(month).padStart(2, '0')
    const from = `${year}-${mm}-01`
    const to = `${year}-${mm}-31`
    request(`/api/emotions/checkins?from=${from}&to=${to}`, 'GET')
      .then((res) => {
        const map = {}
        ;(res.items || []).forEach((it) => { map[it.checkinDate] = it.emotion })
        this.setData({
          checkedDates: map,
          streakDays: res.streakDays || 0,
          total: res.total || 0
        })
        this.buildGrid()
      })
      .catch(() => {
        wx.showToast({ title: '加载失败，检查 Mock 地址', icon: 'none' })
      })
  },

  buildGrid() {
    const { year, month } = this.data
    const first = new Date(year, month - 1, 1).getDay()
    const days = new Date(year, month, 0).getDate()
    const cells = []
    for (let i = 0; i < first; i++) cells.push({ empty: true })
    for (let d = 1; d <= days; d++) {
      const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      const emotion = this.data.checkedDates[ds]
      cells.push({
        empty: false,
        day: d,
        date: ds,
        emotion,
        color: emotion ? EMOTION_COLOR[emotion] : ''
      })
    }
    this.setData({ cells })
  },

  prevMonth() { this.step(-1) },
  nextMonth() { this.step(1) },
  step(delta) {
    let { year, month } = this.data
    month += delta
    if (month < 1) { month = 12; year-- } else if (month > 12) { month = 1; year++ }
    this.setData({ year, month })
    this.loadCheckins()
  },

  toggleRemind(e) {
    this.setData({ remindOn: e.detail.value })
    wx.setStorageSync('remindOn', e.detail.value)
  },
  onTime(e) {
    this.setData({ remindTime: e.detail.value })
    wx.setStorageSync('remindTime', e.detail.value)
  },
  loadRemind() {
    this.setData({
      remindOn: wx.getStorageSync('remindOn') || false,
      remindTime: wx.getStorageSync('remindTime') || '21:00'
    })
  }
})
