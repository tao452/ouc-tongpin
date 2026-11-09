# 第二周内容过滤测试样本

PII 扫描用的是另一份合成基线 `pii-baseline.v1.json`，复现方法和适用边界见 `../pii-baseline/README.md`。

`w2-moderation-regression.jsonl` 共 300 条合成文本：200 条正常文本和 100 条需要拦截的文本。
正常文本包括校园社交、情绪求助、学习、环保、常见词义和英文边界。
拦截文本由 25 种 HIGH 词变体和 4 种句式组合，覆盖繁简、全角、谐音、拼音、声调、分隔符和重复词。
这 100 条来自组合构造，并非随机收集的 100 条独立文本。

每条样本先填写预期结果，再运行过滤器。评估器会拒绝重复 ID 和相同正文。
当前使用 5 词示例库；正式词表和正常短语例外等 M1 确认。
这批样本用于开发回归。M1 确认词表和分级规则后，M6 更新词库并复测；可另选一批文本做补充测试。

CI 要求：正常文本不少于 200 条、拦截文本不少于 100 条、HIGH 检出率不低于 95%、误杀率低于 2%。
误杀率 = 被 HIGH 拦截的正常文本数 / 正常文本总数；LOW/MEDIUM 命中不算拦截。
本地函数测试和实际容器 HTTP 测试分别保存混淆矩阵及文件哈希。
算法 app 的语句与分支合计覆盖率门槛为 90%。

在仓库根目录运行，先激活算法虚拟环境：

```powershell
python services/algo/scripts/evaluate_dataset.py docs/qa/data/w2-moderation-regression.jsonl --min-benign 200 --min-blocked 100 --output qa-private/w2-moderation-function.json
python services/algo/scripts/evaluate_dataset.py docs/qa/data/w2-moderation-regression.jsonl --base-url http://127.0.0.1:8080 --min-benign 200 --min-blocked 100 --output qa-private/w2-moderation-http.json
```

第二条命令需要先启动临时测试环境，默认网关地址为 `http://127.0.0.1:8080`。
