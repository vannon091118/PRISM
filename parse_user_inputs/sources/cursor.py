"""
parse_user_inputs.sources.cursor
=================================
Cursor Desktop Reader — state.vscdb agentKv blobs.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from parse_user_inputs.categorizer import categorize
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "cursor"


def _cursor_db_path() -> str:
    home = str(os.environ.get("USERPROFILE", os.path.expanduser("~")))
    return os.path.join(home, "AppData", "Roaming", "Cursor", "User", "globalStorage", "state.vscdb")


def scan_inputs() -> list[dict[str, Any]]:
    """Liest User-Inputs aus Cursor state.vscdb."""
    inputs: list[dict[str, Any]] = []
    db_path = _cursor_db_path()

    if not os.path.exists(db_path):
        return inputs

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            "SELECT key, value FROM cursorDiskKV "
            "WHERE key LIKE 'agentKv:%' AND value IS NOT NULL"
        ):
            try:
                data = json.loads(row["value"])
                role = data.get("role", "")
                if role != "user":
                    continue
                ct = data.get("content", "")
                if not ct or len(ct) < 5:
                    continue
                if ct.startswith("<user_info>") or ct.startswith("<system_notification>"):
                    continue

                inputs.append({
                    "date": "?",
                    "content": ct.strip()[:2000],
                    "categories": categorize(ct),
                    "source": PLATFORM_ID,
                    "session": row["key"][:12],
                    "platform": PLATFORM_ID,
                })
            except Exception:
                pass
        conn.close()
    except Exception:
        pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Cursor state.vscdb."""
    threads: list[Thread] = []
    db_path = _cursor_db_path()

    if not os.path.exists(db_path):
        return threads

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        messages = []
        for row in conn.execute(
            "SELECT key, value FROM cursorDiskKV "
            "WHERE key LIKE 'agentKv:%' AND value IS NOT NULL"
        ):
            try:
                data = json.loads(row["value"])
                role = data.get("role", "")
                ct = data.get("content", "")
                if not ct or len(ct) < 3:
                    continue
                if ct.startswith("<user_info>") or ct.startswith("<system_notification>"):
                    continue
                messages.append(Message(
                    role=role if role in ("user", "assistant", "tool") else "assistant",
                    content=ct.strip()[:2000],
                ))
            except Exception:
                pass
        conn.close()

        if not messages:
            return threads

        # Threads an User-Messages aufteilen
        current: list[Message] = []
        for m in messages:
            if m.is_user and current:
                cats = categorize(" ".join(x.content for x in current if x.is_user))
                threads.append(Thread(
                    id=f"cursor_{len(threads)}",
                    platform=PLATFORM_ID,
                    project="cursor",
                    title=current[0].content[:60],
                    date="?",
                    messages=current,
                    categories=cats,
                ))
                current = []
            current.append(m)

        if current:
            cats = categorize(" ".join(x.content for x in current if x.is_user))
            threads.append(Thread(
                id=f"cursor_{len(threads)}",
                platform=PLATFORM_ID,
                project="cursor",
                title=current[0].content[:60],
                date="?",
                messages=current,
                categories=cats,
            ))
    except Exception:
        pass

    return threads
