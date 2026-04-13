# Progress: seo-daily-optimization
Last updated: 2026-03-17T03:40:00Z
Terminal: windows-vscode
Current step: 10 / 11

## Completed
- [x] Step 1: Implement duplicate-safe daily SEO publishing workflow
  - Added daily mode, local state tracking, CSV normalization, slug dedupe, safer SEO template generation, and runtime verification.
- [x] Step 2: Implement automatic topic generation into topics.csv
  - Added topic generation sources (auto, seed, gsc), CLI flags, CSV append helpers, and automatic queue replenishment before publishing.
- [x] Step 3: Add macOS launchd scheduling support and docs
  - Added daily runner/install/uninstall scripts and updated README/.env.example with automatic topic generation and scheduling instructions.
- [x] Step 4: Reframe the roadmap around a slow-rollout SEO MVP
  - Reorganized the future work around draft-only samples, manual QA, explicit publish state, deterministic product matching, intent-specific templates, anchor variation, limited pilot publishing, and weekly GSC review before scale.
- [x] Step 5: Start MVP guardrails in data/schema form
  - Added `data/page_registry.json`, `data/keyword_page_map.json`, and `data/pilot_exit_criteria.json` so the pilot has explicit lifecycle, keyword ownership, and expansion gates.
- [x] Step 6: Build idempotent page state, deterministic product matching, and safe page generation for the pilot
  - Integrated registry and keyword-ownership checks into `src/run_mvp.py`, added `src/product_selector.py` for rule-based catalog matching, and updated `src/content_generator.py` so product recommendations only appear when deterministic matches exist. If `data/products.json` is missing or no rule matches, the page is generated without product recommendations rather than inventing products.
- [x] Step 7: Build the content brief engine and stronger pilot templates
  - Added `src/content_brief_engine.py`, saved brief metadata into the page registry, generated JSON briefs under `content_briefs/`, and upgraded `src/content_generator.py` so page structure, FAQ, CTA, internal links, meta description, and product blocks can all be driven by the brief. Verified with `python3 -m py_compile` plus an offline render smoke test.
- [x] Step 8: Generate draft-only sample pages and complete manual QA
  - Added `src/export_pilot_samples.py` for draft-only sample export, synced a real WooCommerce catalog into `data/products.json` with `src/sync_product_catalog.py`, and exported pilot sample packs under `pilot_samples/`. The pilot sample set now includes `white-knight-chocolate-where-to-buy-australia`, `fantales-lollies-buying-guide`, and `are-jolly-ranchers-halal`, plus a manual QA checklist and notes.
- [x] Step 9: Add internal link variation and publish a limited approved batch
  - Internal-link anchor variation and link target selection now come from the brief layer, `guide_page` links prefer representative retail products, and a limited approved batch has been published safely. `white-knight-chocolate-where-to-buy-australia` and `fantales-lollies-buying-guide` are live, their category routing has been corrected away from `Newcastle`, the legacy `Newcastle` bucket has been fully reclassified, and sitemap refresh now shows the correct URLs. A lightweight `src/internal_link_engine.py` plus `data/internal_links.json` now export the current pilot link graph.

## Current
- [ ] Step 10: Review weekly Search Console data and decide whether to expand
  - Status: in progress
  - Notes: Two pilot pages are live and in the refreshed `post-sitemap.xml`: `white-knight-chocolate-where-to-buy-australia` and `fantales-lollies-buying-guide`. `are-jolly-ranchers-halal` remains `review_pending`. The next safe move is to monitor the published pilot batch instead of adding more pages, so the repo now needs a lightweight dashboard over the published registry records, live page health, sitemap presence, and optional GSC metrics.

## Remaining
- Step 10: Review weekly Search Console data and decide whether to expand.
- Step 11: Add broader AI generation, authority, and scheduler automation only after the pilot is validated.

## Recovery Notes
`src/run_mvp.py` now respects page-registry status and canonical keyword ownership, only auto-publishes when the registry status is already `approved`, and saves a `content_brief` before rendering content. `src/product_selector.py` now works against a real `data/products.json` catalog synced via `src/sync_product_catalog.py`, and it is stricter about generic terms like `lollies`. The published pilot batch has already been reclassified into stable category paths, the `Newcastle` category is empty, and live sitemap refresh has been verified. The next continuation point is `src/ranking_monitor.py` / `src/analytics_engine.py`, which should generate a small weekly dashboard before any further rollout.
