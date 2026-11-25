"""Validación y decodificación de imágenes subidas (solo en memoria; nada se escribe en disco)."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .config import Settings
from .errors import APIError

# Firmas (magic bytes) de los formatos aceptados y de algunos rechazados con mensaje específico.
_JPEG = b"\xff\xd8\xff"
_PNG = b"\x89PNG\r\n\x1a\n"

_RECHAZADOS: list[tuple[str, callable]] = [
    ("GIF", lambda b: b[:6] in (b"GIF87a", b"GIF89a")),
    ("WebP", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
    ("HEIC/HEIF/AVIF", lambda b: b[4:8] == b"ftyp"),
    ("PDF", lambda b: b[:5] == b"%PDF-"),
    ("BMP", lambda b: b[:2] == b"BM"),
    ("TIFF", lambda b: b[:4] in (b"II*\x00", b"MM\x00*")),
    ("SVG/XML", lambda b: b.lstrip()[:5].lower() in (b"<?xml", b"<svg ", b"<svg>") or b"<svg" in b[:512].lower()),
]


def detectar_formato(datos: bytes) -> str:
    """Devuelve 'JPEG' o 'PNG' según los magic bytes; lanza 415 en cualquier otro caso."""
    if datos.startswith(_JPEG):
        return "JPEG"
    if datos.startswith(_PNG):
        return "PNG"
    for nombre, prueba in _RECHAZADOS:
        if prueba(datos[:1024]):
            raise APIError(415, "tipo_no_soportado", f"Formato {nombre} no soportado. Usa una imagen JPEG o PNG.")
    raise APIError(415, "tipo_no_soportado", "El archivo no es una imagen JPEG o PNG válida.")


def _a_rgb(img: Image.Image) -> Image.Image:
    """Convierte a RGB: compone la transparencia sobre blanco y expande escala de grises a 3 canales."""
    tiene_alfa = img.mode in ("RGBA", "LA", "RGBa", "La") or (img.mode == "P" and "transparency" in img.info)
    if tiene_alfa:
        rgba = img.convert("RGBA")
        fondo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(fondo, rgba).convert("RGB")
    if img.mode.startswith("I;16") or img.mode in ("I", "F"):
        # PNG de 16 bits en escala de grises: escalar a 8 bits antes de convertir.
        arr = np.asarray(img, dtype=np.float64)
        maximo = 65535.0 if img.mode.startswith("I;16") or arr.max() > 255 else 255.0
        arr8 = np.clip(arr / maximo * 255.0 + 0.5, 0, 255).astype(np.uint8)
        return Image.fromarray(arr8, mode="L").convert("RGB")
    return img.convert("RGB")


def decodificar(datos: bytes, settings: Settings) -> tuple[np.ndarray, tuple[int, int]]:
    """Valida y decodifica la imagen. Devuelve (array uint8 HxWx3 RGB, (ancho, alto))."""
    if not datos:
        raise APIError(400, "archivo_vacio", "El archivo está vacío.")
    formato = detectar_formato(datos)

    Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
    try:
        with Image.open(io.BytesIO(datos), formats=[formato]) as img:
            ancho, alto = img.size
            _comprobar_pixeles(ancho, alto, settings)
            if getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1:
                raise APIError(415, "tipo_no_soportado", "No se admiten imágenes animadas. Usa una foto JPEG o PNG.")
            img.verify()  # detecta estructuras corruptas sin decodificar todos los píxeles
        # verify() invalida el objeto: hay que reabrir para decodificar.
        with Image.open(io.BytesIO(datos), formats=[formato]) as img:
            img.load()  # falla si la imagen está truncada
            img = ImageOps.exif_transpose(img)
            rgb = _a_rgb(img)
    except APIError:
        raise
    except Image.DecompressionBombError as exc:
        raise APIError(413, "imagen_demasiado_grande", "La imagen tiene demasiados píxeles.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        raise APIError(400, "imagen_corrupta", "No se pudo leer la imagen: el archivo está dañado o incompleto.") from exc

    ancho, alto = rgb.size
    _comprobar_dimensiones(ancho, alto, settings)
    arr = np.asarray(rgb, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise APIError(400, "imagen_corrupta", "No se pudo convertir la imagen a RGB.")
    return arr, (ancho, alto)


def _comprobar_pixeles(ancho: int, alto: int, settings: Settings) -> None:
    if ancho * alto > settings.max_image_pixels:
        mp = settings.max_image_pixels / 1_000_000
        raise APIError(413, "imagen_demasiado_grande", f"La imagen supera el máximo de {mp:g} megapíxeles.")


def _comprobar_dimensiones(ancho: int, alto: int, settings: Settings) -> None:
    minimo = settings.min_image_side
    if min(ancho, alto) < minimo:
        raise APIError(
            422, "imagen_muy_pequena",
            f"La imagen mide {ancho}×{alto} px; el mínimo es {minimo}×{minimo} px. Usa una foto con más resolución.",
        )
    proporcion = max(ancho, alto) / min(ancho, alto)
    if proporcion > settings.max_aspect_ratio:
        raise APIError(
            422, "proporcion_invalida",
            f"La imagen es demasiado alargada ({proporcion:.1f}:1). Recorta la foto para centrar la hoja.",
        )
