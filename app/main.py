from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.mysql_connector import get_pool_status, init_connection_pool, ping_database
from app.middleware.logging import RequestLoggingMiddleware, app_logger, configure_logging, log_json
from app.routes.attendance import router as attendance_router
from app.routes.courses import router as courses_router
from app.routes.dashboard import router as dashboard_router
from app.routes.enrollments import router as enrollments_router
from app.routes.students import router as students_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)
    init_connection_pool()
    log_json(
        "info",
        "application_startup",
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )
    yield
    log_json("info", "application_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(students_router)
app.include_router(courses_router)
app.include_router(enrollments_router)
app.include_router(attendance_router)
app.include_router(dashboard_router)


@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check():
    db_ok = ping_database()
    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "success": db_ok,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "database": "up" if db_ok else "down",
            "pool": get_pool_status(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    app_logger.exception(
        {
            "event": "unhandled_exception",
            "path": str(request.url.path),
            "method": request.method,
            "request_id": getattr(request.state, "request_id", "-"),
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", "-"),
        },
    )
