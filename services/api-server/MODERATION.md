# M5 内容发布接入说明

对应 #25。`ModerationClient` 是 Spring 服务，可通过构造函数注入发布业务服务。
在执行 insert/update **之前**调用 `moderationClient.requireAllowed(content)`，
并且只持久化实际通过检测的同一份内容，不能捕获检查异常后继续写库。

- 返回 Result：允许继续，hits 仍可能含 LOW/MEDIUM 提示；等级动作待 M1 最终确认。
- 高风险阻断：抛出 `ResponseStatusException`，状态 422，不携带正文。
- 超时、不可达、非 2xx、缺字段、格式错误、矛盾结果：503，不允许继续。
- 空白、空值、超过 2000 Unicode 码点：400，不调用算法服务。
- 连接超时 2 秒、读取超时 3 秒，无自动重试；避免失败后静默放行。

`MODERATION_BASE_URL` 指向可信内部算法地址，不能使用客户端传入的 URL。
Docker 已设 `http://algo:8000`；本机默认 `http://localhost:8000`。
禁止记录请求体或上游响应正文。

单测使用 MockRestServiceServer 检查响应和失败分支；另有本机 HTTP 测试验证生产请求工厂。
W2 已将 `TreeholeService.createPost` 的占位检查替换为真实客户端调用，先审核再写 MySQL/Redis。
`GlobalExceptionHandler` 保留 422/503 HTTP 状态，响应不回显正文或上游细节。
正常发布返回契约规定的 201，树洞正文最大 500 字符。
新增业务顺序单测和控制器/异常处理测试，验证 HIGH、不可达/超时以及允许类的处理。
CI 的 `scripts/qa/verify_treehole_moderation.py` 在临时容器环境验证六个场景：
正常、HIGH、MEDIUM、LOW、正常上下文、算法容器停止；同时检查 MySQL 行数和 Redis 队列条数。
该脚本仅允许在一次性 GitHub Actions 环境执行，会短暂停止并恢复算法容器。

三级动作沿用本次 W2 任务：HIGH 拦截、MEDIUM 提示、LOW 放行。
正式词表仍待 M1 审核。当前树洞响应尚不包含提示命中字段，前端提示展示需与 M3/M5 对齐；
算法接口的 hits 已提供等级。搭子发布接口尚未实现，可复用同一客户端。
