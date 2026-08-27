"""
parse_user_inputs.sources.claude_code
======================================
Claude Code Reader — ~/.claude/history.jsonl.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "claude_code"


def _history_path() -> str:
    return os.path.join(str(Path.home()), ".claude", "history.jsonl")


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Claude Code User-Inputs aus history.jsonl."""
    inputs: list[dict[str, Any]] = []
    path = _history_path()

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

                display = entry.get("display", "")
                if display.startswith("/") and len(display) < 20:
                    continue
                if not display or len(display) < 3:
                    continue

                session_id = entry.get("sessionId", "?")
                ts = entry.get("timestamp", 0)
                project = entry.get("project", "")
                dt = _ts_to_str(ts)
                proj_name = os.path.basename(project) if project else "unknown"

                inputs.append({
                    "date": dt,
                    "content": display.strip()[:2000],
                    "categories": categorize(display),
                    "source": PLATFORM_ID,
                    "session": str(session_id)[:12],
                    "platform": PLATFORM_ID,
                    "project": proj_name,
                })
    except Exception:
        pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Claude Code history.jsonl."""
    threads: list[Thread] = []
    path = _history_path()

    if not os.path.exists(path):
        return threads

    sessions: dict[str, dict] = {}
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

                display = entry.get("display", "")
                if not display or len(display) < 2:
                    continue
                # Befehle filtern (/model, /init, /cd, etc.)
                if display.startswith("/") and len(display) < 20:
                    continue
                if not is_real_user_input(display):
                    continue

                session_id = entry.get("sessionId", "?")
                if session_id not in sessions:
                    sessions[session_id] = {
                        "project": entry.get("project", ""),
                        "messages": [],
                    }

                dt = _ts_to_str(entry.get("timestamp", 0))
                sessions[session_id]["messages"].append(Message(
                    role="user",
                    content=display.strip()[:2000],
                    timestamp=dt,
                ))
    except Exception:
        pass

    for sid, data in sessions.items():
        if not data["messages"]:
            continue

        project = os.path.basename(data["project"]) if data["project"] else "unknown"
        all_user_text = " ".join(m.content for m in data["messages"] if m.is_user)
        cats = categorize(all_user_text)

        threads.append(Thread(
            id=sid[:12],
            platform=PLATFORM_ID,
            project=project,
            title=data["messages"][0].content[:60],
            date=data["messages"][0].timestamp,
            messages=data["messages"],
            categories=cats,
        ))

    return threads


def _ts_to_str(ts: float) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(float(ts) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"
