// 本机通过忽略提交的 config.local.js 指定网关；体验版和正式版必须使用 HTTPS。
let local = {}
try { local = require('./config.local.js') } catch (error) {
  const message = String(error.message)
  const missing = error.code === 'MODULE_NOT_FOUND' || message.includes("module 'config.local.js' is not defined")
  if (!missing || !message.includes('config.local.js')) throw error
}
const account = typeof wx !== 'undefined' && wx.getAccountInfoSync ? wx.getAccountInfoSync() : {}
const env = (account.miniProgram && account.miniProgram.envVersion) || 'develop'
const baseURL = local.baseURL || (env === 'develop' ? 'http://127.0.0.1:8080' : '')
if (!/^https?:\/\//.test(baseURL) || (env !== 'develop' && !baseURL.startsWith('https://'))) {
  throw new Error('请配置当前环境的 API HTTPS 地址')
}
module.exports = { baseURL: baseURL.replace(/\/$/, '') }
