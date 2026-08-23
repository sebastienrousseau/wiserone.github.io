#!/usr/bin/env python3
"""Fail the build on links that break at /name/ URLs.

ssg publishes every page twice: /name.html and /name/index.html. A
relative href resolves against whichever URL the visitor is on, so
`href="about.html"` reaches /about.html from the flat copy but
/2024-01-11/about.html — a 404 — from the directory copy.

Every internal link and asset reference must therefore be root-relative.
This also resolves each one against the output tree, so a link to a page
that was never built fails here rather than in a browser.
"""
from __future__ import annotations

import pathlib
import re
import sys

ATTR = re.compile(r'(?:href|src)="([^"]+)"')
SKIP = ("http://", "https://", "//", "#", "mailto:", "data:", "tel:")


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    relative: list[str] = []
    missing: list[str] = []

    for page in sorted(root.rglob("*.html")):
        rel_page = page.relative_to(root)
        for target in ATTR.findall(page.read_text(encoding="utf-8")):
            if target.startswith(SKIP) or not target:
                continue
            if not target.startswith("/"):
                relative.append(f"{rel_page}: {target}")
                continue
            path = target.split("#")[0].split("?")[0].lstrip("/")
            if not path:
                continue
            candidate = root / path
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.exists():
                missing.append(f"{rel_page}: {target}")

    for label, items in (("relative", relative), ("missing target", missing)):
        if items:
            print(f"ERROR: {len(items)} {label} link(s):")
            for line in sorted(set(items))[:8]:
                print(f"  {line}")
    if relative or missing:
        return 1
    print("all internal links are root-relative and resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
