// index.js
const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'
const { request } = require('../../utils/request.js')
const { setToken, getToken } = require('../../utils/storage.js')

Page({
  data: {
    motto: 'Hello World',
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: '',
    },
    hasUserInfo: false,
    canIUseGetUserProfile: wx.canIUse('getUserProfile'),
    canIUseNicknameComp: wx.canIUse('input.type.nickname'),
  },

  bindViewTap() {
    wx.navigateTo({
      url: '../logs/logs'
    })
  },

  onChooseAvatar(e) {
    const { avatarUrl } = e.detail
    const { nickName } = this.data.userInfo
    this.setData({
      "userInfo.avatarUrl": avatarUrl,
      hasUserInfo: nickName && avatarUrl && avatarUrl !== defaultAvatarUrl,
    })
  },

  onInputChange(e) {
    const nickName = e.detail.value
    const { avatarUrl } = this.data.userInfo
    this.setData({
      "userInfo.nickName": nickName,
      hasUserInfo: nickName && avatarUrl && avatarUrl !== defaultAvatarUrl,
    })
  },

  mockLogin() {
    wx.login({
      success: (res) => {
        if (!res.code) {
          console.error('获取登录 code 失败：', res.errMsg)
          return
        }

        request({
          url: '/api/auth/login',
          method: 'POST',
          data: {
            code: res.code
          }
        })
          .then((data) => {
            if (data.token) {
              setToken(data.token)
              console.log('模拟登录成功，Token 已保存')
            }

            console.log('本地读取的 Token：', getToken() ? '已读取' : '未读取')
          })
          .catch((err) => {
            console.error('模拟登录失败：', err)
          })
      },

      fail: (err) => {
        console.error('wx.login 调用失败：', err)
      }
    })
  },

  getUserProfile() {
    wx.getUserProfile({
      desc: '展示用户信息',
      success: (res) => {
        this.setData({
          userInfo: res.userInfo,
          hasUserInfo: true
        })
      }
    })
  },
})
