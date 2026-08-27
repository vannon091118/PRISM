"""
parse_user_inputs.sources.gemini_desktop
=========================================
Gemini Desktop (antigravity) Reader — Protobuf-DBs aus conversations/.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from parse_user_inputs.categorizer import categorize
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "gemini_desktop"


def _conv_dir() -> str:
    return os.path.join(str(os.path.expanduser("~")), ".gemini", "antigravity", "conversations")


def scan_inputs() -> list[dict[str, Any]]:
    """Liest User-Inputs aus Gemini Desktop Protobuf-DBs."""
    inputs: list[dict[str, Any]] = []
    conv_dir = _conv_dir()

    if not os.path.exists(conv_dir):
        return inputs

    dbs = sorted(glob.glob(os.path.join(conv_dir, "*.db")))

    for db_path in dbs:
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            # Steps-Tabelle: Spalte 10 hat User-Input-Text
            try:
                for row in conn.execute("SELECT * FROM steps"):
                    blob = row[10] if len(row) > 10 else None
                    if not blob or not isinstance(blob, bytes):
                        continue

                    # Protobuf-Strings extrahieren
                    texts = _extract_user_texts(blob)
                    for text in texts:
                        if len(text) < 10:
                            continue
                        # Befehle filtern
                        if text.startswith("command("):
                            continue
                        if text.startswith("sessionID"):
                            continue
                        if re.match(r'^[0-9]+$', text):
                            continue

                        inputs.append({
                            "date": "?",
                            "content": text[:2000],
                            "categories": categorize(text),
                            "source": PLATFORM_ID,
                            "session": os.path.basename(db_path)[:12],
                            "platform": PLATFORM_ID,
                        })
            except Exception:
                pass

            # Trajectory-Metadata-Blob hat Workspace-Pfade
            try:
                for row in conn.execute("SELECT value FROM trajectory_metadata_blob"):
                    blob = row[0]
                    if blob and isinstance(blob, bytes):
                        paths = _extract_file_paths(blob)
                        # Workspace-Pfad als Projekt-Info
                        for p in paths:
                            if "snippet-empire" in p.lower() or "snip-war" in p.lower():
                                inputs.append({
                                    "date": "?",
                                    "content": f"Workspace: {p}",
                                    "categories": categorize(p),
                                    "source": PLATFORM_ID,
                                    "session": os.path.basename(db_path)[:12],
                                    "platform": PLATFORM_ID,
                                })
            except Exception:
                pass

            conn.close()
        except Exception:
            pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Gemini Desktop Protobuf-DBs."""
    threads: list[Thread] = []
    conv_dir = _conv_dir()

    if not os.path.exists(conv_dir):
        return threads

    dbs = sorted(glob.glob(os.path.join(conv_dir, "*.db")))

    for db_idx, db_path in enumerate(dbs):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            messages: list[Message] = []
            workspace = ""

            # Trajectory-Metadata fuer Workspace
            try:
                for row in conn.execute("SELECT value FROM trajectory_metadata_blob"):
                    blob = row[0]
                    if blob and isinstance(blob, bytes):
                        paths = _extract_file_paths(blob)
                        if paths:
                            workspace = paths[0]
            except Exception:
                pass

            # Steps durchgehen
            try:
                for row in conn.execute("SELECT * FROM steps ORDER BY rowid"):
                    # User-Input aus Spalte 10
                    blob = row[10] if len(row) > 10 else None
                    if blob and isinstance(blob, bytes):
                        texts = _extract_user_texts(blob)
                        for text in texts:
                            if len(text) < 10:
                                continue
                            if text.startswith("command("):
                                continue
                            if text.startswith("sessionID"):
                                continue
                            if re.match(r'^[0-9]+$', text):
                                continue

                            messages.append(Message(
                                role="user",
                                content=text[:2000],
                            ))

                    # Agent-Output aus Spalte 4 (andere Blob-Spalte)
                    blob4 = row[4] if len(row) > 4 else None
                    if blob4 and isinstance(blob4, bytes):
                        texts = _extract_user_texts(blob4)
                        for text in texts:
                            if len(text) > 20 and not text.startswith("sessionID"):
                                messages.append(Message(
                                    role="assistant",
                                    content=text[:2000],
                                ))
            except Exception:
                pass

            conn.close()

            if not messages:
                continue

            # Projekt aus Workspace-Pfad
            project = "unknown"
            if workspace:
                lower = workspace.lower()
                if "snip-war" in lower:
                    project = "snip-war"
                elif "snippet-empire" in lower:
                    project = "snippet-empire"
                elif "godu" in lower or "godot" in lower:
                    project = "godot-project"
                else:
                    project = os.path.basename(workspace)

            user_text = " ".join(m.content for m in messages if m.is_user)
            cats = categorize(user_text) if user_text else ["UNCATEGORIZED"]

            threads.append(Thread(
                id=f"gemini_desktop_{db_idx}",
                platform=PLATFORM_ID,
                project=project,
                title=messages[0].content[:60] if messages else "?",
                date="?",
                messages=messages,
                categories=cats,
                metadata={"workspace": workspace, "db": os.path.basename(db_path)},
            ))
        except Exception:
            pass

    return threads


def _extract_user_texts(blob: bytes) -> list[str]:
    """Extrahiert lesbare User-Texte aus Protobuf-Blobs."""
    texts = []
    current = []

    for byte in blob:
        if 32 <= byte <= 126 or byte in (10, 13, 9):
            current.append(chr(byte))
        else:
            if len(current) >= 10:
                s = "".join(current).strip()
                if s and len(s) >= 10:
                    texts.append(s)
            current = []

    if len(current) >= 10:
        s = "".join(current).strip()
        if s:
            texts.append(s)

    return texts


def _extract_file_paths(blob: bytes) -> list[str]:
    """Extrahiert Dateipfade aus Protobuf-Blobs."""
    paths = []
    text = blob.decode("utf-8", errors="ignore")

    # file:/// URLs
    for match in re.finditer(r"file:///([^\x00-\x1f\x7f-\x9f]+)", text):
        p = match.group(1).replace("/", "\\") if os.name == "nt" else match.group(1)
        if len(p) > 5:
            paths.append(p)

    # Windows-Pfade
    for match in re.finditer(r"([A-Z]:\\[^\x00-\x1f\x7f-\x9f]{5,})", text):
        paths.append(match.group(1))

    return list(dict.fromkeys(paths))
