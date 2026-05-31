# backend/agents/marketing/backlinking_agent.py

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import requests
from pydantic import BaseModel, Field, field_validator

from backend.config.settings import settings

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backlinking_agent")

# ── Rutas ─────────────────────────────────────────────────
PROJECT_ROOT = Path("C:/merlin-ai-2.0")
ESTADO_PATH  = PROJECT_ROOT / "backend" / "core" / "estado.json"
DRAFTS_DIR   = PROJECT_ROOT / "backend" / "agents" / "marketing" / "drafts"

# ── Umbrales operativos modificables en caliente ──────────
REMEDIATION_THRESHOLDS: dict[str, Any] = {
    "max_cost_per_image_usd":  0.035,
    "max_cost_per_video_usd":  0.100,
    "margin_floor_pct":        70.0,
    "flux_inference_steps":    28,
    "default_guidance_scale":  3.5,
}

# ── Perplexity ────────────────────────────────────────────
PERPLEXITY_URL   = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"
PERPLEXITY_QUERY_TEMPLATE = (
    "Search for news from the last 7 days about: {niche}. "
    "Focus strictly on: API price changes, model deprecations, "
    "infrastructure outages, new competitor launches, and demand spikes. "
    "Return only factual data with sources and dates. No opinions."
)

# ── Prompt de análisis Claude ─────────────────────────────
MARKET_ANALYSIS_SYSTEM_PROMPT = """
You are a senior market intelligence analyst for an AI-powered image generation SaaS.
You will receive raw internet data fetched by an external search engine (Perplexity).
Your ONLY job: analyze that data and return a structured JSON classification.

Output rules — non-negotiable:
- No filler words. No AI-sounding phrases. No "it's worth noting", no "in conclusion".
- Short sentences. Metrics first. CTO voice.
- linkedin_draft must read like a human wrote it at 6am before a board meeting.
- Banned words: "revolutionize", "game-changer", "leverage", "seamless", "robust",
  "cutting-edge", "innovative", "delve", "empower", "transformative", "unlock".
- Trend type must be ONE of: PRICE_SHIFT | MODEL_DEPRECATION | PROMPT_OPTIMIZATION |
  DEMAND_SPIKE | COMPETITOR_MOVE

Respond ONLY with this JSON. No markdown, no backticks, no preamble:
{
  "trend_type": "<CLASSIFICATION>",
  "trend_summary": "<1 brutal sentence>",
  "metric_highlight": "<key stat or empty string>",
  "recommended_internal_action": "<what to adjust internally, or NONE>",
  "linkedin_draft": "<full markdown post, human CTO voice, metrics-first>"
}
""".strip()


