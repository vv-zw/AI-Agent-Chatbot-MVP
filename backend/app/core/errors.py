import logging
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def error_payload(
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details if details is not None else {},
        }
    }


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_payload(exc.code, exc.message, exc.details)),
    )


async def validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            error_payload(
                "VALIDATION_ERROR",
                "请求参数校验失败。",
                exc.errors(),
            )
        ),
    )


async def http_error_handler(
    _: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    code = "HTTP_ERROR"
    message = "请求处理失败。"
    if exc.status_code == 404:
        code = "ROUTE_NOT_FOUND"
        message = "请求的接口不存在。"
    elif exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
        message = "当前接口不支持该请求方法。"

    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            code,
            message,
            {"status_code": exc.status_code},
        ),
        headers=exc.headers,
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error on %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_payload(
            "INTERNAL_SERVER_ERROR",
            "服务暂时不可用，请稍后重试。",
        ),
    )