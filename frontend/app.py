# frontend/app.py
import sys
import os

# Forzar a Python a incluir la raíz del proyecto en las búsquedas de módulos de inmediato
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
import urllib.parse
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

GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO   = "https://www.googleapis.com/oauth2/v3/userinfo"


def _get_oauth_config():
    return {
        "client_id":     os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri":  os.environ.get("REDIRECT_URI", "http://localhost:8501"),
    }


def _build_auth_url(cfg: dict) -> str:
    params = {
        "client_id":     cfg["client_id"],
        "redirect_uri":  cfg["redirect_uri"],
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def _exchange_code_for_token(code: str, cfg: dict) -> dict:
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri":  cfg["redirect_uri"],
        "grant_type":    "authorization_code",
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_user_info(access_token: str) -> dict:
    resp = requests.get(GOOGLE_USERINFO, headers={
        "Authorization": f"Bearer {access_token}"
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _handle_oauth_callback():
    """Procesa el código OAuth que llega en los query params tras el redirect."""
    params = st.query_params
    code  = params.get("code", "")
    error = params.get("error", "")

    if error:
        st.error(f"❌ Google denegó el acceso: {error}")
        st.query_params.clear()
        return

    if not code:
        return

    cfg = _get_oauth_config()
    try:
        token_data  = _exchange_code_for_token(code, cfg)
        access_token = token_data.get("access_token", "")
        if not access_token:
            st.error("❌ No se recibió access_token de Google.")
            st.query_params.clear()
            return

        user = _get_user_info(access_token)
        st.session_state["user_email"] = user.get("email", "")
        st.session_state["user_name"]  = user.get("name", "Usuario")
        st.session_state["user_pic"]   = user.get("picture", "")
        st.session_state["logged_in"]  = True
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.error(f"❌ Error al autenticar: {e}")
        st.query_params.clear()


def _show_login() -> None:
    inject_css(**THEMES["Merlin Premium"])

    # Procesar callback OAuth si viene con ?code=
    _handle_oauth_callback()

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
    .google-btn {
        display: inline-flex; align-items: center; gap: 0.6rem;
        background: #fff; color: #3c4043;
        border: 1px solid #dadce0; border-radius: 8px;
        padding: 0.7rem 1.5rem; font-size: 0.95rem; font-weight: 500;
        text-decoration: none; cursor: pointer;
        transition: box-shadow 0.2s;
        width: 100%; justify-content: center;
    }
    .google-btn:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
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

        cfg = _get_oauth_config()
        if not cfg["client_id"] or not cfg["client_secret"]:
            st.error("❌ Credenciales Google OAuth no configuradas en Secrets.")
        else:
            auth_url = _build_auth_url(cfg)
            st.markdown(
                f'<a href="{auth_url}" target="_self" class="google-btn">'
                f'<img src="https://www.google.com/favicon.ico" width="20"/> '
                f'Continuar con Google</a>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.caption("Al acceder aceptas los términos de uso de Merlín AI.")


def _show_app() -> None:
    init_session()

    user_name  = st.session_state.get("user_name", "Usuario")
    user_pic   = st.session_state.get("user_pic", "")
    user_email = st.session_state.get("user_email", "")

    with st.sidebar:
        if user_pic:
            st.markdown(
                f'<img src="{user_pic}" style="border-radius:50%;width:48px;'
                f'height:48px;display:block;margin:0 auto 0.5rem;">',
                unsafe_allow_html=True,
            )
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
    
    # Renderizar la vista seleccionada usando el despachador
    dispatch(selected_view)


# --- FLUJO DE CONTROL PRINCIPAL ---
if __name__ == "__main__":
    if not st.session_state.get("logged_in", False):
        _show_login()
    else:
        _show_app()