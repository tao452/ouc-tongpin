
const mockNeeds = [
    {
      id: 1,
      title: '一起准备计算机考研',
      description: '想找一个自律的伙伴，一起复习专业课和数学，互相监督。',
      category: '学习交流',
      scene: '考研学习',
      time: '工作日',
      distance: 0.8,
      location: '西海岸校区图书馆',
      tags: ['考研', '互相监督'],
      peopleCount: 2,
      publishTime: '2026-11-25 09:30',
      publishText: '今天发布'
    },
    {
      id: 2,
      title: '周末一起打羽毛球',
      description: '寻找羽毛球搭子，水平不限，主要是锻炼身体。',
      category: '生活兴趣',
      scene: '运动健身',
      time: '周末',
      distance: 1.2,
      location: '体育馆',
      tags: ['羽毛球', '运动'],
      peopleCount: 3,
      publishTime: '2026-11-24 18:20',
      publishText: '昨天发布'
    },
    {
      id: 3,
      title: '寻找英语口语练习搭子',
      description: '希望每周约几次练习英语口语，可以一起打卡。',
      category: '学习交流',
      scene: '语言学习',
      time: '工作日',
      distance: 2.1,
      location: '教学楼附近',
      tags: ['英语', '口语'],
      peopleCount: 2,
      publishTime: '2026-11-24 14:00',
      publishText: '昨天发布'
    },
    {
      id: 4,
      title: '周末一起去海边散步',
      description: '天气好的话想去海边走走，拍拍照片。',
      category: '生活兴趣',
      scene: '休闲娱乐',
      time: '周末',
      distance: 3.5,
      location: '石老人海水浴场',
      tags: ['散步', '拍照'],
      peopleCount: 4,
      publishTime: '2026-11-23 16:40',
      publishText: '2天前'
    },
    {
      id: 5,
      title: '找人一起做课程项目',
      description: '希望找一位同学一起完成课程设计，认真沟通、合理分工。',
      category: '学习交流',
      scene: '课程项目',
      time: '工作日',
      distance: 0.5,
      location: '教学楼',
      tags: ['课程设计', '编程'],
      peopleCount: 2,
      publishTime: '2026-11-23 10:15',
      publishText: '2天前'
    },
    {
      id: 6,
      title: '寻找健身搭子',
      description: '想规律健身，寻找可以一起去健身房的伙伴。',
      category: '生活兴趣',
      scene: '运动健身',
      time: '工作日',
      distance: 1.8,
      location: '校内健身房',
      tags: ['健身', '运动'],
      peopleCount: 2,
      publishTime: '2026-11-22 19:00',
      publishText: '3天前'
    },
    {
      id: 7,
      title: '一起准备期末考试',
      description: '希望找同学一起复习，整理重点，互相答疑。',
      category: '学习交流',
      scene: '考试复习',
      time: '周末',
      distance: 0.6,
      location: '图书馆',
      tags: ['期末复习', '学习'],
      peopleCount: 3,
      publishTime: '2026-11-22 11:30',
      publishText: '3天前'
    },
    {
      id: 8,
      title: '周末寻找桌游搭子',
      description: '想约几位同学一起玩桌游，轻松认识新朋友。',
      category: '生活兴趣',
      scene: '休闲娱乐',
      time: '周末',
      distance: 2.6,
      location: '学生生活区',
      tags: ['桌游', '交友'],
      peopleCount: 4,
      publishTime: '2026-11-21 15:20',
      publishText: '4天前'
    },
    {
      id: 9,
      title: '一起练习算法题',
      description: '想找伙伴一起刷算法题，交流解题思路。',
      category: '学习交流',
      scene: '编程学习',
      time: '工作日',
      distance: 1.0,
      location: '信息学部',
      tags: ['算法', '编程'],
      peopleCount: 2,
      publishTime: '2026-11-21 09:00',
      publishText: '4天前'
    },
    {
      id: 10,
      title: '寻找摄影爱好者',
      description: '平时喜欢拍照，希望认识喜欢摄影的朋友。',
      category: '生活兴趣',
      scene: '兴趣爱好',
      time: '周末',
      distance: 4.2,
      location: '校园内',
      tags: ['摄影', '兴趣'],
      peopleCount: 3,
      publishTime: '2026-11-20 20:10',
      publishText: '5天前'
    }
  ]

  //const PAGE_SIZE = 5
  // 虚拟列表：卡片高度缓存（单位：px）
  //const itemHeightMap = {}

  const testNeeds = Array.from({ length: 1000 }, (_, index) => {
    const source = mockNeeds[index % mockNeeds.length]

    return {
      ...source,
      id: `test-${index + 1}`,
      title: `测试需求 ${index + 1}`
    }
  })


