# wiserone.com

The public site for **The Wiser One** — a daily quote, published as a
static site and served from GitHub Pages at
[wiserone.com](https://wiserone.com).

Built with [SSG](https://github.com/sebastienrousseau/static-site-generator).

## Layout

```
_data/site.json       site metadata (title, description, url, …)
_data/quotes/*.json   the quotes — the source of truth for all content
_layouts/             page templates, CSS and JS
_posts/               generated markdown — do not edit by hand
tools/build_posts.py  regenerates _posts/ from _data/quotes/
tools/unescape_content.py  post-build fixup, see below
build.sh              the whole build
public/               build output, gitignored
```

`_posts/` is derived. To change content, edit `_data/quotes/*.json` and
rebuild; anything written directly into `_posts/` is deleted on the next
build.

## Building

```sh
cargo binstall ssg     # or: cargo install ssg
./build.sh
```

Output lands in `public/`. Serve it with any static file server.

## The daily quote

`index.html` is the quote for the current day, chosen as
`day-of-year % number-of-quotes`. That is deterministic for a given day,
so a rebuild produces the same page, and it advances on its own without
anyone editing content. The workflow therefore runs on a daily schedule
as well as on push — without that, the front page would freeze on
whatever day the last push happened.

## Why there is a post-build fixup

`tools/unescape_content.py` exists because ssg renders markdown to HTML
correctly and then escapes the result when it substitutes `{{content}}`,
so a page would show literal `&lt;blockquote&gt;` text.

It only rewrites the block inside `<main>`. The same content is also
interpolated into `meta[name=twitter:description]` and the JSON-LD
block, where it is correctly escaped and must stay that way: unescaping
it there yields a `content="<div lang="en">…"` attribute that ends at
the first inner quote, and JSON-LD that no longer parses.

## Deployment

`.github/workflows/build.yml` builds and publishes `public/` to the
`gh-pages` branch. The deploy is guarded — it refuses to publish if
`index.html`, `archive.html` or `CNAME` are missing, if fewer than 60
pages were produced, or if the front page has no rendered quote. Since
the branch is force-orphaned there is no previous commit to fall back
to, so a bad build must not reach it.

`CNAME` is committed at the repository root and copied into `public/` on
every build. It has to be republished each time, or the force-orphan
would drop it and the custom domain would be lost.
