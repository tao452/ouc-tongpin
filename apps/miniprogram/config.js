// 本地演示走 dev：指向 infra/docker-compose.yml 起在本机 127.0.0.1:8080 的 nginx 网关。
// 微信开发者工具需勾选「不校验合法域名、web-view、TLS 版本以及 HTTPS 证书」才能访问 http。
// 如需回到 Apifox 联调，把 ENV 改回 'mock' 并确保本机 4523 端口的 mock 服务已启动。
//const ENV = 'dev'
const ENV = 'mock'
const ENV_CONFIG = {
  dev: {
    baseURL: 'http://127.0.0.1:8080'
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
