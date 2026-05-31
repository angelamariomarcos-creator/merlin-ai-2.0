import streamlit as st

def merlin_card(content: str) -> None:
    """Envuelve un bloque de texto dentro de una tarjeta con diseño Merlín usando contenedores nativos."""
    # Usamos container con borde para simular la clase .merlin-card
    with st.container(border=True):
        st.write(content)

def merlin_metric(label: str, value: str) -> None:
    """Renderiza una métrica personalizada usando componentes nativos de Streamlit."""
    # Usamos st.metric que es el estándar profesional y estable
    st.metric(label=label, value=value)