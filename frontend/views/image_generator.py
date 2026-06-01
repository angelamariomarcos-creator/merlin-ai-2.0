# frontend/views/image_generator.py
import streamlit as st
from components.panic_button import render_panic_button
from core.async_runner import run_with_spinner
from core.gallery import save_to_gallery
from core.prompt_loader import load_panic_pools

def render() -> None:
    st.subheader("Generador de Imágenes · FLUX Dev")

    # ── Botón de Pánico Creativo ──────────────────────────
    render_panic_button()
    st.divider()

    # ── Formulario de generación ──────────────────────────
    st.subheader("⚙️ Configurar generación")
    pools = load_panic_pools()
    
    camera_labels  = ["— Selecciona —"] + [
        c["name"] for c in _load_cameras_full()
    ]
    style_labels   = ["— Selecciona —"] + [
        s["name"] for s in _load_styles_full()
    ]

    prompt = st.text_area(
        "Prompt",
        value=st.session_state.get("selected_panic_prompt", ""),
        placeholder="Describe la imagen o usa el Botón de Pánico Creativo...",
        height=100,
        key="prompt_input",
    )

    c1, c2 = st.columns(2)
    c1.selectbox("Cámara",           camera_labels, key="sel_camera")
    c2.selectbox("Estilo artístico",  style_labels,  key="sel_style")

    c3, c4 = st.columns(2)
    c3.slider(
        "Inference steps", 1, 50, step=1,
        key="flux_inference_steps",
    )
    c4.slider(
        "Guidance scale", 1.0, 7.0, step=0.1,
        key="default_guidance_scale",
    )

    st.divider()

    col_gen, col_demo = st.columns([3, 1])

    # ── Generación real (agente conectado) ────────────────
    with col_gen:
        if st.button("🎨 Generar imagen", use_container_width=True):
            _prompt = st.session_state.get("prompt_input", "").strip()
            if not _prompt:
                st.warning("Escribe un prompt antes de generar.")
                return

            payload = {
                "session_id":          st.session_state.get("_session_id", "demo"),
                "prompt":              _prompt,                "image_size":          "landscape_16_9",
                "num_inference_steps": st.session_state.get("flux_inference_steps", 28),
                "guidance_scale":      st.session_state.get("default_guidance_scale", 3.5),
                "num_images":          1,
                "enable_safety_checker": True,
            }

            # ── Simulación hasta conexión real ────────────
            import time
            result = run_with_spinner(
                fn=lambda: (
                    time.sleep(3),
                    {
                        "url":    "https://picsum.photos/seed/merlin-ai-demo/512/512",
                        "seed":   42,
                        "width":  1024,
                        "height": 576,
                    }
                )[1],
                agent="image-generator",
            )

            # ── Cuando image_generator.py esté conectado: ─
            # from backend.agents.image_generator.image_generator import image_generator
            # result = run_with_spinner(
            #     fn=lambda: image_generator.generate_sync(payload),
            #     agent="image-generator",
            # )

            if result.success and result.data:
                st.image(
                    result.data["url"],
                    caption=f"Seed: {result.data.get('seed', '—')} · "
                            f"{result.data.get('width', '—')}×"
                            f"{result.data.get('height', '—')}px",
                    use_container_width=True,
                )
                
                record = save_to_gallery(
                    prompt=payload["prompt"],
                    style=st.session_state.get("sel_style", "Sin estilo"),
                    agent="image-generator",
                    url=result.data["url"],
                    is_demo=False,
                )
                if record:
                    st.toast(
                        f"✅ Guardado en galería · ID: {record.entry_id}",
                        icon="🖼️",
                    )

    # ── Guardado demo rápido ──────────────────────────────
    with col_demo:
        if st.button("💾 Demo", use_container_width=True, help="Guarda una entrada de demostración en la galería"):
            _prompt = st.session_state.get("prompt_input", "").strip()
            if not _prompt:
                st.warning("Escribe un prompt antes de guardar.")
                return

            record = save_to_gallery(
                prompt=_prompt,
                style=st.session_state.get("sel_style", "Sin estilo"),
                agent="demo",
                is_demo=True,
            )
            if record:
                st.toast(
                    f"✅ Demo guardado · {len(st.session_state.galeria)} items",
                    icon="💾",
                )

    # ── Vista previa de galería reciente ──────────────────
    galeria = st.session_state.get("galeria", [])
    if galeria:
        st.divider()
       st.subheader("🖼️ Últimas generaciones")
        recent = galeria[:3]
        cols   = st.columns(len(recent))
        for col, record in zip(cols, recent):
            with col:
                from core.gallery import render_gallery_image
                render_gallery_image(record)
                st.caption(
                    f"{record.get('entry_id', '—')} · "
                    f"{record.get('timestamp', '—')}"
                )

# ── Helpers locales ───────────────────────────────────────
import json
from pathlib import Path

_PROMPTS_DIR = Path("C:/merlin-ai-2.0/backend/core/prompts")

@st.cache_resource
def _load_cameras_full() -> list[dict]:
    try:
        with open(_PROMPTS_DIR / "cameras.json", encoding="utf-8") as f:
            return json.load(f).get("cameras", [])
    except Exception:
        return []

@st.cache_resource
def _load_styles_full() -> list[dict]:
    try:
        with open(_PROMPTS_DIR / "styles.json", encoding="utf-8") as f:
            return json.load(f).get("styles", [])
    except Exception:
        return []