"""Calibra la heurística «posible no-hoja» (proporción de píxeles de vegetación).

Compara la distribución de `proporcion_hoja` en imágenes reales de los datasets con la de
fotos genéricas que no son hojas, para elegir MIN_LEAF_RATIO.

Uso (desde api/, con el venv activo):
    python scripts/calibrar_hoja.py --beans ~/beancass_datos/beans_test/test --otros ~/beancass_datos/no_hojas
    (Cassava se lee de TFDS si está descargado.)

Resultado usado en la app (2026-11-25): tono >= 40°, saturación >= 0,15, umbral 0,12
  Beans Test (128):          mínimo 0,20 · percentil 1: 0,30
  Cassava Validation (400):  mínimo 0,14 · percentil 1: 0,24
  Fotos genéricas (24, picsum.photos id 0–24): 19 por debajo de 0,12; las 5 restantes son paisajes con vegetación.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.calidad import proporcion_hoja  # noqa: E402


def cargar_carpeta(ruta: Path) -> list[np.ndarray]:
    archivos = sorted([*ruta.rglob("*.jpg"), *ruta.rglob("*.png")])
    return [np.asarray(Image.open(p).convert("RGB")) for p in archivos]


def resumen(nombre: str, valores: np.ndarray, umbral: float) -> None:
    if len(valores) == 0:
        print(f"{nombre}: sin imágenes")
        return
    print(f"{nombre} (n={len(valores)}): mín {valores.min():.2f} · p1 {np.percentile(valores, 1):.2f} · "
          f"p5 {np.percentile(valores, 5):.2f} · mediana {np.median(valores):.2f} · "
          f"por debajo de {umbral}: {(valores < umbral).sum()}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--beans", type=Path)
    ap.add_argument("--otros", type=Path)
    ap.add_argument("--cassava-n", type=int, default=400)
    ap.add_argument("--umbral", type=float, default=0.12)
    a = ap.parse_args()

    if a.beans:
        resumen("Beans", np.array([proporcion_hoja(x) for x in cargar_carpeta(a.beans.expanduser())]), a.umbral)
    try:
        import tensorflow_datasets as tfds

        ds = tfds.load("cassava", split="validation", download=False).take(a.cassava_n)
        resumen("Cassava", np.array([proporcion_hoja(r["image"].numpy()) for r in ds]), a.umbral)
    except Exception as exc:  # dataset no disponible
        print(f"Cassava: no disponible ({type(exc).__name__})")
    if a.otros:
        resumen("No-hojas", np.array([proporcion_hoja(x) for x in cargar_carpeta(a.otros.expanduser())]), a.umbral)


if __name__ == "__main__":
    main()
