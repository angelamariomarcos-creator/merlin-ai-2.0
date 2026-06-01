# frontend/core/async_runner.py
import logging
import threading
import time
from typing import Any, Callable

import streamlit as st

logger = logging.getLogger("async_runner")

# ── Timeouts por agente (segundos) ────────────────────────
AGENT_TIMEOUTS: dict[str, int] = {
    "image-generator": 90,
    "animation": 240,
    "upscaler": 120,
    "market-intel": 45,
    "linkedin-writer": 30,
    "orchestrator": 20,
    "default": 60,
}

# ── Mensajes de progreso por agente ──────────────────────
AGENT_PROGRESS_MESSAGES: dict[str, list[str]] = {
    "image-generator": [
        "🔮 Invocando a Merlín...",
        "🎨 FLUX procesando tu prompt...",
        "✨ Aplicando estilos y texturas...",
        "🖼️ Finalizando composición...",
    ],
    "animation": [
        "🔮 Preparando el hechizo de animación...",
        "🎬 SeedAnce analizando la imagen...",
        "🌀 Generando frames de movimiento...",
        "⏱️ Renderizando vídeo 4s...",
        "🎞️ Codificando salida final...",
    ],
    "upscaler": [
        "🔮 Iniciando reescalado 4K...",
        "🔍 AuraSR analizando texturas...",
        "⬆️ Procesando tiles en alta resolución...",
        "✅ Finalizando imagen 4K...",
    ],
    "market-intel": [
        "🔮 Consultando a los oráculos del mercado...",
        "🌐 Perplexity buscando tendencias...",
        "🧠 Claude analizando los datos...",
        "📊 Estructurando informe final...",
    ],
    "linkedin-writer": [
        "🔮 Afilando la pluma editorial...",
        "✍️ Claude redactando el borrador...",
        "📝 Revisando tono y métricas...",
    ],
    "default": [
        "🔮 Procesando...",
        "⚙️ Trabajando en ello...",
        "🌀 Casi listo...",
    ],
}

# ── Resultado del runner ──────────────────────────────────
class RunnerResult:
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = "",
        elapsed: float = 0.0,
        timed_out: bool = False,
    ):
        self.success   = success
        self.data      = data
        self.error     = error
        self.elapsed   = elapsed
        self.timed_out = timed_out

# ── Runner con timeout en hilo separado ───────────────────
def run_with_timeout(
    fn: Callable[[], Any],
    agent: str = "default",
) -> RunnerResult:
    timeout = AGENT_TIMEOUTS.get(agent, AGENT_TIMEOUTS["default"])
    result_container: dict[str, Any] = {}
    error_container:  dict[str, Any] = {}

    def target() -> None:
        try:
            result_container["value"] = fn()
        except Exception as e:
            error_container["value"] = str(e)

    thread = threading.Thread(target=target, daemon=True)
    t_start = time.perf_counter()
    thread.start()
    thread.join(timeout=timeout)
    elapsed = round(time.perf_counter() - t_start, 2)

    if thread.is_alive():
        return RunnerResult(success=False, error=f"Timeout: {agent} no respondió.", elapsed=elapsed, timed_out=True)

    if "value" in error_container:
        return RunnerResult(success=False, error=error_container["value"], elapsed=elapsed)

    return RunnerResult(success=True, data=result_container.get("value"), elapsed=elapsed)

# ── Bloque de carga con progreso visual ───────────────────
def run_with_spinner(
    fn: Callable[[], Any],
    agent: str = "default",
    label_override: str = "",
) -> RunnerResult:
    messages  = AGENT_PROGRESS_MESSAGES.get(agent, AGENT_PROGRESS_MESSAGES["default"])
    timeout   = AGENT_TIMEOUTS.get(agent, AGENT_TIMEOUTS["default"])
    main_label = label_override or messages[0]

    result_holder: list[RunnerResult] = []
    done_flag = threading.Event()

    def worker() -> None:
        r = run_with_timeout(fn, agent)
        result_holder.append(r)
        done_flag.set()

    threading.Thread(target=worker, daemon=True).start()

    progress_bar = st.progress(0, text=main_label)
    # Cambio clave: usamos un contenedor en lugar de st.empty() para evitar el removeChild
    status_container = st.container()
    
    t_start = time.time()
    while not done_flag.is_set():
        elapsed_pct = min((time.time() - t_start) / timeout, 0.95)
        current_msg = messages[min(int(elapsed_pct * len(messages)), len(messages) - 1)]
        
        progress_bar.progress(elapsed_pct, text=current_msg)
        with status_container:
            st.caption(f"⏱️ {current_msg}")
        
        time.sleep(0.5)

    progress_bar.empty()
    status_container.empty()

    result = result_holder[0] if result_holder else RunnerResult(success=False, error="Error interno.")
    _render_result_feedback(result, agent)
    return result

def _render_result_feedback(result: RunnerResult, agent: str) -> None:
    if result.success:
        st.success(f"✅ Completado en {result.elapsed}s.", icon="✅")
    elif result.timed_out:
        st.error(f"⏱️ Timeout: El agente `{agent}` tardó demasiado.", icon="⏱️")
    else:
        st.error(f"❌ Error en `{agent}`: {result.error}", icon="🚨")