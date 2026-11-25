"""Señales heurísticas de calidad/confianza. Son advertencias, nunca una verdad absoluta."""

from __future__ import annotations

import math

import numpy as np

ADV_NO_CONCLUYENTE = (
    "El modelo no está seguro entre varias categorías. Repite la foto con buena luz, "
    "enfocando una sola hoja que ocupe la mayor parte del encuadre."
)
ADV_BAJA_CONFIANZA = "Confianza moderada: interpreta el resultado con precaución."
ADV_NO_HOJA = "La imagen no parece contener una hoja (muy poca superficie verde o amarillo-verde)."
ADV_CASSAVA_SANA = (
    "En la evaluación de Test, este modelo clasificó 40 hojas de yuca enfermas como sanas. "
    "Una predicción de «Hoja sana» no garantiza la ausencia de enfermedad."
)


def entropia_normalizada(probs: np.ndarray) -> float:
    p = probs[probs > 0]
    return float(-(p * np.log(p)).sum() / math.log(len(probs)))


def proporcion_hoja(rgb: np.ndarray) -> float:
    """Fracción aproximada de píxeles con tono de vegetación (amarillo → verde), saturación y brillo mínimos.

    Se calcula sobre una versión reducida (paso fijo) para que sea barata.
    """
    paso = max(1, int(max(rgb.shape[:2]) // 128))
    x = rgb[::paso, ::paso].astype(np.float32) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    maximo = x.max(axis=-1)
    minimo = x.min(axis=-1)
    delta = maximo - minimo
    sat = np.where(maximo > 0, delta / np.maximum(maximo, 1e-6), 0.0)
    d = np.maximum(delta, 1e-6)
    hue = np.where(
        maximo == r, ((g - b) / d) % 6.0,
        np.where(maximo == g, (b - r) / d + 2.0, (r - g) / d + 4.0),
    ) * 60.0
    vegetal = (hue >= 25) & (hue <= 170) & (sat >= 0.15) & (maximo >= 0.12) & (delta > 0.03)
    return float(vegetal.mean())


def evaluar(probs: np.ndarray, rgb: np.ndarray, umbrales: dict, cultivo: str, clase_top: str) -> dict:
    orden = np.sort(probs)[::-1]
    top1 = float(orden[0])
    margen = float(orden[0] - orden[1])
    entropia = entropia_normalizada(probs)
    hoja = proporcion_hoja(rgb)

    avisos: list[str] = []
    motivos: list[str] = []
    if top1 < umbrales["t_min"]:
        motivos.append("confianza_baja")
    if margen < umbrales["t_margin"]:
        motivos.append("margen_estrecho")
    if entropia > umbrales["t_entropy"]:
        motivos.append("entropia_alta")
    parece_no_hoja = hoja < umbrales["min_leaf_ratio"]

    if motivos:
        nivel = "inconclusive"
        avisos.append(ADV_NO_CONCLUYENTE)
    elif top1 < umbrales["t_warn"] or parece_no_hoja:
        nivel = "low_confidence"
        if top1 < umbrales["t_warn"]:
            avisos.append(ADV_BAJA_CONFIANZA)
    else:
        nivel = "ok"
    if parece_no_hoja:
        avisos.append(ADV_NO_HOJA)
    if cultivo == "cassava" and clase_top == "healthy":
        avisos.append(ADV_CASSAVA_SANA)

    return {
        "level": nivel,
        "warnings": avisos,
        "signals": {
            "top1": round(top1, 4),
            "margin": round(margen, 4),
            "entropy": round(entropia, 4),
            "leaf_ratio": round(hoja, 4),
            "reasons": motivos,
        },
    }
