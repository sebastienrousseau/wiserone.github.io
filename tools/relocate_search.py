#!/usr/bin/env python3
"""Move ssg's search trigger into the site navigation.

ssg appends its widget at the end of <body> and positions the trigger
with `position: fixed; top: 16px; right: 16px`. That places it near the
header without being part of it, so it never shares the navigation's
baseline — and no `top` value can fix that, because the header's padding
is fluid (clamp on vh) while the fixed offset is not.

Moving the button into the nav makes it a sibling of the links, so the
flex row aligns all three on one baseline at every viewport. The dialog,
its script and its ids are untouched: the widget binds by id at runtime,
so it keeps working from its new position.
"""

from __future__ import annotations

import pathlib
import re
import sys

BTN = re.compile(r'<button id="ssg-search-btn".*?</button>', re.S)
TOGGLE = '<button class="theme-toggle"'


def relocate(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8")
    match = BTN.search(text)
    if not match or TOGGLE not in text:
        return False
    button = match.group(0)
    text = text[: match.start()] + text[match.end():]
    text = text.replace(TOGGLE, button + TOGGLE, 1)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    moved = sum(relocate(p) for p in root.rglob("*.html"))
    print(f"search trigger moved into the nav in {moved} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
