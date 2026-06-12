# frontend/views/landing.py
import streamlit as st
import os


def render() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Raleway:wght@300;400;600&display=swap');

    .landing-hero { text-align: center; padding: 3rem 1rem 2rem; position: relative; }
    .landing-logo {
        font-family: 'Cinzel', serif; font-size: 5rem; font-weight: 900;
        background: linear-gradient(135deg, #7B5EA7, #C084FC, #F0D0FF, #7B5EA7);
        background-size: 300% 300%;
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        animation: gradientShift 4s ease infinite; line-height: 1; margin-bottom: 0.5rem;
    }
    .landing-tagline {
        font-family: 'Raleway', sans-serif; font-size: 1.3rem; font-weight: 300;
        color: #C084FC; letter-spacing: 0.3em; text-transform: uppercase; margin-bottom: 1rem;
    }
    .landing-desc {
        font-family: 'Raleway', sans-serif; font-size: 1.1rem; color: #B0A0CC;
        max-width: 600px; margin: 0 auto 2rem; line-height: 1.8;
    }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0; }
    .feature-card {
        background: linear-gradient(135deg, #1A0F2E, #12122B); border: 1px solid #7B5EA733;
        border-radius: 12px; padding: 1.5rem; text-align: center; transition: all 0.3s ease;
        position: relative; overflow: hidden;
    }
    .feature-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #C084FC, transparent);
    }
    .feature-card:hover { border-color: #7B5EA7; transform: translateY(-3px); box-shadow: 0 8px 32px #7B5EA733; }
    .feature-num { font-family: 'Cinzel', serif; font-size: 0.75rem; color: #4A3A60; letter-spacing: 0.2em; display: block; margin-bottom: 0.5rem; }
    .feature-title { font-family: 'Cinzel', serif; font-size: 0.9rem; color: #C084FC; letter-spacing: 0.1em; margin-bottom: 0.5rem; font-weight: 700; }
    .feature-desc { font-family: 'Raleway', sans-serif; font-size: 0.85rem; color: #8A7AA0; line-height: 1.5; }
    .stats-row { display: flex; justify-content: center; gap: 3rem; margin: 2rem 0; flex-wrap: wrap; }
    .stat-item { text-align: center; }
    .stat-number { font-family: 'Cinzel', serif; font-size: 2.5rem; font-weight: 900; color: #C084FC; display: block; }
    .stat-label { font-family: 'Raleway', sans-serif; font-size: 0.8rem; color: #8A7AA0; letter-spacing: 0.2em; text-transform: uppercase; }
    .demo-badge {
        display: inline-block; background: linear-gradient(135deg, #7B5EA7, #C084FC); color: white;
        font-family: 'Raleway', sans-serif; font-size: 0.75rem; font-weight: 600;
        letter-spacing: 0.2em; text-transform: uppercase; padding: 0.3rem 1rem; border-radius: 20px; margin-bottom: 1rem;
    }
    .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin: 2rem 0; }
    .pricing-card {
        background: linear-gradient(135deg, #0D0D1A, #12122B); border: 1px solid #7B5EA733;
        border-radius: 16px; padding: 2rem 1.5rem; text-align: center; position: relative;
    }
    .pricing-card.featured { border-color: #C084FC; box-shadow: 0 0 40px #7B5EA722; }
    .pricing-card.featured::before {
        content: 'POPULAR'; position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
        background: linear-gradient(135deg, #7B5EA7, #C084FC); color: white;
        font-family: 'Raleway', sans-serif; font-size: 0.7rem; font-weight: 700;
        letter-spacing: 0.2em; padding: 0.2rem 1rem; border-radius: 20px; white-space: nowrap;
    }
    .pricing-plan { font-family: 'Cinzel', serif; font-size: 1.1rem; color: #C084FC; margin-bottom: 0.5rem; }
    .pricing-price { font-family: 'Cinzel', serif; font-size: 2.5rem; font-weight: 900; color: white; margin: 0.5rem 0; }
    .pricing-period { font-family: 'Raleway', sans-serif; font-size: 0.85rem; color: #8A7AA0; margin-bottom: 1.5rem; }
    .pricing-feature { font-family: 'Raleway', sans-serif; font-size: 0.85rem; color: #B0A0CC; margin: 0.4rem 0; text-align: left; }
    .divider-magic { text-align: center; margin: 2rem 0; position: relative; }
    .divider-magic::before { content: ''; position: absolute; top: 50%; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, #7B5EA7, transparent); }
    .divider-text { font-family: 'Cinzel', serif; font-size: 0.8rem; color: #7B5EA7; letter-spacing: 0.3em; background: #0D0D1A; padding: 0 1rem; position: relative; }
    @keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    </style>
    """, unsafe_allow_html=True)

    galeria = st.session_state.get("galeria", [])
    videos  = st.session_state.get("videos", [])

    st.markdown(f"""
    <div class="landing-hero">
        <div class="demo-badge">Plataforma IA Generativa</div>
        <div class="landing-logo">MERLÍN AI</div>
        <div class="landing-tagline">Crea. Anima. Escala.</div>
        <div class="landing-desc">
            Genera imágenes profesionales, anima tus creaciones en video
            y escala a 4K con inteligencia artificial. Sin diseñador. Sin complicaciones.
        </div>
    </div>
    <div class="stats-row">
        <div class="stat-item"><span class="stat-number">{len(galeria)}</span><span class="stat-label">Imágenes creadas</span></div>
        <div class="stat-item"><span class="stat-number">{len(videos)}</span><span class="stat-label">Videos generados</span></div>
        <div class="stat-item"><span class="stat-number">4K</span><span class="stat-label">Resolución máxima</span></div>
        <div class="stat-item"><span class="stat-number">FLUX</span><span class="stat-label">Motor</span></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Empezar a crear — es gratis", use_container_width=True, type="primary"):
            st.session_state.vista = "Generador de Imagenes"
            st.rerun()
        st.caption("Sin tarjeta de crédito · Sin instalación · Funciona en el navegador")

    st.markdown('<div class="divider-magic"><span class="divider-text">CAPACIDADES</span></div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card"><span class="feature-num">I</span><div class="feature-title">Generación de Imágenes</div><div class="feature-desc">FLUX Dev con 15 estilos artísticos y 15 tipos de cámara cinematográfica</div></div>
        <div class="feature-card"><span class="feature-num">II</span><div class="feature-title">Animación de Video</div><div class="feature-desc">Convierte cualquier imagen en un clip de video con movimiento natural</div></div>
        <div class="feature-card"><span class="feature-num">III</span><div class="feature-title">Reescalado 4K</div><div class="feature-desc">Aumenta la resolución de tus imágenes 4x sin perder calidad con AuraSR</div></div>
        <div class="feature-card"><span class="feature-num">IV</span><div class="feature-title">El Intérprete</div><div class="feature-desc">Motor RCTC que transforma ideas en bruto en prompts técnicos de alta precisión</div></div>
        <div class="feature-card"><span class="feature-num">V</span><div class="feature-title">Redactor LinkedIn</div><div class="feature-desc">Posts profesionales optimizados para engagement con Llama 3.3</div></div>
        <div class="feature-card"><span class="feature-num">VI</span><div class="feature-title">Inteligencia de Mercado</div><div class="feature-desc">Análisis de tendencias de nicho con IA en tiempo real. Gratis.</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider-magic"><span class="divider-text">PLANES</span></div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="pricing-grid">
        <div class="pricing-card">
            <div class="pricing-plan">FREE</div>
            <div class="pricing-price">0€</div>
            <div class="pricing-period">para siempre</div>
            <div class="pricing-feature">— 5 imágenes al día</div>
            <div class="pricing-feature">— Análisis de mercado</div>
            <div class="pricing-feature">— Redactor LinkedIn</div>
            <div class="pricing-feature">— El Intérprete</div>
        </div>
        <div class="pricing-card featured">
            <div class="pricing-plan">PREMIUM</div>
            <div class="pricing-price">9.99€</div>
            <div class="pricing-period">al mes</div>
            <div class="pricing-feature">— Imágenes ilimitadas</div>
            <div class="pricing-feature">— 30 videos al mes</div>
            <div class="pricing-feature">— Reescalado 4K ilimitado</div>
            <div class="pricing-feature">— Sin marca de agua</div>
            <div class="pricing-feature">— Soporte prioritario</div>
        </div>
        <div class="pricing-card">
            <div class="pricing-plan">EMPRESA</div>
            <div class="pricing-price">49€</div>
            <div class="pricing-period">al mes</div>
            <div class="pricing-feature">— Todo lo de Premium</div>
            <div class="pricing-feature">— API dedicada</div>
            <div class="pricing-feature">— Múltiples usuarios</div>
            <div class="pricing-feature">— SLA garantizado</div>
            <div class="pricing-feature">— Factura mensual</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider-magic"><span class="divider-text">EMPIEZA AHORA</span></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Entrar a Merlín AI", use_container_width=True, type="primary"):
            st.session_state.vista = "Generador de Imagenes"
            st.rerun()
        st.markdown("""
        <div style="text-align:center; margin-top:1rem;">
            <span style="font-family:'Raleway',sans-serif; font-size:0.8rem; color:#8A7AA0;">
                Construido por Javi García · Merlín AI 2.0
            </span>
        </div>
        """, unsafe_allow_html=True)