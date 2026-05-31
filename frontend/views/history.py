# frontend/views/history.py
import streamlit as st
from core.gallery import render_gallery_image, clear_gallery, get_gallery_count

def render() -> None:
    st.subheader("📂 Historial de Generaciones")
    
    galeria = st.session_state.get("galeria", [])
    
    if not galeria:
        st.info("La galería está vacía.")
        return
        
    st.caption(f"{get_gallery_count()} generaciones en sesión.")
    
    if st.button("🗑 Limpiar galería"):
        clear_gallery()
        st.rerun()
        
    st.divider()
    
    cols_per_row = 3
    for i in range(0, len(galeria), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, record in zip(cols, galeria[i:i + cols_per_row]):
            with col:
                render_gallery_image(record)
                st.markdown(
                    f'<div class="gallery-card">'
                    f'<b>🆔</b> {record["entry_id"]}<br>'
                    f'<b>🎨</b> {record["style"]}<br>'
                    f'<b>🤖</b> {record["agent"]}<br>'
                    f'<b>🕐</b> {record["timestamp"]}<br>'
                    f'<b>📝</b> {record["prompt"][:80]}'
                    f'{"..." if len(record["prompt"]) > 80 else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )