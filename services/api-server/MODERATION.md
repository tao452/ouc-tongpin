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
禁止记录请求体或上游响应正文。未实现树洞/搭子控制器，因此当前还没有业务写库链路可验收。

单测使用 MockRestServiceServer 检查响应和失败分支；另有本机 HTTP 测试验证生产请求工厂。
这两者验证客户端，不等于已验证真实树洞/搭子接口。后续联调须同时检查响应状态和数据库无新增正文。
