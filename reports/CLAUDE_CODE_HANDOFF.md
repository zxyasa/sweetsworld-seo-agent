# SweetsWorld SEO Agent Handoff For Claude Code

Date: 2026-03-17
Repo path: /Users/michaelzhao/agents/agents/sweetsworld-seo-agent
Project status: Step 10 / 11 in progress
Current decision: HOLD

## 1. Project goal
This repo is being evolved into a slow-rollout SEO MVP for SweetsWorld.
The current goal is not scale. The current goal is to prove that the page system can:
- generate intent-correct pages
- publish safely without duplicates
- enter sitemap correctly
- avoid technical SEO regressions
- begin receiving GSC impression and query-fit signals

Only after that should the project move into broader AI generation, authority work, and scheduler automation.

## 2. Current rollout state
Published pilot pages:
- https://sweetsworld.com.au/where-to-buy/white-knight-chocolate-where-to-buy-australia/
- https://sweetsworld.com.au/candy-guides/fantales-lollies-buying-guide/

Approved but intentionally unpublished:
- are-jolly-ranchers-halal

The current gate decision is HOLD because:
- only 2 pilot pages are published
- pilot target range is 3-5 published pages before expansion
- GSC currently shows 0 impressions and 0 clicks
- technical health is clean, so the blocker is data, not implementation

## 3. Most important current files
Read these first when resuming:
- reports/CURRENT_CHECKPOINT.md
- reports/seo_dashboard.md
- reports/pilot_gate.md
- reports/pilot_gate.json
- data/page_registry.json
- data/internal_links.json
- data/pilot_exit_criteria.json

Core workflow files:
- src/run_mvp.py
- src/content_brief_engine.py
- src/content_generator.py
- src/product_selector.py
- src/wp_client.py
- src/export_pilot_samples.py
- src/approve_pilot_samples.py
- src/backfill_registry_from_wp.py
- src/reclassify_newcastle_posts.py
- src/internal_link_engine.py
- src/ranking_monitor.py
- src/analytics_engine.py
- src/pilot_gate.py

## 4. What has already been completed
Step 1:
- Duplicate-safe daily publishing flow exists.
- run_mvp.py has state handling and duplicate prevention.

Step 2:
- topics.csv auto-generation support exists.
- topic_generator.py can replenish topics.

Step 3:
- macOS launchd support exists.
- scripts/run_daily_seo.sh and install/uninstall helpers are present.

Step 4:
- The roadmap was explicitly narrowed into a slow, quality-first MVP.

Step 5:
- Guardrail schemas exist:
  - data/page_registry.json
  - data/keyword_page_map.json
  - data/pilot_exit_criteria.json

Step 6:
- Page registry and keyword ownership checks are wired into publishing.
- Product matching is deterministic and rule-based.
- Product recommendations are omitted when no safe match exists.

Step 7:
- content_brief_engine.py exists and drives structure.
- Content now uses brief-driven intro, sections, FAQ, CTA, and internal links.

Step 8:
- Pilot sample export exists.
- A real WooCommerce catalog was synced into data/products.json.
- Sample packs were generated for:
  - white-knight-chocolate-where-to-buy-australia
  - fantales-lollies-buying-guide
  - are-jolly-ranchers-halal

Step 9:
- Internal-link anchor variation exists.
- Limited pilot publish was completed.
- Category routing was fixed so new SEO pages no longer default to Newcastle.
- Existing Newcastle-tagged posts were reclassified.
- Sitemap refresh was confirmed and correct URLs are now in sitemap.

Step 10:
- Weekly monitoring now exists.
- reports/seo_dashboard.md is generated from live checks.
- reports/pilot_gate.md and reports/pilot_gate.json turn the dashboard plus criteria into an explicit hold-or-expand decision.

## 5. Current technical health
Current live pilot technical status is good:
- HTTP 200 on both live pilot pages
- canonical is correct
- noindex is false
- H1 count is 1
- both pages are present in post-sitemap.xml

Important fix already made:
- content_generator.py used to emit an extra H1 inside article HTML
- that caused H1 count = 2 on published pages
- the extra H1 was removed
- both live pilot pages were backfilled so the fix is already live, not just future-only

## 6. Category and URL cleanup already done
Problem:
- new pages were initially landing under /newcastle/
- this was wrong because WordPress default category was being applied implicitly

Fixes already completed:
- guide_page and occasion_page route to Candy Guides
- landing_page routes to Where to Buy
- category_page target is Products
- Where to Buy category was created
- Newcastle category was emptied

Important result:
- old /newcastle/ URLs were removed from current post sitemap
- current relevant URLs are correct

## 7. Live site classification state
Current top relevant categories include:
- Candy Guides
- Where to Buy
- Trending
- Chocolate
- Easter (child of Chocolate)
- Tik Tok

Newcastle category count is now 0.

