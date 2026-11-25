"""Validaciones del servidor: tipos, tamaños, imágenes corruptas, parámetros, errores y límites."""

from __future__ import annotations

import asyncio
import struct
import zlib

import pytest
from conftest import EJEMPLO_BEAN, ajustes, enviar, png
from fastapi.testclient import TestClient

from app.errors import APIError
from app.main import create_app
from app.modelos import Registro
from app import multipart_memoria


def _error(r, status, code=None):
    assert r.status_code == status, r.text
    cuerpo = r.json()
    assert set(cuerpo) == {"error"} and set(cuerpo["error"]) == {"code", "message"}
    if code:
        assert cuerpo["error"]["code"] == code
    return cuerpo["error"]


def _png_con_dimensiones(ancho: int, alto: int) -> bytes:
    """PNG pequeño cuya cabecera IHDR declara dimensiones enormes (bomba de descompresión)."""
    datos = bytearray(png(8, 8))
    ihdr = struct.pack(">II", ancho, alto) + bytes(datos[24:29])
    datos[16:29] = ihdr
    datos[29:33] = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF)
    return bytes(datos)


# --- Parámetros ---------------------------------------------------------------

def test_crop_ausente(cliente):
    _error(enviar(cliente, None, png()), 400, "cultivo_requerido")


@pytest.mark.parametrize("crop", ["maiz", "", "BEAN; DROP", "../bean"])
def test_crop_invalido(cliente, crop):
    _error(enviar(cliente, crop, png()), 400)


def test_falta_archivo(cliente):
    # multipart con solo el campo crop (sin parte de archivo)
    r = cliente.post("/api/v1/predict", files={"crop": (None, "bean")})
    _error(r, 400, "archivo_requerido")


def test_formulario_urlencoded_rechazado(cliente):
    _error(enviar(cliente, "bean", None), 400, "solicitud_invalida")


def test_varios_archivos(cliente):
    r = cliente.post("/api/v1/predict", data={"crop": "bean"},
                     files=[("file", ("a.png", png(), "image/png")), ("file", ("b.png", png(), "image/png"))])
    _error(r, 400, "multiples_archivos")


def test_cuerpo_no_multipart(cliente):
    _error(cliente.post("/api/v1/predict", json={"crop": "bean"}), 400, "solicitud_invalida")


def test_crop_en_mayusculas_se_normaliza(cliente):
    assert enviar(cliente, "Bean", png()).status_code == 200


# --- Tipo de archivo (magic bytes) ------------------------------------------

def test_archivo_vacio(cliente):
    _error(enviar(cliente, "bean", b""), 400, "archivo_vacio")


def test_texto_con_extension_jpg(cliente):
    _error(enviar(cliente, "bean", b"esto es texto plano, no una foto", nombre="hoja.jpg", tipo="image/jpeg"), 415)


def test_content_type_del_cliente_no_se_confia(cliente):
    # PNG real enviado con tipo y extensión de texto: se acepta por magic bytes.
    assert enviar(cliente, "bean", png(), nombre="hoja.txt", tipo="text/plain").status_code == 200