const ESTIMATED_ITEM_HEIGHT = 220 // 未测量卡片的预估高度，单位 px
const OVERSCAN = 2 // 上下各多渲染 2 张卡片

Page({
  data: {
    allNeeds: testNeeds,
    filteredNeeds: [],
    visibleNeeds: [],

    searchKeyword: '',
    activeCategory: '全部',
    activeScene: '全部',
    activeTime: '全部',
    activeDistance: '不限',
    activeTag: '全部',
    activeSort: '最新发布',

    categories: ['全部', '学习交流', '生活兴趣'],
    scenes: ['全部', '考研学习', '运动健身', '语言学习', '休闲娱乐', '课程项目', '考试复习', '编程学习', '兴趣爱好'],
    times: ['全部', '工作日', '周末'],
    distances: ['不限', '1km内', '3km内', '5km内'],
    tags: ['全部', '学习', '运动', '编程', '交友', '兴趣'],
    sortOptions: ['最新发布', '距离最近', '人数最多'],

    windowStart: 0,
    windowEnd: 0,
    topSpacerHeight: 0,
    bottomSpacerHeight: 0,
    hasMore: false
  },

  onLoad() {
    this.itemHeightMap = {}
    this.listTop = 0
    this.windowHeight = 600
    this.scrollTop = 0
    this.isMeasuring = false
    this.applyFilters()
  },

  onReady() {
    const systemInfo = wx.getSystemInfoSync()
    this.windowHeight = systemInfo.windowHeight

    this.getListTop()
  },

  // 获取需求列表在页面中的绝对位置
  getListTop() {
    this.createSelectorQuery()
      .select('.need-list')
      .boundingClientRect(rect => {
        if (!rect) return

        this.listTop = rect.top + this.scrollTop
        this.updateVirtualWindow()
      })
      .exec()
  },

  // 页面滚动
  onPageScroll(e) {
    this.scrollTop = e.scrollTop
    this.updateVirtualWindow()


  },

  // 获取卡片高度，未测量时使用预估高度
  getItemHeight(item) {
    return this.itemHeightMap[item.id] || ESTIMATED_ITEM_HEIGHT
  },

  // 计算指定范围之前的总高度
  getTotalHeight(start, end) {
    const list = this.data.filteredNeeds
    let total = 0

    for (let i = start; i < end; i++) {
      total += this.getItemHeight(list[i])
    }

    return total
  },

  // 根据滚动位置计算需要渲染的卡片窗口
  updateVirtualWindow() {
    const list = this.data.filteredNeeds
    if (!list.length) {
      this.setData({
        visibleNeeds: [],
        windowStart: 0,
        windowEnd: 0,
        topSpacerHeight: 0,
        bottomSpacerHeight: 0,
        hasMore: false
      })
      return
    }

    const relativeScrollTop = Math.max(
      0,
      this.scrollTop - this.listTop
    )

    const startOffset = Math.max(
      0,
      relativeScrollTop - this.windowHeight * 0.5
    )

    const endOffset =
      relativeScrollTop + this.windowHeight * 1.5

    let start = 0
    let end = 0
    let currentOffset = 0

    while (
      start < list.length &&
      currentOffset + this.getItemHeight(list[start]) < startOffset
    ) {
      currentOffset += this.getItemHeight(list[start])
      start++
    }

    end = start
    while (
      end < list.length &&
      currentOffset < endOffset
    ) {
      currentOffset += this.getItemHeight(list[end])
      end++
    }

    start = Math.max(0, start - OVERSCAN)
    end = Math.min(list.length, end + OVERSCAN)

    const topHeight = this.getTotalHeight(0, start)
    const bottomHeight = this.getTotalHeight(end, list.length)

    const visibleNeeds = list.slice(start, end)

    if (
      start === this.data.windowStart &&
      end === this.data.windowEnd &&
      topHeight === this.data.topSpacerHeight &&
      bottomHeight === this.data.bottomSpacerHeight
    ) {
      return
    }

    this.setData({
      visibleNeeds,
      windowStart: start,
      windowEnd: end,
      topSpacerHeight: topHeight,
      bottomSpacerHeight: bottomHeight,
      hasMore: end < list.length
    }, () => {
      this.measureVisibleItems()
    })
  },

  // 测量当前渲染出来的卡片高度
  measureVisibleItems() {
    if (this.isMeasuring) return
    this.isMeasuring = true

    this.createSelectorQuery()
      .selectAll('.virtual-card')
      .fields({
        dataset: true,
        size: true
      })
      .exec(result => {
        this.isMeasuring = false

        const cards = result && result[0]
        if (!cards || !cards.length) return

        let changed = false

        cards.forEach(card => {
          const id = card.dataset.id
          const height = card.height

          if (!id || !height) return

          if (
            Math.abs((this.itemHeightMap[id] || 0) - height) > 1
          ) {
            this.itemHeightMap[id] = height
            changed = true
          }
        })

        if (changed) {
          this.updateVirtualWindow()
        }
      })
  },

  // 搜索关键词
  onSearchInput(e) {
    this.setData({
      searchKeyword: e.detail.value.replace(/\s+/g, '')
    })
    this.applyFilters()
  },

  // 切换分类
  onCategoryChange(e) {
    this.setData({
      activeCategory: e.currentTarget.dataset.value
    })
    this.applyFilters()
  },

  // 切换场景
  onSceneChange(e) {
    const index = Number(e.detail.value)

    this.setData({
      activeScene: this.data.scenes[index]
    })
    this.applyFilters()
  },
  // 切换时间
  onTimeChange(e) {
    const index = Number(e.detail.value)

    this.setData({
      activeTime: this.data.times[index]
    })
    this.applyFilters()
  },
  // 切换距离
  onDistanceChange(e) {
    const index = Number(e.detail.value)

    this.setData({
      activeDistance: this.data.distances[index]
    })
    this.applyFilters()
  },
  // 切换标签
  onTagChange(e) {
    this.setData({
      activeTag: e.currentTarget.dataset.value
    })
    this.applyFilters()
  },

  // 切换排序
  onSortChange(e) {
    this.setData({
      activeSort: e.currentTarget.dataset.value
    })
    this.applyFilters()
  },

  // 筛选、排序
  applyFilters() {
    const {
      allNeeds,
      searchKeyword,
      activeCategory,
      activeScene,
      activeTime,
      activeDistance,
      activeTag,
      activeSort
    } = this.data

    let result = allNeeds.filter(item => {
      const keyword = searchKeyword.replace(/\s+/g, '')

      const keywordMatch = !keyword ||
        item.title.replace(/\s+/g, '').includes(keyword) ||
        item.description.replace(/\s+/g, '').includes(keyword) ||
        item.tags.some(tag => tag.replace(/\s+/g, '').includes(keyword))

      const categoryMatch = activeCategory === '全部' ||
        item.category === activeCategory

      const sceneMatch = activeScene === '全部' ||
        item.scene === activeScene

      const timeMatch = activeTime === '全部' ||
        item.time === activeTime

      let distanceMatch = true
      if (activeDistance === '1km内') distanceMatch = item.distance <= 1
      if (activeDistance === '3km内') distanceMatch = item.distance <= 3
      if (activeDistance === '5km内') distanceMatch = item.distance <= 5

      const tagMatch = activeTag === '全部' ||
        item.tags.some(tag => tag.includes(activeTag))

      return keywordMatch &&
        categoryMatch &&
        sceneMatch &&
        timeMatch &&
        distanceMatch &&
        tagMatch
    })

    if (activeSort === '最新发布') {
      result.sort((a, b) =>
        new Date(b.publishTime.replace(/-/g, '/') + ':00').getTime() -
        new Date(a.publishTime.replace(/-/g, '/') + ':00').getTime()
      )
    } else if (activeSort === '距离最近') {
      result.sort((a, b) => a.distance - b.distance)
    } else if (activeSort === '人数最多') {
      result.sort((a, b) => b.peopleCount - a.peopleCount)
    }

    // 筛选结果变化后，重新计算虚拟列表
    this.itemHeightMap = {}

    this.setData({
      filteredNeeds: result,
      visibleNeeds: [],
      windowStart: 0,
      windowEnd: 0,
      topSpacerHeight: 0,
      bottomSpacerHeight: 0,
      hasMore: result.length > 0
    }, () => {
      this.scrollTop = 0

      wx.pageScrollTo({
        scrollTop: 0,
        duration: 0,
        complete: () => {
          this.getListTop()
        }
      })
    })
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.applyFilters()
    wx.stopPullDownRefresh()
  },

  // 点击需求卡片
  onNeedTap() {
    //const id = e.detail.id

    wx.showToast({
      title: '需求详情页暂未开发',
      icon: 'none'
    })
  }
})
