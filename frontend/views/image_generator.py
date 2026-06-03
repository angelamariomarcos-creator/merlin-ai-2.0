# frontend/views/image_generator.py
import time
import streamlit as st

def render() -> None:
    st.subheader("🎨 Generador de Imagenes · FLUX Dev")

    prompt = st.text_area(
        "Prompt",
        value=st.session_state.get("selected_panic_prompt", ""),
        placeholder="Describe la imagen...",
        height=100,
        key="prompt_input",
    )

    c1, c2 = st.columns(2)
    c1.slider("Inference steps", 1, 50, step=1, key="flux_steps")
    c2.slider("Guidance scale", 1.0, 7.0, step=0.1, key="guidance_scale")

    if st.button("🎨 Generar imagen", use_container_width=True):
        _prompt = st.session_state.get("prompt_input", "").strip()
        if not _prompt:
            st.warning("Escribe un prompt antes de generar.")
            return

        with st.spinner("Generando imagen..."):
            time.sleep(2)
            url = "https://picsum.photos/seed/merlin/512/512"

        st.image(url, caption=f"Prompt: {_prompt[:60]}...", use_container_width=True)

        if "galeria" not in st.session_state:
            st.session_state.galeria = []

        st.session_state.galeria.insert(0, {
            "prompt": _prompt,
            "url": url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        })
        st.toast("✅ Imagen guardada en galería", icon="🖼️")