# frontend/views/image_generator.py
import time
import os
import httpx
import streamlit as st


def _get_fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    if not key:
        st.error("FAL_KEY no encontrada en secrets.")
    return key


def _generate_image(prompt: str, steps: int, guidance: float) -> dict:
    key = _get_fal_key()
    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "num_inference_steps": steps,
        "guidance_scale": guidance,
        "image_size": "landscape_16_9",
        "num_images": 1,
        "enable_safety_checker": True,
    }

    # Submit a la queue
    with httpx.Client(timeout=30) as client:
        resp = client.post("https://queue.fal.run/fal-ai/flux/dev", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    request_id = data.get("request_id")
    if not request_id:
        raise ValueError(f"No request_id en respuesta: {data}")

    # Poll status
    status_url = f"https://queue.fal.run/fal-ai/flux/dev/requests/{request_id}/status"
    result_url = f"https://queue.fal.run/fal-ai/flux/dev/requests/{request_id}"

    for _ in range(60):
        time.sleep(3)
        with httpx.Client(timeout=30) as client:
            r = client.get(status_url, headers=headers)
            r.raise_for_status()
            status_data = r.json()

        status = status_data.get("status")
        if status == "COMPLETED":
            # Fetch result
            with httpx.Client(timeout=30) as client:
                res = client.get(result_url, headers=headers)
                res.raise_for_status()
                result = res.json()
            images = result.get("images", [])
            if images:
                return {"url": images[0]["url"], "seed": result.get("seed", 0)}
            raise ValueError("No images en resultado.")
        elif status in ("FAILED", "ERROR"):
            raise ValueError(f"FAL.AI error: {status_data}")

    raise TimeoutError("FAL.AI no respondio en tiempo.")


def render() -> None:
    st.subheader("🎨 Generador de Imagenes · FLUX Dev")

    st.text_area(
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

        with st.spinner("🔮 Generando con FLUX Dev..."):
            try:
                result = _generate_image(
                    prompt=_prompt,
                    steps=st.session_state.get("flux_steps", 28),
                    guidance=st.session_state.get("guidance_scale", 3.5),
                )
                url = result["url"]
                st.image(url, caption=f"Seed: {result.get('seed', '—')}", use_container_width=True)

                if "galeria" not in st.session_state:
                    st.session_state.galeria = []

                st.session_state.galeria.insert(0, {
                    "prompt": _prompt,
                    "url": url,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                })
                st.toast("✅ Imagen guardada en galería", icon="🖼️")

            except Exception as e:
                st.error(f"❌ Error generando imagen: {e}")