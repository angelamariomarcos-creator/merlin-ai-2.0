# backend/agents/image_generator/image_generator.py

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
logger = logging.getLogger("image_generator")

# ── Constantes FAL.AI ─────────────────────────────────────
FAL_SUBMIT_URL = "https://queue.fal.run/fal-ai/flux/dev"
FAL_STATUS_BASE = "https://queue.fal.run/fal-ai/flux/dev/requests"
FAL_POLL_INTERVAL_SECONDS = 2.0
FAL_MAX_POLL_ATTEMPTS = 60  # 2 min timeout


# ── Contrato de entrada ───────────────────────────────────
class ImageInputContract(BaseModel):
    model_config = {"strict": True}

    session_id: str = Field(min_length=1)
    prompt: str = Field(min_length=3, max_length=2000)
    image_size: Literal[
        "square_hd",
        "square",
        "portrait_4_3",
        "portrait_16_9",
        "landscape_4_3",
        "landscape_16_9",
    ] = Field(default="landscape_16_9")
    num_inference_steps: int = Field(default=28, ge=1, le=50)
    guidance_scale: float = Field(default=3.5, ge=1.0, le=20.0)
    num_images: int = Field(default=1, ge=1, le=4)
    enable_safety_checker: bool = Field(default=True)
    seed: int | None = Field(default=None)

    @field_validator("session_id", "prompt", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("El campo no puede ser una cadena vacía.")
        return v.strip()

    @model_validator(mode="after")
    def validate_prompt_not_empty_after_strip(self) -> "ImageInputContract":
        if len(self.prompt) < 3:
            raise ValueError("El prompt debe tener al menos 3 caracteres.")
        return self


# ── Contrato de salida ────────────────────────────────────
class ImageOutputContract(BaseModel):
    generation_id: str
    session_id: str
    prompt: str
    url: str
    seed: int
    width: int
    height: int
    content_type: str
    timing_seconds: float
    timestamp: str
    fal_request_id: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Agente generador de imágenes ──────────────────────────
class ImageGenerator:
    """
    Agente asíncrono que conecta con FAL.AI FLUX Dev
    mediante el patrón submit → poll → result de la queue API.
    """

    def __init__(self) -> None:
        self._fal_key: str = settings.FAL_KEY
        if not self._fal_key or self._fal_key.strip() == "":
            logger.warning(
                "[ImageGenerator] FAL_KEY no definida. "
                "Las llamadas a generate() fallarán hasta configurarla."
            )
        self._headers = {
            "Authorization": f"Key {self._fal_key}",
            "Content-Type": "application/json",
        }

    # ── API pública ───────────────────────────────────────

    async def generate(self, raw_payload: dict[str, Any]) -> ImageOutputContract:
        """
        Punto de entrada principal.
        Acepta dict crudo, valida con ImageInputContract
        y devuelve ImageOutputContract con los metadatos completos.
        """
        contract = ImageInputContract.model_validate(raw_payload)
        self._assert_fal_key()

        t_start = time.perf_counter()

        async with httpx.AsyncClient(timeout=30.0) as client:
            request_id = await self._submit(client, contract)
            result_raw = await self._poll(client, request_id)

        t_end = time.perf_counter()
        timing = round(t_end - t_start, 3)

        return self._build_output(contract, result_raw, request_id, timing)

    def generate_sync(self, raw_payload: dict[str, Any]) -> ImageOutputContract:
        """Wrapper síncrono para entornos sin event loop activo."""
        return asyncio.run(self.generate(raw_payload))

    # ── Submit ────────────────────────────────────────────

    async def _submit(
        self,
        client: httpx.AsyncClient,
        contract: ImageInputContract,
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": contract.prompt,
            "image_size": contract.image_size,
            "num_inference_steps": contract.num_inference_steps,
            "guidance_scale": contract.guidance_scale,
            "num_images": contract.num_images,
            "enable_safety_checker": contract.enable_safety_checker,
        }
        if contract.seed is not None:
            payload["seed"] = contract.seed

        response = await client.post(
            FAL_SUBMIT_URL,
            headers=self._headers,
            json=payload,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"[ImageGenerator] FAL submit falló "
                f"{response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        request_id: str = data.get("request_id", "")
        if not request_id:
            raise RuntimeError(
                f"[ImageGenerator] FAL no devolvió request_id. "
                f"Respuesta: {data}"
            )

        logger.info(f"[ImageGenerator] Job enviado. request_id={request_id}")
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
            await asyncio.sleep(FAL_POLL_INTERVAL_SECONDS)

            status_response = await client.get(status_url, headers=self._headers)

            if status_response.status_code != 200:
                raise RuntimeError(
                    f"[ImageGenerator] Error consultando status "
                    f"{status_response.status_code}: {status_response.text[:200]}"
                )

            status_data = status_response.json()
            status = status_data.get("status", "")

            logger.info(
                f"[ImageGenerator] Intento {attempt}/{FAL_MAX_POLL_ATTEMPTS} "
                f"— status={status}"
            )

            if status == "COMPLETED":
                result_response = await client.get(result_url, headers=self._headers)
                if result_response.status_code != 200:
                    raise RuntimeError(
                        f"[ImageGenerator] Error obteniendo resultado "
                        f"{result_response.status_code}: {result_response.text[:200]}"
                    )
                return result_response.json()

            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(
                    f"[ImageGenerator] Job terminó con estado '{status}'. "
                    f"Detalle: {status_data}"
                )

        raise TimeoutError(
            f"[ImageGenerator] Timeout tras {FAL_MAX_POLL_ATTEMPTS} intentos "
            f"({FAL_MAX_POLL_ATTEMPTS * FAL_POLL_INTERVAL_SECONDS}s) "
            f"para request_id={request_id}"
        )

    # ── Build output ──────────────────────────────────────

    def _build_output(
        self,
        contract: ImageInputContract,
        result: dict[str, Any],
        request_id: str,
        timing: float,
    ) -> ImageOutputContract:
        images: list[dict[str, Any]] = result.get("images", [])
        if not images:
            raise RuntimeError(
                f"[ImageGenerator] FAL devolvió resultado sin imágenes. "
                f"Payload: {result}"
            )

        first = images[0]
        return ImageOutputContract(
            generation_id=str(uuid.uuid4()),
            session_id=contract.session_id,
            prompt=contract.prompt,
            url=first.get("url", ""),
            seed=result.get("seed", 0),
            width=first.get("width", 0),
            height=first.get("height", 0),
            content_type=first.get("content_type", "image/jpeg"),
            timing_seconds=timing,
            timestamp=datetime.now(timezone.utc).isoformat(),
            fal_request_id=request_id,
        )

    # ── Guard ─────────────────────────────────────────────

    def _assert_fal_key(self) -> None:
        if not self._fal_key or self._fal_key.strip() == "":
            raise EnvironmentError(
                "[ImageGenerator] FAL_KEY no está definida en .env. "
                "Añade FAL_KEY=<tu_clave> para activar la generación de imágenes."
            )


# ── Singleton exportable ──────────────────────────────────
image_generator = ImageGenerator()