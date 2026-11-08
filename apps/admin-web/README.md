# OUC同频 · 管理端（admin-web）

基于 **Vite + Vue 3 + Element Plus + ECharts** 的管理后台前端工程。

## 当前状态
- ✅ 工程脚手架已补齐（PR #43 配套），`npm ci && npm run build` 可在 CI 通过。
- ✅ `src/views/DataBoard.vue`（US-37 数据看板）已可编译运行，数据为**前端写死的 mock 演示**。
- ✅ `lint` / `test` 已接入 ESLint 与 Vitest，检查 Vue/TypeScript 和现有组件交互。
- ⚠️ 页面数据为写死 mock，接入后端真实接口（见 `packages/contract/openapi.yaml` 的 admin 分组）后替换。

## 本地开发

质量检查：Node 22 下执行 `npm ci`、`npm run lint`、`npm test -- --run`、`npm run build`。
组件测试覆盖图表初始化/销毁、批量审核选择与取消、登录表单校验及凭证不输出到控制台。
登录和审核测试使用页面当前的模拟交互，图表测试替换 Canvas 渲染；真实鉴权、RBAC 与接口联调仍由 M4/M5 接入。

```bash
npm install        # 安装依赖（生成 package-lock.json）
npm run dev        # 启动开发服务器 http://localhost:5173
npm run build      # 生产构建，输出 dist/
npm run preview    # 预览构建产物
```

## 目录约定
- `src/views/*.vue` —— 页面级组件（每个 US 一个视图）
- `src/components/` —— 可复用组件（后续补充）
- 接口调用统一走 `packages/contract/openapi.yaml` 契约，先用 mock，后端就绪后切换为真实请求。

## CI
`.github/workflows/ci.yml` 的 `admin-web` job 在检测到 `apps/admin-web/**` 变更时运行：
`npm ci` → `npm run lint` → `npm run test` → `npm run build`。
