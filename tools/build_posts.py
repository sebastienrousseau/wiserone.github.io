#!/usr/bin/env python3
"""Generate the markdown ssg compiles, from the quote pool.

`_data/quotes/quotes.json` is the source of truth: a pool of calibrated
quotes, ordered and stable. It is deliberately small. Until 2026-08-23
the corpus held 1,033 entries of which only 138 had been written by ear
— the other 895 were machine-generated backfill in a register the site
had long since abandoned, and they were what a reader saw 87% of the
time. They were deleted.

That left a problem: 1,033 dated URLs were live and indexed. So dates no
longer own quotes. Instead:

  * Every quote gets one canonical page at `/q/<slug>.html`.
  * Every date in the published range still resolves, at
    `/YYYY-MM-DD.html`, showing the quote that date maps to.
  * A date page's canonical points at the quote's own page, so the
    duplication a cycling pool necessarily creates — each quote surfaces
    on roughly every 138th date — never reads as duplicate content.

The map is `date.toordinal() % len(pool)`: deterministic, so a rebuild
of the same day yields the same page, and total, so the front page can
never run dry again the way it did when it sat on 25 February 2024.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
SITE = json.loads((ROOT / "_data" / "site.json").read_text())
BASE = SITE["url"].rstrip("/")

# Dates published before the cut. They predate the pool and must never
# 404; see _data/legacy_range.json.
LEGACY = json.loads((ROOT / "_data" / "legacy_range.json").read_text())
# Days ahead of today to pre-render, so today's permalink and the next
# few days resolve between scheduled rebuilds.
LOOKAHEAD = 30


def load_pool() -> list[dict]:
    data = json.loads((ROOT / "_data" / "quotes" / "quotes.json").read_text())
    pool = data["quotes"]
    pool.sort(key=lambda q: q["id"])
    return pool


def slug(text: str, limit: int = 64) -> str:
    """Stable, readable URL segment for a quote."""
    s = unicodedata.normalize("NFKD", text.lower())
    s = s.encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0]
    return s


def assign_slugs(pool: list[dict]) -> None:
    seen: dict[str, int] = {}
    for q in pool:
        base = slug(q["quote_text"])
        n = seen.get(base, 0)
        seen[base] = n + 1
        q["slug"] = base if n == 0 else f"{base}-{n + 1}"


def for_date(pool: list[dict], date: dt.date) -> dict:
    return pool[date.toordinal() % len(pool)]


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
    path = POSTS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def quote_body(quote: dict, shown_date: dt.date | None, layout: str,
               canonical: str, title: str | None = None) -> str:
    """One rendered quote.

    `canonical` is what ssg emits as rel=canonical and og:url. For a date
    page that is deliberately NOT the page's own address — it is the
    quote's canonical page, which is how the cycling pool avoids putting
    eight near-identical URLs into the index for every quote.
    """
    text = html.escape(quote["quote_text"])
    author = html.escape(quote["author"])
    fields = dict(
        name=SITE["title"],
        short_name=SITE.get("short_name", SITE["title"]),
        keywords=SITE.get("keywords", ""),
        title=title or f"{summarise(quote['quote_text'], 60)} — The Wiser One",
        description=summarise(quote["quote_text"]),
        author=quote["author"],
        language=SITE["language"],
        layout=layout,
        permalink=canonical,
    )
    # Every page needs a date field or ssg's news-sitemap generator falls
    # back to wall-clock time, which makes the feed non-reproducible. A
    # canonical quote page has no date on it, so it carries the day the
    # line was written — provenance, not publication.
    when = (shown_date.isoformat() if shown_date is not None
            else quote["date_added"][:10])
    fields["date"] = when
    # ssg's news-sitemap generator reads its own key and does not fall
    # back to `date`. Unset, it emits an empty <news:publication_date>
    # for every page — the deployed sitemap has carried that since the
    # site launched — and stamps wall-clock time into the build, which
    # makes consecutive builds of the same commit differ.
    fields["news_publication_date"] = when
    body = front_matter(**fields)
    # Markdown, not raw HTML: ssg escapes embedded HTML in the body, so a
    # hand-written <blockquote> arrives on the page as visible tags. The
    # quote is the page's h1 — every page needs exactly one for
    # WAVE/Lighthouse, and the quote is what the page is about.
    if shown_date is not None:
        body += f"\n{shown_date.strftime('%-d %B %Y')}\n"
    body += f"\n> # {text}\n>\n> — {author}\n"
    if quote.get("image_url"):
        body += f'\n![]({quote["image_url"]})\n'
    return body


def daterange(first: dt.date, last: dt.date):
    for n in range((last - first).days + 1):
        yield first + dt.timedelta(days=n)


def main() -> None:
    POSTS.mkdir(exist_ok=True)
    for stale in POSTS.rglob("*.md"):
        stale.unlink()

    pool = load_pool()
    if not pool:
        raise SystemExit("no quotes in _data/quotes/quotes.json")
    assign_slugs(pool)

    today = dt.datetime.now(dt.timezone.utc).date()

    # 1. Canonical page per quote — the only quote URLs in the sitemap.
    for q in pool:
        write(f"q/{q['slug']}.md",
              quote_body(q, None, "quote", f"{BASE}/q/{q['slug']}/"))

    # 2. Every previously-published date, plus a short runway ahead.
    first = dt.date.fromisoformat(LEGACY["first"])
    last = max(dt.date.fromisoformat(LEGACY["last"]),
               today + dt.timedelta(days=LOOKAHEAD))
    dates = list(daterange(first, last))
    for d in dates:
        q = for_date(pool, d)
        write(f"{d.isoformat()}.md",
              quote_body(q, d, "quote", f"{BASE}/q/{q['slug']}/"))

    # 3. Front page — today's quote, canonical to the site root.
    chosen = for_date(pool, today)
    write("index.md",
          quote_body(chosen, today, "index", f"{BASE}/",
                     title=f"The Wiser One — {SITE['tagline']}"))

    # 4. Archive lists the pool, not the dates: 138 real pages, not 1,000
    #    rotations of them.
    # Grouped by pillar, not flat: it gives a reader some shape to the
    # collection, and it gives a retired slug's redirect a destination
    # with the right context rather than the top of a 136-item list.
    pillars = json.loads((ROOT / "_data" / "pillars.json").read_text())["pillars"]
    sections = []
    for pil in pillars:
        members = [q for q in pool if q.get("pillar") == pil["slug"]]
        if not members:
            continue
        sections.append(f'## {pil["title"]}\n\n' + "\n".join(
            f'- [{summarise(q["quote_text"], 80)}](/q/{q["slug"]}/)'
            for q in members))
    rows = "\n\n".join(sections)
    write("archive.md", front_matter(
        name=SITE["title"],
        short_name=SITE.get("short_name", SITE["title"]),
        keywords=SITE.get("keywords", ""),
        title=f"Archive — {SITE['title']}",
        description=f"Every quote published by The Wiser One — {len(pool)} in all.",
        author=SITE["author"],
        language=SITE["language"],
        layout="page",
        permalink=f"{BASE}/archive/",
    ) + f"\n# Archive\n\n{len(pool)} quotes.\n\n{rows}\n")

    write("about.md", front_matter(
        name=SITE["title"],
        short_name=SITE.get("short_name", SITE["title"]),
        keywords=SITE.get("keywords", ""),
        title=f"About — {SITE['title']}",
        description=SITE["description"],
        author=SITE["author"],
        language=SITE["language"],
        layout="page",
        permalink=f"{BASE}/about/",
    ) + f"\n# About\n\n{SITE['description']}\n")

    write("404.md", front_matter(
        name=SITE["title"],
        short_name=SITE.get("short_name", SITE["title"]),
        keywords=SITE.get("keywords", ""),
        title="Not found — The Wiser One",
        description="That page does not exist.",
        author=SITE["author"],
        language=SITE["language"],
        layout="404",
        permalink=f"{BASE}/404.html",
    ) + "\n# Not found\n\nThat page does not exist.\n")

    print(f"pool {len(pool)} quotes → {len(pool)} canonical pages "
          f"+ {len(dates)} date pages ({first} → {last})")
    print(f"today {today}: {chosen['slug']}")


if __name__ == "__main__":
    main()
