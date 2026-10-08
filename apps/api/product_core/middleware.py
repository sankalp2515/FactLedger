"""Count ingress bytes as they arrive, before JSON or multipart parsing."""

from uuid import uuid4

from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse


class RequestBodyTooLarge(MultiPartException):
    # MultipartParser closes every partial upload on MultiPartException.
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes=21 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/v1"):
            return await self.app(scope, receive, send)

        request_id = scope.setdefault("state", {}).setdefault("request_id", str(uuid4()))
        rejection = JSONResponse(
            {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "Request exceeds the 20 MB source limit.",
                "request_id": request_id,
            },
            status_code=413,
            headers={
                "Cache-Control": "private, no-store",
                "X-Request-ID": request_id,
                "X-Content-Type-Options": "nosniff",
            },
        )
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                declared = value.lstrip(b"0") or b"0"
                if (
                    not value.isdigit()
                    or len(declared) > len(str(self.max_bytes))
                    or int(declared) > self.max_bytes
                ):
                    return await rejection(scope, receive, send)

        total = 0
        exceeded = False
        rejected = False
        response_started = False

        async def limited_receive():
            nonlocal total, exceeded
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    exceeded = True
                    raise RequestBodyTooLarge("Request body exceeds its limit.")
            return message

        async def limited_send(message):
            nonlocal rejected, response_started
            if exceeded:
                # Framework parsers can translate ingress exceptions to 400.
                # Replace that response with the safe, consistent 413 envelope.
                if not rejected and not response_started:
                    rejected = True
                    await rejection(scope, receive, send)
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, limited_send)
        except RequestBodyTooLarge:
            if not rejected and not response_started:
                await rejection(scope, receive, send)
