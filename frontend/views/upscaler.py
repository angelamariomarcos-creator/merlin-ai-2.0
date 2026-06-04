# frontend/views/upscaler.py
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


def _upscale_thread(image_url: str, result_holder: list, error_holder: list) -> None:
    try:
        key = os.environ.get("FAL_KEY", "")
        if not key:
            error_holder.append("FAL_KEY no configurada.")
            return

        headers = {
            "Authorization": f"Key {key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://queue.fal.run/fal-ai/aura-sr",
                json={"image_url": image_url},
                headers=headers,
            )
            resp.raise_for_status()
            submit_data = resp.json()

        response_url = submit_data.get("response_url")
        status_url = submit_data.get("status_url")

        if not response_url:
            error_holder.append(f"No response_url: {submit_data}")
            return

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
                url = result.get("image", {}).get("url") or result.get("output", {}).get("url", "")
                if url:
                    result_holder.append(url)
                    return
                error_holder.append(f"No url en resultado: {result}")
                return
            elif status in ("FAILED", "ERROR"):
                error_holder.append(f"AuraSR fallo: {status_data}")
                return

        error_holder.append("Timeout: AuraSR no respondio.")

    except Exception as e:
        error_holder.append(str(e))


def render() -> None:
    st.subheader("🔍 Reescalado 4K · AuraSR")
    st.caption("Aumenta la resolución de cualquier imagen 4x con IA. Sin pérdida de calidad.")
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
        sel = st.selectbox("Imagen base", opciones, key="upscale_sel_galeria")
        if sel != "— Selecciona —":
            idx = opciones.index(sel) - 1
            image_url = galeria[idx].get("url", "")
            if image_url:
                st.image(image_url, caption="Original", use_container_width=True)

    # ── Opción 2: Subir desde PC ──────────────────────────
    st.subheader("💻 Subir imagen desde tu PC")
    uploaded = st.file_uploader(
        "Selecciona una imagen (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
        key="upscale_upload",
    )
    if uploaded:
        st.image(uploaded, caption="Original", use_container_width=True)
        image_url = _to_data_url(uploaded.read(), uploaded.name)
        st.success("✅ Imagen lista.")

    # ── Opción 3: URL ─────────────────────────────────────
    st.subheader("🔗 O pega una URL")
    url_input = st.text_input("URL de imagen", placeholder="https://...", key="upscale_url_input")
    if url_input.strip():
        image_url = url_input.strip()
        st.image(image_url, caption="Original", use_container_width=True)

    st.divider()

    if st.button("🔍 Reescalar a 4K", use_container_width=True):
        if not image_url:
            st.warning("Selecciona, sube o pega una imagen.")
            return

        result_holder: list = []
        error_holder: list = []

        thread = threading.Thread(
            target=_upscale_thread,
            args=(image_url, result_holder, error_holder),
            daemon=True,
        )
        thread.start()

        progress_msgs = [
            "🔍 Analizando imagen...",
            "⬆️ Aumentando resolución 4x...",
            "✨ Mejorando detalles...",
            "🎯 Finalizando...",
        ]
        placeholder = st.empty()
        i = 0
        while thread.is_alive():
            placeholder.info(progress_msgs[i % len(progress_msgs)])
            time.sleep(3)
            i += 1
        placeholder.empty()

        if error_holder:
            st.error(f"❌ Error: {error_holder[0]}")
        elif result_holder:
            upscaled_url = result_holder[0]
            st.image(upscaled_url, caption="✅ Imagen 4K", use_container_width=True)
            st.success("✅ Reescalado completado.")
            st.markdown(f"[⬇️ Descargar imagen 4K]({upscaled_url})")
            st.toast("✅ Imagen reescalada a 4K", icon="🔍")