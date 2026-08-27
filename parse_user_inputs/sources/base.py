"""
parse_user_inputs.sources.base
===============================
Basis-Protocol fuer alle Plattform-Reader.
Jede Plattform implementiert scan_inputs() und reconstruct_threads().
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from parse_user_inputs.models import Thread


@runtime_checkable
class PlatformReader(Protocol):
    """
    Jede Plattform-Datei in sources/ muss diese Schnittstelle erfuellen.

    Beispiel::

        # sources/hermes.py
        def scan_inputs() -> list[dict]:
            ...

        def reconstruct_threads() -> list[Thread]:
            ...

        PLATFORM_ID = "hermes"
    """

    PLATFORM_ID: str

    def scan_inputs(self) -> list[dict]:
        """Scannt die Plattform und gibt User-Inputs als Dict-Liste zurueck."""
        ...

    def reconstruct_threads(self) -> list[Thread]:
        """Rekonstruiert vollstaendige Threads (User -> Agent -> Ergebnis)."""
        ...
