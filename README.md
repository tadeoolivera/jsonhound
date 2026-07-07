# jsonhound

[![CI](https://github.com/tadeoolivera/jsonhound/actions/workflows/ci.yml/badge.svg)](https://github.com/tadeoolivera/jsonhound/actions/workflows/ci.yml)

Sniff out changes in JSON APIs.

A lean CLI tool that fetches JSON from an HTTP endpoint, remembers the last state, and barks when something's new, removed, or modified (with color-coded field-level diffs).

## Install

```bash
uv add httpx2
```

## Usage

```bash
uv run jsonhound.py <url> [options]
```

First run saves the initial state. Every run after that prints a diff.

```bash
# Basic - sniff a list of items keyed by "id"
uv run jsonhound.py https://api.example.com/posts

# Key by a different field, save state elsewhere
uv run jsonhound.py https://api.example.com/users -k username -o users-state.json

# Show specific fields in reports
uv run jsonhound.py https://api.example.com/posts -d title author

# Quieter output for cron / CI
uv run jsonhound.py https://api.example.com/posts --no-color
```

## Options

| Argument | Default | Description |
|---|---|---|
| `url` | - | URL to fetch JSON from |
| `-o`, `--output` | `saved.json` | Path to save/read the previous state |
| `-k`, `--key` | `id` | Field used as unique identifier for list items |
| `-d`, `--display` | (the key field) | Field(s) shown in change reports |
| `--timeout` | `10.0` | HTTP request timeout in seconds |
| `--no-color` | - | Disable colored output |

## How it works

1. Fetches JSON from the given URL
2. If the root is a **list**, items are indexed by their `--key` field
3. If the root is a **dict**, it's used as-is (keys become identifiers)
4. Compares current data against the previous state saved in `--output`
5. Prints changes grouped by **new** (+), **removed** (-), and **modified** (~)
6. Modified items show exactly which fields changed, with old → new values
7. Saves the current data as the new baseline for next time

jsonhound never mutates the source - it only reads from the URL and writes to your local state file.

## Tests

The test suite lives in `tests/` and runs with [pytest](https://docs.pytest.org), declared in the `dev` dependency group in `pyproject.toml`.

```bash
# Sync dependencies (the dev group, with pytest, is included by default)
uv sync

# Run the whole suite
uv run pytest
```

`uv run pytest` pulls in the `dev` group automatically, so no extra flags are needed. To run a single file:

```bash
uv run pytest tests/test_cli.py
```
