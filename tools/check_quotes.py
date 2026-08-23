#!/usr/bin/env python3
"""Quality gate for the quote corpus.

Bulk-written aphorisms fail in predictable ways: exact duplicates,
near-duplicates that differ by a word, one opening formula used
hundreds of times, and drift in length. This measures all four so the
corpus can be judged rather than vouched for.

It also refuses well-known quotations reproduced verbatim: everything
here is attributed to "The Wiser One", so a famous line copied in is
misattributed as well as someone else's to give.
"""

from __future__ import annotations

import glob
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Lines that are famous enough that publishing them under another name
# would be misattribution. Matched on a distinctive fragment.
KNOWN_QUOTATIONS = [
    "crazy enough to think they can change the world",
    "stay hungry, stay foolish",
    "real artists ship",
    "design is not just what it looks like",
    "your time is limited",
    "the only way to do great work",
    "simplicity is the ultimate sophistication",
    "think different",
    "connecting the dots",
    "put a dent in the universe",
]


def load() -> list[dict]:
    out: list[dict] = []
    for path in sorted(glob.glob(str(ROOT / "_data" / "quotes" / "*.json"))):
        out.extend(json.loads(pathlib.Path(path).read_text())["quotes"])
    return out


def words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def shingles(text: str, n: int = 4) -> set[tuple[str, ...]]:
    w = words(text)
    return {tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def main() -> int:
    quotes = load()
    texts = [q["quote_text"] for q in quotes]
    problems: list[str] = []

    # 1. exact duplicates
    dupes = [t for t, n in Counter(texts).items() if n > 1]
    for d in dupes:
        problems.append(f"duplicate: {d[:70]}")

    # 2. duplicate dates
    dates = [q["date_added"][:10] for q in quotes]
    for d, n in Counter(dates).items():
        if n > 1:
            problems.append(f"date used {n}×: {d}")

    # 3. near-duplicates: heavy 4-gram overlap between any two
    sh = [shingles(t) for t in texts]
    near = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if not sh[i] or not sh[j]:
                continue
            overlap = len(sh[i] & sh[j]) / min(len(sh[i]), len(sh[j]))
            if overlap >= 0.6:
                near += 1
                if near <= 5:
                    problems.append(
                        f"near-duplicate ({overlap:.0%}):\n"
                        f"    {texts[i][:64]}\n    {texts[j][:64]}"
                    )
    if near > 5:
        problems.append(f"...and {near - 5} more near-duplicate pairs")

    # 4. famous quotations reproduced verbatim
    for q in quotes:
        low = q["quote_text"].lower()
        for known in KNOWN_QUOTATIONS:
            if known in low:
                problems.append(
                    f"known quotation attributed to {q['author']}: "
                    f"{q['quote_text'][:70]}"
                )

    # 5. opening-formula concentration
    openers = Counter(" ".join(words(t)[:2]) for t in texts)
    worst, count = openers.most_common(1)[0] if openers else ("", 0)
    share = count / len(texts) if texts else 0

    lengths = [len(t) for t in texts]
    print(f"  quotes            {len(quotes)}")
    print(f"  distinct texts    {len(set(texts))}")
    print(f"  date range        {min(dates)} → {max(dates)}")
    print(f"  length            min {min(lengths)}, mean {sum(lengths)//len(lengths)}, max {max(lengths)}")
    print(f"  commonest opener  \"{worst}\" ×{count} ({share:.1%})")
    print(f"  near-dup pairs    {near}")

    if share > 0.06:
        problems.append(
            f"opening formula \"{worst}\" used in {share:.1%} of quotes "
            "(limit 6%) — the corpus reads as templated"
        )

    if problems:
        print(f"\nERROR: {len(problems)} problem(s):")
        for p in problems[:12]:
            print(f"  - {p}")
        return 1
    print("\n  corpus passes: no duplicates, no near-duplicates, no known quotations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
