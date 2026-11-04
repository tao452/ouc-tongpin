# OUC同频 · 小程序端（apps/miniprogram）

## 质量检查

在 Node 22 下运行 `npm ci`、`npm run lint`、`npm test`、`npm run check:project`。
检查包括 JavaScript/CJS 静态检查、请求重试与鉴权头、loading 并发、HTTP 错误、token 存取，以及页面和组件引用。
CI 的 miniprogram 任务执行这些命令，失败会使 quality 检查失败。
页面引用检查不执行微信打包；开发者工具编译、真实微信登录和三套环境联调由 M3/M5 另行验证。

情绪打卡日历与提醒（US-02）前端，微信小程序原生 + TDesign（后续接入）。

## 一、本地导入（微信开发者工具）

1. 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)。
2. 打开工具 → 「导入项目」→ 目录选本文件夹 `apps/miniprogram`。
3. AppID：
   - 有团队小程序账号 → 填 `mp.weixin.qq.com` 注册的 AppID；
   - 仅本地调试 → 选「测试号」（对应 `project.config.json` 里的 `touristappid`）。
4. 编译即可在模拟器看到「打卡日历」页。

## 二、Mock 优先（不等后端）

接口调用统一走 `utils/request.js` → `config.js` 的 `BASE_URL`：

```js
const USE_MOCK = true
const MOCK_BASE = 'https://xxxx.mock.apifox.cn' // TODO: 替换为 M5 在 Apifox 给出的 Mock 地址
```

- `USE_MOCK = true`：请求发到 Apifox 云端 Mock，返回契约里的示例数据，前端可独立开发。
- 后端（M5）起好 Spring Boot 后，把 `USE_MOCK` 改为 `false`，自动切到 `http://localhost:8080`。

> Mock 地址千万别写死进业务代码，统一在 `config.js` 切换。

## 三、目录结构

```
apps/miniprogram/
├── app.js / app.json / app.wxss      # 小程序入口与全局配置
├── config.js                         # 环境切换（USE_MOCK / BASE_URL）
├── utils/request.js                  # wx.request 封装
├── project.config.json               # 开发者工具项目配置
└── pages/
    ├── index/                        # 首页入口
    └── checkin-calendar/             # US-02 打卡日历 + 提醒开关
```

## 四、对接契约

打卡日历调用 `GET /api/emotions/checkins?from=&to=`，返回结构见
`packages/contract/openapi.yaml`：

```json
{ "items": [ { "checkinDate":"2026-10-21", "emotion":"HAPPY", "intensity":4, ... } ],
  "streakDays": 5, "total": 12 }
```

日历按 `checkinDate` 打点，`streakDays` 显示连续天数。

## 五、后端就绪后

提醒的「真正定时推送」由 `services/api-server` 的
`CheckinReminderScheduler`（每天 21:00）负责，当前前端只做提醒时间开关占位。
