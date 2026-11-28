// 按 Unicode 码点遍历，截断时保留完整代理对。
function codePointCount(text) {
  return Array.from(String(text || '')).length
}

function truncateCodePoints(text, limit) {
  return Array.from(String(text || '')).slice(0, limit).join('')
}

module.exports = { codePointCount, truncateCodePoints }
