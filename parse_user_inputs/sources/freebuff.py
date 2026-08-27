"""
parse_user_inputs.sources.freebuff
===================================
Freebuff Desktop Reader — SQLite + API Hybrid.

Liest direkt aus den Freebuff Desktop SQLite-DBs unter
~/.config/freebuff-desktop/projects/*/desktop-v2.db
Falls API erreichbar, wird diese als Primary verwendet.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from parse_user_inputs.categorizer import categorize
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "freebuff"
API_BASE = "http://127.0.0.1:55703"

# Freebuff Desktop speichert Daten in ~/.config/freebuff-desktop/projects/
_FREEBUFF_CONFIG_DIRS = [
    os.path.expanduser("~/.config/freebuff-desktop"),
    os.path.expanduser("~/.config/manicode"),
]


def _api_get(path: str, timeout: int = 5) -> dict | None:
    """Holt Daten von der Freebuff API."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{API_BASE}{path}")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception:
        return None


def _find_db_files() -> list[tuple[str, str]]:
    """Findet alle Freebuff Desktop SQLite-DBs.
    
    Returns: List of (db_path, project_name) tuples.
    """
    db_files = []
    for config_dir in _FREEBUFF_CONFIG_DIRS:
        if not os.path.isdir(config_dir):
            continue
        for db_path in glob.glob(os.path.join(config_dir, "projects", "*", "desktop-v2.db")):
            proj_dir = os.path.basename(os.path.dirname(db_path))
            # Entferne UUID-Suffix: "snip-war-c7a6e49e-dc98-46d2-8827-14c92e6b8faf" -> "snip-war"
            # UUID pattern: 8-4-4-4-12 hex chars
            proj_name = re.sub(r'-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', '', proj_dir)
            if proj_name == proj_dir:
                # Fallback: strip trailing dash segments that look like UUIDs
                proj_name = proj_dir.rsplit("-", 1)[0] if "-" in proj_dir else proj_dir
            db_files.append((db_path, proj_name))
    return db_files


def _ts_to_str(ts: float | int | None) -> str:
    """Konvertiert Millisecond-Timestamp zu Datumsstring."""
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"


def _extract_project_name(proj_path: str) -> str:
    """Extrahiert den Projekt-Namen aus dem Pfad."""
    if not proj_path:
        return "unknown"
    stripped = proj_path.rstrip("/\\")
    if not stripped:
        return "unknown"
    return os.path.basename(stripped) or "unknown"


