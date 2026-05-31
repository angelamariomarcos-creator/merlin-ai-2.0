# frontend/core/persistence.py

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

logger = logging.getLogger("persistence")

# ── Ruta dinámica y portable (Raíz del proyecto) ──────────
ROOT_DIR = Path(__file__).resolve().parents[2]
PERSISTENCE_PATH = ROOT_DIR / "backend" / "core" / "estado.json"

# ── Claves planas: coinciden exactamente con key= de cada widget ──
PERSISTIBLE_KEYS: dict[str, Any] = {
    "galeria": [],
    "max_cost_per_image_usd": 0.035,
    "max_cost_per_video_usd": 0.100,
    "margin_floor_pct": 70.0,
    "flux_inference_steps": 28,
    "default_guidance_scale": 3.5,
}


# ── Guardar estado local ──────────────────────────────────

def guardar_estado_local() -> bool:
    """
    Serializa las claves planas de st.session_state en la
    macro-entidad 'frontend' dentro de estado.json.
    """
    try:
        # Asegurar que el directorio contenedor exista en el backend
        PERSISTENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        estado: dict[str, Any] = {}
        if PERSISTENCE_PATH.exists():
            try:
                with open(PERSISTENCE_PATH, "r", encoding="utf-8") as f:
                    estado = json.load(f)
            except json.JSONDecodeError:
                logger.warning("[persistence] estado.json corrupto. Se sobrescribirá.")

        frontend_block: dict[str, Any] = estado.setdefault("frontend", {})

        for key in PERSISTIBLE_KEYS:
            if key in st.session_state:
                frontend_block[key] = st.session_state[key]

        frontend_block["last_saved"] = datetime.now(timezone.utc).isoformat()

        with open(PERSISTENCE_PATH, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)

        logger.info(f"[persistence] Guardado OK. Claves: {list(PERSISTIBLE_KEYS.keys())}")
        return True

    except OSError as e:
        logger.error(f"[persistence] Error de I/O al guardar: {e}")
        return False


# ── Cargar estado local ───────────────────────────────────

def cargar_estado_local() -> bool:
    """
    Carga los datos en st.session_state antes de que se rendericen los widgets.
    Evita la pérdida de datos y respeta el ciclo de vida de Streamlit.
    """
    if not PERSISTENCE_PATH.exists():
        logger.warning(f"[persistence] estado.json no encontrado en {PERSISTENCE_PATH}. Aplicando defaults.")
        _apply_defaults()
        return False

    try:
        with open(PERSISTENCE_PATH, "r", encoding="utf-8") as f:
            estado = json.load(f)

        frontend_block: dict[str, Any] = estado.get("frontend", {})

        if not frontend_block:
            logger.info("[persistence] Sin bloque 'frontend'. Aplicando defaults.")
            _apply_defaults()
            return False

        loaded: list[str] = []
        for key, default in PERSISTIBLE_KEYS.items():
            if key not in st.session_state:
                # Copia profunda para evitar mutaciones de listas (para la galería)
                if isinstance(default, list):
                    st.session_state[key] = json.loads(json.dumps(frontend_block.get(key, default)))
                else:
                    st.session_state[key] = frontend_block.get(key, default)
                loaded.append(key)

        logger.info(f"[persistence] Cargado OK. Restauradas: {loaded}")
        return True

    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"[persistence] Error al cargar: {e}")
        _apply_defaults()
        return False


# ── Aplicar defaults si no hay persistencia ───────────────

def _apply_defaults() -> None:
    for key, default in PERSISTIBLE_KEYS.items():
        if key not in st.session_state:
            if isinstance(default, list):
                st.session_state[key] = json.loads(json.dumps(default))
            else:
                st.session_state[key] = default


# ── Resetear estado persistido ────────────────────────────

def resetear_estado_local() -> bool:
    """
    Limpia el bloque 'frontend' del JSON y reestablece session_state.
    """
    for key, default in PERSISTIBLE_KEYS.items():
        if isinstance(default, list):
            st.session_state[key] = json.loads(json.dumps(default))
        else:
            st.session_state[key] = default

    if not PERSISTENCE_PATH.exists():
        return True

    try:
        with open(PERSISTENCE_PATH, "r", encoding="utf-8") as f:
            estado = json.load(f)

        if "frontend" in estado:
            del estado["frontend"]

        with open(PERSISTENCE_PATH, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)

        logger.info("[persistence] Bloque 'frontend' eliminado correctamente.")
        return True

    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"[persistence] Error al resetear: {e}")
        return False