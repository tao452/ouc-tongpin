const ENV = 'mock'

const ENV_CONFIG = {
  dev: {
    baseURL: 'http://localhost:8080'
  },
  test: {
    baseURL: ''
  },
  prod: {
    baseURL: ''
  },
  mock: {
    baseURL: 'http://127.0.0.1:4523/m1/8992998-8800539-8811149'
  }
}

if (!ENV_CONFIG[ENV]) {
  throw new Error(`未知的运行环境：${ENV}`)
}

module.exports = ENV_CONFIG[ENV]
