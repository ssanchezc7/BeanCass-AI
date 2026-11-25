"""Errores de la API con formato único: {"error": {"code": ..., "message": ...}}."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("beancass.api")


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers


def respuesta_error(status: int, code: str, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}}, headers=headers)


_MENSAJES_HTTP = {
    404: ("no_encontrado", "Recurso no encontrado."),
    405: ("metodo_no_permitido", "Método HTTP no permitido para este recurso."),
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(_: Request, exc: APIError):
        return respuesta_error(exc.status, exc.code, exc.message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        campos = sorted({str(e.get("loc", ["?"])[-1]) for e in exc.errors()})
        return respuesta_error(422, "parametros_invalidos", f"Parámetros inválidos: {', '.join(campos)}.")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code, msg = _MENSAJES_HTTP.get(exc.status_code, ("error_http", "Solicitud no válida."))
        return respuesta_error(exc.status_code, code, msg)

    @app.exception_handler(Exception)
    async def _generico(request: Request, exc: Exception):
        # Se registra el tipo de excepción, nunca el contenido de la imagen ni datos del usuario.
        log.exception("Error no controlado en %s %s (%s)", request.method, request.url.path, type(exc).__name__)
        return respuesta_error(500, "error_interno", "Ocurrió un error interno. Intenta de nuevo más tarde.")
