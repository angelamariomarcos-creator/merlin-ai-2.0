# frontend/app.py
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os
import streamlit as st
from frontend.config.themes import THEMES
from frontend.config.views import VIEWS
from frontend.core.session import init_session
from frontend.core.css_engine import inject_css
from frontend.core.registry import dispatch

st.set_page_config(
    page_title="Merlin AI 2.0",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _show_login() -> None:
    inject_css(**THEMES["Merlin Premium"])

    st.markdown("""
    <style>
    .login-container {
        max-width: 420px;
        margin: 8vh auto;
        text-align: center;
        padding: 3rem 2rem;
        background: linear-gradient(135deg, #12122B, #1A0F2E);
        border: 1px solid #7B5EA755;
        border-radius: 20px;
        box-shadow: 0 20px 60px #7B5EA722;
    }
    .login-logo { font-size: 4rem; margin-bottom: 0.5rem; }
    .login-title {
        font-size: 2rem; font-weight: 900;
        background: linear-gradient(135deg, #7B5EA7, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
    }
    .login-subtitle { font-size: 0.9rem; color: #8A7AA0; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-logo">🔮</div>
            <div class="login-title">MERLÍN AI</div>
            <div class="login-subtitle">Plataforma IA Generativa</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.subheader("Acceder a Merlín AI")

        try:
            from streamlit_oauth import OAuth2Component

            client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
            redirect_uri  = os.environ.get("REDIRECT_URI", "http://localhost:8501")

            if not client_id or not client_secret:
                st.error("❌ Credenciales Google OAuth no configuradas en Secrets.")
                return

            oauth2 = OAuth2Component(
                client_id,
                client_secret,
                "https://accounts.google.com/o/oauth2/auth",
                "https://oauth2.googleapis.com/token",
                "https://oauth2.googleapis.com/token",
                "https://oauth2.googleapis.com/revoke",
            )

            result = oauth2.authorize_button(
                name="Continuar con Google",
                icon="https://www.google.com/favicon.ico",
                redirect_uri=redirect_uri,
                scope="openid email profile",
                key="google_oauth",
                use_container_width=True,
            )

            if result and "token" in result:
                import jwt as pyjwt
                token    = result["token"]
                id_token = token.get("id_token", "")
                if id_token:
                    payload = pyjwt.decode(id_token, options={"verify_signature": False})
                    st.session_state["user_email"] = payload.get("email", "")
                    st.session_state["user_name"]  = payload.get("name", "Usuario")
                    st.session_state["user_pic"]   = payload.get("picture", "")
                    st.session_state["logged_in"]  = True
                    st.rerun()

        except Exception as e:
            st.error(f"❌ Error OAuth: {e}")

        st.divider()
        st.caption("Al acceder aceptas los términos de uso de Merlín AI.")


def _show_app() -> None:
    init_session()

    user_name  = st.session_state.get("user_name", "Usuario")
    user_pic   = st.session_state.get("user_pic", "")
    user_email = st.session_state.get("user_email", "")

    with st.sidebar:
        if user_pic:
            st.markdown(f'<img src="{user_pic}" style="border-radius:50%;width:48px;height:48px;display:block;margin:0 auto 0.5rem;">', unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;font-weight:600;color:#C084FC;'>{user_name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;font-size:0.75rem;color:#8A7AA0;'>{user_email}</div>", unsafe_allow_html=True)
        st.divider()

        selected_theme = st.selectbox("🎨 Tema", list(THEMES.keys()), key="tema")
        st.divider()
        selected_view = st.radio("📂 Módulos", VIEWS, key="vista")
        st.divider()
        st.caption("v2.0.0 · Fase 5")
        st.caption(f"🖼 Galería: {len(st.session_state.get('galeria', []))} items")
        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for key in ["logged_in", "user_email", "user_name", "user_pic"]:
                st.session_state.pop(key, None)
            st.rerun()

    inject_css(**THEMES[selected_theme])
    st.title(selected_view)
    st.divider()
    dispatch(selected_view)


if st.session_state.get("logged_in"):
    _show_app()
else:
    _show_login()