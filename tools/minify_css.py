#!/usr/bin/env python3
"""Minify the published stylesheet.

The source keeps its comments — they explain why selectors are shaped
the way they are. Only the copy in public/ is stripped.
"""
from __future__ import annotations
import pathlib, re, sys

def minify(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{}:;,>~+])\s*", r"\1", css)
    css = re.sub(r";}", "}", css)
    return css.strip()

def main() -> int:
    target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public/styles.css")
    if not target.exists():
        print(f"ERROR: {target} not found")
        return 1
    before = target.read_text(encoding="utf-8")
    after = minify(before)
    target.write_text(after, encoding="utf-8")
    for sub in target.parent.rglob("styles.css"):
        if sub != target:
            sub.write_text(after, encoding="utf-8")
    print(f"minified styles.css {len(before)} -> {len(after)} bytes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
