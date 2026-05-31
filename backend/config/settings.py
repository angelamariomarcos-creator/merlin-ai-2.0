# backend/config/settings.py

import json
import logging
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT       = Path("C:/merlin-ai-2.0")
ESTADO_JSON_PATH   = PROJECT_ROOT / "backend" / "core" / "estado.json"
REQUIRED_ESTADO_KEYS = {"session", "memory", "billing", "queue"}


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ── Servidor ──────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development"
    )

    # ── API Keys obligatorias ─────────────────────────────
    ANTHROPIC_API_KEY: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")

    # ── API Keys opcionales ───────────────────────────────
    REPLICATE_API_KEY:  str = Field(default="")
    STABILITY_API_KEY:  str = Field(default="")
    FAL_KEY:            str = Field(default="")
    PERPLEXITY_API_KEY: str = Field(default="")

    # ── GitHub ────────────────────────────────────────────
    GITHUB_TOKEN:        str = Field(default="")
    GITHUB_REPO_OWNER:   str = Field(default="")
    GITHUB_REPO_NAME:    str = Field(default="")
    GITHUB_BRANCH:       str = Field(default="main")
    GITHUB_ESTADO_PATH:  str = Field(default="backend/core/estado.json")

    # ── Base de datos ─────────────────────────────────────
    DATABASE_URL: str = Field(default="sqlite:///./merlin.db")

    # ── Seguridad ─────────────────────────────────────────
    SECRET_KEY: str = Field(default="")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    @model_validator(mode="after")
    def validate_required_api_keys(self) -> "Settings":
        missing: list[str] = []
        if not self.ANTHROPIC_API_KEY or self.ANTHROPIC_API_KEY.strip() == "":
            missing.append("ANTHROPIC_API_KEY")
        if not self.GEMINI_API_KEY or self.GEMINI_API_KEY.strip() == "":
            missing.append("GEMINI_API_KEY")
        if missing:
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║         MERLÍN AI 2.0 — ERROR DE CONFIGURACIÓN       ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"║  Variables de entorno OBLIGATORIAS no encontradas:    ║\n"
                f"║                                                        ║\n"
                f"{''.join([f'║   ✗  {k:<47}║\n' for k in missing])}"
                f"║                                                        ║\n"
                f"║  Solución: Añade las claves en tu archivo .env         ║\n"
                f"╚══════════════════════════════════════════════════════╝\n"
            )
        return self

    @model_validator(mode="after")
    def validate_optional_keys_warnings(self) -> "Settings":
        _log = logging.getLogger("settings")
        if not self.FAL_KEY or self.FAL_KEY.strip() == "":
            _log.warning("[Settings] FAL_KEY no definida. image_generator/animation/upscaler inactivos.")
        if not self.PERPLEXITY_API_KEY or self.PERPLEXITY_API_KEY.strip() == "":
            _log.warning("[Settings] PERPLEXITY_API_KEY no definida. backlinking_agent usará fallback.")
        return self

    @model_validator(mode="after")
    def validate_secret_key_in_production(self) -> "Settings":
        if self.ENVIRONMENT == "production" and (
            not self.SECRET_KEY or self.SECRET_KEY.strip() == ""
        ):
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║         MERLÍN AI 2.0 — ERROR DE PRODUCCIÓN           ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"║  SECRET_KEY es obligatoria en ENVIRONMENT=production   ║\n"
                f"╚══════════════════════════════════════════════════════╝\n"
            )
        return self

    @model_validator(mode="after")
    def validate_estado_json(self) -> "Settings":
        if not ESTADO_JSON_PATH.exists():
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║       MERLÍN AI 2.0 — ESTADO CENTRAL NO ENCONTRADO   ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"║   ✗  {str(ESTADO_JSON_PATH):<47}║\n"
                f"╚══════════════════════════════════════════════════════╝\n"
            )
        try:
            with open(ESTADO_JSON_PATH, "r", encoding="utf-8") as f:
                estado = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║       MERLÍN AI 2.0 — ESTADO CENTRAL CORRUPTO        ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"║   ✗  Error: {str(e):<40}║\n"
                f"╚══════════════════════════════════════════════════════╝\n"
            )
        if not isinstance(estado, dict):
            raise ValueError("[Settings] estado.json debe ser un objeto JSON en la raíz.")
        missing_keys = REQUIRED_ESTADO_KEYS - set(estado.keys())
        if missing_keys:
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║       MERLÍN AI 2.0 — ESTADO CENTRAL INCOMPLETO      ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"{''.join([f'║   ✗  {k:<47}║\n' for k in sorted(missing_keys)])}"
                f"╚══════════════════════════════════════════════════════╝\n"
            )
        session = estado.get("session", {})
        required_session_fields = {"id", "estado", "fase_actual"}
        missing_session = required_session_fields - set(session.keys())
        if missing_session:
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║       MERLÍN AI 2.0 — SESSION INCOMPLETA             ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"{''.join([f'║   ✗  {k:<47}║\n' for k in sorted(missing_session)])}"
                f"╚══════════════════════════════════════════════════════╝\n"
            )
        return self


try:
    settings = Settings()
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)