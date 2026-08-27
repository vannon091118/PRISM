"""
parse_user_inputs.sources
==========================
Registry aller Plattform-Reader.

Jede Plattform-Datei in diesem Paket implementiert:
  - PLATFORM_ID: str
  - scan_inputs() -> list[dict]
  - reconstruct_threads() -> list[Thread]

Die Registry oben fuehrt alles zusammen:
  - scan_all_inputs()    -> dict[platform_id, list[dict]]
  - scan_all_threads()   -> dict[platform_id, list[Thread]]
  - discover_installed() -> list[dict]

Alte Kompatibilitaets-Imports fuer die Legacy-API bleiben erhalten.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from parse_user_inputs.models import Thread

# ─── Plattform-Module importieren ────────────────────────────────────────────

from parse_user_inputs.sources import hermes
from parse_user_inputs.sources import freebuff
from parse_user_inputs.sources import claude_code
from parse_user_inputs.sources import codex
from parse_user_inputs.sources import cursor
from parse_user_inputs.sources import gemini_cli
from parse_user_inputs.sources import aider
from parse_user_inputs.sources import gemini_desktop
from parse_user_inputs.sources import kilo_code
from parse_user_inputs.sources import cline
from parse_user_inputs.sources import roo_code
from parse_user_inputs.sources import copilot

# ─── Registry ────────────────────────────────────────────────────────────────

# Plattform-Reader die eigene scan_inputs() + reconstruct_threads() haben
NATIVE_READERS = {
    "hermes": hermes,
    "freebuff": freebuff,
    "claude_code": claude_code,
    "codex": codex,
    "cursor": cursor,
    "gemini_cli": gemini_cli,
    "gemini_desktop": gemini_desktop,
    "kilo_code": kilo_code,
    "aider": aider,
    "cline": cline,
    "roo_code": roo_code,
    "copilot": copilot,
}

# Legacy: VS Code Extensions (jetzt alle als Native)
VSCODE_PLATFORMS = []


# ─── Oeffentliche API ───────────────────────────────────────────────────────

def scan_all_inputs(
    platform_filter: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Scannt alle Plattformen und gibt User-Inputs pro Plattform zurueck.

    Returns:
        Dict mit platform_id -> [input_dicts]
    """
    from parse_user_inputs.platforms import ALL_PLATFORMS, PLATFORM_BY_ID

    results: dict[str, list[dict[str, Any]]] = {}

    targets = ALL_PLATFORMS
    if platform_filter:
        targets = [p for p in ALL_PLATFORMS if p.id in platform_filter]

    for platform in targets:
        pid = platform.id
        inputs: list[dict[str, Any]] = []

        if pid in NATIVE_READERS:
            try:
                inputs = NATIVE_READERS[pid].scan_inputs()
            except Exception:
                pass
        elif pid in VSCODE_PLATFORMS:
            try:
                inputs = vscode_extensions.scan_inputs(pid, platform)
            except Exception:
                pass

        if inputs:
            results[pid] = inputs

    return results


def scan_all_threads() -> dict[str, list[Thread]]:
    """
    Scannt alle Plattformen und gibt vollstaendige Threads zurueck.

    Returns:
        Dict mit platform_id -> [Thread]
    """
    from parse_user_inputs.platforms import ALL_PLATFORMS
    from parse_user_inputs.config import Config

    results: dict[str, list[Thread]] = {}
    cfg = Config()

    for platform in ALL_PLATFORMS:
        pid = platform.id
        threads: list[Thread] = []

        if pid in NATIVE_READERS:
            try:
                if pid == "hermes":
                    threads = hermes.reconstruct_threads(cfg.db_path)
                else:
                    threads = NATIVE_READERS[pid].reconstruct_threads()
            except Exception:
                pass
        elif pid in VSCODE_PLATFORMS:
            try:
                threads = vscode_extensions.reconstruct_threads(pid, platform)
            except Exception:
                pass

        if threads:
            results[pid] = threads

    # Git-Commits aus allen Projekten lesen und mit Threads matchen
    _match_git_commits(results)

    return results


