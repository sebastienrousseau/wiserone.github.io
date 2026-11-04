#!/usr/bin/env python3
"""Fail the build on the indexing faults Search Console reported.

Each check is one Search Console finding, held so it cannot come back:

  * a legacy `/YYYY_MM_DD.html` date URL, or `/q/`, that 404s;
  * a 404 page that declares a canonical, or lacks noindex;
  * `/404/` listed in the sitemap.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_posts import BASE  # noqa: E402
from legacy_redirects import legacy_dates  # noqa: E402

CANONICAL = re.compile(r'<link[^>]+rel=["\']canonical["\']', re.I)
NOINDEX = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]*noindex', re.I)


def not_found_errors(out: pathlib.Path) -> list[str]:
    found: list[str] = []
    for page in (out / "404.html", out / "404" / "index.html"):
        text = page.read_text(encoding="utf-8") if page.exists() else ""
        if CANONICAL.search(text):
            found.append(f"{page.relative_to(out)} declares a canonical")
        if not NOINDEX.search(text):
            found.append(f"{page.relative_to(out)} is not noindex")
    return found


def errors(out: pathlib.Path) -> list[str]:
    found = not_found_errors(out)
    missing = [d.strftime("%Y_%m_%d.html") for d in legacy_dates()
               if not (out / d.strftime("%Y_%m_%d.html")).exists()]
    if missing:
        found.append(f"{len(missing)} legacy date URL(s) would 404: "
                     f"{missing[:3]}")
    if not (out / "q" / "index.html").exists():
        found.append("/q/ would 404")
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    if f"<loc>{BASE}/404" in sitemap:
        found.append("sitemap.xml lists the 404 page")
    return found


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    found = errors(out)
    for line in found:
        print(f"ERROR: {line}")
    if not found:
        print(f"indexing: {len(legacy_dates())} legacy date URLs and /q/ "
              "redirect; 404 page is noindex with no canonical; "
              "sitemap omits it")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
