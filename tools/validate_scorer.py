#!/usr/bin/env python3
"""Assert the scorer ranks known-good above known-bad.

A rubric that is internally consistent can still be externally wrong.
The previous one was: it scored carpentry pastiche 9.5 and plain
colloquial writing 2.9. Ordering is the only validation that catches
that, so it runs as a gate rather than living in a commit message.

GOOD lines are in the register being matched — colloquial, forward,
declarative. BAD lines are the two failure modes already produced and
rejected: workshop imagery, and literary/backward-looking phrasing.
"""
from __future__ import annotations
import pathlib, statistics, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rate_quotes import score_one

GOOD = [
 "Getting told no is the cheapest education you'll ever get. It costs an afternoon and it saves you a year.",
 "You can't plan a career forwards. You can only look back and see why the detours mattered, so take the interesting one now.",
 "Most people don't need a better idea. They need to stop asking permission for the one they already have.",
 "You're going to be dead soon enough. That's not depressing, it's clarifying — it makes almost every worry look small.",
 "Being a beginner again is lighter than being an expert. You stop defending and start learning, and the work gets better fast.",
 "If you're the smartest person in the room, you picked the wrong room. Go find the one where you're behind.",
 "Say no to a hundred good things. That's the only way the great thing gets your whole attention.",
 "Your work is going to fill a huge part of your life. Do something you'd still respect if nobody ever paid you for it.",
]
BAD = [
 "Never varnish a flaw; cut the joint your craft rejects.",
 "Never square the frame; cut the beam your floor deserves.",
 "Only the post your spade sank will outlast the coming storm.",
 "Regret gathers at the door you never opened, never at the one that closed.",
 "Fear polishes the handle, never the hinge your door deserves.",
 "Waste sleeps in the yard, never the field your plough opened.",
]

def main() -> int:
    g = [(score_one(t)[0], t) for t in GOOD]
    b = [(score_one(t)[0], t) for t in BAD]
    gm, bm = statistics.mean(s for s, _ in g), statistics.mean(s for s, _ in b)
    print(f"  register being matched   mean {gm:.2f}   min {min(s for s,_ in g):.2f}")
    print(f"  rejected pastiche        mean {bm:.2f}   max {max(s for s,_ in b):.2f}")
    print()
    for s, t in sorted(g, reverse=True)[:3]:
        print(f"    good {s:>5}  {t[:64]}")
    for s, t in sorted(b, reverse=True)[:3]:
        print(f"    bad  {s:>5}  {t[:64]}")

    problems = []
    if gm <= bm:
        problems.append(f"good mean {gm:.2f} does not exceed bad mean {bm:.2f}")
    if min(s for s, _ in g) <= max(s for s, _ in b):
        problems.append("the ranges overlap: some pastiche outranks some good writing")
    if problems:
        print("\nERROR: the scorer does not order these correctly:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\n  ordering holds: every good line outranks every rejected one")
    return 0

if __name__ == "__main__":
    sys.exit(main())