## 8. Pilot content specifics
white-knight-chocolate-where-to-buy-australia
- page_type: landing_page
- status: published
- URL: https://sweetsworld.com.au/where-to-buy/white-knight-chocolate-where-to-buy-australia/
- Notes: existing published post was found and synchronized rather than re-created

fantales-lollies-buying-guide
- page_type: guide_page
- status: published
- URL: https://sweetsworld.com.au/candy-guides/fantales-lollies-buying-guide/
- Notes: substitute-guide logic was tightened before approval and publishing

are-jolly-ranchers-halal
- page_type: guide_page
- status: approved, not published
- sample path: pilot_samples/are-jolly-ranchers-halal/
- Notes: halal-intent wording was tightened, retail-first product ordering was added, but publishing is intentionally held until the GSC gate improves

## 9. Jolly Ranchers sample details
This sample was revised because the earlier version was too generic.
The improved version now:
- focuses on ingredients, gelatine, labelling, and market-specific formula uncertainty
- avoids pretending to certify halal status
- prefers smaller retail SKUs instead of bulk-first ordering
- uses collection + product links as references, not proof of suitability

Important related changes:
- content_brief_engine.py gained suitability-guide logic for halal, vegan, kosher, gelatine, ingredients, gluten, and allergen style queries
- product_selector.py now prefers retail/smaller packs for these informational guide queries
- content_generator.py now uses a better guide-page product heading: Relevant Products to Inspect

## 10. Monitoring and decision layer
Monitoring scripts:
- src/ranking_monitor.py
- src/analytics_engine.py
- src/pilot_gate.py

Outputs:
- reports/seo_dashboard.md
- reports/pilot_gate.md
- reports/pilot_gate.json

Current pilot gate result:
- decision: hold

Current blocking reasons:
- published pilot count is 2, below expected 3-5
- no GSC impression signal yet
- no GSC click/query-fit signal yet

Current positive signals:
- manual QA complete enough for current samples
- no technical blockers on published pilot pages
- no duplicate publish issue detected
- one approved page is queued and ready if the gate opens

## 11. Internal link graph state
Internal link export now exists in:
- data/internal_links.json

Current export includes 3 records:
- white-knight-chocolate-where-to-buy-australia (published)
- fantales-lollies-buying-guide (published)
- are-jolly-ranchers-halal (approved)

The graph currently captures category, collection, and product links from approved/published briefs.

## 12. Commands that matter right now
Rebuild dashboard:
- .venv/bin/python src/analytics_engine.py --days 7 --output reports/seo_dashboard.md

Rebuild pilot gate:
- .venv/bin/python src/pilot_gate.py --days 7 --json-output reports/pilot_gate.json --md-output reports/pilot_gate.md

Re-export internal links:
- .venv/bin/python src/internal_link_engine.py

Re-export one sample:
- .venv/bin/python src/export_pilot_samples.py --slug are-jolly-ranchers-halal

Approve a sample without publishing:
- .venv/bin/python src/approve_pilot_samples.py are-jolly-ranchers-halal --status approved --note "..."

Targeted publish of a specific approved slug:
- .venv/bin/python src/run_mvp.py --slug are-jolly-ranchers-halal --only-approved --publish-created

Backfill WP metadata into registry:
- .venv/bin/python src/backfill_registry_from_wp.py --all-published --write
- .venv/bin/python src/backfill_registry_from_wp.py white-knight-chocolate-where-to-buy-australia

## 13. Important constraints and guardrails
Do not expand page volume yet.
Do not enable broader AI generation yet.
Do not enable scheduler-driven rollout expansion yet.
Do not start authority automation yet.

Reason:
- the MVP gate is intentionally conservative
- the system is technically stable but not yet validated by discovery/ranking data
- scaling before GSC signal appears would amplify an unproven template system

## 14. What should happen next
The next correct move is NOT more publishing.
The next correct move is:
1. wait for more time/data
2. regenerate reports
3. check if impressions appear
4. check if queries match intended page intent
5. only then decide whether to publish are-jolly-ranchers-halal

If GSC starts showing impressions and query-fit on the two live pilot pages, then the approved Jolly Ranchers page is the next page to consider publishing.

## 15. Reminder already scheduled
A real reminder has already been scheduled on mac-studio:
- system: at
- queue id: 1
- trigger time: 2026-03-24 15:10:00 AEDT

The reminder is meant to bring the operator back to:
- reports/seo_dashboard.md
- reports/pilot_gate.md
before publishing anything else.

## 16. Resume recommendation for Claude Code
When resuming, Claude Code should do this first:
1. read reports/CURRENT_CHECKPOINT.md
2. read reports/seo_dashboard.md
3. read reports/pilot_gate.md
4. read data/page_registry.json
5. decide whether the gate is still hold

Only if the gate has genuinely improved should it consider publishing are-jolly-ranchers-halal.

If no GSC improvement is present, Claude Code should keep the system in hold state and avoid adding broader automation.
