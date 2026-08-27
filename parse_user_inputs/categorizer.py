"""
parse_user_inputs.categorizer
=============================
Text-Kategorisierung und User-Input-Validierung.
Rein funktional — keine Abhaengigkeiten von IO oder Config.

Verbesserungen:
  - Multi-Word Keywords fuer Praezision
  - Negative Keywords (Falsch-Treffer vermeiden)
  - Context-Aware Matching (Umkontext beruecksichtigen)
  - Neue Kategorien: GIT, ARCHITEKTUR, PERFORMANCE, CONFIG
"""

from __future__ import annotations

import re


# ─── Kategorie-Definitionen ─────────────────────────────────────────────────
#
# Jede Kategorie hat:
#   keywords:    Liste von Strings/Patterns die im Text vorkommen mueussen
#   phrases:     Multi-Word Phrases (hoehere Praezision)
#   negative:    Keywords die einen Treffer AUFHEBEN
#   min_matches: Mindestanzahl an Treffern fuer diese Kategorie

CATEGORIES: dict[str, dict] = {
    "MCP_ADDON": {
        "keywords": ["mcp", "addon", "plugin"],
        "phrases": [
            "addon bauen", "plugin bauen", "mcp server", "mcp tool",
            "eigenes addon", "eigenes modul", "marketplace",
            "modul hinzufuegen", "modul erstellen",
        ],
        "negative": ["modulImport", "modul system"],
    },
    "ENTKOPPELUNG": {
        "keywords": ["entkoppel", "standalone", "portabel", "portable"],
        "phrases": [
            "project agnostic", "project-agnostic", "eigenes repo",
            "snipwar entkoppel", "vermischt", "eigenes projekt",
            "automatisch registri",
        ],
        "negative": [],
    },
    "HEADLESS_VERBOT": {
        "keywords": ["headless"],
        "phrases": [
            "nur sichtbar", "visible only", "sichtbar ist valide",
            "hedless", "heless", "headless verbot",
            "kein headless", "nicht headless",
        ],
        "negative": [],
    },
    "GAMEPLAY": {
        "keywords": ["spielbar", "playthrough", "tutorial"],
        "phrases": [
            "3 planeten", "ressourcenket", "erstes schiff",
            "schiff bauen", "werft", "forschung", "orbitale",
            "durchspielen", "result=fail", "gameplay loop",
            "planet entdeck", "fleet", "combat system",
            "missions", "quest", "story",
        ],
        "negative": [
            "sichtbar ist", "sichtbar machen", "sichtbar werden",
            "sichtbarkeit", "im sichtbaren",
        ],
    },
    "QA_TEST": {
        "keywords": ["preflight", "audit", "finding", "findings"],
        "phrases": [
            "test runner", "contract test", "constraint check",
            "qa pruef", "qa check", "autonom test",
            "integration test", "unit test", "e2e test",
            " regression ", " test suite",
        ],
        "negative": [
            "test theo", "test daten", "test eingabe",
        ],
    },
    "BUG": {
        "keywords": ["bug", "fehler", "kaputt", "broken", "crash"],
        "phrases": [
            "nicht funktioniert", "schlaegt fehl", "error occured",
            "exception", "traceback", "segfault", "null pointer",
            "index out of", "connection refused",
        ],
        "negative": [],
    },
    "DOKU": {
        "keywords": ["doku", "dokument", "readme", "handoff"],
        "phrases": [
            "dokumentation", "erklarung", "hinweis schreib",
            "readme schreib", "readme aktualisier",
            "docu", "anleitung", "anweisung",
        ],
        "negative": [
            "doc string", "docstring",
        ],
    },
    "REFACTOR": {
        "keywords": ["refactor", "umbau", "umstrukturier", "cleanup"],
        "phrases": [
            "aufräumen", "separation of concern",
            "code smell", "technical debt", "schlanker",
            "struktur verbesser",
        ],
        "negative": [],
    },
    "FEATURE": {
        "keywords": ["feature"],
        "phrases": [
            "neu bauen", "neues tool", "neue tool",
            "ergaenzung", "erweiterung", "hinzufuegen",
            "neue funktion", "neues feature",
            "funktionalitaet",
        ],
        "negative": [
            "feature branch",
        ],
    },
    "SERVER_START": {
        "keywords": ["server starten", "server einrichten"],
        "phrases": [
            "port 9090", "port 9091", "port 8080", "port 3000",
            "server hochfahren", "server start",
            "localhost", "127.0.0.1",
        ],
        "negative": [
            "port forwarding", "port number",
        ],
    },
    "COST": {
        "keywords": ["budget", "kosten", "preis"],
        "phrases": [
            "token cost", "token verbrauch", "modell kosten",
            "nvidia", "deepseek", "glm", "cost per",
            "api kosten", "rate limit",
        ],
        "negative": [],
    },
    "SUCHSYSTEM": {
        "keywords": ["grep", "ripgrep", "concept index"],
        "phrases": [
            "global search", "global_search", "concept_index",
            "volltextsuche", "indexed search",
            "suche einbauen", "suche implementier",
        ],
        "negative": [
            "find file", "find function", "find variable",
        ],
    },
    "REMOTE_CONTROL": {
        "keywords": ["remote control", "remote-control"],
        "phrases": [
            "live test", "e2e test", "playthrough test",
            "debugging session", "remote debugging",
            "fernsteuerung",
        ],
        "negative": [
            "remote repository", "remote branch", "git remote",
        ],
    },
    "GIT": {
        "keywords": ["git"],
        "phrases": [
            "git commit", "git push", "git pull", "git merge",
            "git branch", "git checkout", "git rebase",
            "git diff", "git status", "git log",
            "merge conflict", "branch erstell",
            "pre-merge", "premerge",
        ],
        "negative": [
            "github copilot", "github extension",
        ],
    },
    "ARCHITEKTUR": {
        "keywords": ["architektur", "modular"],
        "phrases": [
            "modul struktur", "modul system", "trennung",
            "separation of concern", "dependency injection",
            "layer architecture", "schichten architektur",
            "code struktur", "projekt struktur",
            "package struktur",
        ],
        "negative": [],
    },
    "PERFORMANCE": {
        "keywords": ["performance", "langsam", "optimierung"],
        "phrases": [
            "geschwindigkeit", "verzoegerung", "latenz",
            "speicher verbrauch", "memory leak",
            "cpu auslastung", "rendering performance",
            "frame rate", "fps",
        ],
        "negative": [],
    },
    "CONFIG": {
        "keywords": ["config", "konfiguration", "einstellung"],
        "phrases": [
            "settings ändern", "einstellung anpass",
            "umgebungsvariable", "env variable",
            "config datei", "config bearbeit",
        ],
        "negative": [
            "config reader", "config parser",
        ],
    },
}


