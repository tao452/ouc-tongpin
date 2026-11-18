# 原 80 条回归新旧对照

历史：2026-11-09，`e4540e14e0a1404d935cfe88b7b9a4a13b65a6c0`，55 PASS / 0 FAIL / 25 BLOCKED。
本次：2026-11-18T17:12:48.476739+08:00，`7c67518fc91583a3983ea265b85f6d2a54d12eab`，63 PASS / 0 FAIL / 17 BLOCKED。

| 状态变化 | 数量 |
|---|---:|
| PASS → PASS | 55 |
| PASS → FAIL | 0 |
| PASS → BLOCKED | 0 |
| BLOCKED → PASS | 8 |
| BLOCKED → FAIL | 0 |
| BLOCKED → BLOCKED | 17 |
| FAIL → PASS | 0 |

历史搭子需求 S1-047–054 已实际发起请求并核对 buddy_demand 行数，接口缺失阻塞解除。
S1-076 的 JWT 和权限技术前置已解除，20 条安全专项及分表检查有本次证据；业务与独立复核仍待补齐。
S1-057/058 的分级规则已有 M1 确认，技术断言本次通过；保留原有正式词库/业务验收门槛。
没有历史 FAIL，因此 FAIL → PASS 为 0；没有把未执行的场景登记为 PASS。

