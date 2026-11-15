// US-03 情绪曲线 / 情绪分布的纯逻辑层：不依赖 wx，便于用 node:test 直接覆盖。
// 口径来源：docs/requirements/情绪曲线与分布-验收口径-v1.md（2026-11-14 M1 确认）
// 数据源契约：packages/contract/openapi.yaml 的 GET /api/emotions/checkins。

const { EMOTION_CODES, EMOTION_COLOR, FALLBACK_WORDS } = require('./checkin.js')

const RANGE_DAYS = [7, 30]
const INTENSITY_MIN = 1
const INTENSITY_MAX = 5

// 固定顺序与颜色，不按占比动态排序；直接复用 utils/checkin.js 的词表，避免两处漂移。
const EMOTIONS = FALLBACK_WORDS.map((word) => ({
  code: word.code,
  label: word.label,
  color: EMOTION_COLOR[word.code] || ''
}))

function normalizeRange(rangeDays) {
  const days = Number(rangeDays)
  return RANGE_DAYS.includes(days) ? days : RANGE_DAYS[0]
}

function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 「近 7 天 / 近 30 天」是含今天的滚动窗口：to 恒为今天（永远合法），
// from = 今天往前数 N-1 天。用本地时间的 Date 构造器做日期运算，跨月 / 跨年自动进位，
// 绝不手拼月末日期（日历页 2026-11-31 → 后端 400 的坑不要重演）。
function getWindowRange(rangeDays, today = new Date()) {
  const days = normalizeRange(rangeDays)
  const base = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const fromDate = new Date(base.getFullYear(), base.getMonth(), base.getDate() - (days - 1))
  return {
    from: formatDate(fromDate),
    to: formatDate(base)
  }
}

// 按窗口聚合。只采信区间内的合法记录；后端同日幂等（一天最多一条），
// 若异常返回同日多条，只取第一条有效记录，绝不取平均。
function buildAnalysis(items, rangeDays, today = new Date()) {
  const days = normalizeRange(rangeDays)
  const { from, to } = getWindowRange(days, today)
  const base = new Date(today.getFullYear(), today.getMonth(), today.getDate())

  const trendData = []
  const indexByDate = {}

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(base.getFullYear(), base.getMonth(), base.getDate() - i)
    const dateString = formatDate(date)

    indexByDate[dateString] = trendData.length
    trendData.push({
      date: dateString,
      label: `${date.getMonth() + 1}/${date.getDate()}`,
      intensity: null,
      emotion: null,
      missing: true
    })
  }

  const byDate = {}
  const list = Array.isArray(items) ? items : []

  list.forEach((item) => {
    if (!item || typeof item.checkinDate !== 'string') return

    const date = item.checkinDate.slice(0, 10)
    if (!Object.prototype.hasOwnProperty.call(indexByDate, date)) return
    if (!EMOTION_CODES.includes(item.emotion)) return

    const intensity = Number(item.intensity)
    if (!Number.isInteger(intensity)
      || intensity < INTENSITY_MIN
      || intensity > INTENSITY_MAX) return

    if (byDate[date]) return
    byDate[date] = { emotion: item.emotion, intensity }
  })

  Object.keys(byDate).forEach((date) => {
    const point = trendData[indexByDate[date]]
    point.intensity = byDate[date].intensity
    point.emotion = byDate[date].emotion
    point.missing = false
  })

  // 分布按「区间内有效打卡记录条数」计占比；未打卡日不进分母，另以 missingDays 单独呈现。
  const counts = {}
  EMOTIONS.forEach((emotion) => {
    counts[emotion.code] = 0
  })
  Object.values(byDate).forEach((record) => {
    counts[record.emotion] += 1
  })

  const analysisTotal = Object.keys(byDate).length
  const distributionData = EMOTIONS.map((emotion) => ({
    code: emotion.code,
    label: emotion.label,
    color: emotion.color,
    count: counts[emotion.code],
    percent: analysisTotal > 0
      ? Math.round((counts[emotion.code] / analysisTotal) * 100)
      : 0
  }))

  return {
    rangeDays: days,
    from,
    to,
    trendData,
    distributionData,
    analysisTotal,
    missingDays: days - analysisTotal,
    hasData: analysisTotal > 0
  }
}

module.exports = {
  RANGE_DAYS,
  EMOTIONS,
  normalizeRange,
  formatDate,
  getWindowRange,
  buildAnalysis
}
