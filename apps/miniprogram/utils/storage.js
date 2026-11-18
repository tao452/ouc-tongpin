const TOKEN_KEY = 'token'

function setToken(token) {
  if (!token) {
    return
  }
  wx.setStorageSync(TOKEN_KEY, token)
}

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || ''
}

function removeToken() {
  wx.removeStorageSync(TOKEN_KEY)
}

module.exports = {
  setToken,
  getToken,
  removeToken
}
