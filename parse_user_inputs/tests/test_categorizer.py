"""
Tests für parse_user_inputs.categorizer
"""

from parse_user_inputs.categorizer import (
    categorize,
    is_real_user_input,
    is_project_session,
    CATEGORIES,
)


class TestCategorize:
    """Tests für die Kategorisierungsfunktion."""

    def test_single_keyword_match(self):
        result = categorize("Ich brauche ein MCP addon")
        assert "MCP_ADDON" in result

    def test_multiple_categories(self):
        result = categorize("Bug im headless modus fixen")
        assert "BUG" in result
        assert "HEADLESS_VERBOT" in result

    def test_no_match_returns_uncategorized(self):
        result = categorize("Hallo wie geht es dir")
        assert result == ["UNCATEGORIZED"]

    def test_case_insensitive(self):
        result = categorize("Refactor den Code bitte")
        assert "REFACTOR" in result

    def test_empty_string(self):
        result = categorize("")
        assert result == ["UNCATEGORIZED"]

    def test_all_categories_have_keywords(self):
        for cat, definition in CATEGORIES.items():
            assert isinstance(definition, dict), f"Kategorie {cat} ist kein Dict"
            assert len(definition.get("keywords", [])) > 0 or len(definition.get("phrases", [])) > 0, \
                f"Kategorie {cat} hat keine Keywords/Phrases"

    def test_known_gameplay_keywords(self):
        assert "GAMEPLAY" in categorize("Schiff bauen in der Werft")
        assert "GAMEPLAY" in categorize("Forschung für neue Technologien")


class TestIsRealUserInput:
    """Tests für die User-Input-Validierung."""

    def test_normal_input(self):
        assert is_real_user_input("Bitte fixe den Bug im Menü") is True

    def test_empty_string(self):
        assert is_real_user_input("") is False
        assert is_real_user_input("   ") is False

    def test_none(self):
        assert is_real_user_input(None) is False  # type: ignore[arg-type]

    def test_init_marker(self):
        assert is_real_user_input("[/init] some system prompt") is False

    def test_skill_invocation(self):
        assert is_real_user_input("[IMPORTANT: The user has invoked /test]") is False

    def test_thinking_process(self):
        assert is_real_user_input("Here's a thinking process...") is False

    def test_interrupt(self):
        assert is_real_user_input("⚡ Interrupt received") is False

    def test_continue_working(self):
        assert is_real_user_input("continue working toward goal") is False

    def test_model_switch(self):
        assert is_real_user_input("[Note: model was just switched to gpt4]") is False

    def test_cutoff(self):
        assert is_real_user_input("[System: The previous response was cut off]") is False

    def test_short_blockquote(self):
        assert is_real_user_input("> das sieht gut aus") is False

    def test_long_blockquote_is_valid(self):
        text = "> " + "x" * 200
        assert is_real_user_input(text) is True

    def test_context_reinjection(self):
        assert is_real_user_input("[Context from the interrupted session]") is False


class TestIsProjectSession:
    """Tests für die Projekt-Session-Erkennung."""

    def test_godot_project(self):
        assert is_project_session("Godot Game", "hermes", "") is True

    def test_snip_session(self):
        assert is_project_session("SnipWar Refactor", "glm", "") is True

    def test_empty_session(self):
        assert is_project_session("", "", "") is False

    def test_irrelevant_session(self):
        assert is_project_session("Random Chat", "gpt4", "Hello world") is False
