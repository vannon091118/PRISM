#!/usr/bin/env python3
"""
parse_user_inputs.py V4 — Trennt USER-INPUTS von Agent-Halluzinationen.

Quellen:
  1. Hermes state.db — User-Messages, Assistant-Reasoning, Tool-Outputs
  2. request_dump JSONs — Volle Conversations-Historien bei API-Fehlern
  3. Git-Commits — Rekonstruierte User-Intentionen
  4. Paste-PNGs — Visuelle User-Inputs (Screenshots)

Usage:
    python parse_user_inputs.py                          # auto-detect project
    python parse_user_inputs.py /path/to/project
    python parse_user_inputs.py --output /path/to/out.md
    python parse_user_inputs.py --html /path/to/out.html  # HTML-Dashboard
    python parse_user_inputs.py --html dashboard.html --output /dev/null
"""

import sqlite3
import json
import os
import sys
import glob
import html as html_mod
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

DEFAULT_DB = r"C:\Users\Vannon\AppData\Local\hermes\state.db"
DEFAULT_SESSIONS_DIR = r"C:\Users\Vannon\AppData\Local\hermes\sessions"
PASTE_DIR = r"C:\Users\Vannon\AppData\Local\Temp\freebuff-desktop-pastes"
DEFAULT_OUTPUT = "USER_INPUTS_ARTIFACT.md"

CATEGORIES = {
    "MCP_ADDON": ["addon", "plugin", "modul", "eigenes", "kompatibl",
                  "bauen", "entwickl", "marketplace", "mcp"],
    "ENTKOPPELUNG": ["entkoppl", "projektagnost", "project-agnostic",
                     "snipwar", "vermischt", "eigenes repo", "standalone",
                     "portabel", "portable", "automatisch registri"],
    "HEADLESS_VERBOT": ["headless verbot", "headless", "nur sichtbar",
                        "visible", "sichtbar ist valide", "hedless", "heless"],
    "GAMEPLAY": ["3 planeten", "ressourcenket", "tutorial", "spielen",
                 "erstes schiff", "schiff bauen", "werft", "forschung",
                 "orbitale", "sichtbar", "RESULT=FAIL", "durchspielen"],
    "QA_TEST": ["qa", "preflight", "contract", "vertrag", "constraint",
                "test runner", "findings", "finding", "audit", "verify",
                "autonom", "test"],
    "BUG": ["bug", "fix", "fehler", "kaputt", "broken", "crash", "error",
            "nicht funktioniert", "schlägt fehl"],
    "DOKU": ["doku", "dokument", "readme", "doc", "handoff", "hinweis",
             "schreib", "erklär", "erkl"],
    "REFACTOR": ["refactor", "umbau", "umstrukturier", "aufräum", "cleanup",
                 "separation of concern"],
    "FEATURE": ["feature", "neu bau", "ergänz", "hinzufüg", "erweiter",
                "neues tool", "neue tool"],
    "SERVER_START": ["einrichten", "starten", "server", "port", "9090", "9091"],
    "COST": ["cost", "token", "budget", "modell", "nvidia", "glm", "deepseek"],
    "SUCHSYSTEM": ["grep", "ripgrep", "search", "suchen", "find", "concept",
                   "global search", "global_search", "concept_index"],
    "REMOTE_CONTROL": ["remote", "remote control", "sichtbar", "live test",
                       "debugging", "e2e", "playthrough"],
}


def categorize(text):
    text_lower = text.lower()
    cats = []
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                cats.append(cat)
                break
    return cats if cats else ["UNCATEGORIZED"]


def is_real_user_input(content):
    if not content or not content.strip():
        return False
    c = content.strip()
    if c.startswith("[/init]"):
        return False
    if c.startswith("[IMPORTANT: The user has invoked"):
        return False
    if c.lower().startswith("here's a thinking process"):
        return False
    if c.startswith("⚡ Interrupt"):
        return False
    if c.startswith("continue working toward"):
        return False
    if c.startswith("[Note: model was just switched"):
        return False
    if c.startswith("[System: The previous response was cut off"):
        return False
    if c.startswith("[Context from the interrupted"):
        return False
    if c.startswith("> ") and len(c) < 100:
        return False
    return True


def is_project_session(title, model, content):
    combined = f"{title or ''} {model or ''} {content or ''}".lower()
    markers = ["snip", "mcp", "preflight", "playthrough", "goal_player",
               "runtime_", "headless", "visible", "autonomy", "contract",
               "dossier", "forschung", "werft", "schiff", "planet", "fleet",
               "combat", "godot", "gdscript", "addon", "plugin"]
    return any(m in combined for m in markers)


def read_state_db(db_path):
    inputs = []
    if not os.path.exists(db_path):
        return inputs
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for row in conn.execute("""
        SELECT m.content, m.timestamp, m.session_id,
               s.title, s.model, s.started_at
        FROM messages m LEFT JOIN sessions s ON m.session_id = s.id
        WHERE m.role = 'user' AND m.active = 1
        ORDER BY m.timestamp
    """):
        content = row["content"] or ""
        title = row["title"] or ""
        model = row["model"] or ""
        if not is_real_user_input(content):
            continue
        if not is_project_session(title, model, content):
            continue
        ts = row["timestamp"] or 0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "?"
        inputs.append({
            "date": dt,
            "content": content.strip(),
            "categories": categorize(content),
            "source": "state_db",
            "session": (row["session_id"] or "")[:12],
        })
    conn.close()
    return inputs


def read_state_db_assistant(db_path):
    """Extrahiert Assistant-Reasoning-Snippets (die eigentliche Agent-Memory)."""
    entries = []
    if not os.path.exists(db_path):
        return entries
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for row in conn.execute("""
        SELECT m.content, m.timestamp, m.session_id,
               s.title, s.model
        FROM messages m LEFT JOIN sessions s ON m.session_id = s.id
        WHERE m.role = 'assistant' AND m.active = 1
        ORDER BY m.timestamp
    """):
        content = row["content"] or ""
        if len(content) < 50:
            continue
        # Reasoning-Snippets: Things zwischen <thinking> Tags oder erste 500 Chars
        reasoning = ""
        # Versuche <thinking> ... </thinking> zu extrahieren
        think_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
        if think_match:
            reasoning = think_match.group(1).strip()[:500]
        else:
            # Sonst die ersten 500 Zeichen
            reasoning = content.strip()[:500]

        if not reasoning or len(reasoning) < 30:
            continue

        ts = row["timestamp"] or 0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "?"
        entries.append({
            "date": dt,
            "reasoning": reasoning,
            "content_len": len(content),
            "session": (row["session_id"] or "")[:12],
            "model": row["model"] or "?",
        })
    conn.close()
    return entries


