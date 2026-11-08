
const { request } = require('../../utils/request.js')

const {
  FALLBACK_WORDS,
  normalizeWords,
  normalizeScale,
  validateCheckin,
  buildCheckinPayload
} = require('../../utils/checkin.js')

const DRAFT_KEY = 'checkinDraft'

Page({
  data: {
    currentDate: '',
    words: [],
    selectedEmotion: '',
    intensity: 3,
    intensityMin: 1,
    intensityMax: 5,
    note: '',
    submitting: false
  },

  onLoad() {
    this.setCurrentDate()
    this.restoreDraft()
    this.loadWords()
  },

  // 设置当前日期和星期
  setCurrentDate() {
    const date = new Date()
    const weekDays = [
      '星期日',
      '星期一',
      '星期二',
      '星期三',
      '星期四',
      '星期五',
      '星期六'
    ]

    this.setData({
      currentDate: `${date.getMonth() + 1}月${date.getDate()}日 ${weekDays[date.getDay()]}`
    })
  },

  // 恢复本地草稿
  restoreDraft() {
    try {
      const draft = wx.getStorageSync(DRAFT_KEY)

      if (draft) {
        this.setData({
          selectedEmotion: draft.selectedEmotion || '',
          intensity: draft.intensity || 3,
          note: draft.note || ''
        })

        wx.showToast({
          title: '已恢复上次草稿',
          icon: 'none'
        })
      }
    } catch (err) {
      console.error('恢复草稿失败：', err)
    }
  },

  // 保存本地草稿
  saveDraft() {
    try {
      wx.setStorageSync(DRAFT_KEY, {
        selectedEmotion: this.data.selectedEmotion,
        intensity: this.data.intensity,
        note: this.data.note
      })
    } catch (err) {
      console.error('保存草稿失败：', err)
    }
  },

  // 清除本地草稿
  clearDraft() {
    try {
      wx.removeStorageSync(DRAFT_KEY)
    } catch (err) {
      console.error('清除草稿失败：', err)
    }
  },

  // 获取情绪词表
  loadWords() {
    request({
      url: '/api/emotions/words',
      method: 'GET',
      showLoading: false
    })
      .then((data) => {
        const words = normalizeWords(data)
        const scale = normalizeScale(data)

        this.setData({
          words,
          intensityMin: scale.min,
          intensityMax: scale.max
        })

        console.log('情绪词表加载成功：', words)
      })
      .catch((err) => {
        console.error('获取情绪词表失败，使用本地兜底：', err)

        this.setData({
          words: FALLBACK_WORDS,
          intensityMin: 1,
          intensityMax: 5
        })

        wx.showToast({
          title: '已使用本地情绪词',
          icon: 'none'
        })
      })
  },

  // 选择情绪
  selectEmotion(e) {
    const emotion = e.currentTarget.dataset.code

    this.setData({
      selectedEmotion: emotion
    }, () => {
      this.saveDraft()
    })
  },

  // 修改情绪强度
  onIntensityChange(e) {
    this.setData({
      intensity: Number(e.detail.value)
    }, () => {
      this.saveDraft()
    })
  },

  // 输入备注
  onNoteInput(e) {
    this.setData({
      note: e.detail.value
    }, () => {
      this.saveDraft()
    })
  },

  // 提交打卡
  submitCheckin() {
    const {
      selectedEmotion,
      intensity,
      note,
      submitting
    } = this.data

    if (submitting) return

    // 使用统一校验逻辑
    const validation = validateCheckin({
      emotion: selectedEmotion,
      intensity,
      note
    })

    if (!validation.ok) {
      wx.showToast({
        title: validation.message,
        icon: 'none'
      })
      return
    }

    this.setData({
      submitting: true
    })

    // 使用统一的数据组装逻辑
    const payload = buildCheckinPayload({
      emotion: selectedEmotion,
      intensity,
      note
    })

    request({
      url: '/api/emotions/checkins',
      method: 'POST',
      data: payload,
      showLoading: false
    })
      .then((data) => {
        console.log('打卡成功：', data)

        // 提交成功后清除草稿
        this.clearDraft()

        wx.navigateTo({
          url: '/pages/checkin/result?success=true'
        })
      })
      .catch((err) => {
        console.error('提交打卡失败：', err)

        // 提交失败时保留草稿
        const reason = err && err.message
          ? err.message
          : '网络连接异常'

        wx.navigateTo({
          url: `/pages/checkin/result?success=false&reason=${encodeURIComponent(reason)}&suggestion=${encodeURIComponent('请检查网络后重新提交')}`
        })
      })
      .finally(() => {
        this.setData({
          submitting: false
        })
      })
  }
})
