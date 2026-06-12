# frontend/views/video_gateway.py
import time
import os
import base64
import threading
import httpx
import streamlit as st


def _to_data_url(image_bytes: bytes, filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _generate_video_thread(image_url: str, prompt: str, result_holder: list, error_holder: list) -> None:
    try:
        key = os.environ.get("FAL_KEY", "")
        headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://queue.fal.run/fal-ai/bytedance/seedance/v1/lite/image-to-video",
                json={"image_url": image_url, "prompt": prompt, "duration": "5", "resolution": "720p", "aspect_ratio": "auto"},
                headers=headers,
            )
            resp.raise_for_status()
            submit_data = resp.json()

        response_url = submit_data.get("response_url")
        status_url = submit_data.get("status_url")
        if not response_url:
            error_holder.append(f"No response_url: {submit_data}")
            return

        for _ in range(120):
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
                    result_holder.append(video_url)
                    return
                error_holder.append(f"No video_url: {result}")
                return
            elif status in ("FAILED", "ERROR"):
                error_holder.append(f"SeedAnce fallo: {status_data}")
                return
        error_holder.append("Timeout: SeedAnce no respondio en 8 minutos.")
    except Exception as e:
        error_holder.append(str(e))


def render() -> None:
    st.subheader("Pasarela de Video AI · SeedAnce Lite")

    is_premium = st.session_state.get("is_premium", False)

    if not is_premium:
        st.divider()
        with st.container(border=True):
            st.markdown("### Función Premium")
            st.write("La generación de video está disponible para usuarios **Premium**.")
            st.divider()
            col1, col2 = st.columns(2)
            col1.metric("Precio", "$9.99/mes")
            col2.metric("Videos incluidos", "30/mes")
            st.markdown("""
**El plan Premium incluye:**
- Videos ilimitados hasta 30/mes
- Imágenes ilimitadas
- Reescalado 4K ilimitado
- Acceso prioritario a nuevos modelos
- Sin marca de agua
            """)
            st.info("Integración con Stripe próximamente. Contacta para acceso anticipado.")
            if os.environ.get("DEMO_MODE", "false").lower() == "true":
                if st.button("Activar modo demo (testing)"):
                    st.session_state.is_premium = True
                    st.rerun()
        return

    st.caption("Anima una imagen en un clip de 5 segundos a 720p.")
    st.divider()

    image_url = ""

    galeria = st.session_state.get("galeria", [])
    if galeria:
        st.subheader("Usar imagen de la galería")
        opciones = ["— Selecciona —"] + [f"{r.get('timestamp', '—')} · {r.get('prompt', '')[:40]}" for r in galeria]
        sel = st.selectbox("Imagen base", opciones, key="video_sel_galeria")
        if sel != "— Selecciona —":
            idx = opciones.index(sel) - 1
            image_url = galeria[idx].get("url", "")
            if image_url:
                st.image(image_url, width=300)

    st.subheader("Subir imagen desde tu PC")
    uploaded = st.file_uploader("Selecciona una imagen (JPG, PNG, WEBP)", type=["jpg", "jpeg", "png", "webp"], key="video_upload")
    if uploaded:
        st.image(uploaded, width=300)
        image_url = _to_data_url(uploaded.read(), uploaded.name)
        st.success("Imagen lista.")

    st.subheader("O pega una URL de imagen")
    url_input = st.text_input("URL de imagen", placeholder="https://...", key="video_url_input")
    if url_input.strip():
        image_url = url_input.strip()
        st.image(image_url, width=300)

    st.divider()

    prompt_inyectado = st.session_state.pop("video_prompt_inject", "")

    col_prompt, col_btn = st.columns([3, 1])
    with col_prompt:
        st.markdown("**Prompt de movimiento**")
    with col_btn:
        if st.button("Optimizar con El Intérprete", use_container_width=True, help="Mejora tu prompt con RCTC"):
            prompt_actual = st.session_state.get("video_prompt", "")
            st.session_state["interprete_input"] = prompt_actual
            st.session_state["interprete_tipo"] = "Video AI"
            st.session_state["vista"] = "El Intérprete"
            st.rerun()

    prompt = st.text_area(
        "Prompt de movimiento",
        value=prompt_inyectado,
        placeholder="Camera slowly zooms in, gentle wind moves the hair, cinematic...",
        height=80,
        key="video_prompt",
    )

    if prompt_inyectado:
        st.info("Prompt optimizado por El Intérprete · Listo para generar")

    if st.button("Generar video", use_container_width=True):
        if not image_url:
            st.warning("Selecciona, sube o pega una imagen base.")
            return
        if not prompt.strip():
            st.warning("Escribe un prompt de movimiento.")
            return

        result_holder: list = []
        error_holder: list = []
        thread = threading.Thread(target=_generate_video_thread, args=(image_url, prompt.strip(), result_holder, error_holder), daemon=True)
        thread.start()

        msgs = ["Enviando a SeedAnce...", "Analizando imagen...", "Generando movimiento...", "Renderizando frames...", "Casi listo..."]
        placeholder = st.empty()
        i = 0
        while thread.is_alive():
            placeholder.info(msgs[i % len(msgs)])
            time.sleep(5)
            i += 1
        placeholder.empty()

        if error_holder:
            st.error(f"Error: {error_holder[0]}")
        elif result_holder:
            video_url = result_holder[0]
            st.video(video_url)
            st.success("Video generado.")
            st.markdown(f"[Descargar video]({video_url})")
            if "videos" not in st.session_state:
                st.session_state.videos = []
            st.session_state.videos.insert(0, {"url": video_url, "prompt": prompt.strip(), "timestamp": time.strftime("%Y-%m-%d %H:%M")})
            st.toast("Video guardado")

    videos = st.session_state.get("videos", [])
    if videos:
        st.divider()
        st.subheader("Videos generados")
        for v in videos[:3]:
            with st.container(border=True):
                st.video(v["url"])
                st.caption(f"{v['timestamp']} · {v['prompt'][:60]}")