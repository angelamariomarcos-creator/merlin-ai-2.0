# frontend/app.py
import sys
import os
from pathlib import Path

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

ASSETS = Path(__file__).parent.parent / "assets" / "images"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"


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


def _handle_oauth_callback() -> bool:
    params = st.query_params
    code  = params.get("code", "")
    error = params.get("error", "")

    if error:
        st.error(f"❌ Google denegó el acceso: {error}")
        st.query_params.clear()
        return False

    if not code:
        return False

    cfg = _get_oauth_config()
    try:
        with st.spinner("Autenticando con Google..."):
            token_data   = _exchange_code_for_token(code, cfg)
            access_token = token_data.get("access_token", "")

        if not access_token:
            st.error("❌ No se recibió access_token de Google.")
            st.query_params.clear()
            return False

        user = _get_user_info(access_token)
        st.session_state["user_email"] = user.get("email", "")
        st.session_state["user_name"]  = user.get("name", "Usuario")
        st.session_state["user_pic"]   = user.get("picture", "")
        st.session_state["logged_in"]  = True
        st.query_params.clear()
        return True

    except Exception as e:
        st.error(f"❌ Error al autenticar: {e}")
        st.query_params.clear()
        return False


def _show_app() -> None:
    init_session()

    user_name  = st.session_state.get("user_name", "Usuario")
    user_pic   = st.session_state.get("user_pic", "")
    user_email = st.session_state.get("user_email", "")

    with st.sidebar:
        # ── MASCOTA MERLÍN ──────────────────────────────
        mascota = ASSETS / "merlin 2.0.png"
        if mascota.exists():
            st.image(str(mascota), use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;font-size:2.5rem;'>🔮</div>", unsafe_allow_html=True)

        st.markdown("---")

        # ── PERFIL DE USUARIO ───────────────────────────
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
    dispatch(selected_view)


# --- FLUJO DE CONTROL PRINCIPAL ---
if not st.session_state.get("logged_in", False):
    st.session_state["logged_in"] = True
    st.session_state["user_name"] = "Javi"
    st.session_state["user_email"] = "demo@merlin.ai"
    st.session_state["user_pic"] = ""
    st.rerun()
else:
    _show_app()