# ── Contratos Pydantic ────────────────────────────────────
class MarketingInputContract(BaseModel):
    model_config = {"strict": True}

    session_id: str = Field(min_length=1)
    target_niche: str = Field(
        min_length=3,
        max_length=200,
        description="Nicho de mercado a analizar. Ej: 'AI image generation for e-commerce'"
    )

    @field_validator("session_id", "target_niche", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("El campo no puede ser una cadena vacía.")
        return v.strip()


class MarketingOutputContract(BaseModel):
    generation_id:       str
    session_id:          str
    target_niche:        str
    market_trend_found:  str
    trend_type:          str
    metric_highlight:    str
    draft_text:          str
    draft_file_path:     str
    auto_executed_action: bool
    action_details:      str
    thresholds_snapshot: dict[str, Any]
    perplexity_used:     bool
    timestamp:           str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Agente de Marketing ───────────────────────────────────
class BacklinkingAgent:
    """
    Agente de inteligencia de mercado con separación real de tareas:
    - Perplexity API: búsqueda factual de internet (últimos 7 días).
    - Claude API: análisis, clasificación y redacción editorial.
    - Action Engine: remediación automática de infraestructura interna.
    - Drafts: guardado local Markdown para revisión y publicación manual.
    """

    def __init__(self) -> None:
        self._claude     = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._claude_model = "claude-sonnet-4-20250514"
        self._perplexity_key: str = settings.PERPLEXITY_API_KEY or ""
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── API pública ───────────────────────────────────────

    def analyze(self, raw_payload: dict[str, Any]) -> MarketingOutputContract:
        """
        Flujo completo:
        1. Validar contrato de entrada.
        2. Perplexity fetcha datos reales de internet.
        3. Claude analiza y estructura el JSON de tendencias.
        4. Action Engine evalúa y ejecuta remediación.
        5. Guardar borrador Markdown local.
        6. Persistir en estado.json.
        7. Devolver MarketingOutputContract.
        """
        contract = MarketingInputContract.model_validate(raw_payload)

        raw_internet_data, perplexity_used = self._fetch_perplexity_real_data(
            contract.target_niche
        )
        trend_data = self._process_data_with_claude(raw_internet_data)
        auto_executed, action_details = self._evaluate_and_execute_remediation(trend_data)
        draft_path = self._save_draft_markdown(
            session_id=contract.session_id,
            niche=contract.target_niche,
            trend_data=trend_data,
        )

        output = MarketingOutputContract(
            generation_id=str(uuid.uuid4()),
            session_id=contract.session_id,
            target_niche=contract.target_niche,
            market_trend_found=trend_data.get("trend_summary", ""),
            trend_type=trend_data.get("trend_type", "UNKNOWN"),
            metric_highlight=trend_data.get("metric_highlight", ""),
            draft_text=trend_data.get("linkedin_draft", ""),
            draft_file_path=str(draft_path),
            auto_executed_action=auto_executed,
            action_details=action_details,
            thresholds_snapshot=dict(REMEDIATION_THRESHOLDS),
            perplexity_used=perplexity_used,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._persist_to_estado(output)
        logger.info(
            f"[BacklinkingAgent] session={contract.session_id} | "
            f"trend={output.trend_type} | "
            f"perplexity={perplexity_used} | "
            f"auto_executed={auto_executed} | "
            f"draft={draft_path.name}"
        )
        return output

    # ── Capa 1: Perplexity — búsqueda real ───────────────

    def _fetch_perplexity_real_data(self, niche: str) -> tuple[str, bool]:
        """
        Realiza petición HTTP real a Perplexity API (modelo sonar).
        Devuelve (texto_crudo, perplexity_usado).
        Si la key no existe o falla, devuelve fallback sin romper el flujo.
        """
        if not self._perplexity_key or self._perplexity_key.strip() == "":
            logger.warning(
                "[BacklinkingAgent] PERPLEXITY_API_KEY no definida. "
                "Usando fallback: Claude analizará sin datos frescos de internet."
            )
            return self._perplexity_fallback(niche), False

        headers = {
            "Authorization": f"Bearer {self._perplexity_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a factual news retrieval engine. "
                        "Return only verified recent data with dates and sources. "
                        "No analysis, no opinions, no editorializing."
                    )
                },
                {
                    "role": "user",
                    "content": PERPLEXITY_QUERY_TEMPLATE.format(niche=niche)
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.1,
            "search_recency_filter": "week",
        }

        try:
            response = requests.post(
                PERPLEXITY_URL,
                headers=headers,
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            content: str = (
                data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
            )
            if not content:
                logger.warning(
                    "[BacklinkingAgent] Perplexity devolvió contenido vacío. "
                    "Activando fallback."
                )
                return self._perplexity_fallback(niche), False

            logger.info(
                f"[BacklinkingAgent] Perplexity OK. "
                f"Datos recibidos: {len(content)} chars."
            )
            return content, True

        except requests.exceptions.Timeout:
            logger.warning("[BacklinkingAgent] Perplexity timeout (20s). Fallback activado.")
            return self._perplexity_fallback(niche), False
        except requests.exceptions.HTTPError as e:
            logger.warning(
                f"[BacklinkingAgent] Perplexity HTTP error {e.response.status_code}. "
                f"Fallback activado."
            )
            return self._perplexity_fallback(niche), False
        except Exception as e:
            logger.warning(f"[BacklinkingAgent] Perplexity error inesperado: {e}. Fallback activado.")
            return self._perplexity_fallback(niche), False

    def _perplexity_fallback(self, niche: str) -> str:
        return (
            f"[FALLBACK — Perplexity no disponible] "
            f"Analyze general market trends for the niche: '{niche}'. "
            f"Use your training knowledge to identify the most relevant recent trend. "
            f"Be explicit that this analysis is based on training data, not live search."
        )

    # ── Capa 2: Claude — análisis y estructuración ────────

    def _process_data_with_claude(self, raw_internet_data: str) -> dict[str, Any]:
        """
        Claude recibe el informe crudo de Perplexity y SOLO estructura
        la clasificación JSON. No busca en internet. No inventa datos.
        """
        message = self._claude.messages.create(
            model=self._claude_model,
            max_tokens=1024,
            system=MARKET_ANALYSIS_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Here is the raw internet data retrieved by Perplexity "
                        f"for your analysis:\n\n"
                        f"---BEGIN RAW DATA---\n"
                        f"{raw_internet_data}\n"
                        f"---END RAW DATA---\n\n"
                        f"Classify the dominant trend and return the JSON."
                    )
                }
            ],
        )

        raw = message.content[0].text.strip()

        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"[BacklinkingAgent] Claude no devolvió JSON válido.\n"
                f"Raw: {raw}\nError: {e}"
            )

    # ── Capa 3: Action Engine — remediación interna ───────

    def _evaluate_and_execute_remediation(
        self,
        trend_data: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Evalúa trend_type y aplica correcciones sobre REMEDIATION_THRESHOLDS.
        Solo modifica parámetros internos en memoria y estado.json.
        No toca APIs externas ni archivos de código fuente.
        """
        trend_type: str  = trend_data.get("trend_type", "")
        recommended: str = trend_data.get("recommended_internal_action", "NONE")

        if recommended.strip().upper() == "NONE" or not recommended.strip():
            return False, "No se requirió acción correctora automática."

        action_log: list[str] = []
        executed = False

        # ── Regla 1: Cambio de precios en APIs ────────────
        if trend_type == "PRICE_SHIFT":
            old_img = REMEDIATION_THRESHOLDS["max_cost_per_image_usd"]
            old_vid = REMEDIATION_THRESHOLDS["max_cost_per_video_usd"]
            REMEDIATION_THRESHOLDS["max_cost_per_image_usd"] = round(old_img * 0.90, 4)
            REMEDIATION_THRESHOLDS["max_cost_per_video_usd"] = round(old_vid * 0.90, 4)
            action_log.append(
                f"PRICE_SHIFT — umbrales de coste reducidos 10%: "
                f"imagen {old_img}→{REMEDIATION_THRESHOLDS['max_cost_per_image_usd']} USD | "
                f"vídeo {old_vid}→{REMEDIATION_THRESHOLDS['max_cost_per_video_usd']} USD."
            )
            executed = True

        # ── Regla 2: Modelo deprecado ─────────────────────
        elif trend_type == "MODEL_DEPRECATION":
            old_steps = REMEDIATION_THRESHOLDS["flux_inference_steps"]
            REMEDIATION_THRESHOLDS["flux_inference_steps"] = min(old_steps + 4, 50)
            action_log.append(
                f"MODEL_DEPRECATION — inference_steps incrementado: "
                f"{old_steps}→{REMEDIATION_THRESHOLDS['flux_inference_steps']} "
                f"para compensar pérdida de calidad."
            )
            executed = True

        # ── Regla 3: Optimización de prompts ──────────────
        elif trend_type == "PROMPT_OPTIMIZATION":
            old_guidance = REMEDIATION_THRESHOLDS["default_guidance_scale"]
            REMEDIATION_THRESHOLDS["default_guidance_scale"] = round(
                min(old_guidance + 0.5, 7.0), 2
            )
            action_log.append(
                f"PROMPT_OPTIMIZATION — guidance_scale ajustado: "
                f"{old_guidance}→{REMEDIATION_THRESHOLDS['default_guidance_scale']}."
            )
            executed = True

        # ── Regla 4: Pico de demanda ──────────────────────
        elif trend_type == "DEMAND_SPIKE":
            old_margin = REMEDIATION_THRESHOLDS["margin_floor_pct"]
            REMEDIATION_THRESHOLDS["margin_floor_pct"] = min(old_margin + 2.0, 85.0)
            action_log.append(
                f"DEMAND_SPIKE — margin_floor_pct elevado: "
                f"{old_margin}%→{REMEDIATION_THRESHOLDS['margin_floor_pct']}% "
                f"para capturar mayor rentabilidad."
            )
            executed = True

        # ── Regla 5: Movimiento competidor ────────────────
        elif trend_type == "COMPETITOR_MOVE":
            action_log.append(
                "COMPETITOR_MOVE detectado. Sin parámetros internos afectados. "
                "Requiere revisión editorial manual del Director."
            )
            executed = False

        if executed:
            self._persist_runtime_overrides()

        return executed, " | ".join(action_log) if action_log else "Sin acción ejecutada."

    # ── Guardado de borrador Markdown ─────────────────────

    def _save_draft_markdown(
        self,
        session_id: str,
        niche: str,
        trend_data: dict[str, Any],
    ) -> Path:
        ts         = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_niche = niche.replace(" ", "_").replace("/", "-")[:40]
        filename   = f"{ts}_{safe_niche}.md"
        filepath   = DRAFTS_DIR / filename

        draft_content = trend_data.get("linkedin_draft", "")
        metric        = trend_data.get("metric_highlight", "")
        trend_summary = trend_data.get("trend_summary", "")
        trend_type    = trend_data.get("trend_type", "")

        markdown = (
            f"---\n"
            f"session_id: {session_id}\n"
            f"niche: {niche}\n"
            f"trend_type: {trend_type}\n"
            f"metric_highlight: {metric}\n"
            f"generated_at: {datetime.now(timezone.utc).isoformat()}\n"
            f"status: PENDING_MANUAL_REVIEW\n"
            f"publishing: MANUAL_ONLY — DO NOT AUTO-POST\n"
            f"---\n\n"
            f"## Tendencia detectada\n\n"
            f"{trend_summary}\n\n"
            f"---\n\n"
            f"## Borrador LinkedIn\n\n"
            f"{draft_content}\n"
        )

        try:
            filepath.write_text(markdown, encoding="utf-8")
            logger.info(f"[BacklinkingAgent] Borrador guardado: {filepath}")
        except OSError as e:
            logger.error(f"[BacklinkingAgent] Error guardando borrador: {e}")

        return filepath

    # ── Persistencia: runtime_overrides ───────────────────

    def _persist_runtime_overrides(self) -> None:
        if not ESTADO_PATH.exists():
            logger.error(
                "[BacklinkingAgent] estado.json no encontrado. "
                "No se persisten runtime_overrides."
            )
            return
        try:
            with open(ESTADO_PATH, "r", encoding="utf-8") as f:
                estado = json.load(f)

            session = estado.setdefault("session", {})
            session["runtime_overrides"] = dict(REMEDIATION_THRESHOLDS)
            session["last_override_at"]  = datetime.now(timezone.utc).isoformat()

            with open(ESTADO_PATH, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)

            logger.info("[BacklinkingAgent] runtime_overrides persistidos en estado.json.")
        except json.JSONDecodeError as e:
            logger.error(f"[BacklinkingAgent] estado.json corrupto al leer overrides: {e}")
        except OSError as e:
            logger.error(f"[BacklinkingAgent] Error de I/O persistiendo overrides: {e}")

    # ── Persistencia: registro de ejecución ───────────────

    def _persist_to_estado(self, output: MarketingOutputContract) -> None:
        if not ESTADO_PATH.exists():
            logger.error(
                "[BacklinkingAgent] estado.json no encontrado. "
                "No se persiste el registro de marketing."
            )
            return
        try:
            with open(ESTADO_PATH, "r", encoding="utf-8") as f:
                estado = json.load(f)

            memory = estado.setdefault("memory", {})
            marketing_log: list[dict] = memory.setdefault("marketing_log", [])
            marketing_log.append({
                "generation_id":      output.generation_id,
                "session_id":         output.session_id,
                "target_niche":       output.target_niche,
                "trend_type":         output.trend_type,
                "perplexity_used":    output.perplexity_used,
                "auto_executed":      output.auto_executed_action,
                "action_details":     output.action_details,
                "draft_file":         output.draft_file_path,
                "timestamp":          output.timestamp,
            })
            memory["last_marketing_run"] = output.timestamp

            with open(ESTADO_PATH, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)

        except json.JSONDecodeError as e:
            logger.error(f"[BacklinkingAgent] estado.json corrupto al persistir: {e}")
        except OSError as e:
            logger.error(f"[BacklinkingAgent] Error de I/O persistiendo marketing log: {e}")


# ── Singleton exportable ──────────────────────────────────
backlinking_agent = BacklinkingAgent()