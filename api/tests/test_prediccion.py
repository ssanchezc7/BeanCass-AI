"""Paridad con el modelo, contrato JSON, orden de clases y señales de calidad."""

from __future__ import annotations

import csv
import io
import json

import numpy as np
import pytest
from conftest import EJEMPLO_BEAN, EJEMPLO_CASSAVA, RAIZ, enviar, jpeg, png

from app.schemas import RespuestaPrediccion

MANIFEST = json.loads((RAIZ / "api/models/manifest.json").read_text(encoding="utf-8"))


def _prediccion_directa(ruta_modelo, ruta_imagen):
    """Ejecuta el checkpoint ORIGINAL del repo con el preprocesamiento del entrenamiento, sin pasar por la API."""
    import keras
    import tensorflow as tf
    from PIL import Image, ImageOps

    modelo = keras.saving.load_model(ruta_modelo, compile=False)
    rgb = np.asarray(ImageOps.exif_transpose(Image.open(ruta_imagen)).convert("RGB"), dtype=np.uint8)
    x = tf.image.resize_with_pad(tf.constant(rgb), 224, 224, antialias=True)
    x = tf.clip_by_value(tf.cast(x, tf.float32), 0.0, 255.0)[None]
    return np.asarray(modelo(x, training=False))[0]


@pytest.mark.parametrize("crop,imagen", [("bean", EJEMPLO_BEAN), ("cassava", EJEMPLO_CASSAVA)])
def test_paridad_con_modelo_directo(cliente, crop, imagen):
    r = enviar(cliente, crop, imagen.read_bytes())
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    api = np.zeros(len(cuerpo["probabilities"]))
    for p in cuerpo["probabilities"]:
        api[p["class_id"]] = p["probability"]
    directa = _prediccion_directa(RAIZ / MANIFEST["models"][crop]["source_path"], imagen)
    np.testing.assert_allclose(api, directa, atol=1e-5)
    assert abs(api.sum() - 1.0) < 1e-5
    assert cuerpo["prediction"]["class_id"] == int(np.argmax(directa))


def test_contrato_json(cliente):
    r = enviar(cliente, "bean", EJEMPLO_BEAN.read_bytes())
    cuerpo = RespuestaPrediccion.model_validate(r.json())
    probs = [p.probability for p in cuerpo.probabilities]
    assert probs == sorted(probs, reverse=True)
    assert cuerpo.probabilities[0].class_id == cuerpo.prediction.class_id
    assert cuerpo.prediction.confidence == pytest.approx(probs[0])
    assert cuerpo.image.resized_to == (224, 224)
    assert cuerpo.model.name == "MobileNetV2"
    assert cuerpo.disclaimer
    assert {p.class_id for p in cuerpo.probabilities} == {0, 1, 2}


def test_predicciones_cambian_con_la_imagen(cliente):
    a = enviar(cliente, "bean", EJEMPLO_BEAN.read_bytes()).json()["probabilities"]
    b = enviar(cliente, "bean", png(300, 300, (150, 90, 40))).json()["probabilities"]
    assert {p["label"]: p["probability"] for p in a} != {p["label"]: p["probability"] for p in b}


