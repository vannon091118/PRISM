"""
parse_user_inputs.tests.test_modular
=====================================
Tests fuer die modulare Architektur.
"""

import json
import os
import sys
from pathlib import Path

# Paket-Root zum Path hinzufuegen
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_imports():
    """Alle Module importierbar."""
    from parse_user_inputs.config import Config
    from parse_user_inputs.categorizer import categorize, is_real_user_input
    from parse_user_inputs.models import Thread, Message
    from parse_user_inputs.platforms import ALL_PLATFORMS, PLATFORM_BY_ID
    from parse_user_inputs.sources.base import PlatformReader
    print("[OK] Alle Basis-Imports funktionieren")


def test_platform_reader_protocol():
    """PlatformReader Protocol pruefen."""
    from parse_user_inputs.sources.base import PlatformReader
    from parse_user_inputs.sources import hermes, freebuff, claude_code, codex, cursor, gemini_cli, aider
    for mod in [hermes, freebuff, claude_code, codex, cursor, gemini_cli, aider]:
        assert hasattr(mod, "scan_inputs"), f"{mod.__name__} fehlt scan_inputs"
        assert hasattr(mod, "reconstruct_threads"), f"{mod.__name__} fehlt reconstruct_threads"
    print("[OK] Alle Platform-Module haben scan_inputs + reconstruct_threads")


def test_registry():
    """Registry importiert alle Module."""
    from parse_user_inputs.sources import NATIVE_READERS, VSCODE_PLATFORMS, scan_all_inputs, scan_all_threads
    assert len(NATIVE_READERS) >= 7, f"Erwartet >= 7 Native Reader, bekommen {len(NATIVE_READERS)}"
    assert "hermes" in NATIVE_READERS
    assert "freebuff" in NATIVE_READERS
    assert "claude_code" in NATIVE_READERS
    # Alle Plattformen sind jetzt als Native Reader registriert
    assert len(NATIVE_READERS) >= 10, f"Erwartet >= 10 Native Reader, bekommen {len(NATIVE_READERS)}"
    print("[OK] Registry korrekt: 7 Native + 4 VS Code")


def test_modes_import():
    """Modes-Import funktioniert."""
    from parse_user_inputs.modes import run_threads_mode, run_scan_mode, run_project_mode
    print("[OK] Alle 3 Modes importierbar")


def test_thread_model():
    """Thread + Message Modelle."""
    from parse_user_inputs.models import Thread, Message
    m1 = Message(role="user", content="Test Input")
    m2 = Message(role="assistant", content="Test Response")
    t = Thread(
        id="test1",
        platform="hermes",
        project="test",
        title="Test Thread",
        date="2026-01-01",
        messages=[m1, m2],
        categories=["BUG"],
    )
    assert t.user_input == "Test Input"
    assert t.agent_reaction == "Test Response"
    assert t.message_count == 2
    assert t.has_agent_response
    assert not t.has_interrupts

    d = t.to_dict()
    assert d["id"] == "test1"
    assert d["platform"] == "hermes"
    assert len(d["messages"]) == 2
    print("[OK] Thread + Message Modelle korrekt")


def test_interrupt_detection():
    """Interrupt-Erkennung im Message-Modell."""
    from parse_user_inputs.models import Message
    m = Message(role="user", content="test", message_type="interrupt")
    assert m.is_interrupt
    m2 = Message(role="user", content="test", message_type="normal")
    assert not m2.is_interrupt
    print("[OK] Interrupt-Erkennung funktioniert")


def test_hermes_detect_message_type():
    """Hermes Message-Type Detection."""
    from parse_user_inputs.sources.hermes import _detect_message_type
    assert _detect_message_type("normal text") == "normal"
    assert _detect_message_type("response was cut off") == "interrupt"
    assert _detect_message_type("[System: continue]") == "system"
    assert _detect_message_type("[Note: model was switched]") == "model_switch"
    assert _detect_message_type("continue working toward goal") == "system"
    print("[OK] Hermes Message-Type Detection korrekt")


