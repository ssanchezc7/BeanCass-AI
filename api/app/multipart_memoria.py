"""Lectura del cuerpo multipart con tope duro y SIN escribir a disco.

El parser por defecto de Starlette vuelca a un archivo temporal las partes de más de 1 MB;
aquí se lee el flujo con un límite de bytes y se parsea completamente en memoria.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from python_multipart.multipart import MultipartParser, parse_options_header
from starlette.requests import ClientDisconnect, Request

from .errors import APIError

MAX_PARTES = 4
MAX_CAMPO_TEXTO = 256
SOBRECARGA_MULTIPART = 64 * 1024  # cabeceras y delimitadores además del archivo


@dataclass
class Parte:
    nombre: str
    archivo: str | None
    content_type: str | None
    datos: bytearray = field(default_factory=bytearray)


def _limite_superado(max_bytes: int) -> APIError:
    mb = max_bytes / (1024 * 1024)
    return APIError(413, "archivo_demasiado_grande", f"El archivo supera el tamaño máximo de {mb:g} MB.")


async def leer_cuerpo(request: Request, max_archivo: int) -> bytes:
    tope = max_archivo + SOBRECARGA_MULTIPART
    declarado = request.headers.get("content-length")
    if declarado is not None:
        try:
            if int(declarado) > tope:
                raise _limite_superado(max_archivo)
        except ValueError as exc:
            raise APIError(400, "solicitud_invalida", "Cabecera Content-Length inválida.") from exc
    trozos: list[bytes] = []
    total = 0
    try:
        async for trozo in request.stream():
            total += len(trozo)
            if total > tope:
                raise _limite_superado(max_archivo)
            trozos.append(trozo)
    except ClientDisconnect as exc:
        raise APIError(400, "solicitud_incompleta", "La conexión se cerró antes de recibir el archivo.") from exc
    return b"".join(trozos)


def parsear(cuerpo: bytes, content_type: str | None, max_archivo: int) -> dict[str, list[Parte]]:
    tipo, params = parse_options_header(content_type or "")
    if tipo != b"multipart/form-data" or b"boundary" not in params:
        raise APIError(400, "solicitud_invalida", "La solicitud debe enviarse como multipart/form-data.")

    partes: list[Parte] = []
    cab: dict[bytes, bytes] = {}
    estado = {"campo": b"", "valor": b""}

    def on_part_begin():
        cab.clear()

    def on_header_field(d, i, f):
        estado["campo"] += d[i:f]

    def on_header_value(d, i, f):
        estado["valor"] += d[i:f]

    def on_header_end():
        cab[estado["campo"].lower()] = estado["valor"]
        estado["campo"] = b""
        estado["valor"] = b""

    def on_headers_finished():
        if len(partes) >= MAX_PARTES:
            raise APIError(400, "demasiados_campos", "La solicitud contiene demasiados campos.")
        _, disp = parse_options_header(cab.get(b"content-disposition", b""))
        nombre = disp.get(b"name", b"").decode("utf-8", "replace")
        archivo = disp.get(b"filename")
        ctype = cab.get(b"content-type")
        partes.append(Parte(
            nombre=nombre,
            archivo=archivo.decode("utf-8", "replace") if archivo is not None else None,
            content_type=ctype.decode("latin-1") if ctype else None,
        ))

    def on_part_data(d, i, f):
        parte = partes[-1]
        parte.datos += d[i:f]
        limite = max_archivo if parte.archivo is not None else MAX_CAMPO_TEXTO
        if len(parte.datos) > limite:
            if parte.archivo is not None:
                raise _limite_superado(max_archivo)
            raise APIError(400, "campo_invalido", f"El campo '{parte.nombre[:32]}' es demasiado largo.")

    parser = MultipartParser(params[b"boundary"], {
        "on_part_begin": on_part_begin,
        "on_header_field": on_header_field,
        "on_header_value": on_header_value,
        "on_header_end": on_header_end,
        "on_headers_finished": on_headers_finished,
        "on_part_data": on_part_data,
    })
    try:
        parser.write(cuerpo)
        parser.finalize()
    except APIError:
        raise
    except Exception as exc:  # errores de formato del parser
        raise APIError(400, "solicitud_invalida", "El cuerpo multipart está mal formado.") from exc

    resultado: dict[str, list[Parte]] = {}
    for parte in partes:
        resultado.setdefault(parte.nombre, []).append(parte)
    return resultado
