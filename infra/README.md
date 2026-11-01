# 本地全栈环境

对应 US-32（#33），在 M5 的 MySQL/Redis 与后端骨架上补容器化、网关及自动验收。
开发机需 Docker Desktop（Linux 容器）与 Docker Compose v2，端口 8080/3307/6379 空闲。
微信小程序仍用微信开发者工具运行，容器启动不代表小程序业务已完成。

## 启动

在仓库根目录执行：

```powershell
Copy-Item .env.example .env
# 修改 .env 的三个数据库/缓存密码，ANON_ID_SECRET 填写至少 32 字节随机密钥
docker compose --env-file .env -f infra/docker-compose.yml config -q
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait --wait-timeout 240
python scripts/e2e/foundation-smoke.py
```

环境变量从根 `.env` 显式读取，不上传此文件。不要使用示例 change-me 密码对外部署。
仅供一次性自动测试时，可用 `python scripts/ci/create-test-env.py` 生成随机测试配置；
它拒绝覆盖已有 `.env`，输出不显示密钥。

管理端及统一 API 入口 `http://127.0.0.1:8080`，MySQL 使用 `127.0.0.1:3307`。
本机单独启动 Java 时需自行将 `.env` 中的值导入进程环境（Spring 不自动读取 `.env`）。
服务通过容器内 mysql/redis/algo/api 名称访问；MySQL、Redis、Java 和算法的健康检查通过后才启动网关。
容器里的 Java `/internal/health` 仅检查进程响应，数据库/缓存由各自的认证健康检查验证。
网关不开放该内部健康地址，不记录访问日志，限制请求体 16 KiB。

```powershell
docker compose --env-file .env -f infra/docker-compose.yml ps
docker compose --env-file .env -f infra/docker-compose.yml down
```

MySQL 使用具名持久卷。正常停止不删除卷；如需清理一次性测试数据，先确认没有需要保留的数据。
本配置只绑定本机回环地址，没有域名、HTTPS、生产机部署或灰度回滚能力。

## CI 与验收边界

PR 的 CI 执行原有 guard、模块检查，以及 Docker 全栈构建与真实 HTTP 冒烟测试。
算法修改执行 Ruff、Pytest 和 ≥80% 覆盖率门槛；Java 的隐私测试并入 Maven verify。
`quality` 汇总所有结果，可由管理员审核后设为分支保护的必过检查；本 PR 不修改仓库保护配置。
现有管理端 lint/test 是其他成员的占位脚本，不能当成前端已经接受测试。
当前 CI 未增加 deploy-test、release、nightly；测试服务器与凭证准备后另行实现。
共享 Issue #33 保持打开，直到双方确认环境、CI、测试环境部署与独立复核。
