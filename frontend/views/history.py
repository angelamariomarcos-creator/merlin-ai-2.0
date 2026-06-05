# frontend/views/history.py
import streamlit as st


def render() -> None:
    st.subheader("📂 Historial de Generaciones")
    st.divider()

    tab_img, tab_vid = st.tabs(["🖼️ Imágenes", "🎬 Videos"])

    # ── Tab Imágenes ──────────────────────────────────────
    with tab_img:
        galeria = st.session_state.get("galeria", [])

        if not galeria:
            st.info("No hay imágenes generadas en esta sesión.")
        else:
            st.caption(f"{len(galeria)} imágenes en sesión.")

            if st.button("🗑️ Limpiar galería", key="clear_galeria"):
                st.session_state.galeria = []
                st.rerun()

            st.divider()

            cols_per_row = 3
            for i in range(0, len(galeria), cols_per_row):
                cols = st.columns(cols_per_row)
                for col, record in zip(cols, galeria[i:i + cols_per_row]):
                    with col:
                        url = record.get("url", "")
                        if url:
                            st.image(url, use_container_width=True)
                        with st.container(border=True):
                            st.caption(f"🕐 {record.get('timestamp', '—')}")
                            prompt = record.get("prompt", "")
                            st.write(f"{prompt[:60]}{'...' if len(prompt) > 60 else ''}")
                            style  = record.get("style", "")
                            camera = record.get("camera", "")
                            if style and style != "— Sin estilo —":
                                st.caption(f"🎨 {style}")
                            if camera and camera != "— Sin cámara —":
                                st.caption(f"📷 {camera}")
                            if url:
                                st.markdown(f"[⬇️ Descargar]({url})")

    # ── Tab Videos ────────────────────────────────────────
    with tab_vid:
        videos = st.session_state.get("videos", [])

        if not videos:
            st.info("No hay videos generados en esta sesión.")
        else:
            st.caption(f"{len(videos)} videos en sesión.")

            if st.button("🗑️ Limpiar videos", key="clear_videos"):
                st.session_state.videos = []
                st.rerun()

            st.divider()

            for v in videos:
                with st.container(border=True):
                    st.video(v["url"])
                    st.caption(f"🕐 {v.get('timestamp', '—')}")
                    st.write(v.get("prompt", "")[:80])
                    st.markdown(f"[⬇️ Descargar video]({v['url']})")