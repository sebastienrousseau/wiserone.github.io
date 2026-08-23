#!/usr/bin/env python3
"""Point each date page's rel=canonical at the quote it shows.

ssg derives rel=canonical from a page's own output path and ignores the
`permalink` front-matter field, which only reaches og:url. That is right
for an ordinary site and wrong for this one: since the 2026-08-23 corpus
cut, ~1,000 dated URLs each render one of 138 pooled quotes, so every
quote appears at roughly eight addresses. Left self-canonical, the site
would ask Google to index eight copies of each line and let it pick.

So this rewrites the tag after the build. og:url already carries the
right target — build_posts puts it there — so that is what we copy,
which also means the two can never disagree.

Pages whose og:url already matches their own address (the front page,
about, archive, and the 138 quote pages themselves) are left alone.
"""

from __future__ import annotations

import pathlib
import re
import sys

CANON = re.compile(
    r'(<link\s+rel="canonical"\s+href=")([^"]+)(")', re.I)
OG_URL = re.compile(
    r'<meta\s+property="og:url"\s+content="([^"]+)"', re.I)


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    changed = 0
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8", errors="replace")
        og = OG_URL.search(text)
        canon = CANON.search(text)
        if not og or not canon:
            continue
        target, current = og.group(1), canon.group(2)
        if target.rstrip("/") == current.rstrip("/"):
            continue
        page.write_text(CANON.sub(
            lambda m: m.group(1) + target + m.group(3), text, count=1),
            encoding="utf-8")
        changed += 1
    print(f"canonicalised {changed} page(s) to their quote's own URL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
