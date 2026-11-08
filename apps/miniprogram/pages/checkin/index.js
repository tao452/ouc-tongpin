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
    },

    onShow() {
      // 每次返回打卡首页时刷新日期
      this.setCurrentDate()
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
