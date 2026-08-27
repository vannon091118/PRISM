"""
parse_user_inputs.sources.freebuff
===================================
Freebuff Desktop Reader — API-basiert (User -> Agent vollstaendig).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from parse_user_inputs.categorizer import categorize
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "freebuff"
API_BASE = "http://127.0.0.1:55703"


def _api_get(path: str, timeout: int = 10) -> dict | None:
    """Holt Daten von der Freebuff API."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{API_BASE}{path}")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception:
        return None


def scan_inputs() -> list[dict[str, Any]]:
    """Liest User-Inputs aus der Freebuff API."""
    inputs: list[dict[str, Any]] = []
    data = _api_get("/api/projects")
    if not data:
        return inputs

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
                    dt = _ts_to_str(ts)
                    inputs.append({
                        "date": dt,
                        "content": text[:2000],
                        "categories": categorize(text),
                        "source": PLATFORM_ID,
                        "session": tid[:12],
                        "platform": PLATFORM_ID,
                        "thread_title": title[:80],
                    })
    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert vollstaendige Threads aus Freebuff Desktop API."""
    threads: list[Thread] = []
    data = _api_get("/api/projects")
    if not data:
        return threads

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

            # Artefakte sammeln
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
                artifacts.append({
                    "type": "branch",
                    "name": branch,
                })

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


def _extract_project_name(proj_path: str) -> str:
    """Extrahiert den Projekt-Namen aus dem Pfad."""
    if not proj_path:
        return "unknown"
    lower = proj_path.lower()
    if "snip-war" in lower:
        return "snip-war"
    if "snippet-empire" in lower:
        return "snippet-empire"
    return os.path.basename(proj_path)


def _ts_to_str(ts: float) -> str:
    """Konvertiert Millisecond-Timestamp zu Datumsstring."""
    if not ts:
        return "?"
    try:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"
