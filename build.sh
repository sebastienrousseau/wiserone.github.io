#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Regenerate the markdown from the quote data. _posts/ is derived, not
# authored: _data/quotes/*.json is the source of truth.
python3 tools/build_posts.py

# ssg reads a web-app manifest from the output directory; seed it from
# the checked-in copy so the build does not fail on an absent file.
mkdir -p public
if [ -f manifest.json ]; then cp -f manifest.json public/manifest.json; fi

# Compile with ssg.
ssg build -c=_posts -t=_layouts -o=public

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

find public -mindepth 1 -type d | while read -r dir; do
  for asset in styles.css main.js theme-init.js favicon.ico; do
    [ -f "public/${asset}" ] && cp -f "public/${asset}" "${dir}/${asset}"
  done
done

# The injected search widget ships a docs-oriented placeholder.
find public -name '*.html' -exec \
  sed -i '' -e 's/placeholder="Search documentation\.\.\."/placeholder="Search quotes…"/g' {} + 2>/dev/null || \
find public -name '*.html' -exec \
  sed -i -e 's/placeholder="Search documentation\.\.\."/placeholder="Search quotes…"/g' {} + 2>/dev/null || true

# ssg's sitemap plugin emits an empty urlset on a clean build, so
# rebuild it from what was actually written.
python3 tools/make_sitemap.py public

# _data/quotes/*.json is shared with the desktop and mobile apps, so the
# site must render every quote it contains — no hand-written pages, none
# dropped. Assert the counts match rather than trusting the generator.
python3 - <<'CHECK'
import glob, json, pathlib, sys
quotes = []
for f in sorted(glob.glob("_data/quotes/*.json")):
    d = json.loads(pathlib.Path(f).read_text())
    quotes.extend(d.get("quotes", d))
dates = {q["date_added"][:10] for q in quotes}
built = {p.stem for p in pathlib.Path("public").glob("2*.html")}
missing = sorted(dates - built)
extra = sorted(built - dates)
print(f"quotes in JSON: {len(dates)}; quote pages built: {len(built)}")
if missing or extra:
    if missing:
        print(f"ERROR: {len(missing)} quote(s) in JSON with no page: {missing[:5]}")
    if extra:
        print(f"ERROR: {len(extra)} page(s) with no quote in JSON: {extra[:5]}")
    sys.exit(1)
CHECK

# Build caches must not be served to the public.
rm -rf public/.ssg-cache public/.ssg-plugin-cache.json public/.meta

# The custom domain must be republished on every deploy: the gh-pages
# branch is force-orphaned, so an un-copied CNAME would be dropped and
# the domain setting lost.
if [ -f CNAME ]; then cp -f CNAME public/CNAME; fi

echo "Built $(find public -name '*.html' | wc -l | tr -d ' ') pages into public/"
