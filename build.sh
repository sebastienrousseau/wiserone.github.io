#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Corpus quality and daily-runway gates. The first refuses duplicates,
# near-duplicates and famous quotations attributed to The Wiser One; the
# second refuses to publish a site whose front page has no quote for
# today, or that is about to run dry.
python3 tools/check_quotes.py
python3 tools/publish_daily.py --check

# Structural scoring against the documented profile. These floors are a
# ratchet, not an achievement: the corpus mean is 4.83 today and the
# rewrite is in progress, so they are set just below current values to
# stop regression while the work continues. Raise them as the mean
# climbs — a floor nobody can breach is not a gate.
#
#   --min-mean   corpus average must not fall
#   --min-quote  no single quote may be worse than the current floor
#   --min-today  the front page carries a higher bar than the archive
# The scorer must first be shown to rank the target register above the
# pastiche it previously rewarded. An internally consistent rubric can
# still be externally wrong; ordering is what catches that.
python3 tools/validate_scorer.py
# Floors re-cut after the 2026-08-23 corpus purge. The old 6.80 mean was
# set against 1,033 quotes of which 895 were backfill; the surviving 138
# average 7.90 and none scores below 6.17. These are ratchets — they
# exist to catch a regression, not to be satisfied by a rewrite.
python3 tools/rate_quotes.py --min-mean 7.75 --min-quote 6.0 --min-today 6.0

# Regenerate the markdown from the quote data. _posts/ is derived, not
# authored: _data/quotes/*.json is the source of truth.
python3 tools/build_posts.py

# ssg reads a web-app manifest from the output directory; seed it from
# the checked-in copy so the build does not fail on an absent file.
mkdir -p public
if [ -f manifest.json ]; then cp -f manifest.json public/manifest.json; fi

# Fail early if the palette drifts below AAA.
python3 tools/contrast.py

# Compile with ssg.
ssg build -f=config.toml -c=_posts -t=_layouts -o=public

# ssg escapes the rendered body when substituting {{content}}; restore it.
python3 tools/unescape_content.py public

# ssg emits <name>/index.html; publish <name>.html alongside it so both
# /archive and /archive.html resolve.
find public -mindepth 2 -type f -name 'index.html' | while read -r page; do
  dir="$(dirname "$page")"
  [ "$dir" = "public" ] && continue
  cp -f "$page" "${dir}.html"
done

# Theme assets sit in _layouts/ and must land beside the pages, both at
# the root and inside each generated subdirectory.
for asset in styles.css main.js theme-init.js; do
  [ -f "_layouts/${asset}" ] && cp -f "_layouts/${asset}" "public/${asset}"
done
if [ -f favicon.ico ]; then cp -f favicon.ico public/favicon.ico; fi
if [ -d assets ]; then mkdir -p public/assets && cp -R assets/. public/assets/; fi


# Lift each quote's banner into a full-screen background.
python3 tools/fullscreen_bg.py public

# Put the search trigger in the nav so it aligns with the links.
python3 tools/relocate_search.py public

# The injected search widget ships a docs-oriented placeholder.
find public -name '*.html' -exec \
  sed -i '' -e 's/placeholder="Search documentation\.\.\."/placeholder="Search quotes…"/g' {} + 2>/dev/null || \
find public -name '*.html' -exec \
  sed -i -e 's/placeholder="Search documentation\.\.\."/placeholder="Search quotes…"/g' {} + 2>/dev/null || true

# Repoint dated pages at the canonical page for the quote they show.
# Must run before the sitemap, which decides membership by reading the
# canonical tags this writes.
python3 tools/canonicalise.py public

# ssg's sitemap plugin emits an empty urlset on a clean build, so
# rebuild it from what was actually written.
python3 tools/make_sitemap.py public

# Two contracts to hold. First, every quote in the pool must have a
# canonical page. Second — and this is the one that matters after the
# corpus cut — every date URL ever published must still resolve: 1,033
# of them were live and indexed when the 895 backfill quotes were
# deleted, and none of them may 404.
python3 - <<'CHECK'
import datetime as dt, json, pathlib, sys
sys.path.insert(0, "tools")
from build_posts import assign_slugs, load_pool

pool = load_pool()
assign_slugs(pool)
public = pathlib.Path("public")

missing_q = [q["slug"] for q in pool
             if not (public / "q" / q["slug"] / "index.html").exists()]

legacy = json.loads(pathlib.Path("_data/legacy_range.json").read_text())
first = dt.date.fromisoformat(legacy["first"])
last = dt.date.fromisoformat(legacy["last"])
today = dt.datetime.now(dt.timezone.utc).date()
required = {first + dt.timedelta(days=n) for n in range((last - first).days + 1)}
required |= {today + dt.timedelta(days=n) for n in range(31)}
missing_d = [d.isoformat() for d in sorted(required)
             if not (public / d.isoformat() / "index.html").exists()]

print(f"pool: {len(pool)} quotes, {len(pool) - len(missing_q)} canonical pages; "
      f"date URLs required {len(required)}, missing {len(missing_d)}")
if missing_q:
    print(f"ERROR: {len(missing_q)} quote(s) with no page: {missing_q[:5]}")
if missing_d:
    print(f"ERROR: {len(missing_d)} date URL(s) would 404: {missing_d[:5]}")
if missing_q or missing_d:
    sys.exit(1)
CHECK

# The image CDN moved from kura.pro to cloudcdn.pro, and every kura.pro
# path now 404s. Fail rather than publish pages with broken banners.
if grep -rqs 'kura\.pro' public; then
  echo "ERROR: kura.pro still referenced in the build output:"
  grep -rls 'kura\.pro' public | head -5
  exit 1
fi

python3 tools/check_links.py public

# Build caches must not be served to the public.
rm -rf public/.ssg-cache public/.ssg-plugin-cache.json public/.meta

python3 tools/minify_css.py public/styles.css

# The custom domain must be republished on every deploy: the gh-pages
# branch is force-orphaned, so an un-copied CNAME would be dropped and
# the domain setting lost.
if [ -f CNAME ]; then cp -f CNAME public/CNAME; fi

echo "Built $(find public -name '*.html' | wc -l | tr -d ' ') pages into public/"
