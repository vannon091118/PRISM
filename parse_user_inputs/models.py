"""
parse_user_inputs.models
========================
Datenmodelle für Threads: User-Input -> Agent-Reaktion -> Ergebnis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """Einzelne Nachricht in einem Thread."""
    role: str  # "user", "assistant", "tool", "system", "interrupt", "followup"
    content: str
    timestamp: str = "?"
    model: str = ""
    message_type: str = "normal"  # normal, interrupt, followup, system, model_switch

    @property
    def is_user(self) -> bool:
        return self.role == "user"

    @property
    def is_agent(self) -> bool:
        return self.role in ("assistant", "agent")

    @property
    def is_tool(self) -> bool:
        return self.role == "tool"

    @property
    def is_interrupt(self) -> bool:
        return self.message_type == "interrupt"

    @property
    def is_followup(self) -> bool:
        return self.message_type == "followup"

    @property
    def is_system(self) -> bool:
        return self.role == "system" or self.message_type == "system"


@dataclass
class Thread:
    """
    Ein vollständiger Konversations-Thread:
    User-Input -> Agent-Reaktion -> Ergebnis.
    """
    id: str
    platform: str
    project: str
    title: str
    date: str
    messages: list[Message] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    git_commits: list[dict[str, Any]] = field(default_factory=list)

    @property
    def user_input(self) -> str:
        """Erste echte User-Nachricht."""
        for m in self.messages:
            if m.is_user:
                return m.content
        return ""

    @property
    def agent_reaction(self) -> str:
        """Erste Assistant-Antwort nach dem User-Input."""
        seen_user = False
        for m in self.messages:
            if m.is_user:
                seen_user = True
            elif seen_user and m.is_agent:
                return m.content
        return ""

    @property
    def result_summary(self) -> str:
        """Zusammenfassung des Ergebnisses (letzte Assistant-Antwort oder Tool-Output)."""
        last_agent = ""
        for m in reversed(self.messages):
            if m.is_agent:
                last_agent = m.content
                break
        return last_agent

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def user_message_count(self) -> int:
        return sum(1 for m in self.messages if m.is_user)

    @property
    def has_agent_response(self) -> bool:
        return any(m.is_agent for m in self.messages)

    def _serializable_messages(self) -> list[dict[str, Any]]:
        """Serialisiert Messages fuer JSON, priorisiert Interrupts/Follow-ups."""
        result = []
        # Zuerst normale Messages (max 12)
        normal_count = 0
        special = []
        for m in self.messages:
            if m.message_type in ("interrupt", "followup", "system", "model_switch"):
                special.append(m)
            elif normal_count < 12:
                result.append({
                    "role": m.role,
                    "content": m.content[:2000],
                    "timestamp": m.timestamp,
                    "message_type": m.message_type,
                })
                normal_count += 1
        # Dann special Messages hinzufuegen
        for m in special:
            result.append({
                "role": m.role,
                "content": m.content[:2000],
                "timestamp": m.timestamp,
                "message_type": m.message_type,
            })
        return result

    @property
    def has_interrupts(self) -> bool:
        return any(m.is_interrupt for m in self.messages)

    @property
    def has_followups(self) -> bool:
        return any(m.is_followup for m in self.messages)

    @property
    def has_commits(self) -> bool:
        return len(self.git_commits) > 0

    @property
    def commit_status(self) -> str:
        if self.git_commits:
            return "committed"
        return "none"

    @property
    def artifacts(self) -> list[dict[str, Any]]:
        """Gibt Artefakte (PRs, Branches) aus der Metadata zurueck."""
        return self.metadata.get("artifacts", [])

    @property
    def has_pr(self) -> bool:
        return any(a.get("type") in ("pull_request", "local_merge") for a in self.artifacts)

    @property
    def has_branch(self) -> bool:
        return any(a.get("type") == "branch" for a in self.artifacts)

    @property
    def pr_status(self) -> str:
        """PR-Status: merged, open, none."""
        for a in self.artifacts:
            if a.get("type") in ("pull_request", "local_merge"):
                return a.get("status", "open")
        return "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "project": self.project,
            "title": self.title,
            "date": self.date,
            "categories": self.categories,
            "user_input": self.user_input[:2000],
            "agent_reaction": self.agent_reaction[:2000],
            "result_summary": self.result_summary[:2000],
            "message_count": self.message_count,
            "user_message_count": self.user_message_count,
            "has_agent_response": self.has_agent_response,
            "has_interrupts": self.has_interrupts,
            "has_followups": self.has_followups,
            "has_commits": self.has_commits,
            "commit_status": self.commit_status,
            "git_commits": self.git_commits[:5],
            "artifacts": self.artifacts[:5],
            "has_pr": self.has_pr,
            "pr_status": self.pr_status,
            "has_branch": self.has_branch,
            "messages": self._serializable_messages(),
        }
