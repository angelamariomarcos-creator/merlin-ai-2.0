# frontend/components/card.py
import streamlit as st

def merlin_card(content: str) -> None:
    """Envuelve un bloque de texto o HTML dentro de una tarjeta con diseño Merlín."""
    st.markdown(
        f'<div class="merlin-card">{content}</div>',
        unsafe_allow_html=True,
    )

def merlin_metric(label: str, value: str) -> None:
    """Renderiza una métrica personalizada sin depender de los selectores nativos de Streamlit."""
    st.markdown(
        f'''
        <div class="merlin-metric">
            <span class="merlin-label">{label}</span><br>
            <span style="font-size:1.6rem;font-weight:700">{value}</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )