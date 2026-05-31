# frontend/core/registry.py (o la ruta donde tengas guardado este diccionario)
import streamlit as st

# Imports absolutos limpios desde la raíz para Streamlit Cloud
from frontend.views import (
    dashboard, image_generator, video_gateway,
    upscaler, market_intel, linkedin_writer,
    thresholds, infra_monitor, billing, history,
    agents_manager, pixar_gallery, prompt_optimizer,
    logs, settings,
)

VIEWS_REGISTRY = {
    "🛸 Dashboard General":                   dashboard.render,
    "🎨 Generador de Imágenes (Flux)":        image_generator.render,
    "🎬 Pasarela de Video AI":                video_gateway.render,
    "🔍 Reescalado 4K Nativo (FAL.AI)":       upscaler.render,
    "📈 Inteligencia de Mercado (Perplexity)": market_intel.render,
    "✍️ Redactor LinkedIn (Claude)":           linkedin_writer.render,
    "⚙️ Configuración de Umbrales":            thresholds.render,
    "🛡️ Monitor de Infraestructura":           infra_monitor.render,
    "💰 Control de Costes y Márgenes":        billing.render,
    "📂 Historial de Generaciones":            history.render,
    "🤖 Gestión de Agentes Orquestadores":      agents_manager.render,
    "🎭 Galería de Estilos Pixar":              pixar_gallery.render,
    "⚡ Optimización de Prompts":              prompt_optimizer.render,
    "📬 Logs del Sistema en Vivo":              logs.render,
    "🔮 Configuración de Merlín AI":           settings.render,
}

def dispatch(selected_view: str) -> None:
    render_fn = VIEWS_REGISTRY.get(selected_view)
    if render_fn:
        render_fn()
    else:
        st.error(f"Vista '{selected_view}' no registrada.")