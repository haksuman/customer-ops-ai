from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Request

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
thread_id_ctx: ContextVar[str] = ContextVar("thread_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "thread_id": thread_id_ctx.get(),
        }
        for key in ("node", "detected_intents", "entity_keys", "latency_ms", "path", "method", "status_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


async def logging_middleware(request: Request, call_next):
    logger = logging.getLogger("app.request")
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request_id_ctx.set(request_id)
    start = time.perf_counter()
    logger.info("request_started", extra={"path": request.url.path, "method": request.method})
    response = await call_next(request)
    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "request_finished",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    response.headers["x-request-id"] = request_id
    return response
