"""
parse_user_inputs.renderers.canvas_dashboard
=============================================
Visuelles Dashboard mit Canvas-Animationen, Side-Panel und Integritaets-Analyse.
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


def render_canvas_dashboard(
    *,
    output_path: str,
    project_path: str,
    threads: list[Thread],
) -> str:
    """Rendert das visuelle Canvas-Dashboard."""

    # Plattformen die nur User-Inputs speichern (keine Agent-Antworten)
    USER_ONLY_PLATFORMS = {"claude_code", "codex", "gemini_cli", "aider"}

    def _is_user_only_platform(platform: str) -> bool:
        return platform in USER_ONLY_PLATFORMS

    # === Daten vorbereiten ===
    projects: dict[str, dict] = {}
    categories: dict[str, int] = {}
    platform_counts: dict[str, int] = {}
    timeline_data: list[dict] = []
    integrity_issues: list[dict] = []

    for t in threads:
        proj = t.project or "unknown"
        if proj not in projects:
            projects[proj] = {
                "name": proj,
                "threads": [],
                "platforms": set(),
                "categories": set(),
                "complete": 0,
                "incomplete": 0,
                "interrupts": 0,
                "total_user_msgs": 0,
                "total_agent_msgs": 0,
            }
        p = projects[proj]
        p["threads"].append(t)
        p["platforms"].add(t.platform)
        for c in t.categories:
            p["categories"].add(c)
            categories[c] = categories.get(c, 0) + 1
        platform_counts[t.platform] = platform_counts.get(t.platform, 0) + 1

        # Integritaet
        has_agent = t.has_agent_response
        has_interrupt = t.has_interrupts
        user_msgs = t.user_message_count

        if has_agent and not has_interrupt and user_msgs <= 3:
            p["complete"] += 1
        else:
            p["incomplete"] += 1
        if has_interrupt:
            p["interrupts"] += 1
        p["total_user_msgs"] += user_msgs
        p["total_agent_msgs"] += sum(1 for m in t.messages if m.is_agent)

        # Timeline
        if t.date and t.date != "?":
            timeline_data.append({
                "date": t.date,
                "platform": t.platform,
                "project": proj,
                "title": t.title[:60],
                "has_agent": has_agent,
                "has_interrupt": has_interrupt,
                "categories": t.categories[:3],
            })

        # Integritaets-Probleme (nur fuer Plattformen mit Agent-Antworten)
        if not has_agent and user_msgs > 0 and not _is_user_only_platform(t.platform):
            integrity_issues.append({
                "type": "no_response",
                "project": proj,
                "title": t.title[:80],
                "platform": t.platform,
                "date": t.date,
                "user_input": t.user_input[:200],
                "thread_id": t.id,
            })
        elif has_interrupt:
            integrity_issues.append({
                "type": "interrupt",
                "project": proj,
                "title": t.title[:80],
                "platform": t.platform,
                "date": t.date,
                "thread_id": t.id,
            })

    # Projects als sortierte Liste
    project_list = []
    for proj_name, data in sorted(projects.items(), key=lambda x: len(x[1]["threads"]), reverse=True):
        total = len(data["threads"])
        comp = data["complete"]
        incomp = data["incomplete"]
        pct = comp / total * 100 if total > 0 else 0
        project_list.append({
            "name": proj_name,
            "total": total,
            "complete": comp,
            "incomplete": incomp,
            "interrupts": data["interrupts"],
            "percent": round(pct, 1),
            "platforms": sorted(data["platforms"]),
            "categories": sorted(data["categories"]),
            "user_msgs": data["total_user_msgs"],
            "agent_msgs": data["total_agent_msgs"],
            "status": "complete" if pct > 80 else "partial" if pct > 50 else "incomplete",
        })

    # Stats
    total_threads = len(threads)
    total_with_agent = sum(1 for t in threads if t.has_agent_response)
    total_interrupts = sum(1 for t in threads if t.has_interrupts)
    total_no_response = sum(1 for t in threads if t.user_message_count > 0 and not t.has_agent_response and not _is_user_only_platform(t.platform))
    completion_pct = round(total_with_agent / total_threads * 100, 1) if total_threads > 0 else 0

    # Canvas-Nodes fuer Partikel-System (zeitbasierte Platzierung)
    canvas_nodes = []
    import math
    from parse_user_inputs.sorting import parse_date

    for i, proj in enumerate(project_list[:20]):
        # Zeitbasierte Platzierung:sortiere nach fruestem Thread-Datum
        proj_threads = projects[proj["name"]]["threads"]
        dates = [parse_date(t.date) for t in proj_threads if t.date and t.date != "?"]
        earliest = min(dates) if dates else datetime.min
        latest = max(dates) if dates else datetime.min
        proj["earliest_date"] = earliest.strftime("%Y-%m-%d %H:%M") if earliest != datetime.min else "?"
        proj["latest_date"] = latest.strftime("%Y-%m-%d %H:%M") if latest != datetime.min else "?"

        # X-Achse = Zeit (links = aeltester, rechts = neuester)
        all_earliest = [min([parse_date(t.date) for t in projects[pn]["threads"] if t.date and t.date != "?"] or [datetime.min]) for pn in projects]
        all_latest = [max([parse_date(t.date) for t in projects[pn]["threads"] if t.date and t.date != "?"] or [datetime.min]) for pn in projects]
        time_min = min(d for d in all_earliest if d != datetime.min) if any(d != datetime.min for d in all_earliest) else datetime.min
        time_max = max(d for d in all_latest if d != datetime.min) if any(d != datetime.min for d in all_latest) else datetime.now()
        time_range = (time_max - time_min).total_seconds() or 1
        x_time = (earliest - time_min).total_seconds() / time_range if earliest != datetime.min else 0.5

        # Y-Achse = Aehnlichkeit (gleiche Plattform/Kategorie nahe beieinander)
        platform_hash = hash(tuple(sorted(proj["platforms"]))) % 100 / 100
        cat_hash = hash(tuple(sorted(proj["categories"][:3]))) % 100 / 100
        y_pos = 0.3 + platform_hash * 0.4

        # Groesse = Thread-Anzahl (skaliert)
        max_total = max((p["total"] for p in project_list), default=1)
        size = 8 + (proj["total"] / max_total) * 30

        # Kategorie-Verteilung pro Projekt als Pie-Segmente
        cat_dist = {}
        for t in proj_threads:
            for c in t.categories:
                cat_dist[c] = cat_dist.get(c, 0) + 1
        total_cat = sum(cat_dist.values()) or 1
        pie_segments = []
        start_angle = 0
        for cat_name, cat_count in sorted(cat_dist.items(), key=lambda x: -x[1]):
            sweep = (cat_count / total_cat) * math.pi * 2
            pie_segments.append({
                "category": cat_name,
                "count": cat_count,
                "percent": round(cat_count / total_cat * 100, 1),
                "start": round(start_angle, 4),
                "end": round(start_angle + sweep, 4),
            })
            start_angle += sweep

        # Abhaengigkeiten: Plattform-Verknüpfungen zu anderen Projekten
        depends_on = []
        for other_proj in project_list:
            if other_proj["name"] == proj["name"]:
                continue
            shared_platforms = set(proj["platforms"]) & set(other_proj["platforms"])
            shared_cats = set(proj["categories"][:5]) & set(other_proj["categories"][:5])
            if shared_platforms or len(shared_cats) >= 2:
                depends_on.append({
                    "project": other_proj["name"],
                    "shared_platforms": sorted(shared_platforms),
                    "shared_categories": sorted(shared_cats),
                    "strength": len(shared_platforms) + len(shared_cats),
                })
        depends_on.sort(key=lambda x: -x["strength"])

        canvas_nodes.append({
            "id": proj["name"],
            "x": 0.08 + x_time * 0.84,
            "y": y_pos,
            "size": size,
            "completeness": proj["percent"],
            "total": proj["total"],
            "status": proj["status"],
            "pie": pie_segments,
            "user_msgs": proj["user_msgs"],
            "agent_msgs": proj["agent_msgs"],
            "platforms": proj["platforms"],
            "depends_on": depends_on[:3],
            "earliest_date": proj["earliest_date"],
            "latest_date": proj["latest_date"],
        })

    # Context
    ctx = {
        "threads_json": json.dumps([t.to_dict() for t in threads], ensure_ascii=False),
        "projects_json": json.dumps(project_list, ensure_ascii=False),
        "categories_json": json.dumps(categories, ensure_ascii=False),
        "platform_counts_json": json.dumps(platform_counts, ensure_ascii=False),
        "timeline_json": json.dumps(sorted(timeline_data, key=lambda x: x["date"]), ensure_ascii=False),
        "integrity_json": json.dumps(integrity_issues, ensure_ascii=False),
        "canvas_nodes_json": json.dumps(canvas_nodes, ensure_ascii=False),
        "project_path": html_mod.escape(project_path),
        "today": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "num_threads": total_threads,
        "num_with_agent": total_with_agent,
        "num_interrupts": total_interrupts,
        "num_no_response": total_no_response,
        "completion_pct": completion_pct,
        "num_platforms": len(platform_counts),
        "num_categories": len(categories),
        "num_projects": len(project_list),
    }

    if Environment is not None and TEMPLATES_DIR.exists():
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )
        template = env.get_template("canvas_visual.html")
        html = template.render(**ctx)
    else:
        html = _render_fallback(ctx)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _render_fallback(ctx: dict[str, Any]) -> str:
    """Minimaler Fallback ohne Jinja2."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Canvas Dashboard</title></head>
<body style="background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:40px">
<h1>Agent Canvas Dashboard</h1>
<p>{ctx['num_threads']} Threads, {ctx['num_with_agent']} mit Agent, {ctx['num_no_response']} ohne Antwort</p>
<p>{ctx['completion_pct']}% Vollstaendigkeit</p>
<p>Jinja2 nicht installiert - fuer volle Visualisierung: pip install jinja2</p>
</body></html>"""
