const { request } = require('./utils/request.js')
const { setToken } = require('./utils/storage.js')

// 演示桩：游客模式（project.config.json 用 touristappid）或后端未接微信 code2session 时，
// wx.login 可能拿不到 code。US-33 正式实现后删除此常量与降级分支。
const DEMO_CODE = 'demo-wx-code'

App({
  onLaunch() {
    // 记录小程序运行期间的普通错误
    wx.onError((error) => {
      console.error('[全局错误]', error)
    })

    // 记录没有被处理的 Promise 异常
    wx.onUnhandledRejection((res) => {
      console.error('[未处理的 Promise 异常]', res.reason)
    })

    this.login()
  },

  login() {
    wx.login({
      success: (res) => this.signIn(res.code || DEMO_CODE),
      fail: () => this.signIn(DEMO_CODE)
    })
  },

  signIn(code) {
    request({
      url: '/api/auth/login',
      method: 'POST',
      data: { code },
      showLoading: false
    })
      .then((data) => {
        if (data.token) {
          setToken(data.token)
          this.globalData.token = data.token
        }

        this.globalData.userInfo = {
          userId: data.userId,
          isNewUser: data.isNewUser,
          needStudentVerify: data.needStudentVerify
        }

        console.log('登录接口调用成功')
      })
      .catch((err) => {
        console.error('登录请求失败', err)
      })
  },

  globalData: {
    token: '',
    userInfo: null
  }
})
