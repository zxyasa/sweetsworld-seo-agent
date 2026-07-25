# Progress — SEO Title/Meta Rewrite

Started: 2026-04-17  
Completed batch 1: 2026-04-17  
Completed batch 2: 2026-04-17  
Total steps: 5 × 2 batches

## Batch 1 (top 10 by impressions)

- [x] Step 1 — Fetch current meta + baseline
- [x] Step 2 — Generate rewrite proposals (Claude opus-4-7)
- [x] Step 3 — Dry-run review (user approved all 10)
- [x] Step 4 — Apply to live site (10/10 success)
- [x] Step 5 — Verify + update tracker (10/10 live)

### Batch 1 Results
- 10/10 pages now have new title + meta on production (verified via HTML fetch)
- Tokens used: 2,782 input + 2,096 output (~$0.10 Claude cost)
- Baseline preserved in baseline.json for rollback
- applied.json and verify.json contain full audit trail

## Batch 2 (remaining 25 content_upgrade_candidates)

- [x] Step 1 — Fetch baseline for 25 slugs → baseline_batch2.json (25/25 ok)
- [x] Step 2 — Generate proposals via Claude opus-4-7 → proposals_batch2.json (21/25 initially valid, 4 metas padded to 140+ chars → 25/25 valid)
- [x] Step 4 — Apply to live site → applied_batch2.json (25/25 write OK, flow pre-approved so Step 3 skipped)
- [x] Step 5 — Verify live HTML with `?nocache=` → verify_batch2.json (24/25 live-verified)
- [x] Step 6 — Update progress.md + MEMORY.md

### Batch 2 Results
- 25/25 writes to WordPress via `wp-seo-meta.php` bridge succeeded
- 24/25 verified on production (new title + meta in `<head>` with cache-bust)
- 1/25 page not live-verifiable: `candy-australia-guide-2026` (post_id 70353) is in `draft` status and its pretty URL 301-redirects to `best-candy-australia-2026` (a newer version of the same topic). The DB write still landed on the draft post, so if the draft is ever re-published the new meta will apply. Recommend leaving as-is (redirect is intentional).
- Tokens used: 7,466 input + 4,530 output (~$0.30 Claude cost — single batch call)
- Baseline preserved in baseline_batch2.json for rollback

## Combined (batches 1 + 2)
- 35/35 content_upgrade_candidate pages now have new SEO title + meta
- 34/35 verified live
- Total LLM cost: ~$0.40

## Key changes (both batches)
- 11 pages had generic "Compare stock options / buying factors / best next steps" boilerplate meta — all replaced with specific product names, counts, brand mentions
- Several batch-1 titles >60c were trimmed; all batch-2 titles generated within 45-58c
- All new metas include "Free Shipping $80+" (or "over $80") CTA hook (brand USP) where it fits naturally
- Listicle slugs now carry specific counts (e.g. "20 Best Candy & Lollies", "15 Iconic Australian Candy Brands", "12 Best Candy for Kids"); question-intent slugs answer the question in-title ("Are Jolly Ranchers Halal? Ingredients Checked 2026").

## Follow-up (not in this task)
- 2026-05-01: Re-check GSC CTR lift (14-day window) across all 35 pages
- 33 approved low-quality pages (H1=0, word count low) still need body regeneration — tracked separately
- Consider body-content refresh for pages still stuck at position 5-10 after 14 days

## Recovery
Batch 1 + Batch 2 complete. For a redo of specific slugs: modify proposals_batch2.json and re-run /tmp/batch2_step4_apply.py (or snapshotted step scripts at .ai/tasks/seo-title-meta-rewrite/).
