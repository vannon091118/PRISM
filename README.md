<p align="center">
  <img src="assets/banner.svg" alt="PRISM — Platform Recognition & Input Session Miner" width="100%">
</p>

<p align="center">
  <strong>P</strong>latform <strong>R</strong>ecognition &amp; <strong>I</strong>nput <strong>S</strong>ession <strong>M</strong>iner<br>
  <em>Die hastigen Eingaben von 15 AI-Coding-Agenten in ein kohärentes Dashboard verwandelt.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-6.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-purple" alt="License">
  <img src="https://img.shields.io/badge/platforms-12+-orange" alt="Platforms">
</p>

---

## Was ist PRISM?

Stell dir vor, du hast 15 AI-Coding-Agenten installiert. Nicht weil du sie brauchst, sondern weil jeder mal "interessant" klang. Claude Code, Gemini, Hermes, Codex, Freebuff, Cursor, Cline, Roo, Kilo, OpenHands, Amp, Aider, Goose, Kiro... Jeder speichert seine Daten irgendwo anders. Manche in SQLite, manche in JSONL, manche in Protobuf-Blobs, manche in `~/.config/manicode/` — weil der Entwickler mal "Manicode" hiess und den Namen nie geaendert hat.

PRISM ist die Antwort auf eine Frage, die niemand gestellt hat: *"Was wenn ich ALLE meine AI-Sessions in einem Dashboard sehen koennte?"*

Die Antwort ist: Es waere ein chaosfarbenes Pie-Chart mit zu vielen Datenpunkten. Also haben wir PRISM gebaut.

---

## Dashboard-Vorschau

<p align="center">
  <img src="docs/screenshots/canvas-preview.png" alt="Canvas Dashboard" width="100%">
  <br>
  <em>Interaktives Canvas-Dashboard mit Pie-Chart-Bubbles und Drill-Down Navigation</em>
</p>

PRISM generiert interaktive Dashboards in verschiedenen Ansichten:

| Dashboard | Beschreibung | Vorschau |
|-----------|-------------|----------|
| **Canvas** | Pie-Charts als Bubbles, Drill-Down, Git-Integration | [Öffnen](docs/screenshots/canvas-preview.html) |
| **Threads** | Kategorisierte Thread-Ansicht mit Filtern | [Öffnen](docs/screenshots/threads-preview.html) |
| **User Inputs** | Detaillierte User-Input-Analyse mit Charts | [Öffnen](docs/screenshots/user-inputs-preview.html) |

### Features

- 🎯 **Pie-Chart-Bubbles** pro Projekt (Kategorie-Verteilung)
- 🔍 **Drill-Down** von Projekt → Threads → Messages
- 🏷️ **COMMIT/PR/BRANCH-Badges** für jeden Thread
- 🔗 **Git-Integration** mit automatischem Matching
- 📊 **12 dedizierte Plattform-Reader** (kein Generic-Fallback)
- 🧹 **Fuzzy-Deduplizierung** via SimHash + Jaccard
- 📈 **Memory-Volumen-Analyse** (User vs. Assistant vs. Tool)
- ⏱️ **Commit-Timeline** mit automatischer Korrelation

---

## Plattformen

PRISM erkennt automatisch, welche Plattformen installiert sind:

| Plattform | Status | Daten |
|-----------|--------|-------|
| Freebuff | ✅ | User→Agent→Tool, PRs, Branches |
| Claude Code | ✅ | User-Inputs (history.jsonl) |
| Gemini CLI | ✅ | User-Inputs (history.jsonl) |
| Gemini Desktop | ✅ | Protobuf-decoded Sessions |
| Hermes | ✅ | User→Agent (state.db) |
| Codex | ✅ | User-Inputs + Sessions |
| Cursor | ✅ | agentKv blobs (state.vscdb) |
| Kilo Code | ✅ | 3-Table-JOIN (session+message+part) |
| Cline | ✅ | Task JSON (nicht installiert) |
| Roo Code | ✅ | Task JSON (nicht installiert) |
| Copilot | ✅ | Chat JSON + OTEL (nicht installiert) |
| Aider | ✅ | Markdown History (nicht installiert) |

---

## Schnellstart

```bash
# Klonen und installieren
git clone https://github.com/vannon091118/PRISM.git
cd PRISM
pip install jinja2  # Optional, für volle Visualisierung

# Welche Plattformen sind installiert?
python -m parse_user_inputs --discover

# Canvas-Dashboard generieren
python -m parse_user_inputs --canvas --html dashboard.html

# Thread-Ansicht generieren
python -m parse_user_inputs --threads --html threads.html

# User-Inputs Dashboard
python -m parse_user_inputs --html user_inputs.html
```

<p align="center">
  <img src="docs/screenshots/threads-preview.png" alt="Threads Dashboard" width="100%">
  <br>
  <em>Thread-Ansicht mit Kategorien, Plattformen und Filtern</em>
</p>

---

## Architektur

```
parse_user_inputs/
├── cli.py                 # ~80 Zeilen, delegiert an modes/
├── config.py              # Portabel — keine hardcoded Pfade
├── categorizer.py         # 18 Kategorien mit Negative-Keywords
├── models.py              # Thread + Message Dataclasses
├── platforms.py           # 34 Plattform-Definitionen
├── sorting.py             # Fuzzy-Dedup (SimHash + Jaccard)
│
├── sources/               # Je eine Datei pro Plattform
│   ├── hermes.py          # state.db JOIN
│   ├── freebuff.py        # API + PRs + Branches
│   ├── claude_code.py     # history.jsonl
│   ├── kilo_code.py       # 3-Table-JOIN (!)
│   ├── git_reader.py      # Git-Commits + Matching
│   └── ...               # 12 Module total
│
├── renderers/             # HTML, Canvas, Markdown, JSON
├── modes/                 # threads, scan, project
├── templates/             # Canvas-Dashboard (standalone)
└── tests/                 # 52 Tests
```

<p align="center">
  <img src="docs/screenshots/user-inputs-preview.png" alt="User Inputs Dashboard" width="100%">
  <br>
  <em>User-Inputs Dashboard mit Memory-Analyse, Charts und Reasoning-Snippets</em>
</p>

---

## Warum "PRISM"?

Weil ein Prisma Licht nimmt und in ein Spektrum bricht.

PRISM nimmt die chaotische Masse an Session-Logs, Datenbanken
und Chat-History-Dateien aus 12+ Plattformen und bricht sie
in sauber kategorisierte, farbcodierte, interaktive Visualisierungen.

Und weil der Name kurz, einpraegsam und nicht
`AISessionParser3000ProMaxUltra` heisst.

---

## Selbstironischer Disclaimer

PRISM wurde gebaut, um die eigene Produktivitaet zu steigern.
Die Ironie: Die meiste Zeit wurde damit verbracht, PRISM selbst
zu bauen, anstatt die eigentlichen Projekte fertigzustellen.

Das ist wie ein Schreiner, der ein perfektes Werkzeug-Regal baut,
statt das Regal zu bauen, fuer das er die Werkzeuge braucht.

Aber immerhin sieht das Dashboard jetzt gut aus.

---

## License

MIT — weil die Welt genug proprietäre AI-Tools hat.
