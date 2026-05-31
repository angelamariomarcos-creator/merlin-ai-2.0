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
                # Renderizamos la imagen primero
                render_gallery_image(record)
                
                # Sustitución de div con clase gallery-card por contenedor nativo
                with st.container(border=True):
                    st.write(f"🆔 **ID:** {record['entry_id']}")
                    st.write(f"🎨 **Estilo:** {record['style']}")
                    st.write(f"🤖 **Agente:** {record['agent']}")
                    st.caption(f"🕐 {record['timestamp']}")
                    st.divider()
                    st.caption("📝 **Prompt:**")
                    st.write(f"{record['prompt'][:80]}{'...' if len(record['prompt']) > 80 else ''}")