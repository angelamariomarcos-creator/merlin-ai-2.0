# backend/agents/git_helper/git_helper.py

import asyncio
import base64
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from backend.config.settings import settings

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("git_helper")

# ── Rutas ─────────────────────────────────────────────────
PROJECT_ROOT = Path("C:/merlin-ai-2.0")
ESTADO_PATH = PROJECT_ROOT / "backend" / "core" / "estado.json"

# ── Configuración lazy write ──────────────────────────────
LAZY_WRITE_DELAY_SECONDS = 5.0
GITHUB_API_BASE = "https://api.github.com"


# ── Resultado de sincronización ───────────────────────────
class SyncResult(BaseModel):
    success: bool
    sha: str = Field(default="")
    commit_url: str = Field(default="")
    timestamp: str = Field(default="")
    error: str = Field(default="")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Agente Git Helper ─────────────────────────────────────
class GitHelper:
    """
    Implementa lazy write asíncrono de estado.json hacia GitHub.
    - Acumula llamadas a schedule_push() dentro de la ventana
      LAZY_WRITE_DELAY_SECONDS y ejecuta un único commit.
    - No bloquea el hilo principal: usa threading.Timer.
    - Thread-safe mediante threading.Lock.
    """

    def __init__(self) -> None:
        self._token: str = settings.GITHUB_TOKEN
        self._owner: str = settings.GITHUB_REPO_OWNER
        self._repo: str = settings.GITHUB_REPO_NAME
        self._branch: str = settings.GITHUB_BRANCH
        self._remote_path: str = settings.GITHUB_ESTADO_PATH

        self._lock = threading.Lock()
        self._pending_timer: threading.Timer | None = None
        self._github_available: bool = self._check_github_config()

    # ── API pública ───────────────────────────────────────

    def schedule_push(self) -> None:
        """
        Programa un push diferido de estado.json.
        Si ya hay uno pendiente, reinicia el temporizador (debounce).
        """
        if not self._github_available:
            logger.warning(
                "[GitHelper] GitHub no configurado. "
                "Define GITHUB_TOKEN, GITHUB_REPO_OWNER y GITHUB_REPO_NAME en .env"
            )
            return

        with self._lock:
            if self._pending_timer is not None:
                self._pending_timer.cancel()

            self._pending_timer = threading.Timer(
                LAZY_WRITE_DELAY_SECONDS,
                self._execute_push
            )
            self._pending_timer.daemon = True
            self._pending_timer.start()
            logger.info(
                f"[GitHelper] Push diferido programado en "
                f"{LAZY_WRITE_DELAY_SECONDS}s."
            )

    def force_push(self) -> SyncResult:
        """Push inmediato y síncrono. Cancela cualquier lazy pendiente."""
        if not self._github_available:
            return SyncResult(
                success=False,
                error="GitHub no configurado en settings."
            )
        with self._lock:
            if self._pending_timer is not None:
                self._pending_timer.cancel()
                self._pending_timer = None

        return asyncio.run(self._push_to_github())

    # ── Ejecución del push ────────────────────────────────

    def _execute_push(self) -> None:
        """Callback del timer. Lanza el push asíncrono en event loop propio."""
        with self._lock:
            self._pending_timer = None
        try:
            result = asyncio.run(self._push_to_github())
            if result.success:
                logger.info(
                    f"[GitHelper] estado.json sincronizado. "
                    f"Commit: {result.commit_url}"
                )
            else:
                logger.error(f"[GitHelper] Fallo en push: {result.error}")
        except Exception as e:
            logger.error(f"[GitHelper] Excepción en _execute_push: {e}")

    async def _push_to_github(self) -> SyncResult:
        """Lógica principal de push hacia la GitHub Contents API."""
        try:
            content_b64, local_sha = self._read_estado_encoded()
        except Exception as e:
            return SyncResult(success=False, error=str(e))

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = (
            f"{GITHUB_API_BASE}/repos/{self._owner}/{self._repo}"
            f"/contents/{self._remote_path}"
        )

        async with httpx.AsyncClient(timeout=15.0) as client:

            # 1. Obtener SHA actual del archivo remoto (necesario para update)
            remote_sha = await self._get_remote_sha(client, url, headers)

            # 2. Construir payload del commit
            commit_message = (
                f"chore(estado): lazy-write sync "
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )
            payload: dict[str, Any] = {
                "message": commit_message,
                "content": content_b64,
                "branch": self._branch,
            }
            if remote_sha:
                payload["sha"] = remote_sha

            # 3. PUT hacia GitHub Contents API
            response = await client.put(url, headers=headers, json=payload)

            if response.status_code in (200, 201):
                data = response.json()
                commit_url = data.get("commit", {}).get("html_url", "")
                return SyncResult(
                    success=True,
                    sha=data.get("content", {}).get("sha", ""),
                    commit_url=commit_url,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            else:
                return SyncResult(
                    success=False,
                    error=(
                        f"GitHub API respondió {response.status_code}: "
                        f"{response.text[:300]}"
                    ),
                )

    async def _get_remote_sha(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
    ) -> str:
        """Obtiene el SHA del archivo remoto. Devuelve '' si no existe aún."""
        try:
            r = await client.get(
                url,
                headers=headers,
                params={"ref": self._branch}
            )
            if r.status_code == 200:
                return r.json().get("sha", "")
            return ""
        except Exception:
            return ""

    # ── Helpers ───────────────────────────────────────────

    def _read_estado_encoded(self) -> tuple[str, str]:
        """Lee estado.json y lo devuelve como (base64_string, sha_local)."""
        if not ESTADO_PATH.exists():
            raise FileNotFoundError(
                f"[GitHelper] estado.json no encontrado en: {ESTADO_PATH}"
            )
        with open(ESTADO_PATH, "r", encoding="utf-8") as f:
            raw = f.read()

        # Validar que es JSON parseable antes de subir
        json.loads(raw)

        encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
        return encoded, ""

    def _check_github_config(self) -> bool:
        return all([
            self._token and self._token.strip(),
            self._owner and self._owner.strip(),
            self._repo and self._repo.strip(),
        ])


# ── Singleton exportable ──────────────────────────────────
git_helper = GitHelper()