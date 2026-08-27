"""
parse_user_inputs.renderers.html_dashboard
==========================================
Generiert ein self-contained HTML-Dashboard via Jinja2.
Das Template, CSS und JS liegen in parse_user_inputs/templates/.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import html as html_mod

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    # Fallback: Jinja2 nicht installiert — alles in der Hand
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _prepare_paste_data(paste_images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bereitet Paste-PNGs als Base64 data-URIs vor."""
    paste_data = []
    for img in paste_images:
        try:
            with open(img["fpath"], "rb") as f:
                raw = f.read()
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
    return paste_data


def _build_template_context(
    *,
    unique_inputs: list[dict[str, Any]],
    git_commits: list[dict[str, Any]],
    paste_images: list[dict[str, Any]],
    assistant_entries: list[dict[str, Any]],
    tool_data: dict[str, Any],
    memory_stats: dict[str, Any],
    project_path: str,
    platform_info: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Baut den Jinja2-Template-Kontext auf."""

    # Kategorien zählen
    cat_counts: dict[str, int] = {}
    for inp in unique_inputs:
        for c in inp["categories"]:
            cat_counts[c] = cat_counts.get(c, 0) + 1

    # Timeline
    by_date: dict[str, list] = {}
    for c in git_commits:
        by_date.setdefault(c["date"], []).append(c)

    ms = memory_stats or {"total_bytes": 0, "by_role": {}, "by_session": {}}
    mem_mb = ms["total_bytes"] / 1024 / 1024
    user_mb = ms["by_role"].get("user", 0) / 1024 / 1024
    asst_mb = ms["by_role"].get("assistant", 0) / 1024 / 1024
    tool_mb = ms["by_role"].get("tool", 0) / 1024 / 1024
    coverage_pct = (len(unique_inputs) * 221 / ms["total_bytes"] * 100) if ms["total_bytes"] > 0 else 0

    # Platform-Stats
    pi = platform_info or {}
    platform_json = json.dumps(pi, ensure_ascii=False)
    platform_counts = {pid: info.get("count", 0) for pid, info in pi.items()}

    # Inputs nach Plattform gruppieren
    inputs_by_platform: dict[str, int] = {}
    for inp in unique_inputs:
        p = inp.get("platform", inp.get("source", "unknown"))
        inputs_by_platform[p] = inputs_by_platform.get(p, 0) + 1

    return {
        # Data (als JSON-Strings für <script>-Blöcke)
        "user_inputs_json": json.dumps([{
            "idx": i + 1,
            "date": html_mod.escape(inp["date"]),
            "content": html_mod.escape(inp["content"][:2000]),
            "categories": inp["categories"],
            "source": inp["source"],
            "session": html_mod.escape(inp["session"]),
        } for i, inp in enumerate(unique_inputs)], ensure_ascii=False),

        "cat_counts_json": json.dumps(cat_counts, ensure_ascii=False),

        "timeline_json": json.dumps([{
            "date": d,
            "count": len(cs),
            "subjects": [c["subject"][:80] for c in cs],
        } for d, cs in sorted(by_date.items())], ensure_ascii=False),

        "paste_json": json.dumps(_prepare_paste_data(paste_images), ensure_ascii=False),

        "memory_stats_json": json.dumps(ms, ensure_ascii=False),

        "reasoning_json": json.dumps([{
            "date": html_mod.escape(e["date"]),
            "reasoning": html_mod.escape(e["reasoning"][:600]),
            "content_len": e["content_len"],
            "session": html_mod.escape(e["session"]),
            "model": html_mod.escape(e["model"]),
        } for e in assistant_entries[:80]], ensure_ascii=False),

        "tool_data_json": json.dumps(tool_data, ensure_ascii=False),

        # Template-Variablen
        "platform_json": platform_json,
        "has_platforms": bool(pi),
        "platform_counts_json": json.dumps(platform_counts, ensure_ascii=False),
        "project_path": html_mod.escape(project_path),
        "today": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "num_inputs": len(unique_inputs),
        "num_reasoning": len(assistant_entries),
        "num_commits": len(git_commits),
        "num_paste": len(paste_images),
        "mem_mb": f"{mem_mb:.1f}",
        "user_mb": f"{user_mb:.1f}",
        "asst_mb": f"{asst_mb:.1f}",
        "tool_mb": f"{tool_mb:.1f}",
    }


def render_html_dashboard(
    *,
    output_path: str,
    project_path: str,
    unique_inputs: list[dict[str, Any]],
    git_commits: list[dict[str, Any]],
    paste_images: list[dict[str, Any]],
    assistant_entries: list[dict[str, Any]],
    tool_data: dict[str, Any],
    memory_stats: dict[str, Any],
    platform_info: dict[str, dict[str, Any]] | None = None,
) -> str:
    """
    Rendert das HTML-Dashboard über Jinja2 Templates.
    Falls Jinja2 nicht verfügbar ist, wird ein Fallback-Inline generiert.
    """

    ctx = _build_template_context(
        unique_inputs=unique_inputs,
        git_commits=git_commits,
        paste_images=paste_images,
        assistant_entries=assistant_entries,
        tool_data=tool_data,
        memory_stats=memory_stats,
        project_path=project_path,
        platform_info=platform_info,
    )

    if Environment is not None and TEMPLATES_DIR.exists():
        # Jinja2-Rendering
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,  # Wir escapen schon selbst
        )
        template = env.get_template("dashboard.html")
        html = template.render(**ctx)
    else:
        # Fallback: Inline-Rendering (kein Jinja2 verfügbar)
        html = _render_fallback(ctx)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _render_fallback(ctx: dict[str, Any]) -> str:
    """
    Minimaler Fallback falls Jinja2 nicht installiert ist.
    Liest CSS und JS separat wenn vorhanden, sonst leer.
    """
    css = ""
    js = ""
    css_path = TEMPLATES_DIR / "dashboard.css"
    js_path = TEMPLATES_DIR / "dashboard.js"

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
    if js_path.exists():
        js = js_path.read_text(encoding="utf-8")

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>User-Inputs Dashboard — {ctx['project_path']}</title>
<style>{css}</style>
</head>
<body>
<div class="header">
  <h1>&#9876; User-Inputs Dashboard V4</h1>
  <div class="meta">Projekt: {ctx['project_path']} &middot; Erstellt: {ctx['today']}</div>
</div>
<div class="container">
  <div class="stats-grid" id="stats"></div>
  <div class="section">
    <div class="section-title"><span class="icon">&#128202;</span> User-Intentionen nach Kategorie</div>
    <canvas id="catChart" height="300"></canvas>
  </div>
  <div class="section">
    <div class="section-title"><span class="icon">&#128172;</span> Alle echten User-Inputs</div>
    <input class="inputs-search" id="searchInput" placeholder="Suche..." autocomplete="off">
    <div class="filter-chips" id="filterChips"></div>
    <div class="inputs-list" id="inputsList"></div>
  </div>
</div>
<script>
const USER_INPUTS = {ctx['user_inputs_json']};
const CAT_COUNTS = {ctx['cat_counts_json']};
const TIMELINE = {ctx['timeline_json']};
const PASTE_IMAGES = {ctx['paste_json']};
const MEM_STATS = {ctx['memory_stats_json']};
const REASONING = {ctx['reasoning_json']};
const TOOL_DATA = {ctx['tool_data_json']};
</script>
<script>{js}</script>
</body>
</html>"""
