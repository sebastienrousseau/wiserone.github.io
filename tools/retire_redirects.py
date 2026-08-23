#!/usr/bin/env python3
"""Keep retired quote URLs alive.

Since the corpus cut, `/q/<slug>/` pages are the canonical, indexed
surface of the site — every dated URL points its rel=canonical at one.
That makes retiring a quote destructive in a way it never used to be:
the slug disappears with it, and a URL search engines were told was
authoritative starts 404ing.

So `_data/retired.json` records every slug ever published and removed,
and this writes a redirect page for each, pointing at the pillar the
quote belonged to.

GitHub Pages serves static files and cannot issue a real 301. A
zero-delay meta refresh with a rel=canonical is the closest equivalent
a static host has, and Google documents it as being treated like a
permanent redirect. The visible link is not decoration: it is what a
reader gets if the refresh is blocked, and what a screen reader
announces before the navigation happens.
"""

from __future__ import annotations

import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "_data" / "site.json").read_text())
BASE = SITE["url"].rstrip("/")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Moved — {title}</title>
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="noindex, follow">
<style>
:root {{ color-scheme: light dark; }}
body {{ font: 1rem/1.6 system-ui, sans-serif; margin: 0; padding: 3rem 1.5rem;
        max-width: 34rem; background: #111; color: #f2f2f2; }}
a {{ color: #9cc3ff; }}
</style>
</head>
<body>
<h1>This quote was retired</h1>
<p>It has been taken out of the collection. You are being sent to
<a href="{target}">{label}</a>.</p>
</body>
</html>
"""


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    retired = json.loads((ROOT / "_data" / "retired.json").read_text())["retired"]
    pillars = {p["slug"]: p["title"] for p in
               json.loads((ROOT / "_data" / "pillars.json").read_text())["pillars"]}

    live = {p.parent.name for p in out.glob("q/*/index.html")}
    written, skipped = 0, []
    for entry in retired:
        slug = entry["slug"]
        # A retired line can be brought back. If it is, the real page
        # wins and this must not overwrite it.
        if slug in live:
            skipped.append(slug)
            continue
        title = pillars.get(entry["pillar"], "the archive")
        body = PAGE.format(
            title=html.escape(SITE["title"]),
            target=f"{BASE}/archive/#{entry['pillar']}",
            canonical=f"{BASE}/archive/",
            label=html.escape(title.lower()),
        )
        (out / "q" / slug).mkdir(parents=True, exist_ok=True)
        (out / "q" / slug / "index.html").write_text(body, encoding="utf-8")
        # ssg publishes both forms; a retired URL may have been indexed
        # under either.
        (out / "q" / f"{slug}.html").write_text(body, encoding="utf-8")
        written += 1

    print(f"retired-slug redirects: {written} written"
          + (f", {len(skipped)} back in the pool ({', '.join(skipped[:3])})"
             if skipped else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
