# 新增 40 条自动化落地方案

最新复测基线为`09a0cd6`（含#91/#93），38条已重新执行，113/114仍待M1/M5确认。完整120条状态、分母口径及17条阻塞责任人见[本次状态报告](../W4-120条测试最终状态-20261122.md)。每次可设置`W4_RUN_DIR=qa-private/<新目录>`，保留前次私有日志与凭据，公开证据按独立运行目录存放。

2026-11-22 已落地并执行38条，结果38 PASS；S1-113/114等待业务和接口口径确认，保持NOT_RUN。JSON是设计与执行索引，Markdown为逐条阅读版，`implementation_file`指向实际脚本。原始设计保存在`design-20261118.snapshot.json`，原静态检查结果保持不变。实际结果见[执行报告](执行报告-20261122.md)。

## 分组与执行层次

| 分组 | 编号 | 建议实现 | 核心证据 |
|---|---|---|---|
| JWT/身份隔离 | S1-081～090 | Python HTTP probe；085 Java 单元；087 MockMvc 过滤链集成 | 每个身份/入口/子样本的响应、限定归属 SQL、拒绝后零写入 |
| 并发幂等 | S1-091～098 | Python 并发 HTTP/响应丢弃代理；098 Java+真实 MySQL 竞态集成 | 全部 future 结果、barrier 调度、首写/重试 ID、唯一键与限定行快照 |
| 树洞焚毁 | S1-099～106 | HTTP 发布及 Java 测试进程调用任务；真实 MySQL8/Redis | 正文/alias/映射清除、归档数与摘要、队列确认前后状态、回滚证据 |
| 搭子参数边界 | S1-107～114 | Python 参数化 HTTP+SQL，DTO/解析单测作为快速层 | 精确构造的输入长度/时间/Decimal、状态码、无截断或拒绝零写入 |
| 敏感词豁免 | S1-115～120 | Python HTTP 矩阵、独立字典实例及启动健康测试 | 精确 hits/passed、字典 hash、业务落库或拒绝、进程启动失败 |

085 为实例级验签，没有 HTTP/MySQL/Redis。087 的响应来自 MockMvc，不是网络 HTTP。098、部分焚毁检查为任务/服务集成，HTTP 没有发生时应记 N/A；不能把返回对象或进程异常改写成 HTTP 200/422。

## 夹具与数据边界

1. 按层级启用所需服务：纯 Java 单元或独立算法进程无需启动无关 MySQL/Redis。需要全栈时创建本次独占 Compose 项目 `ouc-w4-new40-${RUN_ID}`、新 MySQL 数据卷、独立 Redis、随机凭据及专属端口。启动前核对项目标签与目标源 Commit；首个业务写入前记录空表证据。禁止指向团队现有数据库或演示数据卷。
2. 每条新建 A/B 合成平台身份，保存真实 JWT 但不写入报告。D 固定为 2034-01-15，可通过新账号或日期偏移隔离。JWT 签名器只能读取本次测试密钥，使用合法 issuer/audience/时效及已存在账号做正控制。
3. NEED/POST 的完整基准输入见目录 JSON。字符串采用构造表达式并先断言实际长度；`省略` 指不发送字段，不能替换为字符串 `null`。Emoji 同时记录码点数、UTF-16 单元和 UTF-8 字节数。
4. 使用响应返回的 P/id 和本条 A/B 限定 SQL、Redis 查询。不能用全局行数代替归属断言；不得 TRUNCATE、FLUSHDB 或清理团队数据。每个子样本的前后快照与它自己的输入对应。
5. 焚毁故障组串行执行；显式任务调用前确认到期队列只含该条受控夹具。测试上下文不启用自动调度，不新增生产管理/时钟/故障接口。不同组若并行必须拥有独立项目和数据卷。
6. 103 的临时 guard DDL 只由本次私有库初始化凭据执行，应用账号维持无 DDL 权限。表名用安全 RUN_ID 后缀并登记归属；finally 先解除 guard，再回收本条夹具。

## 并发与故障控制

