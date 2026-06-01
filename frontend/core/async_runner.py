# frontend/core/async_runner.py

import logging
import threading
import time
from typing import Any, Callable

import streamlit as st

logger = logging.getLogger("async_runner")

# ── Timeouts por agente (segundos) ────────────────────────
AGENT_TIMEOUTS: dict[str, int] = {
    "image-generator":  90,
    "animation":        240,
    "upscaler":         120,
    "market-intel":     45,
    "linkedin-writer":  30,
    "orchestrator":     20,
    "default":          60,
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
    """
    Ejecuta fn() en un hilo separado con timeout.
    No bloquea el hilo principal de Streamlit.
    Devuelve RunnerResult con el resultado o el error.
    """
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
        logger.error(
            f"[async_runner] Timeout ({timeout}s) para agente '{agent}'."
        )
        return RunnerResult(
            success=False,
            error=f"Timeout: el agente '{agent}' no respondió en {timeout}s.",
            elapsed=elapsed,
            timed_out=True,
        )

    if "value" in error_container:
        logger.error(
            f"[async_runner] Error en agente '{agent}': {error_container['value']}"
        )
        return RunnerResult(
            success=False,
            error=error_container["value"],
            elapsed=elapsed,
        )

    return RunnerResult(
        success=True,
        data=result_container.get("value"),
        elapsed=elapsed,
    )


# ── Bloque de carga con progreso visual ───────────────────
def run_with_spinner(
    fn: Callable[[], Any],
    agent: str = "default",
    label_override: str = "",
) -> RunnerResult:
    """
    Wrapper completo para llamadas a agentes desde vistas Streamlit.
    Muestra spinner + barra de progreso animada + mensajes de estado.
    Gestiona timeout y errores con feedback visual claro.

    Uso en cualquier vista:
        result = run_with_spinner(
            fn=lambda: image_generator.generate_sync(payload),
            agent="image-generator",
        )
        if result.success:
            st.image(result.data.url)
    """
    messages  = AGENT_PROGRESS_MESSAGES.get(agent, AGENT_PROGRESS_MESSAGES["default"])
    timeout   = AGENT_TIMEOUTS.get(agent, AGENT_TIMEOUTS["default"])
    main_label = label_override or messages[0]

    result_holder: list[RunnerResult] = []
    done_flag = threading.Event()

    # Hilo de ejecución real
    def worker() -> None:
        r = run_with_timeout(fn, agent)
        result_holder.append(r)
        done_flag.set()

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    # UI de progreso en hilo principal
    progress_bar   = st.progress(0, text=main_label)
    status_text    = st.empty()
    t_start        = time.time()
    msg_index      = 0
    update_every   = max(timeout / (len(messages) * 4), 0.5)

    while not done_flag.is_set():
        elapsed_pct = min((time.time() - t_start) / timeout, 0.95)
        current_msg = messages[min(
            int(elapsed_pct * len(messages)),
            len(messages) - 1
        )]

        if int(time.time() / update_every) != msg_index:
            msg_index = int(time.time() / update_every)
            status_text.caption(f"⏱️ {current_msg}")

        progress_bar.progress(elapsed_pct, text=current_msg)
        time.sleep(0.3)

    # Limpiar UI de progreso
    progress_bar.empty()
    status_text.empty()

    result = result_holder[0] if result_holder else RunnerResult(
        success=False, error="El worker no devolvió resultado."
    )

    # Feedback final
    _render_result_feedback(result, agent)
    return result


# ── Feedback post-ejecución ───────────────────────────────
def _render_result_feedback(result: RunnerResult, agent: str) -> None:
    if result.success:
        st.success(
            f"✅ Completado en {result.elapsed}s.",
            icon="✅",
        )
        return

    if result.timed_out:
        timeout = AGENT_TIMEOUTS.get(agent, AGENT_TIMEOUTS["default"])
        st.error(
            f"⏱️ **Timeout ({timeout}s):** El agente `{agent}` tardó demasiado. "
            f"Comprueba tu conexión o reduce la complejidad del prompt.",
            icon="⏱️",
        )
        with st.expander("ℹ️ ¿Qué puedes hacer?"):
                      st.info(...)

                f"- Reintenta en unos segundos.\n"
                f"- Reduce `inference_steps` o la resolución.\n"
                f"- Verifica que `FAL_KEY` sea válida en `.env`.\n"
                f"- Timeout configurado para `{agent}`: **{timeout}s** "
                f"(editable en `core/async_runner.py`)."
            )
        return

    st.error(
        f"❌ **Error en `{agent}`:** {result.error}",
        icon="🚨",
    )
    with st.expander("🔍 Detalle del error"):
        st.code(result.error, language="text")