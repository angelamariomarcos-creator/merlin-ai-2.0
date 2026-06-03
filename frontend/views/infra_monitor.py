# frontend/views/infra_monitor.py
import streamlit as st

def render() -> None:
    st.subheader("🛡️ Monitor de Infraestructura")
    st.write("Estado de los servidores, contenedores y servicios en tiempo real.")