# Plan: seo-daily-optimization

## Steps
- [x] Step 1: Implement duplicate-safe daily SEO publishing workflow | Files: src/run_mvp.py, src/config.py, src/content_generator.py, src/wp_client.py, .gitignore | Risk: medium
- [x] Step 2: Implement automatic topic generation into topics.csv | Files: src/run_mvp.py, src/topic_generator.py, src/config.py | Risk: medium
- [x] Step 3: Add macOS launchd scheduling support and docs | Files: scripts/run_daily_seo.sh, scripts/install_launchd.sh, scripts/uninstall_launchd.sh, README.md, .env.example | Risk: low
- [x] Step 4: Extend roadmap into the layered Autonomous SEO Factory umbrella architecture | Files: .ai/tasks/seo-daily-optimization/plan.md, .ai/tasks/seo-daily-optimization/context.md, .ai/tasks/seo-daily-optimization/progress.md | Risk: low
- [x] Step 5: Define MVP guardrails, page taxonomy, and rollout gates | Files: .ai/tasks/seo-daily-optimization/plan.md, data/page_registry.json, data/keyword_page_map.json, data/pilot_exit_criteria.json | Risk: medium
- [x] Step 6: Build idempotent page state, deterministic product matching, and page-type-safe generation for the pilot | Files: src/run_mvp.py, src/product_selector.py, src/content_generator.py | Risk: high
- [x] Step 7: Build the SEO Content Brief Engine and stronger pilot templates | Files: src/content_brief_engine.py, src/content_generator.py, src/export_pilot_samples.py | Risk: high
- [x] Step 8: Generate a small draft-only sample set and manual QA checklist | Files: pilot_samples/, src/export_pilot_samples.py, src/sync_product_catalog.py | Risk: high
- [x] Step 9: Add internal link graph with anchor variation and publish a limited pilot batch | Files: src/internal_link_engine.py, src/run_mvp.py, src/wp_client.py, data/internal_links.json | Risk: high
- [ ] Step 10: Review weekly Search Console data and decide whether to expand page volume or page types | Files: reports/seo_dashboard.md, src/analytics_engine.py, src/ranking_monitor.py | Risk: medium
- [ ] Step 11: Add broader AI generation, authority engine, and scheduler automation only after pilot quality is proven | Files: src/content_generator.py, src/authority_engine.py, scheduler/task_scheduler.py | Risk: high

## Roadmap Notes
- Autonomous SEO Factory remains the umbrella architecture, but implementation is now explicitly MVP-first and slow-rollout.
- Primary near-term goal: prove the page system can be indexed, rank, and earn clicks before scaling volume.
- Five architecture layers: Data Layer, Intelligence Layer, Content Generation Layer, Publishing Layer, Growth Layer.
- Six core modules: Keyword Universe, Content Brief Engine, Programmatic Page Generator, Internal Link Graph, Authority Engine, Analytics Engine.
- Operating loop: discover keywords -> SERP analysis -> generate briefs -> generate content/pages -> internal linking -> publish -> build authority -> monitor rankings -> iterate.
- Current repo implementation lives under `src/`; the user architecture describes the same engines logically and may later be reorganized under `engines/` and `scheduler/`.
- Keyword Universe V2 should become the source of truth ahead of `topics.csv`.
- `keywords_master.csv` target fields: `keyword,cluster,intent,page_type,priority`.
- Required keyword families: Store / Brand, Candy Category, Buying Intent, Occasion, Location, Comparison, Guide, Programmatic.
- Initial programmatic rules: `best candy for + occasion`, `best + candy type`, `buy + candy type`, `top + candy type`.
- Product database target fields: `product_name,category,description,price,url`.
- Initial page types to generate from the keyword universe: `occasion_page`, `category_page`, `landing_page`.
- Programmatic pipeline target: keyword database -> page type detection -> template engine -> product matching -> content generation -> markdown output -> WordPress publishing.
- Content Brief Engine inputs: keyword database, SERP data, topic clusters.
- Content Brief target fields: `keyword,search_intent,page_type,title,meta_description,outline,sections,faq_questions,internal_links`.
- Content briefs should become the blueprint layer between keyword discovery and AI/page generation.
- Authority Engine should become the second growth engine beside the page engine, but only after the page MVP is validated.
- Analytics Engine target outputs: ranking, impressions, clicks, conversion, and SEO dashboard reporting.

## MVP Guardrails
- Do not start with large-scale publishing; begin with a small pilot batch only.
- Start in `draft-only` mode until sample pages are manually reviewed and approved.
- Maintain explicit publish state / idempotency so the same page cannot be auto-published twice.
- Product matching should be rule-based first; AI may assist, but must not be the sole selector.
- Page templates must be intent-specific; category pages and landing pages must not share ambiguous structure.
- Every pilot page must have meaningful structure, not thin filler text.
- Internal links must vary anchors; do not reuse identical anchor text everywhere.
- Weekly Google Search Console review is a rollout gate before expansion.
- Quality proof beats scale: do not expand to hundreds of pages before the template and link system are validated.

## Pilot Recommendation
- Start with one page family at a time, not all page types simultaneously.
- Generate 5 to 20 sample pages maximum in the first pilot.
- Manually review sample pages for intent match, product match, template quality, and link quality before publishing.
- Publish only a limited approved batch, then observe indexation, impressions, clicks, and query fit in GSC.
- Expand page count or add new page types only after the first pilot performs acceptably.

## Dependencies
- WordPress REST credentials in `.env`
- Optional OpenAI / Claude API credentials for richer generation
- WooCommerce product data or API access for product link insertion
- Google Search Console for keyword discovery and analytics outputs
- Future keyword discovery inputs: Google Suggest, GSC, later Ahrefs/Semrush
- Product catalog source for `data/products.json`
- SERP input source for `data/serp_data.json`
- Future authority inputs: influencer/contact datasets plus backlink data sources
- Google Analytics for analytics engine outputs
- Repo virtualenv for local execution
- launchd available on macOS for scheduled runs

## Estimated Token Budget
Total steps: 11 | High-risk steps: 6 | Recommend: complete Steps 5-10 before broader automation
