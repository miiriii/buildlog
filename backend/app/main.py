from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from app.accounts.router import router as accounts_router
from app.core.config import Settings
from app.db.session import create_db_engine
from app.materials.router import router as materials_router
from app.materials.analysis_worker import AnalysisWorker
from app.materials.storage import UPLOAD_ROOT


class HealthResponse(BaseModel):
    status: str
    service: str


def create_app(settings: Settings | None = None, *, analysis_adapter=None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    @asynccontextmanager
    async def lifespan(application):
        engine = create_db_engine(settings.database_url.get_secret_value())
        application.state.db_engine = engine
        worker = AnalysisWorker(engine, settings, getattr(application.state, 'uploads_root', UPLOAD_ROOT), analysis_adapter)
        application.state.analysis_worker = worker
        worker.start()
        try:
            yield
        finally:
            try:
                await worker.stop()
            finally:
                engine.dispose()

    application = FastAPI(title="BuildLog API", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key.get_secret_value(),
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.session_cookie_secure,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Range", "If-Range"],
        expose_headers=["Content-Disposition", "Content-Range", "Accept-Ranges", "Content-Length", "ETag", "Last-Modified"],
    )

    @application.exception_handler(RequestValidationError)
    async def invalid_input(_request: Request, error: RequestValidationError):
        messages = {
            "email": "올바른 이메일 주소를 입력해 주세요.",
            "password": "비밀번호는 8~64자로 입력해 주세요.",
            "nickname": "닉네임은 한글·영문·숫자·밑줄로 2~20자를 입력해 주세요.",
        }
        field = next((item["loc"][-1] for item in error.errors()
                      if item["loc"][-1] in messages), None)
        # Never return Pydantic's raw input, exception context or a password value.
        return JSONResponse(status_code=422, content={
            "detail": messages.get(field, "입력 항목을 확인해 주세요."),
        })

    @application.exception_handler(SQLAlchemyError)
    async def database_failure(_request: Request, _error: SQLAlchemyError):
        return JSONResponse(status_code=503, content={
            "detail": "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        })

    application.include_router(accounts_router)
    application.include_router(materials_router)

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="BuildLog")

    return application


app = create_app()
