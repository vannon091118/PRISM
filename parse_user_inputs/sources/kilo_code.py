"""
parse_user_inputs.sources.kilo_code
=====================================
Kilo Code Reader — ~/.local/share/kilo/kilo.db (Drizzle ORM SQLite).

Schema:
  session  — Metadaten (title, parent_id, agent, model, tokens)
  message  — Rollen/Metadaten (role, agent, model) — KEIN Content!
  part     — EIGENTLICHER Content (text, tool_use, reasoning, etc.)

Reader Joint: session + message + part
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "kilo_code"


def _kilo_db_path() -> str:
    home = str(Path.home())
    candidates = [
        os.path.join(home, ".local", "share", "kilo", "kilo.db"),
        os.path.join(home, "AppData", "Local", "kilo", "kilo.db"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Kilo Code User-Inputs aus kilo.db."""
    inputs: list[dict[str, Any]] = []
    db_path = _kilo_db_path()

    if not os.path.exists(db_path):
        return inputs

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        # GROUP_CONCAT Limit erhoehen (fuer lange Messages)
        conn.execute("PRAGMA group_concat_limit = -1")

        # JOIN: message + parts -> User-Text
        for row in conn.execute("""
            SELECT m.id as msg_id, m.session_id, m.time_created,
                   m.data as msg_data,
                   GROUP_CONCAT(p.data, '|||') as parts_data
            FROM message m
            LEFT JOIN part p ON p.message_id = m.id
            WHERE m.data LIKE '%"role":"user"%'
            GROUP BY m.id
            ORDER BY m.time_created
        """):
            msg_data = json.loads(row["msg_data"] or "{}")
            if msg_data.get("role") != "user":
                continue

            content = _extract_text_from_parts(row["parts_data"] or "")
            if not content or len(content) < 5:
                continue
            if not is_real_user_input(content):
                continue

            dt = _ts_to_str(row["time_created"] or 0)
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


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert vollstaendige Threads aus kilo.db."""
    threads: list[Thread] = []
    db_path = _kilo_db_path()

    if not os.path.exists(db_path):
        return threads

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # 1. Alle Sessions laden (Haupt + Subagent)
        sessions: dict[str, dict] = {}
        for row in conn.execute("""
            SELECT id, title, directory, time_created, agent, model,
                   tokens_input, tokens_output, parent_id
            FROM session
            ORDER BY time_created
        """):
            sid = row["id"] or ""
            if not sid:
                continue
            pid = row["parent_id"] or ""

            sessions[sid] = {
                "title": row["title"] or "?",
                "directory": row["directory"] or "",
                "time_created": row["time_created"] or 0,
                "agent": row["agent"] or "",
                "model": row["model"] or "",
                "tokens_input": row["tokens_input"] or 0,
                "tokens_output": row["tokens_output"] or 0,
                "parent_id": pid,
                "messages": [],
            }

        # 2. Messages + Parts laden
        conn2 = sqlite3.connect(db_path)
        conn2.execute("PRAGMA group_concat_limit = -1")
        conn2.row_factory = sqlite3.Row
        for row in conn2.execute("""
            SELECT m.id as msg_id, m.session_id, m.data as msg_data, m.time_created,
                   GROUP_CONCAT(p.data, '|||') as parts_data
            FROM message m
            LEFT JOIN part p ON p.message_id = m.id
            WHERE m.session_id IN ({ids})
            GROUP BY m.id
            ORDER BY m.time_created
        """.format(ids=",".join(f"'{s}'" for s in sessions.keys()))):
            sid = row["session_id"] or ""
            if sid not in sessions:
                continue

            msg_data = json.loads(row["msg_data"] or "{}")
            role = msg_data.get("role", "user")
            content = _extract_text_from_parts(row["parts_data"] or "")

            if not content or len(content) < 2:
                continue

            ts = row["time_created"] or 0
            dt = _ts_to_str(ts)

            sessions[sid]["messages"].append(Message(
                role=role if role in ("user", "assistant") else "user",
                content=content.strip()[:2000],
                timestamp=dt,
            ))

        conn2.close()

        # 3. Threads erzeugen
        for sid, data in sessions.items():
            if not data["messages"]:
                continue
            if not any(m.is_user for m in data["messages"]):
                continue

            project = os.path.basename(data["directory"]) if data["directory"] else "kilo_code"
            all_user_text = " ".join(m.content for m in data["messages"] if m.is_user)
            cats = categorize(all_user_text)

            dt = _ts_to_str(data["time_created"])

            threads.append(Thread(
                id=sid[:12],
                platform=PLATFORM_ID,
                project=project,
                title=data["title"][:80],
                date=dt,
                messages=data["messages"],
                categories=cats,
                metadata={
                    "agent": data["agent"],
                    "model": _parse_model_name(data["model"]),
                    "tokens_input": data["tokens_input"],
                    "tokens_output": data["tokens_output"],
                },
            ))

    except Exception:
        pass

    return threads


def _extract_text_from_parts(parts_concat: str) -> str:
    """Extrahiert User-Text aus part-Tabelle (||| getrennt)."""
    if not parts_concat:
        return ""

    texts = []
    for part_str in parts_concat.split("|||"):
        if not part_str:
            continue
        try:
            part = json.loads(part_str)
        except json.JSONDecodeError:
            continue

        ptype = part.get("type", "")
        # Nur Text-Parts (keine tool_use, step-start, reasoning)
        if ptype == "text":
            text = part.get("text", "")
            if text and not part.get("synthetic"):
                texts.append(text)
        elif ptype == "tool-result":
            # Tool-Ergebnisse koennten User-Input enthalten
            pass

    return " ".join(texts)


def _parse_model_name(model_str: str) -> str:
    """Parst Modell-Name aus Kilo Code JSON."""
    if not model_str:
        return ""
    try:
        model = json.loads(model_str)
        return model.get("modelID", model.get("id", ""))
    except (json.JSONDecodeError, TypeError):
        return str(model_str)[:50]


def _ts_to_str(ts: float) -> str:
    if not ts:
        return "?"
    try:
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"
