"""Request correlation and structured logs without prompts or secrets."""
import json
import logging
from time import perf_counter
from uuid import uuid4

from starlette.responses import JSONResponse

logger = logging.getLogger("workshop")


def event(name, **fields):
    logger.info(json.dumps({"event": name, **fields}))


async def request_log(request, call_next):
    started = perf_counter()
    request.state.request_id = uuid4().hex
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request.state.request_id
        return response
    finally:
        route = request.scope.get("route")
        event("request", request_id=request.state.request_id, method=request.method,
              route=getattr(route, "path", "unmatched"), status=status,
              duration_ms=round((perf_counter() - started) * 1000))


class LimitBody:
    def __init__(self, app, limit: int):
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        data = bytearray()
        while True:
            incoming = await receive()
            if incoming["type"] == "http.disconnect":
                return
            if len(data) + len(incoming["body"]) > self.limit:
                return await JSONResponse({"detail": "Request body too large."}, 413)(scope, receive, send)
            data.extend(incoming["body"])
            if not incoming.get("more_body"):
                break

        async def replay():
            nonlocal data
            if data is not None:
                message = {"type": "http.request", "body": bytes(data), "more_body": False}
                data = None
                return message
            return await receive()

        await self.app(scope, replay, send)
