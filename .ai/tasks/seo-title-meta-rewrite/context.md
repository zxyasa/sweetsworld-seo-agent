# Context — SEO Title/Meta Rewrite

## Key Files
- `src/wp_client.py` — `write_seo_meta_via_db()` line 498, `find_post_by_slug()` line 380
- `reports/pilot_gate.json` — content_upgrade_candidates list
- `public_html/wp-seo-meta.php` (on server) — RankMath write bridge, 1083 bytes
- `.env` — needs `WP_SEO_BRIDGE_TOKEN` for the bridge

## Search Hints
- RankMath DB key names: `rank_math_title`, `rank_math_description`, `rank_math_focus_keyword`
- WP meta fetch (REST): `/wp/v2/posts/{id}?context=edit` but RankMath fields not exposed via REST — use HTML scrape
- Cache: add `?nocache=$(date +%s)` to verify fetches

## Environment Requirements
- `WP_BASE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` (from sites/sweetsworld/.env)
- `WP_SEO_BRIDGE_TOKEN` (must match token inside wp-seo-meta.php)
