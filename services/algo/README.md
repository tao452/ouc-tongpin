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
不回显提交内容。网关和服务自身均限制请求体 16 KiB，包括直连、分块和伪造长度头。
服务部署在内网，不直接对公网提供访问。
Uvicorn 必须关闭访问日志，避免 URL 查询参数泄露信息；不应记录输入正文。

## 词库与规则

默认词表位于 `app/data/words.json`，目前只有 **5 个示例词**，供规则和接口联调使用。
通过 `MODERATION_DICTIONARY_PATH` 可以完整替换词表；启动时严格校验字段与冲突。
M1 已在 [PR #49](https://github.com/tao452/ouc-tongpin/pull/49#pullrequestreview-5733159309)确认 S1 阶段使用 HIGH 阻断、MEDIUM/LOW 放行的处理方式，并将正式词库、词条等级和独立样本评估留到后续验收。
支持 NFKC、英文大小写、OpenCC 繁简转换、移除符号/空白/不可见分隔、指定谐音别名。
拼音保留拉丁字母段边界，支持连续/分隔拼音、拉丁声调和句中重复词；不匹配英文单词子串，
不使用拼音首字母缩写，也不对所有汉字做同音归并。
词条可配置 `allow_phrases`（例如“去死海”）：只豁免同一词条中被完整正常短语包住的那次命中，
同条内容中的其他攻击仍会被拦截；禁止把整个敏感词直接设成豁免项。
这样仍可能漏掉变体，且词汇上下文可能造成误判，需要标注语料评估。
当前 LOW/MEDIUM 命中返回 hits 并放行，调用方按等级处理提示；危机识别和人工复核按后续迭代安排接入。

## 验证

```powershell
python -m ruff check app tests scripts
python -m pytest -q
python scripts/evaluate.py
```

测试覆盖正常内容、符号/拼音/繁体变体、等级与去重、错误词表、长度边界、异常请求和契约字段。
W2 将语句与分支合计覆盖率门槛提高至 90%，CI 归档覆盖率、JUnit 和效果报告。
`scripts/evaluate.py` 使用 16 条开发回归示例，并测量单进程热身后的函数耗时。
W2 新增 300 条公开合成回归样本，要求允许类 ≥200、拦截类 ≥100、召回 ≥95%、误杀严格 <2%；
CI 在函数和实际构建的容器 HTTP 中分别执行。样本来源、定义和复现命令见 `docs/qa/data/README.md`。
当前结果用于开发回归和函数耗时检查；业务召回率、误杀率及并发 HTTP 延迟待独立测试。
正式业务效果按 #25 的后续安排，用正式词库和独立标注样本检查召回 ≥95%、误杀 <2%、耗时 <30ms。

## 后端交接

M5 可使用 Java `ModerationClient.requireAllowed(text)`，在树洞、搭子入库前调用。
Compose 已将客户端地址设为 `http://algo:8000`；本机默认 `http://localhost:8000`。
遇到不可达、超时或非 200 时应阻止本次发布并返回可重试错误，不能静默放行。
W2 已在 `TreeholeService.createPost` 的 MySQL/Redis 写入前接入真实客户端，
全局异常处理保留 422/503，防止异常被吞成 HTTP 200。CI 用隔离 MySQL/Redis 验证放行、
HIGH 拒绝以及算法容器停止时拒绝发布；搭子发布接口待业务实现后复用。

独立语料评估、PII 扫描和 80 条用例初稿的操作说明见 `docs/qa/工具与验收用法.md`。
