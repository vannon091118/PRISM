"""
parse_user_inputs.sources.vscode_extensions
=============================================
Generischer Reader fuer VS Code Extensions (Cline, Roo, Kilo, Copilot).
Liest JSON-Dateien aus dem tasks/-Verzeichnis oder state.vscdb.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

# Extension-IDs die wir unterstuetzen
EXTENSION_IDS = ["cline", "roo_code", "kilo_code", "copilot"]


def scan_inputs(platform_id: str, platform: Any = None) -> list[dict[str, Any]]:
    """
    Liest User-Inputs aus einer VS Code Extension.

    Args:
        platform_id: z.B. "cline", "roo_code", "kilo_code", "copilot"
        platform: Platform-Objekt (optional, fuer resolve_paths)
    """
    if platform is None:
        return []

    inputs: list[dict[str, Any]] = []
    resolved = platform.resolve_paths()

    for path, desc, ftype in resolved:
        if not os.path.exists(path):
            continue

        if ftype == "directory":
            inputs.extend(_scan_task_files(path, platform_id))
        elif ftype == "sqlite":
            inputs.extend(_scan_vscdb(path, platform_id))

    return inputs


def reconstruct_threads(platform_id: str, platform: Any = None) -> list[Thread]:
    """Rekonstruiert Threads aus einer VS Code Extension."""
    if platform is None:
        return []

    threads: list[Thread] = []
    resolved = platform.resolve_paths()

    for path, desc, ftype in resolved:
        if not os.path.exists(path):
            continue

        if ftype == "directory":
            threads.extend(_threads_from_tasks(path, platform_id))
        elif ftype == "sqlite":
            threads.extend(_threads_from_vscdb(path, platform_id))

    return threads


def _scan_task_files(directory: str, platform_id: str) -> list[dict[str, Any]]:
    """Liest JSON-Task-Dateien aus einem Verzeichnis."""
    inputs: list[dict[str, Any]] = []

    for task_file in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = data.get("messages", data.get("conversation", []))
            if not messages:
                content = data.get("input", data.get("query", data.get("text", "")))
                if content and len(content) > 5 and is_real_user_input(content):
                    ts = data.get("timestamp", data.get("createdAt", ""))
                    dt = str(ts)[:16] if ts else "?"
                    inputs.append({
                        "date": dt,
                        "content": content.strip()[:2000],
                        "categories": categorize(content),
                        "source": platform_id,
                        "session": Path(task_file).stem[:12],
                        "platform": platform_id,
                    })
                continue

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
                    "source": platform_id,
                    "session": Path(task_file).stem[:12],
                    "platform": platform_id,
                })
        except Exception:
            pass

    return inputs


def _scan_vscdb(db_path: str, platform_id: str) -> list[dict[str, Any]]:
    """Liest User-Inputs aus einer VS Code state.vscdb."""
    inputs: list[dict[str, Any]] = []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        for table in tables:
            if not any(c in table.lower() for c in ["chat", "message", "conversation", "history"]):
                continue
            try:
                rows = conn.execute(f"SELECT * FROM [{table}] LIMIT 10").fetchall()
                if not rows:
                    continue
                cols = [d[0] for d in conn.execute(f"SELECT * FROM [{table}] LIMIT 1").description]
                for row in rows:
                    for col in cols:
                        val = str(row[cols.index(col)] or "")
                        if len(val) > 50 and is_real_user_input(val):
                            inputs.append({
                                "date": "?",
                                "content": val[:2000],
                                "categories": categorize(val),
                                "source": platform_id,
                                "session": table[:12],
                                "platform": platform_id,
                            })
                            break
            except Exception:
                continue

        conn.close()
    except Exception:
        pass

    return inputs


def _threads_from_tasks(directory: str, platform_id: str) -> list[Thread]:
    """Rekonstruiert Threads aus Task-Dateien."""
    threads: list[Thread] = []

    for task_file in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = data.get("messages", data.get("conversation", []))
            if not messages:
                content = data.get("input", data.get("query", data.get("text", "")))
                if content and len(content) > 5 and is_real_user_input(content):
                    threads.append(Thread(
                        id=Path(task_file).stem[:12],
                        platform=platform_id,
                        project=platform_id,
                        title=content[:60],
                        date="?",
                        messages=[Message(role="user", content=content.strip()[:2000])],
                        categories=categorize(content),
                    ))
                continue

            thread_msgs = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", msg.get("text", ""))
                if content and len(content) > 2:
                    thread_msgs.append(Message(
                        role=role if role in ("user", "assistant") else "user",
                        content=content.strip()[:2000],
                    ))

            if thread_msgs:
                user_text = " ".join(m.content for m in thread_msgs if m.is_user)
                threads.append(Thread(
                    id=Path(task_file).stem[:12],
                    platform=platform_id,
                    project=platform_id,
                    title=thread_msgs[0].content[:60],
                    date="?",
                    messages=thread_msgs,
                    categories=categorize(user_text),
                ))
        except Exception:
            pass

    return threads


def _threads_from_vscdb(db_path: str, platform_id: str) -> list[Thread]:
    """Rekonstruiert Threads aus state.vscdb."""
    # Vereinfacht: Nutzt die gleiche Logik wie scan
    inputs = _scan_vscdb(db_path, platform_id)
    if not inputs:
        return []

    threads = []
    for inp in inputs:
        threads.append(Thread(
            id=inp["session"],
            platform=platform_id,
            project=platform_id,
            title=inp["content"][:60],
            date=inp["date"],
            messages=[Message(role="user", content=inp["content"])],
            categories=inp["categories"],
        ))
    return threads
