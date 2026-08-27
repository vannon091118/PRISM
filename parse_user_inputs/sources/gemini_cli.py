"""
parse_user_inputs.sources.gemini_cli
=====================================
Gemini CLI Reader — ~/.gemini/antigravity-cli/history.jsonl.
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "gemini_cli"


def _history_path() -> str:
    return os.path.join(str(Path.home()), ".gemini", "antigravity-cli", "history.jsonl")


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Gemini CLI User-Inputs."""
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
                if not display or len(display) < 3:
                    continue
                if display.startswith("/") and len(display) < 20:
                    continue

                workspace = entry.get("workspace", "")
                project = os.path.basename(workspace) if workspace else "unknown"
                dt = _ts_to_str(entry.get("timestamp", 0))

                inputs.append({
                    "date": dt,
                    "content": display.strip()[:2000],
                    "categories": categorize(display),
                    "source": PLATFORM_ID,
                    "session": "gemini",
                    "platform": PLATFORM_ID,
                    "project": project,
                })
    except Exception:
        pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Gemini CLI history.jsonl."""
    threads: list[Thread] = []
    path = _history_path()

    if not os.path.exists(path):
        return threads

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
                if not display or len(display) < 3:
                    continue
                if display.startswith("/") and len(display) < 20:
                    continue

                workspace = entry.get("workspace", "")
                project = os.path.basename(workspace) if workspace else "unknown"
                dt = _ts_to_str(entry.get("timestamp", 0))
                cats = categorize(display)

                threads.append(Thread(
                    id=f"gemini_{len(threads)}",
                    platform=PLATFORM_ID,
                    project=project,
                    title=display[:60],
                    date=dt,
                    messages=[Message(role="user", content=display.strip()[:2000], timestamp=dt)],
                    categories=cats,
                ))
    except Exception:
        pass

    return threads


def _ts_to_str(ts: float) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(float(ts) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"
