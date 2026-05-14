"""Keep the first N people from an evaluation_run.v1 (for faster ``cursor agent`` smoke tests)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("-n", "--people", type=int, default=1, help="Number of people rows to keep from the start (default 1)")
    args = p.parse_args()
    if args.people < 1:
        print("--people must be >= 1", file=sys.stderr)
        return 1
    d = json.loads(args.input.read_text(encoding="utf-8"))
    people = d.get("people")
    if not isinstance(people, list) or not people:
        print("input.people must be a non-empty list", file=sys.stderr)
        return 1
    d["people"] = people[: args.people]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} people={len(d['people'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
