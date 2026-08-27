"""
parse_user_inputs.scanner
=========================
Thin wrapper — delegiert an sources/ Registry.

Alle Plattform-spezifische Logik lebt jetzt in:
  - sources/hermes.py
  - sources/freebuff.py
  - sources/claude_code.py
  - sources/codex.py
  - sources/cursor.py
  - sources/gemini_cli.py
  - sources/aider.py
  - sources/vscode_extensions.py
"""

from __future__ import annotations

from typing import Any

from parse_user_inputs.sources import (
    scan_all_inputs,
    scan_all_threads,
    discover_installed,
    print_discovery,
)


# Legacy-API: scan_all_platforms delegiert an scan_all_inputs
def scan_all_platforms(
    platform_filter: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Scannt alle Plattformen. Wrapper fuer Abwaertskompatibilitaet."""
    return scan_all_inputs(platform_filter)


# Legacy-API: discover_platforms delegiert an discover_installed
def discover_platforms() -> list[dict[str, Any]]:
    """Findet installierte Plattformen. Wrapper fuer Abwaertskompatibilitaet."""
    return discover_installed()
