# frontend/views/market_intel.py
import time
import threading
import httpx
import streamlit as st
import os
import json


def _search_duckduckgo(query: str) -> list[dict]:
    """Búsqueda real via DuckDuckGo API — gratuita, sin key."""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
                headers={"User-Agent": "MerlinAI/2.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        # Abstract principal
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["Abstract"],
                "url": data.get("AbstractURL", ""),
            })
        # Resultados relacionados
        for r in data.get("RelatedTopics", [])[:5]:
            if isinstance(r, dict) and r.get("Text"):
                results.append({
                    "title": r.get("Text", "")[:60],
                    "snippet": r.get("Text", ""),
                    "url": r.get("FirstURL", ""),
                })
        return results
    except Exception as e:
        return [{"title": "Error", "snippet": str(e), "url": ""}]


def _analyze_with_claude(niche: str, search_results: list[dict]) -> str:
    """Analiza los resultados con Claude API."""
    try:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return "ANTHROPIC_API_KEY no configurada en secrets."

        context = "\n".join([
            f"- {r['title']}: {r['snippet']}"
            for r in search_results if r.get("snippet")
        ])

        prompt = f"""Eres un analista de mercado experto. Analiza el nicho "{niche}" basándote en esta información:

{context}

Proporciona un análisis conciso con:
1. **Tendencias principales** del sector
2. **Oportunidades** detectadas
3. **Competidores clave** mencionados
4. **Recomendación estratégica** para entrar o posicionarse en este nicho

Sé directo y práctico. Máximo 300 palabras."""

        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
    except Exception as e:
        return f"Error en análisis: {e}"


def _analyze_thread(niche: str, result_holder: list, error_holder: list) -> None:
    try:
        # 1. Búsqueda DuckDuckGo
        results = _search_duckduckgo(f"{niche} market trends 2025")
        if not results:
            error_holder.append("Sin resultados de búsqueda.")
            return

        # 2. Análisis con Claude
        analysis = _analyze_with_claude(niche, results)
        result_holder.append({
            "analysis": analysis,
            "sources": results,
        })
    except Exception as e:
        error_holder.append(str(e))


def render() -> None:
    st.subheader("📈 Inteligencia de Mercado")
    st.caption("Búsqueda real con DuckDuckGo · Análisis con Claude · Coste cero")
    st.divider()

    niche = st.text_input(
        "Nicho de mercado",
        placeholder="ej: generación de imágenes IA para e-commerce",
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
            "🔍 Buscando en DuckDuckGo...",
            "🧠 Claude analizando tendencias...",
            "📊 Estructurando informe...",
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

            with st.expander("🔗 Fuentes consultadas"):
                for s in data["sources"]:
                    if s.get("url"):
                        st.markdown(f"- [{s['title'][:60]}]({s['url']})")
                    else:
                        st.markdown(f"- {s['title'][:60]}")