def _match_git_commits(results: dict[str, list[Thread]]):
    """Liest Git-Commits und matcht sie mit Threads."""
    from parse_user_inputs.sources.git_reader import read_commits, find_git_repos
    from parse_user_inputs.sorting import parse_date
    from parse_user_inputs.config import Config

    # Sammle alle Projekt-Pfade
    project_paths: dict[str, str] = {}  # project_name -> path
    
    # Erst: Alle bekannten Git-Repos im Home-Verzeichnis finden
    home = os.path.expanduser("~")
    known_repos = find_git_repos(home, max_depth=3)
    
    # Projekt-Namen zu Pfaden zuordnen
    for pid, threads in results.items():
        for t in threads:
            proj = t.project
            if proj and proj not in project_paths:
                # Suche nach Verzeichnis das dem Projekt-Namen entspricht
                for repo_path in known_repos:
                    repo_name = os.path.basename(repo_path)
                    if repo_name.lower() == proj.lower() or proj.lower() in repo_name.lower():
                        project_paths[proj] = repo_path
                        break
                
                # Fallback: Standard-Suchpfade (portabel)
                if proj not in project_paths:
                    for candidate in [
                        os.path.join(home, "Documents", proj),
                        os.path.join(home, "Desktop", proj),
                        os.path.join(home, "Projects", proj),
                        os.path.join(home, "repos", proj),
                        os.path.join(home, "code", proj),
                        os.path.join(home, proj),
                    ]:
                        if os.path.exists(os.path.join(candidate, ".git")):
                            project_paths[proj] = candidate
                            break

    # Commits lesen und matchen
    all_commits_by_project: dict[str, list[dict]] = {}
    for proj_name, proj_path in project_paths.items():
        commits = read_commits(proj_path, max_count=200)
        if commits:
            all_commits_by_project[proj_name] = commits

    # Commits zu Threads zuordnen
    for pid, threads in results.items():
        for thread in threads:
            proj = thread.project
            if proj not in all_commits_by_project:
                continue

            commits = all_commits_by_project[proj]
            thread_dt = parse_date(thread.date)
            if thread_dt == datetime.min:
                continue

            # Finde Commits die zeitlich passen (innerhalb 60 Min)
            for commit in commits:
                commit_dt = parse_date(commit["date"])
                if commit_dt == datetime.min:
                    continue
                delta = abs((commit_dt - thread_dt).total_seconds()) / 60
                if delta < 60:
                    thread.git_commits.append({
                        "hash": commit["hash"],
                        "message": commit["message"],
                        "date": commit["date"],
                        "author": commit["author"],
                        "files_changed": commit["files_changed"],
                        "insertions": commit["insertions"],
                        "deletions": commit["deletions"],
                        "minutes_after": round(delta),
                    })


def discover_installed() -> list[dict[str, Any]]:
    """Findet installierte Plattformen und gibt deren Pfade zurueck."""
    from parse_user_inputs.platforms import ALL_PLATFORMS

    discovered = []
    for platform in ALL_PLATFORMS:
        resolved = platform.resolve_paths()
        found_paths = []
        for path, desc, ftype in resolved:
            if os.path.exists(path):
                found_paths.append({
                    "path": path,
                    "description": desc,
                    "file_type": ftype,
                })
        if found_paths:
            discovered.append({
                "platform": platform,
                "found_paths": found_paths,
            })
    return discovered


def print_discovery():
    """Druckt eine Uebersicht der entdeckten Plattformen."""
    discovered = discover_installed()
    print(f"\n{'='*60}")
    print(f"  Agent-Plattformen Discovery ({len(discovered)} gefunden)")
    print(f"{'='*60}")
    for d in discovered:
        p = d["platform"]
        print(f"\n  {p.name} ({p.vendor})")
        print(f"  {p.description}")
        for fp in d["found_paths"]:
            exists = "[OK]" if os.path.exists(fp["path"]) else "[--]"
            print(f"    [{exists}] {fp['path']}")
            print(f"         {fp['description']} ({fp['file_type']})")
    print(f"\n{'='*60}\n")
    return discovered


# ─── Legacy-Kompatibilität (alte Imports) ───────────────────────────────────

