
Page({
    data: {
      success: false,
      checkinDate: '',
      errorReason: '网络连接异常',
      errorSuggestion: '请检查网络后重新提交'
    },

    onLoad(options) {
      const success = options.success === 'true'

      this.setData({
        success,
        checkinDate: this.getToday()
      })

      if (!success) {
        this.setData({
          errorReason: options.reason
            ? decodeURIComponent(options.reason)
            : '网络连接异常',
          errorSuggestion: options.suggestion
            ? decodeURIComponent(options.suggestion)
            : '请检查网络后重新提交'
        })
      }
    },

    // 获取今天的日期
    getToday() {
      const date = new Date()
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')

      return `${year}年${month}月${day}日`
    },

    // 返回上一页
    goBack() {
      wx.navigateBack({
        delta: 1
      })
    },

    
    // 成功后返回打卡首页
    goHome() {
        wx.switchTab({
        url: '/pages/checkin/index'
        })
    },

    // 失败后返回填写页
    retry() {
      wx.navigateBack({
        delta: 1
      })
    }
  })
