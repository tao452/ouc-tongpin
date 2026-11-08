
const { request } = require('../../utils/request.js')

Page({
  data: {
    studentId: '',
    // 当前只保存本地临时图片路径，用于页面预览，不作为服务器图片 URL
    screenshotUrl: '',
    submitting: false
  },

  // 输入学号
  onStudentIdInput(e) {
    this.setData({
      studentId: e.detail.value
    })
  },

  // 选择教务系统截图
  chooseScreenshot() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath

        this.setData({
          screenshotUrl: tempFilePath
        })
      },
      fail: () => {
        wx.showToast({
          title: '未能选择图片',
          icon: 'none'
        })
      }
    })
  },

  // 提交学号认证
  submitVerify() {
    const { studentId, submitting } = this.data
    const trimmedStudentId = studentId.trim()

    if (submitting) return

    // 检查学号是否为空
    if (!trimmedStudentId) {
      wx.showToast({
        title: '请输入学号',
        icon: 'none'
      })
      return
    }

    // 检查学号是否为11位数字
    if (!/^\d{11}$/.test(trimmedStudentId)) {
      wx.showToast({
        title: '学号必须是11位数字',
        icon: 'none'
      })
      return
    }

    this.setData({
      submitting: true
    })

    request({
      url: '/api/auth/student-verify',
      method: 'POST',
      data: {
        studentId: trimmedStudentId
      },
      showLoading: false
    })
      .then((data) => {
        let message = '认证申请已提交，等待审核'

        if (data.status === 'VERIFIED') {
          message = '学号认证已通过'

          const app = getApp()

          if (app.globalData.userInfo) {
            app.globalData.userInfo.needStudentVerify = false
          }

        } else if (data.status === 'REJECTED') {
          message = data.reason || '认证未通过'
        } else if (data.status === 'PENDING') {
          message = '认证申请已提交，等待审核'
        }

        wx.showModal({
          title: '认证结果',
          content: message,
          showCancel: false
        })
      })
      .catch((err) => {
        let message = err.message || '提交失败，请稍后重试'

        if (err.statusCode === 409) {
          message = '该学号已绑定其他账号'
        }

        wx.showToast({
          title: message,
          icon: 'none'
        })
      })
      .finally(() => {
        this.setData({
          submitting: false
        })
      })
  }
})
