# frontend/core/css_engine.py
import streamlit as st

def inject_css(bg: str, sidebar: str, text: str, accent: str) -> None:
    css = f"""
    <style>
    .stApp {{ background-color: {bg}; color: {text}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar}; }}
    h1, h2, h3 {{ color: {accent} !important; }}
    .stButton > button {{ border-color: {accent}; color: {accent}; }}
    .stButton > button:hover {{ background-color: {accent}; color: {bg}; }}
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-thumb {{ background: {accent}66; border-radius: 3px; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)