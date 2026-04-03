import json
import logging
import time
import uuid
from contextvars import ContextVar
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")
_request_counter = 0
_counter_lock = Lock()

app_logger = logging.getLogger("sms")


def configure_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_request_id() -> str:
    return request_id_ctx_var.get()


def increment_request_count():
    global _request_counter
    with _counter_lock:
        _request_counter += 1


def get_request_count() -> int:
    return _request_counter


def log_json(level: str, event: str, **kwargs):
    payload = {"event": event, **kwargs}
    getattr(app_logger, level.lower(), app_logger.info)(json.dumps(payload, default=str))


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_ctx_var.set(request_id)
        start = time.perf_counter()

        request.state.request_id = request_id

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            app_logger.exception(
                json.dumps(
                    {
                        "event": "request_exception",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    }
                )
            )
            request_id_ctx_var.reset(token)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        increment_request_count()

        log_json(
            "info",
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
        )

        request_id_ctx_var.reset(token)
        return response
