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
                            # Generisch: Jeden Workspace-Pfad als Input erfassen
                            if len(p) > 10:
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
    """Rekonstruiert Threads aus Gemini Desktop Protobuf-DBs.
    
    Verbesserte Extraktion:
      - Datum aus trajectory_meta oder DB-Datei-Modifikationszeit
      - Modell-Informationen aus gen_metadata
      - Bessere User/Agent-Trennung
    """
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
            model = "gemini"
            trajectory_id = ""

            # Trajectory-Metadata fuer Workspace
            try:
                for row in conn.execute("SELECT data FROM trajectory_metadata_blob"):
                    blob = row[0]
                    if blob and isinstance(blob, bytes):
                        paths = _extract_file_paths(blob)
                        if paths:
                            workspace = paths[0]
            except Exception:
                pass

            # Trajectory-Meta fuer ID
            try:
                for row in conn.execute("SELECT trajectory_id FROM trajectory_meta"):
                    trajectory_id = row[0] or ""
            except Exception:
                pass

            # Gen-Metadata fuer Modell-Info
            try:
                for row in conn.execute("SELECT data FROM gen_metadata LIMIT 1"):
                    if row[0] and isinstance(row[0], bytes):
                        meta_text = row[0].decode('utf-8', errors='ignore')
                        # Modell-Name extrahieren
                        model_match = re.search(r'(gemini-[a-z0-9\-\.]+)', meta_text)
                        if model_match:
                            model = model_match.group(1)
            except Exception:
                pass

            # Steps durchgehen
            try:
                for row in conn.execute("SELECT * FROM steps ORDER BY rowid"):
                    step_type = row[1] if len(row) > 1 else 0
                    
                    # User-Input aus Spalte 9 (step_payload)
                    payload = row[9] if len(row) > 9 else None
                    if payload and isinstance(payload, bytes):
                        texts = _extract_user_texts(payload)
                        for text in texts:
                            if _is_user_input(text):
                                messages.append(Message(
                                    role="user",
                                    content=text[:2000],
                                    model=model,
                                ))

                    # Agent-Output aus Spalte 4 (metadata)
                    meta = row[4] if len(row) > 4 else None
                    if meta and isinstance(meta, bytes):
                        texts = _extract_user_texts(meta)
                        for text in texts:
                            if _is_agent_output(text):
                                messages.append(Message(
                                    role="assistant",
                                    content=text[:2000],
                                    model=model,
                                ))
            except Exception:
                pass

            conn.close()

            if not messages:
                continue

            # Projekt aus Workspace-Pfad (generisch)
            project = "unknown"
            if workspace:
                project = os.path.basename(workspace.rstrip(os.sep)) or "unknown"

            # Datum aus DB-Datei-Modifikationszeit
            date_str = "?"
            try:
                mtime = os.path.getmtime(db_path)
                dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

            user_text = " ".join(m.content for m in messages if m.is_user)
            cats = categorize(user_text) if user_text else ["UNCATEGORIZED"]

            threads.append(Thread(
                id=f"gemini_desktop_{trajectory_id[:8] or db_idx}",
                platform=PLATFORM_ID,
                project=project,
                title=messages[0].content[:60] if messages else "?",
                date=date_str,
                messages=messages,
                categories=cats,
                metadata={
                    "workspace": workspace,
                    "db": os.path.basename(db_path),
                    "model": model,
                    "trajectory_id": trajectory_id,
                },
            ))
        except Exception:
            pass

    return threads


def _is_user_input(text: str) -> bool:
    """Prueft ob ein Text ein User-Input ist."""
    if not text or len(text) < 10:
        return False
    # JSON-Objekte mit User-Input
    if text.startswith('{') and 'Pattern' in text:
        return True
    # Normale Texte
    words = text.split()
    if len(words) < 2:
        return False
    # Nicht User-Input
    if text.startswith('sessionID'):
        return False
    if re.match(r'^[a-f0-9\-]+$', text):
        return False
    return True


