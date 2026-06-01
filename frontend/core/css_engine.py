# frontend/core/css_engine.py

from pathlib import Path
import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent.parent / "styles.css"


@st.cache_resource
def _load_css_template() -> str:
    if not _CSS_PATH.exists():
        return ""
    return _CSS_PATH.read_text(encoding="utf-8")


def inject_css(
    accent: str,
    bg: str,
    sidebar: str,
    text: str,
) -> None:
    template = _load_css_template()
    if not template:
        # Fallback inline si styles.css no existe
        template = _DEFAULT_CSS

    css = (
        template
        .replace("{{ACCENT}}", accent)
        .replace("{{BG}}", bg)
        .replace("{{SIDEBAR}}", sidebar)
        .replace("{{TEXT}}", text)
    )

    # CRÍTICO: usar un contenedor vacío fijo para evitar
    # que React intente reconciliar nodos huérfanos en reruns
    if "css_placeholder" not in st.session_state:
        st.session_state.css_placeholder = st.empty()

    st.session_state.css_placeholder.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


_DEFAULT_CSS = """
.stApp { background-color: {{BG}}; color: {{TEXT}}; }
[data-testid="stSidebar"] { background-color: {{SIDEBAR}}; }
h1, h2, h3 { color: {{ACCENT}} !important; }
.merlin-card {
    background-color: {{SIDEBAR}};
    border: 1px solid {{ACCENT}}55;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.gallery-card {
    background-color: {{SIDEBAR}};
    border: 1px solid {{ACCENT}}33;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    font-size: 0.85rem;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: {{BG}}; }
::-webkit-scrollbar-thumb { background: {{ACCENT}}66; border-radius: 3px; }
"""