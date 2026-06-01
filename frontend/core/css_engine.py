# frontend/core/css_engine.py
from pathlib import Path
import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent.parent / "styles.css"

@st.cache_resource
def _load_css_template() -> str:
    """Carga y cachea la plantilla CSS una sola vez."""
    if not _CSS_PATH.exists():
        return _DEFAULT_CSS
    return _CSS_PATH.read_text(encoding="utf-8")

def inject_css(accent: str, bg: str, sidebar: str, text: str) -> None:
    """Inyecta el CSS de forma estática para evitar conflictos con el DOM de Streamlit."""
    template = _load_css_template()
    css = (
        template
        .replace("{{ACCENT}}", accent)
        .replace("{{BG}}", bg)
        .replace("{{SIDEBAR}}", sidebar)
        .replace("{{TEXT}}", text)
    )
    
    # Inyección directa. Al usarlo en el punto de entrada de la app, 
    # Streamlit lo tratará como un elemento estático.
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

_DEFAULT_CSS = """
.stApp { background-color: {{BG}}; color: {{TEXT}}; }
[data-testid="stSidebar"] { background-color: {{SIDEBAR}}; }
h1, h2, h3 { color: {{ACCENT}} !important; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: {{BG}}; }
::-webkit-scrollbar-thumb { background: {{ACCENT}}66; border-radius: 3px; }
"""