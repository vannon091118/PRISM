"""
Tests für parse_user_inputs.config
"""

import os
from parse_user_inputs.config import Config


class TestConfig:
    """Tests für die Konfiguration."""

    def test_default_project_path_fallback(self):
        """Ohne ENV-Variablen und ohne Git-Repo → cwd als Fallback."""
        cfg = Config()
        # resolve_project_path should return something
        result = cfg.resolve_project_path()
        assert result is not None
        assert len(result) > 0

    def test_explicit_project_path(self):
        cfg = Config(project_path="/tmp/test")
        result = cfg.resolve_project_path()
        assert result == "/tmp/test"

    def test_resolve_output_paths(self):
        cfg = Config()
        paths = cfg.resolve_output_paths("/tmp/project")
        assert paths["md"].endswith(".md")
        assert paths["html"].endswith(".html")
        assert paths["json"].endswith(".json")
        # Platform-aware: Windows uses backslash
        import os
        normalized = os.path.normpath(paths["md"])
        assert "project" in normalized

    def test_freebuff_api_url(self):
        cfg = Config(freebuff_api_host="192.168.1.1", freebuff_api_port=8080)
        assert cfg.freebuff_api_url == "http://192.168.1.1:8080"

    def test_env_override(self):
        os.environ["USER_INPUTS_DB_PATH"] = "/tmp/fake.db"
        try:
            cfg = Config()
            assert cfg.db_path == "/tmp/fake.db"
        finally:
            del os.environ["USER_INPUTS_DB_PATH"]