@pytest.mark.parametrize("contenido,formato", [
    (b"GIF89a" + b"\x00" * 64, "GIF"),
    (b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>', "SVG"),
    (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "SVG"),
    (b"%PDF-1.7\n" + b"0" * 64, "PDF"),
    (b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 32, "WebP"),
    (b"\x00\x00\x00\x18ftypheic" + b"\x00" * 32, "HEIC"),
])
def test_formatos_no_soportados(cliente, contenido, formato):
    err = _error(enviar(cliente, "bean", contenido, nombre="x.jpg", tipo="image/jpeg"), 415, "tipo_no_soportado")
    assert formato.split("/")[0][:3].upper() in err["message"].upper() or "JPEG" in err["message"]


def test_png_animado(cliente):
    import io

    from PIL import Image

    buf = io.BytesIO()
    cuadros = [Image.new("RGB", (100, 100), c) for c in ((0, 200, 0), (200, 0, 0))]
    cuadros[0].save(buf, "PNG", save_all=True, append_images=cuadros[1:])
    _error(enviar(cliente, "bean", buf.getvalue()), 415, "tipo_no_soportado")


# --- Imágenes corruptas / dimensiones ----------------------------------------

def test_png_corrupto(cliente):
    datos = EJEMPLO_BEAN.read_bytes()
    _error(enviar(cliente, "bean", datos[: len(datos) // 2]), 400, "imagen_corrupta")


def test_jpeg_solo_cabecera(cliente):
    _error(enviar(cliente, "bean", b"\xff\xd8\xff\xe0" + b"\x00" * 100, nombre="x.jpg", tipo="image/jpeg"), 400,
           "imagen_corrupta")


def test_imagen_1x1(cliente):
    err = _error(enviar(cliente, "bean", png(1, 1)), 422, "imagen_muy_pequena")
    assert "1×1" in err["message"]


def test_proporcion_extrema(cliente):
    _error(enviar(cliente, "bean", png(1000, 100)), 422, "proporcion_invalida")


def test_bomba_de_descompresion(cliente):
    _error(enviar(cliente, "bean", _png_con_dimensiones(50_000, 50_000)), 413, "imagen_demasiado_grande")


# --- Tamaño ---------------------------------------------------------------------

def test_archivo_demasiado_grande(cliente):
    grande = b"\xff\xd8\xff\xe0" + b"\x00" * (9 * 1024 * 1024)
    _error(enviar(cliente, "bean", grande, nombre="g.jpg", tipo="image/jpeg"), 413, "archivo_demasiado_grande")


def test_archivo_justo_sobre_el_limite(registro):
    s = ajustes(MAX_UPLOAD_MB="0.5")
    with TestClient(create_app(s, registro)) as c:
        datos = b"\xff\xd8\xff\xe0" + b"\x00" * (s.max_upload_bytes - 3)  # 1 byte de más, cabe en la sobrecarga
        _error(enviar(c, "bean", datos, nombre="g.jpg", tipo="image/jpeg"), 413, "archivo_demasiado_grande")


class _RequestFalso:
    def __init__(self, headers: dict, trozos: list[bytes]):
        self.headers = headers
        self._trozos = trozos

    async def stream(self):
        for t in self._trozos:
            yield t


def test_content_length_declarado_excesivo():
    req = _RequestFalso({"content-length": str(50 * 1024 * 1024)}, [b"x"])
    with pytest.raises(APIError) as e:
        asyncio.run(multipart_memoria.leer_cuerpo(req, 8 * 1024 * 1024))
    assert e.value.status == 413


def test_streaming_sin_content_length_tiene_tope_duro():
    leidos = []

    class Req(_RequestFalso):
        async def stream(self):
            for _ in range(1000):
                leidos.append(1)
                yield b"\x00" * (64 * 1024)

    with pytest.raises(APIError) as e:
        asyncio.run(multipart_memoria.leer_cuerpo(Req({}, []), 1 * 1024 * 1024))
    assert e.value.status == 413
    assert len(leidos) < 30  # corta en cuanto supera el tope, no lee todo


# --- Errores del servidor ------------------------------------------------------

def test_error_500_sin_trazas(registro, monkeypatch):
    modelo = registro.modelos["bean"]

    def falla(_x):
        raise RuntimeError(r"C:\ruta\secreta\modelo.keras Traceback interno")

    monkeypatch.setattr(modelo, "predecir", falla)
    with TestClient(create_app(ajustes(), registro), raise_server_exceptions=False) as c:
        r = enviar(c, "bean", png())
    err = _error(r, 500, "error_interno")
    assert "secreta" not in r.text and "Traceback" not in r.text and "RuntimeError" not in r.text
    assert err["message"]


def test_modelo_no_disponible_503(registro):
    parcial = Registro(manifest=registro.manifest, modelos={"bean": registro.modelos["bean"]},
                       errores={"cassava": "fallo simulado"})
    with TestClient(create_app(ajustes(), parcial)) as c:
        _error(enviar(c, "cassava", png()), 503, "modelo_no_disponible")
        assert enviar(c, "bean", png()).status_code == 200
        r = c.get("/health")
        assert r.status_code == 503 and r.json()["models_loaded"] == {"bean": True, "cassava": False}


def test_rate_limit(registro):
    with TestClient(create_app(ajustes(RATE_LIMIT="3/minute"), registro)) as c:
        codigos = [enviar(c, "bean", png()).status_code for _ in range(4)]
        assert codigos[:3] == [200, 200, 200]
        r = enviar(c, "bean", png())
        _error(r, 429, "limite_solicitudes")
        assert r.headers.get("retry-after") == "60"


def test_rate_limit_por_x_forwarded_for(registro):
    with TestClient(create_app(ajustes(RATE_LIMIT="2/minute", TRUST_FORWARDED_FOR="true"), registro)) as c:
        for _ in range(2):
            assert enviar(c, "bean", png(), headers={"X-Forwarded-For": "10.0.0.1"}).status_code == 200
        assert enviar(c, "bean", png(), headers={"X-Forwarded-For": "10.0.0.1"}).status_code == 429
        assert enviar(c, "bean", png(), headers={"X-Forwarded-For": "10.0.0.2"}).status_code == 200


def test_cabeceras_de_seguridad_y_cors(cliente):
    r = cliente.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    r = cliente.get("/health", headers={"Origin": "https://malicioso.example"})
    assert "access-control-allow-origin" not in r.headers


def test_ruta_inexistente_formato_unico(cliente):
    _error(cliente.get("/no-existe"), 404, "no_encontrado")
    _error(cliente.get("/api/v1/predict"), 405, "metodo_no_permitido")


def test_nombre_de_archivo_no_se_refleja(cliente):
    r = enviar(cliente, "bean", png(), nombre="../../etc/<script>alert(1)</script>.png")
    assert r.status_code == 200
    assert "script" not in r.text and "etc" not in r.text


def test_no_se_escribe_a_disco(cliente, monkeypatch, tmp_path):
    import tempfile

    llamadas = []
    original = tempfile.SpooledTemporaryFile

    def espia(*a, **k):
        llamadas.append(1)
        return original(*a, **k)

    monkeypatch.setattr(tempfile, "SpooledTemporaryFile", espia)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", lambda *a, **k: pytest.fail("escritura a disco"))
    grande = EJEMPLO_BEAN.read_bytes()  # > 1 MB: Starlette lo volcaría a disco
    assert len(grande) > 1024 * 1024
    assert enviar(cliente, "bean", grande).status_code == 200
    assert llamadas == []
