from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Bound buffered moderation requests even when the service is reached without Nginx."""

    def __init__(self, app, limit=16384):
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope["method"] != "POST"
                or scope["path"] != "/api/moderation/check"):
            return await self.app(scope, receive, send)
        lengths = [v for k, v in scope.get("headers", []) if k.lower() == b"content-length"]
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit():
                return await self.reject(scope, receive, send, 400)
            # Compare strings first to avoid integer conversion of unbounded headers.
            length = lengths[0].lstrip(b"0") or b"0"
            if len(length) > 5 or int(length) > self.limit:
                return await self.reject(scope, receive, send, 413)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.limit:
                return await self.reject(scope, receive, send, 413)
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()

        return await self.app(scope, replay, send)

    @staticmethod
    async def reject(scope, receive, send, status):
        response = JSONResponse({"detail": "Invalid request"}, status_code=status)
        await response(scope, receive, send)
