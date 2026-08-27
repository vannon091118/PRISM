"""
parse_user_inputs.platforms
===========================
Registrierung aller bekannten AI-Coding-Agent-Plattformen.
Pfade basieren auf offizieller Doku + tokscale-Datenbank (38+ Plattformen).

Alle Pfade sind portabel: ~, $XDG_*, $HOME, %APPDATA%, %LOCALAPPDATA%
werden automatisch aufgelöst.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StoragePath:
    """Ein einzelner Speicherpfad mit Beschreibung und Typ."""
    path: str
    description: str
    file_type: str  # "sqlite", "jsonl", "json", "directory", "glob"


@dataclass(frozen=True)
class Platform:
    """Definiert eine AI-Agent-Plattform und ihre lokalen Speicherorte."""
    id: str
    name: str
    vendor: str
    description: str
    variant: str = "cli"  # cli, desktop, extension, web
    storage_paths: list[StoragePath] = field(default_factory=list)
    env_override: str = ""  # z.B. "HERMES_HOME", "CODEBUFF_DATA_DIR"

    def resolve_paths(self) -> list[tuple[str, str, str]]:
        """Loest alle Pfade auf und gibt (resolved, desc, type) tuples zurueck."""
        home = Path.home()
        results = []
        for sp in self.storage_paths:
            raw = sp.path
            resolved = _resolve_path(raw, home)
            results.append((resolved, sp.description, sp.file_type))
        return results


def _resolve_path(raw: str, home: Path) -> str:
    """Loest ~, $ENV, %ENV% in Pfaden auf."""
    # ~ am Anfang
    if raw.startswith("~"):
        resolved = str(home / raw[2:])
    # %VAR% Windows-Style
    elif "%" in raw and raw.count("%") >= 2:
        import re
        def _replace_win(m):
            var = m.group(1)
            if var == "USERPROFILE":
                return str(home)
            elif var == "APPDATA":
                return os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
            elif var == "LOCALAPPDATA":
                return os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
            elif var == "APPDATA%\\Code":
                return os.environ.get("APPDATA", str(home / "AppData" / "Roaming")) + "\\Code"
            else:
                return os.environ.get(var, m.group(0))
        resolved = re.sub(r"%([^%]+)%", _replace_win, raw)
    # $ENV Unix-Style
    elif "$" in raw:
        import re
        def _replace_unix(m):
            var = m.group(1)
            if var == "HOME":
                return str(home)
            elif var == "XDG_CONFIG_HOME":
                return os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
            elif var == "XDG_DATA_HOME":
                return os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
            elif var == "HERMES_HOME":
                return os.environ.get("HERMES_HOME", str(home / ".hermes"))
            elif var == "GEMINI_CLI_HOME":
                return os.environ.get("GEMINI_CLI_HOME", str(home / ".gemini"))
            elif var == "GROK_HOME":
                return os.environ.get("GROK_HOME", str(home / ".grok"))
            elif var == "CLINE_SESSION_DATA_DIR":
                return os.environ.get("CLINE_SESSION_DATA_DIR", "")
            elif var == "CLINE_DATA_DIR":
                return os.environ.get("CLINE_DATA_DIR", "")
            elif var == "CLINE_DIR":
                return os.environ.get("CLINE_DIR", "")
            elif var == "CODEBUFF_DATA_DIR":
                return os.environ.get("CODEBUFF_DATA_DIR", "")
            elif var == "FREEBUFF_DATA_DIR":
                return os.environ.get("FREEBUFF_DATA_DIR", "")
            else:
                return os.environ.get(var, m.group(0))
        resolved = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", _replace_unix, raw)
    else:
        resolved = raw
    return resolved


# ═════════════════════════════════════════════════════════════════════════════
# Plattform-Definitionen (sortiert nach Beliebtheit)
# ═════════════════════════════════════════════════════════════════════════════

CLAUDE_CODE = Platform(
    id="claude_code",
    name="Claude Code",
    vendor="Anthropic",
    description="Agentic CLI — history in ~/.claude/history.jsonl + transcripts",
    variant="cli",
    env_override="CLAUDE_CODE_DIR",
    storage_paths=[
        StoragePath("~/.claude/history.jsonl", "User input history", "jsonl"),
        StoragePath("~/.claude/projects", "Project session transcripts (JSONL)", "glob:*.jsonl"),
        StoragePath("~/.claude/transcripts", "Transcript files", "directory"),
        StoragePath("~/.claude/settings.json", "Global settings", "json"),
    ],
)

CLAUDE_DESKTOP = Platform(
    id="claude_desktop",
    name="Claude Desktop",
    vendor="Anthropic",
    description="Desktop App — conversations stored server-side",
    variant="desktop",
    storage_paths=[
        StoragePath("%APPDATA%/Claude", "Windows: Claude Desktop data", "directory"),
        StoragePath("~/Library/Application Support/Claude", "macOS: Claude Desktop data", "directory"),
    ],
)

GEMINI_CLI = Platform(
    id="gemini_cli",
    name="Gemini CLI (Antigravity CLI)",
    vendor="Google",
    description="Terminal AI agent — history + conversation DBs",
    variant="cli",
    env_override="GEMINI_CLI_HOME",
    storage_paths=[
        StoragePath("~/.gemini/antigravity-cli/history.jsonl", "User input history", "jsonl"),
        StoragePath("~/.gemini/antigravity-cli/conversations", "Conversation SQLite DBs", "directory"),
        StoragePath("$GEMINI_CLI_HOME/tmp/*/chats/*.json", "Session chats (tokscale)", "glob"),
    ],
)

GEMINI_DESKTOP = Platform(
    id="gemini_desktop",
    name="Gemini Desktop (Antigravity)",
    vendor="Google",
    description="Desktop App — conversation DBs (protobuf format)",
    variant="desktop",
    storage_paths=[
        StoragePath("~/.gemini/antigravity/conversations", "Conversation SQLite DBs (protobuf)", "directory"),
        StoragePath("~/.gemini/antigravity/annotations", "Annotations (pbtxt)", "directory"),
    ],
)

CODEX = Platform(
    id="codex",
    name="OpenAI Codex",
    vendor="OpenAI",
    description="CLI — sessions in ~/.codex/sessions/",
    variant="cli",
    storage_paths=[
        StoragePath("~/.codex/sessions", "Session JSONL files", "directory"),
        StoragePath("~/.codex/history.jsonl", "User input history (legacy)", "jsonl"),
        StoragePath("~/.codex/state_5.sqlite", "Thread state database", "sqlite"),
        StoragePath("~/.codex/logs_2.sqlite", "Log database", "sqlite"),
    ],
)

CODEX_DESKTOP = Platform(
    id="codex_desktop",
    name="Codex Desktop",
    vendor="OpenAI",
    description="Desktop App — sessions stored server-side",
    variant="desktop",
    storage_paths=[
        StoragePath("%LOCALAPPDATA%/Codex", "Windows: Codex Desktop data", "directory"),
        StoragePath("~/Library/Application Support/Codex", "macOS: Codex Desktop data", "directory"),
    ],
)

CURSOR = Platform(
    id="cursor",
    name="Cursor",
    vendor="Cursor",
    variant="desktop",
    description="AI-native code editor — chats in state.vscdb",
    storage_paths=[
        StoragePath("~/.cursor/User/globalStorage/state.vscdb", "Global state database", "sqlite"),
        StoragePath("%APPDATA%/Cursor/User/globalStorage/state.vscdb", "Windows: Global state database", "sqlite"),
        StoragePath("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb", "macOS: Global state database", "sqlite"),
    ],
)

HERMES = Platform(
    id="hermes",
    name="Hermes Agent",
    vendor="NousResearch",
    description="Model-agnostic conversational agent — SQLite state",
    storage_paths=[
        StoragePath("$HERMES_HOME/state.db", "SQLite state database", "sqlite"),
        StoragePath("~/.hermes/state.db", "Fallback: SQLite state database", "sqlite"),
        StoragePath("$HERMES_HOME/profiles/*/state.db", "Profile-specific state", "sqlite"),
        StoragePath("~/.hermes/sessions", "Session metadata directory", "directory"),
        StoragePath("~/.hermes/memories", "Curated memory files", "directory"),
        StoragePath("%LOCALAPPDATA%/hermes/state.db", "Windows: SQLite state database", "sqlite"),
        StoragePath("%LOCALAPPDATA%/hermes/sessions", "Windows: Session metadata", "directory"),
    ],
)

FREEBUFF = Platform(
    id="freebuff",
    name="Freebuff / Codebuff",
    vendor="Codebuff",
    variant="desktop",
    description="Desktop AI coding agent — shares ~/.config/manicode/ with Codebuff",
    env_override="FREEBUFF_DATA_DIR",
    storage_paths=[
        StoragePath("~/.config/manicode", "Shared Codebuff/Freebuff data", "directory"),
        StoragePath("~/.config/manicode/projects/<project>/chats/<chatId>/chat", "Per-project chat data", "directory"),
    ],
)

AIDER = Platform(
    id="aider",
    name="Aider",
    vendor="Aider-AI",
    variant="cli",
    description="Terminal pair programmer — .aider.chat.history.md",
    storage_paths=[
        StoragePath("~/.aider", "Aider config and history", "directory"),
        StoragePath("~/.aider.chat.history.md", "Aider chat history", "json"),
    ],
)

WINDSURF = Platform(
    id="windsurf",
    name="Windsurf",
    vendor="Codeium",
    variant="desktop",
    description="AI-native editor — Cascade chats in state.vscdb",
    storage_paths=[
        StoragePath("%APPDATA%/Windsurf/User/globalStorage/state.vscdb", "Windsurf global state database", "sqlite"),
        StoragePath("~/.windsurf/User/globalStorage/state.vscdb", "Linux: Windsurf state database", "sqlite"),
        StoragePath("~/Library/Application Support/Windsurf/User/globalStorage/state.vscdb", "macOS: Windsurf state database", "sqlite"),
    ],
)

# ─── VS Code Extensions ──────────────────────────────────────────────────────

COPILOT = Platform(
    id="copilot",
    name="GitHub Copilot",
    vendor="GitHub / Microsoft",
    variant="extension",
    description="VS Code extension — chat in workspaceStorage + OTEL logs",
    storage_paths=[
        StoragePath("~/.copilot/otel/*.jsonl", "Copilot OTEL logs (CLI)", "glob"),
        StoragePath("$COPILOT_OTEL_FILE_EXPORTER_PATH", "Custom OTEL export path", "jsonl"),
        StoragePath("%APPDATA%/Code/User/workspaceStorage", "VS Code workspace storage", "directory"),
        StoragePath("%APPDATA%/Code/User/globalStorage", "VS Code global storage", "directory"),
        StoragePath("~/.vscode-server/data/User/workspaceStorage", "VS Code Remote workspace storage", "directory"),
    ],
)

CLINE = Platform(
    id="cline",
    name="Cline",
    vendor="Cline (cline)",
    variant="extension",
    description="VS Code extension + CLI — task history + session logs",
    storage_paths=[
        StoragePath("%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/tasks", "Cline VS Code task history", "directory"),
        StoragePath("~/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/tasks", "VS Code Remote: Cline tasks", "directory"),
        StoragePath("$CLINE_SESSION_DATA_DIR", "Cline CLI session data", "directory"),
        StoragePath("$CLINE_DATA_DIR/sessions/", "Cline CLI sessions", "directory"),
        StoragePath("$CLINE_DIR/data/sessions/", "Cline CLI data sessions", "directory"),
        StoragePath("~/.cline/data/sessions/", "Fallback: Cline CLI sessions", "directory"),
    ],
)

ROO_CODE = Platform(
    id="roo_code",
    name="Roo Code",
    vendor="RooCodeInc",
    variant="extension",
    description="Cline fork — task history in globalStorage",
    storage_paths=[
        StoragePath("~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks", "Roo Code task history (Linux)", "directory"),
        StoragePath("%APPDATA%/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks", "Roo Code task history (Windows)", "directory"),
        StoragePath("~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/tasks", "Roo Code task history (macOS)", "directory"),
        StoragePath("~/.vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/tasks", "VS Code Remote: Roo Code tasks", "directory"),
    ],
)

KILO_CODE = Platform(
    id="kilo_code",
    name="Kilo Code",
    vendor="Kilo-Org",
    variant="extension",
    description="VS Code extension + CLI — task history + kilo.db",
    storage_paths=[
        StoragePath("~/.config/Code/User/globalStorage/kilocode.kilo-code/tasks", "Kilo Code task history (Linux)", "directory"),
        StoragePath("%APPDATA%/Code/User/globalStorage/kilocode.kilo-code/tasks", "Kilo Code task history (Windows)", "directory"),
        StoragePath("~/.vscode-server/data/User/globalStorage/kilocode.kilo-code/tasks", "VS Code Remote: Kilo Code tasks", "directory"),
        StoragePath("~/.local/share/kilo/kilo.db", "Kilo CLI SQLite database", "sqlite"),
    ],
)

CONTINUE_DEV = Platform(
    id="continue",
    name="Continue.dev",
    vendor="Continue (acquired by Cursor)",
    variant="extension",
    description="Open-source AI coding assistant — chat in globalStorage",
    storage_paths=[
        StoragePath("%APPDATA%/Code/User/globalStorage/continue.continue", "Continue.dev global storage", "directory"),
        StoragePath("~/.continue", "Continue config directory", "directory"),
    ],
)

# ─── Neue Plattformen (tokscale-basiert) ─────────────────────────────────────

OPENCODE = Platform(
    id="opencode",
    name="OpenCode",
    vendor="SST",
    variant="cli",
    description="Open-source coding agent — opencode.db + message storage",
    storage_paths=[
        StoragePath("~/.local/share/opencode/opencode.db", "OpenCode SQLite database (1.2+)", "sqlite"),
        StoragePath("~/.local/share/opencode/storage/message/", "Legacy message storage", "directory"),
    ],
)

OPENHANDS = Platform(
    id="openhands",
    name="OpenHands",
    vendor="OpenHands (All Hands AI)",
    variant="cli",
    description="SWE agent — conversation JSON in .openhands-state",
    storage_paths=[
        StoragePath("~/.openhands-state", "Conversation history (JSON files)", "directory"),
        StoragePath("~/.openhands", "OpenHands config directory", "directory"),
    ],
)

AMP = Platform(
    id="amp",
    name="Amp",
    vendor="Sourcegraph",
    variant="cli",
    description="Server-first coding agent — local thread JSON",
    storage_paths=[
        StoragePath("~/.local/share/amp/threads/", "Thread manager JSON files", "directory"),
        StoragePath("~/.amp", "Amp data directory", "directory"),
        StoragePath("~/.amp/oauth", "OAuth tokens", "directory"),
    ],
)

BEADS = Platform(
    id="beads",
    name="Beads",
    vendor="Beads",
    variant="cli",
    description="Git-friendly issue tracker for AI agents — SQLite per project",
    storage_paths=[
        StoragePath(".beads/beads.db", "Per-project SQLite issue database", "sqlite"),
    ],
)

CHATGPT = Platform(
    id="chatgpt_desktop",
    name="ChatGPT Desktop",
    vendor="OpenAI",
    variant="desktop",
    description="Desktop App — conversations in local storage",
    storage_paths=[
        StoragePath("%LOCALAPPDATA%/ChatGPT", "Windows: ChatGPT Desktop data", "directory"),
        StoragePath("~/Library/Application Support/ChatGPT", "macOS: ChatGPT Desktop data", "directory"),
        StoragePath("~/.config/ChatGPT", "Linux: ChatGPT config", "directory"),
    ],
)

PI_AGENT = Platform(
    id="pi_agent",
    name="Pi",
    vendor="Earendil Works",
    variant="cli",
    description="Lightweight coding agent — session JSONL logs",
    storage_paths=[
        StoragePath("~/.pi/agent/sessions/", "Pi agent session logs", "directory"),
        StoragePath("~/.pi-agent", "Pi-Agent data directory (legacy)", "directory"),
    ],
)

FACTORY = Platform(
    id="factory",
    name="Factory (Droid)",
    vendor="Factory AI",
    variant="cli",
    description="Enterprise coding agent — session logs",
    storage_paths=[
        StoragePath("~/.factory/sessions/", "Session logs", "directory"),
    ],
)

GROK_BUILD = Platform(
    id="grok_build",
    name="Grok Build",
    vendor="xAI",
    variant="cli",
    description="xAI coding agent — session history with nested updates",
    storage_paths=[
        StoragePath("$GROK_HOME/sessions/*/*/updates.jsonl", "Session updates", "glob"),
        StoragePath("~/.grok/sessions/*/*/updates.jsonl", "Fallback: session updates", "glob"),
    ],
)

PRIME_AGENT = Platform(
    id="prime_agent",
    name="Prime Agent",
    vendor="PrimeIntellect",
    variant="cli",
    description="RLM coding agent — session logs + artifacts",
    storage_paths=[
        StoragePath("~/.prime/agent/sessions/", "Session logs", "directory"),
        StoragePath("~/.prime/agent/session-artifacts/", "RLM child session artifacts", "directory"),
    ],
)

GOOSE = Platform(
    id="goose",
    name="Goose",
    vendor="AAIF Goose",
    variant="cli",
    description="AI agent framework — sessions.db",
    storage_paths=[
        StoragePath("~/.local/share/goose/sessions/sessions.db", "Sessions SQLite database", "sqlite"),
    ],
)

ZED_AGENT = Platform(
    id="zed",
    name="Zed Agent",
    vendor="Zed",
    variant="desktop",
    description="Zed editor AI agent — threads.db",
    storage_paths=[
        StoragePath("~/.local/share/zed/threads/threads.db", "Linux: threads database", "sqlite"),
        StoragePath("~/Library/Application Support/Zed/threads/threads.db", "macOS: threads database", "sqlite"),
        StoragePath("%LOCALAPPDATA%/Zed/threads/threads.db", "Windows: threads database", "sqlite"),
    ],
)

KIRO = Platform(
    id="kiro",
    name="Kiro",
    vendor="Amazon",
    variant="cli",
    description="Amazon AI coding agent — CLI sessions + SQLite + IDE globalStorage",
    storage_paths=[
        StoragePath("~/.kiro/sessions/cli/*.json", "CLI session JSON", "glob"),
        StoragePath("~/.kiro/sessions/cli/*.jsonl", "CLI session JSONL", "glob"),
        StoragePath("~/.local/share/kiro-cli/data.sqlite3", "Linux: CLI SQLite database", "sqlite"),
        StoragePath("~/Library/Application Support/kiro-cli/data.sqlite3", "macOS: CLI SQLite database", "sqlite"),
        StoragePath("%APPDATA%/Kiro/User/globalStorage/kiro.kiroagent", "Windows: Kiro IDE globalStorage", "directory"),
    ],
)

KIMCHI = Platform(
    id="kimchi",
    name="Kimchi Coding",
    vendor="Kimchi",
    variant="cli",
    description="AI coding agent — harness sessions",
    storage_paths=[
        StoragePath("~/.config/kimchi/harness/sessions/", "Session logs", "directory"),
    ],
)

KIMI = Platform(
    id="kimi",
    name="Kimi CLI / Kimi Code",
    vendor="MoonshotAI",
    variant="cli",
    description="Moonshot AI coding agents — session logs",
    storage_paths=[
        StoragePath("~/.kimi/sessions/", "Kimi CLI sessions", "directory"),
        StoragePath("~/.kimi-code/sessions/", "Kimi Code sessions", "directory"),
    ],
)

QWEN_CLI = Platform(
    id="qwen_cli",
    name="Qwen CLI",
    vendor="Alibaba",
    variant="cli",
    description="Qwen coding agent — project logs",
    storage_paths=[
        StoragePath("~/.qwen/projects/", "Project session logs", "directory"),
    ],
)

MUX = Platform(
    id="mux",
    name="Mux",
    vendor="Coder",
    variant="cli",
    description="Coding agent — session logs",
    storage_paths=[
        StoragePath("~/.mux/sessions/", "Session logs", "directory"),
    ],
)

JUNIE = Platform(
    id="junie",
    name="Junie",
    vendor="JetBrains",
    variant="cli",
    description="JetBrains AI coding agent — session event logs",
    storage_paths=[
        StoragePath("~/.junie/sessions/*/events.jsonl", "Session event logs", "glob"),
    ],
)

SENPI = Platform(
    id="senpi",
    name="Senpi (OmO Native)",
    vendor="code-yeongyu",
    variant="cli",
    description="Native coding agent — session logs",
    storage_paths=[
        StoragePath("~/.senpi/agent/sessions/", "Session logs", "directory"),
    ],
)

CRUSH = Platform(
    id="crush",
    name="Crush",
    vendor="Crush AI",
    variant="cli",
    description="AI coding agent — project registry",
    storage_paths=[
        StoragePath("$XDG_DATA_HOME/crush/projects.json", "Project registry", "json"),
    ],
)

# ═════════════════════════════════════════════════════════════════════════════
# Plattform-Registry
# ═════════════════════════════════════════════════════════════════════════════

ALL_PLATFORMS: list[Platform] = [
    # Top-Reihenfolge nach Beliebtheit
    CLAUDE_CODE,
    GEMINI_CLI,
    CODEX,
    FREEBUFF,
    CURSOR,
    HERMES,
    GEMINI_DESKTOP,
    AIDER,
    WINDSURF,
    CLAUDE_DESKTOP,
    COPILOT,
    CLINE,
    ROO_CODE,
    KILO_CODE,
    CONTINUE_DEV,
    OPENCODE,
    OPENHANDS,
    AMP,
    BEADS,
    CHATGPT,
    PI_AGENT,
    FACTORY,
    GROK_BUILD,
    PRIME_AGENT,
    GOOSE,
    ZED_AGENT,
    KIRO,
    KIMCHI,
    KIMI,
    QWEN_CLI,
    MUX,
    JUNIE,
    SENPI,
    CRUSH,
]

PLATFORM_BY_ID: dict[str, Platform] = {p.id: p for p in ALL_PLATFORMS}


def get_platform(platform_id: str) -> Platform | None:
    """Gibt eine Plattform anhand ihrer ID zurueck."""
    return PLATFORM_BY_ID.get(platform_id)


def list_platforms() -> list[dict[str, str]]:
    """Listet alle Plattformen als dicts auf."""
    return [{"id": p.id, "name": p.name, "vendor": p.vendor, "description": p.description} for p in ALL_PLATFORMS]