def _parse_parts_json(parts_json: str) -> list[dict]:
    """Parst parts_json aus Freebuff DB."""
    try:
        parts = json.loads(parts_json) if parts_json else []
        return parts if isinstance(parts, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def scan_inputs() -> list[dict[str, Any]]:
    """Liest User-Inputs aus Freebuff Desktop DBs (direkt oder API)."""
    # Zuerst API versuchen
    data = _api_get("/api/projects")
    if data:
        return _scan_inputs_from_api(data)

    # Fallback: Direkter SQLite-Lesen
    return _scan_inputs_from_db()


def _scan_inputs_from_api(data: dict) -> list[dict[str, Any]]:
    """API-basiertes Scannen (Legacy)."""
    inputs: list[dict[str, Any]] = []
    for proj in data.get("projects", []):
        for t in proj.get("threads", []):
            tid = t["id"]
            title = t.get("title", "?")
            detail = _api_get(f"/api/thread/{tid}")
            if not detail:
                continue
            for m in detail.get("messages", []):
                if m.get("role") != "user":
                    continue
                for p in m.get("parts", []):
                    if p.get("kind") != "text":
                        continue
                    text = p.get("text", "").strip()
                    if not text or len(text) <= 3:
                        continue
                    ts = m.get("ts", 0)
                    inputs.append({
                        "date": _ts_to_str(ts),
                        "content": text[:2000],
                        "categories": categorize(text),
                        "source": PLATFORM_ID,
                        "session": tid[:12],
                        "platform": PLATFORM_ID,
                        "thread_title": title[:80],
                    })
    return inputs


def _scan_inputs_from_db() -> list[dict[str, Any]]:
    """Direktes Scannen aus Freebuff Desktop SQLite-DBs."""
    inputs: list[dict[str, Any]] = []

    for db_path, proj_name in _find_db_files():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()

            # Nur User-Messages mit Text
            cur.execute("""
                SELECT m.thread_id, m.parts_json, m.ts, t.title
                FROM messages m
                JOIN threads t ON m.thread_id = t.id
                WHERE m.role = 'user'
                ORDER BY m.ts ASC
            """)

            for row in cur.fetchall():
                tid, parts_json, ts, title = row
                parts = _parse_parts_json(parts_json)
                for p in parts:
                    if p.get("kind") != "text":
                        continue
                    text = (p.get("text") or "").strip()
                    if not text or len(text) <= 3:
                        continue
                    inputs.append({
                        "date": _ts_to_str(ts),
                        "content": text[:2000],
                        "categories": categorize(text),
                        "source": PLATFORM_ID,
                        "session": tid[:12],
                        "platform": PLATFORM_ID,
                        "project": proj_name,
                        "thread_title": (title or "?")[:80],
                    })

            conn.close()
        except Exception:
            continue

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert vollstaendige Threads aus Freebuff Desktop DBs."""
    # Zuerst API versuchen
    data = _api_get("/api/projects")
    if data:
        return _reconstruct_from_api(data)

    # Fallback: Direkter SQLite-Lesen
    return _reconstruct_from_db()


def _reconstruct_from_api(data: dict) -> list[Thread]:
    """API-basierte Thread-Rekonstruktion (Legacy)."""
    threads: list[Thread] = []
    for proj in data.get("projects", []):
        proj_path = proj.get("path", "")
        proj_name = _extract_project_name(proj_path)

        for t in proj.get("threads", []):
            tid = t["id"]
            title = t.get("title", "?")
            model = t.get("model", "?")
            branch = t.get("branch")
            outcome = t.get("lastTurnOutcome", "")
            deliveries = t.get("deliveries", [])
            agent_mode = t.get("agentMode", "")
            exec_mode = t.get("executionMode", "")

            detail = _api_get(f"/api/thread/{tid}")
            if not detail:
                continue

            messages = _parse_api_messages(detail, model)
            if not messages:
                continue

            all_user_text = " ".join(m.content for m in messages if m.is_user)
            cats = categorize(all_user_text)

            artifacts: list[dict] = []
            for d in deliveries:
                artifacts.append({
                    "type": d.get("kind", "unknown"),
                    "status": d.get("status", ""),
                    "url": d.get("url", ""),
                    "number": d.get("number"),
                    "branch": d.get("branch", ""),
                })
            if branch:
                artifacts.append({"type": "branch", "name": branch})

            threads.append(Thread(
                id=tid[:12],
                platform=PLATFORM_ID,
                project=proj_name,
                title=title[:80],
                date=messages[0].timestamp if messages else "?",
                messages=messages,
                categories=cats,
                metadata={
                    "model": model,
                    "outcome": outcome,
                    "agent_mode": agent_mode,
                    "exec_mode": exec_mode,
                    "artifacts": artifacts,
                },
            ))

    return threads


def _parse_api_messages(detail: dict, model: str) -> list[Message]:
    """Parst API-Thread-Detail zu Message-Objekten."""
    messages = []
    for m in detail.get("messages", []):
        role = m.get("role", "user")
        ts = m.get("ts", 0)
        dt = _ts_to_str(ts)
        for p in m.get("parts", []):
            if p.get("kind") == "text":
                text = p.get("text", "").strip()
                if text and len(text) > 2:
                    messages.append(Message(
                        role=role,
                        content=text[:2000],
                        timestamp=dt,
                        model=model,
                    ))
    return messages


def _reconstruct_from_db() -> list[Thread]:
    """Direkte Thread-Rekonstruktion aus Freebuff Desktop SQLite-DBs."""
    threads: list[Thread] = []

    for db_path, proj_name in _find_db_files():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()

            # Lade Threads
            cur.execute("""
                SELECT id, title, model, agent_mode, execution_mode,
                       branch, last_turn_outcome, status, created_at
                FROM threads
                ORDER BY created_at DESC
            """)
            thread_rows = cur.fetchall()

            # Lade Deliveries pro Thread
            cur.execute("SELECT thread_id, kind, status, branch, url, number FROM thread_deliveries")
            deliveries_by_thread: dict[str, list] = {}
            for row in cur.fetchall():
                tid = row[0]
                if tid not in deliveries_by_thread:
                    deliveries_by_thread[tid] = []
                deliveries_by_thread[tid].append({
                    "type": row[1],
                    "status": row[2],
                    "branch": row[3],
                    "url": row[4],
                    "number": row[5],
                })

            # Lade Messages pro Thread
            cur.execute("""
                SELECT thread_id, role, parts_json, ts
                FROM messages
                ORDER BY ts ASC
            """)
            all_messages = cur.fetchall()
            messages_by_thread: dict[str, list] = {}
            for row in all_messages:
                tid = row[0]
                if tid not in messages_by_thread:
                    messages_by_thread[tid] = []
                messages_by_thread[tid].append(row)

            for trow in thread_rows:
                tid = trow[0]
                title = trow[1] or "?"
                model = trow[2] or ""
                agent_mode = trow[3] or ""
                exec_mode = trow[4] or ""
                branch = trow[5]
                outcome = trow[6] or ""
                created_at = trow[8]

                # Parse messages
                msg_rows = messages_by_thread.get(tid, [])
                messages = []
                for mrow in msg_rows:
                    role = mrow[1]
                    parts = _parse_parts_json(mrow[2])
                    ts = mrow[3]

                    for p in parts:
                        kind = p.get("kind", "")
                        text = (p.get("text") or "").strip()
                        if not text or len(text) <= 2:
                            continue

                        if kind == "text":
                            msg_role = role
                        elif kind == "reasoning":
                            msg_role = "assistant"
                        elif kind == "tool":
                            msg_role = "tool"
                        else:
                            msg_role = role

                        messages.append(Message(
                            role=msg_role,
                            content=text[:2000],
                            timestamp=_ts_to_str(ts),
                            model=model,
                        ))

                if not messages:
                    continue

                all_user_text = " ".join(m.content for m in messages if m.is_user)
                cats = categorize(all_user_text)

                # Collect artifacts
                artifacts: list[dict] = []
                for d in deliveries_by_thread.get(tid, []):
                    artifacts.append(d)
                if branch:
                    artifacts.append({"type": "branch", "name": branch})

                threads.append(Thread(
                    id=tid[:12],
                    platform=PLATFORM_ID,
                    project=proj_name,
                    title=title[:80],
                    date=messages[0].timestamp if messages else _ts_to_str(created_at),
                    messages=messages,
                    categories=cats,
                    metadata={
                        "model": model,
                        "outcome": outcome,
                        "agent_mode": agent_mode,
                        "exec_mode": exec_mode,
                        "artifacts": artifacts,
                        "status": trow[7] or "unknown",
                    },
                ))

            conn.close()
        except Exception:
            continue

    return threads
