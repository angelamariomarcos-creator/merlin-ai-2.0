# frontend/views/dashboard.py
import os
import time
import streamlit as st


def render() -> None:

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Raleway:wght@300;400;600&display=swap');

    .dash-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(160deg, #1A0F2E, #12122B);
        border: 1px solid #7B5EA733;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .metric-card::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #C084FC, transparent);
    }
    .metric-val {
        font-family: 'Cinzel', serif;
        font-size: 2rem;
        font-weight: 900;
        color: #C084FC;
        line-height: 1;
        display: block;
    }
    .metric-label {
        font-family: 'Raleway', sans-serif;
        font-size: 0.72rem;
        color: #8A7AA0;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 0.35rem;
        display: block;
    }
    .section-title {
        font-family: 'Cinzel', serif;
        font-size: 0.75rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #7B5EA7;
        margin: 1.5rem 0 0.6rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #7B5EA722;
    }
    .module-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 0.6rem;
        margin-bottom: 1rem;
    }
    .module-btn {
        background: #12122B;
        border: 1px solid #7B5EA733;
        border-radius: 10px;
        padding: 0.9rem 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
        text-align: left;
    }
    .module-btn:hover {
        border-color: #C084FC;
        background: #1A0F2E;
    }
    .module-icon { font-size: 1.4rem; display: block; margin-bottom: 0.3rem; }
    .module-name {
        font-family: 'Raleway', sans-serif;
        font-size: 0.82rem;
        font-weight: 600;
        color: #E8E8FF;
        display: block;
    }
    .module-desc {
        font-family: 'Raleway', sans-serif;
        font-size: 0.73rem;
        color: #8A7AA0;
        margin-top: 0.15rem;
        display: block;
    }
    .api-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.55rem 0.8rem;
        border-radius: 8px;
        background: #12122B;
        border: 1px solid #7B5EA722;
        margin-bottom: 0.4rem;
        font-family: 'Raleway', sans-serif;
        font-size: 0.82rem;
    }
    .api-dot-ok  { width: 8px; height: 8px; border-radius: 50%; background: #4ADE80; flex-shrink: 0; }
    .api-dot-err { width: 8px; height: 8px; border-radius: 50%; background: #F87171; flex-shrink: 0; }
    .api-name  { color: #E8E8FF; font-weight: 600; flex: 1; }
    .api-label { color: #8A7AA0; font-size: 0.73rem; }
    .gallery-strip {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    .gallery-thumb {
        aspect-ratio: 1;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #7B5EA733;
    }
    .gallery-thumb img {
        width: 100%; height: 100%; object-fit: cover;
        display: block;
    }
    .empty-state {
        text-align: center;
        padding: 1.5rem;
        color: #8A7AA0;
        font-family: 'Raleway', sans-serif;
        font-size: 0.85rem;
        border: 1px dashed #7B5EA733;
        border-radius: 10px;
    }
    .welcome-bar {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        background: linear-gradient(135deg, #1A0F2E, #12122B);
        border: 1px solid #7B5EA744;
        border-radius: 14px;
        margin-bottom: 1.5rem;
    }
    .welcome-emoji { font-size: 2rem; }
    .welcome-name {
        font-family: 'Cinzel', serif;
        font-size: 1.1rem;
        color: #C084FC;
        font-weight: 700;
    }
    .welcome-sub {
        font-family: 'Raleway', sans-serif;
        font-size: 0.8rem;
        color: #8A7AA0;
        margin-top: 0.1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── BIENVENIDA ──────────────────────────────────────────────
    user_name = st.session_state.get("user_name", "Mago")
    hora = int(time.strftime("%H"))
    saludo = "Buenos días" if hora < 13 else "Buenas tardes" if hora < 20 else "Buenas noches"

    st.markdown(f"""
    <div class="welcome-bar">
        <div class="welcome-emoji">🔮</div>
        <div>
            <div class="welcome-name">{saludo}, {user_name}</div>
            <div class="welcome-sub">Tu cuartel general de IA generativa · Merlín AI 2.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MÉTRICAS ─────────────────────────────────────────────────
    galeria = st.session_state.get("galeria", [])
    videos  = st.session_state.get("videos",  [])
    is_premium = st.session_state.get("is_premium", False)
    plan_label = "⭐ Premium" if is_premium else "🆓 Free"

    st.markdown(f"""
    <div class="dash-grid">
        <div class="metric-card">
            <span class="metric-val">{len(galeria)}</span>
            <span class="metric-label">Imágenes creadas</span>
        </div>
        <div class="metric-card">
            <span class="metric-val">{len(videos)}</span>
            <span class="metric-label">Videos generados</span>
        </div>
        <div class="metric-card">
            <span class="metric-val">4K</span>
            <span class="metric-label">Resolución máx.</span>
        </div>
        <div class="metric-card">
            <span class="metric-val">{plan_label}</span>
            <span class="metric-label">Tu plan</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ACCESO RÁPIDO ────────────────────────────────────────────
    st.markdown('<div class="section-title">Acceso rápido</div>', unsafe_allow_html=True)

    modulos = [
        ("🎨", "Generador",     "Crea imágenes con FLUX",         "🎨 Generador de Imagenes"),
        ("🎬", "Video AI",      "Anima tus imágenes",             "🎬 Video AI"),
        ("🔍", "Reescalado 4K", "Sube la resolución con AuraSR",  "🔍 Reescalado 4K"),
        ("📈", "Mercado",       "Analiza tendencias con IA",       "📈 Inteligencia de Mercado"),
        ("✍️", "LinkedIn",      "Posts con Llama 3.3",            "✍️ Redactor LinkedIn"),
        ("💰", "Costes",        "Monitoriza tu gasto en APIs",    "💰 Control de Costes"),
    ]

    cols = st.columns(3)
    for i, (icon, nombre, desc, vista_key) in enumerate(modulos):
        with cols[i % 3]:
            if st.button(f"{icon} {nombre}", key=f"dash_mod_{i}", use_container_width=True, help=desc):
                st.session_state.vista = vista_key
                st.rerun()
            st.caption(desc)

    # ── ESTADO DE APIs ───────────────────────────────────────────
    st.markdown('<div class="section-title">Estado del sistema</div>', unsafe_allow_html=True)

    apis = {
        "FAL_KEY":       ("FAL.AI", "Imágenes · Video · Upscaling"),
        "GROQ_API_KEY":  ("Groq",   "LinkedIn · Análisis de mercado"),
        "GEMINI_API_KEY":("Gemini", "Google AI"),
        "GITHUB_TOKEN":  ("GitHub", "Persistencia de galería"),
    }

    api_html = ""
    apis_ok = 0
    for env_key, (nombre, desc) in apis.items():
        val = os.environ.get(env_key, "")
        if val:
            apis_ok += 1
            api_html += f'<div class="api-row"><div class="api-dot-ok"></div><span class="api-name">{nombre}</span><span class="api-label">{desc}</span></div>'
        else:
            api_html += f'<div class="api-row"><div class="api-dot-err"></div><span class="api-name">{nombre}</span><span class="api-label">Sin configurar · ve a ⚙️ Configuración</span></div>'

    st.markdown(api_html, unsafe_allow_html=True)

    if apis_ok == len(apis):
        st.success(f"✅ Todas las APIs operativas ({apis_ok}/{len(apis)})")
    else:
        st.warning(f"⚠️ {len(apis) - apis_ok} APIs sin configurar. El sistema puede funcionar en modo parcial.")

    # ── ÚLTIMAS GENERACIONES ─────────────────────────────────────
    st.markdown('<div class="section-title">Últimas imágenes</div>', unsafe_allow_html=True)

    if galeria:
        recientes = galeria[:6]
        thumb_html = '<div class="gallery-strip">'
        for item in recientes:
            url = item.get("url", "")
            if url:
                thumb_html += f'<div class="gallery-thumb"><img src="{url}" alt="{item.get("prompt","")[:30]}"/></div>'
        thumb_html += '</div>'
        st.markdown(thumb_html, unsafe_allow_html=True)

        if st.button("📂 Ver galería completa", use_container_width=False):
            st.session_state.vista = "📂 Historial"
            st.rerun()
    else:
        st.markdown("""
        <div class="empty-state">
            🖼️ Aún no has generado ninguna imagen.<br>
            <small>Ve al Generador para crear tu primera obra.</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🎨 Ir al Generador", use_container_width=False):
            st.session_state.vista = "🎨 Generador de Imagenes"
            st.rerun()

    # ── FOOTER ───────────────────────────────────────────────────
    st.divider()
    st.caption(f"Merlín AI 2.0 · Fase 5 · {time.strftime('%d/%m/%Y %H:%M')}")