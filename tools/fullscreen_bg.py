#!/usr/bin/env python3
"""Promote each quote's banner to a full-screen background.

The quote pages carry the banner as an <img> inside the article. This
lifts it out and hands the URL to CSS as `--page-bg` on <body>, so the
stylesheet can paint it edge to edge behind the whole viewport, the way
the original wiserone site did.

The image is removed from the flow rather than hidden: leaving it would
download the same bytes twice and put a decorative duplicate in the
accessibility tree.

Pages without a banner (archive, about, 404) are left alone and simply
render on the flat paper colour.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

# the banner is the only <img> the generator emits, wrapped in its own <p>
IMG_P = re.compile(r"<p>\s*<img[^>]*\bsrc=\"(?P<src>[^\"]+)\"[^>]*>\s*</p>", re.S)
BODY = re.compile(r"<body(?P<attrs>[^>]*)>")


def promote(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8")
    match = IMG_P.search(text)
    if not match:
        return False
    src = html.unescape(match.group("src"))
    if '"' in src or ")" in src:          # refuse to build a broken url()
        return False

    text = text[: match.start()] + text[match.end():]

    body = BODY.search(text)
    if not body:
        return False
    attrs = body.group("attrs")
    style = f' style="--page-bg:url(&quot;{html.escape(src, quote=True)}&quot;)"'
    text = text[: body.start()] + f"<body{attrs}{style}>" + text[body.end():]

    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    promoted = sum(promote(p) for p in root.rglob("*.html"))
    print(f"banner promoted to full-screen background on {promoted} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
