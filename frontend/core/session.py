# frontend/core/session.py

import streamlit as st
from frontend.core.persistence import cargar_estado_local

_SESSION_INITIALIZED_KEY = "_merlin_session_ready"


def init_session() -> None:
    if st.session_state.get(_SESSION_INITIALIZED_KEY):
        return

    cargar_estado_local()

    st.session_state.setdefault("panic_ideas", [])
    st.session_state.setdefault("selected_panic_prompt", "")
    st.session_state.setdefault("_session_id", "merlin-session-001")

    st.session_state[_SESSION_INITIALIZED_KEY] = True