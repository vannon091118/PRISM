"""
PRISM — Platform Recognition & Input Session Miner
====================================================
Brech散t verstreute User-Inputs aus 30+ AI-Agent-Plattformen
in ein kohaerentes, durchsuchbares Dashboard.

Vergleichbar mit einem physikalischen Prisma, das weisses Licht
in seinen Farbspektrum bricht — PRISM nimmt die chaotische Masse
an Session-Logs, Datenbanken und Chat-History-Dateien und zerlegt sie
in sauber kategorisierte, farbcodierte, interaktive Visualisierungen.

Oeffentliche API:
    from parse_user_inputs.config import Config
    from parse_user_inputs.categorizer import categorize, is_real_user_input
    from parse_user_inputs.sources import scan_all_threads, scan_all_inputs
    from parse_user_inputs.models import Thread, Message
    from parse_user_inputs.renderers import render_markdown, render_html_dashboard, render_json

CLI:
    python -m parse_user_inputs --discover             # Installierte Plattformen finden
    python -m parse_user_inputs --threads --html out.html  # Thread-Dashboard
    python -m parse_user_inputs --canvas --html out.html   # Canvas-Dashboard
    python -m parse_user_inputs --scan-all             # Alle Plattformen scannen
"""

__version__ = "6.0.0"
__codename__ = "PRISM"
__acronym__ = "Platform Recognition & Input Session Miner"
