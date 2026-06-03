# frontend/components/sidebar.py
import streamlit as st


def render_sidebar(styles: dict, views: list[str]) -> tuple[str, str]:
    with st.sidebar:
        st.title("🔮 Merlín AI 2.0")
        st.divider()

        selected_style = st.selectbox(
            "🎨 Tema visual",
            options=list(styles.keys()),
            key="selected_style",
        )

        st.divider()

        selected_view = st.radio(
            "📂 Módulos",
            options=views,
            key="selected_view",
        )

    return selected_style, selected_view