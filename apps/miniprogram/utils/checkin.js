// US-01 每日情绪打卡的纯逻辑层：不依赖 wx，便于用 node:test 直接覆盖。
// 契约见 packages/contract/openapi.yaml 的 /api/emotions/words 与 /api/emotions/checkins。

const EMOTION_CODES = ['HAPPY', 'CALM', 'ANXIOUS', 'LONELY', 'IRRITABLE', 'DOWN']

const EMOTION_COLOR = {
  HAPPY: '#FFD93D',
  CALM: '#95E1D3',
  ANXIOUS: '#FF9F68',
  LONELY: '#A6B1E1',
  IRRITABLE: '#FF6B6B',
  DOWN: '#6C7A89'
}

// 后端词表不可用时的兜底，保证演示页面不白屏；来源会在页面上明确标注为「本地兜底」。
const FALLBACK_WORDS = EMOTION_CODES.map((code, index) => ({
  code,
  label: ['开心', '平静', '焦虑', '孤独', '烦躁', '低落'][index],
  color: EMOTION_COLOR[code]
}))

const DEFAULT_SCALE = { min: 1, max: 5 }

function normalizeWords(response) {
  if (!response || !Array.isArray(response.words)) return FALLBACK_WORDS
  const words = response.words
    .filter((item) => item && EMOTION_CODES.includes(item.code))
    .map((item) => ({
      code: item.code,
      label: item.label || item.code,
      color: EMOTION_COLOR[item.code] || ''
    }))
  return words.length ? words : FALLBACK_WORDS
}

function normalizeScale(response) {
  const scale = response && response.intensityScale
  const min = Number(scale && scale.min)
  const max = Number(scale && scale.max)
  if (!Number.isInteger(min) || !Number.isInteger(max)
    || min < 1 || max < min || max > 10) return { ...DEFAULT_SCALE }
  return { min, max }
}

function validateCheckin(form) {
  const data = form || {}
  const emotion = data.emotion
  const intensity = Number(data.intensity)
  const note = String(data.note || '')
  if (!EMOTION_CODES.includes(emotion)) return { ok: false, message: '请先选择一个情绪词' }
  if (!Number.isInteger(intensity) || intensity < 1 || intensity > 5) {
    return { ok: false, message: '强度需为 1–5 级' }
  }
  if (note.length > 100) return { ok: false, message: '备注最多 100 字' }
  return { ok: true, message: '' }
}

function buildCheckinPayload(form) {
  const payload = {
    emotion: form.emotion,
    intensity: Number(form.intensity)
  }
  const note = String(form.note || '').trim()
  if (note) payload.note = note
  return payload
}

module.exports = {
  EMOTION_CODES,
  EMOTION_COLOR,
  FALLBACK_WORDS,
  normalizeWords,
  normalizeScale,
  validateCheckin,
  buildCheckinPayload
}