| 编号 | 模块 | 测试目的 | 11月9日 | 本次 | 变化 |
|---|---|---|---|---|---|
| S1-001 | 登录认证 | 有效微信 code | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-002 | 登录认证 | 无效 code | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-003 | 登录认证 | 复用 code | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-004 | 登录认证 | 缺少 code | PASS | PASS | PASS → PASS |
| S1-005 | 登录认证 | 新用户标记 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-006 | 登录认证 | 认证提示 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-007 | 登录认证 | 提交校内认证 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-008 | 登录认证 | 重复绑定 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-009 | 登录认证 | 缺少学号 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-010 | 登录认证 | 拒绝原因 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-011 | 登录认证 | 认证隔离 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-012 | 登录认证 | 截图隐私 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-013 | 情绪打卡 | 开心打卡 | PASS | PASS | PASS → PASS |
| S1-014 | 情绪打卡 | 平静打卡 | PASS | PASS | PASS → PASS |
| S1-015 | 情绪打卡 | 焦虑打卡 | PASS | PASS | PASS → PASS |
| S1-016 | 情绪打卡 | 孤独打卡 | PASS | PASS | PASS → PASS |
| S1-017 | 情绪打卡 | 烦躁打卡 | PASS | PASS | PASS → PASS |
| S1-018 | 情绪打卡 | 低落打卡 | PASS | PASS | PASS → PASS |
| S1-019 | 情绪打卡 | 强度下界 | PASS | PASS | PASS → PASS |
| S1-020 | 情绪打卡 | 强度上界 | PASS | PASS | PASS → PASS |
| S1-021 | 情绪打卡 | 强度过小 | PASS | PASS | PASS → PASS |
| S1-022 | 情绪打卡 | 强度过大 | PASS | PASS | PASS → PASS |
| S1-023 | 情绪打卡 | 非法情绪枚举 | PASS | PASS | PASS → PASS |
| S1-024 | 情绪打卡 | 缺少必要字段 | PASS | PASS | PASS → PASS |
| S1-025 | 情绪打卡 | 备注上界 | PASS | PASS | PASS → PASS |
| S1-026 | 情绪打卡 | 备注超长 | PASS | PASS | PASS → PASS |
| S1-027 | 情绪打卡 | 同日幂等 | PASS | PASS | PASS → PASS |
| S1-028 | 情绪打卡 | 默认当天 | PASS | PASS | PASS → PASS |
| S1-029 | 情绪打卡 | 日期区间 | PASS | PASS | PASS → PASS |
| S1-030 | 情绪打卡 | 连续与断签 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-031 | 匿名树洞 | 默认匿名 | PASS | PASS | PASS → PASS |
| S1-032 | 匿名树洞 | 显式匿名 | PASS | PASS | PASS → PASS |
| S1-033 | 匿名树洞 | 显式实名 | PASS | PASS | PASS → PASS |
| S1-034 | 匿名树洞 | 高风险阻断 | PASS | PASS | PASS → PASS |
| S1-035 | 匿名树洞 | 审核超时 | PASS | PASS | PASS → PASS |
| S1-036 | 匿名树洞 | 内容长度边界 | PASS | PASS | PASS → PASS |
| S1-037 | 匿名树洞 | 内容超长 | PASS | PASS | PASS → PASS |
| S1-038 | 匿名树洞 | 缺少内容 | PASS | PASS | PASS → PASS |
| S1-039 | 匿名树洞 | 缺少情绪标签 | PASS | PASS | PASS → PASS |
| S1-040 | 匿名树洞 | 非法情绪标签 | PASS | PASS | PASS → PASS |
| S1-041 | 匿名树洞 | 按标签浏览 | PASS | PASS | PASS → PASS |
| S1-042 | 匿名树洞 | 游标分页 | PASS | PASS | PASS → PASS |
| S1-043 | 匿名树洞 | 分页末尾 | PASS | PASS | PASS → PASS |
| S1-044 | 匿名树洞 | 焚毁列表 | PASS | PASS | PASS → PASS |
| S1-045 | 匿名树洞 | 焚毁详情 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-046 | 匿名树洞 | 焚毁存储 | PASS | PASS | PASS → PASS |
| S1-047 | 搭子需求 | 合法搭子需求 | BLOCKED | PASS | BLOCKED → PASS |
| S1-048 | 搭子需求 | 缺少场景 | BLOCKED | PASS | BLOCKED → PASS |
| S1-049 | 搭子需求 | 缺少时间 | BLOCKED | PASS | BLOCKED → PASS |
| S1-050 | 搭子需求 | 缺少地点 | BLOCKED | PASS | BLOCKED → PASS |
| S1-051 | 搭子需求 | 技能标签上界 | BLOCKED | PASS | BLOCKED → PASS |
| S1-052 | 搭子需求 | 技能标签超限 | BLOCKED | PASS | BLOCKED → PASS |
| S1-053 | 搭子需求 | 补充说明上界 | BLOCKED | PASS | BLOCKED → PASS |
| S1-054 | 搭子需求 | 补充说明超长 | BLOCKED | PASS | BLOCKED → PASS |
| S1-055 | 内容审核 | 普通文本 | PASS | PASS | PASS → PASS |
| S1-056 | 内容审核 | HIGH 等级 | PASS | PASS | PASS → PASS |
| S1-057 | 内容审核 | MEDIUM 等级 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-058 | 内容审核 | LOW 等级 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-059 | 内容审核 | 繁简体 | PASS | PASS | PASS → PASS |
| S1-060 | 内容审核 | 全角变体 | PASS | PASS | PASS → PASS |
| S1-061 | 内容审核 | 指定谐音 | PASS | PASS | PASS → PASS |
| S1-062 | 内容审核 | 完整拼音 | PASS | PASS | PASS → PASS |
| S1-063 | 内容审核 | 符号插入 | PASS | PASS | PASS → PASS |
| S1-064 | 内容审核 | 纯空白 | PASS | PASS | PASS → PASS |
| S1-065 | 内容审核 | 字符上界 | PASS | PASS | PASS → PASS |
| S1-066 | 内容审核 | 字符超长 | PASS | PASS | PASS → PASS |
| S1-067 | 内容审核 | 畸形 JSON | PASS | PASS | PASS → PASS |
| S1-068 | 内容审核 | 请求体超限 | PASS | PASS | PASS → PASS |
| S1-069 | 隐私保护 | 别名稳定性 | PASS | PASS | PASS → PASS |
| S1-070 | 隐私保护 | 用户隔离 | PASS | PASS | PASS → PASS |
| S1-071 | 隐私保护 | 场景隔离 | PASS | PASS | PASS → PASS |
| S1-072 | 隐私保护 | 换密钥 | PASS | PASS | PASS → PASS |
| S1-073 | 隐私保护 | 弱密钥拒绝 | PASS | PASS | PASS → PASS |
| S1-074 | 隐私保护 | 普通日志脱敏 | PASS | PASS | PASS → PASS |
| S1-075 | 隐私保护 | 异常日志脱敏 | PASS | PASS | PASS → PASS |
| S1-076 | 隐私保护 | 身份分表与授权 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
| S1-077 | 基础设施 | 配置与缺失变量 | PASS | PASS | PASS → PASS |
| S1-078 | 基础设施 | 全栈启动 | PASS | PASS | PASS → PASS |
| S1-079 | 基础设施 | 网关链路 | PASS | PASS | PASS → PASS |
| S1-080 | 基础设施 | 质量门禁 | BLOCKED | BLOCKED | BLOCKED → BLOCKED |
