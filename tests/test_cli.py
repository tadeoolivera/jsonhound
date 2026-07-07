"""End-to-end tests for main(), with the httpx2 network call mocked out."""

import json
import sys

import pytest

import jsonhound

URL = "https://example.test/data"


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeHttpx:
    """Stand-in for the httpx2 module: records calls, returns canned JSON."""

    def __init__(self, data):
        self._data = data
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        return FakeResponse(self._data)


def run(monkeypatch, capsys, data, state_file, extra_args=None):
    """Run main() with httpx2 mocked to return `data`; return (out, err, fake)."""
    fake = FakeHttpx(data)
    monkeypatch.setattr(jsonhound, "httpx2", fake)
    argv = ["jsonhound.py", URL, "--no-color", "-o", str(state_file)]
    if extra_args:
        argv += extra_args
    monkeypatch.setattr(sys, "argv", argv)
    jsonhound.main()
    captured = capsys.readouterr()
    return captured.out, captured.err, fake


def read_state(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def test_first_run_saves_initial_state(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    out, _, _ = run(monkeypatch, capsys, [{"id": 1, "title": "A"}], state)

    assert "First run" in out
    assert "(saved initial state)" in out
    assert state.exists()
    # a list root is indexed by the key field, coerced to str
    assert read_state(state) == {"1": {"id": 1, "title": "A"}}


def test_second_identical_run_reports_no_changes(monkeypatch, capsys, tmp_path):
    # Regression: integer `id` keys must survive the JSON round-trip so that an
    # unchanged endpoint does not look like "everything is new".
    state = tmp_path / "state.json"
    data = [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]

    run(monkeypatch, capsys, data, state)
    out, _, _ = run(monkeypatch, capsys, data, state)

    assert "No changes" in out
    assert "new" not in out
    assert "removed" not in out
    assert "modified" not in out


def test_default_timeout_passed_to_httpx(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    _, _, fake = run(monkeypatch, capsys, [{"id": 1}], state)
    assert fake.calls == [(URL, 10.0)]


def test_new_item_detected(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    run(monkeypatch, capsys, [{"id": 1}], state)
    out, _, _ = run(monkeypatch, capsys, [{"id": 1}, {"id": 2}], state)

    assert "+1 new:" in out
    assert "    2" in out


def test_removed_item_detected(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    run(monkeypatch, capsys, [{"id": 1}, {"id": 2}], state)
    out, _, _ = run(monkeypatch, capsys, [{"id": 1}], state)

    assert "-1 removed:" in out
    assert "    2" in out


def test_modified_item_shows_field_diff(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    run(monkeypatch, capsys, [{"id": 1, "title": "A", "score": 10}], state)
    out, _, _ = run(monkeypatch, capsys, [{"id": 1, "title": "B", "score": 10}], state)

    assert "~1 modified:" in out
    # changed field rendered as old -> new using an arrow (not an em-dash)
    assert "~ title: A → B" in out
    # an unchanged field is not reported
    assert "score" not in out


def test_modified_item_reports_added_and_removed_fields(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    run(monkeypatch, capsys, [{"id": 1, "a": 1}], state)
    out, _, _ = run(monkeypatch, capsys, [{"id": 1, "b": 2}], state)

    assert "~1 modified:" in out
    assert "+ b:" in out
    assert "- a:" in out


def test_dict_root_used_as_is(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    data = {"alpha": {"v": 1}, "beta": {"v": 2}}
    out, _, _ = run(monkeypatch, capsys, data, state)

    assert "First run" in out
    assert read_state(state) == data


def test_custom_key_field(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    run(
        monkeypatch,
        capsys,
        [{"username": "neo", "role": "admin"}],
        state,
        extra_args=["-k", "username"],
    )
    assert read_state(state) == {"neo": {"username": "neo", "role": "admin"}}


def test_display_fields_in_report(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    disp = ["-d", "title", "author"]
    run(monkeypatch, capsys, [{"id": 1, "title": "Hello", "author": "me"}], state, disp)
    out, _, _ = run(
        monkeypatch,
        capsys,
        [
            {"id": 1, "title": "Hello", "author": "me"},
            {"id": 2, "title": "World", "author": "you"},
        ],
        state,
        disp,
    )
    assert "World | you" in out


def test_missing_key_exits_with_error(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, capsys, [{"name": "x"}], state)  # default key is "id"
    assert exc.value.code == 1
    assert "key 'id' not found" in capsys.readouterr().err


def test_non_container_root_exits_with_error(monkeypatch, capsys, tmp_path):
    state = tmp_path / "state.json"
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, capsys, 42, state)
    assert exc.value.code == 1
    assert "must be a list or dict" in capsys.readouterr().err
