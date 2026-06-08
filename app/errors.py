import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, NoResultFound

logger = structlog.get_logger()


async def _integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("integrity_error", path=str(request.url.path), detail=str(exc.orig))
    return JSONResponse(
        status_code=409,
        content={"detail": "Conflicto de datos: el recurso ya existe o viola una restricción.", "code": "CONFLICT"},
    )


async def _not_found_handler(request: Request, exc: NoResultFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": "Recurso no encontrado.", "code": "NOT_FOUND"},
    )


async def _generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", path=str(request.url.path), exc_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor.", "code": "INTERNAL_ERROR"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
    app.add_exception_handler(NoResultFound, _not_found_handler)
    app.add_exception_handler(Exception, _generic_error_handler)