# ─── Kernfunktionen ──────────────────────────────────────────────────────────

def categorize(text: str) -> list[str]:
    """
    Weist Text einer oder mehreren Kategorien basierend auf Keywords zu.

    Verbesserte Logik:
      1. Prueft negative Keywords (verhindert False Positives)
      2. Prueft Multi-Word Phrases (hoechste Praezision)
      3. Prueft Single-Keywords (fallback)
      4. Mindestens 1 Treffer pro Kategorie noetig
    """
    if not text:
        return ["UNCATEGORIZED"]

    text_lower = text.lower()
    cats: list[str] = []

    for cat, definition in CATEGORIES.items():
        keywords = definition.get("keywords", [])
        phrases = definition.get("phrases", [])
        negative = definition.get("negative", [])

        # Negative Keywords pruefen — wenn getroffen, Kategorie ueberspringen
        if negative and any(neg in text_lower for neg in negative):
            continue

        matched = False

        # Zuerst Phrases pruefen (hoechste Praezision)
        for phrase in phrases:
            if phrase in text_lower:
                matched = True
                break

        # Dann Single-Keywords
        if not matched:
            for kw in keywords:
                # Wortgrenzen-Check fuer kurze Keywords (3-4 Zeichen)
                if len(kw) <= 4:
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                        matched = True
                        break
                else:
                    if kw in text_lower:
                        matched = True
                        break

        if matched:
            cats.append(cat)

    return cats if cats else ["UNCATEGORIZED"]


def is_real_user_input(content: str) -> bool:
    """
    Prueft ob ein Content echte User-Eingabe ist (keine System-Init,
    keine Skill-Invocation, keine Agent-Antwort).
    """
    if not content or not content.strip():
        return False

    c = content.strip()

    # System-Initialisierung
    if c.startswith("[/init]"):
        return False
    # Skill-Invocation
    if c.startswith("[IMPORTANT: The user has invoked"):
        return False
    # Agent-Intros
    if c.lower().startswith("here's a thinking process"):
        return False
    # Interrupts
    if c.startswith("⚡ Interrupt"):
        return False
    # Auto-Continue
    if c.startswith("continue working toward"):
        return False
    # Modell-Switch
    if c.startswith("[Note: model was just switched"):
        return False
    # Response-Cutoff
    if c.startswith("[System: The previous response was cut off"):
        return False
    # Context-Reinjection
    if c.startswith("[Context from the interrupted"):
        return False
    # Kurze Blockquotes (oft Agent-Output)
    if c.startswith("> ") and len(c) < 100:
        return False
    # Nur Befehle (ohne Inhalt)
    if re.match(r'^/[a-z\-]+$', c):
        return False
    # reine Zahlen
    if re.match(r'^[\d\s\.\,\-]+$', c):
        return False

    return True


def is_project_session(title: str, model: str, content: str) -> bool:
    """Prueft ob eine Session zum Projekt gehoert (Marker-basiert)."""
    combined = f"{title or ''} {model or ''} {content or ''}".lower()
    markers = [
        "snip", "mcp", "preflight", "playthrough", "goal_player",
        "runtime_", "headless", "visible", "autonomy", "contract",
        "dossier", "forschung", "werft", "schiff", "planet", "fleet",
        "combat", "godot", "gdscript", "addon", "plugin",
    ]
    return any(m in combined for m in markers)


# ─── Legacy-Kompatibilitaet ──────────────────────────────────────────────────

def get_category_keywords() -> dict[str, list[str]]:
    """Gibt Keyword-Listen zur Kompatibilitaet zurueck."""
    result = {}
    for cat, definition in CATEGORIES.items():
        all_kw = list(definition.get("keywords", []))
        all_kw.extend(definition.get("phrases", []))
        result[cat] = all_kw
    return result
