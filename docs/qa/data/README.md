# W2 内容安全开发回归语料

`w2-moderation-regression.jsonl` 共 300 条：200 条允许文本和 100 条拦截文本。
均为本轮开发中编写的合成数据，没有真实用户信息；不是用户数据、盲测集或 M1 审核后的独立验收集。
200 条允许文本覆盖校园社交、情绪求助、学习、环保、正常词义和英文边界。
100 条拦截文本由 25 种 HIGH 词变体与 4 种句式组合，覆盖繁简、全角、谐音、拼音、声调、插入分隔符及重复词。
这些相关变体不能解释为 100 条独立抽样证据。

标签是开发者对现有三级动作的预期，不是运行过滤器后反写的结果。
评估器拒绝重复 ID 和完全相同的正文。语料更新必须作为显式代码变更接受评审。
词库仍使用原有 5 词开发基线，正式词库、局部白名单与三级业务动作待 M1 审核。

CI 要求同时满足：允许样本 ≥200、拦截样本 ≥100、HIGH 拦截召回率 ≥95%、误杀率严格 <2%。
误杀率 = 被 HIGH 拦截的允许文本数 / 全部允许文本数；LOW/MEDIUM 命中不计为拦截。
函数和真实容器 HTTP 分别执行、归档数据哈希和混淆矩阵；函数覆盖率门槛为 90%（含分支）。
这些结果只用于本版本回归，不替代经 M1 复核的独立业务效果验收。

复现（仓库根目录，先激活算法虚拟环境）：

```powershell
python services/algo/scripts/evaluate_dataset.py docs/qa/data/w2-moderation-regression.jsonl --min-benign 200 --min-blocked 100 --output qa-private/w2-moderation-function.json
python services/algo/scripts/evaluate_dataset.py docs/qa/data/w2-moderation-regression.jsonl --base-url http://127.0.0.1:8080 --min-benign 200 --min-blocked 100 --output qa-private/w2-moderation-http.json
```
