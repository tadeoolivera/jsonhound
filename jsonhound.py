import httpx2
import json
import argparse
import sys
import time
from pathlib import Path


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def color(text, code):
    return f"{code}{text}{RESET}"


def fmt(val):
    s = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
    if len(s) > 80:
        s = s[:77] + "..."
    return s


def field_diff(old, new):
    all_keys = set(old.keys()) | set(new.keys())
    for key in sorted(all_keys, key=str):
        if key not in old:
            yield (key, None, new[key])
        elif key not in new:
            yield (key, old[key], None)
        elif old[key] != new[key]:
            yield (key, old[key], new[key])


def main():
    parser = argparse.ArgumentParser(
        description="Track changes in JSON data from an HTTP endpoint."
    )
    parser.add_argument("url", help="URL to fetch JSON from")
    parser.add_argument("-o", "--output", default="saved.json",
                        help="Path to the saved state file (default: saved.json)")
    parser.add_argument("-k", "--key", default="id",
                        help="Field used as unique identifier (default: id)")
    parser.add_argument("-d", "--display", nargs="+",
                        help="Field(s) to show in reports (default: the key field)")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="HTTP timeout in seconds (default: 10.0)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")

    args = parser.parse_args()

    if args.no_color:
        globals()["GREEN"] = globals()["RED"] = globals()["YELLOW"] = ""
        globals()["CYAN"] = globals()["BOLD"] = globals()["DIM"] = ""
        globals()["RESET"] = ""

    disp_fields = args.display or [args.key]

    sys.stderr.write(f"Fetching {args.url} ... ")
    sys.stderr.flush()
    t0 = time.time()
    try:
        res = httpx2.get(args.url, timeout=args.timeout)
        res.raise_for_status()
        raw = res.json()
    except Exception as e:
        sys.stderr.write("\n")
        print(f"{color('Error', RED)} fetching/parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    elapsed = time.time() - t0
    sys.stderr.write(f"done ({elapsed:.2f}s)\n")
    sys.stderr.flush()

    if isinstance(raw, list):
        try:
            current = {str(obj[args.key]): obj for obj in raw}
        except KeyError:
            print(f"{color('Error', RED)} key '{args.key}' not found in list items", file=sys.stderr)
            sys.exit(1)
    elif isinstance(raw, dict):
        current = raw
    else:
        print(f"{color('Error', RED)} JSON root must be a list or dict", file=sys.stderr)
        sys.exit(1)

    saved_path = Path(args.output)
    if saved_path.exists():
        try:
            prev = json.loads(saved_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"{color('Error', RED)} reading saved state: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        prev = {}

    prev_ids = set(prev.keys())
    cur_ids = set(current.keys())

    new_ids = cur_ids - prev_ids
    removed_ids = prev_ids - cur_ids
    modified_ids = [i for i in (cur_ids & prev_ids) if prev[i] != current[i]]

    if not prev:
        print(f"\n{color('First run', CYAN)} (saved initial state).")
    elif not (new_ids or removed_ids or modified_ids):
        print(f"\n{color('No changes', GREEN)} - {len(current)} item(s) up to date.")
    else:
        if new_ids:
            print(f"\n{color('+' + str(len(new_ids)), GREEN)} new:")
            for i in sorted(new_ids, key=str):
                info = " | ".join(str(current[i].get(f, "")) for f in disp_fields)
                print(f"    {info}")

        if removed_ids:
            print(f"\n{color('-' + str(len(removed_ids)), RED)} removed:")
            for i in sorted(removed_ids, key=str):
                info = " | ".join(str(prev[i].get(f, "")) for f in disp_fields)
                print(f"    {info}")

        if modified_ids:
            print(f"\n{color('~' + str(len(modified_ids)), YELLOW)} modified:")
            for i in sorted(modified_ids, key=str):
                label = " | ".join(str(current[i].get(f, "")) for f in disp_fields)
                print(f"    {label}")
                for field, old_val, new_val in field_diff(prev[i], current[i]):
                    if old_val is None:
                        print(f"       + {field}: {color(fmt(new_val), GREEN)}")
                    elif new_val is None:
                        print(f"       - {field}: {color(fmt(old_val), RED)}")
                    else:
                        print(f"       ~ {field}: {color(fmt(old_val), RED)} → {color(fmt(new_val), GREEN)}")

    try:
        saved_path.write_text(
            json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        n_new, n_rem, n_mod = len(new_ids), len(removed_ids), len(modified_ids)
        tags = []
        if n_new: tags.append(f"+{n_new}")
        if n_rem: tags.append(f"-{n_rem}")
        if n_mod: tags.append(f"~{n_mod}")
        tag_str = f"{DIM}[{', '.join(tags)}]{RESET} " if tags else ""
        print(f"\n{color('Saved', GREEN)} {len(current)} item(s) to {args.output}  {tag_str}{DIM}({elapsed:.2f}s){RESET}")
    except Exception as e:
        print(f"{color('Error', RED)} saving state: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{color('Interrupted', YELLOW)}")
        sys.exit(130)
