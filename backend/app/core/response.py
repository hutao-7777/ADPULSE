"""Unified API response envelope and auto-wrapping router."""

import json
import logging
from typing import Any, Generic, Optional, TypeVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute, APIRouter as FastAPIRouter
from pydantic import BaseModel

from app.core.exceptions import AdPulseException

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    All successful responses are wrapped as ``{code, message, data}``.
    Error responses use the same envelope with a non-zero ``code``.
    """

    code: int
    message: str
    data: Optional[T] = None

    @classmethod
    def success(cls, data: Any, message: str = "success") -> dict:
        return {"code": 0, "message": message, "data": data}

    @classmethod
    def error(cls, code: int, message: str, data: Any = None) -> dict:
        return {"code": code, "message": message, "data": data}


class WrappedAPIRoute(APIRoute):
    """`APIRoute` subclass that wraps normal JSON responses in `ApiResponse`.

    Exception responses are handled separately by `register_exception_handlers`.
    """

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request):
            response = await original_route_handler(request)

            if isinstance(response, JSONResponse):
                body = response.body
                if body:
                    try:
                        payload = json.loads(body)
                    except Exception:  # pragma: no cover - non-JSON body
                        return response

                    # Already wrapped; avoid double wrapping.
                    if (
                        isinstance(payload, dict)
                        and set(payload.keys()) == {"code", "message", "data"}
                    ):
                        return response

                    wrapped = ApiResponse.success(payload)
                    headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
                    return JSONResponse(
                        content=wrapped,
                        status_code=response.status_code,
                        headers=headers,
                        background=response.background,
                    )

            return response

        return custom_route_handler


class WrappedAPIRouter(FastAPIRouter):
    """Router that uses `WrappedAPIRoute` by default."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("route_class", WrappedAPIRoute)
        super().__init__(*args, **kwargs)


# Re-export so API modules can replace ``from fastapi import APIRouter``.
APIRouter = WrappedAPIRouter


# ------------------------------------------------------------------
# Exception handlers
# ------------------------------------------------------------------

async def adpulse_exception_handler(_request: Request, exc: AdPulseException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(exc.code, exc.message),
    )


async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(exc.status_code, exc.detail),
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiResponse.error(
            422,
            "请求参数校验失败",
            exc.errors(),
        ),
    )


async def generic_exception_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled server exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(500, "服务器内部错误"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach unified exception handlers to a FastAPI application."""
    app.add_exception_handler(AdPulseException, adpulse_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
