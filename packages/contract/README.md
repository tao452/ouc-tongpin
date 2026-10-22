# packages/contract 接口契约

前后端共享的唯一事实源：`openapi.yaml`（OpenAPI 3.1）+ 由此生成的 TS 类型。

流程：改接口先改契约 → 发 PR（M5 + 调用方双人批准）→ 再改实现。
契约未合并前，前端按 `openapi.yaml` 生成 Mock，不等后端。
