# parse_user_inputs — Modular User-Input Parser

Extrahiert echte User-Inputs aus AI-Agent-Sessions und trennt sie von Agent-Halluzinationen.

## Architektur (V5)

```
parse_user_inputs/
├── __init__.py                  # Package + Version
├── __main__.py                  # python -m parse_user_inputs
├── cli.py                       # CLI + Orchestrierung
├── config.py                    # Konfiguration (ENV-Overrides)
├── categorizer.py               # Kategorisierung (rein funktional)
├── sources/
│   ├── state_db.py              # Hermes DB (User/Assistant/Tool/Memory)
│   ├── request_dumps.py         # JSON Dump Reader
│   ├── freebuff_threads.py      # HTTP API Reader
│   ├── paste_images.py          # PNG Metadata Reader
│   └── git_commits.py           # Git Log Reader
├── renderers/
│   ├── markdown.py              # MD-Artefakt
│   ├── html_dashboard.py        # HTML (Jinja2)
│   └── json_output.py           # JSON (Agent-Modus)
├── templates/
│   ├── dashboard.html           # Jinja2 Template
│   ├── dashboard.css            # CSS (Dark-Theme)
│   └── dashboard.js             # Canvas Charts + Interaction
└── tests/
    ├── test_categorizer.py
    ├── test_merge.py
    └── test_config.py
```

## Quick Start

```bash
# Auto-detect Projekt + HTML-Dashboard
python -m parse_user_inputs .

# Bestimmtes Projekt
python -m parse_user_inputs /pfad/zum/projekt

# Nur HTML
python -m parse_user_inputs . --html dashboard.html --output /dev/null

# Nur Markdown
python -m parse_user_inputs . --output artifact.md

# JSON-Output (Agent-Integration)
python -m parse_user_inputs . --json output.json --output /dev/null
```

## Agent-Unabhängigkeit

Jedes Modul kann unabhängig importiert werden:

```python
# Nur Kategorisierung
from parse_user_inputs.categorizer import categorize, is_real_user_input
cats = categorize("Bug im headless Modus")  # ['BUG', 'HEADLESS_VERBOT']

# Nur Datenquellen
from parse_user_inputs.sources import read_state_db
inputs = read_state_db("/path/to/state.db")

# Nur Renderer
from parse_user_inputs.renderers import render_json
render_json(output_path="out.json", project_path=".", unique_inputs=[], ...)

# Gesamte Pipeline als Funktion
from parse_user_inputs.cli import main
result = main([".", "--json", "output.json"])
```

## Konfiguration (ENV-Overrides)

```bash
export USER_INPUTS_DB_PATH=/custom/path/to/state.db
export USER_INPUTS_SESSIONS_DIR=/custom/sessions
export USER_INPUTS_PASTE_DIR=/tmp/pastes
export USER_INPUTS_FREEBUFF_PORT=8080
export USER_INPUTS_SINCE_DATE=2026-08-18
```

## Datenquellen

| Quelle | Modul | Inhalt |
|--------|-------|--------|
| Hermes state.db | `sources/state_db.py` | User-Messages, Assistant-Reasoning, Tool-Outputs |
| Request Dumps | `sources/request_dumps.py` | API-Error-Snapshots |
| Freebuff Threads | `sources/freebuff_threads.py` | User-Inputs via Orchestrator API |
| Paste-PNGs | `sources/paste_images.py` | Screenshots mit Metadaten |
| Git-Commits | `sources/git_commits.py` | Rekonstruierte User-Intentionen |

## Tests

```bash
# Alle Tests
python -c "from parse_user_inputs.tests import test_categorizer, test_merge, test_config; ..."

# Oder inline
python -m parse_user_inputs.tests.test_categorizer
```

## Dashboard-Sektionen

1. **Stats-Cards** — User-Inputs, Assistant-Snippets, Commits, PNGs, Memory
2. **Memory-Volumen-Analyse** — Donut-Chart + Session-Table
3. **Kategorie-Balken** — User-Intentionen nach Topic
4. **Aktivitäts-Chart** — Commits pro Tag
5. **Tool-Nutzungs-Statistik** — Aufrufe + Daten pro Tool
6. **Top Reasoning-Snippets** — Assistant-Entscheidungen
7. **Commit-Timeline** — Alle Commits nach Datum
8. **Paste-PNG Grid** — Thumbnails mit Klick-zu-Modal
9. **User-Inputs Liste** — Durchsuchbar, filterbar, expandierbar
