# 合成数据 PII 扫描基线包 v1

日期：2026-11-09。对应 M6 W3“协助 M1 搭 PII 扫描基线”，Refs #26。
本包验证离线扫描工具的候选匹配、输入边界和报告保密性，使用开发者编写的合成数据。
没有连接业务数据库、读取真实用户数据或调用网络，也不代表真实业务隐私验收通过。

## 包含什么

| 文件 | 用途 |
|---|---|
| `docs/qa/data/pii-baseline.v1.json` | 固定版本的合成样本与预期候选规则；标签先定义，运行时不反写 |
| `scripts/qa/pii_scan.py` | 离线 UTF-8 文本候选扫描器，报告只含文件顺序号、行号和规则名 |
| `scripts/qa/pii_baseline.py` | 校验样本，实际写入临时文本后调用文件扫描器，比较逐条预期 |
| `scripts/qa/run_pii_baseline.py` | 一键复现，输出版本、文件哈希、规则统计和逐条结果 |
| `docs/qa/evidence/pii-baseline-20261109/baseline-local.json` | 实际本地运行结果；CI 另生成并上传独立报告 |
| `人工复核模板.md` | 候选项复核与误报登记模板；含合成演示，不伪造业务审批 |

## 62 条样本的含义

| 类型 | 条数 | 验证什么 |
|---|---:|---|
| positive | 36 | 六类规则的正样本与多规则混合行，应产生指定候选命中 |
| negative | 16 | 普通日志、已脱敏文本、长度边界及相似字段名，应无候选命中 |
| review | 4 | 订单号、占位值、公共邮箱、示例密码等有上下文歧义的候选项 |
| out_of_scope | 6 | 姓名、地址、图像、密文、分隔手机号、无字段名的学号等已知缺口 |

62 条是版本化的功能回归样本，不是独立抽样的业务语料。`baseline_passed=true` 只表示
所有结果符合这些预期，不表示“没有个人信息”，也不代表生产识别率或合规结论。
review 例子保留候选命中，交给人工判断；不会因此把同样的值全局加入白名单。
out_of_scope 的“未匹配”记录的是检测能力缺口，不能作为无隐私风险的证据。
本基线与跨模块 80 条目录分别统计；正式身份/授权用例仍按原依赖验收。

## 规则与格式范围

- phone：疑似中国大陆 11 位手机号及 +86 / 0086 / 86 国码前缀，国码后可有空格或短横线。
- identity_number：18 位数字/末位 X 的形态，不验证行政区、日期、校验码，也可能命中普通订单号。
- email：常见文本邮箱形态，公共角色邮箱也会成为候选项。
- student_field：studentId / student_id / studentNo / student_no / studentNumber / student_number / 学号。
- credential_field：token / accessToken / refresh_token / password / secret / client_secret /
  openid / open_id / session_key / sessionKey / api_key / apiKey 等具名字段。
- authorization：Bearer / Basic 值；检查完整前缀边界，避免把 NotBearer 当成 Bearer。

输入应为 UTF-8 文本，逐行带字段名的 JSONL、key=value 导出或日志更适合复核。
CSV 的裸值没有字段上下文时，不能靠本工具推断学号；图片、自由文本姓名/地址、密文字段需另行检查。
字段名采用完整边界，避免 notstudentId / notsecret 等相似前缀误匹配。
报告不输出原文、匹配值、输入文件名或绝对路径，输入顺序和文件名的映射由执行人在本地保留。

## 一键复现

在仓库根目录，用 Python 3.11+（仅标准库）执行：

```powershell
python scripts/qa/run_pii_baseline.py --output qa-private/pii-baseline.json
```

默认样本路径相对脚本定位，因此从其他工作目录执行也可用；`--output` 相对当前工作目录。
样本拒绝重复 ID/正文、未知规则、混合生产标签、多行文本及缺少类型/规则覆盖。
结果带数据哈希、三个代码文件哈希、Python 版本、UTC 时间和 Git 版本/工作区状态。
没有 Git 时仍能以文件哈希复现。报告不复制任何样本原文。

| 命令 | 退出码 0 | 退出码 1 | 退出码 2 |
|---|---|---|---|
| run_pii_baseline.py | 全部合成预期匹配 | 有结果不符合预期 | 输入/扫描结果/输出无效 |
| pii_scan.py | 未匹配规则 | 存在候选项，需人工复核 | 读取/编码/输出错误 |

基线故意包含候选数据，因此会观察到 40 条候选命中；这与基线验证成功是相容的。
PR CI 和已有 nightly 均执行本基线并上传报告；nightly 变更合入默认分支后按既有计划生效。

## 实际业务扫描时怎样交接

1. M1 确认表/字段/日志范围、必须脱敏的内容、允许例外和复核人。
2. M5 提供表结构及受限的隔离测试导出/日志；本工具不直接连接数据库，不在仓库保存真实输入。
3. 执行人本地保存文件顺序映射，运行下述扫描，依据报告位置在受控环境复核原文。
4. M1 按模板登记“确认问题/上下文允许/误报/待补证”，M5 修复实际存储或日志问题后复扫。

```powershell
python scripts/qa/pii_scan.py qa-private/authorized-export.jsonl qa-private/test-log.txt --output qa-private/pii-candidates.json
```

本轮只完成合成工具基线。真实业务扫描、授权/越权测试和正式词库效果评估分别留证据。
