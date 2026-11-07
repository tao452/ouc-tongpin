const { request } = require('../../utils/request.js')
const {
  FALLBACK_WORDS,
  normalizeWords,
  normalizeScale,
  validateCheckin,
  buildCheckinPayload
} = require('../../utils/checkin.js')

// US-01 每日情绪打卡：词表来自 GET /api/emotions/words，提交走 POST /api/emotions/checkins。
// 词表接口不可用时降级为本地兜底并在页面标明来源，不伪造接口数据。
Page({
  data: {
    words: FALLBACK_WORDS,
    source: '本地兜底',
    scale: { min: 1, max: 5 },
    levels: [1, 2, 3, 4, 5],
    emotion: '',
    intensity: 3,
    note: '',
    noteLength: 0,
    submitting: false,
    result: null
  },

  onLoad() {
    this.loadWords()
  },

  loadWords() {
    request({ url: '/api/emotions/words', method: 'GET', showLoading: false })
      .then((res) => {
        const scale = normalizeScale(res)
        const levels = []
        for (let i = scale.min; i <= scale.max; i++) levels.push(i)
        this.setData({
          words: normalizeWords(res),
          scale,
          levels,
          source: '后端 /api/emotions/words'
        })
      })
      .catch(() => {
        // request.js 已统一提示网络错误；这里只标明词表来源，避免把兜底数据当成接口返回。
        this.setData({ source: '本地兜底（后端词表不可用）' })
      })
  },

  onSelectEmotion(e) {
    this.setData({ emotion: e.currentTarget.dataset.code })
  },

  onSelectIntensity(e) {
    this.setData({ intensity: Number(e.currentTarget.dataset.value) })
  },

  onNoteInput(e) {
    const note = e.detail.value
    this.setData({ note, noteLength: note.length })
  },

  submit() {
    if (this.data.submitting) return
    const check = validateCheckin(this.data)
    if (!check.ok) {
      wx.showToast({ title: check.message, icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    request({
      url: '/api/emotions/checkins',
      method: 'POST',
      data: buildCheckinPayload(this.data)
    })
      .then((res) => {
        this.setData({ result: res || {}, submitting: false })
        wx.showToast({ title: '打卡成功', icon: 'success' })
      })
      .catch(() => {
        // 错误提示由 request.js 统一处理，这里只恢复按钮可用状态。
        this.setData({ submitting: false })
      })
  },

  goCalendar() {
    wx.navigateTo({ url: '/pages/checkin-calendar/checkin-calendar' })
  }
})
