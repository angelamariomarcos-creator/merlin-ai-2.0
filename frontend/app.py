# frontend/app.py
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from frontend.config.themes import THEMES
from frontend.config.views import VIEWS
from frontend.core.session import init_session
from frontend.core.css_engine import inject_css
from frontend.core.registry import dispatch

st.set_page_config(
    page_title="Merlin AI 2.0",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

with st.sidebar:
    st.title("🔮 Merlin AI 2.0")
    st.divider()
    selected_theme = st.selectbox("🎨 Tema", list(THEMES.keys()), key="tema")
    st.divider()
    selected_view = st.radio("📂 Módulos", VIEWS, key="vista")
    st.divider()
    st.caption("v2.0.0 · Fase 5")
    st.caption(f"🖼 Galería: {len(st.session_state.get('galeria', []))} items")

inject_css(**THEMES[selected_theme])

st.title(selected_view)
st.divider()
dispatch(selected_view)