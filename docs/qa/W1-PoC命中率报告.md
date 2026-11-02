# W1 敏感词 PoC 测试报告

日期：2026-11-02。测试脚本：`scripts/w1/run_poc.py`；样例：`scripts/w1/poc-cases.json`。
原始结果见 [poc-local.json](evidence/w1/poc-local.json)。

## 测试口径

本轮使用 5 词开发库，构造 64 条变体样例和 64 条正常校园文本。
变体包括简体、繁体、符号插入、空格、零宽字符、重复词、上下文、完整拼音、全角拼音、大小写及显式谐音。
“变体检出”按结果 hits 包含规范词计算，覆盖 HIGH/MEDIUM/LOW；“正常文本误拦截”按 passed=false 计算。
当前分级动作沿用代码配置：HIGH 拦截，MEDIUM/LOW 返回命中并放行。
样例由开发过程构造，结果用于 W1 技术 PoC。正式业务效果评估使用独立标注样本。

## 实测结果

| 指标 | 结果 |
|---|---|
| 变体检出 | 64/64，100% |
| 正常文本误拦截 | 0/64，0% |
| 配置判定一致 | 128/128 |
| 函数 P95 | 4.394 ms |
| 耗时输入 | 1980 字符，预热 50 次，执行 1000 次 |
| 运行环境 | Python 3.12.14，Windows |

JSON 记录逐条结果、词库哈希、样例哈希及时间。耗时为本机单进程函数调用，HTTP 和并发性能另行测试。

## 复现与后续

```powershell
python -m pip install -r services/algo/requirements.txt
python scripts/w1/run_poc.py --output qa-private/w1-poc.json
```

CI 的 w1-poc 检查复跑同一份样例并上传结果文件。
服务继续通过 `MODERATION_DICTIONARY_PATH` 接入正式词库；更换词库后记录新哈希并重新运行评估。
