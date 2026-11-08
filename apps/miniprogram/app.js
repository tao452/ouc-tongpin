const { request } = require('./utils/request.js')
const { setToken } = require('./utils/storage.js')

// 演示桩：游客模式或后端暂未接入微信 code2session 时使用
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

    // 保存登录 Promise，供页面等待登录结果
    this.loginPromise = this.login()
  },

  login() {
    return new Promise((resolve) => {
      wx.login({
        success: (res) => {
          const code = res.code || DEMO_CODE
          this.signIn(code).then(resolve)
        },

        fail: (err) => {
          console.error('wx.login 调用失败', err)
          this.signIn(DEMO_CODE).then(resolve)
        }
      })
    })
  },

  signIn(code) {
    return request({
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

        this.globalData.loginError = null

        console.log('登录接口调用成功')
        return data
      })
      .catch((err) => {
        console.error('登录请求失败', err)
        this.globalData.loginError = err
        return null
      })
      .finally(() => {
        this.globalData.loginReady = true
      })
  },

  globalData: {
    token: '',
    userInfo: null,
    loginReady: false,
    loginError: null
  }
})
