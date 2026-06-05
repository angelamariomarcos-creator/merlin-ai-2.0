# frontend/views/image_generator.py
import time
import json
import os
from pathlib import Path
import httpx
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPTS = _ROOT / "backend" / "core" / "prompts"

# Imágenes demo variadas — sin coste
DEMO_IMAGES = [
    "https://picsum.photos/seed/merlin1/1024/576",
    "https://picsum.photos/seed/merlin2/1024/576",
    "https://picsum.photos/seed/merlin3/1024/576",
    "https://picsum.photos/seed/merlin4/1024/576",
    "https://picsum.photos/seed/merlin5/1024/576",
    "https://picsum.photos/seed/merlin6/1024/576",
    "https://picsum.photos/seed/merlin7/1024/576",
    "https://picsum.photos/seed/merlin8/1024/576",
]


@st.cache_resource
def _load_cameras() -> list[dict]:
    try:
        with open(_PROMPTS / "cameras.json", encoding="utf-8") as f:
            return json.load(f).get("cameras", [])
    except Exception:
        return []


@st.cache_resource
def _load_styles() -> list[dict]:
    try:
        with open(_PROMPTS / "styles.json", encoding="utf-8") as f:
            return json.load(f).get("styles", [])
    except Exception:
        return []


def _is_demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "false").lower() == "true"


def _generate_real(prompt: str, steps: int, guidance: float) -> dict:
    key = os.environ.get("FAL_KEY", "")
    if not key:
        raise ValueError("FAL_KEY no configurada en secrets.")

    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://queue.fal.run/fal-ai/flux/dev",
            json={
                "prompt": prompt,
                "num_inference_steps": steps,
                "guidance_scale": guidance,
                "image_size": "landscape_16_9",
                "num_images": 1,
                "enable_safety_checker": True,
            },
            headers=headers,
        )
        resp.raise_for_status()
        submit_data = resp.json()

    response_url = submit_data.get("response_url")
    status_url = submit_data.get("status_url")

    if not response_url:
        raise ValueError(f"No response_url: {submit_data}")

    for _ in range(60):
        time.sleep(3)
        with httpx.Client(timeout=30) as client:
            r = client.get(status_url, headers=headers)
            r.raise_for_status()
            status_data = r.json()

        status = status_data.get("status")
        if status == "COMPLETED":
            with httpx.Client(timeout=30) as client:
                res = client.get(response_url, headers=headers)
                res.raise_for_status()
                result = res.json()
            images = result.get("images", [])
            if images:
                return {"url": images[0]["url"], "seed": result.get("seed", 0)}
            raise ValueError("No images en resultado.")
        elif status in ("FAILED", "ERROR"):
            raise ValueError(f"FAL.AI fallo: {status_data}")

    raise TimeoutError("FAL.AI no respondio en tiempo limite.")


def _generate_demo(prompt: str) -> dict:
    """Simula generación sin coste — para testing."""
    time.sleep(2)
    import hashlib
    idx = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % len(DEMO_IMAGES)
    return {"url": DEMO_IMAGES[idx], "seed": 42}


def render() -> None:
    demo_mode = _is_demo_mode()

    st.subheader("🎨 Generador de Imagenes · FLUX Dev")

    if demo_mode:
        st.warning("🧪 **MODO DEMO** — Las imágenes son placeholders. Cambia `DEMO_MODE=false` en Secrets para generar con FLUX real.")

    cameras = _load_cameras()
    styles  = _load_styles()

    camera_options = ["— Sin cámara —"] + [c["label_es"] for c in cameras]
    style_options  = ["— Sin estilo —"]  + [s["label_es"] for s in styles]

    st.text_area(
        "Prompt",
        value=st.session_state.get("selected_panic_prompt", ""),
        placeholder="Describe la imagen...",
        height=100,
        key="prompt_input",
    )

    c1, c2 = st.columns(2)
    sel_camera = c1.selectbox("📷 Cámara", camera_options, key="sel_camera")
    sel_style  = c2.selectbox("🎨 Estilo", style_options,  key="sel_style")

    c3, c4 = st.columns(2)
    c3.slider("Inference steps", 1, 50, value=28, step=1,       key="flux_steps")
    c4.slider("Guidance scale",  1.0, 7.0, value=3.5, step=0.1, key="guidance_scale")

    btn_label = "🧪 Generar imagen (DEMO)" if demo_mode else "🎨 Generar imagen"

    if st.button(btn_label, use_container_width=True):
        _prompt = st.session_state.get("prompt_input", "").strip()
        if not _prompt:
            st.warning("Escribe un prompt antes de generar.")
            return

        enriched = _prompt
        if sel_camera != "— Sin cámara —":
            cam = next((c for c in cameras if c["label_es"] == sel_camera), None)
            if cam:
                enriched += f", {cam['prompt_fragment']}"
        if sel_style != "— Sin estilo —":
            sty = next((s for s in styles if s["label_es"] == sel_style), None)
            if sty:
                enriched += f", {sty['prompt_fragment']}"

        spinner_msg = "🧪 Modo demo — generando placeholder..." if demo_mode else "🔮 Generando con FLUX Dev..."

        with st.spinner(spinner_msg):
            try:
                if demo_mode:
                    result = _generate_demo(enriched)
                else:
                    result = _generate_real(
                        prompt=enriched,
                        steps=st.session_state.get("flux_steps", 28),
                        guidance=st.session_state.get("guidance_scale", 3.5),
                    )

                url = result["url"]
                caption = f"[DEMO] Seed: {result.get('seed', '—')}" if demo_mode else f"Seed: {result.get('seed', '—')}"
                st.image(url, caption=caption, use_container_width=True)

                if "galeria" not in st.session_state:
                    st.session_state.galeria = []

                st.session_state.galeria.insert(0, {
                    "prompt": _prompt,
                    "url": url,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                    "style": sel_style,
                    "camera": sel_camera,
                    "is_demo": demo_mode,
                })
                st.toast("🧪 Demo guardado" if demo_mode else "✅ Imagen guardada en galería", icon="🖼️")

            except Exception as e:
                st.error(f"❌ Error: {e}")

    galeria = st.session_state.get("galeria", [])
    if galeria:
        st.divider()
        st.subheader("🖼️ Últimas generaciones")
        recent = galeria[:3]
        cols = st.columns(len(recent))
        for col, record in zip(cols, recent):
            with col:
                if record.get("url"):
                    st.image(record["url"], use_container_width=True)
                st.caption(f"{record.get('timestamp', '—')}")
                if record.get("is_demo"):
                    st.caption("🧪 Demo")