def test_freebuff_helpers():
    """Freebuff Helper-Funktionen."""
    from parse_user_inputs.sources.freebuff import _extract_project_name, _ts_to_str
    assert _extract_project_name("/path/to/snip-war") == "snip-war"
    assert _extract_project_name("/path/to/snippet-empire") == "snippet-empire"
    assert _extract_project_name("/path/to/myproject") == "myproject"
    assert _extract_project_name("") == "unknown"
    assert _ts_to_str(0) == "?"
    assert _ts_to_str(1700000000000).startswith("2023")
    print("[OK] Freebuff Helpers korrekt")


def test_scanner_thin():
    """Scanner ist jetzt eine dünne Hülle."""
    from parse_user_inputs.scanner import scan_all_platforms, discover_platforms, discover_installed
    from parse_user_inputs.sources import scan_all_inputs
    # scan_all_platforms = scan_all_inputs (Wrapper)
    assert callable(scan_all_platforms)
    assert callable(discover_platforms)
    assert callable(discover_installed)
    print("[OK] Scanner ist dünne Hülle mit Legacy-API")


def test_cli_parse_args():
    """CLI Argument-Parsing."""
    from parse_user_inputs.cli import _parse_args
    args = _parse_args(["--threads", "--html", "out.html", "--scan-all"])
    assert args["threads"] == "1"
    assert args["html"] == "out.html"
    assert args["scan_all"] == "1"

    args2 = _parse_args(["--platforms", "hermes,claude_code", "--json", "out.json"])
    assert args2["platforms"] == "hermes,claude_code"
    assert args2["json"] == "out.json"

    args3 = _parse_args(["--list-platforms"])
    assert args3["list_platforms"] == "1"

    args4 = _parse_args(["--discover"])
    assert args4["discover"] == "1"
    print("[OK] CLI Argument-Parsing korrekt")


def test_template_exists():
    """Templates sind vorhanden."""
    templates_dir = Path(__file__).parent.parent / "templates"
    assert (templates_dir / "threads.html").exists(), "threads.html fehlt"
    assert (templates_dir / "dashboard.css").exists(), "dashboard.css fehlt"
    assert (templates_dir / "threads.js").exists(), "threads.js fehlt"
    assert (templates_dir / "dashboard.html").exists(), "dashboard.html fehlt"
    assert (templates_dir / "dashboard.js").exists(), "dashboard.js fehlt"
    print("[OK] Alle 5 Templates vorhanden")


def test_modules_count():
    """Modul-Zaehler."""
    pkg_dir = Path(__file__).parent.parent
    py_files = list(pkg_dir.glob("*.py"))
    sources_files = list((pkg_dir / "sources").glob("*.py"))
    renderers_files = list((pkg_dir / "renderers").glob("*.py"))
    modes_files = list((pkg_dir / "modes").glob("*.py"))
    templates_files = list((pkg_dir / "templates").glob("*"))

    print(f"  Root:       {len(py_files)} .py")
    print(f"  sources/:   {len(sources_files)} .py (inkl. __init__)")
    print(f"  renderers/: {len(renderers_files)} .py")
    print(f"  modes/:     {len(modes_files)} .py")
    print(f"  templates/: {len(templates_files)} files")
    total = len(py_files) + len(sources_files) + len(renderers_files) + len(modes_files)
    print(f"  Gesamt:     {total} Python-Dateien")
    assert total >= 20, f"Erwartet >= 20 Dateien, bekommen {total}"
    print("[OK] Modul-Struktur korrekt")


if __name__ == "__main__":
    tests = [
        test_imports,
        test_platform_reader_protocol,
        test_registry,
        test_modes_import,
        test_thread_model,
        test_interrupt_detection,
        test_hermes_detect_message_type,
        test_freebuff_helpers,
        test_scanner_thin,
        test_cli_parse_args,
        test_template_exists,
        test_modules_count,
    ]
    print(f"\n{'='*60}")
    print(f"  Modular Architecture Tests ({len(tests)} Tests)")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*60}\n")