def read_state_db_tools(db_path):
    """Extrahiert Tool-Usage-Statistiken aus Tool-Messages."""
    tools = Counter()
    tool_sizes = Counter()
    tool_sessions = {}
    if not os.path.exists(db_path):
        return {"counter": tools, "sizes": tool_sizes, "sessions": tool_sessions}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for row in conn.execute("""
        SELECT m.content, m.timestamp, m.session_id
        FROM messages m
        WHERE m.role = 'tool' AND m.active = 1
        ORDER BY m.timestamp
    """):
        content = row["content"] or ""
        content_len = len(content)

        # Versuche Tool-Name zu extrahieren aus Content
        # Tool messages haben oft "Tool: <name>" oder JSON mit "tool"
        tool_name = "unknown"
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                tool_name = data.get("tool", data.get("name", "unknown"))
        except (json.JSONDecodeError, TypeError):
            # Versuche aus Content-Pattern zu extrahieren
            if "run_terminal_command" in content:
                tool_name = "run_terminal_command"
            elif "read_files" in content or "read_file" in content:
                tool_name = "read_files"
            elif "code_search" in content:
                tool_name = "code_search"
            elif "str_replace" in content:
                tool_name = "str_replace"
            elif "write_file" in content:
                tool_name = "write_file"
            elif "glob" in content:
                tool_name = "glob"
            elif "list_directory" in content:
                tool_name = "list_directory"
            elif "preview_" in content:
                tool_name = "preview"
            elif "web_search" in content:
                tool_name = "web_search"
            elif "git" in content.lower():
                tool_name = "git"

        tools[tool_name] += 1
        tool_sizes[tool_name] += content_len

        sid = (row["session_id"] or "")[:12]
        if sid not in tool_sessions:
            tool_sessions[sid] = {"count": 0, "total_bytes": 0}
        tool_sessions[sid]["count"] += 1
        tool_sessions[sid]["total_bytes"] += content_len

    conn.close()
    return {"counter": dict(tools), "sizes": dict(tool_sizes), "sessions": tool_sessions}


def read_state_db_memory_stats(db_path):
    """Berechnet Memory-Statistiken pro Session und Rolle."""
    stats = {"total_bytes": 0, "by_role": {}, "by_session": {}}
    if not os.path.exists(db_path):
        return stats
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    for row in conn.execute("""
        SELECT role, session_id, SUM(LENGTH(content)) as bytes, COUNT(*) as cnt
        FROM messages WHERE active = 1
        GROUP BY role, session_id
    """):
        role = row["role"]
        sid = (row["session_id"] or "")[:12]
        b = row["bytes"] or 0

        stats["total_bytes"] += b
        stats["by_role"][role] = stats["by_role"].get(role, 0) + b
        if sid not in stats["by_session"]:
            stats["by_session"][sid] = {"user": 0, "assistant": 0, "tool": 0, "total": 0}
        stats["by_session"][sid][role] = b
        stats["by_session"][sid]["total"] += b

    # Session titles
    for row in conn.execute("SELECT id, title FROM sessions"):
        sid = (row["id"] or "")[:12]
        if sid in stats["by_session"]:
            stats["by_session"][sid]["title"] = (row["title"] or "?")[:60]

    conn.close()
    return stats


def read_request_dumps(sessions_dir):
    inputs = []
    for fpath in sorted(glob.glob(os.path.join(sessions_dir, "request_dump_*.json"))):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            req = data.get("request", {})
            body = req.get("body", {})
            msgs = body.get("messages", [])
            sid = data.get("session_id", "?")
            ts = data.get("timestamp", "?")
            for m in msgs:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    if content and len(content) > 5 and is_real_user_input(content):
                        dt = ts[:16].replace("T", " ") if ts else "?"
                        inputs.append({
                            "date": dt,
                            "content": content.strip()[:2000],
                            "categories": categorize(content),
                            "source": "request_dump",
                            "session": sid[:12] if sid else "?",
                            "file": os.path.basename(fpath),
                        })
        except Exception:
            pass
    return inputs


def read_freebuff_threads(project_filter="snip-war"):
    """Extrahiert User-Inputs aus Freebuff Desktop Threads via lokaler API."""
    inputs = []
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:55703/api/projects")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
    except Exception:
        return inputs

    for proj in data.get("projects", []):
        path = proj.get("path", "")
        if project_filter not in path.lower():
            continue
        for t in proj.get("threads", []):
            tid = t["id"]
            title = t.get("title", "?")
            model = t.get("model", "?")
            try:
                req2 = urllib.request.Request(f"http://127.0.0.1:55703/api/thread/{tid}")
                resp2 = urllib.request.urlopen(req2, timeout=10)
                detail = json.loads(resp2.read())
                for m in detail.get("messages", []):
                    if m.get("role") != "user":
                        continue
                    for p in m.get("parts", []):
                        if p.get("kind") == "text":
                            text = p.get("text", "").strip()
                            if text and len(text) > 3:
                                ts = m.get("ts", 0)
                                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "?"
                                inputs.append({
                                    "date": dt,
                                    "content": text[:2000],
                                    "categories": categorize(text),
                                    "source": "freebuff_thread",
                                    "session": tid[:12],
                                    "thread_title": title[:80],
                                    "model": model,
                                })
            except Exception:
                pass
    return inputs


def read_paste_images(paste_dir):
    import struct
    images = []
    if not os.path.exists(paste_dir):
        return images
    for fname in sorted(os.listdir(paste_dir)):
        if not fname.endswith(".png"):
            continue
        fpath = os.path.join(paste_dir, fname)
        size = os.path.getsize(fpath)
        parts = fname.replace(".png", "").split("-")
        ts_str = "?"
        if len(parts) >= 3:
            try:
                ts_millis = int(parts[1])
                dt = datetime.fromtimestamp(ts_millis / 1000, tz=timezone.utc)
                ts_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        dims = "?x?"
        try:
            with open(fpath, "rb") as f:
                header = f.read(30)
                if header[:8] == b"\x89PNG\r\n\x1a\n":
                    w = struct.unpack(">I", header[16:20])[0]
                    h = struct.unpack(">I", header[20:24])[0]
                    dims = f"{w}x{h}"
        except Exception:
            pass
        images.append({
            "date": ts_str,
            "dims": dims,
            "size_kb": size // 1024,
            "file": fname,
            "fpath": fpath,
            "source": "paste_png",
        })
    return images


