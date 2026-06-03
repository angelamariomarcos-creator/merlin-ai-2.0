# frontend/views/thresholds.py
import streamlit as st
from frontend.core.persistence import guardar_estado_local

def render() -> None:
    st.subheader("Configuración de Umbrales Operativos")

    st.slider("Coste máximo por imagen (USD)", 0.001, 0.100, step=0.001, key="max_cost_per_image_usd")
    st.slider("Coste máximo por vídeo (USD)", 0.010, 0.300, step=0.005, key="max_cost_per_video_usd")
    st.slider("Margen mínimo requerido (%)", 50.0, 90.0, step=0.5, key="margin_floor_pct")
    st.slider("Inference steps FLUX", 1, 50, step=1, key="flux_inference_steps")
    st.slider("Guidance scale FLUX", 1.0, 7.0, step=0.1, key="default_guidance_scale")

    if st.button("💾 Guardar umbrales"):
        ok = guardar_estado_local()
        st.toast("✅ Umbrales persistidos." if ok else "❌ Error al persistir.")