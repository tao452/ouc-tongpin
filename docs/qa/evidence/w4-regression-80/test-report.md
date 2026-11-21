# W4 原 80 条回归测试报告

测试版本：`7c67518fc91583a3983ea265b85f6d2a54d12eab`（develop，2026-11-18 获取）。本次逐条尝试 80/80，完整执行并判定 63 条，其余保留依赖或验收阻塞。
结果：**63 PASS / 0 FAIL / 17 BLOCKED**。历史为 55 PASS / 25 BLOCKED。

| 模块 | 数量 | PASS | FAIL | BLOCKED |
|---|---:|---:|---:|---:|
| 登录认证 | 12 | 1 | 0 | 11 |
| 情绪打卡 | 18 | 17 | 0 | 1 |
| 匿名树洞 | 16 | 15 | 0 | 1 |
| 搭子需求 | 8 | 8 | 0 | 0 |
| 内容审核 | 14 | 12 | 0 | 2 |
| 隐私保护 | 8 | 7 | 0 | 1 |
| 基础设施 | 4 | 3 | 0 | 1 |

## 主要发现

- S1-047–054：搭子发布及缺字段、标签 5/6 个、备注 200/201 字边界均实际执行，成功增加一行，非法输入不落库。
- 登录、签名 JWT、过期/错误签名/audience、双账号查询与写入隔离、并发身份、数据库只读角色和日志 PII 已执行 20 条安全专项；详见 security-results.json。专项不计入原 80 条数量。
- 打卡 6 种情绪、强度、100/101 字备注、日期查询、同日幂等及 8 并发提交均使用真实服务；树洞包含审核故障暂停、匿名响应、分页、过期隐藏和焚毁存储检查。
- HIGH 阻断、敏感词变体、正常英文短语豁免、422/413 边界使用 HTTP 实测；MEDIUM/LOW 技术通过与正式词库业务验收分开记录。
- 另对“去死海 / 去死记硬背 / 去死胡同 / 废物利用”等正常短语与同句真实敏感词做 8 条 HTTP 正反控制，8/8 通过，见 phrase-results.json；不增加原目录数量。
- 隐私目录 7 条由当前源码 Maven/JUnit 实际执行；Java 全套 141 项，0 失败、0 错误、0 跳过。
- 五服务从干净源码构建、空卷初始化；完整配置、缺密钥配置、全部健康及 Nginx 7 项 smoke 有本次结果。
- 当前提交 GitHub CI 的 guard、stack、quality 成功；按文档变更跳过的模块 job 不登记为实际执行。保护设置仍待管理员证明。

## 执行命令

```powershell
mvn -B -q verify  # 在 services/api-server 内执行
python scripts/qa/collect_java_evidence.py --reports services/api-server/target/surefire-reports --output qa-private/w4/java-results.json
python -X utf8 docs/qa/evidence/w4-regression-80/run-local.py
python -X utf8 docs/qa/evidence/w4-regression-80/run-phrase-checks.py
python -X utf8 docs/qa/evidence/w4-regression-80/sanitize-evidence.py
python -X utf8 docs/qa/evidence/w4-regression-80/assemble.py
```

Docker 构建与回收命令、网络重试和隔离边界见 environment.md。run-local.py 是本次证据适配器，仅连接指定 WSL daemon/project，调用原有断言并附加输入、响应、SQL/Redis 和时间记录；未伪造 GITHUB_ACTIONS。

## 证据与判定

results.json 保留原编号、测试目的、步骤和预期；逐条链接历史状态、当前状态、测试时间、测试 Commit、实际输入/步骤、响应及数据库证据。BLOCKED 记录本次前置检查与缺少的条件；不能完成原场景的 HTTP 404 不算 PASS。
api-results.json、stack-results.json、java-results.json、security-results.json 为当前执行材料；junit-cases.json 为去除系统属性和控制台材料的 JUnit 方法清单。仅使用合成身份和新建卷，凭证在证据中脱敏。
原目录和历史证据的 SHA-256 记录在 results.json / manifest.json；原目录及历史文件不变。报告提交与测试目标提交区分记录，业务代码无改动。

## 后续安排

可以进入新增 40 条测试的设计阶段。优先设计 JWT/跨用户访问、重试与并发、搭子时区与审核、焚毁竞态、正常短语和网关权限的补充用例；独立编号并关联本报告。现有阻塞继续按 blocked-items.md 补证，本报告不代表这些业务或管理员验收已完成。
