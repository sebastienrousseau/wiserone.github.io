#!/usr/bin/env python3
"""Score the corpus against Steve Jobs' actual register.

Rebuilt. The previous version scored structural devices drawn from a
summary matrix — imperative openings, "never/not...but" markers,
concrete nouns, possessive density, a negative-to-positive word arc.
Assembled into a weighted checklist those describe a voice he does not
have. It rated

    "Never varnish a flaw; cut the joint your craft rejects."      9.5
    "Most people don't need a better idea. They need to stop
     asking permission for the one they already have."            2.9

which is backwards. The second is the one that sounds like him.

What the register actually is
-----------------------------
* Colloquial and direct. Contractions, common words, plain abstract
  nouns — permission, education, worry, attention — not literary ones.
* Active and forward-looking. Metaphors that move ("connecting the
  dots", "dent in the universe"), not ones that settle ("regret
  gathers").
* Mortality as a tool for clearing fear and pride, never as a lament
  for missed chances.
* Short declaratives. Statements, not commands; he rarely instructs.
* Second person, plainly used.

Every component below is falsifiable and printed. The validation that
matters is ordering: known-good lines must outrank known-bad ones, and
tools/validate_scorer.py asserts exactly that.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent

TOPICS = {
    "innovation": {"band": (6, 14), "target": 8.5,
        "lexicon": {"idea", "ideas", "design", "simple", "simplicity", "build",
                    "built", "make", "makes", "product", "products", "better",
                    "different", "new", "craft", "quality", "detail", "taste",
                    "invent", "innovation", "ship", "shipped"}},
    "life": {"band": (15, 35), "target": 9.8,
        "lexicon": {"life", "time", "die", "died", "death", "dead", "dying",
                    "heart", "love", "fear", "courage", "years", "year",
                    "day", "days", "live", "living", "yourself", "worry",
                    "worried", "pride", "regret", "beginner", "learn",
                    "learning", "curious", "curiosity", "intuition", "gut"}},
    "business": {"band": (20, 50), "target": 7.9,
        "lexicon": {"company", "team", "people", "hire", "hired", "customer",
                    "customers", "money", "market", "job", "work", "boss",
                    "manage", "managers", "employees", "business", "startup"}},
}

# ---------------------------------------------------------------- signals

CONTRACTIONS = re.compile(
    r"\b\w+'(?:t|s|re|ve|ll|d|m)\b|\bcan't\b|\bdon't\b|\bwon't\b", re.I)

# The thousand-odd words that carry ordinary speech. A line built from
# these sounds spoken; a line that reaches past them sounds written.
PLAIN = {
    "a","about","after","again","all","almost","already","also","always","am",
    "an","and","another","any","anyone","anything","are","around","as","ask",
    "asked","asking","at","away","back","bad","be","because","been","before",
    "begin","being","best","better","big","both","but","buy","by","call",
    "called","came","can","cannot","care","change","choose","come","could",
    "day","days","did","different","do","does","doing","done","down","each",
    "early","end","enough","even","ever","every","everything","far","fast",
    "few","find","first","for","found","from","get","gets","getting","give",
    "go","going","gone","good","got","great","had","half","hard","has","have",
    "he","hear","help","her","here","him","his","hold","home","hour","hours",
    "how","i","if","in","into","is","it","its","just","keep","kind","知","know",
    "last","late","later","learn","leave","left","less","let","life","like",
    "little","live","long","look","looking","lose","lot","made","make","makes",
    "making","man","many","matter","may","me","mean","might","mind","money",
    "more","most","much","must","my","never","new","next","no","nobody","not",
    "nothing","now","of","off","often","old","on","once","one","only","or",
    "other","our","out","over","own","part","people","person","put","real",
    "really","right","room","said","same","say","see","seen","set","she",
    "should","show","side","small","so","some","someone","something","soon",
    "start","started","still","stop","such","sure","take","talk","tell","than",
    "that","the","their","them","then","there","these","they","thing","things",
    "think","this","those","though","thought","time","times","to","today",
    "together","too","took","turn","two","under","until","up","us","use","used",
    "very","want","wanted","was","way","we","week","well","went","were","what",
    "when","where","which","while","who","whole","why","will","with","without",
    "work","worked","working","world","would","year","years","yes","yet","you",
    "your","yourself",
}

# Verbs and nouns that mark writing rather than speech.
LITERARY = {
    "gathers","gather","beckons","outlasts","outlast","endures","endure",
    "abides","dwells","lingers","laments","yearns","aspires","transcends",
    "illuminates","kindles","forges","tempers","hews","carves","adorns",
    "bestows","imparts","engenders","begets","wanes","waxes","ebbs",
    "whispers","murmurs","echoes","resonates","permeates","suffuses",
    "myriad","manifold","sublime","ephemeral","eternal","infinite","profound",
    "profundity","essence","virtue","folly","yonder","thence","whence",
    "hitherto","henceforth","therein","wherein","albeit","whilst","amongst",
    "unto","doth","seldom","oft","ere","betwixt",
}

# Forward motion. He points at what you do next, not what was lost.
FORWARD = {
    "will","going","next","now","today","tomorrow","ahead","forward","start",
    "starting","begin","beginning","become","becomes","get","getting","make",
    "making","build","building","go","take","move","moving","keep","change",
    "learn","learning","try","do","ship","choose","find","reach","grow",
}

BACKWARD = {
    "regret","regrets","regretted","missed","lost","wasted","should've",
    "shouldve","mourn","mourning","nostalgia","yesterday","once","former",
    "past","gone","never opened","too late","if only",
}

# Mortality used to clear fear and pride, which is his actual move.
MORTALITY = {"die","died","death","dead","dying","mortal","grave","buried",
             "alive","short","limited","finite","end","ends","ending","time"}
CLEARING = {"fear","pride","worry","worries","embarrassment","expectation",
            "expectations","opinion","opinions","failure","shame","ego"}

BINARY = [
    r"\byou can'?t\b[^.]*\byou can only\b", r"\bnot\b[^.]*\bbut\b",
    r"\binstead of\b", r"\brather than\b", r"\beither\b[^.]*\bor\b",
    r"\bthe (?:only|best) way\b", r"\bmore\b[^.]*\bthan\b",
    r"\bit'?s not\b[^.]*\bit'?s\b", r"\bdon'?t\b[^.]*\bdo\b",
    r"\bstop\b[^.]*\bstart\b", r"\bless\b[^.]*\bmore\b",
]

PASSIVE = re.compile(
    r"\b(?:is|are|was|were|been|being|be)\s+\w+(?:ed|en)\b(?:\s+by\b)?", re.I)

JARGON = {"software","hardware","api","sdk","database","server","cloud",
          "codebase","deploy","backend","frontend","kpi","roi","agile",
          "sprint","stakeholder","synergy","leverage","paradigm","backlog"}

WEIGHTS = {
    "colloquial":   2.0,   # contractions and common words — the core signal
    "plain_words":  2.0,   # absence of literary vocabulary
    "direct":       1.2,   # second person, plainly used
    "active":       1.2,   # active voice
    "forward":      1.8,   # points at what you do next
    "declarative":  1.0,   # statements, short sentences
    "binary":       1.3,   # plain either/or framing
    "universal":    1.0,   # no jargon
    "length_fit":   1.0,   # inside the topic's band
    "stakes":       0.5,   # mortality used to clear fear (bonus, not required)
}


def words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


UBIQUITOUS = {"you", "your", "yours", "yourself", "we", "our", "us", "thing",
              "things", "way", "people"}


def classify(text: str) -> str:
    w = set(words(text)) - UBIQUITOUS
    scores = {n: len(w & s["lexicon"]) / (len(w) ** 0.5 or 1)
              for n, s in TOPICS.items()}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        return best
    n = len(words(text))
    return "innovation" if n <= 14 else ("life" if n <= 38 else "business")


def score_one(text: str) -> tuple[float, str, dict[str, float]]:
    w = words(text)
    n = len(w)
    topic = classify(text)
    lo, hi = TOPICS[topic]["band"]
    sentences = [s.strip() for s in re.split(r"[.;!?]", text) if s.strip()]
    p: dict[str, float] = {}

    # colloquial: contractions plus a high share of everyday words
    contractions = len(CONTRACTIONS.findall(text))
    plain_share = sum(1 for x in w if x in PLAIN) / max(1, n)
    p["colloquial"] = min(1.0, (0.6 if contractions else 0.0)
                          + max(0.0, (plain_share - 0.55) / 0.30))

    # plain words: literary vocabulary is disqualifying, not merely costly
    literary = sum(1 for x in w if x in LITERARY)
    p["plain_words"] = 0.0 if literary else 1.0

    p["direct"] = 1.0 if {"you", "your", "yourself", "you're", "you'll",
                          "you've", "you'd"} & set(w) else 0.3

    passives = len(PASSIVE.findall(text))
    p["active"] = 1.0 if passives == 0 else max(0.0, 1 - passives * 0.5)

    fwd = len(set(w) & FORWARD)
    back = len(set(w) & BACKWARD) + (1 if any(b in text.lower() for b in
                                              ("never opened", "if only", "too late")) else 0)
    p["forward"] = max(0.0, min(1.0, 0.35 + 0.35 * fwd - 0.55 * back))

    avg_sentence = n / max(1, len(sentences))
    p["declarative"] = 1.0 if avg_sentence <= 16 else max(0.0, 1 - (avg_sentence - 16) / 12)

    p["binary"] = 1.0 if any(re.search(b, text.lower()) for b in BINARY) else 0.45

    p["universal"] = 0.0 if set(w) & JARGON else 1.0

    if lo <= n <= hi:
        p["length_fit"] = 1.0
    else:
        d = (lo - n) if n < lo else (n - hi)
        p["length_fit"] = max(0.0, 1.0 - d / 10)

    p["stakes"] = 1.0 if (set(w) & MORTALITY and set(w) & CLEARING) else 0.5

    total = sum(p[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(10 * total / sum(WEIGHTS.values()), 2), topic, p


def load() -> list[dict]:
    out: list[dict] = []
    for path in sorted(glob.glob(str(ROOT / "_data" / "quotes" / "*.json"))):
        out.extend(json.loads(pathlib.Path(path).read_text())["quotes"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--worst", type=int, default=0)
    ap.add_argument("--min-mean", type=float, default=0.0)
    ap.add_argument("--min-quote", type=float, default=0.0)
    ap.add_argument("--min-today", type=float, default=0.0)
    ap.add_argument("--json", metavar="FILE")
    args = ap.parse_args()

    quotes = load()
    rows = [{"date": q["date_added"][:10], "text": q["quote_text"],
             **dict(zip(("score", "topic", "parts"), score_one(q["quote_text"]))),
             "words": len(words(q["quote_text"]))} for q in quotes]

    overall = [r["score"] for r in rows]
    by_topic: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_topic[r["topic"]].append(r["score"])

    print(f"  corpus            {len(rows)} quotes")
    print(f"  mean score        {statistics.mean(overall):.2f} / 10")
    print(f"  median            {statistics.median(overall):.2f}")
    print(f"  at or above 9.0   {sum(1 for s in overall if s >= 9.0)}")
    print()
    print(f"  {'topic':<12}{'n':>6}{'mean':>8}{'target':>8}{'words':>8}")
    for name in TOPICS:
        v = by_topic.get(name, [])
        if v:
            wc = statistics.mean(r["words"] for r in rows if r["topic"] == name)
            print(f"  {name:<12}{len(v):>6}{statistics.mean(v):>8.2f}"
                  f"{TOPICS[name]['target']:>8.1f}{wc:>8.1f}")

    print("\n  component means (0-1, weight in brackets)")
    for k in WEIGHTS:
        print(f"    {k:<13} {statistics.mean(r['parts'][k] for r in rows):.2f}   [{WEIGHTS[k]}]")

    if args.worst:
        print(f"\n  {args.worst} lowest-scoring")
        for r in sorted(rows, key=lambda r: r["score"])[:args.worst]:
            print(f"    {r['score']:>5}  {r['text'][:66]}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, indent=2) + "\n")

    failed = False
    mean = statistics.mean(overall)
    if args.min_mean and mean < args.min_mean:
        print(f"\nERROR: corpus mean {mean:.2f} below floor {args.min_mean}")
        failed = True
    if args.min_quote:
        weak = [r for r in rows if r["score"] < args.min_quote]
        if weak:
            print(f"\nERROR: {len(weak)} quote(s) below {args.min_quote}")
            for r in sorted(weak, key=lambda r: r["score"])[:8]:
                print(f"  {r['score']:>5}  {r['text'][:62]}")
            failed = True
    if args.min_today:
        import datetime as _dt
        today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
        mine = [r for r in rows if r["date"] == today]
        if not mine:
            print(f"\nERROR: no quote dated {today}")
            failed = True
        elif mine[0]["score"] < args.min_today:
            print(f"\nERROR: today's quote scores {mine[0]['score']}, floor {args.min_today}")
            failed = True
        else:
            print(f"\n  today's quote scores {mine[0]['score']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
