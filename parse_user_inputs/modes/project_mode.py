"""
parse_user_inputs.modes.project_mode
======================================
Klassischer Projekt-Modus: Einzelnes Projekt scannen.
"""

from __future__ import annotations

from pathlib import Path

from parse_user_inputs.config import Config
from parse_user_inputs.sources import (
    read_state_db,
    read_state_db_assistant,
    read_state_db_tools,
    read_state_db_memory_stats,
    read_request_dumps,
    read_freebuff_threads,
    read_paste_images,
    read_git_commits,
)
from parse_user_inputs.renderers import render_markdown, render_html_dashboard, render_json


from parse_user_inputs.sorting import merge_and_dedup


def run_project_mode(cfg: Config, raw_args: dict[str, str]) -> dict:
    """Klassischer Projekt-Modus (einzelnes Projekt scannen)."""
    # CLI-Overrides
    if "project_path" in raw_args:
        cfg.project_path = raw_args["project_path"]
    if "db_path" in raw_args:
        cfg.db_path = raw_args["db_path"]
    if "sessions_dir" in raw_args:
        cfg.sessions_dir = raw_args["sessions_dir"]

    project_path = cfg.resolve_project_path()
    outputs = cfg.resolve_output_paths(project_path)

    # CLI-Overrides fuer Outputs
    if "output" in raw_args:
        outputs["md"] = raw_args["output"]
    if "html" in raw_args:
        outputs["html"] = raw_args["html"]
    if "json" in raw_args:
        outputs["json"] = raw_args["json"]

    print(f"Projekt: {project_path}")
    print(f"Hermes DB: {cfg.db_path}")
    print(f"Sessions Dir: {cfg.sessions_dir}")
    print(f"Output MD: {outputs['md']}")
    if outputs["html"]:
        print(f"Output HTML: {outputs['html']}")
    if outputs["json"]:
        print(f"Output JSON: {outputs['json']}")

    # ─── Quellen: User Inputs ────────────────────────────────────────────
    db_inputs = read_state_db(cfg.db_path)
    print(f"  state.db User-Inputs: {len(db_inputs)}")

    dump_inputs = read_request_dumps(cfg.sessions_dir)
    print(f"  request_dump User-Inputs: {len(dump_inputs)}")

    git_commits = read_git_commits(project_path, cfg.since_date)
    print(f"  Git-Commits: {len(git_commits)}")

    paste_images = read_paste_images(cfg.paste_dir)
    print(f"  Paste-PNGs: {len(paste_images)}")

    project_filter = raw_args.get("project_filter", "")
    freebuff_inputs = read_freebuff_threads(
        api_host=cfg.freebuff_api_host,
        api_port=cfg.freebuff_api_port,
        project_filter=project_filter,
    )
    print(f"  Freebuff Desktop Threads: {len(freebuff_inputs)}")

    # ─── Quellen: Assistant + Tool ───────────────────────────────────────
    assistant_entries = read_state_db_assistant(cfg.db_path)
    print(f"  Assistant-Reasoning-Snippets: {len(assistant_entries)}")

    tool_data = read_state_db_tools(cfg.db_path)
    print(f"  Tool-Aufrufe: {sum(tool_data['counter'].values())} ({len(tool_data['counter'])} verschiedene Tools)")

    memory_stats = read_state_db_memory_stats(cfg.db_path)
    mem_mb = memory_stats["total_bytes"] / 1024 / 1024
    print(f"  Memory Gesamt: {mem_mb:.1f} MB")
    for role, b in memory_stats["by_role"].items():
        print(f"    {role}: {b / 1024 / 1024:.1f} MB")

    # ─── Merge + Dedup ───────────────────────────────────────────────────
    unique = merge_and_dedup(db_inputs, dump_inputs, freebuff_inputs)
    print(f"  Einzigartige User-Inputs: {len(unique)}")
    if memory_stats["total_bytes"] > 0:
        coverage = len(unique) * 221 / memory_stats["total_bytes"] * 100
        print(f"  Memory-Coverage: {coverage:.1f}% der Gesamt-Memory")

    # ─── Renderers ───────────────────────────────────────────────────────

    # Markdown
    if outputs["md"] and outputs["md"] != "/dev/null":
        render_markdown(
            output_path=outputs["md"],
            project_path=project_path,
            unique_inputs=unique,
            git_commits=git_commits,
            paste_images=paste_images,
            assistant_entries=assistant_entries,
            tool_data=tool_data,
            memory_stats=memory_stats,
        )
        print(f"\nARTIFAKT MD: {outputs['md']} ({len(unique)} User-Inputs)")

    # HTML Dashboard
    if outputs["html"]:
        result = render_html_dashboard(
            output_path=outputs["html"],
            project_path=project_path,
            unique_inputs=unique,
            git_commits=git_commits,
            paste_images=paste_images,
            assistant_entries=assistant_entries,
            tool_data=tool_data,
            memory_stats=memory_stats,
        )
        size_kb = Path(result).stat().st_size // 1024
        print(f"ARTIFAKT HTML: {result} ({size_kb} KB)")
        print(f"  -> Oeffne im Browser: file:///{Path(result).resolve().as_posix()}")

    # JSON Output (Agent-Modus)
    if outputs["json"]:
        result = render_json(
            output_path=outputs["json"],
            project_path=project_path,
            unique_inputs=unique,
            git_commits=git_commits,
            paste_images=paste_images,
            assistant_entries=assistant_entries,
            tool_data=tool_data,
            memory_stats=memory_stats,
        )
        size_kb = Path(result).stat().st_size // 1024
        print(f"ARTIFAKT JSON: {result} ({size_kb} KB)")

    return {
        "unique_inputs": unique,
        "git_commits": git_commits,
        "paste_images": paste_images,
        "assistant_entries": assistant_entries,
        "tool_data": tool_data,
        "memory_stats": memory_stats,
    }
