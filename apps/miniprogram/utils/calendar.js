// 打卡日历的纯逻辑：月份区间、网格、后端响应规范化。
// 抽成独立模块是为了能脱离微信环境跑单元测试（日期 bug 在这里最容易复发）。

const WEEK = ['日', '一', '二', '三', '四', '五', '六']

const EMOTION_COLOR = {
  HAPPY: '#FFD93D',
  CALM: '#95E1D3',
  ANXIOUS: '#FF9F68',
  LONELY: '#A6B1E1',
  IRRITABLE: '#FF6B6B',
  DOWN: '#6C7A89'
}

// month 为 1-12；new Date(year, month, 0) 即「第 month 月的第 0 天」= 该月最后一天。
// 不能把月末写死成 31：2/4/6/9/11 月的 31 日是非法日期，后端 LocalDate.parse 会抛 400。
function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate()
}

function getMonthRange(year, month) {
  const mm = String(month).padStart(2, '0')
  const lastDay = String(daysInMonth(year, month)).padStart(2, '0')

  return {
    from: `${year}-${mm}-01`,
    to: `${year}-${mm}-${lastDay}`
  }
}

function shiftMonth(year, month, delta) {
  const index = year * 12 + (month - 1) + delta

  return {
    year: Math.floor(index / 12),
    month: (index % 12) + 1
  }
}

function buildMonthGrid(year, month, checkedDates) {
  const dates = checkedDates || {}
  const first = new Date(year, month - 1, 1).getDay()
  const days = daysInMonth(year, month)
  const mm = String(month).padStart(2, '0')
  const cells = []

  for (let i = 0; i < first; i++) {
    cells.push({ key: `empty-${i}`, empty: true })
  }

  for (let d = 1; d <= days; d++) {
    const ds = `${year}-${mm}-${String(d).padStart(2, '0')}`
    const emotion = dates[ds]

    cells.push({
      key: ds,
      empty: false,
      day: d,
      date: ds,
      emotion,
      color: emotion ? EMOTION_COLOR[emotion] || '' : ''
    })
  }

  return cells
}

// 后端 total 是「本次查询区间内的条数」，不是历史累计；翻月时会变成 0，
// 所以页面文案用「本月 N 次」，不要写成「累计」。streakDays 才是全局连续天数。
function normalizeCheckins(payload) {
  const data = payload || {}
  const items = Array.isArray(data.items) ? data.items : []
  const checkedDates = {}

  items.forEach((item) => {
    if (item && item.checkinDate) {
      checkedDates[item.checkinDate] = item.emotion
    }
  })

  const total = Number(data.total)

  return {
    checkedDates,
    streakDays: Number(data.streakDays) || 0,
    // 优先采信契约字段；后端将来分页时 total 仍是区间总数，数 items 就会少算。
    monthTotal: Number.isFinite(total) ? total : items.length
  }
}

module.exports = {
  WEEK,
  EMOTION_COLOR,
  daysInMonth,
  getMonthRange,
  shiftMonth,
  buildMonthGrid,
  normalizeCheckins
}
