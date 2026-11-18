// US-05 / US-07 匿名树洞的纯逻辑层：不依赖 wx，便于用 node:test 直接覆盖。
// 契约见 packages/contract/openapi.yaml 的 /api/treehole/posts；
// 后端返回 LocalDateTime（UTC+8 本地时间，无时区后缀），POST 带纳秒、GET 精确到秒。

const MAX_CONTENT_LENGTH = 500

const EMOTION_TAGS = [
  { code: 'HAPPY', label: '开心', bg: '#FFF1BF' },
  { code: 'CALM', label: '平静', bg: '#D9F2EC' },
  { code: 'ANXIOUS', label: '焦虑', bg: '#FFE4D3' },
  { code: 'LONELY', label: '孤独', bg: '#E4E8FA' },
  { code: 'IRRITABLE', label: '烦躁', bg: '#FFDADB' },
  { code: 'DOWN', label: '低落', bg: '#E3E8EC' }
]

const EMOTION_CODES = EMOTION_TAGS.map((item) => item.code)

function emotionMeta(code) {
  return EMOTION_TAGS.find((item) => item.code === code) || null
}

// 不用 new Date(string)：iOS 对无时区的 ISO 串解析不一致，手工拆成本地时间。
function parseLocalDateTime(value) {
  if (typeof value !== 'string') return null
  const matched = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(value)
  if (!matched) return null
  const date = new Date(
    Number(matched[1]),
    Number(matched[2]) - 1,
    Number(matched[3]),
    Number(matched[4]),
    Number(matched[5])
  )
  return Number.isNaN(date.getTime()) ? null : date
}

function formatLocalTime(value) {
  const date = parseLocalDateTime(value)
  if (!date) return ''
  const pad = (num) => String(num).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatRemaining(value, now = Date.now()) {
  const date = parseLocalDateTime(value)
  if (!date) return ''
  const minutes = Math.floor((date.getTime() - now) / 60000)
  if (minutes <= 0) return '即将焚毁'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours >= 24) return '剩余约 24 小时'
  if (hours > 0) return rest ? `剩余 ${hours} 小时 ${rest} 分` : `剩余 ${hours} 小时`
  return `剩余 ${minutes} 分钟`
}

function authorText(post) {
  const mask = String(post.authorMask || '')
  if (post.anonymous === false) return mask || '同学'
  const short = mask.replace(/[^A-Za-z0-9]/g, '').slice(-4).toUpperCase()
  return short ? `匿名同学 · #${short}` : '匿名同学'
}

function normalizePosts(items, now = Date.now()) {
  if (!Array.isArray(items)) return []
  return items
    .filter((post) => post && typeof post.content === 'string')
    .map((post) => {
      const meta = emotionMeta(post.emotionTag)
      return {
        id: post.id,
        content: post.content,
        emotionTag: post.emotionTag,
        emotionLabel: meta ? meta.label : '其他',
        emotionBg: meta ? meta.bg : '#E3E8EC',
        anonymous: post.anonymous !== false,
        authorText: authorText(post),
        createdText: formatLocalTime(post.createdAt),
        remainingText: formatRemaining(post.expiresAt, now),
        hugCount: Number(post.hugCount) || 0
      }
    })
}

function buildListQuery(options = {}) {
  const params = []
  if (options.emotionTag) params.push(`emotionTag=${encodeURIComponent(options.emotionTag)}`)
  if (options.cursor) params.push(`cursor=${encodeURIComponent(options.cursor)}`)
  return `/api/treehole/posts${params.length ? `?${params.join('&')}` : ''}`
}

function validatePost(form) {
  const data = form || {}
  const content = String(data.content || '').trim()
  if (!content) return { ok: false, message: '先写点什么吧' }
  if (content.length > MAX_CONTENT_LENGTH) return { ok: false, message: '最多 500 字' }
  if (!EMOTION_CODES.includes(data.emotionTag)) {
    return { ok: false, message: '请选择一个情绪标签' }
  }
  return { ok: true, message: '', content }
}

function buildPostPayload(form) {
  const data = form || {}
  return {
    content: String(data.content || '').trim(),
    emotionTag: data.emotionTag,
    anonymous: data.anonymous !== false
  }
}

// 后端：400 参数不合法 / 422 命中 HIGH / 503 审核服务不可用，三种情况都不写库。
function failureMessage(statusCode, serverMessage) {
  if (statusCode === 422) return '内容未通过安全检查，没有发布出去。换个说法再试试吧。'
  if (statusCode === 503) return '内容安全服务暂时不可用，内容没有发布，请稍后重试。'
  if (statusCode === 400) return serverMessage || '内容或情绪标签不合法，请检查后重试。'
  return '发布失败，请检查网络后重试。'
}

function nextCursor(data) {
  return data && data.nextCursor ? String(data.nextCursor) : ''
}

module.exports = {
  MAX_CONTENT_LENGTH,
  EMOTION_TAGS,
  EMOTION_CODES,
  emotionMeta,
  formatLocalTime,
  formatRemaining,
  normalizePosts,
  buildListQuery,
  validatePost,
  buildPostPayload,
  failureMessage,
  nextCursor
}
