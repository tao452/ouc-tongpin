# 内容过滤服务

对应 US-24（#25）。Python 3.11 起，FastAPI + DFA 前缀树；不调用外部模型。

## 本地运行

在本目录执行（先创建并激活独立虚拟环境）：

```powershell
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

健康检查 `GET /health`。接口与根目录 `packages/contract/openapi.yaml` 对齐：

```http
POST /api/moderation/check
Content-Type: application/json

{"text":"一起去图书馆"}
```

返回 `passed`、`normalized`、`hits`；每项命中包含 `word` 与 `level`。
HIGH 拦截（passed=false），MEDIUM 提示，LOW 放行；后两者 passed=true。
调用方仍需根据 hits 展示提示。空白、非字符串、超出 2000 字符或未知字段返回 422，
不回显提交内容。网关另限制请求体 16 KiB。服务部署在内网，不直接对公网提供访问。
Uvicorn 必须关闭访问日志，避免 URL 查询参数泄露信息；不应记录输入正文。

## 词库与规则

词表位于 `app/data/words.json`，目前只有 **5 个示例词**，供规则和接口联调使用。
正式词表与等级须由 M1 审核，当前版本不构成完整内容审核能力。
支持 NFKC、英文大小写、OpenCC 繁简转换、移除符号/空白/不可见分隔、指定谐音别名。
拼音只匹配完整连续拉丁字母段；不使用拼音首字母缩写，也不对所有汉字做同音归并。
这样仍可能漏掉变体，且词汇上下文可能造成误判，需要标注语料评估。
含普通贬义词的 LOW/MEDIUM 命中不会直接阻断；不能用词匹配替代危机识别或人工复核。

## 验证

```powershell
python -m ruff check app tests scripts
python -m pytest -q
python scripts/evaluate.py
```

测试覆盖正常内容、符号/拼音/繁体变体、等级与去重、错误词表、长度边界、异常请求和契约字段。
覆盖率门槛为语句与分支合计 80%。评估脚本使用 16 条开发回归示例，并测量单进程热身后的函数耗时。
这些示例不独立于开发过程，结果不能代表真实召回率、误杀率或并发 HTTP 延迟。
任务书的召回 ≥95%、误杀 <2%、耗时 <30ms 仍需用审核后的独立样本验收。

## 后端交接

M5 在树洞、搭子内容入库前经网关或容器内 `http://algo:8000/api/moderation/check` 调用。
遇到不可达、超时或非 200 时应阻止本次发布并返回可重试错误，不能静默放行。
当前仓库没有树洞/搭子发布接口，发布前拦截尚未完成联调。
