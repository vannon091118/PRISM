"""
parse_user_inputs.renderers.markdown
=====================================
Generiert das USER_INPUTS_ARTIFACT.md als strukturiertes Markdown.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def render_markdown(
    *,
    output_path: str,
    project_path: str,
    unique_inputs: list[dict[str, Any]],
    git_commits: list[dict[str, Any]],
    paste_images: list[dict[str, Any]],
    assistant_entries: list[dict[str, Any]],
    tool_data: dict[str, Any],
    memory_stats: dict[str, Any],
) -> str:
    """Schreibt das Markdown-Artefakt und gibt den Pfad zurück."""

    mem_mb = memory_stats["total_bytes"] / 1024 / 1024

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# User-Inputs Artifact V4\n\n")
        f.write(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Projekt:** `{project_path}`\n")
        f.write(f"**Memory Gesamt:** {mem_mb:.1f} MB\n")
        f.write(
            f"**Quellen:** state.db ({len(unique_inputs)} user + "
            f"{len(assistant_entries)} assistant + "
            f"{sum(tool_data['counter'].values())} tool) + "
            f"Git ({len(git_commits)}) + Paste-PNGs ({len(paste_images)})\n"
        )
        f.write(f"**User-Inputs gesamt:** {len(unique_inputs)} (dedupliziert)\n\n")
        f.write("---\n\n")

        # Kategorien
        cat_counts: dict[str, int] = {}
        for inp in unique_inputs:
            for c in inp["categories"]:
                cat_counts[c] = cat_counts.get(c, 0) + 1
        if cat_counts:
            f.write("## User-Intentionen nach Kategorie\n\n")
            f.write("| Kategorie | Anzahl |\n|-----------|--------|\n")
            for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
                f.write(f"| {cat} | {count} |\n")
            f.write("\n---\n\n")

        # Tool-Stats
        if tool_data["counter"]:
            f.write("## Tool-Nutzung\n\n")
            f.write("| Tool | Aufrufe | Daten |\n|------|---------|-------|\n")
            for name, count in sorted(tool_data["counter"].items(), key=lambda x: -x[1]):
                kb = tool_data["sizes"].get(name, 0) / 1024
                f.write(f"| {name} | {count} | {kb:.0f} KB |\n")
            f.write("\n---\n\n")

        # Top Reasoning
        if assistant_entries:
            f.write("## Top Assistant-Reasoning-Snippets\n\n")
            for e in assistant_entries[:30]:
                f.write(f"### {e['date']} ({e['model']}) — {e['content_len'] // 1024} KB\n\n")
                f.write(f"```\n{e['reasoning']}\n```\n\n")
            f.write("---\n\n")

        # Timeline
        if git_commits:
            f.write("## Rekonstruierte Timeline (Git-Commits)\n\n")
            by_date: dict[str, list] = {}
            for c in git_commits:
                by_date.setdefault(c["date"], []).append(c)
            for date in sorted(by_date.keys()):
                commits = by_date[date]
                f.write(f"### {date} ({len(commits)} Commits)\n\n")
                for c in commits:
                    f.write(f"- `{c['hash']}` {c['subject']}\n")
                f.write("\n")
            f.write("---\n\n")

        # Alle User-Inputs
        f.write("## Alle echten User-Inputs\n\n")
        f.write("> Nur tatsaechliche User-Nachrichten. Keine System-Messages,\n")
        f.write("> keine Skill-Invocations, keine Agent-Antworten.\n\n")
        for idx, inp in enumerate(unique_inputs, 1):
            cats = ", ".join(inp["categories"])
            content = inp["content"][:2000]
            f.write(f"### [{idx}] {inp['date']} — {inp['source']} — Session: {inp['session']}..\n\n")
            f.write(f"**Kategorien:** {cats}\n\n")
            f.write(f"```\n{content}\n```\n\n")
            f.write("---\n\n")

        # Paste-PNGs
        if paste_images:
            f.write("## Visuelle User-Inputs (Paste-PNGs)\n\n")
            f.write("| Zeitstempel | Aufloesung | Groesse | Datei |\n")
            f.write("|-------------|------------|---------|-------|\n")
            for img in paste_images:
                f.write(f"| {img['date']} | {img['dims']} | {img['size_kb']}KB | `{img['file']}` |\n")
            f.write("\n---\n\n")

        # Zusammenfassung
        f.write("## Zusammenfassung\n\n")
        f.write(f"1. **USER-INPUTS** (Text) — Was der User WIRKLICH gesagt hat: {len(unique_inputs)}\n")
        f.write(f"2. **ASSISTANT-REASONING** — Agent-Entscheidungen: {len(assistant_entries)} Snippets\n")
        f.write(f"3. **TOOL-OUTPUTS** — {sum(tool_data['counter'].values())} Tool-Aufrufe\n")
        f.write(f"4. **VISUAL INPUTS** (PNGs) — Screenshots: {len(paste_images)}\n")
        f.write(f"5. **AGENT-ERGEBNISSE** (Git-Commits): {len(git_commits)}\n")
        f.write(f"6. Agent-Halluzinationen sind NICHT in diesem Artefakt\n")

    return output_path
