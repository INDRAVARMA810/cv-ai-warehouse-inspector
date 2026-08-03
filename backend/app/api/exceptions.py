"""Global exception handlers.

Every error leaving the API is converted into the single
:class:`~app.api.schemas.ErrorResponse` envelope, so clients need only
one parsing path regardless of what failed.

Handlers also decide what *not* to expose. A database outage or an
unhandled bug is logged in full server-side but returned to the client
as a generic message — internal exception text routinely contains
connection strings, table names and stack context that should not cross
the network.
"""

from typing import Any, Dict, List

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas import ErrorResponse
from app.database.database import DatabaseError
from app.logger import logger


def _render(
    status_code: int,
    error: str,
    detail: str,
    request: Request,
    errors: List[Dict[str, Any]] | None = None,
) -> JSONResponse:
    """Build a JSON response in the standard error envelope.

    Args:
        status_code: HTTP status code to return.
        error: Short machine-readable error code.
        detail: Human-readable explanation, safe for clients.
        request: The failing request, used to report its path.
        errors: Field-level validation failures, when applicable.

    Returns:
        The rendered error response.
    """
    payload = ErrorResponse(
        error=error,
        detail=detail,
        status_code=status_code,
        path=request.url.path,
        errors=errors,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Render deliberate HTTP errors in the standard envelope.

    Args:
        request: The failing request.
        exc: The raised HTTP exception.

    Returns:
        The error response.
    """
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."

    if exc.status_code >= 500:
        logger.error(f"{request.method} {request.url.path} -> {exc.status_code}: {detail}")
    else:
        logger.info(f"{request.method} {request.url.path} -> {exc.status_code}: {detail}")

    return _render(
        status_code=exc.status_code,
        error=f"http_{exc.status_code}",
        detail=detail,
        request=request,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render request-validation failures with per-field detail.

    Args:
        request: The failing request.
        exc: The validation error raised by FastAPI.

    Returns:
        A ``422`` response listing every invalid field.
    """
    errors: List[Dict[str, Any]] = []

    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(part) for part in error.get("loc", ())),
                "message": error.get("msg", "Invalid value."),
                "type": error.get("type", "value_error"),
            }
        )

    logger.info(
        f"{request.method} {request.url.path} -> 422: "
        f"{len(errors)} validation error(s)."
    )

    return _render(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error="validation_error",
        detail="Request validation failed.",
        request=request,
        errors=errors,
    )


async def database_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Render database failures as a service-unavailable response.

    A database outage is a temporary infrastructure condition, not a
    client mistake, so it maps to ``503`` — which also tells clients the
    request is worth retrying. The underlying error is logged but never
    returned, since it can contain connection details.

    Args:
        request: The failing request.
        exc: The database error.

    Returns:
        A ``503`` response.
    """
    logger.error(f"{request.method} {request.url.path} -> database error: {exc}")

    return _render(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        error="database_unavailable",
        detail="The database is currently unavailable. Please retry shortly.",
        request=request,
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Render any unanticipated error as a generic ``500``.

    The full traceback is logged server-side; the client receives no
    internal detail.

    Args:
        request: The failing request.
        exc: The unhandled exception.

    Returns:
        A ``500`` response.
    """
    logger.exception(f"{request.method} {request.url.path} -> unhandled error: {exc}")

    return _render(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="internal_error",
        detail="An unexpected internal error occurred.",
        request=request,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every global handler to an application.

    Args:
        app: The FastAPI application to configure.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(DatabaseError, database_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.debug("Global exception handlers registered.")
