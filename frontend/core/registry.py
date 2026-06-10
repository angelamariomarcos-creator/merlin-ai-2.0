# frontend/core/registry.py
import streamlit as st

REGISTRY_MAP = {
    "🏠 Inicio":                  ("frontend.views.landing",         "render"),
    "🛸 Dashboard":               ("frontend.views.dashboard",        "render"),
    "🎨 Generador de Imagenes":   ("frontend.views.image_generator",  "render"),
    "🧠 El Intérprete":           ("frontend.views.interprete",       "render"),
    "🎬 Video AI":                ("frontend.views.video_gateway",    "render"),
    "🔍 Reescalado 4K":           ("frontend.views.upscaler",         "render"),
    "📈 Inteligencia de Mercado": ("frontend.views.market_intel",     "render"),
    "✍️ Redactor LinkedIn":        ("frontend.views.linkedin_writer",  "render"),
    "💰 Control de Costes":       ("frontend.views.billing",          "render"),
    "📂 Historial":               ("frontend.views.history",          "render"),
    "⚙️ Configuracion":           ("frontend.views.settings",         "render"),
}

def dispatch(view: str) -> None:
    entry = REGISTRY_MAP.get(view)
    if not entry:
        st.error(f"Vista no encontrada: {view}")
        return
    module_path, fn_name = entry
    try:
        import importlib
        mod = importlib.import_module(module_path)
        fn  = getattr(mod, fn_name)
        fn()
    except Exception as e:
        st.error(f"Error cargando vista '{view}': {e}")