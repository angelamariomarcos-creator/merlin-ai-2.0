# backend/agents/upscaler/upscaler.py

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config.settings import settings

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("upscaler")

# ── Constantes FAL.AI AuraSR ──────────────────────────────
FAL_SUBMIT_URL        = "https://queue.fal.run/fal-ai/aura-sr"
FAL_STATUS_BASE       = "https://queue.fal.run/fal-ai/aura-sr/requests"
FAL_POLL_INTERVAL_S   = 2.5
FAL_MAX_POLL_ATTEMPTS = 72   # ~3 min timeout


# ── Contrato de entrada ───────────────────────────────────
class UpscalerInputContract(BaseModel):
    model_config = {"strict": True}

    session_id: str = Field(min_length=1)
    image_url: str = Field(min_length=10)
    scale_factor: Literal[2, 4] = Field(
        default=4,
        description="Factor de escala: 2x (Full HD→4K) o 4x (HD→4K)."
    )
    overlapping_tiles: bool = Field(
        default=True,
        description="Activa solapamiento de tiles para eliminar artefactos en bordes."
    )
    checkpoint: Literal["v1", "v2"] = Field(
        default="v2",
        description="Versión del modelo AuraSR. v2 produce texturas más nítidas."
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
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(
                f"image_url debe ser una URL http/https pública válida. "
                f"Recibido: '{v}'"
            )
        return v

    @model_validator(mode="after")
    def log_scale_intent(self) -> "UpscalerInputContract":
        logger.info(
            f"[UpscalerInputContract] scale_factor={self.scale_factor}x | "
            f"checkpoint={self.checkpoint} | "
            f"overlapping_tiles={self.overlapping_tiles}"
        )
        return self


# ── Contrato de salida ────────────────────────────────────
class UpscalerOutputContract(BaseModel):
    generation_id: str
    session_id: str
    source_image_url: str
    enhanced_image_url: str
    scale_factor: int
    width: int
    height: int
    content_type: str
    timing_seconds: float
    timestamp: str
    fal_request_id: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Agente de reescalado ──────────────────────────────────
class UpscalerAgent:
    """
    Agente asíncrono de súper-resolución 4K usando FAL.AI AuraSR.
    Flujo: submit → poll status → fetch result.
    Acepta únicamente image_url pública (salida de ImageGenerator o CDN externo).
    """

    def __init__(self) -> None:
        self._fal_key: str = settings.FAL_KEY
        if not self._fal_key or self._fal_key.strip() == "":
            logger.warning(
                "[UpscalerAgent] FAL_KEY no definida. "
                "Las llamadas a upscale() fallarán hasta configurarla en .env"
            )
        self._headers = {
            "Authorization": f"Key {self._fal_key}",
            "Content-Type": "application/json",
        }

    # ── API pública ───────────────────────────────────────

    async def upscale(self, raw_payload: dict[str, Any]) -> UpscalerOutputContract:
        """
        Punto de entrada principal asíncrono.
        Acepta dict crudo, valida con UpscalerInputContract
        y devuelve UpscalerOutputContract con metadatos 4K.
        """
        contract = UpscalerInputContract.model_validate(raw_payload)
        self._assert_fal_key()

        t_start = time.perf_counter()

        async with httpx.AsyncClient(timeout=30.0) as client:
            request_id = await self._submit(client, contract)
            result_raw = await self._poll(client, request_id)

        t_end = time.perf_counter()
        timing = round(t_end - t_start, 3)

        return self._build_output(contract, result_raw, request_id, timing)

    def upscale_sync(self, raw_payload: dict[str, Any]) -> UpscalerOutputContract:
        """Wrapper síncrono para entornos sin event loop activo."""
        return asyncio.run(self.upscale(raw_payload))

    # ── Submit ────────────────────────────────────────────

    async def _submit(
        self,
        client: httpx.AsyncClient,
        contract: UpscalerInputContract,
    ) -> str:
        payload: dict[str, Any] = {
            "image_url": contract.image_url,
            "overlapping_tiles": contract.overlapping_tiles,
            "checkpoint": contract.checkpoint,
        }

        response = await client.post(
            FAL_SUBMIT_URL,
            headers=self._headers,
            json=payload,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"[UpscalerAgent] FAL submit falló "
                f"{response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        request_id: str = data.get("request_id", "")
        if not request_id:
            raise RuntimeError(
                f"[UpscalerAgent] FAL no devolvió request_id. "
                f"Respuesta: {data}"
            )

        logger.info(f"[UpscalerAgent] Job enviado. request_id={request_id}")
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
                    f"[UpscalerAgent] Error consultando status "
                    f"{status_response.status_code}: {status_response.text[:200]}"
                )

            status_data = status_response.json()
            status: str = status_data.get("status", "")

            logger.info(
                f"[UpscalerAgent] Intento {attempt}/{FAL_MAX_POLL_ATTEMPTS} "
                f"— status={status}"
            )

            if status == "COMPLETED":
                result_response = await client.get(
                    result_url,
                    headers=self._headers
                )
                if result_response.status_code != 200:
                    raise RuntimeError(
                        f"[UpscalerAgent] Error obteniendo resultado "
                        f"{result_response.status_code}: {result_response.text[:200]}"
                    )
                return result_response.json()

            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(
                    f"[UpscalerAgent] Job terminó con estado '{status}'. "
                    f"Detalle: {status_data}"
                )

        raise TimeoutError(
            f"[UpscalerAgent] Timeout tras {FAL_MAX_POLL_ATTEMPTS} intentos "
            f"({FAL_MAX_POLL_ATTEMPTS * FAL_POLL_INTERVAL_S}s) "
            f"para request_id={request_id}"
        )

    # ── Build output ──────────────────────────────────────

    def _build_output(
        self,
        contract: UpscalerInputContract,
        result: dict[str, Any],
        request_id: str,
        timing: float,
    ) -> UpscalerOutputContract:
        image: dict[str, Any] = result.get("image", {})
        if not image or not image.get("url"):
            raise RuntimeError(
                f"[UpscalerAgent] FAL devolvió resultado sin imagen. "
                f"Payload completo: {result}"
            )

        return UpscalerOutputContract(
            generation_id=str(uuid.uuid4()),
            session_id=contract.session_id,
            source_image_url=contract.image_url,
            enhanced_image_url=image.get("url", ""),
            scale_factor=contract.scale_factor,
            width=image.get("width", 0),
            height=image.get("height", 0),
            content_type=image.get("content_type", "image/png"),
            timing_seconds=timing,
            timestamp=datetime.now(timezone.utc).isoformat(),
            fal_request_id=request_id,
        )

    # ── Guard ─────────────────────────────────────────────

    def _assert_fal_key(self) -> None:
        if not self._fal_key or self._fal_key.strip() == "":
            raise EnvironmentError(
                "[UpscalerAgent] FAL_KEY no está definida en .env. "
                "Añade FAL_KEY=<tu_clave> para activar el reescalado 4K."
            )


# ── Singleton exportable ──────────────────────────────────
upscaler_agent = UpscalerAgent()