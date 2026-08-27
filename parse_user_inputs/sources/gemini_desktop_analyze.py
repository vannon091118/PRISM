"""
parse_user_inputs.sources.gemini_desktop_analyze
=================================================
Analysiert Gemini Desktop (antigravity) Protobuf-DBs und extrahiert User-Inputs.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
from typing import Any


def analyze_gemini_dbs() -> dict[str, Any]:
    """Analysiert alle Gemini Desktop DBs."""
    home = str(os.path.expanduser("~"))
    conv_dir = os.path.join(home, ".gemini", "antigravity", "conversations")
    
    result = {
        "total_dbs": 0,
        "total_steps": 0,
        "workspaces": set(),
        "user_inputs": [],
        "table_schemas": {},
    }
    
    if not os.path.exists(conv_dir):
        return result
    
    dbs = sorted(glob.glob(os.path.join(conv_dir, "*.db")))
    result["total_dbs"] = len(dbs)
    
    for db_path in dbs:
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            # Tabellen finden
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            
            for table in tables:
                if table not in result["table_schemas"]:
                    try:
                        cols = [d[1] for d in conn.execute(
                            f"SELECT * FROM [{table}] LIMIT 1"
                        ).description]
                        result["table_schemas"][table] = cols
                    except:
                        pass
            
            # Steps zaehlen
            try:
                cnt = conn.execute("SELECT COUNT(*) FROM steps").fetchone()[0]
                result["total_steps"] += cnt
            except:
                pass
            
            # Trajectory-Metadata-Blobs haben Workspace-Pfade
            try:
                for row in conn.execute("SELECT value FROM trajectory_metadata_blob"):
                    blob = row[0]
                    if blob:
                        _extract_workspaces(blob, result["workspaces"])
            except:
                pass
            
            # Gen-Metadata hat User-Inputs in Protobuf
            try:
                for row in conn.execute("SELECT blob FROM gen_metadata"):
                    blob = row[0]
                    if blob:
                        inputs = _extract_strings_from_protobuf(blob)
                        for inp in inputs:
                            if len(inp) > 10 and not inp.startswith("\x00"):
                                result["user_inputs"].append(inp[:500])
            except:
                pass
            
            # Steps haben auch User-Inputs
            try:
                for row in conn.execute("SELECT step_data FROM steps LIMIT 100"):
                    blob = row[0]
                    if blob:
                        inputs = _extract_strings_from_protobuf(blob)
                        for inp in inputs:
                            if len(inp) > 10:
                                result["user_inputs"].append(inp[:500])
            except:
                pass
            
            # Executor-Metadata
            try:
                for row in conn.execute("SELECT data FROM executor_metadata"):
                    blob = row[0]
                    if blob:
                        inputs = _extract_strings_from_protobuf(blob)
                        for inp in inputs:
                            if len(inp) > 10:
                                result["user_inputs"].append(inp[:500])
            except:
                pass
            
            conn.close()
        except Exception as e:
            pass
    
    # Deduplizieren
    result["user_inputs"] = list(dict.fromkeys(result["user_inputs"]))
    result["workspaces"] = sorted(result["workspaces"])
    
    return result


def _extract_workspaces(blob: bytes, workspaces: set):
    """Extrahiert Workspace-Pfade aus Protobuf-Blobs."""
    # Einfach: Strings im Blob suchen die nach Dateipfaden aussehen
    text = blob.decode("utf-8", errors="ignore")
    
    # file:/// URLs
    urls = re.findall(r"file:///[^\x00-\x1f\x7f-\x9f]+", text)
    for u in urls:
        path = u.replace("file:///", "")
        if len(path) > 5:
            workspaces.add(path)
    
    # Windows-Pfade
    win_paths = re.findall(r"[A-Z]:\\[^\x00-\x1f\x7f-\x9f]+", text)
    for p in win_paths:
        if len(p) > 10 and ("users" in p.lower() or "documents" in p.lower()):
            workspaces.add(p)


def _extract_strings_from_protobuf(blob: bytes) -> list[str]:
    """Extrahiert lesbare Strings aus Protobuf-Blobs."""
    strings = []
    # Alle laengeren Strings die UTF-8 kompatibel sind
    current = []
    for byte in blob:
        if 32 <= byte <= 126 or byte in (10, 13, 9):  # printable + newline + tab
            current.append(chr(byte))
        else:
            if len(current) >= 8:
                s = "".join(current).strip()
                if s and len(s) >= 8:
                    strings.append(s)
            current = []
    
    if len(current) >= 8:
        s = "".join(current).strip()
        if s and len(s) >= 8:
            strings.append(s)
    
    return strings


if __name__ == "__main__":
    import json
    result = analyze_gemini_dbs()
    
    print(f"=== Gemini Desktop Analyse ===")
    print(f"DBs: {result['total_dbs']}")
    print(f"Steps: {result['total_steps']}")
    print(f"Workspaces: {len(result['workspaces'])}")
    for w in result['workspaces'][:10]:
        print(f"  {w}")
    print(f"Tabellen: {list(result['table_schemas'].keys())}")
    print(f"User-Inputs (extrahiert): {len(result['user_inputs'])}")
    for inp in result['user_inputs'][:20]:
        print(f"  > {inp[:120]}")