def read_git_commits(project_path):
    import subprocess
    results = []
    try:
        proc = subprocess.run(
            ["git", "log", "--since=2026-08-18", "--format=%h|%ad|%s", "--date=short"],
            cwd=project_path, capture_output=True, text=True, timeout=10
        )
        for line in proc.stdout.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue
            results.append({"date": parts[1], "hash": parts[0], "subject": parts[2]})
    except Exception:
        pass
    return results


# ─── HTML Dashboard Generator ───────────────────────────────────────────────

def generate_html_dashboard(unique, git_commits, paste_images, output_path,
                            project_path, assistant_entries=None, tool_data=None,
                            memory_stats=None):
    """Erzeugt ein self-contained HTML Dashboard mit Canvas/DOM-Optik."""

    cat_counts = {}
    for inp in unique:
        for c in inp["categories"]:
            cat_counts[c] = cat_counts.get(c, 0) + 1

    by_date = {}
    for c in git_commits:
        by_date.setdefault(c["date"], []).append(c)

    # Paste-PNGs als data-URIs
    paste_data = []
    for img in paste_images:
        try:
            with open(img["fpath"], "rb") as f:
                raw = f.read()
            import base64
            b64 = base64.b64encode(raw).decode()
            paste_data.append({
                "file": html_mod.escape(img["file"]),
                "date": html_mod.escape(img["date"]),
                "dims": html_mod.escape(img["dims"]),
                "size_kb": img["size_kb"],
                "data_uri": f"data:image/png;base64,{b64}",
            })
        except Exception:
            paste_data.append({
                "file": html_mod.escape(img["file"]),
                "date": html_mod.escape(img["date"]),
                "dims": html_mod.escape(img["dims"]),
                "size_kb": img["size_kb"],
                "data_uri": "",
            })

    inputs_json = json.dumps([{
        "idx": i + 1,
        "date": html_mod.escape(inp["date"]),
        "content": html_mod.escape(inp["content"][:2000]),
        "categories": inp["categories"],
        "source": inp["source"],
        "session": html_mod.escape(inp["session"]),
    } for i, inp in enumerate(unique)], ensure_ascii=False)

    cat_json = json.dumps(cat_counts, ensure_ascii=False)
    timeline_json = json.dumps([{
        "date": d,
        "count": len(cs),
        "subjects": [c["subject"][:80] for c in cs],
    } for d, cs in sorted(by_date.items())], ensure_ascii=False)
    paste_json = json.dumps(paste_data, ensure_ascii=False)

    # Memory Stats
    ms = memory_stats or {"total_bytes": 0, "by_role": {}, "by_session": {}}
    ms_json = json.dumps(ms, ensure_ascii=False)

    # Assistant Reasoning (top snippets)
    ae = assistant_entries or []
    reasoning_json = json.dumps([{
        "date": html_mod.escape(e["date"]),
        "reasoning": html_mod.escape(e["reasoning"][:600]),
        "content_len": e["content_len"],
        "session": html_mod.escape(e["session"]),
        "model": html_mod.escape(e["model"]),
    } for e in ae[:80]], ensure_ascii=False)

    # Tool Stats
    td = tool_data or {"counter": {}, "sizes": {}, "sessions": {}}
    tool_json = json.dumps(td, ensure_ascii=False)

    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    mem_mb = ms["total_bytes"] / 1024 / 1024
    user_mb = ms["by_role"].get("user", 0) / 1024 / 1024
    asst_mb = ms["by_role"].get("assistant", 0) / 1024 / 1024
    tool_mb = ms["by_role"].get("tool", 0) / 1024 / 1024
    coverage_pct = (len(unique) * 221 / ms["total_bytes"] * 100) if ms["total_bytes"] > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>User-Inputs Dashboard V4 — {html_mod.escape(project_path)}</title>
