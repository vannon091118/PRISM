"""
parse_user_inputs.modes.scan_mode
===================================
Scannt alle Plattformen und generiert Input-Dashboard.
"""

from __future__ import annotations

from pathlib import Path

from parse_user_inputs.config import Config


from parse_user_inputs.sorting import merge_and_dedup


def run_scan_mode(
    cfg: Config,
    raw_args: dict[str, str],
    scan_all: bool,
    platform_filter: list[str] | None,
) -> dict:
    """Scannt alle Plattformen und generiert Dashboard."""
    from parse_user_inputs.sources import scan_all_inputs, discover_installed
    from parse_user_inputs.renderers import render_html_dashboard, render_json, render_markdown

    print(f"\n{'='*60}")
    print(f"  MULTI-PLATTFORM SCAN MODUS")
    print(f"{'='*60}")

    if scan_all:
        print("  Modus: Alle Plattformen scannen")
    if platform_filter:
        print(f"  Filter: {', '.join(platform_filter)}")

    # Plattformen scannen
    platform_results = scan_all_inputs(platform_filter)

    all_inputs: list[dict] = []
    for pid, inputs in platform_results.items():
        print(f"  {pid}: {len(inputs)} User-Inputs gefunden")
        all_inputs.extend(inputs)

    # Deduplizieren
    unique = merge_and_dedup(all_inputs)
    total = sum(len(v) for v in platform_results.values())
    print(f"\n  Gesamt: {total} Inputs -> {len(unique)} einzigartig")

    # Discover info
    discovered = discover_installed()
    print(f"  Installierte Plattformen: {len(discovered)}")

    # Output-Pfade
    output_dir = Path(raw_args.get("output", "."))
    if output_dir.is_dir():
        outputs = {
            "md": str(output_dir / cfg.default_output_filename),
            "html": str(output_dir / cfg.default_html_filename),
            "json": str(output_dir / cfg.default_json_filename),
        }
    else:
        outputs = {
            "md": raw_args.get("output", ""),
            "html": raw_args.get("html", ""),
            "json": raw_args.get("json", ""),
        }

    if "html" in raw_args:
        outputs["html"] = raw_args["html"]
    if "json" in raw_args:
        outputs["json"] = raw_args["json"]

    # Plattform-Info fuer Dashboard
    platform_info = {
        pid: {"name": pid, "count": len(inputs)}
        for pid, inputs in platform_results.items()
    }

    # Render HTML
    if outputs["html"]:
        result = render_html_dashboard(
            output_path=outputs["html"],
            project_path=f"Multi-Plattform Scan ({len(platform_results)} Plattformen)",
            unique_inputs=unique,
            git_commits=[],
            paste_images=[],
            assistant_entries=[],
            tool_data={"counter": {}, "sizes": {}, "sessions": {}},
            memory_stats={"total_bytes": 0, "by_role": {}, "by_session": {}},
            platform_info=platform_info,
        )
        size_kb = Path(result).stat().st_size // 1024
        print(f"\nARTIFAKT HTML: {result} ({size_kb} KB)")
        print(f"  -> Oeffne im Browser: file:///{Path(result).resolve().as_posix()}")

    # Render JSON
    if outputs["json"]:
        result = render_json(
            output_path=outputs["json"],
            project_path="multi-platform",
            unique_inputs=unique,
            git_commits=[],
            paste_images=[],
            assistant_entries=[],
            tool_data={"counter": {}, "sizes": {}, "sessions": {}},
            memory_stats={"total_bytes": 0, "by_role": {}, "by_session": {}},
        )
        size_kb = Path(result).stat().st_size // 1024
        print(f"ARTIFAKT JSON: {result} ({size_kb} KB)")

    # Render Markdown
    if outputs["md"] and outputs["md"] != "/dev/null":
        render_markdown(
            output_path=outputs["md"],
            project_path="multi-platform",
            unique_inputs=unique,
            git_commits=[],
            paste_images=[],
            assistant_entries=[],
            tool_data={"counter": {}, "sizes": {}, "sessions": {}},
            memory_stats={"total_bytes": 0, "by_role": {}, "by_session": {}},
        )
        print(f"ARTIFAKT MD: {outputs['md']} ({len(unique)} User-Inputs)")

    return {"unique_inputs": unique, "platform_results": platform_results}
