# ◈ PRISM

**P**latform **R**ecognition & **I**nput **S**ession **M**iner

> *Ein Tool, das seine eigene Existenz bereut — aber trotzdem funktioniert.*

---

## Was ist PRISM?

Stell dir vor, du hast 15 AI-Coding-Agenten installiert. Nicht weil du sie brauchst, sondern weil jeder mal "interessant" klang. Claude Code, Gemini, Hermes, Codex, Freebuff, Cursor, Cline, Roo, Kilo, OpenHands, Amp, Aider, Goose, Kiro... Jeder speichert seine Daten irgendwo anders. Manche in SQLite, manche in JSONL, manche in Protobuf-Blobs, manche in `~/.config/manicode/` — weil der Entwickler mal "Manicode" hiess und den Namen nie geaendert hat.

PRISM ist die Antwort auf eine Frage, die niemand gestellt hat: *"Was wenn ich ALLE meine AI-Sessions in einem Dashboard sehen koennte?"*

Die Antwort ist: Es waere ein chaosfarbenes Pie-Chart mit zu vielen Datenpunkten. Also haben wir PRISM gebaut.

---

## Das Dashboard

PRISM generiert ein interaktives Canvas-Dashboard. So sieht es aus:

```
┌─────────────────────────────────────────────────────────┐
│  ◈ PRISM          341    207    6    10    60.7%        │
│                  Threads Beantwortet Offen Interrupts   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    ╭─────╮         Pie-Charts als Bubbles              │
│    │█████│ ← snip-war (109 Threads)                    │
│    │█░░██│   Gruen = committed                          │
│    ╰─────╯   Lila = pending                            │
│                                                         │
│  ◇ PR  MERGED    #4 "Preflight Hardening"              │
│  ◇ PR  MERGED    #3 "MCP-Server Performance"           │
│  ◇ COMMIT  59ed222 feat: add character dialogue        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [Uebersicht] [Projekte] [Zeitstrahl] [Integritaet]    │
└─────────────────────────────────────────────────────────┘
```

Features:
- **Pie-Chart-Bubbles** pro Projekt (Kategorie-Verteilung)
- **Drill-Down** von Projekt → Threads → Messages
- **COMMIT/PR/BRANCH-Badges** fuer jeden Thread
- **Git-Integration** mit automatischem Matching
- **12 dedizierte Plattform-Reader** (kein Generic-Fallback)
- **Fuzzy-Deduplizierung** via SimHash + Jaccard

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
git clone https://github.com/vannon091118/PRISM.git
cd PRISM
pip install jinja2  # Optional, fuer volle Visualisierung

# Was ist installiert?
python -m parse_user_inputs --discover

# Dashboard generieren
python -m parse_user_inputs --canvas --html dashboard.html

# Thread-Ansicht
python -m parse_user_inputs --threads --html threads.html
```

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
