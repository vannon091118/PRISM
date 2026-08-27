"""parse_user_inputs.cli
=====================
CLI-Wrapper mit Argument-Parsing und Delegation an modes/.

Usage:
    python -m parse_user_inputs                          # auto-detect project
    python -m parse_user_inputs /path/to/project
    python -m parse_user_inputs . --html out.html --output out.md
    python -m parse_user_inputs . --json out.json         # Agent JSON-Modus

Multi-Plattform Scan:
    python -m parse_user_inputs --scan-all               # Alle Plattformen scannen
    python -m parse_user_inputs --scan-all --html out.html
    python -m parse_user_inputs --platforms claude_code,codex
    python -m parse_user_inputs --list-platforms          # Alle Plattformen auflisten
    python -m parse_user_inputs --discover                # Installierte finden

Env-Variablen:
    USER_INPUTS_DB_PATH        Pfad zur Hermes state.db
    USER_INPUTS_SESSIONS_DIR   Pfad zum Sessions-Verzeichnis
    USER_INPUTS_PASTE_DIR      Pfad zum Paste-PNG-Verzeichnis
    USER_INPUTS_PROJECT_PATH   Pfad zum Projekt
    USER_INPUTS_OUTPUT_MD      Pfad zum Markdown-Output
    USER_INPUTS_OUTPUT_HTML    Pfad zum HTML-Output
    USER_INPUTS_OUTPUT_JSON    Pfad zum JSON-Output
    USER_INPUTS_SCAN_ALL       1 = Multi-Plattform Scan aktivieren
    USER_INPUTS_PLATFORMS      Komma-getrennte Plattform-Filter
"""

from __future__ import annotations

import sys

from parse_user_inputs.config import Config


def _parse_args(argv: list[str]) -> dict[str, str]:
    """Parst CLI-Argumente in ein Dict."""
    args: dict[str, str] = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--output" and i + 1 < len(argv):
            args["output"] = argv[i + 1]; i += 2
        elif argv[i] == "--html" and i + 1 < len(argv):
            args["html"] = argv[i + 1]; i += 2
        elif argv[i] == "--json" and i + 1 < len(argv):
            args["json"] = argv[i + 1]; i += 2
        elif argv[i] == "--hermes-db" and i + 1 < len(argv):
            args["db_path"] = argv[i + 1]; i += 2
        elif argv[i] == "--sessions-dir" and i + 1 < len(argv):
            args["sessions_dir"] = argv[i + 1]; i += 2
        elif argv[i] == "--project-filter" and i + 1 < len(argv):
            args["project_filter"] = argv[i + 1]; i += 2
        elif argv[i] == "--threads":
            args["threads"] = "1"; i += 1
        elif argv[i] == "--scan-all":
            args["scan_all"] = "1"; i += 1
        elif argv[i] == "--canvas":
            args["canvas"] = "1"; i += 1
        elif argv[i] == "--platforms" and i + 1 < len(argv):
            args["platforms"] = argv[i + 1]; i += 2
        elif argv[i] == "--list-platforms":
            args["list_platforms"] = "1"; i += 1
        elif argv[i] == "--discover":
            args["discover"] = "1"; i += 1
        elif argv[i] in ("--help", "-h"):
            print(__doc__); sys.exit(0)
        elif not argv[i].startswith("-"):
            args["project_path"] = argv[i]; i += 1
        else:
            i += 1
    return args


def main(argv: list[str] | None = None):
    """Hauptfunktion: Parst Argumente und delegiert an den passenden Modus."""
    if argv is None:
        argv = sys.argv[1:]

    raw_args = _parse_args(argv)
    cfg = Config()

    # ─── Spezial-Modi ────────────────────────────────────────────────────

    if raw_args.get("list_platforms"):
        from parse_user_inputs.platforms import list_platforms
        for p in list_platforms():
            print(f"  {p['id']:20s} {p['name']:25s} {p['vendor']:20s} {p['description']}")
        return

    if raw_args.get("discover"):
        from parse_user_inputs.sources import print_discovery
        print_discovery()
        return

    # ─── Modus bestimmen ─────────────────────────────────────────────────

    scan_all = raw_args.get("scan_all") == "1" or cfg.scan_all
    platform_filter = None
    if "platforms" in raw_args:
        platform_filter = [p.strip() for p in raw_args["platforms"].split(",")]
    elif cfg.get_platform_filter():
        platform_filter = cfg.get_platform_filter()

    # --canvas: Visuelles Canvas-Dashboard
    if raw_args.get("canvas"):
        from parse_user_inputs.modes import run_threads_mode
        return run_threads_mode(cfg, raw_args, canvas=True)

    # --threads: Thread-basierte Ansicht
    if raw_args.get("threads") or raw_args.get("scan_all"):
        from parse_user_inputs.modes import run_threads_mode
        return run_threads_mode(cfg, raw_args)

    if scan_all or platform_filter:
        from parse_user_inputs.modes import run_scan_mode
        return run_scan_mode(cfg, raw_args, scan_all, platform_filter)

    # ─── Klassischer Projekt-Modus ──────────────────────────────────────
    from parse_user_inputs.modes import run_project_mode
    return run_project_mode(cfg, raw_args)
