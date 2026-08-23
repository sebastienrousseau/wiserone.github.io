#!/usr/bin/env python3
"""Generate the markdown ssg compiles, from the quote data.

`_data/quotes/*.json` is the source of truth. This writes one post per
quote, plus the index, archive and supporting pages, into `_posts/`.

The index is chosen by date rather than fixed, so a scheduled rebuild
publishes a different quote each day without anyone editing content.
The selection is `day-of-year % len(quotes)`: deterministic for a given
day, which keeps builds reproducible, and stable if the build reruns.
"""

from __future__ import annotations

import datetime as dt
import glob
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
SITE = json.loads((ROOT / "_data" / "site.json").read_text())
BASE = SITE["url"].rstrip("/")


def load_quotes() -> list[dict]:
    quotes: list[dict] = []
    for path in sorted(glob.glob(str(ROOT / "_data" / "quotes" / "*.json"))):
        data = json.loads(pathlib.Path(path).read_text())
        quotes.extend(data.get("quotes", data))
    quotes.sort(key=lambda q: q["date_added"])
    return quotes


def slug(date_added: str) -> str:
    return date_added[:10]


def summarise(text: str, limit: int = 155) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter(**fields: str) -> str:
    lines = ["---"]
    lines += [f"{k}: {yaml_quote(v)}" for k, v in fields.items()]
    lines.append("---")
    return "\n".join(lines) + "\n"


def write(name: str, body: str) -> None:
    (POSTS / name).write_text(body, encoding="utf-8")


def quote_page(quote: dict) -> str:
    date = slug(quote["date_added"])
    pretty = dt.date.fromisoformat(date).strftime("%-d %B %Y")
    text = html.escape(quote["quote_text"])
    author = html.escape(quote["author"])
    body = front_matter(
        name=SITE["title"],
        short_name=SITE.get("short_name", SITE["title"]),
        keywords=SITE.get("keywords", ""),
        title=f"{summarise(quote['quote_text'], 60)} — The Wiser One",
        description=summarise(quote["quote_text"]),
        author=quote["author"],
        date=date,
        language=SITE["language"],
        layout="quote",
        permalink=f"{BASE}/{date}.html",
    )
    # Markdown, not raw HTML: ssg escapes embedded HTML in the body, so
    # a hand-written <blockquote> arrives on the page as visible tags.
    body += f"\n{pretty}\n\n> {text}\n>\n> — {author}\n"
    if quote.get("image_url"):
        body += f'\n![]({quote["image_url"]})\n'
    return body


def main() -> None:
    POSTS.mkdir(exist_ok=True)
    for stale in POSTS.glob("*.md"):
        stale.unlink()

    quotes = load_quotes()
    if not quotes:
        raise SystemExit("no quotes found in _data/quotes/*.json")

    for quote in quotes:
        write(f"{slug(quote['date_added'])}.md", quote_page(quote))

    today = dt.date.today()
    chosen = quotes[today.timetuple().tm_yday % len(quotes)]
    index = quote_page(chosen).replace('layout: "quote"', 'layout: "index"', 1)
    index = re.sub(r'^permalink: .*$', f'permalink: "{BASE}/"', index,
                   count=1, flags=re.M)
    index = re.sub(r'^title: .*$', f'title: "The Wiser One — {SITE["tagline"]}"',
                   index, count=1, flags=re.M)
    write("index.md", index)

    rows = "\n".join(
        f'- [{summarise(q["quote_text"], 80)}]({slug(q["date_added"])}.html) '
        f'— {dt.date.fromisoformat(slug(q["date_added"])).strftime("%-d %b %Y")}'
        for q in reversed(quotes)
    )
    write(
        "archive.md",
        front_matter(
            name=SITE["title"],
            short_name=SITE.get("short_name", SITE["title"]),
            keywords=SITE.get("keywords", ""),
            title=f"Archive — {SITE['title']}",
            description=f"Every quote published by The Wiser One — {len(quotes)} in all.",
            author=SITE["author"],
            language=SITE["language"],
            layout="page",
            permalink=f"{BASE}/archive.html",
        )
        + f"\n# Archive\n\n{len(quotes)} quotes, newest first.\n\n{rows}\n",
    )

    write(
        "about.md",
        front_matter(
            name=SITE["title"],
            short_name=SITE.get("short_name", SITE["title"]),
            keywords=SITE.get("keywords", ""),
            title=f"About — {SITE['title']}",
            description=SITE["description"],
            author=SITE["author"],
            language=SITE["language"],
            layout="page",
            permalink=f"{BASE}/about.html",
        )
        + f"\n# About\n\n{SITE['description']}\n\n"
        "The site is a static build: nothing runs on the server and no data "
        "is collected. Content lives in `_data/quotes/` and is compiled by "
        "[SSG](https://github.com/sebastienrousseau/static-site-generator).\n",
    )

    write(
        "404.md",
        front_matter(
            name=SITE["title"],
            short_name=SITE.get("short_name", SITE["title"]),
            keywords=SITE.get("keywords", ""),
            title="Not found — The Wiser One",
            description="That page does not exist.",
            author=SITE["author"],
            language=SITE["language"],
            layout="404",
            permalink=f"{BASE}/404.html",
        )
        + "\n# Not found\n\nThat page does not exist.\n",
    )

    print(f"generated {len(quotes)} quote pages + index, archive, about, 404")
    print(f"index quote: {slug(chosen['date_added'])} (day {today.timetuple().tm_yday})")


if __name__ == "__main__":
    main()
