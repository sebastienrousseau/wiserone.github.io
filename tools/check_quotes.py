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
    # The WWDC focus answer and the Stanford address are the two texts
    # this corpus is most likely to drift into paraphrasing, because
    # they are the clearest statements of the themes being written to.
    "saying no to the hundred other good ideas",
    "innovation is saying no to",
    "as proud of the things we haven't done",
    "focus means saying yes",
    "lightness of being a beginner again",
    "heaviness of being successful",
    "less sure about everything",
    "don't lose faith",
    "the only way to do great work is to love what you do",
    "have the courage to follow your heart",
    # His statement on this exact theme. Writing about simplicity-as-
    # difficulty without tripping into it needs the guard explicit.
    "simple can be harder than complex",
    "work hard to get your thinking clean",
    "get your thinking clean to make it simple",
    "simplicity is the ultimate",
    "it takes a lot of hard work to make something simple",
    # The Stanford commencement address. Writing mortality-as-clarifier
    # without echoing it requires these blocked explicitly.
    "remembering that i'll be dead soon",
    "remembering that i will be dead soon",
    "the single best invention of life",
    "death is very likely",
    "no reason not to follow your heart",
    "you are already naked",
    "the trap of thinking you have something to lose",
    "all external expectations, all pride",
    "these things just fall away in the face of death",
    "the most important tool i've ever encountered",
    "if today were the last day of my life",
]


# Phrases that mark modern management writing rather than the register
# being matched. Each was identified in editorial review of a batch that
# passed every numeric gate: "if you have ten priorities you have none"
# is a productivity-blog cliché, "adequate" is a word he never reached
# for, and defining "strategy" as a noun is consultant framing.
CORPORATE = [
    "priorities, you have none", "if everything is a priority",
    "adequate", "wish list", "strategy is", "actionable", "deliverable",
    "stakeholder", "bandwidth", "circle back", "best practice",
    "value-add", "synergy", "leverage the", "double down",
    "at the end of the day", "move the needle", "low-hanging fruit",
]


def load() -> list[dict]:
    out: list[dict] = []
    for path in sorted(glob.glob(str(ROOT / "_data" / "quotes" / "*.json"))):
        out.extend(json.loads(pathlib.Path(path).read_text())["quotes"])
    return out


def words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


# Function words survive paraphrase while content words change, so a
# skeleton of them exposes structural templating that vocabulary-based
# similarity misses entirely. Five lines built on
# "<negative> <verb> your <time>. <imperative> the <noun>, not the
# <noun>, and your <noun> will <positive>" share 5% of their 4-grams —
# invisible to the near-duplicate check — while being the same sentence
# wearing different words.
FUNCTION_WORDS = {
    "a", "an", "and", "as", "at", "be", "been", "but", "by", "for", "from",
    "in", "into", "is", "it", "its", "never", "no", "not", "of", "on",
    "only", "or", "our", "that", "the", "their", "them", "then", "they",
    "this", "to", "until", "up", "was", "what", "when", "which", "while",
    "who", "will", "with", "without", "you", "your", "yours",
}


def skeleton(text: str, keep: int = 12) -> tuple[str, ...]:
    """Function-word spine of a line, with content words masked."""
    out = []
    for w in words(text)[:keep]:
        out.append(w if w in FUNCTION_WORDS else "_")
    return tuple(out)


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

    # 4. structural templating: same skeleton, different vocabulary
    skeletons = Counter(skeleton(t) for t in texts)
    worst_skel, skel_count = skeletons.most_common(1)[0] if skeletons else ((), 0)
    skel_share = skel_count / len(texts) if texts else 0
    if skel_share > 0.03:
        problems.append(
            f"structural template used by {skel_share:.1%} of the corpus "
            f"(limit 3%): {' '.join(worst_skel)}"
        )

    # 5. management-speak that reads as a seminar rather than a person
    for q in quotes:
        low = q["quote_text"].lower()
        for phrase in CORPORATE:
            if phrase in low:
                problems.append(
                    f"management-speak ({phrase!r}): {q['quote_text'][:60]}")

    # 6. famous quotations reproduced verbatim
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
    print(f"  commonest skeleton {skel_share:.1%}  {' '.join(worst_skel[:9])}")

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
