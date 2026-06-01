# frontend/core/prompt_loader.py

import json
import logging
from pathlib import Path
from typing import Any

import streamlit as st

logger = logging.getLogger("prompt_loader")

_ROOT       = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = _ROOT / "backend" / "core" / "prompts"


def _load_json(filename: str) -> dict[str, Any]:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"[prompt_loader] No encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def load_panic_pools() -> dict[str, list[str]]:
    try:
        cameras_raw  = _load_json("cameras.json")
        styles_raw   = _load_json("styles.json")
        subjects_raw = _load_json("subjects.json")
        settings_raw = _load_json("settings.json")
        return {
            "subjects": subjects_raw["subjects"],
            "settings": settings_raw["settings"],
            "styles":   [s["prompt_fragment"] for s in styles_raw["styles"]],
            "cameras":  [c["prompt_fragment"] for c in cameras_raw["cameras"]],
        }
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"[prompt_loader] {e}")
        return {
            "subjects": ["a lone wanderer", "an ancient guardian"],
            "settings": ["in a forgotten realm", "inside a neon city"],
            "styles":   ["hyperrealistic, 8K, cinematic lighting"],
            "cameras":  ["wide shot, cinematic 35mm, anamorphic bokeh"],
        }