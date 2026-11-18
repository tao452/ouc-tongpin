// US-05 / US-07：树洞发布、列表、情绪筛选、24h 焚毁提示。
// 后端 POST/GET /api/treehole/posts 已实装并接入内容审核，本页只做前端接线，
// 不复制词库逻辑、不本地判断敏感词，判定结果一律以后端状态码为准。

const { request } = require('../../utils/request.js')
const {
  MAX_CONTENT_LENGTH,
  EMOTION_TAGS,
  buildListQuery,
  buildPostPayload,
  failureMessage,
  nextCursor,
  normalizePosts,
  validatePost
} = require('../../utils/treehole.js')

const ALL_FILTER = { code: '', label: '全部' }

Page({
  data: {
    title: '匿名树洞',
    description: '在这里，说出那些不方便说的话。',
    filters: [ALL_FILTER].concat(EMOTION_TAGS),
    tags: EMOTION_TAGS,
    activeTag: '',
    posts: [],
    loading: false,
    loadingMore: false,
    error: false,
    hasMore: false,
    cursor: '',
    composerOpen: false,
    content: '',
    selectedTag: '',
    anonymous: true,
    submitting: false,
    maxContentLength: MAX_CONTENT_LENGTH
  },

  onLoad() {
    this._skipFirstShow = true
    this.loadPosts(true)
  },

  // tabBar 页面切走不销毁，切回时静默刷新；首次由 onLoad 加载，避免双请求。
  onShow() {
    if (this._skipFirstShow) {
      this._skipFirstShow = false
      return
    }
    if (!this.data.loading && !this.data.loadingMore) {
      this.loadPosts(true)
    }
  },

  onPullDownRefresh() {
    this.loadPosts(true)
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loadingMore && !this.data.loading) {
      this.loadPosts(false)
    }
  },

  loadPosts(reset) {
    if (this.data.loading || this.data.loadingMore) return

    const cursor = reset ? '' : this.data.cursor
    if (!reset && !cursor) return

    this.setData(reset
      ? { loading: true, error: false }
      : { loadingMore: true, error: false })

    request({
      url: buildListQuery({ emotionTag: this.data.activeTag, cursor }),
      method: 'GET',
      showLoading: false
    })
      .then((data) => {
        const incoming = normalizePosts(data && data.items)
        const posts = reset ? incoming : this.data.posts.concat(incoming)
        const cursorNext = nextCursor(data)

        this.setData({
          posts,
          cursor: cursorNext,
          hasMore: Boolean(cursorNext),
          error: false
        })
      })
      .catch((err) => {
        console.error('树洞列表加载失败：', err)
        if (reset) this.setData({ error: true })
      })
      .finally(() => {
        this.setData({ loading: false, loadingMore: false })
        wx.stopPullDownRefresh()
      })
  },

  retryLoad() {
    this.loadPosts(true)
  },

  selectFilter(e) {
    const code = e.currentTarget.dataset.code || ''
    if (code === this.data.activeTag) return

    this.setData({
      activeTag: code,
      posts: [],
      cursor: '',
      hasMore: false
    }, () => {
      this.loadPosts(true)
    })
  },

  openComposer() {
    this.setData({ composerOpen: true })
  },

  closeComposer() {
    if (this.data.submitting) return
    this.setData({ composerOpen: false })
  },

  onContentInput(e) {
    this.setData({ content: e.detail.value })
  },

  selectTag(e) {
    this.setData({ selectedTag: e.currentTarget.dataset.code || '' })
  },

  onAnonymousChange(e) {
    this.setData({ anonymous: e.detail.value })
  },

  submitPost() {
    if (this.data.submitting) return

    // 页面用 selectedTag，契约用 emotionTag，此处显式映射，避免把整个 data 传下去。
    const form = {
      content: this.data.content,
      emotionTag: this.data.selectedTag,
      anonymous: this.data.anonymous
    }

    const validation = validatePost(form)
    if (!validation.ok) {
      wx.showToast({ title: validation.message, icon: 'none' })
      return
    }

    this.setData({ submitting: true })

    request({
      url: '/api/treehole/posts',
      method: 'POST',
      data: buildPostPayload(form),
      showLoading: false
    })
      .then(() => {
        // 切回「全部」，保证刚发布的帖子一定出现在列表里。
        this.setData({
          composerOpen: false,
          content: '',
          selectedTag: '',
          anonymous: true,
          activeTag: ''
        })
        wx.showToast({ title: '发布成功 · 24 小时后焚毁', icon: 'none' })
        this.loadPosts(true)
      })
      .catch((err) => {
        console.error('树洞发布失败：', err)
        const serverMessage = err && err.data && err.data.message
        wx.showModal({
          title: '没有发布出去',
          content: failureMessage(err && err.statusCode, serverMessage),
          showCancel: false,
          confirmText: '知道了'
        })
      })
      .finally(() => {
        this.setData({ submitting: false })
      })
  }
})
