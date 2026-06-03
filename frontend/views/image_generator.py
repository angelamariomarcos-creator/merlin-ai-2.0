# frontend/views/image_generator.py
import time
import os
import httpx
import streamlit as st


def _generate_image(prompt: str, steps: int, guidance: float) -> dict:
    key = os.environ.get("FAL_KEY", "")
    if not key:
        raise ValueError("FAL_KEY no configurada en secrets.")

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

    # Submit
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://queue.fal.run/fal-ai/flux/dev",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        submit_data = resp.json()

    # FAL devuelve response_url y status_url en el submit
    response_url = submit_data.get("response_url")
    status_url = submit_data.get("status_url")

    if not response_url:
        raise ValueError(f"No response_url en submit: {submit_data}")

    # Poll usando status_url (GET) hasta COMPLETED
    for _ in range(60):
        time.sleep(3)
        with httpx.Client(timeout=30) as client:
            r = client.get(status_url, headers=headers)
            r.raise_for_status()
            status_data = r.json()

        status = status_data.get("status")
        if status == "COMPLETED":
            # Fetch resultado final con response_url (GET)
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
                st.error(f"❌ Error: {e}")