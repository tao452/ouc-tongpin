const app = getApp()

Page({
  data: {
    loginReady: false,
    loginSuccess: false,
    needStudentVerify: false,
    userId: ''
  },

  onShow() {
    this.syncLoginState()
  },

  // 同步全局登录状态
  syncLoginState() {
    const globalData = app.globalData

    if (!globalData.loginReady && app.loginPromise) {
      app.loginPromise.then(() => {
        this.updateLoginState()
      })
      return
    }

    this.updateLoginState()
  },

  // 更新页面上的登录状态
  updateLoginState() {
    const globalData = app.globalData
    const userInfo = globalData.userInfo || {}

    this.setData({
      loginReady: globalData.loginReady,
      loginSuccess: !!globalData.token,
      needStudentVerify: !!userInfo.needStudentVerify,
      userId: userInfo.userId || ''
    })
  },

  // 跳转到打卡 TabBar 页面
  goCheckin() {
    wx.switchTab({
      url: '/pages/checkin/index'
    })
  },

  // 跳转到树洞 TabBar 页面；树洞页已接入真实发布 / 列表接口
  goTreehole() {
    wx.switchTab({
      url: '/pages/treehole/index'
    })
  },

  // 跳转到学号认证页面
  goStudentVerify() {
    wx.navigateTo({
      url: '/pages/student-verify/index'
    })
  },

  // 跳转到打卡日历页面
  goCalendar() {
    wx.navigateTo({
      url: '/pages/checkin-calendar/checkin-calendar'
    })
  },

  // 跳转到个人资料页面
  goProfile() {
    wx.navigateTo({
      url: '/pages/profile/profile'
    })
  }
})
