# frontend/app.py

import streamlit as st
from config.styles import STYLES
from config.views import VIEWS
from core.css_engine import inject_css
from core.session import init_session
from components.sidebar import render_sidebar
from core.registry import VIEWS_REGISTRY
from core.persistence import guardar_estado_local, resetear_estado_local

# 1. Configuración de la ventana del navegador
st.set_page_config(page_title="Merlín AI 2.0", page_icon="🔮", layout="wide")

# 2. Inicializar los estados de la sesión (session_state) leyendo estado.json
init_session()

# 3. Renderizar la barra lateral y obtener la selección del usuario
selected_style, selected_view = render_sidebar(STYLES, VIEWS)

# 4. Inyectar el CSS del tema seleccionado de forma dinámica
style = STYLES[selected_style]
inject_css(**style)

# 5. Botones de control de persistencia exacta de Claude en el Sidebar
with st.sidebar:
    st.markdown("---")
    if st.button("💾 Guardar sesión"):
        ok = guardar_estado_local()
        st.toast("✅ Estado guardado." if ok else "❌ Error al guardar.")

    if st.button("🗑 Resetear sesión"):
        resetear_estado_local()
        st.rerun()

# 6. Renderizado de la vista activa mediante el Registro Centralizado
view_fn = VIEWS_REGISTRY.get(selected_view)
if view_fn:
    view_fn()
else:
    st.error(f"Vista '{selected_view}' no registrada en VIEWS_REGISTRY.")