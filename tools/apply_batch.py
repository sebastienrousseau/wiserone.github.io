#!/usr/bin/env python3
"""Replace the lowest-scoring quotes with lines supplied on stdin.

One quote per line. Dates are preserved: the weakest existing quote
keeps its slot and gets new words, so the archive stays continuous.

Reports the hit rate against the 9.0 floor and lists anything that fell
short, so a batch can be corrected rather than silently accepted.
"""
from __future__ import annotations
import glob, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rate_quotes import score_one
from check_quotes import shingles

FLOOR = 9.0

def main() -> int:
    lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
    if not lines:
        print("no lines supplied"); return 1

    files = [pathlib.Path(f) for f in sorted(glob.glob("_data/quotes/*.json"))]
    data = {f: json.loads(f.read_text()) for f in files}
    allq = [(f, q) for f in files for q in data[f]["quotes"]]

    existing = [q["quote_text"] for _, q in allq]
    ex_sh = [shingles(t) for t in existing]

    accepted, rejected = [], []
    for line in lines:
        s, _, _ = score_one(line)
        sh = shingles(line)
        dup = any(sh and e and len(sh & e) / min(len(sh), len(e)) >= 0.6 for e in ex_sh)
        if dup:
            rejected.append((line, s, "near-duplicate of an existing quote"))
        elif s < FLOOR:
            rejected.append((line, s, f"scores {s}"))
        else:
            accepted.append((line, s))

    scored = sorted(allq, key=lambda fq: score_one(fq[1]["quote_text"])[0])
    n = 0
    for (f, oldq), (new, _) in zip(scored, accepted):
        for q in data[f]["quotes"]:
            if q["date_added"] == oldq["date_added"]:
                q["quote_text"] = new; n += 1; break
    for f, d in data.items():
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

    print(f"  supplied {len(lines)}  accepted {n}  rejected {len(rejected)}")
    if accepted:
        print(f"  accepted mean {sum(s for _, s in accepted)/len(accepted):.2f}")
    for line, s, why in rejected[:10]:
        print(f"    REJECT {s:>5}  {why[:34]:<34} {line[:44]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
