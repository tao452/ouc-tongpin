# OUC同频 · 小程序端（apps/miniprogram）

## 质量检查

在 Node 22 下运行 `npm ci`、`npm run lint`、`npm test`、`npm run check:project`。
检查包括 JavaScript/CJS 静态检查、请求重试与鉴权头、loading 并发、HTTP 错误、token 存取，以及页面和组件引用。
CI 的 miniprogram 任务执行这些命令，失败会使 quality 检查失败。
页面引用检查不执行微信打包；开发者工具编译、真实微信登录和三套环境联调由 M3/M5 另行验证。

小程序为微信原生页面。当前没有任何页面引用 TDesign 组件，本地导入**无需「构建 npm」**，详见第六节。

## 一、本地导入（微信开发者工具）

1. 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)。
2. 打开工具 → 「导入项目」→ 目录选本文件夹 `apps/miniprogram`。
3. AppID：
   - 有团队小程序账号 → 填 `mp.weixin.qq.com` 注册的 AppID；
   - 当前 `project.config.json` 已填入团队真实 AppID；仅本地调试需要测试号时，可临时改回 `touristappid`，该改动不要提交。
4. 编译即可在模拟器看到「打卡日历」页。

## 二、运行环境切换

接口统一走 `utils/request.js` → `config.js`，由 `ENV` 选择 `baseURL`：

| ENV | baseURL | 用途 |
|---|---|---|
| `dev`（当前默认） | `http://127.0.0.1:8080` | 本机 Docker 演示环境 |
| `mock` | `http://127.0.0.1:4523/...` | Apifox 云端 Mock |
| `test` / `prod` | 空 | 未配置，勿用于演示 |

课堂演示：先按仓库根目录说明起好 5 个容器，再在微信开发者工具「详情 → 本地设置」勾选
**「不校验合法域名、web-view、TLS 版本以及 HTTPS 证书」**，否则 `http://127.0.0.1` 会被拦截。
`config.js` 里是**开发机回环地址**，真机预览时手机上的 `127.0.0.1` 指向手机自身，
需改成电脑的局域网 IP 且手机与电脑同网。

> 不要把地址写死在业务代码里，统一在 `config.js` 切换；`project.private.config.json`
> 是本机配置（gitignore），不要提交。

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

日历按 `checkinDate` 打点，`streakDays` 是**全局**连续天数；`total` 是**本次查询区间内**的条数，不是历史累计，翻月会变化。

## 五、后端就绪后

提醒的「真正定时推送」由 `services/api-server` 的
`CheckinReminderScheduler`（每天 21:00）负责，当前前端只做提醒时间开关占位。

## 六、TDesign 与「构建 npm」

`package.json` 保留了 `tdesign-miniprogram` 依赖，但**当前所有页面的 wxml 都没有使用 `<t-*>` 组件**，
各页面 `usingComponents` 均为空。因此 clone 后直接导入微信开发者工具即可编译，不需要构建 npm，
也不需要 `miniprogram_npm/` 目录（该目录是本地产物，已被 gitignore）。

历史上首页 `index.json` 残留过一条无效的 `t-button` 声明，即使 wxml 没用到，开发者工具仍会去解析
组件路径并报「组件不存在」。该残留已删除；**若将来真的引入 TDesign 组件**，记得先在开发者工具
「工具 → 构建 npm」生成 `miniprogram_npm/`，再编译，否则换机器会复现同类错误。
