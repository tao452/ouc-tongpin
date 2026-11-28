const { request } = require('../../../utils/request.js')

const PAGE_SIZE = 10

// 后端返回的是 buddy_demand 既有列，这里补齐卡片渲染所需的展示字段。
function normaliseBackendItem(item) {
  const distance = typeof item.distance === 'number' ? item.distance : null

  return {
    id: item.id,
    title: item.title || item.scene || '搭子需求',
    description: item.description || '',
    category: item.category || '其他',
    scene: item.scene || '',
    time: item.time || '时间待定',
    location: item.location || '地点待定',
    distance,
    distanceText: distance === null ? '距离未测' : `距离 ${distance} km`,
    tags: Array.isArray(item.tags) ? item.tags : [],
    peopleCount: item.peopleCount == null ? 1 : item.peopleCount,
    publishTime: item.publishTime || '',
    publishText: item.publishText || '发布时间未知',
    status: item.status || 'OPEN'
  }
}

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
    // 启动时请求后端广场接口；失败或空库时回退 Mock，并显式标注数据来源。
    allNeeds: [],
    filteredNeeds: [],
    visibleNeeds: [],

    dataSource: 'loading',
    demoNotice: '',
    noticeLevel: 'info',
    cursorId: 0,
    hasNextPage: true,
    loadingMore: false,

    searchKeyword: '',
    activeCategory: '全部',
    activeScene: '全部',
    activeTime: '全部',
    activeDistance: '不限',
    activeTag: '全部',
    activeSort: '最新发布',

    categories: ['全部', '学习交流', '生活兴趣', '其他'],
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
  },

  // 首次进入和从发布页返回都会触发，重新拉第一页，保证新需求立即可见。
  onShow() {
    this.fetchSquare(false)
  },

  // 游标分页：首次 cursorId=0，后续用上一页最后一条的 id 作游标。
  fetchSquare(append) {
    if (append && (!this.data.hasNextPage || this.data.loadingMore)) {
      return Promise.resolve()
    }
    this.setData({ loadingMore: append })

    return request({
      url: '/api/match/needs/square',
      method: 'POST',
      data: {
        cursorId: append ? this.data.cursorId : 0,
        size: PAGE_SIZE,
        radius: 5000
      },
      showLoading: !append
    }).then(res => {
      const rows = Array.isArray(res && res.data) ? res.data : []

      // 后端可达但确实没有需求：显示真实空状态，不再拿示例数据冒充。
      if (!rows.length && !append) {
        this.setData({
          allNeeds: [],
          filteredNeeds: [],
          visibleNeeds: [],
          cursorId: 0,
          hasNextPage: false,
          dataSource: 'empty',
          demoNotice: '',
          loadingMore: false
        })
        return
      }

      const items = rows.map(normaliseBackendItem)
      const allNeeds = append ? this.data.allNeeds.concat(items) : items
      const lastId = items.length ? items[items.length - 1].id : this.data.cursorId

      this.setData({
        allNeeds,
        cursorId: lastId,
        hasNextPage: items.length === PAGE_SIZE,
        dataSource: 'backend',
        demoNotice: '',
        noticeLevel: 'info',
        loadingMore: false
      }, () => this.applyFilters())
    }).catch(() => {
      // 只有请求真正失败才回退示例数据，并用醒目样式标红提示。
      this.useMock('后端查询不可用，当前展示示例数据（非真实需求）', 'error')
    })
  },

  useMock(notice, level) {
    this.setData({
      allNeeds: mockNeeds.slice(),
      cursorId: 0,
      hasNextPage: false,
      dataSource: 'mock',
      demoNotice: notice,
      noticeLevel: level || 'info',
      loadingMore: false
    }, () => this.applyFilters())
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

  // 清空搜索关键词
  onClearSearch() {
    this.setData({ searchKeyword: '' })
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
      if (activeDistance !== '不限') {
        const maxDistance = activeDistance === '1km内' ? 1
          : activeDistance === '3km内' ? 3 : 5
        // 未传坐标时 distance 为 null，不能把它当作 0 km 参与筛选。
        distanceMatch = typeof item.distance === 'number' && item.distance <= maxDistance
      }

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
      // 兼容 Mock 的 "YYYY-MM-DD HH:mm" 与后端的 "YYYY-MM-DDTHH:mm:ss"。
      result.sort((a, b) => {
        const ta = Date.parse(String(a.publishTime || '').replace(/-/g, '/'))
        const tb = Date.parse(String(b.publishTime || '').replace(/-/g, '/'))
        return (Number.isNaN(tb) ? 0 : tb) - (Number.isNaN(ta) ? 0 : ta)
      })
    } else if (activeSort === '距离最近') {
      result.sort((a, b) =>
        (a.distance == null ? Infinity : a.distance) -
        (b.distance == null ? Infinity : b.distance)
      )
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

  // 手动加载 1000 条压测数据，用于验证虚拟列表滚动性能；明确标注非真实需求。
  loadPerfTestData() {
    this.setData({
      allNeeds: testNeeds,
      dataSource: 'mock',
      demoNotice: '当前为 1000 条压测数据，非真实需求',
      hasNextPage: false
    })
    this.applyFilters()
  },

  // 下拉刷新：回到第一页重新拉取
  onPullDownRefresh() {
    this.fetchSquare(false).finally(() => wx.stopPullDownRefresh())
  },

  // 触底加载下一游标页；Mock 模式没有服务端分页。
  onReachBottom() {
    if (this.data.dataSource === 'backend') {
      this.fetchSquare(true)
    }
  },

  // 点击需求卡片
  onNeedTap(e) {
    const id = e.detail && e.detail.id
    wx.showToast({
      title: '需求详情页暂未开发',
      icon: 'none'
    })
    console.log('[plaza/list] need tapped:', id)
  }
})
