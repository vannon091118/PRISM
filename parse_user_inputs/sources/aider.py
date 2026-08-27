"""
parse_user_inputs.sources.aider
================================
Aider CLI Reader — Chat History (Markdown).
"""

from __future__ import annotations

import glob
import os
from typing import Any

from parse_user_inputs.categorizer import categorize, is_real_user_input
from parse_user_inputs.models import Thread, Message

PLATFORM_ID = "aider"


def scan_inputs() -> list[dict[str, Any]]:
    """Liest Aider Chat History aus .aider.chat.history.md Dateien."""
    inputs: list[dict[str, Any]] = []
    home = str(os.path.expanduser("~"))

    # Aider schreibt .aider.chat.history.md in JEDES Repo
    # Plus globale History in ~/.aider/
    search_paths = []
    
    # Globale History
    aider_dir = os.path.join(home, ".aider")
    if os.path.exists(aider_dir):
        search_paths.append(aider_dir)
    
    # Globale chat.history.md
    global_history = os.path.join(home, ".aider.chat.history.md")
    if os.path.exists(global_history):
        search_paths.append(global_history)
    
    # Alle .aider.chat.history.md im Home-Verzeichnis ( rekursiv, begrenzt )
    for pattern in [
        os.path.join(home, "*", ".aider.chat.history.md"),
        os.path.join(home, "*", "*", ".aider.chat.history.md"),
        os.path.join(home, "*", "*", "*", ".aider.chat.history.md"),
    ]:
        search_paths.extend(glob.glob(pattern))

    for path in search_paths:
        if os.path.isfile(path) and path.endswith(".md"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("## ") and len(line) > 10:
                        text = line[3:].strip()
                        if is_real_user_input(text):
                            inputs.append({
                                "date": "?",
                                "content": text[:2000],
                                "categories": categorize(text),
                                "source": PLATFORM_ID,
                                "session": os.path.basename(path)[:12],
                                "platform": PLATFORM_ID,
                            })
            except Exception:
                pass
        elif os.path.isdir(path):
            for md_file in glob.glob(os.path.join(path, "**", "*.md"), recursive=True):
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    for line in content.split("\n"):
                        line = line.strip()
                        if line.startswith("## ") and len(line) > 10:
                            text = line[3:].strip()
                            if is_real_user_input(text):
                                inputs.append({
                                    "date": "?",
                                    "content": text[:2000],
                                    "categories": categorize(text),
                                    "source": PLATFORM_ID,
                                    "session": os.path.basename(md_file)[:12],
                                    "platform": PLATFORM_ID,
                                })
                except Exception:
                    pass

    return inputs


def reconstruct_threads() -> list[Thread]:
    """Rekonstruiert Threads aus Aider Chat History."""
    threads: list[Thread] = []
    inputs = scan_inputs()

    for inp in inputs:
        threads.append(Thread(
            id="aider",
            platform=PLATFORM_ID,
            project="aider",
            title=inp["content"][:60],
            date=inp["date"],
            messages=[Message(role="user", content=inp["content"])],
            categories=inp["categories"],
        ))

    return threads
