# frontend/views/logs.py
import streamlit as st

def render() -> None:
    st.subheader("📬 Logs del Sistema en Vivo")
    st.write("Consola de salida con los eventos de backend y trazas del sistema.")