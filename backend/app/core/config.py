"""Configurazione locale tramite variabili d'ambiente e percorsi relativi."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "database" / "fantacalcio.db"


def database_url() -> str:
    """Restituisce l'URL SQLAlchemy, con SQLite locale come default."""

    configured = os.getenv("FANTACALCIO_DATABASE_URL")
    if configured:
        return configured
    return f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"

