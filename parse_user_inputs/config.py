"""
parse_user_inputs.config
========================
Zentrale Konfiguration fuer alle Pfade und Parameter.
Portabel: keine hardcoded Pfade, alles via ENV oder automatische Erkennung.

Env-Variablen:
    USER_INPUTS_DB_PATH        — Pfad zur Hermes state.db
    USER_INPUTS_SESSIONS_DIR   — Pfad zum Sessions-Verzeichnis
    USER_INPUTS_PASTE_DIR      — Pfad zum Paste-PNG-Verzeichnis
    USER_INPUTS_PROJECT_PATH   — Pfad zum Projekt
    USER_INPUTS_OUTPUT_MD      — Pfad zum Markdown-Output
    USER_INPUTS_OUTPUT_HTML    — Pfad zum HTML-Output
    USER_INPUTS_OUTPUT_JSON    — Pfad zum JSON-Output
    USER_INPUTS_FREEBUFF_PORT  — Port der Freebuff Desktop API
    USER_INPUTS_SINCE_DATE     — Git-Log Startdatum (YYYY-MM-DD)
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    """Liest einen ENV-Wert oder gibt den Default zurueck."""
    return os.environ.get(name, default)


def _home() -> Path:
    """Gibt das Home-Verzeichnis zurueck (portabel)."""
    return Path.home()


def _config_dir() -> Path:
    """Gibt das Config-Verzeichnis zurueck (XDG oder Plattform-spezifisch)."""
    if sys.platform == "win32":
        return _home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        return _home() / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(_home() / ".config"))
        return Path(xdg)


def _data_dir() -> Path:
    """Gibt das Data-Verzeichnis zurueck (XDG oder Plattform-spezifisch)."""
    if sys.platform == "win32":
        return _home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        return _home() / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_DATA_HOME", str(_home() / ".local" / "share"))
        return Path(xdg)


# ─── Plattform-abhanguenige Defaults ─────────────────────────────────────────

def _default_hermes_db() -> str:
    """Findet Hermes state.db automatisch."""
    candidates = [
        _data_dir() / "hermes" / "state.db",
        _home() / ".hermes" / "state.db",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # Fallback: erstes das existiert
    return str(_data_dir() / "hermes" / "state.db")


def _default_sessions_dir() -> str:
    """Findet Hermes Sessions-Verzeichnis automatisch."""
    candidates = [
        _data_dir() / "hermes" / "sessions",
        _home() / ".hermes" / "sessions",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(_data_dir() / "hermes" / "sessions")


def _default_paste_dir() -> str:
    """Findet Freebuff Paste-Verzeichnis automatisch."""
    return str(Path(tempfile.gettempdir()) / "freebuff-desktop-pastes")


# ─── Konfigurations-Datenclass ──────────────────────────────────────────────

@dataclass(frozen=False)
class Config:
    """Zentrale Konfiguration. Portabel, ENV-ueberschreibbar."""

    # Pfade (alle ENV-ueberschreibbar)
    db_path: str = field(default_factory=lambda: _env("USER_INPUTS_DB_PATH", _default_hermes_db()))
    sessions_dir: str = field(default_factory=lambda: _env("USER_INPUTS_SESSIONS_DIR", _default_sessions_dir()))
    paste_dir: str = field(default_factory=lambda: _env("USER_INPUTS_PASTE_DIR", _default_paste_dir()))
    project_path: str = field(default_factory=lambda: _env("USER_INPUTS_PROJECT_PATH", ""))
    output_md: str = field(default_factory=lambda: _env("USER_INPUTS_OUTPUT_MD", ""))
    output_html: str = field(default_factory=lambda: _env("USER_INPUTS_OUTPUT_HTML", ""))
    output_json: str = field(default_factory=lambda: _env("USER_INPUTS_OUTPUT_JSON", ""))

    # Freebuff Desktop API
    freebuff_api_host: str = field(default_factory=lambda: _env("USER_INPUTS_FREEBUFF_HOST", "127.0.0.1"))
    freebuff_api_port: int = field(default_factory=lambda: int(_env("USER_INPUTS_FREEBUFF_PORT", "55703")))

    # Git
    since_date: str = field(default_factory=lambda: _env("USER_INPUTS_SINCE_DATE", ""))

    # Scan-Modus
    scan_all: bool = field(default_factory=lambda: _env("USER_INPUTS_SCAN_ALL", "") == "1")
    platform_filter: str = field(default_factory=lambda: _env("USER_INPUTS_PLATFORMS", ""))

    # Default Output-Dateiname
    default_output_filename: str = "PRISM_OUTPUT.md"
    default_html_filename: str = "PRISM_DASHBOARD.html"
    default_json_filename: str = "PRISM_OUTPUT.json"

    def resolve_project_path(self) -> str:
        """Findet das Projekt automatisch, wenn nicht gesetzt."""
        if self.project_path:
            return self.project_path
        for candidate in [Path.cwd(), Path.cwd().parent]:
            if (candidate / ".git").exists() or (candidate / "project.godot").exists():
                return str(candidate)
        return str(Path.cwd())

    def resolve_output_paths(self, project_path: str) -> dict[str, str]:
        """Loest alle Output-Pfade auf."""
        pp = Path(project_path)
        return {
            "md": self.output_md or str(pp / self.default_output_filename),
            "html": self.output_html or str(pp / self.default_html_filename),
            "json": self.output_json or str(pp / self.default_json_filename),
        }

    @property
    def freebuff_api_url(self) -> str:
        return f"http://{self.freebuff_api_host}:{self.freebuff_api_port}"

    def get_platform_filter(self) -> list[str] | None:
        """Gibt die Plattform-Filter als Liste zurueck oder None fuer alle."""
        if self.platform_filter:
            return [p.strip() for p in self.platform_filter.split(",") if p.strip()]
        return None
