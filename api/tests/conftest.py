from __future__ import annotations

import io
import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
warnings.filterwarnings("ignore", category=DeprecationWarning)

DIR_API = Path(__file__).resolve().parents[1]
RAIZ = DIR_API.parent
sys.path.insert(0, str(DIR_API))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modelos import cargar_registro  # noqa: E402

EJEMPLO_BEAN = RAIZ / "web/public/bean-leaf.png"
EJEMPLO_CASSAVA = RAIZ / "web/public/cassava-leaf.png"


def ajustes(**extra) -> Settings:
    base = {"RATE_LIMIT": "1000/minute", "ALLOWED_ORIGINS": "http://localhost:3000"}
    base.update(extra)
    return Settings(_env_file=None, **base)


@pytest.fixture(scope="session")
def registro():
    return cargar_registro(ajustes())


@pytest.fixture()
def cliente(registro):
    with TestClient(create_app(ajustes(), registro), raise_server_exceptions=False) as c:
        yield c


def png(ancho=256, alto=256, color=(60, 140, 60), modo="RGB") -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new(modo, (ancho, alto), color).save(buf, "PNG")
    return buf.getvalue()


def jpeg(ancho=256, alto=256, color=(60, 140, 60), exif_orientacion: int | None = None, modo="RGB") -> bytes:
    from PIL import Image

    img = Image.new(modo, (ancho, alto), color)
    buf = io.BytesIO()
    if exif_orientacion:
        exif = Image.Exif()
        exif[0x0112] = exif_orientacion
        img.save(buf, "JPEG", exif=exif.tobytes())
    else:
        img.save(buf, "JPEG")
    return buf.getvalue()


def enviar(cliente, crop="bean", contenido: bytes | None = None, nombre="hoja.png", tipo="image/png", **kw):
    data = {"crop": crop} if crop is not None else {}
    files = {"file": (nombre, contenido, tipo)} if contenido is not None else None
    return cliente.post("/api/v1/predict", data=data, files=files, **kw)
