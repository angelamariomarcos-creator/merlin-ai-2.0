# frontend/views/dashboard.py
import streamlit as st

def render() -> None:
    st.subheader("Panel de Control · Merlin AI 2.0")
    col1, col2, col3 = st.columns(3)
    col1.metric("Imagenes generadas", len(st.session_state.get("galeria", [])))
    col2.metric("Estado", "🟢 Online")
    col3.metric("Version", "2.0.0")
    st.info("Selecciona un módulo en el sidebar para comenzar.")