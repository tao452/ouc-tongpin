# W4 测试环境

测试日期：2026-11-18，时区 Asia/Shanghai。HTTP 主套件约 17:02–17:07；Java 独立执行约 16:50–16:51。逐条时间以 results.json 为准，JUnit 方法仅有耗时，采集时间已单独标注。

## Git 与测试目标

| 项目 | 本次记录 |
|---|---|
| 仓库 | tao452/ouc-tongpin |
| 目标分支 | fetch 后的 origin/develop |
| 测试 Commit | `7c67518fc91583a3983ea265b85f6d2a54d12eab` |
| Git tree | `0fdee4ce183f85cadf3b1c0f2b162bc520f88aef` |
| 报告分支 | `test/w4-regression-80-20261118` |
| 测试目录 | `D:/18199/桌面/软件工程/ouc-tongpin-w4-regression-80` |
| 历史 Commit | `e4540e14e0a1404d935cfe88b7b9a4a13b65a6c0` |
| 历史执行时间 | `2026-11-09T07:23:22.149004+00:00` |

开始时主工作区是 `feature/demo-v1.0-validation`，HEAD `84f99537f353f8340958705a3b1c01bc01a0fe73`，含未提交演示改动。使用独立干净 worktree，从 develop 建立报告分支；主工作区的分支、文件和暂存状态未改动。应用提供的 worktree 创建工具未能识别 Windows checkout，随后使用 `git worktree add` 成功建立。没有在 develop/main 提交或合并。

基线为该 develop 的 `docs/qa/s1-test-cases.json` 与 `docs/qa/evidence/regression-20261109/catalogue-results.json`。未改动原编号、目的、步骤、预期或历史状态。输入哈希及业务源码无差异检查见 manifest.json / validation.json。

## 运行环境与隔离

| 项目 | 配置 |
|---|---|
| 宿主 | Windows 11，Python 3.13.5 |
| Linux | WSL Ubuntu 22.04.1 LTS |
| Docker Engine | 29.1.3，独立于演示 daemon |
| Compose | 2.40.3+ds1-0ubuntu1~22.04.1 |
| Java / Maven | 本机 Temurin 17.0.20.1 / Maven 3.9.16，实际执行 `mvn -B -q verify` |
| Docker socket | `unix:///var/run/docker.sock`，演示栈使用另一个 socket |
| Compose project | `ouc-w4-20261118-7c67518` |
| 网关 / MySQL / Redis | 127.0.0.1:18084 / 13384 / 6379 |
| MySQL | 官方 mysql:8.0；新建 `ouc-w4-20261118-7c67518_mysql-data` 卷 |
| Redis | 官方 redis:7-alpine；独立容器，未复用演示缓存 |
| 业务镜像 | api / algo / web 均由目标 Commit 原始 Dockerfile 构建 |
| 授权 | 随机独立 JWT/HMAC/数据库/Redis 密钥；`WX_MOCK_ENABLED=true` |
| 真实微信 | 未提供应用凭据、真实授权账号或 code |

initial-state.json 记录六张业务表均为 0 行，再开始创建合成账号与数据。HTTP 经过真实 Nginx、Java、FastAPI，SQL/Redis 在指定项目的容器内执行。故障注入只暂停本项目 algo，随后恢复。临时只读账号仅在本测试库创建，并由 finally 删除。

api-results.json / security-results.json 保存合成输入、脱敏响应、SQL/Redis 证据和起止时间。JWT 不归档；私有身份 SQL 输出只保留行数与摘要；运行 PII 材料不归档。java-results.json 和 junit-cases.json 来自本次真实 Surefire XML；XML 原件位于本 worktree 的 target/surefire-reports，归档清单保留 SHA-256，未复制系统属性或控制台材料。

## 构建与网络处理

首次拉取镜像遇到 Docker Hub 超时；第二次 BuildKit 获取 token 超时。给本次 daemon 与 CLI 接入已有 Windows 代理后，三个业务镜像完成原始 Dockerfile 构建。MySQL 的大层下载停滞后取消该次拉取，以 `docker save | docker load` 只读导入演示 daemon 已缓存的官方 MySQL/Redis 镜像；没有复制容器、挂载目录或数据库卷。镜像 ID/digest 见 environment-snapshot.json。

最终在全新项目和空卷上启动成功。以下命令在 WSL 的本测试目录执行；代理仅在网络需要时配置：

```sh
export COMPOSE_PROJECT_NAME=ouc-w4-20261118-7c67518
docker compose --env-file .env -f infra/docker-compose.yml config -q
docker compose --env-file .env -f infra/docker-compose.yml build \
  --build-arg HTTP_PROXY=http://172.17.0.1:17890 \
  --build-arg HTTPS_PROXY=http://172.17.0.1:17890
docker compose --env-file .env -f infra/docker-compose.yml up \
  -d --no-build --pull never --wait --wait-timeout 240
```

`.env` 由原 `scripts/ci/create-test-env.py` 创建，避免覆盖已有环境文件；只把 WEB_PORT 改为 18084、MYSQL_PORT 改为 13384 以避开演示端口。未改动已跟踪的 Compose、Dockerfile 或业务配置。

## 执行与复现

run-local.py 在 Windows Python 中调用原有回归断言，通过 WSL Docker 传输访问固定 daemon/project，并记录每条实际输入、响应和数据库证据；没有设置 `GITHUB_ACTIONS=true`，也未改动原执行器的环境保护。原栈执行器内置的 “Linux CI” 文本已保留为 original_runner_scope_label，实际运行环境另外注明为本地 WSL。

复现时先准备目标 Commit 的干净 checkout，再把本报告目录复制到该 checkout 的相同路径，创建新 `.env` 和空测试栈。适配器会核对 Commit、项目及空库；不能对现有数据栈直接重跑。

在仓库根目录运行（Maven 命令在 services/api-server 内执行）：

```powershell
python scripts/ci/create-test-env.py
# 按上文调整测试端口并构建、启动隔离栈
python -X utf8 docs/qa/evidence/w4-regression-80/run-local.py
python -X utf8 docs/qa/evidence/w4-regression-80/run-phrase-checks.py
python -X utf8 docs/qa/evidence/w4-regression-80/sanitize-evidence.py
python -X utf8 docs/qa/evidence/w4-regression-80/assemble.py
```

Java 先执行 `mvn -B -q verify`，再运行 collect_java_evidence.py。assemble.py 需要本次 Java、栈和安全专项材料齐备，按原 80 个编号汇总；附加专项、短语检查与技术前置探测不计入 80 的数量。

## GitHub 与环境回收

GitHub 连接器不能读取分支保护详情，因此使用本机现有 Git 凭据对官方 REST API 只读查询，凭据不输出、不归档。github-checks.json 记录当前 Commit 的 CI/quality 成功、实际跳过的 job、PR #53 历史失败实验，以及 protection 404 / rulesets 空列表；没有把历史失败实验写成本次新实验。

执行完成后仅对明确项目执行 `docker compose --project-name ouc-w4-20261118-7c67518 --env-file .env -f infra/docker-compose.yml down -v`。cleanup.json 证实本次容器、卷和网络均已删除，演示栈五个容器仍 healthy。随后停止本次启动的 daemon/代理中继并删除本 worktree 的临时 `.env`；保留已下载的镜像缓存。
