# frontend/views/video_gateway.py
import time
import os
import httpx
import streamlit as st


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

    galeria = st.session_state.get("galeria", [])
    image_url = ""

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

    st.subheader("🔗 O pega una URL de imagen")
    url_input = st.text_input("URL de imagen", placeholder="https://...", key="video_url_input")
    if url_input.strip():
        image_url = url_input.strip()
        st.image(image_url, width=300)

    prompt = st.text_area(
        "Prompt de movimiento",
        placeholder="Camera slowly zooms in, gentle wind moves the hair, cinematic...",
        height=80,
        key="video_prompt",
    )

    if st.button("🎬 Generar video", use_container_width=True):
        if not image_url:
            st.warning("Selecciona o pega una imagen base.")
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

    videos = st.session_state.get("videos", [])
    if videos:
        st.divider()
        st.subheader("🎞️ Videos generados")
        for v in videos[:3]:
            with st.container(border=True):
                st.video(v["url"])
                st.caption(f"{v['timestamp']} · {v['prompt'][:60]}")