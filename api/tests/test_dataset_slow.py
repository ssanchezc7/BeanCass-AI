"""Pruebas opcionales con imágenes reales de los datasets (marcadas `slow`).

Detectan errores graves de integración (doble normalización, clases desordenadas,
preprocesamiento distinto): con cualquiera de ellos la exactitud se desploma y las
probabilidades dejan de coincidir con las que registró el estudio.

Datos:
- Fréjol: carpetas `test/` y `validation/` del dataset Beans (Makerere AI Lab) tal como se
  publican en Hugging Face (AI-Lab-Makerere/beans, data/test.zip y data/validation.zip).
  Rutas: BEANS_DIR (por defecto ~/beancass_datos) → beans_test/test y beans_val/validation.
  (El bucket de TFDS para beans devuelve 403 desde 2026.)
- Yuca: TFDS `cassava` ya descargado (tensorflow-datasets).

Ejecutar:  pytest -m slow -s
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

import numpy as np
import pytest
from conftest import RAIZ, enviar

pytestmark = pytest.mark.slow

BEANS_DIR = Path(os.environ.get("BEANS_DIR", Path.home() / "beancass_datos"))
CSV_VAL_BEANS = RAIZ / "beans/resultados/comparacion_modelos/validation_20261122_184949_012897/predicciones_MobileNetV2.csv"
CSV_VAL_CASSAVA = RAIZ / "cassava/resultados/comparacion_modelos/validation_20261122_094623_066739/predicciones_EfficientNetB0.csv"
CLASES = {"bean": ["angular_leaf_spot", "bean_rust", "healthy"], "cassava": ["cbb", "cbsd", "cgm", "cmd", "healthy"]}


def _leer_csv(ruta: Path) -> dict[str, dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        return {fila["imagen"]: fila for fila in csv.DictReader(f)}


def _tfds(nombre: str, split: str):
    tfds = pytest.importorskip("tensorflow_datasets")
    try:
        return tfds.load(nombre, split=split, with_info=True, download=False)
    except Exception as exc:  # dataset no descargado
        pytest.skip(f"Dataset {nombre} no disponible: {type(exc).__name__}")


def _png(arr: np.ndarray) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")  # sin pérdida: mismos píxeles que decodificó TFDS
    return buf.getvalue()


def _probs(r) -> dict[str, float]:
    assert r.status_code == 200, r.text
    return {p["label"]: p["probability"] for p in r.json()["probabilities"]}


def _beans(carpeta: str) -> Path:
    ruta = BEANS_DIR / carpeta
    if not ruta.is_dir():
        pytest.skip(f"No existe {ruta}; descarga Beans de Hugging Face (ver docstring).")
    return ruta


def test_exactitud_minima_test_beans(cliente):
    raiz = _beans("beans_test/test")
    imagenes = sorted(raiz.glob("*/*.jpg"))
    aciertos = sum(
        enviar(cliente, "bean", p.read_bytes(), nombre=p.name, tipo="image/jpeg").json()["prediction"]["label"] == p.parent.name
        for p in imagenes
    )
    exactitud = aciertos / len(imagenes)
    print(f"\nBeans Test: exactitud {exactitud:.4f} ({aciertos}/{len(imagenes)}) — estudio: 0.9688 (124/128)")
    assert len(imagenes) >= 50
    assert exactitud >= 0.90


def test_paridad_con_estudio_beans_validation(cliente):
    raiz = _beans("beans_val")
    estudio = _leer_csv(CSV_VAL_BEANS)
    difs, coinciden = [], 0
    for nombre, fila in estudio.items():
        p = raiz / nombre
        api = _probs(enviar(cliente, "bean", p.read_bytes(), nombre=p.name, tipo="image/jpeg"))
        difs.append(max(abs(api[c] - float(fila[f"prob_{c}"])) for c in CLASES["bean"]))
        coinciden += max(api, key=api.get) == fila["predicha"]
    print(f"\nBeans Validation: {coinciden}/{len(estudio)} predicciones iguales al estudio; "
          f"dif. máx. {max(difs):.2e}, mediana {np.median(difs):.2e}")
    assert coinciden / len(estudio) >= 0.98  # el decodificador JPEG puede variar en casos frontera
    assert np.median(difs) < 1e-2


def test_exactitud_minima_test_cassava(cliente):
    ds, info = _tfds("cassava", "test")
    clases = info.features["label"].names
    assert clases == CLASES["cassava"]
    total = aciertos = 0
    for registro in ds.take(150):
        api = _probs(enviar(cliente, "cassava", _png(registro["image"].numpy())))
        aciertos += max(api, key=api.get) == clases[int(registro["label"].numpy())]
        total += 1
    print(f"\nCassava Test ({total} imágenes): exactitud {aciertos / total:.3f} — estudio: 0.8228")
    assert aciertos / total >= 0.70


def test_paridad_con_estudio_cassava_validation(cliente):
    """Con los mismos píxeles que decodificó TFDS, la API reproduce las probabilidades del estudio."""
    ds, _ = _tfds("cassava", "validation")
    estudio = _leer_csv(CSV_VAL_CASSAVA)
    difs = []
    for registro in ds.take(80):
        nombre = registro["image/filename"].numpy().decode()
        if nombre not in estudio:
            continue
        api = _probs(enviar(cliente, "cassava", _png(registro["image"].numpy())))
        difs.append(max(abs(api[c] - float(estudio[nombre][f"prob_{c}"])) for c in CLASES["cassava"]))
        assert max(api, key=api.get) == estudio[nombre]["predicha"]
    print(f"\nCassava Validation: {len(difs)} imágenes, dif. máx. con el estudio {max(difs):.2e}")
    assert len(difs) >= 50
    assert max(difs) < 1e-3
