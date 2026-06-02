# frontend/components/panic_button.py
import random
import streamlit as st
from frontend.core.prompt_loader import load_panic_pools


def _generate_ideas(pools: dict[str, list[str]], n: int = 3) -> list[str]:
    ideas: list[str] = []
    for _ in range(n):
        idea = (
            f"{random.choice(pools['subjects'])} "
            f"{random.choice(pools['settings'])}, "
            f"{random.choice(pools['styles'])}, "
            f"{random.choice(pools['cameras'])}, "
            f"masterpiece, ultra-detailed"
        )
        ideas.append(idea)
    return ideas


def render_panic_button() -> None:
    st.subheader("🎲 Botón de Pánico Creativo")
    st.caption("¿Sin inspiración? Genera 3 combinaciones premium al azar.")

    pools = load_panic_pools()

    if st.button("🎲 ¡Pánico Creativo! Genera 3 ideas", use_container_width=True):
        st.session_state.panic_ideas = _generate_ideas(pools)
        st.session_state.selected_panic_prompt = ""

    if st.session_state.get("panic_ideas"):
        st.write("**Elige una idea para usarla como prompt:**")
        for i, idea in enumerate(st.session_state.panic_ideas):
            col_text, col_btn = st.columns([5, 1])
            with col_text:
                with st.container(border=True):
                    st.info(f"💡 **Idea {i+1}:** {idea}")
                    st.write(idea)
            with col_btn:
                st.write("")
                st.write("")
                if st.button(f"Usar #{i+1}", key=f"panic_select_{i}"):
                    st.session_state.selected_panic_prompt = idea
                    st.rerun()