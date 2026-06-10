# frontend/views/interprete.py
import os
import streamlit as st
from google.genai import Client


def estimar_tokens(texto: str) -> int:
    return max(1, len(texto) // 4)


def calcular_ahorro(tokens_original: int, tokens_optimizado: int) -> dict:
    precio_por_token = 3 / 1_000_000
    ahorro_pct = max(0, round((1 - tokens_optimizado / tokens_original) * 100)) if tokens_original > 0 else 0
    return {
        "tokens_original": tokens_original,
        "tokens_optimizado": tokens_optimizado,
        "ahorro_pct": ahorro_pct,
        "coste_original_usd": tokens_original * precio_por_token,
        "coste_optimizado_usd": tokens_optimizado * precio_por_token,
    }


def render() -> None:

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Raleway:wght@300;400;600&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap');

    .interprete-badge {
        display: inline-block;
        background: linear-gradient(135deg, #7B5EA7, #C084FC);
        color: white;
        font-family: 'Raleway', sans-serif;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        padding: 0.25rem 0.9rem;
        border-radius: 20px;
        margin-bottom: 0.75rem;
    }
    .interprete-title {
        font-family: 'Cinzel', serif;
        font-size: 1.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #7B5EA7, #C084FC, #F0D0FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
    }
    .interprete-sub {
        font-family: 'Raleway', sans-serif;
        font-size: 0.88rem;
        color: #8A7AA0;
        margin-bottom: 1.5rem;
    }
    .rctc-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem;
        margin: 0.5rem 0 1.5rem;
    }
    .rctc-card {
        background: linear-gradient(160deg, #1A0F2E, #12122B);
        border: 1px solid #7B5EA733;
        border-radius: 10px;
        padding: 0.75rem;
        text-align: center;
    }
    .rctc-letter {
        font-family: 'Cinzel', serif;
        font-size: 1.4rem;
        font-weight: 900;
        color: #C084FC;
        display: block;
    }
    .rctc-word {
        font-family: 'Raleway', sans-serif;
        font-size: 0.68rem;
        color: #8A7AA0;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    .metric-box {
        background: #0F172A;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.85rem;
        color: #94A3B8;
    }
    .metric-box .valor {
        font-size: 1.05rem;
        font-weight: 700;
        color: #4ADE80;
    }
    .metric-box .etiqueta {
        font-size: 0.73rem;
        color: #64748B;
        margin-top: 2px;
    }
    .problema-box {
        background: linear-gradient(160deg, #1A0F2E, #12122B);
        border: 1px solid #7B5EA733;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.88rem;
        color: #CBD5E1;
        line-height: 1.6;
        height: 100%;
    }
    .problema-title {
        font-family: 'Raleway', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #C084FC;
        margin-bottom: 0.6rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── HERO ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem;">
        <div class="interprete-badge">Motor de Optimización · Merlín AI</div>
        <div class="interprete-title">El Intérprete</div>
        <div class="interprete-sub">Transforma ideas en bruto en instrucciones técnicas de alta precisión</div>
    </div>
    """, unsafe_allow_html=True)

    # ── FRAMEWORK RCTC ───────────────────────────────────────────
    st.markdown("""
    <div class="rctc-grid">
        <div class="rctc-card"><span class="rctc-letter">R</span><span class="rctc-word">Role</span></div>
        <div class="rctc-card"><span class="rctc-letter">C</span><span class="rctc-word">Context</span></div>
        <div class="rctc-card"><span class="rctc-letter">T</span><span class="rctc-word">Task</span></div>
        <div class="rctc-card"><span class="rctc-letter">C</span><span class="rctc-word">Constraint</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── DOS COLUMNAS: CONTEXTO + CONSOLA ─────────────────────────
    col1, col2 = st.columns([1.1, 0.9], gap="large")

    with col1:
        st.markdown("""
        <div class="problema-box">
            <div class="problema-title">🎯 El Problema de Negocio</div>
            Modelos avanzados como <strong>Claude 3.5 Sonnet</strong> son potentes pero costosos.
            Lanzar prompts incompletos obliga al sistema a iterar de más,
            <strong>duplicando el gasto operativo</strong> en llamadas innecesarias.
            <br><br>
            <div class="problema-title">🛠️ La Solución: Arquitectura Filtro</div>
            Gemini 2.5 Flash actúa como filtro previo para reestructurar tu idea
            bajo el framework <strong>RCTC</strong> (Rol · Contexto · Tarea · Constraint).
            El resultado: instrucción técnica blindada que obtiene la respuesta perfecta
            <strong>a la primera</strong>.
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("##### 🕹️ Consola de Optimización")

        # Puede venir precargado desde otro módulo
        prompt_inicial = st.session_state.pop("interprete_input", "")

        prompt_usuario = st.text_area(
            "Introduce tu idea en bruto:",
            value=prompt_inicial,
            placeholder="Ej: Redacta un correo de reclamación formal...",
            height=110,
            label_visibility="collapsed",
            key="interprete_prompt",
        )

        # Tipo de optimización
        tipo = st.radio(
            "Optimizar para:",
            ["🤖 Claude / LLM", "🎨 Imagen (FLUX)", "✍️ LinkedIn"],
            horizontal=True,
            key="interprete_tipo",
        )

        boton_ejecutar = st.button("🧠 Procesar e Inyectar Estructura RCTC", use_container_width=True, type="primary")

    # ── PROCESAMIENTO ────────────────────────────────────────────
    if boton_ejecutar:
        st.markdown("---")

        if not prompt_usuario.strip():
            st.warning("El campo de texto no puede estar vacío.")
        else:
            # Intentar GEMINI_API_KEY de Secrets primero
            api_key = os.environ.get("GEMINI_API_KEY", "")

            if not api_key:
                st.error("⚙️ GEMINI_API_KEY no configurada en Secrets. Ve a ⚙️ Configuración.")
            else:
                with st.spinner("🔮 Reestructurando sintaxis bajo framework RCTC..."):
                    try:
                        client = Client(api_key=api_key)

                        tipo_contexto = {
                            "🤖 Claude / LLM": "modelo de lenguaje Claude 3.5 Sonnet",
                            "🎨 Imagen (FLUX)": "modelo de generación de imágenes FLUX Dev",
                            "✍️ LinkedIn": "redacción de posts profesionales en LinkedIn",
                        }.get(tipo, "modelo de lenguaje")

                        instrucciones_experto = f"""Eres un Ingeniero de Prompts Senior especializado en {tipo_contexto}.
Tu misión es reestructurar el input del usuario siguiendo el framework RCTC:

- ROLE: Define el rol exacto que debe asumir el modelo (experto, persona, función).
- CONTEXT: Proporciona el contexto mínimo necesario para que el modelo no haga suposiciones erróneas.
- TASK: Describe la tarea de forma inequívoca: qué debe producir, en qué formato, con qué extensión.
- CONSTRAINT: Establece restricciones de tono, estilo, longitud o limitaciones explícitas.

El prompt resultante debe ser ejecutable sin iteraciones adicionales.
Escribe con claridad técnica, no con adornos. Cada palabra debe justificarse por su utilidad.

Responde ÚNICAMENTE con estos dos bloques, en este orden exacto, sin texto adicional:

[PROMPT_FINAL]
El prompt estructurado siguiendo RCTC, listo para copiar y usar.

[CONSEJOS]
Lista de 3 a 5 puntos concretos explicando qué tenía el prompt original que generaba desperdicio de tokens y cómo lo has corregido. Sé específico, no genérico."""

                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=(
                                f"Prompt original del usuario:\n\n{prompt_usuario}\n\n"
                                f"Optimízalo para {tipo_contexto} siguiendo el framework RCTC."
                            ),
                            config={'system_instruction': instrucciones_experto}
                        )

                        texto_respuesta = response.text.strip()

                        # ── PARSEO CON FALLBACK EXPLÍCITO ──
                        if "[PROMPT_FINAL]" in texto_respuesta and "[CONSEJOS]" in texto_respuesta:
                            partes = texto_respuesta.split("[CONSEJOS]")
                            prompt_final = partes[0].replace("[PROMPT_FINAL]", "").strip()
                            consejos_final = partes[1].strip()
                            parse_ok = True
                        else:
                            prompt_final = texto_respuesta
                            consejos_final = None
                            parse_ok = False

                        # ── MÉTRICAS DE AHORRO ──
                        tokens_orig = estimar_tokens(prompt_usuario)
                        tokens_opt  = estimar_tokens(prompt_final)
                        metricas    = calcular_ahorro(tokens_orig, tokens_opt)

                        st.markdown(
                            f"""
                            <div class="metric-box">
                                <div>
                                    <div class="valor">{metricas['tokens_original']} → {metricas['tokens_optimizado']} tokens</div>
                                    <div class="etiqueta">Estimación de tokens (prompt original vs. optimizado)</div>
                                </div>
                                <div style="text-align:right">
                                    <div class="valor">~{metricas['ahorro_pct']}% {'más eficiente' if metricas['ahorro_pct'] > 0 else 'de overhead necesario'}</div>
                                    <div class="etiqueta">Coste ref. Claude 3.5 Sonnet · $3/1M tokens</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if not parse_ok:
                            st.warning("⚠️ El modelo no devolvió el formato esperado. Se muestra la respuesta completa.")

                        st.success("✅ Reestructuración RCTC completada.")

                        tab1, tab2 = st.tabs(["📋 Prompt Estructurado", "💡 Auditoría de Tokens"])

                        with tab1:
                            st.code(prompt_final, language="text")

                            # ── BOTONES DE USO DIRECTO ──
                            st.markdown("**Enviar directamente a:**")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("🎨 Generador de Imágenes", use_container_width=True):
                                    st.session_state["selected_panic_prompt"] = prompt_final
                                    st.session_state["vista"] = "🎨 Generador de Imagenes"
                                    st.rerun()
                            with c2:
                                if st.button("✍️ Redactor LinkedIn", use_container_width=True):
                                    st.session_state["linkedin_topic"] = prompt_final
                                    st.session_state["vista"] = "✍️ Redactor LinkedIn"
                                    st.rerun()

                        with tab2:
                            if consejos_final:
                                st.markdown(consejos_final)
                            else:
                                st.info("No se pudo extraer la auditoría. Revisa el prompt en la pestaña anterior.")

                    except Exception as e:
                        st.error(f"Error al conectar con Gemini: {str(e)}")
                        st.caption("Verifica que GEMINI_API_KEY es válida en Secrets.")