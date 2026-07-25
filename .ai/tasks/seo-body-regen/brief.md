# SEO Body Regeneration — Stuck-at-5-10 Pages

## Goal
Lift 25 published landing/guide pages currently stuck at Google positions 5-10
to positions 1-4 by regenerating body content (deeper, more E-E-A-T signals,
better schema). Title/meta already fixed in sister task `seo-title-meta-rewrite`.

## Target
- Average position delta: +2 across Tier A (6 pages)
- Minimum success: 4 of 6 Tier A pages improve by ≥1 position within 30 days
- LLM spend: ~$3 total (sonnet-4-6)
- Engineering: 10-11h spread over ~35 calendar days

## Scope
- 25 pages from `reports/pilot_gate.json` → `pages_stuck_detail`
- Tiered rollout: A (6) → wait 14d → B (8) → wait 14d → C (11)
- Per-page backup + rollback recipe mandatory

## Out of Scope
- Title / meta description (already done in seo-title-meta-rewrite)
- H1 (already corrected)
- URL slug, post_id, featured image, focus keyword postmeta
- Newcastlehub site
