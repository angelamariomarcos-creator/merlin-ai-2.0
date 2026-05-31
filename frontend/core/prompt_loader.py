# frontend/core/prompt_loader.py
import json
import logging
from pathlib import Path
from typing import Any
import streamlit as st

logger = logging.getLogger("prompt_loader")
PROMPTS_DIR = Path("C:/merlin-ai-2.0/backend/core/prompts")

def _load_json(filename: str) -> dict[str, Any]:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"[prompt_loader] Archivo no encontrado: {path}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_resource
def load_panic_pools() -> dict[str, list[str]]:
    """
    Carga los 4 archivos JSON de prompts una sola vez por sesión.
    Devuelve un dict con las 4 listas listas para random.choice().
    """
    try:
        cameras_raw  = _load_json("cameras.json")
        styles_raw   = _load_json("styles.json")
        subjects_raw = _load_json("subjects.json")
        settings_raw = _load_json("settings.json")
        return {
            "subjects":  subjects_raw["subjects"],
            "settings":  settings_raw["settings"],
            "styles":    [s["prompt_fragment"] for s in styles_raw["styles"]],
            "cameras":   [c["prompt_fragment"] for c in cameras_raw["cameras"]],
        }
    except FileNotFoundError as e:
        logger.error(str(e))
        return _fallback_pools()
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"[prompt_loader] Error parseando JSON: {e}")
        return _fallback_pools()

def _fallback_pools() -> dict[str, list[str]]:
    """
    Valores mínimos de emergencia si los archivos JSON no están disponibles.
    El frontend no se rompe, pero avisa en logs.
    """
    logger.warning(
        "[prompt_loader] Usando pools de fallback. "
        "Verifica que backend/core/prompts/ esté accesible."
    )
    return {
        "subjects": ["a lone wanderer", "an ancient guardian"],
        "settings": ["in a forgotten realm", "inside a neon city"],
        "styles":   ["hyperrealistic, 8K, cinematic lighting"],
        "cameras":  ["wide shot, cinematic 35mm, anamorphic bokeh"],
    }