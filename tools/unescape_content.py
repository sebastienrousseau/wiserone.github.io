#!/usr/bin/env python3
"""Unescape the page body ssg emits HTML-escaped.

ssg renders markdown to HTML correctly, then escapes the result when it
substitutes `{{content}}`, wrapping it in a language div. A page ends up
carrying literal `&lt;blockquote&gt;` text instead of a quotation.

The upstream theme this site is modelled on never hits this: its posts
are frontmatter-only and their markup lives in the layouts. Pages here
differ per quote, so the body must come through `{{content}}`.

Scope matters. ssg also interpolates the same content into
`meta[name=twitter:description]` and into the JSON-LD block, where it is
correctly escaped and MUST stay that way — unescaping it there produces
a `content="<div lang="en">…"` attribute that terminates at the first
inner quote, and JSON-LD that no longer parses. Those copies appear
earlier in the document than `<main>`, so a document-wide "first match"
substitution corrupts exactly the wrong one.

Only the block inside `<main>` is touched.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

MAIN = re.compile(r"(?P<open><main\b[^>]*>)(?P<body>.*?)(?P<close></main>)", re.S)
BLOCK = re.compile(
    r"&lt;div lang=&quot;(?P<lang>[^&]*)&quot;&gt;(?P<body>.*?)&lt;/div&gt;",
    re.S,
)


def fix(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8")
    main = MAIN.search(text)
    if not main:
        return False
    block = BLOCK.search(main.group("body"))
    if not block:
        return False
    inner = html.unescape(block.group("body")).strip()
    new_main_body = (
        main.group("body")[: block.start()]
        + f'<div lang="{block.group("lang")}">{inner}</div>'
        + main.group("body")[block.end():]
    )
    path.write_text(
        text[: main.start()]
        + main.group("open") + new_main_body + main.group("close")
        + text[main.end():],
        encoding="utf-8",
    )
    return True


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    changed = sum(fix(p) for p in root.rglob("*.html"))
    print(f"unescaped <main> body in {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
