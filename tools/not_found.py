#!/usr/bin/env python3
"""Make the 404 page say it is not a page worth indexing.

GitHub Pages serves `404.html`, with status 404, for every missing URL.
ssg's canonical plugin stamps `<link rel="canonical">` on every page it
writes, with no opt-out, so each of those responses told Google the
missing URL's canonical was https://wiserone.com/404/. Its AI plugin
also adds a robots meta that invites snippets. And `/404/` itself is
served with status 200, which Search Console reads as a soft 404.

A 404 page must not name a canonical. This strips the tag from the 404
page, in both forms ssg publishes, and replaces its robots meta with
`noindex`, which also keeps it out of the sitemap (make_sitemap skips
noindex pages).
"""

from __future__ import annotations

import pathlib
import re
import sys

CANONICAL = re.compile(r'\s*<link[^>]+rel=["\']canonical["\'][^>]*>', re.I)
ROBOTS = re.compile(r'\s*<meta[^>]+name=["\']robots["\'][^>]*>', re.I)
NOINDEX = '<meta name="robots" content="noindex">'


def fix(text: str) -> str:
    text = CANONICAL.sub("", text)
    text = ROBOTS.sub("", text)
    return text.replace("</head>", f"  {NOINDEX}\n</head>", 1)


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    pages = [p for p in (out / "404.html", out / "404" / "index.html")
             if p.exists()]
    if not pages:
        print("ERROR: no 404 page in the build")
        return 1
    for p in pages:
        p.write_text(fix(p.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"404 page: canonical removed, noindex set ({len(pages)} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
