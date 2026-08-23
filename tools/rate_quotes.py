#!/usr/bin/env python3
"""Score the corpus against the documented Steve Jobs structural profile.

What this measures, and what it does not
----------------------------------------
It measures *structural conformance* to the published profile of Jobs'
rhetoric: length bands per topic, imperative and axiomatic phrasing,
possessive density, oppositional contrast, concrete grounding, absence
of domain jargon, hedging, and the negative-constraint-into-positive-
resolution arc.

It does not measure whether a line is good. No script does. Treat the
score as a falsifiable proxy: every component is visible, weighted
openly, and can be recomputed. A quote can score 9 and still be flat.

Calibration targets come from the structural matrix, not from a stored
corpus of Jobs quotations — republishing copyrighted lines as a test
fixture is avoidable, and the matrix is the actual specification:

    Innovation & Design    6–12 words   target 8.5
    Life & Motivation     15–35 words   target 9.8
    Business & Startups   20–50 words   target 7.9
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
    "innovation": {
        "band": (6, 12), "target": 8.5,
        "lexicon": {"design", "simplicity", "simple", "craft", "build", "make",
                    "innovation", "innovate", "idea", "ideas", "invention",
                    "abstraction", "system", "product", "prototype", "elegant",
                    "complexity", "detail", "details", "quality", "taste"},
    },
    "life": {
        "band": (15, 35), "target": 9.8,
        "lexicon": {"time", "life", "heart", "courage", "fear", "doubt",
                    "curiosity", "learning", "learn", "growth", "grow",
                    "attention", "meaning", "patience", "regret", "yourself",
                    "your", "you", "care", "humility", "purpose"},
    },
    "business": {
        "band": (20, 50), "target": 7.9,
        "lexicon": {"team", "teams", "customer", "market", "decision",
                    "decisions", "process", "priority", "priorities", "plan",
                    "deadline", "trust", "leadership", "ownership", "standard",
                    "standards", "hire", "manage", "scope", "estimate",
                    "stakeholder", "reputation", "incentive", "incentives"},
    },
}

# Detection notes
# ---------------
# An earlier version of this scorer checked only the first word for an
# imperative, matched contrast against a dozen fixed phrases, and used a
# 24-word sentiment list. Well-formed lines scored 6.5 while losing
# points on components that were really measuring the narrowness of
# those lists. Optimising the corpus against that would have been
# writing to please a regex. The lexicons below are broader and the
# structural checks look across sentences, not just at position zero.

IMPERATIVES = {
    "ask", "build", "give", "take", "refuse", "choose", "prefer", "watch",
    "understand", "learn", "judge", "measure", "guard", "design", "ship",
    "start", "stop", "say", "do", "make", "keep", "find", "notice", "begin",
    "accept", "question", "trust", "reduce", "remove", "protect", "write",
    "speak", "listen", "focus", "structure", "optimise", "optimize", "hire",
    "iterate", "sharpen", "delegate", "set", "show", "fix", "avoid", "treat",
}

IMPERATIVES |= {
    "consider", "decide", "define", "deliver", "demand", "earn", "expect",
    "explain", "forget", "hold", "invest", "leave", "look", "name", "offer",
    "own", "pick", "practise", "practice", "prove", "read", "remember",
    "replace", "resist", "respect", "return", "seek", "sell", "solve",
    "spend", "study", "teach", "test", "think", "throw", "try", "use",
    "wait", "walk", "want", "work", "write", "cut", "draw", "drop", "face",
    "finish", "follow", "get", "go", "grow", "help", "know", "lead", "let",
    "live", "love", "move", "put", "raise", "run", "see", "serve", "share",
    "step", "take", "tell", "turn",
}

POSSESSIVE = {"your", "yours", "you", "our", "ours", "we", "my", "mine", "us",
              "yourself", "ourselves", "themselves", "their", "his", "her"}

CONTRAST = [
    # explicit antithesis
    r"\bnot\b[^.]*\bbut\b", r"\bis not\b[^.]*\bit is\b",
    r"\brather than\b", r"\binstead of\b", r"\bnot\b[^.]*[.;] *it is\b",
    # comparatives
    r"\bmore\b[^.]*\bthan\b", r"\bbetter\b[^.]*\bthan\b",
    r"\bless\b[^.]*\bthan\b", r"\bfaster\b[^.]*\bthan\b",
    r"\boutlasts?\b", r"\boutruns?\b", r"\boutranks?\b", r"\bbeats\b",
    r"\bcosts more\b", r"\bworth more\b",
    # oppositional / limiting
    r"\bversus\b", r"\bwhereas\b", r"\bwhile\b", r"\bnever\b",
    r"\bonly\b", r"\bwithout\b", r"\bexcept\b", r"\bunless\b",
    r"\byet\b", r"\bstill\b", r"\bhowever\b", r"\bbut\b",
    r"\beither\b[^.]*\bor\b", r"\bchoose between\b",
    # negation followed by affirmation in the next sentence
    r"\b(no|not|nothing|nobody|never)\b[^.]*\.[^.]*\b(it is|they are|that is)\b",
    # em-dash and colon antithesis
    r"—", r"\b\w+: [a-z]",
]

CONCRETE = {
    "door", "doors", "wall", "walls", "road", "roads", "hand", "hands",
    "tool", "tools", "room", "rooms", "floor", "ceiling", "foundation",
    "bridge", "corridor", "seam", "seams", "edge", "edges", "material",
    "rubble", "museum", "engine", "instrument", "map", "maps", "calendar",
    "clock", "hour", "hours", "morning", "mornings", "week", "weeks",
    "midnight", "bar", "yardstick", "guardrail", "net", "line", "lines",
    "wire", "brick", "bricks", "stone", "table", "chair", "window",
    "garden", "seed", "roots", "river", "mountain", "path", "step", "steps",
    "ladder", "rope", "knife", "hammer", "nail", "carpenter", "cabinet",
    "drawer", "fence", "gate", "key", "lock", "lamp", "candle", "mirror",
    "compass", "anchor", "sail", "harbour", "harbor", "machine", "gear",
    "lever", "switch", "thread", "cloth", "paper", "ink", "page", "shelf",
}

JARGON = {
    "software", "hardware", "api", "sdk", "database", "server", "cloud",
    "kubernetes", "javascript", "python", "rust", "compiler", "repository",
    "commit", "deploy", "microservice", "backend", "frontend", "devops",
    "startup", "saas", "kpi", "roi", "agile", "scrum", "sprint",
}

# Universal relatability is not merely the absence of "software". A line
# built from "backlog", "stakeholder" and "sprint" is just as narrow: it
# addresses a job rather than a person. The high-scoring register trades
# domain nouns for shared human resources — time, fear, work, years,
# attention — which is why those lines survive outside the industry that
# produced them.
UNIVERSAL_NOUNS = {
    "time", "years", "year", "day", "days", "hour", "hours", "life",
    "heart", "mind", "hand", "hands", "voice", "fear", "courage", "doubt",
    "hope", "regret", "patience", "attention", "curiosity", "passion",
    "intuition", "instinct", "work", "people", "person", "someone",
    "everyone", "nobody", "children", "friend", "friends", "stranger",
    "strangers", "morning", "night", "week", "future", "past", "memory",
    "story", "road", "path", "door", "hunger", "taste", "care", "trust",
    "truth", "meaning", "purpose", "self", "you", "your", "yourself",
}

DOMAIN_NOUNS = {
    "backlog", "stakeholder", "stakeholders", "sprint", "roadmap",
    "deploy", "deployment", "release", "ticket", "tickets", "standup",
    "retrospective", "velocity", "burndown", "kpi", "okr", "metric",
    "metrics", "dashboard", "pipeline", "workflow", "process", "processes",
    "review", "reviews", "reviewer", "estimate", "estimates", "estimation",
    "scope", "requirement", "requirements", "specification", "abstraction",
    "architecture", "refactor", "codebase", "commit", "merge", "branch",
    "feature", "features", "bug", "bugs", "test", "tests", "testing",
    "config", "configuration", "dependency", "dependencies", "system",
    "systems", "product", "roadmaps", "onboarding", "handover",
}

HEDGES = {"maybe", "perhaps", "somewhat", "possibly", "arguably", "fairly",
          "rather quite", "sort of", "kind of", "probably", "usually might"}

NEGATIVE_OPENERS = {
    "no", "not", "never", "nothing", "nobody", "none", "without", "fear",
    "afraid", "doubt", "failure", "fail", "fails", "failed", "cannot",
    "refuse", "stop", "avoid", "beware", "rarely", "few", "hard", "harder",
    "hardest", "difficult", "pain", "painful", "cost", "costs", "expensive",
    "short", "limited", "scarce", "spent", "waste", "wasted", "lost", "lose",
    "wrong", "mistake", "mistakes", "risk", "risks", "danger", "fragile",
    "broken", "break", "breaks", "debt", "burden", "tired", "late", "delay",
    "confusion", "confused", "unclear", "ambiguity", "uncertain", "regret",
    "ignore", "ignored", "forget", "forgotten", "weak", "weakness", "problem",
    "problems", "obstacle", "constraint", "pressure", "crisis", "worse",
}

POSITIVE_RESOLVERS = {
    "trust", "trusted", "clarity", "clear", "growth", "grow", "value",
    "worth", "meaning", "freedom", "free", "possible", "easier", "easy",
    "better", "best", "durable", "lasting", "lasts", "advantage", "strength",
    "strong", "stronger", "confidence", "confident", "excellence", "craft",
    "quality", "progress", "learn", "learning", "learned", "wisdom",
    "respect", "care", "life", "gift", "joy", "delight", "beauty",
    "beautiful", "elegant", "mastery", "master", "skill", "reward",
    "rewards", "win", "wins", "succeed", "success", "achieve", "build",
    "built", "create", "creates", "make", "makes", "opens", "unlock",
    "matters", "useful", "honest", "generous", "kind", "courage",
    "brave", "hope", "future", "forward", "compound", "compounds",
}

WEIGHTS = {
    "length_fit": 1.6,
    "punchiness": 1.2,
    "imperative": 1.3,
    "possessive": 0.9,
    "contrast": 1.6,
    "concrete": 0.9,
    "universal": 1.8,
    "no_hedge": 0.7,
    "valence_arc": 2.0,
    "single_clause": 1.2,
}


def words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def classify(text: str) -> str:
    w = set(words(text))
    scores = {
        name: len(w & spec["lexicon"]) / (len(w) ** 0.5 or 1)
        for name, spec in TOPICS.items()
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "life"


def score_one(text: str) -> tuple[float, str, dict[str, float]]:
    w = words(text)
    n = len(w)
    topic = classify(text)
    lo, hi = TOPICS[topic]["band"]
    parts: dict[str, float] = {}

    # inside the band scores 1; outside decays with distance
    if lo <= n <= hi:
        parts["length_fit"] = 1.0
    else:
        d = (lo - n) if n < lo else (n - hi)
        parts["length_fit"] = max(0.0, 1.0 - d / 12)

    # Jobs' distribution is bimodal: punchy soundbite or full narrative.
    parts["punchiness"] = 1.0 if (n <= 10 or n >= 25) else max(0.0, 1 - (min(n - 10, 25 - n) / 8))

    sentences = [s.strip() for s in re.split(r"[.;!?]", text) if s.strip()]
    starts = [words(s)[0] for s in sentences if words(s)]
    parts["imperative"] = 1.0 if any(s in IMPERATIVES for s in starts) else 0.0
    poss = sum(1 for x in w if x in POSSESSIVE)
    parts["possessive"] = min(1.0, poss / max(1, n * 0.08))
    parts["contrast"] = 1.0 if any(re.search(p, text.lower()) for p in CONTRAST) else 0.0
    parts["concrete"] = min(1.0, sum(1 for x in w if x in CONCRETE) / 2 + 
                            (0.5 if any(x in CONCRETE for x in w) else 0.0))
    # jargon is disqualifying; beyond that, reward human nouns and
    # penalise workplace-domain ones
    if set(w) & JARGON:
        parts["universal"] = 0.0
    else:
        human = len(set(w) & UNIVERSAL_NOUNS)
        domain = len(set(w) & DOMAIN_NOUNS)
        parts["universal"] = max(0.0, min(1.0, 0.35 + 0.35 * human - 0.30 * domain))
    parts["no_hedge"] = 0.0 if any(h in text.lower() for h in HEDGES) else 1.0

    # The signature movement: open on a constraint or warning, resolve
    # into a positive call to action. Measured over the opening and
    # closing thirds so a long line is not judged by its midpoint, and
    # a closing imperative counts as the call to action.
    third = max(1, n // 3)
    head, tail = set(w[:third]), set(w[-third:])
    opens_negative = bool(head & NEGATIVE_OPENERS)
    ends_positive = bool(tail & POSITIVE_RESOLVERS)
    ends_imperative = bool(starts and starts[-1] in IMPERATIVES) if n > 12 else False
    if opens_negative and (ends_positive or ends_imperative):
        parts["valence_arc"] = 1.0
    elif opens_negative or ends_positive or ends_imperative:
        parts["valence_arc"] = 0.45
    else:
        parts["valence_arc"] = 0.0

    # Short lines should be single-clause; longer narrative lines are
    # expected to carry two or three sentences, as his commencement
    # passages do. Penalising commas there measured the wrong thing.
    if n <= 12:
        parts["single_clause"] = 1.0 if text.count(",") <= 1 else 0.5
    else:
        parts["single_clause"] = 1.0 if len(sentences) >= 2 else 0.6

    total = sum(parts[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(10 * total / sum(WEIGHTS.values()), 2), topic, parts


def load() -> list[dict]:
    out: list[dict] = []
    for path in sorted(glob.glob(str(ROOT / "_data" / "quotes" / "*.json"))):
        out.extend(json.loads(pathlib.Path(path).read_text())["quotes"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--worst", type=int, default=0, help="list the N lowest-scoring quotes")
    ap.add_argument("--min-mean", type=float, default=0.0,
                    help="fail if the corpus mean falls below this")
    ap.add_argument("--json", metavar="FILE", help="write per-quote scores")
    ap.add_argument("--min-quote", type=float, default=0.0,
                    help="fail if any single quote scores below this")
    ap.add_argument("--min-today", type=float, default=0.0,
                    help="fail if today's quote (the front page) scores below this")
    args = ap.parse_args()

    quotes = load()
    rows = []
    for q in quotes:
        s, topic, parts = score_one(q["quote_text"])
        rows.append({"date": q["date_added"][:10], "text": q["quote_text"],
                     "score": s, "topic": topic, "parts": parts,
                     "words": len(words(q["quote_text"]))})

    by_topic: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_topic[r["topic"]].append(r["score"])
    overall = [r["score"] for r in rows]

    print(f"  corpus            {len(rows)} quotes")
    print(f"  mean score        {statistics.mean(overall):.2f} / 10")
    print(f"  median            {statistics.median(overall):.2f}")
    print(f"  std dev           {statistics.pstdev(overall):.2f}")
    print()
    print(f"  {'topic':<12}{'n':>6}{'mean':>8}{'target':>8}{'gap':>8}{'words':>8}")
    for name in TOPICS:
        vals = by_topic.get(name, [])
        if not vals:
            continue
        wcount = statistics.mean(r["words"] for r in rows if r["topic"] == name)
        m = statistics.mean(vals)
        t = TOPICS[name]["target"]
        print(f"  {name:<12}{len(vals):>6}{m:>8.2f}{t:>8.1f}{m - t:>+8.2f}{wcount:>8.1f}")

    print("\n  score distribution")
    buckets = Counter(min(9, int(s)) for s in overall)
    for b in sorted(buckets):
        bar = "█" * max(1, round(40 * buckets[b] / len(overall)))
        print(f"    {b}–{b+1}  {buckets[b]:>5}  {bar}")

    print("\n  component means (0–1, weight in brackets)")
    for k in WEIGHTS:
        mean = statistics.mean(r["parts"][k] for r in rows)
        print(f"    {k:<14} {mean:.2f}   [{WEIGHTS[k]}]")

    if args.worst:
        print(f"\n  {args.worst} lowest-scoring")
        for r in sorted(rows, key=lambda r: r["score"])[:args.worst]:
            print(f"    {r['score']:>5}  {r['date']}  {r['text'][:66]}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, indent=2) + "\n")
        print(f"\n  per-quote scores written to {args.json}")

    failed = False
    mean = statistics.mean(overall)
    if args.min_mean and mean < args.min_mean:
        print(f"\nERROR: corpus mean {mean:.2f} is below the floor {args.min_mean}")
        failed = True

    if args.min_quote:
        weak = [r for r in rows if r["score"] < args.min_quote]
        if weak:
            print(f"\nERROR: {len(weak)} quote(s) below the per-quote floor "
                  f"{args.min_quote}:")
            for r in sorted(weak, key=lambda r: r["score"])[:8]:
                print(f"  {r['score']:>5}  {r['date']}  {r['text'][:62]}")
            failed = True

    if args.min_today:
        import datetime as _dt
        today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
        mine = [r for r in rows if r["date"] == today]
        if not mine:
            print(f"\nERROR: no quote dated {today} to score")
            failed = True
        elif mine[0]["score"] < args.min_today:
            print(f"\nERROR: today's quote scores {mine[0]['score']}, "
                  f"below the front-page floor {args.min_today}")
            print(f"  {mine[0]['text']}")
            failed = True
        else:
            print(f"\n  today's quote scores {mine[0]['score']} "
                  f"(front-page floor {args.min_today})")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