def _columnas_prob(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return [c.removeprefix("prob_") for c in next(csv.reader(f)) if c.startswith("prob_")]


def test_orden_de_clases_regresion(registro):
    esperado = {
        "bean": ["angular_leaf_spot", "bean_rust", "healthy"],
        "cassava": ["cbb", "cbsd", "cgm", "cmd", "healthy"],
    }
    csvs = {
        "bean": "beans/resultados/comparacion_modelos/validation_20261122_184949_012897/predicciones_MobileNetV2.csv",
        "cassava": "cassava/resultados/comparacion_modelos/validation_20261122_094623_066739/predicciones_EfficientNetB0.csv",
    }
    protocolo_beans = json.loads((RAIZ / "beans/resultados/comparacion_modelos/validation_20261122_184949_012897/protocolo.json").read_text(encoding="utf-8"))
    assert protocolo_beans["clases"] == esperado["bean"]
    for crop, clases in esperado.items():
        assert [c["code"] for c in MANIFEST["models"][crop]["classes"]] == clases
        assert [c["id"] for c in MANIFEST["models"][crop]["classes"]] == list(range(len(clases)))
        assert _columnas_prob(RAIZ / csvs[crop]) == clases
        assert registro.modelos[crop].modelo.output_shape[-1] == len(clases)


def test_sha256_y_metadatos(registro):
    from app.modelos import sha256_archivo

    for crop, info in MANIFEST["models"].items():
        assert sha256_archivo(RAIZ / "api/models" / info["file"]) == info["sha256"]
        assert sha256_archivo(RAIZ / info["source_path"]) == info["sha256"]
        assert tuple(registro.modelos[crop].modelo.input_shape) == (None, 224, 224, 3)


def test_resize_with_pad_equivale_a_resize_en_cuadradas():
    """Beans se entrenó con tf.image.resize en fotos 500×500; la API usa resize_with_pad."""
    import tensorflow as tf

    rgb = np.random.default_rng(0).integers(0, 256, (500, 500, 3), dtype=np.uint8)
    a = tf.image.resize(rgb, (224, 224), antialias=True)
    b = tf.image.resize_with_pad(rgb, 224, 224, antialias=True)
    np.testing.assert_allclose(a.numpy(), b.numpy(), atol=1e-4)


def test_no_doble_normalizacion(registro):
    """El preprocesamiento entrega 0–255; la normalización vive dentro del modelo."""
    from app.modelos import preprocesar

    x = preprocesar(np.full((300, 300, 3), 200, dtype=np.uint8)).numpy()
    assert x.dtype == np.float32 and x.shape == (1, 224, 224, 3)
    assert x.max() == pytest.approx(200.0)
    capa = registro.modelos["bean"].modelo.get_layer("normalizacion_mobilenetv2")
    assert capa.scale == pytest.approx(1 / 127.5) and capa.offset == pytest.approx(-1.0)


def test_rgba_y_grises_se_aceptan(cliente):
    assert enviar(cliente, "bean", png(200, 200, (40, 120, 40, 128), modo="RGBA")).status_code == 200
    r = enviar(cliente, "cassava", jpeg(200, 200, 120, modo="L"), nombre="g.jpg", tipo="image/jpeg")
    assert r.status_code == 200


def test_orientacion_exif(cliente):
    r = enviar(cliente, "bean", jpeg(400, 200, exif_orientacion=6), nombre="rot.jpg", tipo="image/jpeg")
    assert r.status_code == 200
    assert (r.json()["image"]["width"], r.json()["image"]["height"]) == (200, 400)


def test_cassava_sana_siempre_advierte():
    from app.calidad import ADV_CASSAVA_SANA, evaluar

    umbrales = {"t_min": 0.5, "t_warn": 0.7, "t_margin": 0.1, "t_entropy": 0.85, "min_leaf_ratio": 0.12}
    hoja = np.zeros((100, 100, 3), np.uint8)
    hoja[..., 1] = 160
    q = evaluar(np.array([0.01, 0.01, 0.01, 0.01, 0.96]), hoja, umbrales, "cassava", "healthy")
    assert q["level"] == "ok" and ADV_CASSAVA_SANA in q["warnings"]
    q = evaluar(np.array([0.01, 0.98, 0.01]), hoja, umbrales, "bean", "bean_rust")
    assert ADV_CASSAVA_SANA not in q["warnings"]


def test_niveles_de_calidad():
    from app.calidad import evaluar

    u = {"t_min": 0.5, "t_warn": 0.7, "t_margin": 0.1, "t_entropy": 0.85, "min_leaf_ratio": 0.12}
    hoja = np.zeros((64, 64, 3), np.uint8)
    hoja[..., 1] = 150
    assert evaluar(np.array([0.45, 0.30, 0.25]), hoja, u, "bean", "x")["level"] == "inconclusive"
    assert evaluar(np.array([0.52, 0.46, 0.02]), hoja, u, "bean", "x")["level"] == "inconclusive"
    assert evaluar(np.array([0.65, 0.30, 0.05]), hoja, u, "bean", "x")["level"] == "low_confidence"
    assert evaluar(np.array([0.95, 0.04, 0.01]), hoja, u, "bean", "x")["level"] == "ok"
    gris = np.full((64, 64, 3), 128, np.uint8)
    q = evaluar(np.array([0.95, 0.04, 0.01]), gris, u, "bean", "x")
    assert q["level"] == "inconclusive" and "posible_no_hoja" in q["signals"]["reasons"]
    assert any("no parece contener una hoja" in w for w in q["warnings"])


@pytest.mark.parametrize("ruta", ["web/public/placeholder.jpg", "web/public/placeholder-user.jpg", "web/public/placeholder-logo.png"])
def test_imagenes_que_no_son_hojas_nunca_salen_ok(cliente, ruta):
    datos = (RAIZ / ruta).read_bytes()
    tipo = "image/png" if ruta.endswith(".png") else "image/jpeg"
    for crop in ("bean", "cassava"):
        r = enviar(cliente, crop, datos, nombre=ruta.rsplit("/", 1)[-1], tipo=tipo)
        if r.status_code != 200:  # p. ej. imagen demasiado alargada
            assert r.status_code in (400, 422)
            continue
        assert r.json()["quality"]["level"] != "ok", r.json()["quality"]


def test_api_models(cliente):
    r = cliente.get("/api/v1/models")
    assert r.status_code == 200
    modelos = {m["crop"]: m for m in r.json()["models"]}
    assert modelos["bean"]["name"] == "MobileNetV2" and modelos["cassava"]["name"] == "EfficientNetB0"
    assert modelos["bean"]["metrics_test"]["exactitud"] == pytest.approx(0.96875)
    assert modelos["cassava"]["metrics_test"]["enfermas_como_sanas"] == 40
    assert "sha256" not in json.dumps(r.json())


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["models_loaded"] == {"bean": True, "cassava": True}
    assert r.json()["tf_version"].startswith("2.21")


def test_jpeg_real_de_buena_calidad(cliente):
    from PIL import Image

    buf = io.BytesIO()
    Image.open(EJEMPLO_BEAN).convert("RGB").save(buf, "JPEG", quality=92)
    r = enviar(cliente, "bean", buf.getvalue(), nombre="hoja.jpg", tipo="image/jpeg")
    assert r.status_code == 200
