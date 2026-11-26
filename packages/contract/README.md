# packages/contract 接口契约

前后端共享的唯一事实源：`openapi.yaml`（OpenAPI 3.1）+ 由此生成的 TS 类型。

**当前状态**：v0.1 已定稿（2026-11-15，**M1 代做**，原主责 M5）。定稿指字段与错误码冻结，**不等于全部实装**：8 个 path 中 6 个已实装，`POST /api/auth/student-verify` 与 `PUT /api/user/profile` 仍实测 404；11/16 #85 合入后已接入签名 JWT 与服务端归属校验，真实微信平台 / 业务验收仍未完成。契约另新增全局 `bearerAuth` 安全要求（登录 / 情绪词 / 风控显式放行）。

- 逐条实装状态、已知差异、接口 ↔ 数据表映射：[docs/api/接口契约与实装状态-v0.1.md](../../docs/api/接口契约与实装状态-v0.1.md)
- 数据表与字段字典：[docs/api/ER图与字段字典-v0.1.md](../../docs/api/ER图与字段字典-v0.1.md)

流程：改接口先改契约 → 发 PR（M5 + 调用方双人批准）→ 再改实现。契约未合并前，前端按 `openapi.yaml` 生成 Mock，不等后端。

CI 校验：`services/algo/tests/test_api.py::test_implementation_matches_repository_contract` 逐字段比对 `/api/moderation/check` 的契约与 FastAPI schema，字段漂移会让 CI 变红；`test_emotion_lexicon.py` 也读取本文件的词表定义。这两处只覆盖部分契约，**不等于 8 个 path 全量契约测试**。
