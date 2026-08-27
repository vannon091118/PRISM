"""
parse_user_inputs.sources.hermes
=================================
Hermes Agent Reader — state.db (User -> Assistant -> Tool).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "hermes"


def scan_inputs(db_path: str | None = None) -> list[dict[str, Any]]:
    """Liest User-Inputs aus der Hermes state.db."""
    from parse_user_inputs.config import Config
    if db_path is None:
        db_path = Config().db_path

    inputs: list[dict[str, Any]] = []
    if not os.path.exists(db_path):
        return inputs

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("""
            SELECT m.content, m.timestamp, m.session_id, s.title
            FROM messages m LEFT JOIN sessions s ON m.session_id = s.id
            WHERE m.role = 'user' AND m.active = 1
            ORDER BY m.timestamp
        """):
            content = row["content"] or ""
            if not content or len(content) < 5:
                continue
            if not is_real_user_input(content):
                continue

            ts = row["timestamp"] or 0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "?"
            inputs.append({
                "date": dt,
                "content": content.strip()[:2000],
                "categories": categorize(content),
                "source": PLATFORM_ID,
                "session": (row["session_id"] or "")[:12],
                "platform": PLATFORM_ID,
            })
        conn.close()
    except Exception:
        pass

    return inputs


def reconstruct_threads(db_path: str | None = None) -> list[Thread]:
    """Rekonstruiert vollstaendige Threads aus der Hermes state.db."""
    from parse_user_inputs.config import Config
    if db_path is None:
        db_path = Config().db_path

    threads: list[Thread] = []
    if not os.path.exists(db_path):
        return threads

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        sessions: dict[str, dict] = {}
        for row in conn.execute("""
            SELECT m.content, m.timestamp, m.role, m.session_id,
                   s.title, s.model
            FROM messages m LEFT JOIN sessions s ON m.session_id = s.id
            WHERE m.active = 1
            ORDER BY m.timestamp
        """):
            sid = row["session_id"] or "unknown"
            if sid not in sessions:
                sessions[sid] = {
                    "title": row["title"] or "?",
                    "model": row["model"] or "?",
                    "messages": [],
                }

            content = row["content"] or ""
            if not content or len(content) < 2:
                continue

            ts = row["timestamp"] or 0
            dt = "?"
            if ts:
                try:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

            msg_type = _detect_message_type(content)

            sessions[sid]["messages"].append(Message(
                role=row["role"] or "user",
                content=content.strip(),
                timestamp=dt,
                model=sessions[sid]["model"],
                message_type=msg_type,
            ))

        conn.close()

        for sid, data in sessions.items():
            if not data["messages"]:
                continue
            if not any(m.is_user for m in data["messages"]):
                continue

            # Hermes-Sessions haben keine Projektinfo, nutze generischen Namen
            # Versuche Projekt aus User-Messages zu erkenen
            project = _detect_project(data["messages"], data["title"])
            all_user_text = " ".join(m.content for m in data["messages"] if m.is_user)
            cats = categorize(all_user_text)

            threads.append(Thread(
                id=sid[:12],
                platform=PLATFORM_ID,
                project=project,
                title=data["title"][:80],
                date=data["messages"][0].timestamp,
                messages=data["messages"],
                categories=cats,
                metadata={"model": data["model"]},
            ))
    except Exception:
        pass

    return threads


def _detect_project(messages: list[Message], title: str) -> str:
    """Erkennt das Projekt aus User-Messages oder Session-Titel."""
    import re
    
    # Bekannte Projekt-Pfade/Muster in User-Messages
    known_projects = {
        'snip-war': 'snip-war',
        'snippet-empire': 'snippet-empire',
        'SyxBridge_Live': 'SyxBridge_Live',
        'RhytmusIsaPatter': 'RhytmusIsaPatter',
        'user_inputs_parser': 'user_inputs_parser',
        'PRISM': 'PRISM',
    }
    
    for m in messages:
        if not m.is_user:
            continue
        text = m.content.lower()
        for pattern, name in known_projects.items():
            if pattern.lower() in text:
                return name
        # Pfad-Muster: C:\Users\...\projectname
        path_match = re.search(r'[\/](?:Desktop|Documents|projects)[\/]+([\w_-]+)', m.content)
        if path_match:
            return path_match.group(1)
    
    # Fallback: Generischer Name
    return "hermes-sessions"


def _detect_message_type(content: str) -> str:
    """Erkennt den Message-Typ anhand von Inhaltspatterns."""
    lower = content.lower()
    if "cut off" in lower or "interrupt" in lower:
        return "interrupt"
    if content.startswith("[System:") or content.startswith("[Context from"):
        return "system"
    if content.startswith("[Note: model was switched"):
        return "model_switch"
    if "continue working toward" in lower:
        return "system"
    return "normal"
