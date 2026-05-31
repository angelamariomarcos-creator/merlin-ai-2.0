# frontend/core/session.py

import streamlit as st
from core.persistence import cargar_estado_local

_SESSION_INITIALIZED_KEY = "_merlin_session_ready"

def init_session() -> None:
    """
    Ejecutar UNA sola vez por sesión de navegador.
    Carga el estado persistido y luego inicializa
    las claves volátiles que no se persisten.
    """
    if st.session_state.get(_SESSION_INITIALIZED_KEY):
        return

    # 1. Restaurar galería y umbrales desde estado.json
    cargar_estado_local()

    # 2. Claves volátiles (no persisten, se resetean con cada sesión)
    st.session_state.setdefault("panic_ideas", [])
    st.session_state.setdefault("selected_panic_prompt", "")

    st.session_state[_SESSION_INITIALIZED_KEY] = True