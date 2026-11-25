"""Configuración de la API (variables de entorno / archivo .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DIR_API = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", DIR_API / ".env"), extra="ignore")

    # Modelos
    models_dir: Path = Field(DIR_API / "models", alias="MODELS_DIR")
    verify_sha256: bool = Field(True, alias="VERIFY_SHA256")

    # Límites de carga
    max_upload_mb: float = Field(8.0, alias="MAX_UPLOAD_MB", gt=0, le=50)
    max_image_pixels: int = Field(40_000_000, alias="MAX_IMAGE_PIXELS", gt=0)
    min_image_side: int = Field(64, alias="MIN_IMAGE_SIDE", ge=1)
    max_aspect_ratio: float = Field(5.0, alias="MAX_ASPECT_RATIO", ge=1)

    # Seguridad / red
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"], alias="ALLOWED_ORIGINS")
    rate_limit: str = Field("20/minute", alias="RATE_LIMIT")
    trust_forwarded_for: bool = Field(False, alias="TRUST_FORWARDED_FOR")
    inference_timeout_s: float = Field(30.0, alias="INFERENCE_TIMEOUT_S", gt=0)

    # TensorFlow
    tf_intra_op_threads: int = Field(0, alias="TF_INTRA_OP_THREADS", ge=0)
    tf_inter_op_threads: int = Field(0, alias="TF_INTER_OP_THREADS", ge=0)

    # Umbrales (vacío = usar los calibrados del manifest)
    bean_t_min: float | None = Field(None, alias="BEAN_T_MIN")
    bean_t_warn: float | None = Field(None, alias="BEAN_T_WARN")
    bean_t_margin: float | None = Field(None, alias="BEAN_T_MARGIN")
    cassava_t_min: float | None = Field(None, alias="CASSAVA_T_MIN")
    cassava_t_warn: float | None = Field(None, alias="CASSAVA_T_WARN")
    cassava_t_margin: float | None = Field(None, alias="CASSAVA_T_MARGIN")
    t_entropy: float = Field(0.85, alias="T_ENTROPY", gt=0, le=1)
    min_leaf_ratio: float = Field(0.12, alias="MIN_LEAF_RATIO", ge=0, le=1)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _origenes(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json

                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator(
        "bean_t_min", "bean_t_warn", "bean_t_margin", "cassava_t_min", "cassava_t_warn", "cassava_t_margin",
        mode="before",
    )
    @classmethod
    def _vacio_a_none(cls, v):
        return None if v in ("", None) else v

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    def umbral_override(self, cultivo: str) -> dict[str, float]:
        valores = {
            "t_min": getattr(self, f"{cultivo}_t_min"),
            "t_warn": getattr(self, f"{cultivo}_t_warn"),
            "t_margin": getattr(self, f"{cultivo}_t_margin"),
        }
        return {k: v for k, v in valores.items() if v is not None}


@lru_cache
def get_settings() -> Settings:
    return Settings()
