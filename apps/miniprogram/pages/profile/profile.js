// US-35 维护个人资料、兴趣与技能标签（契约：PUT /api/user/profile）
const {
  LIMITS,
  EMPTY_PROFILE,
  normalizeProfile,
  validateProfile,
  parseTagInput,
  buildPayload,
} = require('../../utils/profile.js')
const { request } = require('../../utils/request.js')
const { getToken } = require('../../utils/storage.js')

const PROFILE_KEY = 'profile'

Page({
  data: {
    profile: normalizeProfile(EMPTY_PROFILE),
    interestInput: '',
    skillInput: '',
    bioLength: 0,
    limits: LIMITS,
    isEmpty: true,
  },

  onLoad() {
    const cached = wx.getStorageSync(PROFILE_KEY)
    this.applyProfile(normalizeProfile(cached))
  },

  applyProfile(profile) {
    this.setData({
      profile,
      bioLength: profile.bio.length,
      isEmpty:
        !profile.nickname &&
        !profile.bio &&
        profile.interestTags.length === 0 &&
        profile.skillTags.length === 0,
    })
  },

  onNicknameInput(e) {
    this.setData({ 'profile.nickname': e.detail.value })
  },

  onBioInput(e) {
    this.setData({
      'profile.bio': e.detail.value,
      bioLength: e.detail.value.length,
    })
  },

  onChooseAvatar(e) {
    this.setData({ 'profile.avatarUrl': e.detail.avatarUrl || '' })
  },

  onTagInput(e) {
    const key = e.currentTarget.dataset.field === 'interest' ? 'interestInput' : 'skillInput'
    this.setData({ [key]: e.detail.value })
  },

  addTag(e) {
    const isInterest = e.currentTarget.dataset.field === 'interest'
    const inputKey = isInterest ? 'interestInput' : 'skillInput'
    const field = isInterest ? 'interestTags' : 'skillTags'
    const incoming = parseTagInput(this.data[inputKey])
    if (incoming.length === 0) {
      wx.showToast({ title: '请先输入标签', icon: 'none' })
      return
    }
    const merged = [...this.data.profile[field], ...incoming]
    if (merged.length > LIMITS.tags) {
      wx.showToast({ title: `每类标签最多 ${LIMITS.tags} 个`, icon: 'none' })
    }
    const normalized = normalizeProfile({ ...this.data.profile, [field]: merged })
    this.setData({
      [`profile.${field}`]: normalized[field],
      [inputKey]: '',
    })
  },

  removeTag(e) {
    const { field, index } = e.currentTarget.dataset
    const key = field === 'interest' ? 'interestTags' : 'skillTags'
    const next = this.data.profile[key].slice()
    next.splice(Number(index), 1)
    this.setData({ [`profile.${key}`]: next })
  },

  onSave() {
    const result = validateProfile(this.data.profile)
    if (!result.valid) {
      wx.showToast({ title: result.errors[0], icon: 'none' })
      return
    }

    const payload = buildPayload(result.profile)
    // 先落本地，保证无后端 / 未登录时主流程也能完整走通一次
    wx.setStorageSync(PROFILE_KEY, payload)
    this.applyProfile(payload)

    if (!getToken()) {
      wx.showToast({ title: '已保存到本地，请登录后同步', icon: 'none' })
      return
    }

    request({ url: '/api/user/profile', method: 'PUT', data: payload })
      .then(() => {
        wx.showToast({ title: '资料已同步', icon: 'success' })
      })
      .catch(() => {
        wx.showToast({ title: '后端未就绪，已保存到本地', icon: 'none' })
      })
  },

  goLogin() {
    wx.showToast({ title: '请先在首页完成模拟登录', icon: 'none' })
  },
})
