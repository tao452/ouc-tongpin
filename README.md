# OUC同频 · 校园搭子匹配与情绪安全社交平台

中国海洋大学「六个核桃团队」课程项目。微信小程序（学生端）+ Vue3 管理端 + Spring Boot 后端 + FastAPI 算法服务，
Scrum 三迭代、每迭代 4 周、每迭代末一个可发布版本（v0.1.0 / v1.0.0 / v2.0.0）。

## 1 目录结构

| 目录 | 内容 | 责任人 |
|---|---|---|
| `apps/miniprogram/` | 微信小程序源码、分包、自定义组件 | M3 |
| `apps/admin-web/` | Vue3 + Vite 管理端 | M4 |
| `services/api-server/` | Spring Boot 主后端、Flyway 迁移脚本 | M5 |
| `services/algo/` | FastAPI 算法服务、离线评估脚本 | M6 |
| `packages/contract/` | OpenAPI 契约与 TS 类型（前后端共享） | M5 |
| `design/` | 设计稿导出、标注、切图、设计规范 | M2 |
| `infra/` | docker-compose、Nginx、部署与回滚脚本 | M6 |
| `docs/` | 需求、ADR、迭代报告、验收记录 | M1 |
| `scripts/e2e/` | Pytest 验收用例、k6 压测脚本 | M1 |
| `.github/` | Actions、Issue/PR 模板、CODEOWNERS | M1 / M6 |

## 2 环境拉起（10 分钟）

```bash
git clone git@github.com:ouc-tongpin/ouc-tongpin.git
cd ouc-tongpin
cp .env.example .env          # 不要提交 .env
docker compose -f infra/docker-compose.yml up -d   # MySQL 8 + Redis
```

按角色装依赖：

```bash
cd apps/admin-web && npm ci                       # M4
cd services/api-server && mvn -q verify           # M5
cd services/algo && pip install -r requirements.txt   # M6
```

小程序用微信开发者工具导入 `apps/miniprogram/`（M3）。三个自检全过才算接入完成：能启动、单测通过、能切出 feature 分支。

## 3 分支模型

| 分支 | 用途 | 规则 |
|---|---|---|
| `main` | 随时可发布 | 受保护，只接受 `release/*` 的 PR，合并即打 tag |
| `develop` | 迭代集成，默认分支 | 受保护，PR + CI 绿 + 1 人批准 |
| `feature/US-xx-描述` | 单个故事 | 从 `develop` 拉出，生命周期 ≤ 3 天 |
| `release/x.y` | 迭代收尾 | 只修缺陷不加功能，验收后合入 `main` 与 `develop` |
| `hotfix/*` | 线上紧急修复 | 从 `main` 拉出，24 小时内合回两条分支 |

## 4 提交规范

格式：`type(scope): subject (#Issue)`

- type：`feat` `fix` `refactor` `test` `docs` `style` `perf` `chore`
- scope：`mp` `admin` `api` `algo` `docs` `infra`
- 一次提交只做一件事，≤ 200 行，提交后必须能编译通过

示例：`feat(api): 四维加权同频指数 (#45)`

## 5 每日循环

```bash
git switch develop && git pull --rebase
git switch -c feature/US-12-match-score
# 写代码
git add -p && git commit -m "feat(api): 四维加权同频指数 (#45)"
git push -u origin feature/US-12-match-score
```

提交 PR 前必须先把 `develop` 合进自己的分支：

```bash
git fetch origin && git rebase origin/develop
# 解冲突：删掉 <<<<<<< ======= >>>>>>> 标记，保留双方意图
git add <file> && git rebase --continue
git push --force-with-lease
```

## 6 PR 规则

1. Base 选 `develop`，标题 `[US-12] 四维加权同频指数`
2. 描述四段：`Closes #45` / 改了什么 / 怎么自测 / 影响面与回滚
3. CI 四个检查项全绿才请求评审
4. 评审人由 CODEOWNERS 自动带出，作者不得自审自合
5. 用 **Squash and merge**，合并后删除分支

## 7 禁止事项

- 不直推 `main` / `develop`
- 不对共享分支 `force push`（自己的 feature 分支用 `--force-with-lease`）
- 不提交密钥、`.env`、`node_modules`、`target`、大文件
- 不自审自合
- feature 分支不超 3 天
- 不把跑不通的代码推上去让 CI 兜底

## 8 版本发布（每 4 周）

```bash
git switch develop && git pull --rebase
git switch -c release/0.1 && git push -u origin release/0.1
# 验收通过后
git switch main && git pull --rebase
git merge --no-ff release/0.1
git tag -a v0.1.0 -m "V0.1 内测可用版"
git push origin main --tags
git switch develop && git merge --no-ff release/0.1 && git push
```

随后在 GitHub → Releases 起草 v0.1.0，写清本版内容、已知问题、体验方式。

## 9 延伸阅读

- **每个故事怎么落地**（工具、目录、六步流程、S1 故事到接口映射）：[`docs/故事落地与开发指南.md`](docs/故事落地与开发指南.md)
- **接口契约 v0.1**：`packages/contract/openapi.yaml`（Apifox 导入此文件做协作界面）
