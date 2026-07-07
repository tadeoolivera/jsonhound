"""Unit tests for the pure helper functions in jsonhound."""

import jsonhound


class TestFmt:
    def test_short_string_unchanged(self):
        assert jsonhound.fmt("hello") == "hello"

    def test_non_string_is_json_encoded(self):
        assert jsonhound.fmt(42) == "42"
        assert jsonhound.fmt({"a": 1}) == '{"a": 1}'
        assert jsonhound.fmt(["x", "y"]) == '["x", "y"]'

    def test_non_ascii_preserved(self):
        # ensure_ascii=False keeps the accented char literal
        assert jsonhound.fmt({"k": "ñ"}) == '{"k": "ñ"}'

    def test_boundary_80_chars_not_truncated(self):
        s = "a" * 80
        assert jsonhound.fmt(s) == s

    def test_over_80_chars_truncated_to_80(self):
        out = jsonhound.fmt("a" * 81)
        assert out == "a" * 77 + "..."
        assert len(out) == 80


class TestColor:
    def test_wraps_text_with_ansi_code_and_reset(self):
        assert jsonhound.color("hi", jsonhound.GREEN) == "\033[92mhi\033[0m"


class TestFieldDiff:
    def test_added_key(self):
        assert list(jsonhound.field_diff({}, {"a": 1})) == [("a", None, 1)]

    def test_removed_key(self):
        assert list(jsonhound.field_diff({"a": 1}, {})) == [("a", 1, None)]

    def test_changed_value(self):
        assert list(jsonhound.field_diff({"a": 1}, {"a": 2})) == [("a", 1, 2)]

    def test_unchanged_key_not_yielded(self):
        assert list(jsonhound.field_diff({"a": 1}, {"a": 1})) == []

    def test_result_is_sorted_by_key(self):
        old = {"b": 1, "a": 1}
        new = {"a": 2, "c": 3}
        assert list(jsonhound.field_diff(old, new)) == [
            ("a", 1, 2),
            ("b", 1, None),
            ("c", None, 3),
        ]