- 081 必须用可保留重复头的客户端，直连 `api:8080` 与经过 `web:80` 分别记录。普通 header 字典会折叠重复 Authorization，不能用于此用例。
- 082 生成精确 4096/4097 字符的**签名正确** JWT。无法构造目标长度属于夹具错误，不能用任意长垃圾字符串假替代。
- 083 使用 T+120 秒的未来 iat，与代码允许的 30 秒偏移保持余量；夹具建立超过 10 秒则重建。禁止调整宿主时钟。
- 088 最多 64 次只读请求/8 worker；091 为 16 请求/8 worker；092～095 最多 32 请求/16 worker；097 为 16 个独立 login→checkin worker。一次执行不无限重试，不在本组附加吞吐量/P95 业务门槛。
- 091 的稳定字段是 id/emotion/intensity/note/checkinDate；时间以 SQL 保存的首写值及数据库精度比较，不要求原始首响纳秒与 DATETIME(0) 逐字相等。092 允许任一完整候选胜出，不预设线程次序。
- 096 代理必须已收到上游完整 200、且 SQL 已提交后再丢下游响应；否则测到的是请求未送达。客户端预期连接中断与后续业务断言分开记录。
- 098 的 barrier 只拦每个 worker 首次实际返回 null 的查询；两个 insert 使用真实唯一键与独立连接，不把它们包在测试线程的同一个未提交事务里。记录实际 DuplicateKeyException 分支计数。
- 100 用 `mockStatic(LocalDateTime.class, CALLS_REAL_METHODS)` 只固定 `now(+08:00)`，保留其他静态日期工厂，避免污染 JDBC/Jackson；固定 T 在 mock 前构造。MockMvc 必须在受控同一线程执行。
- 102 在两次真实领取之后释放两个 worker；104 只对 P 的确认操作注入失败，不能让第一次领取也失效。异步 future 全部收集；worker 超时 10 秒释放 barrier、还原 spy 并失败；HTTP 批次最长 30 秒。
- 所有 spy、时钟、代理、guard、子进程均在 finally 恢复/关闭。失败时保留已产生证据，不把后续未执行步骤标为 PASS。

## 两项规则决策

| 用例 | 缺少的口径 | 设计中的候选预期 | 责任角色与解除条件 |
|---|---|---|---|
| S1-113 | OpenAPI 无 lat/lng 最小/最大值，DTO 只有 BigDecimal 类型 | 建议 lat [-90,90]、lng [-180,180] 闭区间；边界 201，越界 400/不落库 | M1 确认是否采用该范围与错误码，M5 同步契约及校验；M6 固定断言后执行 |
| S1-114 | “200 字符”尚未明确 Unicode 码点或 UTF-16 单元 | 两个分支的 100/101/200/201 Emoji 预期已逐项列出 | M1 确认计数单位，M5 对齐契约/后端并协同前端计数；M6 固定唯一分支后执行 |

这两条仍是 NOT_RUN，PENDING_RULE 是设计就绪状态，不是执行结果 BLOCKED。不得把当前实现观察、提议或任一未批准预期登记成 PASS/FAIL。旧目录真实微信、连续天数、正式词库和隐私独立复核等事项继续按 PR #91 的阻塞清单处理，本设计不解除旧阻塞。

## 预期依据与已有覆盖

每条 `source_refs` 指向固定 Commit 的实际路径，`expected.basis_type` 区分契约、当前代码回归、待确认规则。`existing_coverage`/`coverage_delta` 说明已有单测、US25 或 W4 补充验证与本条的关系。已有覆盖的升级登记必须实际执行新入口/矩阵后才能获得新编号的结果，不能复制过去的 PASS。

baseline-manifest.json 保存原 80 条、既有证据和设计依据的 Git blob SHA-256，以及旧 W4 报告提交/目录 tree。设计分支从 develop 独立建立，通过不可变链接关联 PR #91，不把另一份报告重复混入本 PR。

## 实现与运行记录

公共隔离检查、签名器、限定SQL/Redis快照及脱敏报告器位于`scripts/qa/w4_new40/`；深度事务和故障测试位于`W4DatabaseCasesIT.java`。113/114规则确认后再加入执行集。

未来输出使用新的 `docs/qa/evidence/w4-additional-40/<RUN_ID>/` 或私有 artifact 目录，至少包括 case_id、source_commit、开始/结束时间、实际输入/步骤、HTTP/方法返回、限定 DB/Redis 前后证据、PASS/FAIL/BLOCKED 和原因。旧 80 条与本 40 条统计分开，再按编号构成 120 条总览；不得覆盖 11 月 9 日或 W4 复测记录。

完整执行入口会创建独立Compose项目和随机凭据，从源码构建服务，在空库执行HTTP及Java测试后仅回收本项目资源。需安装Python、JDK17/Maven及Docker Compose，使用干净checkout和空闲端口：

```sh
python scripts/qa/w4_new40/run_owned.py --project ouc-w4-new40-local --output qa-private/w4-new40/results.json
```

设计/执行索引的一致性检查命令为：

```powershell
python -X utf8 docs/qa/w4-additional-40/validate_design.py
```

该校验只检查设计字段、JSON/Markdown/实际结果一致性、证据齐全及历史文件未变，不发业务请求、不生成业务执行PASS。38条业务结果来自本次专用环境实际运行，与静态检查分开记录。

校验需要本地已有基线 `7c67518fc91583a3983ea265b85f6d2a54d12eab` 和旧报告 `0843ae851af8221272fdd101052b6c49d66ab007` 的 Git 对象。本次完整仓库已有；若在浅克隆或单分支克隆运行，先用 `git fetch origin <基线SHA> <旧报告SHA>` 补齐。校验脚本不会自动连接远端或修改分支。
