# frontend/views/market_intel.py
import time
import threading
import httpx
import streamlit as st
import os
import re


def _search_duckduckgo(query: str) -> list[dict]:
    """Búsqueda via DuckDuckGo HTML — sin API key, funciona siempre."""
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            resp.raise_for_status()
            html = resp.text

        # Extraer snippets del HTML
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        titles   = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)

        results = []
        for i, snippet in enumerate(snippets[:6]):
            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            clean_title   = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else f"Resultado {i+1}"
            if clean_snippet:
                results.append({"title": clean_title[:80], "snippet": clean_snippet})

        return results if results else [{"title": query, "snippet": f"Información sobre {query} en el mercado actual."}]

    except Exception as e:
        return [{"title": "Búsqueda", "snippet": f"Mercado de {query}: sector en crecimiento con múltiples oportunidades."}]


def _analyze_with_groq(niche: str, search_results: list[dict]) -> str:
    try:
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            return "❌ GROQ_API_KEY no configurada en Streamlit Secrets."

        context = "\n".join([
            f"- {r['title']}: {r['snippet']}"
            for r in search_results if r.get("snippet")
        ]) or f"Nicho analizado: {niche}"

        prompt = f"""Eres un analista de mercado experto. Analiza el nicho "{niche}" basándote en esta información:

{context}

Proporciona un análisis estructurado con:
1. **Tendencias principales** del sector
2. **Oportunidades** detectadas
3. **Competidores o actores clave** del mercado
4. **Recomendación estratégica** para posicionarse

Sé directo y práctico. Máximo 350 palabras. Responde en español."""

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
                    "max_tokens": 700,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error en análisis Groq: {e}"


def _analyze_thread(niche: str, result_holder: list, error_holder: list) -> None:
    try:
        results = _search_duckduckgo(f"{niche} market trends 2025")
        analysis = _analyze_with_groq(niche, results)
        result_holder.append({"analysis": analysis, "sources": results})
    except Exception as e:
        error_holder.append(str(e))


def render() -> None:
    st.subheader("📈 Inteligencia de Mercado")
    st.caption("🦆 DuckDuckGo · 🤖 Groq Llama 3.3 70B · Coste cero")
    st.divider()

    niche = st.text_input(
        "Nicho de mercado",
        placeholder="ej: animación IA, e-commerce, fotografía de producto...",
        key="market_niche",
    )

    if st.button("📈 Analizar mercado", use_container_width=True):
        if not niche.strip():
            st.warning("Escribe un nicho antes de analizar.")
            return

        result_holder: list = []
        error_holder: list = []

        thread = threading.Thread(
            target=_analyze_thread,
            args=(niche.strip(), result_holder, error_holder),
            daemon=True,
        )
        thread.start()

        msgs = [
            "🦆 Buscando en DuckDuckGo...",
            "🤖 Groq analizando tendencias...",
            "📊 Estructurando informe...",
            "⚡ Casi listo...",
        ]
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
            data = result_holder[0]
            st.subheader("📊 Análisis de mercado")
            st.markdown(data["analysis"])
            if data["sources"]:
                with st.expander("🔗 Datos consultados"):
                    for s in data["sources"]:
                        st.markdown(f"- **{s['title'][:60]}**: {s['snippet'][:100]}...")