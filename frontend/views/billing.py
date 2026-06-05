# frontend/views/billing.py
import streamlit as st
import time


# Costes aproximados por operación en FAL.AI
COSTS = {
    "imagen_flux": 0.003,      # FLUX Dev por imagen
    "video_seedance": 0.025,   # SeedAnce Lite 5s
    "upscale_aura": 0.001,     # AuraSR por imagen
}


def render() -> None:
    st.subheader("💰 Control de Costes y Márgenes")
    st.caption("Seguimiento de uso y costes estimados de APIs")
    st.divider()

    # ── Resumen de sesión ─────────────────────────────────
    galeria = st.session_state.get("galeria", [])
    videos  = st.session_state.get("videos", [])

    n_imagenes = len(galeria)
    n_videos   = len(videos)

    coste_imagenes = n_imagenes * COSTS["imagen_flux"]
    coste_videos   = n_videos   * COSTS["video_seedance"]
    coste_total    = coste_imagenes + coste_videos

    col1, col2, col3 = st.columns(3)
    col1.metric("🖼️ Imágenes generadas", n_imagenes, f"~${coste_imagenes:.4f}")
    col2.metric("🎬 Videos generados",   n_videos,   f"~${coste_videos:.4f}")
    col3.metric("💸 Coste total sesión", f"${coste_total:.4f}", "estimado")

    st.divider()

    # ── Tabla de precios de referencia ────────────────────
    st.subheader("📊 Precios de referencia FAL.AI")
    st.table({
        "Operación": ["Imagen FLUX Dev", "Video SeedAnce 5s", "Upscale AuraSR"],
        "Coste aprox.": ["$0.003", "$0.025", "$0.001"],
        "100 unidades": ["$0.30", "$2.50", "$0.10"],
        "1000 unidades": ["$3.00", "$25.00", "$1.00"],
    })

    st.divider()

    # ── Configuración de alertas ──────────────────────────
    st.subheader("⚙️ Umbrales de alerta")

    budget = st.number_input(
        "Presupuesto máximo por sesión (USD)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        key="budget_limit",
    )

    if coste_total > budget:
        st.error(f"⚠️ Has superado el presupuesto de ${budget:.2f}. Coste actual: ${coste_total:.4f}")
    elif coste_total > budget * 0.8:
        st.warning(f"⚠️ Al 80% del presupuesto. Coste actual: ${coste_total:.4f}")
    else:
        st.success(f"✅ Dentro del presupuesto. Quedan ${budget - coste_total:.4f}")

    st.divider()
    st.caption("💡 Los costes son estimados. Consulta tu dashboard de FAL.AI para datos exactos.")
    st.markdown("[🔗 Ver dashboard FAL.AI](https://fal.ai/dashboard)")