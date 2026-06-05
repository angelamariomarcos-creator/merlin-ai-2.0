# frontend/views/settings.py
import streamlit as st
import os


def render() -> None:
    st.subheader("⚙️ Configuración de Merlín AI")
    st.divider()

    tab_gen, tab_apis, tab_about = st.tabs(["🎛️ Generación", "🔑 APIs", "ℹ️ Acerca de"])

    # ── Tab Generación ────────────────────────────────────
    with tab_gen:
        st.subheader("Parámetros por defecto")

        st.slider(
            "Inference steps FLUX (calidad vs velocidad)",
            1, 50, step=1,
            key="flux_steps",
            help="Más steps = mejor calidad pero más lento. Recomendado: 28"
        )
        st.slider(
            "Guidance scale FLUX",
            1.0, 7.0, step=0.1,
            key="guidance_scale",
            help="Controla cuánto sigue el modelo el prompt. Recomendado: 3.5"
        )

        st.divider()
        st.subheader("Galería")

        max_galeria = st.number_input(
            "Máximo de items en galería",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            key="max_galeria",
        )

        if st.button("🗑️ Limpiar toda la galería", type="secondary"):
            st.session_state.galeria = []
            st.session_state.videos = []
            st.success("✅ Galería limpiada.")

    # ── Tab APIs ──────────────────────────────────────────
    with tab_apis:
        st.subheader("Estado de las APIs configuradas")

        apis = {
            "FAL_KEY": "FAL.AI (imágenes, video, upscaling)",
            "GROQ_API_KEY": "Groq (LinkedIn, análisis de mercado)",
            "GEMINI_API_KEY": "Google Gemini",
            "GITHUB_TOKEN": "GitHub (persistencia)",
        }

        for key, desc in apis.items():
            val = os.environ.get(key, "")
            if val:
                st.success(f"✅ **{key}** — {desc}")
            else:
                st.error(f"❌ **{key}** — {desc} — No configurada")

        st.divider()
        st.info("Las API keys se configuran en Streamlit Cloud → Settings → Secrets")
        st.markdown("[🔗 Ir a Streamlit Cloud Secrets](https://share.streamlit.io)")

    # ── Tab About ─────────────────────────────────────────
    with tab_about:
        st.subheader("Merlín AI 2.0")
        st.markdown("""
**Versión:** 2.0.0 · Fase 5

**Stack tecnológico:**
- 🎨 Generación de imágenes: FLUX Dev (FAL.AI)
- 🎬 Animación de video: SeedAnce Lite (FAL.AI)  
- 🔍 Upscaling 4K: AuraSR (FAL.AI)
- 🤖 Análisis e IA: Groq Llama 3.3 70B
- 🦆 Búsqueda: DuckDuckGo API
- 🌐 Frontend: Streamlit
- ☁️ Deploy: Streamlit Community Cloud

**Creado por:** Javi García · Merlín AI
        """)
        st.divider()
        st.caption("Construido con determinación, café y muchos errores corregidos. 🔮")