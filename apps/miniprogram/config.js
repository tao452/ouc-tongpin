// ============================================================
// 环境配置：Mock 优先，后端就绪后改 USE_MOCK = false
// ============================================================
const USE_MOCK = true

// TODO(M5): 替换为 Apifox 给出的云端 Mock 地址
//   在 Apifox 项目内任意接口点「Mock」标签 或 项目设置→Mock 设置 复制
const MOCK_BASE = 'https://xxxx.mock.apifox.cn'

// 后端本地地址（M5 起好 Spring Boot 后使用）
const LOCAL_BASE = 'http://localhost:8080'

const BASE_URL = USE_MOCK ? MOCK_BASE : LOCAL_BASE

module.exports = { BASE_URL, USE_MOCK, MOCK_BASE, LOCAL_BASE }