<style>
  :root {{
    --bg: #0d1117; --bg2: #161b22; --bg3: #21262d;
    --border: #30363d; --text: #e6edf3; --text2: #8b949e;
    --accent: #58a6ff; --accent2: #3fb950; --accent3: #d2a8ff;
    --warn: #f0883e; --err: #f85149;
    --radius: 12px; --shadow: 0 8px 32px rgba(0,0,0,0.4);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
    min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a1e2e 100%);
    border-bottom: 1px solid var(--border); padding: 32px 48px;
  }}
  .header h1 {{
    font-size: 28px; font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent3));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .header .meta {{ color: var(--text2); font-size: 13px; margin-top: 6px; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 48px; }}
  .stats-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-bottom: 32px;
  }}
  .stat-card {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px 20px;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .stat-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow); }}
  .stat-card .label {{ color: var(--text2); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }}
  .stat-card .value {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
  .stat-card .sub {{ color: var(--text2); font-size: 11px; margin-top: 2px; }}
  .stat-card .value.blue {{ color: var(--accent); }}
  .stat-card .value.green {{ color: var(--accent2); }}
  .stat-card .value.purple {{ color: var(--accent3); }}
  .stat-card .value.orange {{ color: var(--warn); }}
  .stat-card .value.red {{ color: var(--err); }}
  .section {{ margin-bottom: 40px; }}
  .section-title {{
    font-size: 18px; font-weight: 600; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }}
  .section-title .icon {{ font-size: 20px; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .chart-row-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }}
  @media (max-width: 1100px) {{ .chart-row-3 {{ grid-template-columns: 1fr; }} }}
  @media (max-width: 900px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
  .chart-box {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px; overflow: hidden;
  }}
  .chart-box canvas {{ width: 100% !important; height: auto !important; }}
  .timeline {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 24px;
  }}
  .timeline-day {{ margin-bottom: 16px; }}
  .timeline-date {{
    font-size: 14px; font-weight: 600; color: var(--accent); margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
  }}
  .timeline-date .badge {{
    background: var(--bg3); border-radius: 12px; padding: 2px 10px;
    font-size: 11px; color: var(--text2); font-weight: 400;
  }}
  .timeline-commits {{ padding-left: 20px; }}
  .timeline-commits li {{
    color: var(--text2); font-size: 13px; margin-bottom: 2px; list-style: none;
  }}
  .timeline-commits li::before {{ content: "\\2192 "; color: var(--accent2); }}
  .paste-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
  }}
  .paste-card {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s; cursor: pointer;
  }}
  .paste-card:hover {{ transform: scale(1.03); box-shadow: var(--shadow); }}
  .paste-card img {{
    width: 100%; height: 140px; object-fit: cover;
    background: var(--bg3); display: block;
  }}
  .paste-card .info {{
    padding: 8px 12px; font-size: 11px; color: var(--text2);
  }}
  .paste-card .info strong {{ color: var(--text); }}
  .modal-overlay {{
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.85); z-index: 1000;
    justify-content: center; align-items: center;
  }}
  .modal-overlay.active {{ display: flex; }}
  .modal-overlay img {{ max-width: 90vw; max-height: 90vh; border-radius: 8px; }}
  .inputs-search {{
    width: 100%; padding: 12px 16px;
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: var(--radius); color: var(--text);
    font-size: 14px; margin-bottom: 16px; outline: none;
  }}
  .inputs-search:focus {{ border-color: var(--accent); }}
  .inputs-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .input-card {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px 20px;
    transition: border-color 0.2s;
  }}
  .input-card:hover {{ border-color: var(--accent); }}
  .input-card .head {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px; flex-wrap: wrap; gap: 6px;
  }}
  .input-card .idx {{ color: var(--accent); font-weight: 700; font-size: 13px; }}
  .input-card .date {{ color: var(--text2); font-size: 12px; }}
  .input-card .tags {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .input-card .tag {{
    background: var(--bg3); border-radius: 8px; padding: 2px 8px;
    font-size: 10px; color: var(--accent3); text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .input-card .body {{
    color: var(--text2); font-size: 13px; white-space: pre-wrap;
    word-break: break-word; max-height: 120px; overflow: hidden;
    position: relative;
  }}
  .input-card .body.expanded {{ max-height: none; }}
  .input-card .expand-btn {{
    color: var(--accent); font-size: 12px; cursor: pointer;
    margin-top: 6px; user-select: none;
  }}
  .reasoning-card {{
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px 20px;
    margin-bottom: 8px;
  }}
  .reasoning-card .meta {{
    display: flex; gap: 12px; margin-bottom: 8px; flex-wrap: wrap;
  }}
  .reasoning-card .meta span {{
    color: var(--text2); font-size: 11px;
  }}
  .reasoning-card .meta .model {{ color: var(--accent3); }}
  .reasoning-card .snippet {{
    color: var(--text2); font-size: 13px; white-space: pre-wrap;
    word-break: break-word; font-family: 'SF Mono', 'Fira Code', monospace;
    max-height: 150px; overflow: hidden; position: relative;
  }}
  .reasoning-card .snippet.expanded {{ max-height: none; }}
  .reasoning-card .expand-btn {{
    color: var(--accent); font-size: 12px; cursor: pointer;
    margin-top: 6px; user-select: none;
  }}
  .mem-bar {{
    display: flex; height: 32px; border-radius: 6px; overflow: hidden;
    margin-bottom: 8px;
  }}
  .mem-bar div {{ display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; }}
  .mem-bar .user {{ background: var(--accent); color: var(--bg); }}
  .mem-bar .asst {{ background: var(--accent3); color: var(--bg); }}
  .mem-bar .tool {{ background: var(--warn); color: var(--bg); }}
  .filter-chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }}
  .chip {{
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 16px; padding: 4px 12px; font-size: 12px;
    color: var(--text2); cursor: pointer; transition: all 0.2s;
  }}
  .chip.active {{ background: var(--accent); color: var(--bg); border-color: var(--accent); }}
  .chip:hover {{ border-color: var(--accent); }}
  .footer {{
    text-align: center; padding: 32px; color: var(--text2);
    font-size: 12px; border-top: 1px solid var(--border);
  }}
  .tab-bar {{ display: flex; gap: 0; margin-bottom: 16px; }}
  .tab {{
    padding: 8px 16px; background: var(--bg3); border: 1px solid var(--border);
    color: var(--text2); cursor: pointer; font-size: 13px; transition: all 0.2s;
  }}
  .tab:first-child {{ border-radius: var(--radius) 0 0 var(--radius); }}
  .tab:last-child {{ border-radius: 0 var(--radius) var(--radius) 0; }}
  .tab.active {{ background: var(--accent); color: var(--bg); border-color: var(--accent); }}
</style>
</head>
<body>
<div class="header">
  <h1>&#9876; User-Inputs Dashboard V4</h1>
  <div class="meta">Projekt: {html_mod.escape(project_path)} &middot; Erstellt: {today} &middot; Datenquellen: state.db (User + Assistant + Tool) + request_dumps + Git + Paste-PNGs</div>
</div>
<div class="container">
  <!-- Stats -->
  <div class="stats-grid" id="stats"></div>

  <!-- Memory Volume -->
  <div class="section">
    <div class="section-title"><span class="icon">&#128200;</span> Memory-Volumen-Analyse</div>
    <div class="chart-box">
      <div class="mem-bar" id="memBar"></div>
      <div id="memLegend" style="display:flex;gap:16px;margin-bottom:12px;"></div>
      <div id="memDetail"></div>
      <canvas id="memChart" height="200" style="margin-top:12px;"></canvas>
    </div>
  </div>

  <!-- Charts Row -->
  <div class="chart-row">
    <div class="chart-box">
      <div class="section-title"><span class="icon">&#128202;</span> User-Intentionen nach Kategorie</div>
      <canvas id="catChart" height="300"></canvas>
    </div>
    <div class="chart-box">
      <div class="section-title"><span class="icon">&#128197;</span> Aktivitat pro Tag</div>
      <canvas id="activityChart" height="300"></canvas>
    </div>
  </div>

  <!-- Tool Usage -->
  <div class="section" style="margin-top:32px">
    <div class="section-title"><span class="icon">&#128295;</span> Tool-Nutzungs-Statistik</div>
    <div class="chart-row">
      <div class="chart-box">
        <div class="section-title" style="font-size:14px">Aufrufe pro Tool</div>
        <canvas id="toolChart" height="300"></canvas>
      </div>
      <div class="chart-box">
        <div class="section-title" style="font-size:14px">Daten pro Tool (KB)</div>
        <canvas id="toolSizeChart" height="300"></canvas>
      </div>
    </div>
  </div>

  <!-- Reasoning Snippets -->
  <div class="section">
    <div class="section-title"><span class="icon">&#129504;</span> Top Assistant-Reasoning-Snippets</div>
    <div id="reasoningList"></div>
  </div>

  <!-- Timeline -->
  <div class="section">
    <div class="section-title"><span class="icon">&#128197;</span> Commit-Timeline</div>
    <div class="timeline" id="timeline"></div>
  </div>

  <!-- Paste-PNGs -->
  <div class="section">
    <div class="section-title"><span class="icon">&#128444;</span> Visuelle User-Inputs (Paste-PNGs)</div>
    <div class="paste-grid" id="pasteGrid"></div>
  </div>

  <!-- User Inputs -->
  <div class="section">
    <div class="section-title"><span class="icon">&#128172;</span> Alle echten User-Inputs</div>
    <input class="inputs-search" id="searchInput" placeholder="&#128269; Suche in User-Inputs..." autocomplete="off">
    <div class="filter-chips" id="filterChips"></div>
    <div class="inputs-list" id="inputsList"></div>
  </div>
</div>
<div class="modal-overlay" id="modal"><img id="modalImg" src="" alt="Full size"></div>
<div class="footer">
  parse_user_inputs.py V4 &middot; Nur echte User-Inputs &middot; Assistant-Reasoning &middot; Tool-Outputs<br>
  User-Inputs: {len(unique)} &middot; Assistant-Snippets: {len(ae)} &middot; Git-Commits: {len(git_commits)} &middot; Paste-PNGs: {len(paste_images)}<br>
  Memory: {mem_mb:.1f} MB (User: {user_mb:.1f} MB, Assistant: {asst_mb:.1f} MB, Tool: {tool_mb:.1f} MB)
</div>

<script>
// ── Data ────────────────────────────────────────────────────────────────────
const USER_INPUTS = {inputs_json};
const CAT_COUNTS = {cat_json};
const TIMELINE = {timeline_json};
const PASTE_IMAGES = {paste_json};
const MEM_STATS = {ms_json};
const REASONING = {reasoning_json};
const TOOL_DATA = {tool_json};

// ── Stats ───────────────────────────────────────────────────────────────────
const statsEl = document.getElementById('stats');
const memMB = (MEM_STATS.total_bytes / 1024 / 1024).toFixed(1);
const userMB = ((MEM_STATS.by_role.user || 0) / 1024 / 1024).toFixed(1);
const asstMB = ((MEM_STATS.by_role.assistant || 0) / 1024 / 1024).toFixed(1);
const toolMB = ((MEM_STATS.by_role.tool || 0) / 1024 / 1024).toFixed(1);
const coveragePct = MEM_STATS.total_bytes > 0 ? ((USER_INPUTS.length * 221 / MEM_STATS.total_bytes) * 100).toFixed(1) : 0;
const statsData = [
  {{ label: 'User-Inputs', value: USER_INPUTS.length, cls: 'blue', sub: coveragePct + '% der Memory' }},
  {{ label: 'Assistant-Snippets', value: REASONING.length, cls: 'purple', sub: 'Reasoning extrahiert' }},
  {{ label: 'Git-Commits', value: TIMELINE.reduce((a,d) => a + d.count, 0), cls: 'green', sub: 'Agent-Arbeit' }},
  {{ label: 'Paste-PNGs', value: PASTE_IMAGES.length, cls: 'orange', sub: 'Visuelle Inputs' }},
  {{ label: 'Memory Gesamt', value: memMB + ' MB', cls: 'red', sub: 'User ' + userMB + ' / Asst ' + asstMB + ' / Tool ' + toolMB }},
];
statsData.forEach(s => {{
  statsEl.innerHTML += `<div class="stat-card"><div class="label">${{s.label}}</div><div class="value ${{s.cls}}">${{s.value}}</div><div class="sub">${{s.sub}}</div></div>`;
}});

// ── Memory Bar ──────────────────────────────────────────────────────────────
(function() {{
  const bar = document.getElementById('memBar');
  const legend = document.getElementById('memLegend');
  const detail = document.getElementById('memDetail');
  const total = MEM_STATS.total_bytes || 1;
  const roles = [
    {{ key: 'user', label: 'User', cls: 'user' }},
    {{ key: 'assistant', label: 'Assistant', cls: 'asst' }},
    {{ key: 'tool', label: 'Tool', cls: 'tool' }},
  ];
  let barHtml = '';
  let legendHtml = '';
  let detailHtml = '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
  detailHtml += '<tr style="color:var(--text2)"><th style="text-align:left;padding:4px 8px">Session</th><th style="text-align:right;padding:4px 8px">User</th><th style="text-align:right;padding:4px 8px">Assistant</th><th style="text-align:right;padding:4px 8px">Tool</th><th style="text-align:right;padding:4px 8px">Total</th></tr>';
  roles.forEach(r => {{
    const bytes = MEM_STATS.by_role[r.key] || 0;
    const pct = (bytes / total * 100).toFixed(1);
    const mb = (bytes / 1024 / 1024).toFixed(1);
    barHtml += `<div class="${{r.cls}}" style="width:${{pct}}%">${{pct > 8 ? r.label : ''}}</div>`;
    legendHtml += `<span style="color:var(--text2);font-size:12px"><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:var(--${{r.key === 'user' ? 'accent' : r.key === 'assistant' ? 'accent3' : 'warn'}});vertical-align:middle;margin-right:4px"></span>${{r.label}}: ${{mb}} MB (${{pct}}%)</span>`;
  }});
  bar.innerHTML = barHtml;
  legend.innerHTML = legendHtml;
  // Session detail table
  const sessions = Object.entries(MEM_STATS.by_session || {{}}).sort((a,b) => b[1].total - a[1].total);
  sessions.forEach(([sid, s]) => {{
    detailHtml += `<tr style="border-top:1px solid var(--border);color:var(--text2)"><td style="padding:4px 8px;font-family:monospace;font-size:11px">${{sid}}.. ${{s.title ? '- ' + s.title : ''}}</td><td style="text-align:right;padding:4px 8px">${{(s.user/1024).toFixed(0)}} KB</td><td style="text-align:right;padding:4px 8px">${{(s.assistant/1024).toFixed(0)}} KB</td><td style="text-align:right;padding:4px 8px">${{(s.tool/1024).toFixed(0)}} KB</td><td style="text-align:right;padding:4px 8px;font-weight:600">${{(s.total/1024).toFixed(0)}} KB</td></tr>`;
  }});
  detailHtml += '</table>';
  detail.innerHTML = detailHtml;

  // Memory donut chart
  const canvas = document.getElementById('memChart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 40;
  const h = 200;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(dpr, dpr);
  const cx = w / 2, cy = h / 2, r = 70;
  let startAngle = -Math.PI / 2;
  const colors = {{ user: '#58a6ff', assistant: '#d2a8ff', tool: '#f0883e' }};
  roles.forEach(role => {{
    const bytes = MEM_STATS.by_role[role.key] || 0;
    const slice = (bytes / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, startAngle, startAngle + slice);
    ctx.fillStyle = colors[role.key];
    ctx.fill();
    startAngle += slice;
  }});
  ctx.beginPath(); ctx.arc(cx, cy, 40, 0, Math.PI * 2);
  ctx.fillStyle = '#161b22'; ctx.fill();
  ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 18px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(memMB + ' MB', cx, cy + 6);
}})();

// ── Canvas: Category Chart ──────────────────────────────────────────────────
(function() {{
  const canvas = document.getElementById('catChart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const cats = Object.entries(CAT_COUNTS).sort((a,b) => b[1] - a[1]);
  const maxVal = Math.max(...cats.map(c => c[1]));
  const barH = 28, gap = 6, pad = 12, labelW = 140;
  const w = canvas.parentElement.clientWidth - 40;
  const h = cats.length * (barH + gap) + pad * 2;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(dpr, dpr);
  const colors = ['#58a6ff','#3fb950','#d2a8ff','#f0883e','#f85149','#79c0ff','#56d364','#bc8cff','#ffa657','#ff7b72','#a5d6ff','#7ee787','#d2a8ff'];
  cats.forEach(([cat, count], i) => {{
    const y = pad + i * (barH + gap);
    const barW = (count / maxVal) * (w - labelW - pad - 60);
    ctx.fillStyle = '#8b949e'; ctx.font = '12px -apple-system, sans-serif';
    ctx.textAlign = 'right'; ctx.fillText(cat, labelW - 8, y + barH / 2 + 4);
    const grad = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
    const c = colors[i % colors.length];
    grad.addColorStop(0, c); grad.addColorStop(1, c + '66');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.roundRect(labelW, y, barW, barH, 4); ctx.fill();
    ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 12px -apple-system, sans-serif';
    ctx.textAlign = 'left'; ctx.fillText(count, labelW + barW + 8, y + barH / 2 + 4);
  }});
}})();

// ── Canvas: Activity Chart ──────────────────────────────────────────────────
(function() {{
  const canvas = document.getElementById('activityChart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const data = TIMELINE;
  if (!data.length) return;
  const maxVal = Math.max(...data.map(d => d.count));
  const w = canvas.parentElement.clientWidth - 40;
  const h = 300;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.scale(dpr, dpr);
  const pad = {{ top: 20, right: 20, bottom: 60, left: 50 }};
  const cw = w - pad.left - pad.right;
  const ch = h - pad.top - pad.bottom;
  ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {{
    const y = pad.top + (ch / 5) * i;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillStyle = '#8b949e'; ctx.font = '11px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxVal - (maxVal / 5) * i), pad.left - 8, y + 4);
  }}
  const barW = Math.min(40, (cw / data.length) - 4);
  data.forEach((d, i) => {{
    const x = pad.left + (cw / data.length) * i + (cw / data.length - barW) / 2;
    const barH = (d.count / maxVal) * ch;
    const y = pad.top + ch - barH;
    const grad = ctx.createLinearGradient(0, y, 0, pad.top + ch);
    grad.addColorStop(0, '#58a6ff'); grad.addColorStop(1, '#58a6ff22');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.roundRect(x, y, barW, barH, 4); ctx.fill();
    ctx.save(); ctx.translate(x + barW / 2, pad.top + ch + 12);
    ctx.rotate(-Math.PI / 4); ctx.fillStyle = '#8b949e';
    ctx.font = '11px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(d.date, 0, 0); ctx.restore();
    ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center'; ctx.fillText(d.count, x + barW / 2, y - 6);
  }});
}})();

// ── Canvas: Tool Charts ─────────────────────────────────────────────────────
(function() {{
  const counter = TOOL_DATA.counter || {{}};
  const sizes = TOOL_DATA.sizes || {{}};
  // Tool calls chart
  const entries = Object.entries(counter).sort((a,b) => b[1] - a[1]).slice(0, 15);
  if (entries.length) {{
    const canvas = document.getElementById('toolChart');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const maxVal = Math.max(...entries.map(e => e[1]));
    const w = canvas.parentElement.clientWidth - 40;
    const h = 300;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);
    const barH = 18, gap = 4, pad = 10, labelW = 140;
    entries.forEach(([name, count], i) => {{
      const y = pad + i * (barH + gap);
      const barW = (count / maxVal) * (w - labelW - pad - 40);
      ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
      ctx.textAlign = 'right'; ctx.fillText(name, labelW - 8, y + barH / 2 + 4);
      const grad = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
      grad.addColorStop(0, '#f0883e'); grad.addColorStop(1, '#f0883e44');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.roundRect(labelW, y, barW, barH, 3); ctx.fill();
      ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'left'; ctx.fillText(count, labelW + barW + 6, y + barH / 2 + 4);
    }});
  }}
  // Tool size chart
  const sizeEntries = Object.entries(sizes).sort((a,b) => b[1] - a[1]).slice(0, 15);
  if (sizeEntries.length) {{
    const canvas = document.getElementById('toolSizeChart');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const maxVal = Math.max(...sizeEntries.map(e => e[1]));
    const w = canvas.parentElement.clientWidth - 40;
    const h = 300;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);
    const barH = 18, gap = 4, pad = 10, labelW = 140;
    sizeEntries.forEach(([name, bytes], i) => {{
      const y = pad + i * (barH + gap);
      const barW = (bytes / maxVal) * (w - labelW - pad - 60);
      ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
      ctx.textAlign = 'right'; ctx.fillText(name, labelW - 8, y + barH / 2 + 4);
      const grad = ctx.createLinearGradient(labelW, 0, labelW + barW, 0);
      grad.addColorStop(0, '#3fb950'); grad.addColorStop(1, '#3fb95044');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.roundRect(labelW, y, barW, barH, 3); ctx.fill();
      const kb = (bytes / 1024).toFixed(0);
      ctx.fillStyle = '#e6edf3'; ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'left'; ctx.fillText(kb + ' KB', labelW + barW + 6, y + barH / 2 + 4);
    }});
  }}
}})();

// ── Timeline ────────────────────────────────────────────────────────────────
(function() {{
  const el = document.getElementById('timeline');
  TIMELINE.forEach(d => {{
    let commits = d.subjects.map(s => `<li>${{s}}</li>`).join('');
    el.innerHTML += `<div class="timeline-day">
      <div class="timeline-date">${{d.date}} <span class="badge">${{d.count}} commits</span></div>
      <ul class="timeline-commits">${{commits}}</ul>
    </div>`;
  }});
}})();

// ── Reasoning Snippets ──────────────────────────────────────────────────────
(function() {{
  const el = document.getElementById('reasoningList');
  REASONING.slice(0, 50).forEach((r, i) => {{
    const card = document.createElement('div');
    card.className = 'reasoning-card';
    card.innerHTML = `<div class="meta">
        <span>${{r.date}}</span>
        <span class="model">${{r.model}}</span>
        <span>${{r.session}}..</span>
        <span>${{(r.content_len/1024).toFixed(0)}} KB msg</span>
      </div>
      <div class="snippet" id="rsn-${{i}}">${{r.reasoning}}</div>
      <div class="expand-btn" onclick="toggleReasoning(${{i}})">&#9656; Mehr</div>`;
    el.appendChild(card);
  }});
}})();

function toggleReasoning(idx) {{
  const el = document.getElementById('rsn-' + idx);
  const btn = el.nextElementSibling;
  el.classList.toggle('expanded');
  btn.textContent = el.classList.contains('expanded') ? '&#9662; Weniger' : '\u25B6 Mehr';
}}

// ── Paste-PNGs ──────────────────────────────────────────────────────────────
(function() {{
  const grid = document.getElementById('pasteGrid');
  const modal = document.getElementById('modal');
  const modalImg = document.getElementById('modalImg');
  PASTE_IMAGES.forEach(p => {{
    const card = document.createElement('div');
    card.className = 'paste-card';
    card.innerHTML = `<img src="${{p.data_uri || ''}}" alt="${{p.file}}" loading="lazy">
      <div class="info"><strong>${{p.date}}</strong><br>${{p.dims}} &middot; ${{p.size_kb}}KB</div>`;
    card.onclick = () => {{ if (p.data_uri) {{ modalImg.src = p.data_uri; modal.classList.add('active'); }} }};
    grid.appendChild(card);
  }});
  modal.onclick = () => modal.classList.remove('active');
}})();

// ── Filter Chips + User Inputs ──────────────────────────────────────────────
(function() {{
  const allCats = [...new Set(USER_INPUTS.flatMap(i => i.categories))].sort();
  const chipsEl = document.getElementById('filterChips');
  const listEl = document.getElementById('inputsList');
  const searchEl = document.getElementById('searchInput');
  let activeFilter = null;

  allCats.forEach(cat => {{
    const chip = document.createElement('span');
    chip.className = 'chip'; chip.textContent = cat;
    chip.onclick = () => {{
      activeFilter = activeFilter === cat ? null : cat;
      document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      if (activeFilter) chip.classList.add('active');
      render();
    }};
    chipsEl.appendChild(chip);
  }});

  function render() {{
    const q = searchEl.value.toLowerCase();
    const filtered = USER_INPUTS.filter(i => {{
      if (activeFilter && !i.categories.includes(activeFilter)) return false;
      if (q && !i.content.toLowerCase().includes(q) && !i.categories.join(' ').toLowerCase().includes(q)) return false;
      return true;
    }});
    listEl.innerHTML = '';
    filtered.forEach(i => {{
      const tags = i.categories.map(c => `<span class="tag">${{c}}</span>`).join('');
      const card = document.createElement('div');
      card.className = 'input-card';
      card.innerHTML = `<div class="head">
          <span><span class="idx">#${{i.idx}}</span> &middot; <span class="date">${{i.date}}</span> &middot; ${{i.source}} &middot; ${{i.session}}..</span>
          <div class="tags">${{tags}}</div>
        </div>
        <div class="body" id="body-${{i.idx}}">${{i.content}}</div>
        <div class="expand-btn" onclick="toggleBody(${{i.idx}})">\u25B6 Mehr anzeigen</div>`;
      listEl.appendChild(card);
    }});
    if (!filtered.length) listEl.innerHTML = '<div style="color:var(--text2);padding:24px;text-align:center">Keine Treffer.</div>';
  }}
  searchEl.oninput = render;
  render();
}})();

function toggleBody(idx) {{
  const el = document.getElementById('body-' + idx);
  const btn = el.nextElementSibling;
  el.classList.toggle('expanded');
  btn.textContent = el.classList.contains('expanded') ? '\u25BE Weniger' : '\u25B6 Mehr anzeigen';
}}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    project_path = None
    output_path = None
    html_path = None
    db_path = DEFAULT_DB
    sessions_dir = DEFAULT_SESSIONS_DIR

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]; i += 2
        elif args[i] == "--html" and i + 1 < len(args):
            html_path = args[i + 1]; i += 2
        elif args[i] == "--hermes-db" and i + 1 < len(args):
            db_path = args[i + 1]; i += 2
        elif args[i] == "--sessions-dir" and i + 1 < len(args):
            sessions_dir = args[i + 1]; i += 2
        elif args[i] in ("--help", "-h"):
            print(__doc__); return
        elif not args[i].startswith("-"):
            project_path = args[i]; i += 1
        else:
            i += 1

    if not project_path:
        for candidate in [Path.cwd(), Path.cwd().parent]:
            if (candidate / ".git").exists() or (candidate / "project.godot").exists():
                project_path = str(candidate); break
    if not project_path:
        project_path = str(Path.cwd())
    if not output_path:
        output_path = os.path.join(project_path, DEFAULT_OUTPUT)

    print(f"Projekt: {project_path}")
    print(f"Hermes DB: {db_path}")
    print(f"Sessions Dir: {sessions_dir}")
    print(f"Output MD: {output_path}")
    if html_path:
        print(f"Output HTML: {html_path}")

    # ─── Quellen: User Inputs ────────────────────────────────────────────────
    db_inputs = read_state_db(db_path)
    print(f"  state.db User-Inputs: {len(db_inputs)}")

    dump_inputs = read_request_dumps(sessions_dir)
    print(f"  request_dump User-Inputs: {len(dump_inputs)}")

    git_commits = read_git_commits(project_path)
    print(f"  Git-Commits: {len(git_commits)}")

    paste_images = read_paste_images(PASTE_DIR)
    print(f"  Paste-PNGs: {len(paste_images)}")

    freebuff_inputs = read_freebuff_threads()
    print(f"  Freebuff Desktop Threads: {len(freebuff_inputs)}")

    # ─── Quellen: Assistant + Tool ───────────────────────────────────────────
    assistant_entries = read_state_db_assistant(db_path)
    print(f"  Assistant-Reasoning-Snippets: {len(assistant_entries)}")

    tool_data = read_state_db_tools(db_path)
    print(f"  Tool-Aufrufe: {sum(tool_data['counter'].values())} ({len(tool_data['counter'])} verschiedene Tools)")

    memory_stats = read_state_db_memory_stats(db_path)
    mem_mb = memory_stats['total_bytes'] / 1024 / 1024
    print(f"  Memory Gesamt: {mem_mb:.1f} MB")
    for role, b in memory_stats['by_role'].items():
        print(f"    {role}: {b/1024/1024:.1f} MB")

    # ─── Merge + Dedup ───────────────────────────────────────────────────────
    all_inputs = db_inputs + dump_inputs + freebuff_inputs
    seen = set()
    unique = []
    for inp in all_inputs:
        key = (inp["session"], inp["content"][:100])
        if key not in seen:
            seen.add(key)
            unique.append(inp)
    unique.sort(key=lambda x: x["date"])

    print(f"  Einzigartige User-Inputs: {len(unique)}")
    print(f"  Memory-Coverage: {len(unique) * 221 / memory_stats['total_bytes'] * 100:.1f}% der Gesamt-Memory")

    # ─── Markdown Artefakt ───────────────────────────────────────────────────
    if output_path and output_path != "/dev/null":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# User-Inputs Artifact V4\n\n")
            f.write(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Projekt:** `{project_path}`\n")
            f.write(f"**Memory Gesamt:** {mem_mb:.1f} MB\n")
            f.write(f"**Quellen:** state.db ({len(db_inputs)} user + {len(assistant_entries)} assistant + {sum(tool_data['counter'].values())} tool) + request_dumps ({len(dump_inputs)}) + Git ({len(git_commits)}) + Paste-PNGs ({len(paste_images)})\n")
            f.write(f"**User-Inputs gesamt:** {len(unique)} (dedupliziert)\n\n")
            f.write("---\n\n")

            cat_counts = {}
            for inp in unique:
                for c in inp["categories"]:
                    cat_counts[c] = cat_counts.get(c, 0) + 1
            if cat_counts:
                f.write("## User-Intentionen nach Kategorie\n\n")
                f.write("| Kategorie | Anzahl |\n|-----------|--------|\n")
                for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
                    f.write(f"| {cat} | {count} |\n")
                f.write("\n---\n\n")

            # Tool-Stats
            if tool_data['counter']:
                f.write("## Tool-Nutzung\n\n")
                f.write("| Tool | Aufrufe | Daten |\n|------|---------|-------|\n")
                for name, count in sorted(tool_data['counter'].items(), key=lambda x: -x[1]):
                    kb = tool_data['sizes'].get(name, 0) / 1024
                    f.write(f"| {name} | {count} | {kb:.0f} KB |\n")
                f.write("\n---\n\n")

            # Top Reasoning
            if assistant_entries:
                f.write("## Top Assistant-Reasoning-Snippets\n\n")
                for e in assistant_entries[:30]:
                    f.write(f"### {e['date']} ({e['model']}) — {e['content_len']//1024} KB\n\n")
                    f.write(f"```\n{e['reasoning']}\n```\n\n")
                f.write("---\n\n")

            if git_commits:
                f.write("## Rekonstruierte Timeline (Git-Commits)\n\n")
                by_date = {}
                for c in git_commits:
                    by_date.setdefault(c["date"], []).append(c)
                for date in sorted(by_date.keys()):
                    commits = by_date[date]
                    f.write(f"### {date} ({len(commits)} Commits)\n\n")
                    for c in commits:
                        f.write(f"- `{c['hash']}` {c['subject']}\n")
                    f.write("\n")
                f.write("---\n\n")

            f.write("## Alle echten User-Inputs\n\n")
            f.write("> Nur tatsaechliche User-Nachrichten. Keine System-Messages,\n")
            f.write("> keine Skill-Invocations, keine Agent-Antworten.\n\n")
            for idx, inp in enumerate(unique, 1):
                cats = ", ".join(inp["categories"])
                content = inp["content"][:2000]
                f.write(f"### [{idx}] {inp['date']} -- {inp['source']} -- Session: {inp['session']}..\n\n")
                f.write(f"**Kategorien:** {cats}\n\n")
                f.write(f"```\n{content}\n```\n\n")
                f.write("---\n\n")

            if paste_images:
                f.write("## Visuelle User-Inputs (Paste-PNGs)\n\n")
                f.write("| Zeitstempel | Aufloesung | Groesse | Datei |\n")
                f.write("|-------------|------------|---------|-------|\n")
                for img in paste_images:
                    f.write(f"| {img['date']} | {img['dims']} | {img['size_kb']}KB | `{img['file']}` |\n")
                f.write("\n---\n\n")

            f.write("## Zusammenfassung\n\n")
            f.write(f"1. **USER-INPUTS** (Text) -- Was der User WIRKLICH gesagt hat: {len(unique)}\n")
            f.write(f"2. **ASSISTANT-REASONING** -- Agent-Entscheidungen: {len(assistant_entries)} Snippets\n")
            f.write(f"3. **TOOL-OUTPUTS** -- {sum(tool_data['counter'].values())} Tool-Aufrufe\n")
            f.write(f"4. **VISUAL INPUTS** (PNGs) -- Screenshots: {len(paste_images)}\n")
            f.write(f"5. **AGENT-ERGEBNISSE** (Git-Commits): {len(git_commits)}\n")
            f.write(f"6. Agent-Halluzinationen sind NICHT in diesem Artefakt\n")

        print(f"\nARTIFAKT MD: {output_path} ({len(unique)} User-Inputs, {len(assistant_entries)} Reasoning)")

    # ─── HTML Dashboard ──────────────────────────────────────────────────────
    if html_path:
        result = generate_html_dashboard(unique, git_commits, paste_images,
                                         html_path, project_path,
                                         assistant_entries, tool_data,
                                         memory_stats)
        size_kb = os.path.getsize(result) // 1024
        print(f"ARTIFAKT HTML: {result} ({size_kb} KB)")
        print(f"  -> Oeffne im Browser: file:///{os.path.abspath(result).replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
