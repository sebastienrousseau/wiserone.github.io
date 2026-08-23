#!/usr/bin/env python3
"""Daily publishing helper for the quote of the day.

Dates no longer own quotes. `_data/quotes/quotes.json` is a pool, and
`build_posts.py` maps each date onto it by `ordinal % len(pool)`, so
the front page can never run dry — the failure that started all this,
where the site sat on 25 February 2024 for months.

That removes the old "runway" question and replaces it with a
different one: is the pool deep enough that a reader does not notice
the rotation? At 138 quotes a given line returns roughly every 4½
months, which is the number --check defends.

Usage:

    tools/publish_daily.py --check
        Report today's quote, the pool depth, and the rotation period.
        Exits non-zero if the pool is below --min-pool.

    tools/publish_daily.py --add "A new aphorism."
        Append a quote to the pool. Lengthens the rotation for every
        date at once; there is no date to choose.

Adding is deliberately manual. These lines are written, not generated:
a script that invented them unattended would fill the pool with filler,
which is the opposite of the point.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
POOL = ROOT / "_data" / "quotes" / "quotes.json"
IMAGE = "https://cloudcdn.pro/stocks/images/vitalis-hirschmann-4ErRQkRiOv4.webp"
AUTHOR = "The Wiser One"


def load() -> list[dict]:
    pool = json.loads(POOL.read_text())["quotes"]
    pool.sort(key=lambda q: q["id"])
    return pool


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def cmd_check(args: argparse.Namespace) -> int:
    pool = load()
    now = today()
    if not pool:
        print("ERROR: the pool is empty")
        return 1
    current = pool[now.toordinal() % len(pool)]

    print(f"  today            {now.isoformat()}")
    print(f"  today's quote    {current['quote_text']}")
    print(f"  pool             {len(pool)} quotes")
    print(f"  rotation         every {len(pool)} days "
          f"(~{len(pool) / 30.4:.1f} months)")
    print(f"  next repeat      "
          f"{(now + dt.timedelta(days=len(pool))).isoformat()}")

    if len(pool) < args.min_pool:
        print(f"\nERROR: pool is {len(pool)}, minimum {args.min_pool}. "
              "A rotation this short is visible to a returning reader. "
              "Add more with --add.")
        return 1
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    text = args.add.strip()
    if not text:
        print("ERROR: empty quote")
        return 1

    pool = load()
    if any(q["quote_text"].strip() == text for q in pool):
        print("ERROR: that quote already exists")
        return 1

    pool.append({
        "id": max((q["id"] for q in pool), default=-1) + 1,
        "quote_text": text,
        "author": AUTHOR,
        "date_added": f"{today().isoformat()}T06:06:06Z",
        "image_url": IMAGE,
    })
    POOL.write_text(json.dumps({"quotes": pool}, indent=2,
                               ensure_ascii=False) + "\n")
    print(f"  pool is now {len(pool)}")
    print(f"  {text}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report today's quote and pool depth")
    parser.add_argument("--add", metavar="TEXT", help="append a quote")
    parser.add_argument("--min-pool", type=int, default=120,
                        help="fail --check below this pool size (default 120)")
    args = parser.parse_args()

    if args.add:
        return cmd_add(args)
    if args.check:
        return cmd_check(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
