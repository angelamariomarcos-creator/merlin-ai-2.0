# frontend/views/dashboard.py
import streamlit as st

def render() -> None:
    """
    Punto de entrada único para esta vista.
    - Sin parámetros: lee estado desde st.session_state.
    - Sin retorno: escribe directamente en el canvas de Streamlit.
    """
    st.subheader("🛸 Dashboard General · Panel de Control")
    st.write("Bienvenido al módulo central de Merlín AI 2.0")