const { getToken } = require('./storage.js');
const config = require('../config.js');

let loadingCount = 0;

function showLoading() {
  loadingCount++;
  if (loadingCount === 1) {
    wx.showLoading({
      title: '加载中...',
      mask: true,
    });
  }
}

function hideLoading() {
  loadingCount = Math.max(0, loadingCount - 1);
  if (loadingCount === 0) {
    wx.hideLoading();
  }
}

function request(options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const showLoadingEnabled = options.showLoading !== false;

  // GET 请求默认重试一次；POST 等请求暂不自动重试，避免重复提交
  const retryCount = options.retry !== undefined ? options.retry : method === 'GET' ? 1 : 0;

  if (showLoadingEnabled) {
    showLoading();
  }

  const token = getToken();

  return new Promise((resolve, reject) => {
    let attempts = 0;

    const sendRequest = () => {
      wx.request({
        url: config.baseURL + options.url,
        method,
        timeout: options.timeout || 10000,
        data: options.data || {},
        header: {
          'content-type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(options.header || {}),
        },

        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data);
          } else {
            reject({
              statusCode: res.statusCode,
              data: res.data,
              message: `请求失败（HTTP ${res.statusCode}）`,
            });
          }
        },

        fail(err) {
          if (attempts < retryCount) {
            attempts++;
            sendRequest();
          } else {
            reject({
              message: '网络连接失败，请检查网络后重试',
              error: err,
            });
          }
        },

        complete() {
          // 每次请求完成时由最终结果统一处理 Loading
        },
      });
    };

    sendRequest();
  })
    .catch((err) => {
      console.error('[请求错误]', err);

      wx.showToast({
        title: err.message || '请求失败，请稍后重试',
        icon: 'none',
      });

      throw err;
    })
    .finally(() => {
      if (showLoadingEnabled) {
        hideLoading();
      }
    });
}

module.exports = {
  request,
};
