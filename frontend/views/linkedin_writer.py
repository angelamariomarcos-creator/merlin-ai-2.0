# frontend/views/linkedin_writer.py
import time
import threading
import httpx
import streamlit as st
import os


def _generate_post_groq(topic: str, tone: str, length: str) -> str:
    try:
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            return "❌ GROQ_API_KEY no configurada en Streamlit Secrets."

        tone_map = {
            "Profesional": "tono profesional y autoritativo",
            "Cercano": "tono cercano, humano y conversacional",
            "Inspiracional": "tono inspiracional y motivador",
            "Humorístico": "tono con humor inteligente e ironía",
        }
        length_map = {
            "Corto (150 palabras)": 150,
            "Medio (300 palabras)": 300,
            "Largo (500 palabras)": 500,
        }

        prompt = f"""Eres un experto en contenido de LinkedIn con miles de seguidores.
Escribe un post de LinkedIn sobre: "{topic}"

Requisitos:
- Tono: {tone_map.get(tone, 'profesional')}
- Longitud: aproximadamente {length_map.get(length, 300)} palabras
- Incluye un gancho potente en la primera línea
- Usa saltos de línea para facilitar la lectura
- Termina con una pregunta para fomentar comentarios
- Añade 5 hashtags relevantes al final
- Escribe en español
- NO uses asteriscos para negrita, usa mayúsculas si necesitas énfasis

El post debe ser auténtico y generar engagement real."""

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.8,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error: {e}"


def _generate_thread(topic: str, tone: str, length: str, result_holder: list, error_holder: list) -> None:
    try:
        post = _generate_post_groq(topic, tone, length)
        result_holder.append(post)
    except Exception as e:
        error_holder.append(str(e))


def render() -> None:
    st.subheader("✍️ Redactor LinkedIn · Groq Llama 3.3")
    st.caption("Posts profesionales optimizados para engagement · Coste cero")
    st.divider()

    # Recoge el prompt inyectado desde El Intérprete si existe
    topic_inyectado = st.session_state.pop("linkedin_topic", "")

    topic = st.text_area(
        "¿Sobre qué quieres escribir?",
        value=topic_inyectado,
        placeholder="ej: Cómo la IA está cambiando el comercio tradicional...",
        height=80,
        key="linkedin_topic",
    )

    if topic_inyectado:
        st.info("✨ Prompt optimizado por El Intérprete · Listo para generar")

    c1, c2 = st.columns(2)
    tone = c1.selectbox(
        "Tono",
        ["Profesional", "Cercano", "Inspiracional", "Humorístico"],
        key="linkedin_tone",
    )
    length = c2.selectbox(
        "Longitud",
        ["Corto (150 palabras)", "Medio (300 palabras)", "Largo (500 palabras)"],
        index=1,
        key="linkedin_length",
    )

    if st.button("✍️ Generar post", use_container_width=True):
        if not topic.strip():
            st.warning("Escribe un tema antes de generar.")
            return

        result_holder: list = []
        error_holder: list = []

        thread = threading.Thread(
            target=_generate_thread,
            args=(topic.strip(), tone, length, result_holder, error_holder),
            daemon=True,
        )
        thread.start()

        msgs = ["✍️ Redactando post...", "🧠 Optimizando engagement...", "📝 Añadiendo hashtags..."]
        placeholder = st.empty()
        i = 0
        while thread.is_alive():
            placeholder.info(msgs[i % len(msgs)])
            time.sleep(2)
            i += 1
        placeholder.empty()

        if error_holder:
            st.error(f"❌ Error: {error_holder[0]}")
        elif result_holder:
            post = result_holder[0]
            st.subheader("📝 Tu post de LinkedIn")
            st.text_area("Copia y pega en LinkedIn:", value=post, height=400, key="linkedin_result")
            st.success("✅ Post generado. Revísalo y personalízalo antes de publicar.")
            char_count = len(post)
            st.caption(f"📊 {char_count} caracteres · LinkedIn permite hasta 3000")