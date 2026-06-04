# frontend/views/video_gateway.py
import time
import os
import httpx
import streamlit as st


def _upload_image_to_fal(image_bytes: bytes, filename: str) -> str:
    """Sube imagen a FAL.AI storage y devuelve la URL."""
    key = os.environ.get("FAL_KEY", "")
    headers = {"Authorization": f"Key {key}"}
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://rest.fal.run/storage/upload/initiate",
            headers=headers,
            json={"file_name": filename, "content_type": "image/jpeg"},
        )
        resp.raise_for_status()
        data = resp.json()

    upload_url = data["upload_url"]
    file_url = data["file_url"]

    with httpx.Client(timeout=60) as client:
        resp = client.put(
            upload_url,
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )
        resp.raise_for_status()

    return file_url


def _generate_video(image_url: str, prompt: str) -> str:
    key = os.environ.get("FAL_KEY", "")
    if not key:
        raise ValueError("FAL_KEY no configurada en secrets.")

    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://queue.fal.run/fal-ai/bytedance/seedance/v1/lite/image-to-video",
            json={
                "image_url": image_url,
                "prompt": prompt,
                "duration": "5",
                "resolution": "720p",
                "aspect_ratio": "16:9",
            },
            headers=headers,
        )
        resp.raise_for_status()
        submit_data = resp.json()

    response_url = submit_data.get("response_url")
    status_url = submit_data.get("status_url")

    if not response_url:
        raise ValueError(f"No response_url: {submit_data}")

    for _ in range(80):
        time.sleep(4)
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
            video_url = result.get("video", {}).get("url") or result.get("video_url", "")
            if video_url:
                return video_url
            raise ValueError(f"No video_url en resultado: {result}")
        elif status in ("FAILED", "ERROR"):
            raise ValueError(f"SeedAnce fallo: {status_data}")

    raise TimeoutError("SeedAnce no respondio en tiempo limite.")


def render() -> None:
    st.subheader("🎬 Pasarela de Video AI · SeedAnce Lite")
    st.caption("Anima una imagen en un clip de 5 segundos a 720p.")
    st.divider()

    image_url = ""

    # ── Opción 1: Galería ─────────────────────────────────
    galeria = st.session_state.get("galeria", [])
    if galeria:
        st.subheader("📷 Usar imagen de la galería")
        opciones = ["— Selecciona —"] + [
            f"{r.get('timestamp', '—')} · {r.get('prompt', '')[:40]}"
            for r in galeria
        ]
        sel = st.selectbox("Imagen base", opciones, key="video_sel_galeria")
        if sel != "— Selecciona —":
            idx = opciones.index(sel) - 1
            image_url = galeria[idx].get("url", "")
            if image_url:
                st.image(image_url, width=300)

    # ── Opción 2: Subir desde PC ──────────────────────────
    st.subheader("💻 Subir imagen desde tu PC")
    uploaded = st.file_uploader(
        "Selecciona una imagen (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
        key="video_upload",
    )
    if uploaded:
        st.image(uploaded, width=300)
        with st.spinner("Subiendo imagen..."):
            try:
                image_url = _upload_image_to_fal(uploaded.read(), uploaded.name)
                st.success("✅ Imagen subida correctamente.")
            except Exception as e:
                st.error(f"❌ Error subiendo imagen: {e}")

    # ── Opción 3: URL manual ──────────────────────────────
    st.subheader("🔗 O pega una URL de imagen")
    url_input = st.text_input("URL de imagen", placeholder="https://...", key="video_url_input")
    if url_input.strip():
        image_url = url_input.strip()
        st.image(image_url, width=300)

    # ── Prompt y generación ───────────────────────────────
    st.divider()
    prompt = st.text_area(
        "Prompt de movimiento",
        placeholder="Camera slowly zooms in, gentle wind moves the hair, cinematic...",
        height=80,
        key="video_prompt",
    )

    if st.button("🎬 Generar video", use_container_width=True):
        if not image_url:
            st.warning("Selecciona, sube o pega una imagen base.")
            return
        if not prompt.strip():
            st.warning("Escribe un prompt de movimiento.")
            return

        with st.spinner("🎬 Generando con SeedAnce... (1-2 min)"):
            try:
                video_url = _generate_video(image_url, prompt.strip())
                st.video(video_url)
                st.success("✅ Video generado.")
                st.markdown(f"[⬇️ Descargar video]({video_url})")

                if "videos" not in st.session_state:
                    st.session_state.videos = []
                st.session_state.videos.insert(0, {
                    "url": video_url,
                    "prompt": prompt.strip(),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                })
                st.toast("✅ Video guardado", icon="🎬")

            except Exception as e:
                st.error(f"❌ Error: {e}")

    # ── Historial ─────────────────────────────────────────
    videos = st.session_state.get("videos", [])
    if videos:
        st.divider()
        st.subheader("🎞️ Videos generados")
        for v in videos[:3]:
            with st.container(border=True):
                st.video(v["url"])
                st.caption(f"{v['timestamp']} · {v['prompt'][:60]}")