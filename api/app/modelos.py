"""Carga, verificación e inferencia de los modelos Keras seleccionados."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .config import Settings

log = logging.getLogger("beancass.modelos")

CULTIVOS = ("bean", "cassava")
TAMANO = 224


class ErrorModelo(RuntimeError):
    """El checkpoint no coincide con el manifest o no se pudo cargar."""


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_manifest(models_dir: Path) -> dict:
    ruta = models_dir / "manifest.json"
    if not ruta.is_file():
        raise ErrorModelo(f"No existe {ruta.name} en el directorio de modelos.")
    return json.loads(ruta.read_text(encoding="utf-8"))


def preprocesar(rgb: np.ndarray):
    """Replica el preprocesamiento del entrenamiento con TensorFlow (sin normalizar: va dentro del modelo).

    rgb: uint8 HxWx3 en 0–255. Devuelve tensor float32 (1, 224, 224, 3) en 0–255.
    tf.image.resize_with_pad + antialias: es lo que usó Cassava; para Beans (fotos 500×500)
    equivale exactamente a tf.image.resize en imágenes cuadradas y evita deformar las no cuadradas.
    """
    import tensorflow as tf

    x = tf.convert_to_tensor(rgb, dtype=tf.uint8)
    x = tf.image.resize_with_pad(x, TAMANO, TAMANO, antialias=True)
    x = tf.clip_by_value(tf.cast(x, tf.float32), 0.0, 255.0)
    return tf.expand_dims(x, 0)


@dataclass
class ModeloCargado:
    cultivo: str
    info: dict
    modelo: object
    umbrales: dict
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def clases(self) -> list[dict]:
        return self.info["classes"]

    def predecir(self, x) -> np.ndarray:
        """Inferencia síncrona (llamar desde un hilo de trabajo, no desde el event loop)."""
        with self._lock:
            salida = self.modelo(x, training=False)
        probs = np.asarray(salida, dtype=np.float64)[0]
        return probs


@dataclass
class Registro:
    manifest: dict | None = None
    modelos: dict[str, ModeloCargado] = field(default_factory=dict)
    errores: dict[str, str] = field(default_factory=dict)

    def disponible(self, cultivo: str) -> bool:
        return cultivo in self.modelos


def configurar_tensorflow(settings: Settings) -> str:
    import tensorflow as tf

    try:
        if settings.tf_intra_op_threads:
            tf.config.threading.set_intra_op_parallelism_threads(settings.tf_intra_op_threads)
        if settings.tf_inter_op_threads:
            tf.config.threading.set_inter_op_parallelism_threads(settings.tf_inter_op_threads)
    except RuntimeError:
        # TensorFlow ya inicializado (p. ej., en tests): se mantiene la configuración existente.
        pass
    return tf.__version__


def _cargar_uno(cultivo: str, info: dict, settings: Settings) -> ModeloCargado:
    import keras

    ruta = settings.models_dir / info["file"]
    if not ruta.is_file():
        raise ErrorModelo(f"No se encontró el archivo del modelo '{info['file']}'.")
    if settings.verify_sha256:
        digest = sha256_archivo(ruta)
        if digest != info["sha256"]:
            raise ErrorModelo(f"SHA-256 de '{info['file']}' no coincide con el manifest.")

    modelo = keras.saving.load_model(ruta, compile=False)

    forma = tuple(modelo.input_shape)
    esperada = tuple(info["input_shape"])
    if forma != esperada:
        raise ErrorModelo(f"Forma de entrada {forma} distinta de la esperada {esperada}.")
    dtype = str(getattr(modelo.inputs[0], "dtype", "float32"))
    if "float32" not in dtype:
        raise ErrorModelo(f"Tipo de entrada {dtype} distinto de float32.")
    n_clases = len(info["classes"])
    if modelo.output_shape[-1] != n_clases:
        raise ErrorModelo(f"El modelo devuelve {modelo.output_shape[-1]} salidas y el manifest define {n_clases} clases.")
    capas = [capa.name for capa in modelo.layers]
    if info.get("expected_layers") and capas != info["expected_layers"]:
        raise ErrorModelo(f"Capas {capas} distintas de las esperadas {info['expected_layers']}.")
    ids = [c["id"] for c in info["classes"]]
    if ids != list(range(n_clases)):
        raise ErrorModelo("Los ids de clase del manifest deben ser 0..N-1 en orden.")

    umbrales = {k: info["thresholds"][k] for k in ("t_min", "t_warn", "t_margin")}
    umbrales.update(settings.umbral_override(cultivo))
    umbrales["t_entropy"] = settings.t_entropy
    umbrales["min_leaf_ratio"] = settings.min_leaf_ratio

    cargado = ModeloCargado(cultivo=cultivo, info=info, modelo=modelo, umbrales=umbrales)
    # Warm-up: la primera llamada construye el grafo; así la primera petición real no es lenta.
    import tensorflow as tf

    probs = cargado.predecir(tf.zeros((1, TAMANO, TAMANO, 3), tf.float32))
    if not np.isclose(probs.sum(), 1.0, atol=1e-3):
        raise ErrorModelo("La salida del modelo no es una distribución softmax.")
    return cargado


def cargar_registro(settings: Settings) -> Registro:
    registro = Registro()
    try:
        registro.manifest = leer_manifest(settings.models_dir)
    except (ErrorModelo, json.JSONDecodeError) as exc:
        log.error("No se pudo leer el manifest: %s", exc)
        for c in CULTIVOS:
            registro.errores[c] = "manifest no disponible"
        return registro

    for cultivo in CULTIVOS:
        info = registro.manifest.get("models", {}).get(cultivo)
        if info is None:
            registro.errores[cultivo] = "no definido en el manifest"
            continue
        inicio = time.perf_counter()
        try:
            registro.modelos[cultivo] = _cargar_uno(cultivo, info, settings)
            log.info("Modelo %s (%s) cargado en %.1f s", cultivo, info["name"], time.perf_counter() - inicio)
        except Exception as exc:  # se registra y se sigue: /health informará 503
            registro.errores[cultivo] = str(exc)
            log.error("No se pudo cargar el modelo %s: %s", cultivo, exc)
    return registro
