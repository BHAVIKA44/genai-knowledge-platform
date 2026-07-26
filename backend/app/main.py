from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import engine
from app.documents.routes import router as documents_router
from app.documents.schemas import ErrorDetail, ErrorResponse
from app.search.routes import router as search_router

settings = get_settings()
app = FastAPI(title="GenAI Knowledge Platform API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(documents_router)
app.include_router(search_router)


def error_response(
    request: Request, code: str, message: str, action: str | None, status_code: int
) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, action=action, request_id=request_id)
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    return error_response(request, error.code, error.message, error.action, error.status_code)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, _: RequestValidationError
) -> JSONResponse:
    return error_response(
        request,
        "INVALID_REQUEST",
        "We could not read that upload request.",
        "Choose one supported file and try again.",
        422,
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
    return error_response(
        request,
        "INTERNAL_ERROR",
        "We could not finish that request.",
        "Please try again shortly.",
        500,
    )


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
