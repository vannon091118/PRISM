"""
parse_user_inputs.sources.cline
================================
Cline (saoudrizwan.claude-dev) Reader.

Speicherort:
  Windows: %APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/*.json
  Linux:   ~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/*.json
  macOS:   ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/*.json

JSON-Schema pro Task:
  - messages: [{role, content, timestamp, ...}]
  - conversation: [{role, content, ...}]
  - input / query / text: Einzelner Input

Cline CLI:
  $CLINE_SESSION_DATA_DIR/sessions/
  $CLINE_DATA_DIR/sessions/
  ~/.cline/data/sessions/
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "cline"


def _task_dirs() -> list[str]:
    """Findet alle Cline Task-Verzeichnisse."""
    home = str(Path.home())
    candidates = [
        # VS Code Extension
        os.path.join(home, "AppData", "Roaming", "Code", "User", "globalStorage",
                      "saoudrizwan.claude-dev", "tasks"),
        os.path.join(home, ".config", "Code", "User", "globalStorage",
                      "saoudrizwan.claude-dev", "tasks"),
        os.path.join(home, "Library", "Application Support", "Code", "User", "globalStorage",
                      "saoudrizwan.claude-dev", "tasks"),
        # VS Code Remote
        os.path.join(home, ".vscode-server", "data", "User", "globalStorage",
                      "saoudrizwan.claude-dev", "tasks"),
        # Cline CLI
        os.path.join(home, ".cline", "data", "sessions"),
    ]
    # ENV-Overrides
    for env_var in ["CLINE_SESSION_DATA_DIR", "CLINE_DATA_DIR", "CLINE_DIR"]:
        val = os.environ.get(env_var, "")
        if val:
            candidates.insert(0, os.path.join(val, "sessions") if not val.endswith("sessions") else val)

    return [p for p in candidates if os.path.exists(p)]


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Cline User-Inputs."""
    inputs: list[dict[str, Any]] = []

    for task_dir in _task_dirs():
        for task_file in sorted(glob.glob(os.path.join(task_dir, "*.json"))):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                inputs.extend(_extract_inputs_from_task(data, task_file))
            except Exception:
                pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Cline Tasks."""
    threads: list[Thread] = []

    for task_dir in _task_dirs():
        for task_file in sorted(glob.glob(os.path.join(task_dir, "*.json"))):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                thread = _extract_thread_from_task(data, task_file)
                if thread:
                    threads.append(thread)
            except Exception:
                pass

    return threads


def _extract_inputs_from_task(data: dict, task_file: str) -> list[dict[str, Any]]:
    """Extrahiert User-Inputs aus einem Task-JSON."""
    inputs: list[dict[str, Any]] = []
    task_id = Path(task_file).stem[:12]

    # Variante 1: messages Array
    messages = data.get("messages", data.get("conversation", []))
    if messages:
        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content", msg.get("text", ""))
            if not content or len(content) < 5:
                continue
            if not is_real_user_input(content):
                continue
            ts = msg.get("timestamp", data.get("timestamp", ""))
            dt = str(ts)[:16] if ts else "?"
            inputs.append({
                "date": dt,
                "content": content.strip()[:2000],
                "categories": categorize(content),
                "source": PLATFORM_ID,
                "session": task_id,
                "platform": PLATFORM_ID,
            })
        return inputs

    # Variante 2: Einzelner Input
    content = data.get("input", data.get("query", data.get("text", "")))
    if content and len(content) > 5 and is_real_user_input(content):
        ts = data.get("timestamp", data.get("createdAt", ""))
        dt = str(ts)[:16] if ts else "?"
        inputs.append({
            "date": dt,
            "content": content.strip()[:2000],
            "categories": categorize(content),
            "source": PLATFORM_ID,
            "session": task_id,
            "platform": PLATFORM_ID,
        })

    return inputs


def _extract_thread_from_task(data: dict, task_file: str) -> Thread | None:
    """Extrahiert einen Thread aus einem Task-JSON."""
    task_id = Path(task_file).stem[:12]
    messages: list[Message] = []

    # Variante 1: messages Array
    raw_msgs = data.get("messages", data.get("conversation", []))
    if raw_msgs:
        for msg in raw_msgs:
            role = msg.get("role", "user")
            content = msg.get("content", msg.get("text", ""))
            if not content or len(content) < 2:
                continue
            ts = msg.get("timestamp", data.get("timestamp", ""))
            dt = str(ts)[:16] if ts else "?"
            messages.append(Message(
                role=role if role in ("user", "assistant") else "user",
                content=content.strip()[:2000],
                timestamp=dt,
            ))
    else:
        # Variante 2: Einzelner Input
        content = data.get("input", data.get("query", data.get("text", "")))
        if content and len(content) > 5:
            ts = data.get("timestamp", data.get("createdAt", ""))
            dt = str(ts)[:16] if ts else "?"
            messages.append(Message(
                role="user",
                content=content.strip()[:2000],
                timestamp=dt,
            ))

    if not messages:
        return None

    all_user_text = " ".join(m.content for m in messages if m.is_user)
    cats = categorize(all_user_text)

    return Thread(
        id=task_id,
        platform=PLATFORM_ID,
        project="cline",
        title=messages[0].content[:60],
        date=messages[0].timestamp,
        messages=messages,
        categories=cats,
    )
