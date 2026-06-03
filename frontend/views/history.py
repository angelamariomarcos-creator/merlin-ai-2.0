# frontend/views/history.py
import streamlit as st
def render() -> None:
    st.subheader("📂 Historial de Generaciones")
    galeria = st.session_state.get("galeria", [])
    if not galeria:
        st.info("La galeria esta vacia.")
        return
    for record in galeria:
        with st.container(border=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                if record.get("url"):
                    st.image(record["url"], use_container_width=True)
            with col2:
                st.write(f"**Prompt:** {record.get('prompt', '')[:100]}")
                st.caption(record.get("timestamp", ""))