const { request } = require('./utils/request.js')
const { setToken } = require('./utils/storage.js')

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
      success: (res) => {
        if (!res.code) {
          console.error('获取微信登录凭证失败', res.errMsg)
          return
        }

        request({
          url: '/api/auth/login',
          method: 'POST',
          data: { code: res.code },
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

      fail: (err) => {
        console.error('微信登录调用失败', err)
      }
    })
  },

  globalData: {
    token: '',
    userInfo: null
  }
})
