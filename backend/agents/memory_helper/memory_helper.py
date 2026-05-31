# backend/agents/memory_helper/memory_helper.py

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
from pydantic import BaseModel, Field, field_validator

from backend.config.settings import settings


# ── Rutas ─────────────────────────────────────────────────
PROJECT_ROOT = Path("C:/merlin-ai-2.0")
ESTADO_PATH = PROJECT_ROOT / "backend" / "core" / "estado.json"

# ── Umbral de compresión ──────────────────────────────────
MAX_INTERACTIONS_BEFORE_COMPRESSION = 10
COMPRESSION_SYSTEM_PROMPT = """
Eres un compresor de contexto para Merlín AI 2.0.
Recibirás una lista de interacciones pasadas entre el usuario y el sistema.
Tu tarea es generar un resumen compacto en español que preserve:
- Las intenciones clave del usuario
- Los agentes que actuaron y sus resultados
- Cualquier dato crítico (IDs, rutas, decisiones importantes)
Responde ÚNICAMENTE con el resumen en texto plano. Sin listas, sin markdown.
Máximo 300 palabras.
""".strip()


# ── Contratos internos ────────────────────────────────────
class InteractionEntry(BaseModel):
    interaction_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_target: str = Field(min_length=1)
    user_input: str = Field(min_length=1, max_length=10000)
    agent_response: str = Field(default="")
    timestamp: str = Field(min_length=1)

    @field_validator("interaction_id", "session_id", "user_input", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("El campo no puede ser una cadena vacía.")
        return v.strip()


class MemoryReadResult(BaseModel):
    interactions: list[dict[str, Any]] = Field(default_factory=list)
    compressed_context: str = Field(default="")
    total_interactions: int = Field(default=0)
    last_updated: str = Field(default="")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Agente de Memoria ─────────────────────────────────────
class MemoryHelper:

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = "claude-sonnet-4-20250514"
        self._ensure_estado_memory_structure()

    # ── API pública ───────────────────────────────────────

    def save_interaction(self, entry: dict[str, Any]) -> None:
        """Valida y persiste una nueva interacción en memory.interactions."""
        contract = InteractionEntry.model_validate(entry)
        estado = self._load_estado()
        memory = estado.setdefault("memory", {})
        interactions: list[dict[str, Any]] = memory.setdefault("interactions", [])

        interactions.append({
            "interaction_id": contract.interaction_id,
            "session_id": contract.session_id,
            "agent_target": contract.agent_target,
            "user_input": contract.user_input,
            "agent_response": contract.agent_response,
            "timestamp": contract.timestamp,
        })

        memory["total_interactions"] = len(interactions)
        memory["last_updated"] = datetime.now(timezone.utc).isoformat()

        if len(interactions) >= MAX_INTERACTIONS_BEFORE_COMPRESSION:
            self._compress(estado)
        else:
            self._save_estado(estado)

    def read_memory(self) -> MemoryReadResult:
        """Devuelve el estado actual de la macro-entidad memory."""
        estado = self._load_estado()
        memory = estado.get("memory", {})
        return MemoryReadResult(
            interactions=memory.get("interactions", []),
            compressed_context=memory.get("compressed_context", ""),
            total_interactions=memory.get("total_interactions", 0),
            last_updated=memory.get("last_updated", ""),
        )

    def force_compress(self) -> str:
        """Fuerza la compresión inmediata del contexto acumulado."""
        estado = self._load_estado()
        summary = self._compress(estado)
        return summary

    def clear_interactions(self) -> None:
        """Elimina el historial de interacciones pero conserva el contexto comprimido."""
        estado = self._load_estado()
        memory = estado.setdefault("memory", {})
        memory["interactions"] = []
        memory["total_interactions"] = 0
        memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_estado(estado)

    # ── Lógica de compresión ──────────────────────────────

    def _compress(self, estado: dict[str, Any]) -> str:
        memory = estado.setdefault("memory", {})
        interactions: list[dict[str, Any]] = memory.get("interactions", [])

        if not interactions:
            return ""

        formatted = self._format_interactions_for_compression(interactions)
        summary = self._call_claude_compression(formatted)

        memory["compressed_context"] = summary
        memory["interactions"] = []
        memory["total_interactions"] = 0
        memory["last_compression"] = datetime.now(timezone.utc).isoformat()
        memory["last_updated"] = datetime.now(timezone.utc).isoformat()

        self._save_estado(estado)
        return summary

    def _format_interactions_for_compression(
        self, interactions: list[dict[str, Any]]
    ) -> str:
        lines: list[str] = []
        for i, entry in enumerate(interactions, start=1):
            lines.append(
                f"[{i}] ({entry.get('timestamp', 'sin fecha')}) "
                f"Agente: {entry.get('agent_target', '?')} | "
                f"Input: {entry.get('user_input', '')} | "
                f"Respuesta: {entry.get('agent_response', '')}"
            )
        return "\n".join(lines)

    def _call_claude_compression(self, formatted_interactions: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=COMPRESSION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": formatted_interactions}
            ],
        )
        return message.content[0].text.strip()

    # ── Helpers de I/O ────────────────────────────────────

    def _load_estado(self) -> dict[str, Any]:
        if not ESTADO_PATH.exists():
            raise FileNotFoundError(
                f"[MemoryHelper] estado.json no encontrado en: {ESTADO_PATH}"
            )
        with open(ESTADO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_estado(self, estado: dict[str, Any]) -> None:
        with open(ESTADO_PATH, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)

    def _ensure_estado_memory_structure(self) -> None:
        """Garantiza que la macro-entidad memory existe con estructura mínima."""
        try:
            estado = self._load_estado()
            memory = estado.setdefault("memory", {})
            memory.setdefault("interactions", [])
            memory.setdefault("compressed_context", "")
            memory.setdefault("total_interactions", 0)
            memory.setdefault("last_updated", "")
            memory.setdefault("last_compression", "")
            self._save_estado(estado)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)


# ── Singleton exportable ──────────────────────────────────
memory_helper = MemoryHelper()