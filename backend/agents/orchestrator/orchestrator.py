# backend/agents/orchestrator/orchestrator.py

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import anthropic
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config.settings import settings


# ── Contrato de entrada (autónomo) ────────────────────────
class ContextContract(BaseModel):
    model_config = {"strict": True}

    agent_target: Literal[
        "orchestrator",
        "image-generator",
        "animation",
        "memory-helper",
        "billing-monitor",
        "logger",
    ]
    max_tokens: int = Field(default=2048, gt=0, le=8192)


class UserInputContract(BaseModel):
    model_config = {"strict": True}

    session_id: str = Field(min_length=1)
    user_input: str = Field(min_length=1, max_length=10000)
    context: ContextContract

    @field_validator("session_id", "user_input", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("El campo no puede ser una cadena vacía.")
        return v.strip()


# ── Decisión de enrutamiento ──────────────────────────────
class RoutingDecision(BaseModel):
    event_id: str
    session_id: str
    agent_target: str
    reasoning: str
    priority: int
    raw_input: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Prompt del sistema ────────────────────────────────────
ROUTING_SYSTEM_PROMPT = """
Eres el orquestador central de Merlín AI 2.0.
Tu única función es analizar la petición del usuario y devolver un JSON con esta estructura exacta:
{
  "agent_target": "<nombre_del_agente>",
  "reasoning": "<explicación breve de por qué ese agente>",
  "priority": <entero_1_a_5>
}
Agentes disponibles: orchestrator, image-generator, animation, memory-helper, billing-monitor, logger.
Responde ÚNICAMENTE con el JSON. Sin texto adicional, sin markdown, sin backticks.
""".strip()


# ── Orquestador principal ─────────────────────────────────
class Orchestrator:

    SUPPORTED_AGENTS = {
        "orchestrator",
        "image-generator",
        "animation",
        "memory-helper",
        "billing-monitor",
        "logger",
    }

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = "claude-sonnet-4-20250514"

    def route(self, raw_payload: dict[str, Any]) -> RoutingDecision:
        """
        Punto de entrada principal.
        Acepta un dict crudo, lo valida con UserInputContract
        y devuelve una RoutingDecision.
        """
        contract = UserInputContract.model_validate(raw_payload)
        raw_response = self._call_claude(contract.user_input)
        parsed = self._parse_routing_response(raw_response)
        self._validate_agent_target(parsed.get("agent_target", ""))

        return RoutingDecision(
            event_id=str(uuid.uuid4()),
            session_id=contract.session_id,
            agent_target=parsed["agent_target"],
            reasoning=parsed.get("reasoning", ""),
            priority=int(parsed.get("priority", 3)),
            raw_input=contract.user_input,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _call_claude(self, user_input: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=ROUTING_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_input}
            ],
        )
        return message.content[0].text.strip()

    def _parse_routing_response(self, raw: str) -> dict[str, Any]:
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"[Orchestrator] Respuesta de Claude no es JSON válido.\n"
                f"Respuesta recibida: {raw}\n"
                f"Error: {e}"
            )

    def _validate_agent_target(self, agent_target: str) -> None:
        if agent_target not in self.SUPPORTED_AGENTS:
            raise ValueError(
                f"[Orchestrator] Agente desconocido: '{agent_target}'.\n"
                f"Agentes válidos: {sorted(self.SUPPORTED_AGENTS)}"
            )


# ── Singleton exportable ──────────────────────────────────
orchestrator = Orchestrator()