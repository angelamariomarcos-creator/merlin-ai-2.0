# frontend/views/settings.py
import streamlit as st
def render() -> None:
    st.subheader("⚙️ Configuracion")
    st.slider("Inference steps FLUX", 1, 50, step=1, key="flux_steps")
    st.slider("Guidance scale FLUX", 1.0, 7.0, step=0.1, key="guidance_scale")
    st.info("Mas opciones de configuracion proximamente.")