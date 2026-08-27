"""
parse_user_inputs.renderers.json_output
========================================
Generiert strukturierten JSON-Output für Agent-Integration.
"""

from __future__ import annotations

import json
from typing import Any


def render_json(
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
    """
    Schreibt strukturiertes JSON mit allen geparsten Daten.
    Ideal für Agent-Integration — kein Parsing von Markdown nötig.
    """

    # paste_images: fpath entfernen (nicht serialisierbar in portable JSON)
    paste_clean = [
        {k: v for k, v in img.items() if k != "fpath"}
        for img in paste_images
    ]

    output = {
        "meta": {
            "project_path": project_path,
            "total_inputs": len(unique_inputs),
            "total_commits": len(git_commits),
            "total_paste_images": len(paste_images),
            "total_assistant_snippets": len(assistant_entries),
            "total_tool_calls": sum(tool_data.get("counter", {}).values()),
            "memory_total_bytes": memory_stats.get("total_bytes", 0),
        },
        "user_inputs": unique_inputs,
        "git_commits": git_commits,
        "paste_images": paste_clean,
        "assistant_reasoning": assistant_entries,
        "tool_stats": tool_data,
        "memory_stats": memory_stats,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output_path
