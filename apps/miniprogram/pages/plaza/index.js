Page({
  data: {
    title: '搭子广场',
    description: '发现志同道合的校园搭子',
    keyword: '',

    // 演示数据：仅用于展示卡片样式；需求列表 / 筛选接口属 V1.0 #12，当前未开放。
    // 页面已加「示例需求 · 演示数据」标注，不要把这些条目当成真实落库数据。
    needs: [
      {
        id: 1,
        scene: '自习',
        description: '寻找一起准备期末考试的自习搭子，互相监督，共同进步。',
        time: '工作日晚上',
        location: '图书馆',
        tags: ['考研', '互相监督'],
        people: '期望人数：2人',
        status: '示例'
      },
      {
        id: 2,
        scene: '运动',
        description: '想找伙伴一起打羽毛球，初学者也可以，主要是锻炼身体。',
        time: '周末下午',
        location: '学校体育馆',
        tags: ['羽毛球', '运动'],
        people: '期望人数：3人',
        status: '示例'
      },
      {
        id: 3,
        scene: '学习',
        description: '寻找一起练习英语口语的小伙伴，希望能够坚持打卡。',
        time: '每周三、周五',
        location: '线上或教学楼',
        tags: ['英语', '学习打卡'],
        people: '期望人数：2人',
        status: '示例'
      }
    ],

    filteredNeeds: []
  },

  onLoad() {
    this.setData({
      filteredNeeds: this.data.needs
    })
  },

  // 搜索需求
  onSearch(e) {
    const keyword = e.detail.value.trim()
    const filteredNeeds = this.data.needs.filter(item => {
      const content = [
        item.scene,
        item.description,
        item.time,
        item.location
      ].concat(item.tags).join('')

      return content.includes(keyword)
    })

    this.setData({
      keyword,
      filteredNeeds
    })
  },

  // 查看需求广场
  goToNeeds() {
    wx.showToast({
      title: '需求列表后续开放',
      icon: 'none'
    })
  },

  // 进入搭子匹配
  goToMatch() {
    wx.showToast({
      title: '搭子匹配功能后续开放',
      icon: 'none'
    })
  },

  // 进入发布页
  goToPublish() {
    wx.navigateTo({
      url: '/pages/plaza/publish/publish'
    })
  }
})
