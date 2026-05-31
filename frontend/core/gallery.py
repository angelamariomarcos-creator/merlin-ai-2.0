# frontend/core/gallery.py

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import streamlit as st
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("gallery")

# ── URL de placeholder FIJA por entorno demo ─────────────
# Misma seed siempre → misma imagen → no cambia en reruns
DEMO_PLACEHOLDER_URL = "https://picsum.photos/seed/merlin-ai-demo/512/512"


# ── Esquema estricto de entrada ───────────────────────────
class GalleryEntry(BaseModel):
    model_config = {"strict": True}

    prompt: str = Field(min_length=3, max_length=2000)
    style: str = Field(min_length=1, max_length=200)
    agent: str = Field(min_length=1)
    url: str = Field(default="")
    image_bytes: bytes | None = Field(default=None)
    is_demo: bool = Field(default=False)

    @field_validator("prompt", "style", "agent", mode="before")
    @classmethod
    def strip_and_reject_empty(cls, v: str) -> str:
        if not isinstance(v, str) or v.strip() == "":
            raise ValueError("El campo no puede ser una cadena vacía.")
        return v.strip()

    @field_validator("agent", mode="before")
    @classmethod
    def validate_agent(cls, v: str) -> str:
        allowed = {
            "image-generator", "animation",
            "upscaler", "demo", "manual",
        }
        v = v.strip()
        if v not in allowed:
            raise ValueError(
                f"Agente '{v}' no permitido. "
                f"Valores válidos: {sorted(allowed)}"
            )
        return v

    @model_validator(mode="after")
    def validate_at_least_one_image_source(self) -> "GalleryEntry":
        """
        En modo real:  url apunta a CDN/FAL.AI  → válido.
        En modo demo:  is_demo=True              → se asigna placeholder fijo.
        En modo bytes: image_bytes proporcionado → válido para display local.
        Los tres son mutuamente excluyentes en prioridad.
        """
        if self.is_demo:
            # Ignoramos url entrante y forzamos placeholder fijo
            object.__setattr__(self, "url", DEMO_PLACEHOLDER_URL)
            return self

        if self.image_bytes is not None:
            # Bytes reales: url no es necesaria
            return self

        if not self.url or not self.url.startswith(("http://", "https://")):
            raise ValueError(
                "Debes proporcionar una URL http/https válida, "
                "image_bytes, o activar is_demo=True."
            )
        return self


# ── Registro persistido en session_state ─────────────────
class GalleryRecord(BaseModel):
    """Estructura final que se guarda en st.session_state.galeria"""
    entry_id:   str
    prompt:     str
    style:      str
    agent:      str
    url:        str           # URL final (CDN, FAL, o placeholder fijo)
    has_bytes:  bool          # True si se guardaron bytes locales
    is_demo:    bool
    timestamp:  str
    prompt_hash: str          # SHA256 primeros 8 chars para deduplicación

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Función principal ─────────────────────────────────────
def save_to_gallery(
    prompt: str,
    style: str,
    agent: str,
    url: str = "",
    image_bytes: bytes | None = None,
    is_demo: bool = False,
) -> GalleryRecord | None:
    """
    Valida la entrada con GalleryEntry (Pydantic),
    construes un GalleryRecord inmutable y lo añade
    al frente de st.session_state.galeria.
    """
    # 1. Validar esquema de entrada
    try:
        entry = GalleryEntry(
            prompt=prompt,
            style=style,
            agent=agent,
            url=url,
            image_bytes=image_bytes,
            is_demo=is_demo,
        )
    except Exception as e:
        logger.error(f"[gallery] Entrada inválida, no guardada: {e}")
        st.toast(f"❌ Error de validación: {e}", icon="🚨")
        return None

    # 2. Deduplicación por hash de prompt + style
    prompt_hash = hashlib.sha256(
        f"{entry.prompt}{entry.style}".encode()
    ).hexdigest()[:8]

    existing_hashes = {
        r.get("prompt_hash") for r in st.session_state.get("galeria", [])
    }
    if prompt_hash in existing_hashes:
        logger.warning(
            f"[gallery] Entrada duplicada detectada (hash={prompt_hash}). "
            f"No guardada."
        )
        st.toast("⚠️ Esta combinación ya está en la galería.", icon="⚠️")
        return None

    # 3. Construir registro final
    entry_index = len(st.session_state.get("galeria", []))
    record = GalleryRecord(
        entry_id=f"gen_{entry_index:04d}_{prompt_hash}",
        prompt=entry.prompt,
        style=entry.style,
        agent=entry.agent,
        url=entry.url,
        has_bytes=entry.image_bytes is not None,
        is_demo=entry.is_demo,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        prompt_hash=prompt_hash,
    )

    # 4. Guardar bytes por separado en session_state si existen
    if entry.image_bytes is not None:
        if "galeria_bytes" not in st.session_state:
            st.session_state.galeria_bytes = {}
        st.session_state.galeria_bytes[record.entry_id] = entry.image_bytes

    # 5. Insertar al frente
    if "galeria" not in st.session_state:
        st.session_state.galeria = []

    st.session_state.galeria.insert(0, record.to_dict())
    logger.info(
        f"[gallery] Guardado: id={record.entry_id} | "
        f"agent={record.agent} | demo={record.is_demo}"
    )
    return record


# ── Renderizado de imagen en vista ────────────────────────
def render_gallery_image(record: dict[str, Any]) -> None:
    """
    Renderiza la imagen de un GalleryRecord priorizando:
    1. bytes locales (calidad máxima, sin red)
    2. URL remota (CDN / FAL.AI)
    3. Placeholder fijo de demo
    """
    entry_id = record.get("entry_id", "")
    bytes_cache: dict = st.session_state.get("galeria_bytes", {})

    if entry_id in bytes_cache:
        st.image(bytes_cache[entry_id], use_container_width=True)
        return

    url = record.get("url", "")
    if url:
        try:
            st.image(url, use_container_width=True)
        except Exception:
            st.image(DEMO_PLACEHOLDER_URL, use_container_width=True)
        return

    st.image(DEMO_PLACEHOLDER_URL, use_container_width=True)


# ── Helpers ───────────────────────────────────────────────
def clear_gallery() -> None:
    st.session_state.galeria = []
    st.session_state.galeria_bytes = {}
    logger.info("[gallery] Galería limpiada.")


def get_gallery_count() -> int:
    return len(st.session_state.get("galeria", []))