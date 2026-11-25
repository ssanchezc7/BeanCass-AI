"""Copia los DOS checkpoints seleccionados por el estudio a api/models/ y genera manifest.json.

- Verifica el orden de clases contra los artefactos del repo (protocolo.json de Beans,
  columnas prob_* de los CSV de Validation y de Test, y seleccion_final_*.json).
- Calcula el SHA-256 de cada checkpoint.
- Incorpora los umbrales calibrados (api/models/umbrales_calibrados.json, generado por
  calibrar_umbrales.py, que solo usa Validation).
- Copia las métricas de Test del modelo seleccionado tal como las registró el estudio
  (solo para informar; no intervienen en ninguna selección).

Uso (desde la raíz del repo):  python api/scripts/preparar_modelos.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "api/models"

COMP_BEANS = RAIZ / "beans/resultados/comparacion_modelos/validation_20261122_184949_012897"
TEST_BEANS = RAIZ / "beans/resultados/comparacion_modelos/validation_20261122_083005_031981/test_modelo_seleccionado"
COMP_CASSAVA = RAIZ / "cassava/resultados/comparacion_modelos/validation_20261122_094623_066739"
SEL_CASSAVA = RAIZ / "cassava/resultados/comparacion_modelos/validation_20261122_182852_477368/seleccion_final_cassava.json"

CLASES = {
    "bean": [
        ("angular_leaf_spot", "Mancha angular", "Manchas foliares angulares causadas por un hongo."),
        ("bean_rust", "Roya", "Pústulas de color óxido causadas por un hongo."),
        ("healthy", "Hoja sana", "Sin síntomas visibles de las enfermedades evaluadas."),
    ],
    "cassava": [
        ("cbb", "CBB — tizón bacteriano", "Lesiones angulares acuosas y marchitez por bacteria."),
        ("cbsd", "CBSD — estría marrón", "Clorosis en venas y manchas amarillas causadas por virus."),
        ("cgm", "CGM — daño por ácaro verde", "Moteado clorótico y hojas pequeñas por ácaros."),
        ("cmd", "CMD — mosaico", "Mosaico amarillo-verde y deformación foliar por virus."),
        ("healthy", "Hoja sana", "Sin síntomas visibles de las enfermedades evaluadas."),
    ],
}


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def cols_prob(ruta: Path) -> list[str]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        return [c.removeprefix("prob_") for c in next(csv.reader(f)) if c.startswith("prob_")]


def leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def verificar_clases() -> None:
    bean = [c for c, _, _ in CLASES["bean"]]
    cassava = [c for c, _, _ in CLASES["cassava"]]
    fuentes = {
        "beans protocolo.json": (leer_json(COMP_BEANS / "protocolo.json")["clases"], bean),
        "beans predicciones_MobileNetV2.csv": (cols_prob(COMP_BEANS / "predicciones_MobileNetV2.csv"), bean),
        "beans metricas_test.json": (list(leer_json(TEST_BEANS / "metricas_test.json")["por_clase"]), bean),
        "cassava predicciones_EfficientNetB0.csv": (cols_prob(COMP_CASSAVA / "predicciones_EfficientNetB0.csv"), cassava),
        "cassava predicciones_test.csv": (cols_prob(COMP_CASSAVA / "test_modelo_seleccionado/predicciones_test.csv"), cassava),
    }
    for nombre, (encontrado, esperado) in fuentes.items():
        if encontrado != esperado:
            raise SystemExit(f"Orden de clases distinto en {nombre}: {encontrado} != {esperado}")
        print(f"  OK orden de clases: {nombre}")


def metricas_test_bean() -> dict:
    m = leer_json(TEST_BEANS / "metricas_test.json")
    aciertos = sum(m["matriz_confusion"][i][i] for i in range(3))
    return {
        "imagenes": m["imagenes"], "exactitud": m["exactitud"], "precision_macro": m["precision_macro"],
        "recall_macro": m["recall_macro"], "f1_macro": m["f1_macro"], "roc_auc_macro_ovr": m["roc_auc_macro_ovr"],
        "errores": m["imagenes"] - aciertos, "enfermas_como_sanas": m["enfermas_como_sanas"],
        "recall_por_clase": {k: v["recall"] for k, v in m["por_clase"].items()},
        "nota": "Los 4 errores ocurren entre enfermedades; ninguna hoja enferma se clasificó como sana.",
    }


def metricas_test_cassava() -> dict:
    m = leer_json(COMP_CASSAVA / "test_modelo_seleccionado/metricas_test.json")["test_completo"]
    clases = [c for c, _, _ in CLASES["cassava"]]
    return {
        "imagenes": m["imagenes"], "exactitud": m["exactitud"], "precision_macro": m["precision_macro"],
        "recall_macro": m["recall_macro"], "f1_macro": m["f1_macro"], "roc_auc_macro_ovr": m["roc_auc_macro_ovr"],
        "errores": m["imagenes"] - m["aciertos"], "enfermas_como_sanas": m["enfermas_como_sanas"],
        "recall_por_clase": dict(zip(clases, m["recall"])),
        "nota": "CBB y CBSD se confunden entre sí; 40 hojas enfermas se clasificaron como sanas.",
    }


def main() -> None:
    print("Verificando orden de clases contra el repo...")
    verificar_clases()
    sel_bean = leer_json(COMP_BEANS / "seleccion_final_beans.json")
    sel_cassava = leer_json(SEL_CASSAVA)
    umbrales = leer_json(DESTINO / "umbrales_calibrados.json")["cultivos"]

    entradas = {
        "bean": {
            "name": "MobileNetV2",
            "version": "ajuste_fino_20261121_181000_639966",
            "epoch": sel_bean["epoca_ajuste_fino"],
            "source": "beans/resultados/mobilenetv2/ajuste_fino_20261121_181000_639966/mejor_modelo.keras",
            "file": "bean_mobilenetv2.keras",
            "expected_layers": ["imagen", "normalizacion_mobilenetv2", "mobilenetv2_1.00_224", "dropout", "clasificacion_beans"],
            "parameters": 2261827,
            "dataset": "Beans — Makerere AI Lab (TFDS beans)",
            "preprocessing": {
                "method": "resize_with_pad", "antialias": True, "clip": [0, 255], "dtype": "float32",
                "description": ("RGB en rango 0–255 (float32). tf.image.resize_with_pad a 224×224 con antialias "
                                "(idéntico a tf.image.resize en fotos cuadradas como las de entrenamiento, 500×500) "
                                "y clip 0–255. La normalización (Rescaling 1/127.5, offset −1) está DENTRO del modelo."),
            },
            "metrics_validation": sel_bean["metricas_validation"],
            "metrics_test": metricas_test_bean(),
        },
        "cassava": {
            "name": "EfficientNetB0",
            "version": "ajuste_fino_20261116_203639",
            "epoch": sel_cassava["epoca_ajuste_fino"],
            "source": "cassava/resultados/efficientnetb0/ajuste_fino_20261116_203639/mejor_modelo.keras",
            "file": "cassava_efficientnetb0.keras",
            "expected_layers": ["imagen", "efficientnetb0", "dropout", "clasificacion_cassava"],
            "parameters": 4055976,
            "dataset": "iCassava 2019 (TFDS cassava)",
            "preprocessing": {
                "method": "resize_with_pad", "antialias": True, "clip": [0, 255], "dtype": "float32",
                "description": ("RGB en rango 0–255 (float32). tf.image.resize_with_pad a 224×224 con antialias y "
                                "clip 0–255, igual que en el entrenamiento. EfficientNetB0 normaliza internamente."),
            },
            "metrics_validation": sel_cassava["metricas_validation_completa"],
            "metrics_test": metricas_test_cassava(),
        },
    }

    manifest = {
        "manifest_version": 1,
        "generated": date.today().isoformat(),
        "image_size": 224,
        "input_shape": [None, 224, 224, 3],
        "input_dtype": "float32",
        "keras_version_training": "3.15.1",
        "tensorflow_version_training": "2.21.0",
        "selection_note": "Modelos seleccionados con Validation en el estudio; las métricas de Test son solo informativas.",
        "models": {},
    }
    DESTINO.mkdir(parents=True, exist_ok=True)
    for cultivo, e in entradas.items():
        origen = RAIZ / e.pop("source")
        destino = DESTINO / e["file"]
        if not destino.exists() or sha256(destino) != sha256(origen):
            shutil.copy2(origen, destino)
        digest = sha256(destino)
        assert digest == sha256(origen)
        u = umbrales[cultivo]
        manifest["models"][cultivo] = {
            **e,
            "source_path": str(origen.relative_to(RAIZ)).replace("\\", "/"),
            "sha256": digest,
            "input_shape": [None, 224, 224, 3],
            "classes": [
                {"id": i, "code": c, "label_es": es, "description": d}
                for i, (c, es, d) in enumerate(CLASES[cultivo])
            ],
            "healthy_class": "healthy",
            "thresholds": {**u["umbrales"], "calibrated": u["calibrado"], "source": u["fuente"],
                           "summary_validation": u["resumen"]},
        }
        print(f"  {cultivo}: {destino.name} sha256={digest[:16]}…")

    (DESTINO / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("manifest.json escrito.")


if __name__ == "__main__":
    main()
