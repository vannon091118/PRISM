"""
parse_user_inputs.renderers.threads_dashboard
=============================================
Generiert das Thread-basierte Dashboard mit User -> Agent -> Ergebnis.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import html as html_mod

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    Environment = None
    FileSystemLoader = None

from parse_user_inputs.models import Thread

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def render_threads_dashboard(
    *,
    output_path: str,
    project_path: str,
    threads: list[Thread],
) -> str:
    """Rendert das Thread-basierte Dashboard."""

    # Stats berechnen
    cat_counts: dict[str, int] = {}
    project_counts: dict[str, int] = {}
    platform_counts: dict[str, int] = {}

    for t in threads:
        for c in t.categories:
            cat_counts[c] = cat_counts.get(c, 0) + 1
        project_counts[t.project] = project_counts.get(t.project, 0) + 1
        platform_counts[t.platform] = platform_counts.get(t.platform, 0) + 1

    # Threads als JSON
    threads_json = json.dumps([t.to_dict() for t in threads], ensure_ascii=False)

    # Context
    ctx = {
        "threads_json": threads_json,
        "cat_counts_json": json.dumps(cat_counts, ensure_ascii=False),
        "project_counts_json": json.dumps(project_counts, ensure_ascii=False),
        "platform_counts_json": json.dumps(platform_counts, ensure_ascii=False),
        "project_path": html_mod.escape(project_path),
        "today": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "num_threads": len(threads),
        "num_messages": sum(t.message_count for t in threads),
        "num_platforms": len(platform_counts),
        "has_platforms": len(platform_counts) > 1,
    }

    if Environment is not None and TEMPLATES_DIR.exists():
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )
        template = env.get_template("threads.html")
        html = template.render(**ctx)
    else:
        html = _render_fallback_threads(ctx)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _render_fallback_threads(ctx: dict[str, Any]) -> str:
    """Minimaler Fallback ohne Jinja2."""
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
<title>Agent Threads — {ctx['project_path']}</title>
<style>{css}</style>
</head>
<body>
<h1>Agent Threads Dashboard</h1>
<p>{ctx['num_threads']} Threads, {ctx['num_messages']} Messages</p>
<script>
const THREADS = {ctx['threads_json']};
const CAT_COUNTS = {ctx['cat_counts_json']};
const PROJECT_COUNTS = {ctx['project_counts_json']};
const PLATFORM_COUNTS = {ctx['platform_counts_json']};
</script>
</body>
</html>"""
