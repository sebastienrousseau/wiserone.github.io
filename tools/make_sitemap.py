#!/usr/bin/env python3
"""Write sitemap.xml and robots.txt from the built pages.

ssg emits a sitemap, but on a clean build it contains zero <url>
entries — a 445-byte empty urlset. It only looked populated locally
because repeated builds accumulated in public/; CI builds cold, so the
deployed sitemap listed nothing at all.

This walks the output instead, so the sitemap describes what was
actually published.

It lists only self-canonical pages. Since the 2026-08-23 corpus cut the
site serves ~1,000 dated URLs that all point their rel=canonical at one
of 138 quote pages, so that the cycling pool cannot flood the index with
near-duplicates. Advertising those dated URLs here would undo exactly
that: a sitemap is a request to index, and these pages ask not to be.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import xml.sax.saxutils as sax

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "_data" / "site.json").read_text())
BASE = SITE["url"].rstrip("/")

# Served copies of the same page: prefer the extensionless directory
# form and skip the .html duplicate, so each page appears once.
# Directory form, matching the locs built below — "404.html"
# silently stopped matching once pages moved to /404/.
SKIP_NAMES = {"/404/"}

CANONICAL = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
    re.I)


def self_canonical(page: pathlib.Path, loc: str) -> bool:
    """True if the page claims itself as canonical.

    A page that names a different canonical is a deliberate duplicate —
    a date view of a pooled quote — and belongs out of the sitemap. A
    page with no canonical at all is kept: absence is not a disclaimer.
    """
    m = CANONICAL.search(page.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return True
    declared = m.group(1).rstrip("/")
    return declared in (loc.rstrip("/"), loc.rstrip("/") + "/index.html")


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    today = dt.date.today().isoformat()

    locs: list[str] = []
    for page in sorted(out.rglob("index.html")):
        rel = page.relative_to(out).parent.as_posix()
        # Directory form, matching what ssg emits as <link rel="canonical">.
        # Listing /x.html here while the page declares /x/ canonical would
        # advertise a URL the site itself says is not the real one.
        loc = f"{BASE}/" if rel == "." else f"{BASE}/{rel}/"
        if self_canonical(page, loc):
            locs.append(loc)

    seen, unique = set(), []
    for loc in locs:
        if loc not in seen and not any(loc.endswith(s) for s in SKIP_NAMES):
            seen.add(loc)
            unique.append(loc)

    entries = "\n".join(
        "  <url>\n"
        f"    <loc>{sax.escape(loc)}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>{'daily' if loc == BASE + '/' else 'monthly'}</changefreq>\n"
        f"    <priority>{'1.0' if loc == BASE + '/' else '0.6'}</priority>\n"
        "  </url>"
        for loc in unique
    )
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n</urlset>\n",
        encoding="utf-8",
    )
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n",
        encoding="utf-8",
    )
    total = sum(1 for _ in out.rglob("index.html"))
    print(f"sitemap.xml: {len(unique)} urls "
          f"({total - len(unique)} non-canonical pages excluded); "
          "robots.txt written")
    return 0 if unique else 1


if __name__ == "__main__":
    raise SystemExit(main())
