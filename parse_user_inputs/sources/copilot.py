"""
parse_user_inputs.sources/copilot.py
======================================
GitHub Copilot Reader.

Speicherort:
  VS Code Extension:
    Windows: %APPDATA%/Code/User/globalStorage/github.copilot-chat/
    Linux:   ~/.config/Code/User/globalStorage/github.copilot-chat/
    macOS:   ~/Library/Application Support/Code/User/globalStorage/github.copilot-chat/

  Copilot CLI (Agent):
    ~/.copilot/otel/*.jsonl

  Workspace Storage:
    %APPDATA%/Code/User/workspaceStorage/<workspaceId>/github.copilot/

Copilot speichert Chat-Data in JSON-Dateien unter:
  - ask-agent/     — Ask Copilot Sessions
  - explore-agent/ — Code-Exploration Sessions
  - plan-agent/    — Planungs-Sessions
  - copilotCli/    — CLI-sessions

Zusatlich: OTEL (OpenTelemetry) Logs in JSONL-Format.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "copilot"


def _copilot_dirs() -> list[str]:
    """Findet alle Copilot Chat-Verzeichnisse."""
    home = str(Path.home())
    candidates = [
        # VS Code Extension (Windows)
        os.path.join(home, "AppData", "Roaming", "Code", "User", "globalStorage",
                      "github.copilot-chat"),
        # VS Code Extension (Linux)
        os.path.join(home, ".config", "Code", "User", "globalStorage",
                      "github.copilot-chat"),
        # VS Code Extension (macOS)
        os.path.join(home, "Library", "Application Support", "Code", "User", "globalStorage",
                      "github.copilot-chat"),
        # VS Code Remote
        os.path.join(home, ".vscode-server", "data", "User", "globalStorage",
                      "github.copilot-chat"),
    ]
    return [p for p in candidates if os.path.exists(p)]


def _otel_files() -> list[str]:
    """Findet Copilot OTEL JSONL-Dateien."""
    home = str(Path.home())
    otel_dir = os.path.join(home, ".copilot", "otel")
    if os.path.exists(otel_dir):
        return sorted(glob.glob(os.path.join(otel_dir, "*.jsonl")))
    return []


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Copilot User-Inputs."""
    inputs: list[dict[str, Any]] = []

    # 1. VS Code Extension Chat-Dateien
    for copilot_dir in _copilot_dirs():
        for agent_dir in ["ask-agent", "explore-agent", "plan-agent", "copilotCli"]:
            agent_path = os.path.join(copilot_dir, agent_dir)
            if not os.path.exists(agent_path):
                continue
            for json_file in sorted(glob.glob(os.path.join(agent_path, "*.json"))):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    inputs.extend(_extract_from_chat_json(data, json_file, agent_dir))
                except Exception:
                    pass

    # 2. OTEL Logs (JSONL)
    for otel_file in _otel_files():
        try:
            inputs.extend(_extract_from_otel(otel_file))
        except Exception:
            pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Copilot Daten."""
    threads: list[Thread] = []

    for copilot_dir in _copilot_dirs():
        for agent_dir in ["ask-agent", "explore-agent", "plan-agent", "copilotCli"]:
            agent_path = os.path.join(copilot_dir, agent_dir)
            if not os.path.exists(agent_path):
                continue
            for json_file in sorted(glob.glob(os.path.join(agent_path, "*.json"))):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    thread = _extract_thread_from_chat_json(data, json_file, agent_dir)
                    if thread:
                        threads.append(thread)
                except Exception:
                    pass

    # OTEL als Fallback wenn keine Chat-Dateien
    if not threads:
        for otel_file in _otel_files():
            try:
                threads.extend(_threads_from_otel(otel_file))
            except Exception:
                pass

    return threads


def _extract_from_chat_json(data: dict, json_file: str, agent: str) -> list[dict[str, Any]]:
    """Extrahiert User-Inputs aus Copilot Chat-JSON."""
    inputs: list[dict[str, Any]] = []
    task_id = Path(json_file).stem[:12]

    # Copilot Chat-Formate
    messages = data.get("messages", data.get("conversation", data.get("history", [])))
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            if role != "user":
                continue
            content = msg.get("content", msg.get("text", ""))
            if isinstance(content, list):
                # Array von Parts
                texts = []
                for part in content:
                    if isinstance(part, dict):
                        texts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        texts.append(part)
                content = " ".join(texts)
            if not content or len(str(content)) < 5:
                continue
            if not is_real_user_input(str(content)):
                continue
            ts = msg.get("timestamp", data.get("timestamp", ""))
            dt = str(ts)[:16] if ts else "?"
            inputs.append({
                "date": dt,
                "content": str(content).strip()[:2000],
                "categories": categorize(str(content)),
                "source": PLATFORM_ID,
                "session": task_id,
                "platform": PLATFORM_ID,
                "project": agent,
            })

    # Einzelner Input
    if not inputs:
        content = data.get("input", data.get("query", data.get("text", "")))
        if content and len(str(content)) > 5 and is_real_user_input(str(content)):
            ts = data.get("timestamp", data.get("createdAt", ""))
            dt = str(ts)[:16] if ts else "?"
            inputs.append({
                "date": dt,
                "content": str(content).strip()[:2000],
                "categories": categorize(str(content)),
                "source": PLATFORM_ID,
                "session": task_id,
                "platform": PLATFORM_ID,
                "project": agent,
            })

    return inputs


def _extract_thread_from_chat_json(data: dict, json_file: str, agent: str) -> Thread | None:
    """Extrahiert einen Thread aus Copilot Chat-JSON."""
    task_id = Path(json_file).stem[:12]
    messages: list[Message] = []

    raw_msgs = data.get("messages", data.get("conversation", data.get("history", [])))
    if isinstance(raw_msgs, list):
        for msg in raw_msgs:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "user")
            content = msg.get("content", msg.get("text", ""))
            if isinstance(content, list):
                texts = []
                for part in content:
                    if isinstance(part, dict):
                        texts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        texts.append(part)
                content = " ".join(texts)
            if not content or len(str(content)) < 2:
                continue
            ts = msg.get("timestamp", data.get("timestamp", ""))
            dt = str(ts)[:16] if ts else "?"
            messages.append(Message(
                role=role if role in ("user", "assistant") else "user",
                content=str(content).strip()[:2000],
                timestamp=dt,
            ))
    else:
        content = data.get("input", data.get("query", data.get("text", "")))
        if content and len(str(content)) > 5:
            ts = data.get("timestamp", data.get("createdAt", ""))
            dt = str(ts)[:16] if ts else "?"
            messages.append(Message(
                role="user",
                content=str(content).strip()[:2000],
                timestamp=dt,
            ))

    if not messages:
        return None

    all_user_text = " ".join(m.content for m in messages if m.is_user)
    cats = categorize(all_user_text)

    return Thread(
        id=task_id,
        platform=PLATFORM_ID,
        project=agent,
        title=messages[0].content[:60],
        date=messages[0].timestamp,
        messages=messages,
        categories=cats,
    )


def _extract_from_otel(otel_file: str) -> list[dict[str, Any]]:
    """Extrahiert User-Inputs aus OTEL JSONL."""
    inputs: list[dict[str, Any]] = []

    with open(otel_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # OTEL Span-Format
            name = entry.get("name", "")
            attrs = entry.get("attributes", {})
            if "user" in name.lower() or attrs.get("role") == "user":
                content = attrs.get("content", attrs.get("input", attrs.get("message", "")))
                if content and len(str(content)) > 5 and is_real_user_input(str(content)):
                    ts = entry.get("timestamp", entry.get("startTimeUnixNano", ""))
                    dt = str(ts)[:16] if ts else "?"
                    inputs.append({
                        "date": dt,
                        "content": str(content).strip()[:2000],
                        "categories": categorize(str(content)),
                        "source": PLATFORM_ID,
                        "session": Path(otel_file).stem[:12],
                        "platform": PLATFORM_ID,
                    })

    return inputs


def _threads_from_otel(otel_file: str) -> list[Thread]:
    """Rekonstruiert Threads aus OTEL Logs."""
    threads: list[Thread] = []
    messages: list[Message] = []

    with open(otel_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            attrs = entry.get("attributes", {})
            role = attrs.get("role", "")
            content = attrs.get("content", attrs.get("input", ""))
            if not content or len(str(content)) < 2:
                continue
            ts = entry.get("timestamp", "")
            dt = str(ts)[:16] if ts else "?"
            messages.append(Message(
                role=role if role in ("user", "assistant") else "user",
                content=str(content).strip()[:2000],
                timestamp=dt,
            ))

    if messages:
        all_user_text = " ".join(m.content for m in messages if m.is_user)
        cats = categorize(all_user_text)
        threads.append(Thread(
            id=Path(otel_file).stem[:12],
            platform=PLATFORM_ID,
            project="copilot",
            title=messages[0].content[:60],
            date=messages[0].timestamp,
            messages=messages,
            categories=cats,
        ))

    return threads
