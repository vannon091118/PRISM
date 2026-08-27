"""
parse_user_inputs.renderers.generate_dashboard
===============================================
Generates the interactive dashboard HTML by combining:
1. The HTML template (interactive_dashboard.html) 
2. Real data from dashboard_data.json

Usage:
    python -m parse_user_inputs.renderers.generate_dashboard
    or
    python parse_user_inputs/renderers/generate_dashboard.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def generate(
    data_path: str = "docs/screenshots/dashboard_data.json",
    template_path: str = "parse_user_inputs/templates/interactive_dashboard.html",
    output_path: str = "DASHBOARD.html",
) -> str:
    """Generates dashboard HTML with real data embedded."""
    
    # Load real data
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # Load template
    with open(template_path, encoding="utf-8") as f:
        html = f.read()
    
    # Replace the hardcoded DATA block
    # Find: const DATA = { ... };
    # Replace with: const DATA = <real data>;
    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    
    # Find the start and end of the DATA block
    import re
    # Match "const DATA = {" ... "};\n" 
    pattern = r"const DATA = \{.*?\};"
    match = re.search(pattern, html, re.DOTALL)
    
    if match:
        new_block = f"const DATA = {data_json};"
        html = html[:match.start()] + new_block + html[match.end():]
    else:
        # Fallback: find the line and replace everything until "// RENDER" or "// INIT"
        print("WARNING: Could not find DATA block pattern, inserting after marker")
        marker = "// DATA\n// "
        idx = html.find(marker)
        if idx >= 0:
            # Find the next section marker
            end_marker = "//\n// "
            end_idx = html.find(end_marker, idx + len(marker))
            if end_idx < 0:
                end_idx = html.find("\nfunction ", idx)
            if end_idx > 0:
                block = f"const DATA = {data_json};\n"
                html = html[:idx] + "// DATA\n// " + "="*70 + "\n" + block + html[end_idx:]
    
    # Save output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Dashboard generated: {output_path}")
    print(f"  Data: {data['stats']['threads']} threads, {data['stats']['answered']} answered, {data['stats']['rate']}% rate")
    print(f"  Platforms: {len(data['platforms'])}")
    for p in data["platforms"]:
        print(f"    {p['name']}: {p.get('threadCount', p.get('count', 0))} threads")
    print(f"  Projects: {len(data['projects'])}")
    
    return output_path


if __name__ == "__main__":
    # Resolve paths relative to project root
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(root)
    
    data_file = sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/dashboard_data.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "DASHBOARD.html"
    
    generate(data_file, output_path=output_file)
