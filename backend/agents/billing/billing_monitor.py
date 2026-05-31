# backend/agents/billing/billing_monitor.py

import json
import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config.settings import settings

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("billing_monitor")

# ── Rutas ─────────────────────────────────────────────────
PROJECT_ROOT  = Path("C:/merlin-ai-2.0")
ESTADO_PATH   = PROJECT_ROOT / "backend" / "core" / "estado.json"

# ── Umbrales financieros ──────────────────────────────────
MARGIN_THRESHOLD_PCT: Decimal = Decimal("70.0")

# ── Tarifas reales por agente (USD por llamada) ───────────
# Actualizar cuando cambien precios en FAL.AI
AGENT_UNIT_COSTS: dict[str, Decimal] = {
    "image-generator":  Decimal("0.025"),   # FLUX Dev por imagen
    "animation":        Decimal("0.080"),   # SeedAnce 4s por vídeo
    "upscaler":         Decimal("0.010"),   # AuraSR 4K por imagen
    "memory-helper":    Decimal("0.002"),   # Claude API compresión (estimado)
    "orchestrator":     Decimal("0.001"),   # Claude API routing (estimado)
    "logger":           Decimal("0.000"),
    "billing-monitor":  Decimal("0.000"),
}


# ── Contrato de entrada ───────────────────────────────────
class BillingCheckInput(BaseModel):
    model_config = {"strict": True}

    session_id: str = Field(min_length=1)
    stripe_revenue: float = Field(
        gt=0,
        description="Ingreso bruto recibido por Stripe para esta sesión (USD)."
    )
    api_costs_accumulated: float = Field(
        ge=0,
        description="Coste acumulado real de todas las llamadas a APIs externas (USD)."
    )
    agent_call_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Desglose opcional de llamadas por agente para auditoría. "
            "Ej: {'image-generator': 2, 'animation': 1}"
        )
    )
    stripe_fee_included: bool = Field(
        default=True,
        description="Si True, descuenta la comisión de Stripe (2.9% + 0.30 USD) del ingreso."
    )

    @field_validator("session_id", mode="before")
    @classmethod
    def strip_session_id(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("session_id no puede ser una cadena vacía.")
        return v.strip()

    @field_validator("stripe_revenue", "api_costs_accumulated", mode="before")
    @classmethod
    def validate_positive_numbers(cls, v: float) -> float:
        if not isinstance(v, (int, float)):
            raise TypeError("Los valores financieros deben ser numéricos.")
        return float(v)

    @model_validator(mode="after")
    def validate_costs_vs_revenue(self) -> "BillingCheckInput":
        if self.api_costs_accumulated > self.stripe_revenue * 10:
            raise ValueError(
                f"api_costs_accumulated ({self.api_costs_accumulated}) supera "
                f"en 10x el stripe_revenue ({self.stripe_revenue}). "
                f"Verifica los datos antes de registrar."
            )
        return self


# ── Contrato de salida ────────────────────────────────────
class BillingCheckOutput(BaseModel):
    session_id: str
    stripe_revenue_gross: float
    stripe_revenue_net: float
    api_costs_accumulated: float
    estimated_costs_from_breakdown: float
    margin_percentage: float
    is_profitable: bool
    action_required: bool
    alert_level: str          # "OK" | "WARNING" | "CRITICAL"
    alert_message: str
    agent_call_breakdown: dict[str, int]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Motor de monitorización financiera ───────────────────
class BillingMonitor:
    """
    Agente financiero de Merlín AI 2.0.
    - Calcula margen neto con precisión Decimal.
    - Aplica regla estricta del 70% de margen mínimo.
    - Persiste registro en la macro-entidad billing de estado.json.
    - Opera de forma totalmente autónoma sin dependencias externas.
    """

    # ── API pública ───────────────────────────────────────

    def check(self, raw_payload: dict[str, Any]) -> BillingCheckOutput:
        """
        Punto de entrada principal.
        Acepta dict crudo, valida con BillingCheckInput
        y devuelve BillingCheckOutput con veredicto financiero.
        """
        contract = BillingCheckInput.model_validate(raw_payload)

        revenue_gross = Decimal(str(contract.stripe_revenue))
        revenue_net   = self._apply_stripe_fee(revenue_gross, contract.stripe_fee_included)
        cost_real     = Decimal(str(contract.api_costs_accumulated))
        cost_estimated = self._estimate_from_breakdown(contract.agent_call_breakdown)
        cost_final    = max(cost_real, cost_estimated)

        margin        = self._calculate_margin(revenue_net, cost_final)
        is_profitable = margin >= MARGIN_THRESHOLD_PCT
        alert_level, alert_message = self._resolve_alert(margin, is_profitable)

        output = BillingCheckOutput(
            session_id=contract.session_id,
            stripe_revenue_gross=float(revenue_gross),
            stripe_revenue_net=float(revenue_net),
            api_costs_accumulated=float(cost_real),
            estimated_costs_from_breakdown=float(cost_estimated),
            margin_percentage=float(margin),
            is_profitable=is_profitable,
            action_required=not is_profitable,
            alert_level=alert_level,
            alert_message=alert_message,
            agent_call_breakdown=contract.agent_call_breakdown,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._emit_log(output)
        self._persist_to_estado(output)
        return output

    # ── Cálculo de margen ─────────────────────────────────

    def _calculate_margin(
        self,
        revenue_net: Decimal,
        cost: Decimal,
    ) -> Decimal:
        """
        Margen = ((Ingreso_neto - Coste) / Ingreso_neto) * 100
        Precisión: ROUND_HALF_UP a 4 decimales.
        """
        if revenue_net <= Decimal("0"):
            raise ValueError(
                "[BillingMonitor] revenue_net debe ser mayor que 0 "
                "para calcular el margen."
            )
        raw_margin = ((revenue_net - cost) / revenue_net) * Decimal("100")
        return raw_margin.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def _apply_stripe_fee(
        self,
        gross: Decimal,
        apply: bool,
    ) -> Decimal:
        """
        Comisión Stripe estándar: 2.9% + 0.30 USD por transacción.
        https://stripe.com/es/pricing
        """
        if not apply:
            return gross
        stripe_pct  = Decimal("0.029")
        stripe_flat = Decimal("0.30")
        fee = (gross * stripe_pct + stripe_flat).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        return (gross - fee).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _estimate_from_breakdown(
        self,
        breakdown: dict[str, int],
    ) -> Decimal:
        """
        Calcula coste estimado desde el desglose de llamadas por agente.
        Usa AGENT_UNIT_COSTS como tabla de tarifas.
        """
        if not breakdown:
            return Decimal("0")
        total = Decimal("0")
        for agent, calls in breakdown.items():
            unit = AGENT_UNIT_COSTS.get(agent, Decimal("0.005"))
            total += unit * Decimal(str(calls))
        return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    # ── Sistema de alertas ────────────────────────────────

    def _resolve_alert(
        self,
        margin: Decimal,
        is_profitable: bool,
    ) -> tuple[str, str]:
        if margin >= MARGIN_THRESHOLD_PCT:
            return (
                "OK",
                f"Margen saludable: {margin}% (umbral mínimo: {MARGIN_THRESHOLD_PCT}%)"
            )
        elif margin >= Decimal("50.0"):
            return (
                "WARNING",
                f"Margen por debajo del umbral: {margin}% < {MARGIN_THRESHOLD_PCT}%. "
                f"Revisar costes de APIs o precio de sesión."
            )
        else:
            return (
                "CRITICAL",
                f"MARGEN CRÍTICO: {margin}% — umbral mínimo requerido: "
                f"{MARGIN_THRESHOLD_PCT}%. Operación NO rentable. "
                f"Acción inmediata requerida."
            )

    def _emit_log(self, output: BillingCheckOutput) -> None:
        msg = (
            f"[BillingMonitor] session={output.session_id} | "
            f"revenue_net={output.stripe_revenue_net:.4f} USD | "
            f"costs={output.api_costs_accumulated:.4f} USD | "
            f"margin={output.margin_percentage:.4f}% | "
            f"alert={output.alert_level}"
        )
        if output.alert_level == "CRITICAL":
            logger.critical(msg)
        elif output.alert_level == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)

    # ── Persistencia en estado.json ───────────────────────

    def _persist_to_estado(self, output: BillingCheckOutput) -> None:
        if not ESTADO_PATH.exists():
            logger.error(
                f"[BillingMonitor] estado.json no encontrado en {ESTADO_PATH}. "
                f"No se persiste el registro de billing."
            )
            return
        try:
            with open(ESTADO_PATH, "r", encoding="utf-8") as f:
                estado = json.load(f)

            billing = estado.setdefault("billing", {})
            billing.setdefault("registros", [])
            billing.setdefault("total_sessions_checked", 0)
            billing.setdefault("total_revenue_net_usd", 0.0)
            billing.setdefault("total_costs_usd", 0.0)
            billing.setdefault("critical_alerts", 0)
            billing.setdefault("warning_alerts", 0)

            billing["registros"].append(output.to_dict())
            billing["total_sessions_checked"] += 1
            billing["total_revenue_net_usd"] = round(
                billing["total_revenue_net_usd"] + output.stripe_revenue_net, 6
            )
            billing["total_costs_usd"] = round(
                billing["total_costs_usd"] + output.api_costs_accumulated, 6
            )
            billing["last_check"] = output.timestamp

            if output.alert_level == "CRITICAL":
                billing["critical_alerts"] += 1
            elif output.alert_level == "WARNING":
                billing["warning_alerts"] += 1

            with open(ESTADO_PATH, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"[BillingMonitor] Error persistiendo en estado.json: {e}")


# ── Singleton exportable ──────────────────────────────────
billing_monitor = BillingMonitor()