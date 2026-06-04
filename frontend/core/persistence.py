# frontend/core/persistence.py
import json
import os
import logging
from typing import Any
import streamlit as st

logger = logging.getLogger("persistence")

_REPO_PATH = "backend/core/estado.json"


def _get_github_repo():
    try:
        from github import Github
        token = os.environ.get("GITHUB_TOKEN", "")
        repo_name = os.environ.get("GITHUB_REPO", "")
        if not token or not repo_name:
            return None, None, None
        g = Github(token)
        repo = g.get_repo(repo_name)
        contents = repo.get_contents(_REPO_PATH)
        return repo, contents, json.loads(contents.decoded_content.decode("utf-8"))
    except Exception as e:
        logger.error(f"[persistence] GitHub error: {e}")
        return None, None, None


def guardar_galeria() -> bool:
    try:
        repo, contents, estado = _get_github_repo()
        if not repo:
            return False

        galeria = st.session_state.get("galeria", [])
        # Solo guardar metadata, no bytes
        galeria_serializable = [
            {k: v for k, v in r.items() if k != "bytes"}
            for r in galeria
        ]

        estado.setdefault("frontend", {})
        estado["frontend"]["galeria"] = galeria_serializable

        repo.update_file(
            _REPO_PATH,
            "chore: actualizar galería desde Merlín AI",
            json.dumps(estado, ensure_ascii=False, indent=2),
            contents.sha,
        )
        logger.info(f"[persistence] Galería guardada: {len(galeria_serializable)} items")
        return True
    except Exception as e:
        logger.error(f"[persistence] Error guardando: {e}")
        return False


def cargar_galeria() -> list:
    try:
        _, _, estado = _get_github_repo()
        if not estado:
            return []
        galeria = estado.get("frontend", {}).get("galeria", [])
        logger.info(f"[persistence] Galería cargada: {len(galeria)} items")
        return galeria
    except Exception as e:
        logger.error(f"[persistence] Error cargando: {e}")
        return []