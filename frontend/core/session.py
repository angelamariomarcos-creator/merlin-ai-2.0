# frontend/core/session.py
import streamlit as st

def init_session() -> None:
    if st.session_state.get("_ready"):
        return

    # Cargar galería persistida de GitHub
    try:
        from frontend.core.persistence import cargar_galeria
        galeria = cargar_galeria()
        st.session_state["galeria"] = galeria
    except Exception:
        st.session_state.setdefault("galeria", [])

    st.session_state.setdefault("videos", [])
    st.session_state.setdefault("panic_ideas", [])
    st.session_state.setdefault("selected_panic_prompt", "")
    st.session_state.setdefault("flux_steps", 28)
    st.session_state.setdefault("guidance_scale", 3.5)
    st.session_state["_ready"] = True