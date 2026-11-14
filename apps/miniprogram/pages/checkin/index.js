const { request } = require('../../utils/request.js')

Page({
    data: {
      currentDate: '',
      weekDay: '',
      hasCheckedIn: false,
      continuousDays: 0,
      totalDays: 0
    },

    onLoad() {
      this.setCurrentDate()
      this.loadStatus()
    },

    onShow() {
      // 每次返回打卡首页时刷新日期与真实打卡状态
      this.setCurrentDate()
      this.loadStatus()
    },

    // 读取后端打卡数据，修复「永远显示今日未打卡、连续/累计都是 0」的问题
    loadStatus() {
      const to = this.formatDate(new Date())

      request({
        url: `/api/emotions/checkins?from=2000-01-01&to=${to}`,
        method: 'GET',
        showLoading: false
      })
        .then((data) => {
          const items = Array.isArray(data.items) ? data.items : []

          this.setData({
            hasCheckedIn: items.some((item) => item.checkinDate === to),
            continuousDays: Number(data.streakDays) || 0,
            totalDays: Number(data.total) || 0
          })
        })
        .catch((err) => {
          // request.js 已统一提示，这里只记录，避免打断演示
          console.warn('打卡状态刷新失败：', err)
        })
    },

    formatDate(date) {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')

      return `${year}-${month}-${day}`
    },

    setCurrentDate() {
      const date = new Date()
      const month = date.getMonth() + 1
      const day = date.getDate()
      const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

      this.setData({
        currentDate: `${month}月${day}日`,
        weekDay: weekDays[date.getDay()]
      })
    },

    goToForm() {
      if (this.data.hasCheckedIn) return

      wx.navigateTo({
        url: '/pages/checkin/form'
      })
    },

    goToRule() {
        wx.navigateTo({
          url: '/pages/checkin/rule'
        })
      },

    goToRecords() {
      wx.navigateTo({
        url: '/pages/checkin/records'
      })
    }
  })
