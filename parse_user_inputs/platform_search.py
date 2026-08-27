"""
parse_user_inputs.platform_search
==================================
Globale Suchlogik fuer alle Plattform-Daten.
Ersetzt hardcoded Pfade durch portale Suchalgorithmen.

Unterstuetzt:
  - Windows: %APPDATA%, %LOCALAPPDATA%, %USERPROFILE%
  - macOS: ~/Library/Application Support, ~/Library/Caches
  - Linux: ~/.config, ~/.local/share, $XDG_*

Sucht nach:
  - Datenbanken (SQLite, JSONL)
  - Konfigurationsverzeichnissen
  - Session-Logs
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator


def get_home() -> Path:
    """Portales Home-Verzeichnis."""
    return Path.home()


def get_config_dirs() -> list[Path]:
    """Gibt alle Config-Verzeichnisse zurueck (plattform-abhaengig)."""
    home = get_home()
    dirs = []
    
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        localappdata = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        dirs.extend([
            Path(appdata),
            Path(localappdata),
            home,
        ])
    elif sys.platform == "darwin":
        dirs.extend([
            home / "Library" / "Application Support",
            home / "Library" / "Caches",
            home,
        ])
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
        xdg_data = os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
        dirs.extend([
            Path(xdg_config),
            Path(xdg_data),
            home / ".config",
            home / ".local" / "share",
            home,
        ])
    
    return dirs


def get_data_dirs() -> list[Path]:
    """Gibt alle Daten-Verzeichnisse zurueck."""
    home = get_home()
    dirs = []
    
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        dirs.extend([
            Path(localappdata),
            home,
        ])
    elif sys.platform == "darwin":
        dirs.extend([
            home / "Library" / "Application Support",
            home / "Library" / "Caches",
            home,
        ])
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
        dirs.extend([
            Path(xdg_data),
            home / ".local" / "share",
            home,
        ])
    
    return dirs


# ─── Plattform-spezifische Suchmuster ──────────────────────────────────────

PLATFORM_SEARCH_PATTERNS: dict[str, list[str]] = {
    "claude_code": [
        "~/.claude/history.jsonl",
        "~/.claude/projects",
        "~/.claude/settings.json",
        "%APPDATA%/Claude",
    ],
    "claude_desktop": [
        "%APPDATA%/Claude",
        "~/Library/Application Support/Claude",
    ],
    "gemini_cli": [
        "~/.gemini/antigravity-cli/history.jsonl",
        "~/.gemini/antigravity-cli/conversations",
        "$GEMINI_CLI_HOME",
    ],
    "gemini_desktop": [
        "~/.gemini/antigravity/conversations",
        "~/.gemini/antigravity/annotations",
    ],
    "codex": [
        "~/.codex/sessions",
        "~/.codex/history.jsonl",
        "~/.codex/state_5.sqlite",
    ],
    "codex_desktop": [
        "%LOCALAPPDATA%/Codex",
        "~/Library/Application Support/Codex",
    ],
    "cursor": [
        "~/.cursor/User/globalStorage/state.vscdb",
        "%APPDATA%/Cursor/User/globalStorage/state.vscdb",
        "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb",
    ],
    "hermes": [
        "$HERMES_HOME/state.db",
        "~/.hermes/state.db",
        "%LOCALAPPDATA%/hermes/state.db",
    ],
    "freebuff": [
        "~/.config/manicode",
        "$FREEBUFF_DATA_DIR",
    ],
    "aider": [
        "~/.aider",
        "~/.aider.chat.history.md",
    ],
    "windsurf": [
        "%APPDATA%/Windsurf/User/globalStorage/state.vscdb",
        "~/.windsurf/User/globalStorage/state.vscdb",
    ],
    "copilot": [
        "~/.copilot/otel/*.jsonl",
        "%APPDATA%/Code/User/workspaceStorage",
    ],
    "cline": [
        "%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/tasks",
        "~/.cline/data/sessions/",
    ],
    "roo_code": [
        "~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks",
        "%APPDATA%/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks",
    ],
    "kilo_code": [
        "~/.config/Code/User/globalStorage/kilocode.kilo-code/tasks",
        "~/.local/share/kilo/kilo.db",
    ],
    "continue": [
        "%APPDATA%/Code/User/globalStorage/continue.continue",
        "~/.continue",
    ],
    "opencode": [
        "~/.local/share/opencode/opencode.db",
    ],
    "openhands": [
        "~/.openhands-state",
    ],
    "amp": [
        "~/.local/share/amp/threads/",
    ],
    "beads": [
        ".beads/beads.db",
    ],
    "chatgpt_desktop": [
        "%LOCALAPPDATA%/ChatGPT",
        "~/Library/Application Support/ChatGPT",
    ],
    "pi_agent": [
        "~/.pi/agent/sessions/",
    ],
    "factory": [
        "~/.factory/sessions/",
    ],
    "grok_build": [
        "$GROK_HOME/sessions",
        "~/.grok/sessions",
    ],
    "prime_agent": [
        "~/.prime/agent/sessions/",
    ],
    "goose": [
        "~/.local/share/goose/sessions/sessions.db",
    ],
    "zed": [
        "~/.local/share/zed/threads/threads.db",
        "~/Library/Application Support/Zed/threads/threads.db",
    ],
    "kiro": [
        "~/.kiro/sessions/cli/",
        "~/.local/share/kiro-cli/data.sqlite3",
    ],
    "kimchi": [
        "~/.config/kimchi/harness/sessions/",
    ],
    "kimi": [
        "~/.kimi/sessions/",
        "~/.kimi-code/sessions/",
    ],
    "qwen_cli": [
        "~/.qwen/projects/",
    ],
    "mux": [
        "~/.mux/sessions/",
    ],
    "junie": [
        "~/.junie/sessions/",
    ],
    "senpi": [
        "~/.senpi/agent/sessions/",
    ],
    "crush": [
        "$XDG_DATA_HOME/crush/projects.json",
    ],
}


def resolve_path(pattern: str) -> Path:
    """Aufloesen eines Pfad-Patterns mit ENV-Variablen."""
    home = get_home()
    
    # ~ am Anfang
    if pattern.startswith("~"):
        return home / pattern[2:]
    
    # %VAR% Windows-Style
    if "%" in pattern:
        import re
        def replace_win(m):
            var = m.group(1)
            if var == "USERPROFILE":
                return str(home)
            elif var == "APPDATA":
                return os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
            elif var == "LOCALAPPDATA":
                return os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
            return os.environ.get(var, m.group(0))
        resolved = re.sub(r"%([^%]+)%", replace_win, pattern)
        return Path(resolved)
    
    # $ENV Unix-Style
    if "$" in pattern:
        import re
        def replace_unix(m):
            var = m.group(1)
            if var == "HOME":
                return str(home)
            elif var == "XDG_CONFIG_HOME":
                return os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
            elif var == "XDG_DATA_HOME":
                return os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
            return os.environ.get(var, m.group(0))
        resolved = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", replace_unix, pattern)
        return Path(resolved)
    
    return Path(pattern)


def find_platform_data(platform_id: str) -> list[dict]:
    """
    Sucht Daten fuer eine Plattform mit globaler Suchlogik.
    
    Returns:
        List of dicts mit path, exists, description
    """
    patterns = PLATFORM_SEARCH_PATTERNS.get(platform_id, [])
    results = []
    
    for pattern in patterns:
        path = resolve_path(pattern)
        exists = path.exists()
        
        # Fuer Verzeichnisse: Pruefe ob Inhalt vorhanden
        if exists and path.is_dir():
            try:
                contents = list(path.iterdir())
                exists = len(contents) > 0
            except PermissionError:
                exists = False
        
        results.append({
            "pattern": pattern,
            "path": str(path),
            "exists": exists,
            "description": f"Platform data for {platform_id}",
        })
    
    return results


def search_all_platforms() -> dict[str, list[dict]]:
    """Sucht Daten fuer alle Plattformen."""
    results = {}
    for platform_id in PLATFORM_SEARCH_PATTERNS:
        data = find_platform_data(platform_id)
        if any(d["exists"] for d in data):
            results[platform_id] = data
    return results


def discover_installed_platforms() -> list[dict]:
    """Findet alle installierten Plattformen."""
    installed = []
    
    for platform_id, patterns in PLATFORM_SEARCH_PATTERNS.items():
        found_paths = []
        for pattern in patterns:
            path = resolve_path(pattern)
            if path.exists():
                found_paths.append({
                    "pattern": pattern,
                    "path": str(path),
                })
        
        if found_paths:
            installed.append({
                "platform_id": platform_id,
                "found_paths": found_paths,
            })
    
    return installed


def find_git_repos(root: Path | None = None, max_depth: int = 3) -> list[Path]:
    """Findet alle Git-Repos unterhalb eines Pfads."""
    if root is None:
        root = get_home()
    
    repos = []
    
    if (root / ".git").exists():
        repos.append(root)
    
    if max_depth <= 0:
        return repos
    
    try:
        for entry in root.iterdir():
            if entry.name.startswith(".") or entry.name.startswith("__"):
                continue
            if entry.is_dir():
                repos.extend(find_git_repos(entry, max_depth - 1))
    except PermissionError:
        pass
    
    return repos


def find_project_by_name(name: str) -> Path | None:
    """Findet ein Projekt anhand seines Namens."""
    home = get_home()
    
    # Standard-Suchpfade
    search_dirs = [
        home / "Documents",
        home / "Desktop",
        home / "Projects",
        home / "repos",
        home / "code",
        home / "dev",
        home,
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        # Exakter Match
        candidate = search_dir / name
        if candidate.exists() and (candidate / ".git").exists():
            return candidate
        
        # Fuzzy Match
        try:
            for entry in search_dir.iterdir():
                if entry.is_dir() and name.lower() in entry.name.lower():
                    if (entry / ".git").exists():
                        return entry
        except PermissionError:
            continue
    
    return None


if __name__ == "__main__":
    # Discovery ausfuehren
    print("=" * 60)
    print("  Globale Plattform-Discovery")
    print("=" * 60)
    
    installed = discover_installed_platforms()
    print(f"\nGefundene Plattformen: {len(installed)}")
    
    for p in installed:
        print(f"\n  {p['platform_id']}:")
        for fp in p["found_paths"]:
            print(f"    [OK] {fp['path']}")
    
    print("\n" + "=" * 60)
