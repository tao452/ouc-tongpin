Page({
    data: {
      title: '我的',
      userInfo: null,
      loginReady: false,
      loginSuccess: false,
      needStudentVerify: false
    },

    onShow() {
      this.syncUserInfo()
    },

    syncUserInfo() {
      const app = getApp()
      const globalData = app.globalData || {}
      const userInfo = globalData.userInfo || {}

      this.setData({
        loginReady: !!globalData.loginReady,
        loginSuccess: !!globalData.token,
        needStudentVerify: !!userInfo.needStudentVerify,
        userInfo
      })
    },

    goStudentVerify() {
      wx.navigateTo({
        url: '/pages/student-verify/index'
      })
    },

    goCheckinRecords() {
      wx.navigateTo({
        url: '/pages/checkin/records'
      })
    }
  })
