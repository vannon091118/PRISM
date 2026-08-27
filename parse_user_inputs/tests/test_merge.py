"""
Tests for parse_user_inputs Sorting/Dedup Logic
"""

from parse_user_inputs.sorting import merge_and_dedup, parse_date, sort_key_multi


class TestMergeAndDedup:
    """Tests für die Merge- und Deduplizierungslogik."""

    def test_empty_lists(self):
        result = merge_and_dedup([], [], [])
        assert result == []

    def test_no_duplicates(self):
        list1 = [{"session": "aaa", "content": "Dies ist ein Test Input", "date": "2026-01-01"}]
        list2 = [{"session": "bbb", "content": "Ein komplett anderer Text hier", "date": "2026-01-02"}]
        result = merge_and_dedup(list1, list2)
        assert len(result) == 2

    def test_dedup_same_session_and_content(self):
        item = {"session": "aaa", "content": "Hallo Welt", "date": "2026-01-01"}
        result = merge_and_dedup([item], [item])
        assert len(result) == 1

    def test_fuzzy_dedup_similar_content(self):
        # Aehnlicher Text wird als Duplikat erkannt (Jaccard > 0.6)
        item1 = {"session": "aaa", "content": "Fix the bug in the parser module now", "date": "2026-01-01"}
        item2 = {"session": "bbb", "content": "Fix the bug in the parser module", "date": "2026-01-02"}
        result = merge_and_dedup([item1], [item2])
        assert len(result) == 1  # Fuzzy-Duplikat

    def test_different_sessions_same_content(self):
        # Gleicher Inhalt in verschiedenen Sessions wird dedupliziert
        item1 = {"session": "aaa", "content": "Hallo Welt Test Input", "date": "2026-01-01"}
        item2 = {"session": "bbb", "content": "Hallo Welt Test Input", "date": "2026-01-02"}
        result = merge_and_dedup([item1], [item2])
        assert len(result) == 1  # Hash-Dedup erkennt gleichen Inhalt

    def test_sorted_by_date(self):
        item1 = {"session": "aaa", "content": "Erstes", "date": "2026-03-01"}
        item2 = {"session": "bbb", "content": "Zweites", "date": "2026-01-01"}
        result = merge_and_dedup([item1], [item2])
        assert result[0]["date"] == "2026-01-01"
        assert result[1]["date"] == "2026-03-01"

    def test_missing_keys(self):
        item = {"content": "Ohne Session", "date": "2026-01-01"}
        result = merge_and_dedup([item])
        assert len(result) == 1

    def test_sort_by_platform(self):
        """Mehrstufige Sortierung: Datum -> Plattform."""
        item1 = {"session": "a", "content": "Alpha Input Test", "date": "2026-01-01", "platform": "zebra"}
        item2 = {"session": "b", "content": "Beta Input Test", "date": "2026-01-01", "platform": "alpha"}
        result = merge_and_dedup([item1, item2])
        assert result[0]["platform"] == "alpha"
        assert result[1]["platform"] == "zebra"

    def test_sort_by_content_length(self):
        """Mehrstufige Sortierung: Laengste Inputs zuerst bei gleichem Datum."""
        item1 = {"session": "a", "content": "Kurzer Test Input", "date": "2026-01-01", "platform": "x"}
        item2 = {"session": "b", "content": "Ein sehr langer Test Input mit vielen Worten", "date": "2026-01-01", "platform": "x"}
        result = merge_and_dedup([item1, item2])
        assert len(result) >= 1
        if len(result) == 2:
            assert len(result[0]["content"]) >= len(result[1]["content"])

    def test_parse_date(self):
        """Datum-Parsing mit verschiedenen Formaten."""
        assert parse_date("2026-01-15 10:30").year == 2026
        assert parse_date("2026-01-15T10:30:00").hour == 10
        assert parse_date("2026-01-15").day == 15
        assert parse_date("?").year == 1  # datetime.min
        assert parse_date("").year == 1

    def test_normalized_dedup(self):
        """Fuzzy-Dedup: Gleicher Text in Gross/Klein."""
        item1 = {"session": "a", "content": "Hallo Welt Test Input hier ist viel Text", "date": "2026-01-01"}
        item2 = {"session": "b", "content": "hallo welt test input hier ist viel text", "date": "2026-01-01"}
        result = merge_and_dedup([item1, item2])
        assert len(result) == 1
