# SEO Title/Meta Rewrite — Content Upgrade Candidates

## Goal
Rewrite SEO title + meta description for Top 10 underperforming landing pages
(from pilot_gate content_upgrade_candidates) to improve CTR and SERP ranking,
without touching page body content.

## Scope
- 10 pages selected by impression volume from 35 content upgrade candidates
- Only `rank_math_title` + `rank_math_description` fields (RankMath DB meta)
- No body content changes, no taxonomy changes
- Dry-run approval gate before live write

## Success Criteria
- Top 10 pages have new title/meta applied to live site
- Each new title contains target keyword + brand
- Each meta description 140-160 chars, includes CTA
- Verification: fetch page HTML, confirm new meta appears in `<head>`
- Record baseline GSC metrics; re-check in 14 days

## Out of Scope
- Body regeneration (that's a separate task: seo-body-regen)
- Products page SEO (different pipeline: optimize_product_seo.py)
- Newcastlehub site