def read_state_db(db_path: str) -> list[dict]:
    """Legacy: Liest User-Inputs aus Hermes state.db."""
    return hermes.scan_inputs(db_path)


def read_state_db_assistant(db_path: str) -> list[dict]:
    """Legacy: Liest Assistant-Entries aus Hermes state.db."""
    # Wird fuer das alte Markdown-Rendering gebraucht
    import sqlite3
    entries = []
    if not os.path.exists(db_path):
        return entries
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("""
            SELECT content, timestamp, session_id, model
            FROM messages WHERE role = 'assistant' AND active = 1
            ORDER BY timestamp
        """):
            content = row["content"] or ""
            if len(content) > 50:
                entries.append({
                    "content": content[:2000],
                    "model": row["model"] or "",
                    "session": (row["session_id"] or "")[:12],
                })
        conn.close()
    except Exception:
        pass
    return entries


def read_state_db_tools(db_path: str) -> dict:
    """Legacy: Liest Tool-Statistiken aus Hermes state.db."""
    result = {"counter": {}, "sizes": {}, "sessions": {}}
    if not os.path.exists(db_path):
        return result
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("""
            SELECT content FROM messages WHERE role = 'tool' AND active = 1
        """):
            content = row["content"] or ""
            if content.startswith("Tool '"):
                tool_name = content.split("'")[1] if "'" in content else "unknown"
                result["counter"][tool_name] = result["counter"].get(tool_name, 0) + 1
        conn.close()
    except Exception:
        pass
    return result


def read_state_db_memory_stats(db_path: str) -> dict:
    """Legacy: Liest Memory-Statistiken aus Hermes state.db."""
    result = {"total_bytes": 0, "by_role": {}, "by_session": {}}
    if not os.path.exists(db_path):
        return result
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("""
            SELECT role, session_id, LENGTH(content) as size
            FROM messages WHERE active = 1
        """):
            role = row["role"] or "unknown"
            size = row["size"] or 0
            result["total_bytes"] += size
            result["by_role"][role] = result["by_role"].get(role, 0) + size
            sid = (row["session_id"] or "")[:12]
            result["by_session"][sid] = result["by_session"].get(sid, 0) + size
        conn.close()
    except Exception:
        pass
    return result


def read_request_dumps(sessions_dir: str) -> list[dict]:
    """Legacy: Liest Request-Dumps aus JSON-Dateien."""
    import json
    inputs = []
    if not os.path.exists(sessions_dir):
        return inputs
    try:
        for fname in sorted(os.listdir(sessions_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(sessions_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Verschiedene Formate
            messages = data.get("messages", data.get("conversation", []))
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", msg.get("text", ""))
                    if content and len(content) > 5:
                        inputs.append({
                            "date": data.get("timestamp", "?"),
                            "content": content[:2000],
                            "categories": [],
                            "source": "request_dump",
                            "session": fname[:12],
                        })
    except Exception:
        pass
    return inputs


def read_freebuff_threads(
    api_host: str = "127.0.0.1",
    api_port: int = 55703,
    project_filter: str = "",
) -> list[dict]:
    """Legacy: Liest Freebuff Inputs."""
    return freebuff.scan_inputs()


def read_paste_images(paste_dir: str) -> list[dict]:
    """Legacy: Liest Paste-PNG Metadaten."""
    images = []
    if not os.path.exists(paste_dir):
        return images
    try:
        for fname in sorted(os.listdir(paste_dir)):
            if not fname.lower().endswith(".png"):
                continue
            fpath = os.path.join(paste_dir, fname)
            images.append({
                "filename": fname,
                "path": fpath,
                "size": os.path.getsize(fpath),
            })
    except Exception:
        pass
    return images


def read_git_commits(project_path: str, since_date: str = "") -> list[dict]:
    """Legacy: Liest Git-Commits."""
    import subprocess
    commits = []
    try:
        cmd = ["git", "-C", project_path, "log", "--oneline", "-50"]
        if since_date:
            cmd.append(f"--since={since_date}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split(" ", 1)
                commits.append({
                    "hash": parts[0] if parts else "",
                    "message": parts[1] if len(parts) > 1 else "",
                })
    except Exception:
        pass
    return commits
