"""
parse_user_inputs.modes.thread_mode
=====================================
Scannt alle Plattformen und generiert Thread-basiertes Dashboard.
"""

from __future__ import annotations

from pathlib import Path

from parse_user_inputs.config import Config
from parse_user_inputs.renderers.threads_dashboard import render_threads_dashboard


def run_threads_mode(cfg: Config, raw_args: dict[str, str], canvas: bool = False) -> dict:
    """Scannt alle Plattformen und generiert Thread-basiertes Dashboard."""
    from parse_user_inputs.sources import scan_all_threads

    sep = "=" * 60
    print()
    print(sep)
    print("  THREAD SCAN MODUS")
    print(sep)

    results = scan_all_threads()

    all_threads = []
    for platform, threads in results.items():
        print(f"  {platform}: {len(threads)} Threads")
        all_threads.extend(threads)

    total_msgs = sum(t.message_count for t in all_threads)
    print()
    print(f"  Gesamt: {len(all_threads)} Threads, {total_msgs} Messages")

    output_path = raw_args.get("html", "THREADS_DASHBOARD.html")

    if canvas:
        from parse_user_inputs.renderers.canvas_dashboard import render_canvas_dashboard
        result = render_canvas_dashboard(
            output_path=output_path,
            project_path="Multi-Plattform Scan",
            threads=all_threads,
        )
    else:
        result = render_threads_dashboard(
            output_path=output_path,
            project_path="Multi-Plattform Scan",
            threads=all_threads,
        )
    size_kb = Path(result).stat().st_size // 1024
    print()
    print(f"ARTIFAKT HTML: {result} ({size_kb} KB)")
    abs_path = Path(result).resolve().as_posix()
    print(f"  -> Oeffne im Browser: file:///{abs_path}")

    if "json" in raw_args:
        from parse_user_inputs.renderers import render_json
        unique_inputs = []
        for t in all_threads:
            if t.user_input:
                unique_inputs.append({
                    "date": t.date,
                    "content": t.user_input,
                    "categories": t.categories,
                    "source": t.platform,
                    "session": t.id,
                    "platform": t.platform,
                })
        render_json(
            output_path=raw_args["json"],
            project_path="multi-platform",
            unique_inputs=unique_inputs,
            git_commits=[], paste_images=[], assistant_entries=[],
            tool_data={"counter": {}, "sizes": {}, "sessions": {}},
            memory_stats={"total_bytes": 0, "by_role": {}, "by_session": {}},
        )
        print(f"ARTIFAKT JSON: {raw_args['json']}")

    return {"threads": all_threads, "platform_results": results}
