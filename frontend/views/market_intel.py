# frontend/views/market_intel.py
import time
import streamlit as st
from frontend.core.async_runner import run_with_spinner

def render() -> None:
    st.subheader("Inteligencia de Mercado · Perplexity + Claude")

    niche = st.text_input(
        "Nicho de mercado",
        placeholder="AI image generation for e-commerce",
    )

    if st.button("📈 Analizar tendencias"):
        if not niche.strip():
            st.warning("Escribe un nicho antes de analizar.")
            return

        result = run_with_spinner(
            fn=lambda: (time.sleep(4), {"trend_summary": "Demo trend"})[1],
            agent="market-intel",
        )

        if result.success and result.data:
            st.subheader("📊 Tendencia detectada")
            st.info(result.data.get("trend_summary", ""))