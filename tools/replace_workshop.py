#!/usr/bin/env python3
"""Replace quotes that drifted into workshop imagery.

Lines supplied on stdin, one per quote. Targets are chosen by vocabulary
rather than by score: these quotes are wrong in register even when they
score well, which is the point — the scorer rewarded them.
"""
from __future__ import annotations
import glob, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rate_quotes import score_one
from check_quotes import shingles

WORKSHOP = {"beam","plank","board","nail","nails","screw","bolt","chisel","saw",
 "blade","hinge","hinges","joint","joints","bench","workshop","shed","yard",
 "timber","wood","grain","seam","stitch","thread","cloth","rope","chain","axle",
 "pulley","crank","kettle","stove","bucket","furrow","fence","post","hedge",
 "orchard","plough","spade","wick","lamp","hearth","sail","harbour","wheel",
 "frame","panel","shelf","knife","hammer","varnish","sand","plane","tool",
 "tools","drawing","sketch","ornament","crack","roof","floor","gate","apprentice"}

def workshopish(text: str) -> bool:
    return bool(set(re.findall(r"[a-z]+", text.lower())) & WORKSHOP)

def main() -> int:
    lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
    files = [pathlib.Path(f) for f in sorted(glob.glob("_data/quotes/*.json"))]
    data = {f: json.loads(f.read_text()) for f in files}
    allq = [(f, q) for f in files for q in data[f]["quotes"]]
    ex_sh = [shingles(q["quote_text"]) for _, q in allq]

    good = []
    for line in lines:
        s, _, _ = score_one(line)
        sh = shingles(line)
        if workshopish(line):
            print(f"    REJECT (workshop imagery) {line[:52]}"); continue
        if any(sh and e and len(sh & e)/min(len(sh), len(e)) >= 0.6 for e in ex_sh):
            print(f"    REJECT (near-duplicate)    {line[:52]}"); continue
        if s < 9.0:
            print(f"    REJECT ({s})               {line[:52]}"); continue
        good.append((line, s))

    targets = [(f, q) for f, q in allq if workshopish(q["quote_text"])]
    n = 0
    for (f, oldq), (new, _) in zip(targets, good):
        for q in data[f]["quotes"]:
            if q["date_added"] == oldq["date_added"]:
                q["quote_text"] = new; n += 1; break
    for f, d in data.items():
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    remaining = sum(1 for f, q in
        [(f, q) for f in files for q in json.loads(f.read_text())["quotes"]]
        if workshopish(q["quote_text"]))
    print(f"  replaced {n};  workshop quotes remaining {remaining}")
    if good:
        print(f"  accepted mean {sum(s for _, s in good)/len(good):.2f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
