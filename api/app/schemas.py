"""Contrato JSON de la API (Pydantic)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Cultivo = Literal["bean", "cassava"]
NivelCalidad = Literal["ok", "low_confidence", "inconclusive"]

DESCARGO = "Resultado orientativo; no constituye diagnóstico."


class ErrorDetalle(BaseModel):
    code: str
    message: str


class ErrorRespuesta(BaseModel):
    error: ErrorDetalle


class ModeloRef(BaseModel):
    name: str
    version: str


class Prediccion(BaseModel):
    class_id: int
    label: str
    label_es: str
    confidence: float = Field(ge=0, le=1)
    is_healthy: bool


class Probabilidad(BaseModel):
    class_id: int
    label: str
    label_es: str
    probability: float = Field(ge=0, le=1)


class Senales(BaseModel):
    top1: float
    margin: float
    entropy: float
    leaf_ratio: float
    reasons: list[str]


class Calidad(BaseModel):
    level: NivelCalidad
    warnings: list[str]
    signals: Senales


class InfoImagen(BaseModel):
    width: int
    height: int
    resized_to: tuple[int, int]


class RespuestaPrediccion(BaseModel):
    crop: Cultivo
    model: ModeloRef
    prediction: Prediccion
    probabilities: list[Probabilidad]
    quality: Calidad
    image: InfoImagen
    inference_ms: int
    disclaimer: str = DESCARGO


class Salud(BaseModel):
    status: Literal["ok", "degraded"]
    models_loaded: dict[str, bool]
    tf_version: str


class ClasePublica(BaseModel):
    id: int
    code: str
    label_es: str
    description: str


class ModeloPublico(BaseModel):
    crop: Cultivo
    name: str
    version: str
    epoch: int
    dataset: str
    parameters: int
    classes: list[ClasePublica]
    preprocessing: str
    metrics_test: dict
    thresholds: dict
    loaded: bool


class ListaModelos(BaseModel):
    generated: str
    selection_note: str
    models: list[ModeloPublico]
