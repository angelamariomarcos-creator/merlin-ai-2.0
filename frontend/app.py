# frontend/app.py

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from frontend.config.styles      import STYLES
from frontend.config.views       import VIEWS
from frontend.core.css_engine    import inject_css
from frontend.core.session       import init_session
from frontend.core.persistence   import guardar_estado_local, resetear_estado_local
from frontend.core.registry      import dispatch
from frontend.components.sidebar import render_sidebar

st.set_page_config(
    page_title="Merlín AI 2.0",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

selected_style, selected_view = render_sidebar(STYLES, VIEWS)

inject_css(**STYLES[selected_style])

with st.sidebar:
    st.divider()
    if st.button("💾 Guardar sesión", use_container_width=True):
        ok = guardar_estado_local()
        st.toast("✅ Estado guardado." if ok else "❌ Error al guardar.")
    if st.button("🗑 Resetear sesión", use_container_width=True):
        resetear_estado_local()
        st.rerun()
    st.caption("v2.0.0 · Fase 5.3")
    st.caption(f"🖼 Galería: {len(st.session_state.get('galeria', []))} items")

st.title(selected_view)
st.divider()
dispatch(selected_view)