def _is_agent_output(text: str) -> bool:
    """Prueft ob ein Text eine Agent-Antwort ist."""
    if not text or len(text) < 20:
        return False
    # Session-IDs filtern
    if 'sessionID' in text:
        return False
    # UUIDs filtern
    if re.match(r'^[a-f0-9\-]+$', text):
        return False
    # Bot-IDs filtern
    if text.startswith(':(bot-'):
        return False
    return True


def _extract_user_texts(blob: bytes) -> list[str]:
    """Extrahiert lesbare User-Texte aus Protobuf-Blobs.
    
    Verbesserte Extraktion:
      - Filtert UUIDs und Session-IDs
      - Erkennt JSON-Daten
      - Extrahiert tatsaechliche User-Nachrichten
    """
    texts = []
    current = []

    for byte in blob:
        if 32 <= byte <= 126 or byte in (10, 13, 9):
            current.append(chr(byte))
        else:
            if len(current) >= 8:
                s = "".join(current).strip()
                if s and len(s) >= 8:
                    # Filtere UUIDs und Session-IDs
                    if _is_valid_text(s):
                        texts.append(s)
            current = []

    if len(current) >= 8:
        s = "".join(current).strip()
        if s and _is_valid_text(s):
            texts.append(s)

    return texts


def _is_valid_text(s: str) -> bool:
    """Prueft ob ein String ein gueltiger User-Text ist."""
    # UUIDs filtern
    if re.match(r'^[a-f0-9\-]{36}$', s.lower()):
        return False
    if re.match(r'^b\$[a-f0-9\-]{36}$', s.lower()):
        return False
    
    # Session-IDs filtern
    if s.startswith('sessionID'):
        return False
    if 'sessionID' in s and len(s) < 60:
        return False
    
    # Bot-IDs filtern
    if re.match(r'^:\(bot-[a-f0-9\-]+', s):
        return False
    
    # Nur Zahlen filtern
    if re.match(r'^[0-9\s\-]+$', s):
        return False
    
    # Zu kurze Strings
    if len(s) < 10:
        return False
    
    # Commands filtern
    if s.startswith('command('):
        return False
    if s.startswith('call_'):
        return False
    
    # JSON-Objekte durchlassen (koennten User-Input enthalten)
    if s.startswith('{'):
        return True
    
    # Normale Texte: Mindestens 2 Woerter
    words = s.split()
    if len(words) < 2:
        return False
    
    return True


def _extract_file_paths(blob: bytes) -> list[str]:
    """Extrahiert Dateipfade aus Protobuf-Blobs.
    
    Behandelt Protobuf-Length-Prefixes (z.B. '9file:///...')
    """
    paths = []
    text = blob.decode("utf-8", errors="ignore")

    # file:/// URLs (mit oder ohne Protobuf-Length-Prefix)
    # Protobuf Length-Prefix ist eine Ziffer vor dem String
    for match in re.finditer(r"file:///[^\x00-\x1f\x7f-\x9f]+", text):
        url = match.group(0)
        # Pfad nach 'file:///' extrahieren
        p = url[7:]  # Remove 'file:///'
        # URL-Decode
        p = p.replace("%3A", ":").replace("%20", " ")
        # Windows-Pfad konvertieren
        if os.name == "nt" and p.startswith("/"):
            # /c:/Users/... -> C:\Users\...
            if len(p) > 2 and p[1].isalpha() and p[2] == ":":
                p = p[1].upper() + p[2:]
                p = p.replace("/", "\\")
        if len(p) > 5:
            paths.append(p)

    # Windows-Pfade (C:\...)
    for match in re.finditer(r"([A-Z]:\\[^\x00-\x1f\x7f-\x9f]{5,})", text):
        paths.append(match.group(1))

    # GitHub-URLs extrahieren
    for match in re.finditer(r"github\.com/([^/]+/[^/]+)", text):
        paths.append(match.group(1))

    return list(dict.fromkeys(paths))
