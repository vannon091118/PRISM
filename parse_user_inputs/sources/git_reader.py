"""
parse_user_inputs.sources.git_reader
======================================
Git Commit Reader — liest Commits aus lokalen Repos und matcht sie mit Threads.

Features:
  - Komplettes git log (hash, message, date, author, files_changed)
  - Automatische Projekt-Erkennung (.git Verzeichnis)
  - Matching von Commits zu Threads via Zeitproximitaet
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import Any


def read_commits(
    project_path: str,
    since_date: str = "",
    max_count: int = 200,
) -> list[dict[str, Any]]:
    """
    Liest Git-Commits aus einem Projekt.

    Returns:
        List of dicts mit: hash, message, date, author, files_changed, insertions, deletions
    """
    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return []

    commits: list[dict[str, Any]] = []

    try:
        # Git log mit Details
        cmd = [
            "git", "-C", project_path, "log",
            f"--max-count={max_count}",
            "--format=%H|%s|%aI|%an",
            "--numstat",
        ]
        if since_date:
            cmd.append(f"--since={since_date}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace"
        )

        if result.returncode != 0:
            return []

        current: dict[str, Any] = {}
        for line in result.stdout.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Commit-Header: hash|message|date|author
            if "|" in line and len(line.split("|")) == 4:
                if current:
                    commits.append(current)
                parts = line.split("|")
                current = {
                    "hash": parts[0][:12],
                    "hash_full": parts[0],
                    "message": parts[1],
                    "date": _parse_git_date(parts[2]),
                    "date_raw": parts[2],
                    "author": parts[3],
                    "files_changed": 0,
                    "insertions": 0,
                    "deletions": 0,
                    "files": [],
                }
            # Numstat-Zeile: insertions deletions filename
            elif current and "\t" in line:
                ns = line.split("\t")
                if len(ns) == 3:
                    ins = int(ns[0]) if ns[0] != "-" else 0
                    dels = int(ns[1]) if ns[1] != "-" else 0
                    current["files_changed"] += 1
                    current["insertions"] += ins
                    current["deletions"] += dels
                    current["files"].append(ns[2])

        if current:
            commits.append(current)

    except Exception:
        pass

    return commits


def find_git_repos(root_path: str, max_depth: int = 3) -> list[str]:
    """
    Findet alle Git-Repos unterhalb eines Pfads.
    """
    repos: list[str] = []

    if os.path.exists(os.path.join(root_path, ".git")):
        repos.append(root_path)

    if max_depth <= 0:
        return repos

    try:
        for entry in os.listdir(root_path):
            if entry.startswith(".") or entry.startswith("__"):
                continue
            child = os.path.join(root_path, entry)
            if os.path.isdir(child):
                repos.extend(find_git_repos(child, max_depth - 1))
    except PermissionError:
        pass

    return repos


def match_commits_to_threads(
    commits: list[dict[str, Any]],
    threads: list[Any],
    tolerance_minutes: int = 30,
) -> dict[str, list[dict[str, Any]]]:
    """
    Matcht Git-Commits zu Threads basierend auf Zeitproximitaet.

    Returns:
        Dict mit thread_id -> [matching_commits]
    """
    from parse_user_inputs.sorting import parse_date

    result: dict[str, list[dict[str, Any]]] = {}

    for commit in commits:
        commit_dt = parse_date(commit["date"])
        if commit_dt == datetime.min:
            continue

        best_thread = None
        best_delta = float("inf")

        for thread in threads:
            thread_dt = parse_date(thread.date)
            if thread_dt == datetime.min:
                continue

            delta = abs((commit_dt - thread_dt).total_seconds()) / 60
            if delta < best_delta and delta < tolerance_minutes:
                best_delta = delta
                best_thread = thread

        if best_thread:
            tid = best_thread.id
            if tid not in result:
                result[tid] = []
            result[tid].append({
                "hash": commit["hash"],
                "message": commit["message"],
                "date": commit["date"],
                "author": commit["author"],
                "files_changed": commit["files_changed"],
                "insertions": commit["insertions"],
                "deletions": commit["deletions"],
                "minutes_after": round(best_delta),
            })

    return result


def get_all_repo_commits(
    root_path: str = "",
    since_date: str = "",
    max_per_repo: int = 100,
) -> dict[str, list[dict[str, Any]]]:
    """
    Liest Commits aus allen gefundenen Git-Repos.

    Returns:
        Dict mit repo_path -> [commits]
    """
    if not root_path:
        root_path = os.path.expanduser("~")

    repos = find_git_repos(root_path, max_depth=4)
    all_commits: dict[str, list[dict[str, Any]]] = {}

    for repo in repos:
        commits = read_commits(repo, since_date, max_per_repo)
        if commits:
            all_commits[repo] = commits

    return all_commits


def _parse_git_date(date_str: str) -> str:
    """Parst Git ISO-Datum zu YYYY-MM-DD HH:MM."""
    if not date_str:
        return "?"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str[:16]
