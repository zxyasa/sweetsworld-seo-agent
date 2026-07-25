# Plan — SEO Title/Meta Rewrite

## Top 10 candidates (by impressions)
| # | slug | pos | CTR | imp | clk |
|---|------|-----|-----|-----|-----|
| 1 | are-nerds-vegan | 3.5 | 0.18% | 1091 | 2 |
| 2 | gluten-free-lollies-australia | 8.7 | 0.49% | 206 | 1 |
| 3 | best-lollies-for-party-bags | 8.3 | 0% | 139 | 0 |
| 4 | sugar-free-lollies-australia | 12.2 | 0% | 127 | 0 |
| 5 | australian-made-chocolate | 20.4 | 0.84% | 119 | 1 |
| 6 | white-knight-chocolate-where-to-buy-australia | 9.3 | 2.11% | 95 | 2 |
| 7 | australian-candy-brands | 22.1 | 0% | 94 | 0 |
| 8 | vegan-lollies-australia | 7.3 | 0% | 84 | 0 |
| 9 | british-chocolate-australia | 6.1 | 0% | 80 | 0 |
| 10 | korean-snacks-australia | 6.2 | 1.33% | 75 | 1 |

## Steps (5 total)

### Step 1 — Fetch current meta + baseline (LOW risk, read-only)
Write `src/title_meta_rewrite.py`. For each top 10 slug:
- `wp_client.find_post_by_slug()` → post_id, current title/content
- Query RankMath meta via existing `wp-seo-meta.php` (read mode — need to check endpoint)
  - Fallback: scrape `<title>` and `<meta name="description">` from live URL
- Record baseline to `.ai/tasks/seo-title-meta-rewrite/baseline.json`

### Step 2 — Generate rewrite proposals (LOW risk, no writes)
Rule-based template generator (no LLM first pass):
- Title: `{keyword_capitalized} | {angle} | Buy Online Australia | SweetsWorld`
  - angle examples: "Complete Guide", "Best Picks 2026", "Top X Brands", "What To Buy"
- Meta desc: hook + unique-value + CTA, 140-160 chars
  - Template: "Looking for {keyword}? Discover {N} {category} at SweetsWorld Australia. {freshness_hook}. Fast AU-wide shipping. Shop now."
- Save proposals to `.ai/tasks/seo-title-meta-rewrite/proposals.json`

### Step 3 — Dry-run review (USER GATE)
Present `proposals.json` as markdown diff: current vs proposed, per page.
Wait for user approval, edits, or reject list.

### Step 4 — Apply to live site (MEDIUM risk, writes)
For each approved page:
- Call `wp_client.write_seo_meta_via_db(post_id, keyword, seo_title, seo_description)`
- Record result to `applied.json`
- Sleep 1s between to be polite

### Step 5 — Verify + update tracker
- Fetch live page HTML, confirm new `<title>` and meta description in `<head>`
- Update `progress.md` with results
- Add GSC re-check reminder to memory for 2026-05-01 (14 days)
- Cleanup: no temp files

## Risk Register
- RankMath endpoint may not support read (only write) → fallback to HTML scrape for baseline
- `wp-seo-meta.php` hardcoded token or disabled → test with 1 page first before batch
- WP Rocket cache → new meta won't show immediately; verify with `?nocache=X`

## Rollback
For each page, baseline.json preserves original title + description. Re-run with
`--restore` flag (TODO: add to script) to revert.
