# backend/agents/animation/animation.py

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config.settings import settings

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("animation")

# ── Constantes FAL.AI SeedAnce ────────────────────────────
FAL_SUBMIT_URL        = "https://queue.fal.run/fal-ai/seedance-1-lite"
FAL_STATUS_BASE       = "https://queue.fal.run/fal-ai/seedance-1-lite/requests"
FAL_POLL_INTERVAL_S   = 3.0
FAL_MAX_POLL_ATTEMPTS = 80   # ~4 min timeout


# ── Contrato de entrada ───────────────────────────────────
class AnimationInputContract(BaseModel):
    model_config = {"strict": True}

    session_id: str = Field(min_length=1)
    image_url: str = Field(min_length=10)
    motion_prompt: str = Field(default="", max_length=500)
    duration: Literal[4] = Field(
        default=4,
        description="Duración fija de 4 segundos según especificación SeedAnce."
    )
    resolution: Literal["480p", "720p"] = Field(default="720p")
    seed: int | None = Field(default=None)
    camera_fixed: bool = Field(
        default=False,
        description="Si True, intenta fijar la cámara y animar solo el sujeto."
    )

    @field_validator("session_id", mode="before")
    @classmethod
    def strip_session_id(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("session_id no puede ser una cadena vacía.")
        return v.strip()

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("image_url no puede ser una cadena vacía.")
        v = v.strip()
        is_remote = v.startswith("http://") or v.startswith("https://")
        is_local  = Path(v).exists()
        if not is_remote and not is_local:
            raise ValueError(
                f"image_url debe ser una URL http/https válida "
                f"o una ruta local existente. Recibido: '{v}'"
            )
        return v

    @field_validator("motion_prompt", mode="before")
    @classmethod
    def strip_motion_prompt(cls, v: str) -> str:
        if not isinstance(v, str):
            return ""
        return v.strip()

    @model_validator(mode="after")
    def warn_empty_motion_prompt(self) -> "AnimationInputContract":
        if not self.motion_prompt:
            logger.warning(
                "[AnimationInputContract] motion_prompt vacío. "
                "SeedAnce inferirá el movimiento automáticamente desde la imagen."
            )
        return self


# ── Contrato de salida ────────────────────────────────────
class AnimationOutputContract(BaseModel):
    generation_id: str
    session_id: str
    source_image_url: str
    motion_prompt: str
    video_url: str
    duration_seconds: int
    width: int
    height: int
    seed: int
    content_type: str
    timing_seconds: float
    timestamp: str
    fal_request_id: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Agente de animación ───────────────────────────────────
class AnimationAgent:
    """
    Agente asíncrono imagen→vídeo 4s usando FAL.AI SeedAnce.
    Flujo: submit → poll status → fetch result.
    Compatible con image_url remota o ruta local (auto-upload no implementado:
    se asume que image_url es siempre una URL pública, e.g. salida de ImageGenerator).
    """

    def __init__(self) -> None:
        self._fal_key: str = settings.FAL_KEY
        if not self._fal_key or self._fal_key.strip() == "":
            logger.warning(
                "[AnimationAgent] FAL_KEY no definida. "
                "Las llamadas a animate() fallarán hasta configurarla en .env"
            )
        self._headers = {
            "Authorization": f"Key {self._fal_key}",
            "Content-Type": "application/json",
        }

    # ── API pública ───────────────────────────────────────

    async def animate(self, raw_payload: dict[str, Any]) -> AnimationOutputContract:
        """
        Punto de entrada principal asíncrono.
        Acepta dict crudo, valida con AnimationInputContract
        y devuelve AnimationOutputContract con metadatos del vídeo.
        """
        contract = AnimationInputContract.model_validate(raw_payload)
        self._assert_fal_key()

        t_start = time.perf_counter()

        async with httpx.AsyncClient(timeout=30.0) as client:
            request_id = await self._submit(client, contract)
            result_raw = await self._poll(client, request_id)

        t_end = time.perf_counter()
        timing = round(t_end - t_start, 3)

        return self._build_output(contract, result_raw, request_id, timing)

    def animate_sync(self, raw_payload: dict[str, Any]) -> AnimationOutputContract:
        """Wrapper síncrono para entornos sin event loop activo."""
        return asyncio.run(self.animate(raw_payload))

    # ── Submit ────────────────────────────────────────────

    async def _submit(
        self,
        client: httpx.AsyncClient,
        contract: AnimationInputContract,
    ) -> str:
        payload: dict[str, Any] = {
            "image_url": contract.image_url,
            "duration": contract.duration,
            "resolution": contract.resolution,
            "camera_fixed": contract.camera_fixed,
        }
        if contract.motion_prompt:
            payload["prompt"] = contract.motion_prompt
        if contract.seed is not None:
            payload["seed"] = contract.seed

        response = await client.post(
            FAL_SUBMIT_URL,
            headers=self._headers,
            json=payload,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"[AnimationAgent] FAL submit falló "
                f"{response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        request_id: str = data.get("request_id", "")
        if not request_id:
            raise RuntimeError(
                f"[AnimationAgent] FAL no devolvió request_id. "
                f"Respuesta: {data}"
            )

        logger.info(f"[AnimationAgent] Job enviado. request_id={request_id}")
        return request_id

    # ── Poll ──────────────────────────────────────────────

    async def _poll(
        self,
        client: httpx.AsyncClient,
        request_id: str,
    ) -> dict[str, Any]:
        status_url = f"{FAL_STATUS_BASE}/{request_id}/status"
        result_url = f"{FAL_STATUS_BASE}/{request_id}"

        for attempt in range(1, FAL_MAX_POLL_ATTEMPTS + 1):
            await asyncio.sleep(FAL_POLL_INTERVAL_S)

            status_response = await client.get(
                status_url,
                headers=self._headers
            )

            if status_response.status_code != 200:
                raise RuntimeError(
                    f"[AnimationAgent] Error consultando status "
                    f"{status_response.status_code}: {status_response.text[:200]}"
                )

            status_data = status_response.json()
            status: str = status_data.get("status", "")

            logger.info(
                f"[AnimationAgent] Intento {attempt}/{FAL_MAX_POLL_ATTEMPTS} "
                f"— status={status}"
            )

            if status == "COMPLETED":
                result_response = await client.get(
                    result_url,
                    headers=self._headers
                )
                if result_response.status_code != 200:
                    raise RuntimeError(
                        f"[AnimationAgent] Error obteniendo resultado "
                        f"{result_response.status_code}: {result_response.text[:200]}"
                    )
                return result_response.json()

            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(
                    f"[AnimationAgent] Job terminó con estado '{status}'. "
                    f"Detalle: {status_data}"
                )

        raise TimeoutError(
            f"[AnimationAgent] Timeout tras {FAL_MAX_POLL_ATTEMPTS} intentos "
            f"({FAL_MAX_POLL_ATTEMPTS * FAL_POLL_INTERVAL_S}s) "
            f"para request_id={request_id}"
        )

    # ── Build output ──────────────────────────────────────

    def _build_output(
        self,
        contract: AnimationInputContract,
        result: dict[str, Any],
        request_id: str,
        timing: float,
    ) -> AnimationOutputContract:
        video: dict[str, Any] = result.get("video", {})
        if not video or not video.get("url"):
            raise RuntimeError(
                f"[AnimationAgent] FAL devolvió resultado sin vídeo. "
                f"Payload completo: {result}"
            )

        return AnimationOutputContract(
            generation_id=str(uuid.uuid4()),
            session_id=contract.session_id,
            source_image_url=contract.image_url,
            motion_prompt=contract.motion_prompt,
            video_url=video.get("url", ""),
            duration_seconds=contract.duration,
            width=video.get("width", 0),
            height=video.get("height", 0),
            seed=result.get("seed", 0),
            content_type=video.get("content_type", "video/mp4"),
            timing_seconds=timing,
            timestamp=datetime.now(timezone.utc).isoformat(),
            fal_request_id=request_id,
        )

    # ── Guard ─────────────────────────────────────────────

    def _assert_fal_key(self) -> None:
        if not self._fal_key or self._fal_key.strip() == "":
            raise EnvironmentError(
                "[AnimationAgent] FAL_KEY no está definida en .env. "
                "Añade FAL_KEY=<tu_clave> para activar la generación de vídeo."
            )


# ── Singleton exportable ──────────────────────────────────
animation_agent = AnimationAgent()