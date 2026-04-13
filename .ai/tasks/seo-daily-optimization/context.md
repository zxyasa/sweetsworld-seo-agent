# Context: seo-daily-optimization
Last updated: 2026-03-16T05:05:12Z

## Key Files (ONLY read these on resume)
- src/run_mvp.py
- src/content_brief_engine.py
- src/content_generator.py
- src/export_pilot_samples.py
- src/sync_product_catalog.py
- src/product_selector.py
- src/topic_generator.py
- src/config.py
- src/wp_client.py
- data/products.json
- data/product_substitutions.json
- data/page_registry.json
- data/keyword_page_map.json
- data/pilot_exit_criteria.json
- pilot_samples/manual_qa_checklist.md
- pilot_samples/manual_qa_notes.md
- pilot_samples/summary.json
- scripts/run_daily_seo.sh
- scripts/install_launchd.sh
- scripts/uninstall_launchd.sh
- .env.example
- README.md
- .ai/tasks/seo-daily-optimization/plan.md

## Architecture Notes
- Current system is a duplicate-safe daily publishing pipeline that still uses `topics.csv` as the immediate publishing queue.
- The repo roadmap uses SWEETSWORLD AUTONOMOUS SEO FACTORY as the umbrella architecture, but execution is now explicitly MVP-first.
- Five architecture layers: Data Layer, Intelligence Layer, Content Generation Layer, Publishing Layer, Growth Layer.
- Core factory modules: Keyword Universe, Content Brief Engine, Programmatic Page Generator, Internal Link Graph, Authority Engine, Analytics Engine.
- Factory loop: keyword discovery -> SERP analysis -> content briefs -> AI content generation -> programmatic page generation -> internal linking -> publishing -> authority building -> analytics.
- Current repo paths are still `src/` and `scripts/`; the user architecture's `engines/` and `scheduler/` should be treated as target logical modules, not a required immediate rename.
- Keyword Universe V2 should replace ad hoc topic seeding with a structured keyword source of truth in `data/keywords_master.csv`.
- `src/content_brief_engine.py` produces a lightweight brief with `brief_id`, `search_intent`, `meta_description`, `intro`, `sections`, `faq_items`, `internal_links`, `related_keywords`, `selected_products`, and `cta`.
- The brief engine now rewrites awkward guide and landing phrasing into more natural copy, including `where to buy` and `whether X are/is ...` style wording.
- `src/run_mvp.py` and `src/export_pilot_samples.py` now share the same improved page-type inference rules: `where to buy` in the primary keyword becomes `landing_page`, explicit guide-style titles can remain `guide_page`, and question-style keywords like `are ... halal` become `guide_page`.
- `src/run_mvp.py` creates and saves a brief under `content_briefs/` before rendering HTML, and it persists `brief_id` into `data/page_registry.json`.
- `src/content_generator.py` accepts an optional `content_brief` and uses it to drive sections, FAQ, CTA, internal-link suggestions, excerpt text, and selected-product rendering.
- Step 8 now includes `src/export_pilot_samples.py`, a draft-only exporter that reads `topics.csv`, infers page type, applies deterministic product matching, builds a brief, and writes `page.html`, `excerpt.txt`, `topic.json`, and `*_brief.json` under `pilot_samples/<slug>/`.
- Step 8 also includes `src/sync_product_catalog.py`, which pulls the public WooCommerce Store API and normalizes products into `data/products.json`.
- `data/products.json` now exists and currently contains 1503 normalized live products from the public store API.
- `src/product_selector.py` now decodes HTML entities and is stricter about generic terms like `lollies`, `where`, `options`, and `ingredients` so it does not invent relevance from weak tokens.
- Current pilot sample state:
  - `white-knight-chocolate-where-to-buy-australia` -> `landing_page` with 4 matched products.
  - `fantales-lollies-buying-guide` -> `guide_page` with 0 matched products, preferred over irrelevant generic matches.
  - `are-jolly-ranchers-halal` -> `guide_page` with 4 matched Jolly Rancher products.
- `pilot_samples/manual_qa_checklist.md` defines the human review gate before anything should move toward `approved` or `published`.
- `pilot_samples/manual_qa_notes.md` records the first QA pass and the current product-match outcomes.
- Category pages and landing pages must remain intent-distinct; do not merge them into one generic template.
- `src/run_mvp.py` infers a page type for each topic and checks `data/keyword_page_map.json` before creating or publishing content.
- `src/run_mvp.py` writes/updates `data/page_registry.json` for discovery, draft, publish, block, and existing-page outcomes.
- Auto-publish is gated by registry state: a topic must already be marked `approved` before an existing draft or newly created draft can be published.
- Internal links now have anchor-text variation in exported briefs and HTML, and target selection is now driven by category hints plus selected-product URLs. For guide pages, representative retail product links are preferred over wholesale SKUs. Limited approved publishing still remains Step 9 work.
- Authority Engine V1 and full scheduler automation remain later-phase work after the page MVP proves quality.

## Recent Changes Summary
Step 8 now has a real product catalog, real deterministic product matching, and a stronger manual QA loop. The latest precision pass tightened branded-query matching so White Knight now resolves to 1 exact product instead of a broad shortlist. The remaining work inside Step 8 is mainly human approval: decide whether the current sample pages are strong enough to approve for a limited pilot, or whether the templates still need another refinement pass before Step 9.

## Search Hints
- Search for `infer_page_type`, `build_content_brief`, `save_content_brief`, and `content_briefs_dir` in `src/run_mvp.py`.
- Search for `_subject_phrase`, `_guide_topic_phrase`, `_build_intro`, and `_build_faq_items` in `src/content_brief_engine.py`.
- Search for `_render_sections`, `_render_brief_links`, `_render_brief_faq`, and `_render_brief_cta` in `src/content_generator.py`.
- Search for `main`, `export_sample`, and `QA_CHECKLIST` in `src/export_pilot_samples.py`.
- Search for `main`, `fetch_products`, and `normalize_product` in `src/sync_product_catalog.py`.
- Search for `STOPWORDS`, `_topic_tokens`, and `select_products_for_topic` in `src/product_selector.py`.
- The next implementation choice is inside Step 8: either tighten product precision one more round, or manually approve one or two sample packs so Step 9 can start on anchor variation and limited approved publishing.
