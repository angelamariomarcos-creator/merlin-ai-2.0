# frontend/core/registry.py
import streamlit as st
from frontend.views import (
    landing, dashboard, image_generator, video_gateway, upscaler,
    market_intel, linkedin_writer, billing, history, settings,
)

REGISTRY = {
    "🏠 Inicio":                  landing.render,
    "🛸 Dashboard":               dashboard.render,
    "🎨 Generador de Imagenes":   image_generator.render,
    "🎬 Video AI":                video_gateway.render,
    "🔍 Reescalado 4K":           upscaler.render,
    "📈 Inteligencia de Mercado": market_intel.render,
    "✍️ Redactor LinkedIn":        linkedin_writer.render,
    "💰 Control de Costes":       billing.render,
    "📂 Historial":               history.render,
    "⚙️ Configuracion":           settings.render,
}

def dispatch(view: str) -> None:
    fn = REGISTRY.get(view)
    if fn:
        fn()
    else:
        st.error(f"Vista no encontrada: {view}")