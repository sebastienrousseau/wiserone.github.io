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

# The custom domain must be republished on every deploy: the gh-pages
# branch is force-orphaned, so an un-copied CNAME would be dropped and
# the domain setting lost.
if [ -f CNAME ]; then cp -f CNAME public/CNAME; fi

echo "Built $(find public -name '*.html' | wc -l | tr -d ' ') pages into public/"
