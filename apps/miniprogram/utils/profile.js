// US-35 个人资料：字段与 packages/contract/openapi.yaml 的 PUT /api/user/profile 对齐。
// 本模块刻意不依赖 wx，便于 node --test 直接覆盖边界用例。
const LIMITS = {
  nickname: 20,
  bio: 100,
  tag: 12,
  tags: 8,
}

const EMPTY_PROFILE = {
  nickname: '',
  avatarUrl: '',
  bio: '',
  interestTags: [],
  skillTags: [],
}

function toText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeTags(value) {
  if (!Array.isArray(value)) {
    return []
  }
  const seen = new Set()
  const tags = []
  for (const item of value) {
    const tag = toText(item).slice(0, LIMITS.tag)
    if (!tag || seen.has(tag)) {
      continue
    }
    seen.add(tag)
    tags.push(tag)
    if (tags.length >= LIMITS.tags) {
      break
    }
  }
  return tags
}

// 读取缓存 / 接口响应时统一裁剪，避免异常数据把页面撑坏
function normalizeProfile(raw) {
  const source = raw && typeof raw === 'object' ? raw : {}
  return {
    nickname: toText(source.nickname).slice(0, LIMITS.nickname),
    avatarUrl: toText(source.avatarUrl),
    bio: toText(source.bio).slice(0, LIMITS.bio),
    interestTags: normalizeTags(source.interestTags),
    skillTags: normalizeTags(source.skillTags),
  }
}

// 校验用原始值，不能先裁剪，否则超长输入会被悄悄吞掉
function validateProfile(raw) {
  const source = raw && typeof raw === 'object' ? raw : {}
  const errors = []
  const nickname = toText(source.nickname)
  const bio = toText(source.bio)

  if (!nickname) {
    errors.push('请填写昵称')
  }
  if (nickname.length > LIMITS.nickname) {
    errors.push(`昵称不能超过 ${LIMITS.nickname} 字`)
  }
  if (bio.length > LIMITS.bio) {
    errors.push(`简介不能超过 ${LIMITS.bio} 字`)
  }

  const groups = [
    ['兴趣标签', source.interestTags],
    ['技能标签', source.skillTags],
  ]
  for (const [label, value] of groups) {
    if (!Array.isArray(value)) {
      continue
    }
    if (value.length > LIMITS.tags) {
      errors.push(`${label}最多 ${LIMITS.tags} 个`)
    }
    for (const item of value) {
      if (toText(item).length > LIMITS.tag) {
        errors.push(`${label}单个不能超过 ${LIMITS.tag} 字`)
        break
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    profile: normalizeProfile(source),
  }
}

// 支持中文逗号、顿号、空白分隔，一次可批量添加多个标签
function parseTagInput(text) {
  return toText(text)
    .split(/[,，、\s]+/)
    .filter(Boolean)
    .map(tag => tag.slice(0, LIMITS.tag))
}

function buildPayload(raw) {
  const profile = normalizeProfile(raw)
  return {
    nickname: profile.nickname,
    avatarUrl: profile.avatarUrl,
    bio: profile.bio,
    interestTags: profile.interestTags,
    skillTags: profile.skillTags,
  }
}

module.exports = {
  LIMITS,
  EMPTY_PROFILE,
  normalizeProfile,
  validateProfile,
  parseTagInput,
  buildPayload,
}
