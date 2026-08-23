#!/usr/bin/env python3
"""Give the archive's pillar headings stable ids.

ssg renders markdown headings as bare `<h2>` with no id, so the pillar
anchors that retired-slug redirects point at (`/archive/#elimination`)
would all land at the top of a 136-item page.

Ids come from `_data/pillars.json` keyed on the heading's own text, not
from slugifying that text: the redirect targets the pillar's slug
(`elimination`) while the heading reads "Elimination and focus", and
inventing the id from the text would silently produce a different
anchor from the one being linked to.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
H2 = re.compile(r"<h2(?![^>]*\bid=)([^>]*)>(.*?)</h2>", re.I | re.S)


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    pillars = json.loads((ROOT / "_data" / "pillars.json").read_text())["pillars"]
    by_title = {p["title"]: p["slug"] for p in pillars}

    page = out / "archive" / "index.html"
    if not page.exists():
        print("ERROR: no archive page to anchor")
        return 1
    text = page.read_text(encoding="utf-8")

    seen: list[str] = []

    def add_id(m: re.Match) -> str:
        label = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        slug = by_title.get(label)
        if not slug:
            return m.group(0)
        seen.append(slug)
        return f'<h2 id="{slug}"{m.group(1)}>{m.group(2)}</h2>'

    page.write_text(H2.sub(add_id, text), encoding="utf-8")

    missing = [p["slug"] for p in pillars if p["slug"] not in seen]
    print(f"archive anchors: {len(seen)} of {len(pillars)} pillars")
    if missing:
        print(f"ERROR: no heading matched for {missing}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
