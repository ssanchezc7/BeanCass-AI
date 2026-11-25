"""Calibra los umbrales de confianza de la API usando SOLO las predicciones de Validation.

Fuente: los CSV `predicciones_<Modelo>.csv` que el estudio generó en
`<cultivo>/resultados/comparacion_modelos/validation_*/`. No se usa Test.

Criterios (iguales para ambos cultivos, sobre una rejilla de valores):
- T_min:    mayor umbral t tal que la exactitud de las predicciones con top1 < t
            es <= 50 % (por debajo de t el modelo acierta como mucho la mitad de las veces).
- T_margin: mayor margen m tal que la exactitud con (top1 - top2) < m es <= 50 %.
- T_warn:   mayor umbral t tal que la exactitud de las predicciones con
            T_min <= top1 < t es <= 80 %.
Si no hay suficientes muestras (< MIN_MUESTRAS) se conserva el valor inicial y se
marca como no calibrado.

Uso:  python api/scripts/calibrar_umbrales.py  (desde la raíz del repo)
Escribe api/models/umbrales_calibrados.json
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FUENTES = {
    "bean": RAIZ / "beans/resultados/comparacion_modelos/validation_20261122_184949_012897/predicciones_MobileNetV2.csv",
    "cassava": RAIZ / "cassava/resultados/comparacion_modelos/validation_20261122_094623_066739/predicciones_EfficientNetB0.csv",
}
INICIALES = {"t_min": 0.50, "t_warn": 0.70, "t_margin": 0.10}
MIN_MUESTRAS = 3
REJILLA_T = [round(0.30 + 0.05 * i, 2) for i in range(14)]  # 0.30 .. 0.95
REJILLA_M = [round(0.05 * i, 2) for i in range(1, 11)]  # 0.05 .. 0.50


def leer(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        columnas = [c for c in lector.fieldnames or [] if c.startswith("prob_")]
        filas = []
        for fila in lector:
            probs = [float(fila[c]) for c in columnas]
            orden = sorted(probs, reverse=True)
            top1 = orden[0]
            clase = columnas[probs.index(top1)].removeprefix("prob_")
            filas.append({
                "top1": top1,
                "margen": orden[0] - orden[1],
                "entropia": -sum(p * math.log(p) for p in probs if p > 0) / math.log(len(probs)),
                "acierto": fila["real"] == fila["predicha"],
                "coherente": clase == fila["predicha"],
            })
    return filas, [c.removeprefix("prob_") for c in columnas]


def exactitud(filas: list[dict]) -> float | None:
    return sum(f["acierto"] for f in filas) / len(filas) if filas else None


def mayor_umbral(filas, clave, rejilla, tope, desde=None):
    elegido = None
    for t in rejilla:
        sub = [f for f in filas if f[clave] < t and (desde is None or f["top1"] >= desde)]
        if len(sub) >= MIN_MUESTRAS and exactitud(sub) <= tope:
            elegido = t
    return elegido


def calibrar(cultivo: str, ruta: Path) -> dict:
    filas, clases = leer(ruta)
    assert all(f["coherente"] for f in filas), "La columna 'predicha' no coincide con el argmax de prob_*"
    t_min = mayor_umbral(filas, "top1", REJILLA_T, 0.50)
    t_margin = mayor_umbral(filas, "margen", REJILLA_M, 0.50)
    base_min = t_min if t_min is not None else INICIALES["t_min"]
    t_warn = mayor_umbral(filas, "top1", [t for t in REJILLA_T if t > base_min], 0.80, desde=base_min)
    res = {
        "t_min": t_min if t_min is not None else INICIALES["t_min"],
        "t_warn": t_warn if t_warn is not None else max(INICIALES["t_warn"], base_min + 0.05),
        "t_margin": t_margin if t_margin is not None else INICIALES["t_margin"],
    }
    calibrado = {k: v is not None for k, v in {"t_min": t_min, "t_warn": t_warn, "t_margin": t_margin}.items()}
    conclusivas = [f for f in filas if f["top1"] >= res["t_min"] and f["margen"] >= res["t_margin"]]
    seguras = [f for f in conclusivas if f["top1"] >= res["t_warn"]]
    inconcl = [f for f in filas if f not in conclusivas]
    return {
        "fuente": str(ruta.relative_to(RAIZ)).replace("\\", "/"),
        "particion": "validation",
        "clases_csv": clases,
        "n": len(filas),
        "exactitud_global": round(exactitud(filas), 4),
        "umbrales": res,
        "calibrado": calibrado,
        "resumen": {
            "inconcluyentes": {"n": len(inconcl), "exactitud": _r(exactitud(inconcl))},
            "concluyentes": {"n": len(conclusivas), "exactitud": _r(exactitud(conclusivas))},
            "confianza_alta": {"n": len(seguras), "exactitud": _r(exactitud(seguras))},
        },
    }


def _r(x):
    return None if x is None else round(x, 4)


def main() -> None:
    salida = {
        "criterio": "Ver docstring de api/scripts/calibrar_umbrales.py. Solo Validation; Test no se consulta.",
        "cultivos": {c: calibrar(c, r) for c, r in FUENTES.items()},
    }
    destino = RAIZ / "api/models/umbrales_calibrados.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
