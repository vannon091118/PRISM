"""
parse_user_inputs.sources.codex
================================
OpenAI Codex CLI Reader — ~/.codex/history.jsonl + state_5.sqlite.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "codex"


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Codex User-Inputs aus history.jsonl."""
    inputs: list[dict[str, Any]] = []
    home = str(Path.home())
    path = os.path.join(home, ".codex", "history.jsonl")

    if not os.path.exists(path):
        return inputs

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                text = entry.get("text", "")
                if not text or len(text) < 3:
                    continue

                session_id = entry.get("session_id", "?")
                ts = entry.get("ts", 0)
                dt = _ts_to_str(ts)

                inputs.append({
                    "date": dt,
                    "content": text.strip()[:2000],
                    "categories": categorize(text),
                    "source": PLATFORM_ID,
                    "session": str(session_id)[:12],
                    "platform": PLATFORM_ID,
                })
    except Exception:
        pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Codex history.jsonl + state_5.sqlite."""
    threads: list[Thread] = []
    home = str(Path.home())

    # User-Inputs aus history.jsonl
    user_inputs: dict[str, list[Message]] = {}
    history_path = os.path.join(home, ".codex", "history.jsonl")

    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    text = entry.get("text", "")
                    if not text or len(text) < 2:
                        continue

                    session_id = entry.get("session_id", "?")
                    if session_id not in user_inputs:
                        user_inputs[session_id] = []

                    dt = _ts_to_str(entry.get("ts", 0))
                    user_inputs[session_id].append(Message(
                        role="user",
                        content=text.strip()[:2000],
                        timestamp=dt,
                    ))
        except Exception:
            pass

    # Threads aus state_5.sqlite
    state_db = os.path.join(home, ".codex", "state_5.sqlite")
    if os.path.exists(state_db):
        try:
            conn = sqlite3.connect(state_db)
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT id, title, created_at, cwd FROM threads"):
                tid = row["id"][:12]
                title = row["title"] or "?"
                cwd = row["cwd"] or ""
                project = os.path.basename(cwd) if cwd else "unknown"
                dt = _ts_to_str(row["created_at"] or 0)

                messages = user_inputs.get(row["id"], [])
                if not messages:
                    continue

                all_user_text = " ".join(m.content for m in messages if m.is_user)
                cats = categorize(all_user_text)

                threads.append(Thread(
                    id=tid,
                    platform=PLATFORM_ID,
                    project=project,
                    title=title[:80],
                    date=dt,
                    messages=messages,
                    categories=cats,
                ))
            conn.close()
        except Exception:
            pass

    return threads


def _ts_to_str(ts: float) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"
