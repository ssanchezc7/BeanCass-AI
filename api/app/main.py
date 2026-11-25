"""API de inferencia de BeanCass AI (FastAPI)."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from . import calidad, imagen, multipart_memoria
from .config import Settings, get_settings
from .errors import APIError, registrar_manejadores, respuesta_error
from .modelos import CULTIVOS, TAMANO, Registro, cargar_registro, configurar_tensorflow, preprocesar
from .schemas import ListaModelos, RespuestaPrediccion, Salud

log = logging.getLogger("beancass.api")

CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
CSP_API = "default-src 'none'; frame-ancestors 'none'"


def _clave_cliente(settings: Settings):
    def clave(request: Request) -> str:
        if settings.trust_forwarded_for:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                return xff.split(",")[0].strip()[:64]
        return request.client.host if request.client else "desconocido"

    return clave


def create_app(settings: Settings | None = None, registro: Registro | None = None) -> FastAPI:
    settings = settings or get_settings()
    limiter = Limiter(key_func=_clave_cliente(settings), storage_uri="memory://")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.tf_version = configurar_tensorflow(settings)
        if app.state.registro is None:
            app.state.registro = await run_in_threadpool(cargar_registro, settings)
        yield

    app = FastAPI(
        title="BeanCass AI — API de inferencia",
        description="Clasificación orientativa de enfermedades foliares de fréjol y yuca.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.registro = registro
    app.state.limiter = limiter
    app.state.tf_version = None
    registrar_manejadores(app)

    @app.exception_handler(RateLimitExceeded)
    async def _limite(_: Request, __: RateLimitExceeded):
        return respuesta_error(
            429, "limite_solicitudes", "Demasiadas solicitudes. Espera un minuto e inténtalo de nuevo.",
            headers={"Retry-After": "60"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def _seguridad_y_registro(request: Request, call_next):
        inicio = time.perf_counter()
        respuesta = await call_next(request)
        for k, v in CABECERAS_SEGURIDAD.items():
            respuesta.headers.setdefault(k, v)
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            respuesta.headers.setdefault("Content-Security-Policy", CSP_API)
            respuesta.headers.setdefault("Cache-Control", "no-store")
        # Solo método, ruta, estado y duración: nunca IP, nombre de archivo ni contenido.
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, respuesta.status_code,
                 (time.perf_counter() - inicio) * 1000)
        return respuesta

    def _registro() -> Registro:
        reg = app.state.registro
        if reg is None:
            raise APIError(503, "modelo_no_disponible", "Los modelos aún se están cargando. Intenta en unos segundos.")
        return reg

    @app.get("/health", response_model=Salud)
    async def salud():
        reg = app.state.registro
        cargados = {c: bool(reg and reg.disponible(c)) for c in CULTIVOS}
        cuerpo = Salud(status="ok" if all(cargados.values()) else "degraded", models_loaded=cargados,
                       tf_version=app.state.tf_version or "desconocida")
        if not all(cargados.values()):
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=503, content=cuerpo.model_dump())
        return cuerpo

    @app.get("/api/v1/models", response_model=ListaModelos)
    async def modelos():
        reg = _registro()
        if reg.manifest is None:
            raise APIError(503, "modelo_no_disponible", "El manifest de modelos no está disponible.")
        lista = []
        for cultivo in CULTIVOS:
            info = reg.manifest["models"][cultivo]
            umbrales = reg.modelos[cultivo].umbrales if reg.disponible(cultivo) else info["thresholds"]
            lista.append({
                "crop": cultivo, "name": info["name"], "version": info["version"], "epoch": info["epoch"],
                "dataset": info["dataset"], "parameters": info["parameters"],
                "classes": [{k: c[k] for k in ("id", "code", "label_es", "description")} for c in info["classes"]],
                "preprocessing": info["preprocessing"]["description"],
                "metrics_test": info["metrics_test"],
                "thresholds": {**{k: umbrales[k] for k in ("t_min", "t_warn", "t_margin")},
                               "calibrated": info["thresholds"]["calibrated"]},
                "loaded": reg.disponible(cultivo),
            })
        return {"generated": reg.manifest["generated"], "selection_note": reg.manifest["selection_note"],
                "models": lista}

    @app.post(
        "/api/v1/predict",
        response_model=RespuestaPrediccion,
        responses={c: {"model": dict} for c in (400, 413, 415, 422, 429, 500, 503)},
    )
    @limiter.limit(settings.rate_limit)
    async def predecir(request: Request):
        cuerpo = await multipart_memoria.leer_cuerpo(request, settings.max_upload_bytes)
        campos = multipart_memoria.parsear(cuerpo, request.headers.get("content-type"), settings.max_upload_bytes)
        del cuerpo

        crops = [p for p in campos.get("crop", []) if p.archivo is None]
        if not crops:
            raise APIError(400, "cultivo_requerido", "Falta el campo 'crop' (bean o cassava).")
        if len(crops) > 1:
            raise APIError(400, "cultivo_invalido", "Envía un solo valor de 'crop'.")
        cultivo = bytes(crops[0].datos).decode("utf-8", "replace").strip().lower()
        if cultivo not in CULTIVOS:
            raise APIError(400, "cultivo_invalido", "Cultivo no válido. Usa 'bean' (fréjol) o 'cassava' (yuca).")

        archivos = [p for p in campos.get("file", []) if p.archivo is not None]
        if not archivos:
            raise APIError(400, "archivo_requerido", "Falta el archivo de imagen en el campo 'file'.")
        if len(archivos) > 1 or sum(1 for ps in campos.values() for p in ps if p.archivo is not None) > 1:
            raise APIError(400, "multiples_archivos", "Envía una sola imagen por solicitud.")
        datos = bytes(archivos[0].datos)
        if not datos:
            raise APIError(400, "archivo_vacio", "El archivo está vacío.")

        reg = _registro()
        if not reg.disponible(cultivo):
            raise APIError(503, "modelo_no_disponible", "El modelo de este cultivo no está disponible en este momento.")
        modelo = reg.modelos[cultivo]

        rgb, (ancho, alto) = await run_in_threadpool(imagen.decodificar, datos, settings)
        del datos

        def inferir():
            t0 = time.perf_counter()
            probs = modelo.predecir(preprocesar(rgb))
            return probs, (time.perf_counter() - t0) * 1000

        try:
            probs, ms = await asyncio.wait_for(run_in_threadpool(inferir), timeout=settings.inference_timeout_s)
        except asyncio.TimeoutError as exc:
            raise APIError(503, "tiempo_agotado", "El análisis tardó demasiado. Intenta de nuevo.") from exc

        if not np.all(np.isfinite(probs)):
            raise APIError(500, "error_interno", "El modelo devolvió un resultado inválido.")
        clases = modelo.clases
        idx = int(np.argmax(probs))
        top = clases[idx]
        orden = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
        q = calidad.evaluar(probs, rgb, modelo.umbrales, cultivo, top["code"])

        return {
            "crop": cultivo,
            "model": {"name": modelo.info["name"], "version": modelo.info["version"]},
            "prediction": {
                "class_id": idx, "label": top["code"], "label_es": top["label_es"],
                "confidence": float(probs[idx]), "is_healthy": top["code"] == modelo.info["healthy_class"],
            },
            "probabilities": [
                {"class_id": i, "label": clases[i]["code"], "label_es": clases[i]["label_es"],
                 "probability": float(probs[i])}
                for i in orden
            ],
            "quality": q,
            "image": {"width": ancho, "height": alto, "resized_to": (TAMANO, TAMANO)},
            "inference_ms": int(round(ms)),
        }

    return app


def _configurar_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


_configurar_logging()
app = create_app()
