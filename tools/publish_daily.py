#!/usr/bin/env python3
"""Daily publishing helper for the quote of the day.

The site shows the quote whose `date_added` falls on today's UTC date,
so publishing is really two questions: is there a quote for today, and
how many days remain before the corpus runs dry?

Usage:

    tools/publish_daily.py --check
        Report today's quote and the remaining runway. Exits non-zero if
        today has no quote, or if the runway is below --min-runway.

    tools/publish_daily.py --add "A new aphorism." [--date YYYY-MM-DD]
        Append a quote. Without --date it takes the first free date
        after the last one, so the queue extends rather than collides.

Adding is deliberately manual. These lines are written, not generated:
a script that invented them unattended would fill the archive with
filler, which is the opposite of the point.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUOTES = ROOT / "_data" / "quotes"
IMAGE = "https://cloudcdn.pro/stocks/images/vitalis-hirschmann-4ErRQkRiOv4.webp"
AUTHOR = "The Wiser One"


def files() -> list[pathlib.Path]:
    return [pathlib.Path(p) for p in sorted(glob.glob(str(QUOTES / "*.json")))]


def load() -> list[dict]:
    out: list[dict] = []
    for path in files():
        out.extend(json.loads(path.read_text())["quotes"])
    out.sort(key=lambda q: q["date_added"])
    return out


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def cmd_check(args: argparse.Namespace) -> int:
    quotes = load()
    by_date = {q["date_added"][:10]: q for q in quotes}
    now = today()
    current = by_date.get(now.isoformat())

    future = sorted(d for d in by_date if d > now.isoformat())
    runway = len(future)

    print(f"  today            {now.isoformat()}")
    if current:
        print(f"  today's quote    {current['quote_text']}")
    else:
        print("  today's quote    MISSING")
    print(f"  corpus           {len(quotes)} quotes")
    print(f"  runway           {runway} day(s) after today")

    failed = False
    if current is None:
        print("\nERROR: no quote for today; the front page would show a stale date.")
        failed = True
    if runway < args.min_runway:
        print(
            f"\nERROR: only {runway} day(s) of quotes remain "
            f"(minimum {args.min_runway}). Add more with --add."
        )
        failed = True
    return 1 if failed else 0


def cmd_add(args: argparse.Namespace) -> int:
    text = args.add.strip()
    if not text:
        print("ERROR: empty quote")
        return 1

    quotes = load()
    if any(q["quote_text"].strip() == text for q in quotes):
        print("ERROR: that quote already exists")
        return 1

    used = {q["date_added"][:10] for q in quotes}
    if args.date:
        target = dt.date.fromisoformat(args.date)
        if target.isoformat() in used:
            print(f"ERROR: {target.isoformat()} already has a quote")
            return 1
    else:
        last = max(dt.date.fromisoformat(d) for d in used)
        target = last + dt.timedelta(days=1)

    latest = files()[-1]
    data = json.loads(latest.read_text())
    data["quotes"].append({
        "quote_text": text,
        "author": AUTHOR,
        "date_added": f"{target.isoformat()}T06:06:06Z",
        "image_url": IMAGE,
    })
    data["quotes"].sort(key=lambda q: q["date_added"])
    latest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  added for {target.isoformat()} in {latest.name}")
    print(f"  {text}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report today's quote and runway")
    parser.add_argument("--add", metavar="TEXT", help="append a quote")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="date for --add")
    parser.add_argument("--min-runway", type=int, default=14,
                        help="fail --check below this many future days (default 14)")
    args = parser.parse_args()

    if args.add:
        return cmd_add(args)
    if args.check:
        return cmd_check(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
