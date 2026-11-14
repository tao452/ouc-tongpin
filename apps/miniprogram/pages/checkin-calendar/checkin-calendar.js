const { request } = require('../../utils/request.js')
const {
  WEEK,
  getMonthRange,
  shiftMonth,
  buildMonthGrid,
  normalizeCheckins
} = require('../../utils/calendar.js')

Page({
  data: {
    week: WEEK,
    cells: [],
    year: 0,
    month: 0,
    checkedDates: {},
    streakDays: 0,
    monthTotal: 0,
    loadError: false,
    remindOn: false,
    remindTime: '21:00'
  },

  onLoad() {
    const now = new Date()
    this._requestSeq = 0
    this.setData({ year: now.getFullYear(), month: now.getMonth() + 1 })
    this.loadRemind()
    this.loadCheckins()
  },

  loadCheckins() {
    const { year, month } = this.data
    const { from, to } = getMonthRange(year, month)
    // 快速连点翻月时，只接受最后一次请求的响应，避免旧月份数据盖住新月份。
    const seq = ++this._requestSeq

    this.setData({ loadError: false })

    request({ url: `/api/emotions/checkins?from=${from}&to=${to}`, method: 'GET' })
      .then((res) => {
        if (seq !== this._requestSeq) return

        const { checkedDates, streakDays, monthTotal } = normalizeCheckins(res)
        this.setData({ checkedDates, streakDays, monthTotal, loadError: false })
        this.buildGrid()
      })
      .catch(() => {
        if (seq !== this._requestSeq) return

        // request.js 已统一 toast；这里保留全局连续天数，只清掉本月打点，
        // 并显示页面内重试入口，避免用户只能看到一个空白日历。
        this.setData({
          checkedDates: {},
          monthTotal: 0,
          loadError: true
        })
        this.buildGrid()
      })
  },

  buildGrid() {
    const { year, month, checkedDates } = this.data
    this.setData({ cells: buildMonthGrid(year, month, checkedDates) })
  },

  goCheckin() {
    // 打卡首页是 tabBar 页，必须用 switchTab；
    // PR#59 重构后 /pages/checkin/checkin 已删除，此处指向 /pages/checkin/index。
    wx.switchTab({ url: '/pages/checkin/index' })
  },

  prevMonth() { this.step(-1) },
  nextMonth() { this.step(1) },
  step(delta) {
    const { year, month } = shiftMonth(this.data.year, this.data.month, delta)
    this.setData({ year, month })
    this.loadCheckins()
  },

  retryLoad() {
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
