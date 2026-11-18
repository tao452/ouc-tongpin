const {request} = require('../../../utils/request')

Page({
  data: {
    sceneOptions: ['自习', '运动', '学习', '美食', '娱乐', '其他'],
    sceneIndex: -1,
    scene: '',

    today: '',
    date: '',
    time: '',

    location: {
      address: '',
      lat: null,
      lng: null
    },

    skillTags: [],
    tagInput: '',
    remark: '',

    submitting: false
  },

  onLoad() {
    const now = new Date()
    const today = this.formatDate(now)

    this.setData({
      today
    })
  },

  // 格式化日期
  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  },

  // 选择场景
  onSceneChange(e) {
    const index = Number(e.detail.value)

    this.setData({
      sceneIndex: index,
      scene: this.data.sceneOptions[index]
    })
  },

  // 选择日期
  onDateChange(e) {
    this.setData({
      date: e.detail.value
    })
  },

  // 选择时间
  onTimeChange(e) {
    this.setData({
      time: e.detail.value
    })
  },

  // 选择地点
  chooseLocation() {
    wx.chooseLocation({
      success: (res) => {
        this.setData({
          location: {
            address: res.address || res.name,
            lat: res.latitude,
            lng: res.longitude
          }
        })
      },
      fail: (err) => {
        console.error('地点选择失败，具体原因：', err)
        if (err.errMsg && err.errMsg.includes('cancel')) {
          return
        }

        wx.showToast({
          title: '地点选择失败，请重试',
          icon: 'none'
        })
      }
    })
  },

  // 输入技能标签
  onTagInput(e) {
    this.setData({
      tagInput: e.detail.value
    })
  },

  // 添加技能标签
  addTag() {
    const tag = this.data.tagInput.trim()

    if (!tag) {
      wx.showToast({
        title: '请输入标签内容',
        icon: 'none'
      })
      return
    }

    if (this.data.skillTags.length >= 5) {
      wx.showToast({
        title: '最多添加5个标签',
        icon: 'none'
      })
      return
    }

    if (this.data.skillTags.includes(tag)) {
      wx.showToast({
        title: '请勿重复添加标签',
        icon: 'none'
      })
      return
    }

    this.setData({
        skillTags: this.data.skillTags.concat(tag),
      tagInput: ''
    })
  },

  // 删除技能标签
  removeTag(e) {
    const index = Number(e.currentTarget.dataset.index)
    const skillTags = this.data.skillTags.slice()

    skillTags.splice(index, 1)

    this.setData({
      skillTags
    })
  },

  // 输入补充说明
  onRemarkInput(e) {
    this.setData({
      remark: e.detail.value
    })
  },

  // 表单校验
  validateForm() {
    const {
      scene,
      date,
      time,
      location
    } = this.data

    if (!scene) {
      wx.showToast({
        title: '请选择需求场景',
        icon: 'none'
      })
      return false
    }

    if (!date || !time) {
      wx.showToast({
        title: '请选择期望时间',
        icon: 'none'
      })
      return false
    }

    if (!location.address || location.lat === null || location.lng === null) {
      wx.showToast({
        title: '请选择活动地点',
        icon: 'none'
      })
      return false
    }

    return true
  },

  // 提交需求
  async submitNeed() {
    if (this.data.submitting) {
      return
    }

    if (!this.validateForm()) {
      return
    }

    const {
      scene,
      date,
      time,
      location,
      skillTags,
      remark
    } = this.data

    const requestData = {
      scene,
      time: new Date(`${date}T${time}:00`).toISOString(),
      location,
      skillTags,
      remark: remark.trim()
    }

    this.setData({
      submitting: true
    })

    try {
      const res = await request({
        url: '/api/match/needs',
        method: 'POST',
        data: requestData
      })

      wx.showToast({
        title: '发布成功',
        icon: 'success'
      })

      console.log('需求发布结果：', res)

      setTimeout(() => {
        wx.navigateBack()
      }, 1200)
    } catch (err) {
      console.error('需求发布失败：', err)

      wx.showToast({
        title: '发布失败，请稍后重试',
        icon: 'none'
      })
    } finally {
      this.setData({
        submitting: false
      })
    }
  }
})
