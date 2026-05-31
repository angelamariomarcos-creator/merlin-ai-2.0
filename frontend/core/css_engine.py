# frontend/core/css_engine.py
from pathlib import Path
import streamlit as st

CSS_PATH = Path(__file__).parent.parent / "styles.css"

@st.cache_resource
def _load_css_template() -> str:
    """Lee el archivo una sola vez. st.cache_resource persiste entre reruns."""
    return CSS_PATH.read_text(encoding="utf-8")

def inject_css(accent: str, bg: str, sidebar: str, text: str) -> None:
    """
    Sustituye las variables CSS con los valores del tema activo
    e inyecta el bloque resultante en el canvas de Streamlit.
    Llamar UNA vez por rerun desde app.py, antes de render de vistas.
    """
    template = _load_css_template()
    css = (
        template
        .replace("{{ACCENT}}", accent)
        .replace("{{BG}}", bg)
        .replace("{{SIDEBAR}}", sidebar)
        .replace("{{TEXT}}", text)
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)