# US25 身份权限与运行数据 PII 验证

更新于 2026-11-16，Refs #26。补齐服务器端身份验证、业务归属隔离及可重复的安全扫描。
平台接口已提供真实微信 code2session 实现；尚未提供微信测试凭据，真实平台联调及独立业务
验收保持待办。CI 使用显式启用的模拟平台身份，运行真实 JWT、安全过滤链、MySQL 和 Redis。

## 身份来源和接口权限

- `WeChatSessionClient` 默认请求固定微信 HTTPS 地址，设置连接／读取超时，禁止重定向，
  验证状态及响应结构。无效 code 返回 401，依赖异常返回 503，错误不回显 code、密钥或原响应。
- 仅保留平台 openid 的场景化 HMAC 查找值；不持久化原始 code、openid、session_key 或 unionid。
  私有 `auth.openid` 字段承载 HMAC 值，唯一索引和独立注册事务防止并发建档产生重复／孤儿账号。
- `JWT_SECRET` 由环境注入，拒绝空值、过短值、示例默认值和历史公开密钥。签名固定 HS256，
  验证 issuer、audience、有效期、签发时间、合法主体以及账号状态；拒绝压缩 JWT。
- Spring Security 使用无状态 Bearer 鉴权，关闭密码登录、Basic、会话缓存；每次请求校验账号
  仍存在且未停用。用户声明的 role 不授予管理员权限，保留的管理／隐私路由拒绝普通用户。
- 打卡、树洞、搭子发布的内部 ID 全部来自已验证的主体。客户端 `userId`、对象 ID、查询参数
  均不能改变归属；打卡查询仅查本人，响应移除内部 owner ID，匿名响应继续使用安全 DTO。

微信平台身份验证不代表校内学籍认证。未绑定学号仍返回 `needStudentVerify=true`，本次不新增
学号／手机号采集入口，也不将普通登录用户提升为学校认证或管理角色。

## 部署配置与既有数据

正常部署填写 `.env` 中的随机 `JWT_SECRET`（至少 32 字节）、稳定的 `ANON_ID_SECRET` 及
`WX_APPID`／`WX_SECRET`；`WX_MOCK_ENABLED=false` 为默认值。模拟身份只应在隔离开发／CI
显式启用。缺少真实微信配置时应用拒绝启动，不自动回退到模拟身份。
Actions 的 `create-test-env.py` 自动生成临时随机密钥并明确打开身份 fixture，不需要本机启动服务。

新空库通过 `01-schema.sql` 建立身份唯一索引，并由 `02-runtime-permissions.sh` 配置：

| 主体 | 允许 | 拒绝 |
|---|---|---|
| 可信后端数据库账号 | 业务 DML，包含登录及匿名私有映射的必要读取 | CREATE／ALTER／DROP 等 DDL |
| `ouc_public_reader` 角色 | 仅查询有效公开帖子的 `treehole_public` 投影 | users、auth、treehole_identity、底层内容表 |

该角色不创建对外登录账号；CI 临时创建受限账号验证授权矩阵，并在 finally 清理。
后端账号属于可信服务边界，不能交给前端、报表或普通管理端直接查询私有表。

已有数据卷须由部署负责人备份、停写，并以管理员执行
`infra/db/migrations/20261115-auth-identity-unique.sql`；存在重复身份时脚本拒绝迁移且保留数据。
随后在对应 MySQL 容器内运行 `/docker-entrypoint-initdb.d/02-runtime-permissions.sh` 配置权限。
此前身份分表迁移仍须完成。应用账号已不具备 DDL 权限，升级不能使用该账号执行迁移。

旧演示账号不自动转换为真实微信账号，原记录保留；禁止按客户端提供的旧 userId 自动补绑。
原 JWT 因密钥与校验规则升级需要重新登录。openid 查找与匿名别名使用同一稳定 HMAC 密钥、
不同 purpose；轮换 `ANON_ID_SECRET` 前必须制定私有身份查找和别名迁移方案，不能直接换钥。
本次未操作共享数据库。回滚代码前须核对身份方案兼容，不能通过恢复公开旧 JWT 密钥回滚。

## Actions 验证与扫描材料

`deploy-test.yml` 在可回收五服务栈上自动运行原有回归及：

```text
python scripts/qa/run_us25_security.py --output qa-private/us25-security.json
```

执行器限制在隔离 Actions 环境，创建合成账号，不把“本机必须启动服务”作为完成条件。
20 项专项覆盖：未登录／畸形凭证、正确签名正控制及过期／错 audience／错误签名、查询串令牌、
HMAC 身份存储、双账号同日打卡、伪造 owner 查询和写入、请求间上下文隔离、匿名映射、
角色声明不能提升权限、未实现对象修改的拒绝、24 次并发隔离读取、并发登录唯一性、停用账号、
只读数据库投影、私有表拒绝、应用账号 DDL 拒绝，以及实际运行数据 PII 扫描。

PII 材料来自测试服务真实返回、实际私有 auth 行、应用和网关容器日志，身份均为合成 fixture。
在测试账号私有行中设置学号／电话 canary 作为正控制，核对私有材料能被识别，公开响应及
日志不包含这些 canary、JWT 或配置密钥；同时运行原有正则扫描。临时材料按私有权限创建并
删除，artifact 仅保留通道计数、规则结论、逐项状态、版本及源码哈希，不保存原文或凭据。

`us25-security.json` 中 `technical_security_checks_passed` 表示这 20 项技术验证结果；
`live_wechat_verified=false`、`independent_business_review=pending` 和
`production_acceptance=false` 保留实际验收边界。无匹配不能证明无姓名、地址或其他隐私。
M1 后续须在明确授权的真实业务范围执行扫描并人工复核；M3 按 Issue 独立复现。

本地预检查为 Java 141 项通过，Python 251 项通过、4 项 Windows 链接限制跳过，app 覆盖率
98.53%；Ruff 和 actionlint 通过。云端实际专项结果及最新提交以 PR 的 CI artifact 为准。
[#26](https://github.com/tao452/ouc-tongpin/issues/26) 在真实平台与独立验收完成前继续打开。
