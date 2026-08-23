#!/usr/bin/env python3
"""Check the palette in _layouts/styles.css against WCAG AAA.

Reads the declared custom properties rather than a copy of them: a
checker that asserts hardcoded literals passes happily while the
stylesheet drifts underneath it.

AAA is 7:1 for normal text. Every foreground token that carries text is
checked against the background it sits on, in both colour schemes.
"""
from __future__ import annotations

import pathlib
import re
import sys

CSS = pathlib.Path(__file__).resolve().parent.parent / "_layouts" / "styles.css"
AAA = 7.0


def srgb(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)


def ratio(fg: str, bg: str) -> float:
    a, b = lum(fg), lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def blocks(css: str) -> dict[str, dict[str, str]]:
    """Custom properties per selector block that defines --paper."""
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, body = m.group(1).strip(), m.group(2)
        props = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", body))
        if "--paper" in props:
            label = " ".join(sel.split())[-60:]
            out[label] = props
    return out


def main() -> int:
    css = CSS.read_text()
    schemes = blocks(css)
    if not schemes:
        print("ERROR: no palette blocks found in styles.css")
        return 1

    failures = 0
    for label, props in schemes.items():
        bg = props["--paper"]
        print(f"  {label}\n    background {bg}")
        for token in ("--ink", "--ink-muted"):
            fg = props.get(token)
            if not fg:
                continue
            r = ratio(fg, bg)
            verdict = "AAA" if r >= AAA else ("AA" if r >= 4.5 else "FAIL")
            if r < AAA:
                failures += 1
            print(f"    {token:<12} {fg}  {r:5.2f}:1  {verdict}")
    if failures:
        print(f"\nERROR: {failures} colour pair(s) below AAA ({AAA}:1)")
        return 1
    print("\n  all text colours meet WCAG AAA (7:1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
