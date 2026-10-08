"""Ingress limits apply to actual streamed bytes before body parsers consume them."""

import json

import pytest
from fastapi import FastAPI, File, UploadFile
from product_core.middleware import RequestBodyLimitMiddleware


async def invoke(app, chunks, headers=(), path="/v1/upload"):
    sent, read = [], []
    messages = iter(chunks)

    async def receive():
        chunk = next(messages, None)
        if chunk is None:
            return {"type": "http.disconnect"}
        read.append(chunk)
        return {"type": "http.request", "body": chunk, "more_body": True}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": list(headers),
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1000),
    }
    await app(scope, receive, send)
    return sent, read


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [[], [(b"content-length", b"1")], [(b"transfer-encoding", b"chunked")]])
async def test_actual_stream_limit_stops_before_forwarding_excess_chunk(headers):
    forwarded = []

    async def consumer(scope, receive, send):
        while True:
            message = await receive()
            forwarded.append(message["body"])

    app = RequestBodyLimitMiddleware(consumer, max_bytes=8)
    sent, read = await invoke(app, [b"abc", b"def", b"ghi", b"never-read"], headers)
    assert forwarded == [b"abc", b"def"]
    assert read == [b"abc", b"def", b"ghi"]
    assert sent[0]["status"] == 413
    payload = json.loads(sent[1]["body"])
    assert payload["code"] == "PAYLOAD_TOO_LARGE" and payload["request_id"]


@pytest.mark.asyncio
async def test_chunked_multipart_is_rejected_and_partial_spool_closed(monkeypatch):
    import starlette.formparsers as forms

    spools = []
    original = forms.SpooledTemporaryFile

    def tracked_spool(*args, **kwargs):
        spool = original(*args, **kwargs)
        spools.append(spool)
        return spool

    monkeypatch.setattr(forms, "SpooledTemporaryFile", tracked_spool)
    app = FastAPI()
    invoked = []
    upload_file = File(...)

    @app.post("/v1/upload")
    async def upload(file: UploadFile = upload_file):
        invoked.append(True)
        return {"accepted": True}

    prefix = b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="x.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
    limited = RequestBodyLimitMiddleware(app, max_bytes=len(prefix) + 8)
    sent, read = await invoke(
        limited,
        [prefix + b"%PDF-", b"x" * 20, b"never-read"],
        [(b"content-type", b"multipart/form-data; boundary=boundary")],
    )
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["code"] == "PAYLOAD_TOO_LARGE"
    assert not invoked and len(read) == 2
    assert spools and all(spool.closed for spool in spools)


@pytest.mark.asyncio
async def test_allowed_body_is_forwarded_incrementally_without_buffering():
    forwarded = []

    async def consumer(scope, receive, send):
        for _ in range(2):
            forwarded.append((await receive())["body"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"stream-one", "more_body": True})
        await send({"type": "http.response.body", "body": b"stream-two"})

    sent, read = await invoke(RequestBodyLimitMiddleware(consumer, max_bytes=8), [b"abcd", b"efgh"])
    assert read == forwarded == [b"abcd", b"efgh"]
    assert [message.get("body") for message in sent[1:]] == [b"stream-one", b"stream-two"]


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [b"9", b"invalid", b"9" * 5000])
async def test_invalid_or_oversized_declared_length_rejects_without_reading(length):
    async def consumer(scope, receive, send):
        pytest.fail("Rejected body must not reach its parser.")

    sent, read = await invoke(
        RequestBodyLimitMiddleware(consumer, max_bytes=8), [b"unread"], [(b"content-length", length)]
    )
    assert sent[0]["status"] == 413 and read == []


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [None, b"1"])
async def test_api_stack_returns_safe_413_for_actual_oversized_json(length):
    from product_core import main

    headers = [(b"content-type", b"application/json"), (b"host", b"testserver")]
    if length is not None:
        headers.append((b"content-length", length))
    sent, read = await invoke(main.app, [b"x" * (11 * 1024 * 1024)] * 2, headers, path="/v1/auth/dev")
    assert sent[0]["status"] == 413
    payload = json.loads(b"".join(message.get("body", b"") for message in sent[1:]))
    assert payload["code"] == "PAYLOAD_TOO_LARGE"
    assert len(read) == 2
    assert (b"cache-control", b"private, no-store") in sent[0]["headers"]
