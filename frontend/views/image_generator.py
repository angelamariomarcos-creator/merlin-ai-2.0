# frontend/views/image_generator.py
import time
import json
import os
import hashlib
from pathlib import Path
import httpx
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPTS = _ROOT / "backend" / "core" / "prompts"

DEMO_KEYWORD_MAP = {
    "playa": "beach", "mar": "ocean", "montaña": "mountain",
    "bosque": "forest", "rio": "river", "lago": "lake",
    "desierto": "desert", "nieve": "snow", "flor": "flowers",
    "naturaleza": "nature", "persona": "portrait", "mujer": "woman",
    "hombre": "man", "bebe": "baby", "niño": "child",
    "retrato": "portrait", "cara": "face", "rockero": "rock-music",
    "ciudad": "city", "edificio": "architecture", "calle": "street",
    "noche": "night", "futurista": "futuristic", "castillo": "castle",
    "perro": "dog", "gato": "cat", "caballo": "horse", "pajaro": "bird",
    "leon": "lion", "tigre": "tiger", "lobo": "wolf", "dragon": "dragon",
    "pantera": "panther", "comida": "food", "pizza": "pizza",
    "cafe": "coffee", "abstracto": "abstract", "arte": "art",
    "magia": "magic", "espacio": "space", "galaxia": "galaxy",
    "robot": "robot", "anime": "anime", "guerra": "war",
    "barco": "ship", "coche": "car", "moto": "motorcycle",
    "avion": "airplane", "cohete": "rocket", "underwater": "underwater",
    "fuego": "fire", "agua": "water", "tierra": "earth",
}


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


def _generate_demo(prompt: str) -> dict:
    time.sleep(1)
    prompt_lower = prompt.lower()
    keyword = next(
        (en for es, en in DEMO_KEYWORD_MAP.items() if es in prompt_lower),
        None
    )
    seed = hashlib.md5(prompt.encode()).hexdigest()[:8]
    url = f"https://picsum.photos/seed/{keyword or seed}/1024/576"
    return {"url": url, "seed": seed}


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


def render() -> None:
    demo_mode = _is_demo_mode()

    st.subheader("🎨 Generador de Imagenes · FLUX Dev")

    if demo_mode:
        st.warning("🧪 **MODO DEMO** — Imágenes temáticas según tu prompt. Cambia `DEMO_MODE=false` para generar con FLUX real.")

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
    c3.slider("Inference steps", 1, 50, value=28, step=1,        key="flux_steps")
    c4.slider("Guidance scale",  1.0, 7.0, value=3.5, step=0.1,  key="guidance_scale")

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

        spinner_msg = "🧪 Buscando imagen temática..." if demo_mode else "🔮 Generando con FLUX Dev..."

        with st.spinner(spinner_msg):
            try:
                if demo_mode:
                    result = _generate_demo(_prompt)
                else:
                    result = _generate_real(
                        prompt=enriched,
                        steps=st.session_state.get("flux_steps", 28),
                        guidance=st.session_state.get("guidance_scale", 3.5),
                    )

                url = result["url"]
                caption = f"[DEMO] tema detectado · Seed: {result.get('seed', '—')}" if demo_mode else f"Seed: {result.get('seed', '—')}"
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
                st.toast("🧪 Demo guardado" if demo_mode else "✅ Imagen guardada", icon="🖼️")

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
                st.caption(record.get("timestamp", "—"))
                if record.get("is_demo"):
                    st.caption("🧪 Demo")