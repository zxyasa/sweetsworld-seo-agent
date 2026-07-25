# Plan — SEO Body Content Regeneration (25 stuck pages)

**Task name**: `seo-body-regen`
**Goal**: Lift 25 landing/guide pages from Google positions 5-10 to positions 1-4 (page-1 top half) by regenerating body content. Title/meta already fixed in sister task `seo-title-meta-rewrite`.
**Target**: +2 positions average, +30% CTR lift from rank, within 30 days.

---

## 1. Identification & Prioritization

Source: `reports/pilot_gate.json` → `gsc_performance.pages_stuck_detail` (25 entries, already filtered to pos 5-10).

**ROI scoring formula**:
```
roi_score = impressions * (11 - position) * (1 + 0.5 * has_recent_ctr_signal)
```

### Tier A — Do first (impressions ≥ 60, pos ≤ 8.5) — 6 pages
| # | slug | pos | imp | note |
|---|------|-----|-----|------|
| 1 | gluten-free-lollies-australia | 8.65 | 206 | highest impressions |
| 2 | best-lollies-for-party-bags | 8.32 | 139 | commercial intent |
| 3 | white-knight-chocolate-where-to-buy-australia | 9.33 | 95 | already converting (CTR 2.11%) |
| 4 | vegan-lollies-australia | 7.26 | 84 | category anchor |
| 5 | british-chocolate-australia | 6.10 | 80 | close to top 3 |
| 6 | korean-snacks-australia | 6.19 | 75 | close to top 3 |

### Tier B — Next (impressions 25-75, pos 5-10) — 8 pages
halal-candy-australia (6.13, 62), best-candy-for-kids-australia (5.61, 74), ferrero-rocher-australia (6.86, 44), best-candy-australia-2026 (6.61, 41), mothers-day-chocolate-australia (9.11, 28), fantales-lollies-buying-guide (10.56, 27), baby-shower-candy-australia (5.67, 18), rocky-road-australia (7.15, 13).

### Tier C — Long-tail (do only if A/B uplift confirmed) — 11 pages
nut-free-candy-australia, european-chocolate-australia, bulk-lollies-australia, fathers-day-candy-australia, engagement-party-lollies, are-jolly-ranchers-halal, candy-gift-box-australia, candy-australia-guide-2026, takis-australia, pick-and-mix-lollies-online, wedding-candy-australia.

**Sequencing**: Tier A → 14-day GSC observation gate → Tier B → 14-day gate → Tier C.

---

## 2. Content Strategy — Regen Recipe Per Page

Current pages: 4,663-6,896 chars (~750-1,200 words). Competitors: 1,800-3,000 words. Thesis: Google sees current pages as relevant but shallow.

**Mandatory additions**:
1. **Word count**: expand to 1,600-2,200 words (no padding — real informational blocks)
2. **Lead paragraph rewrite** (first 120 words): answer query in sentence 1
3. **Comparison table** (HTML `<table>`): 6-10 rows of products/brands with relevant columns
4. **FAQ section, 5-7 Q&A** with `FAQPage` JSON-LD (`content_generator._build_schema_json_ld` line 800)
5. **E-E-A-T expert tip block**: 1-2 short paragraphs attributed to named author
6. **Internal linking**: +3 to +5 contextual cluster links via `internal_link_engine.build_internal_link_graph`
7. **Outbound authority link**: 1 link to high-authority source (Coeliac Australia, Vegan Australia, brand official)
8. **Schema upgrades**: keep BreadcrumbList, add FAQPage, Article/ItemList, Product snippets
9. **Image alt text audit**: ≥3 images per page, descriptive alt with keyword variation

**Will NOT touch**: H1, title/meta, focus keyword, existing internal links (only ADD), featured image, slug, post_id

---

## 3. Technical Approach

### Script: `src/body_regen.py` (new, single file ~300 lines)

Don't reuse `run_mvp.py` (designed for new topic publishing — touches slug/category/products).

Flow per page:
```
1. wp_client.find_post_by_slug(slug) → current HTML + post_id
2. Parse HTML (BeautifulSoup): H1, intro, sections, links, images, schema
3. Preserve-list: H1 text, image tags, internal links, existing FAQ, BreadcrumbList
4. Fetch GSC query data (gsc_client.py)
5. Build regen prompt with preserve-list + GSC queries + word target + required blocks + site voice
6. LLM call → new HTML body
7. Post-process: inject FAQPage JSON-LD, verify preserve-list intact, run validate_content_quality()
8. Write preview to .ai/tasks/seo-body-regen/previews/<slug>.html
9. USER GATE → approve
10. wp_client.update_item_content('posts', post_id, new_html)
11. Save backup to .ai/tasks/seo-body-regen/backups/<slug>__<post_id>__<timestamp>.html
```

### LLM Choice
**Claude sonnet-4-6** for all 25 pages. Body regen is structured, sonnet handles well.
- Per page: 8k input + 4k output tokens ≈ $0.09
- Total: ~$2.25 (sonnet) + $0.50 (2 opus spot-checks) = **~$3**

### WP Write Path (verified)
`wp_client.update_item_content('posts', post_id, html_content)` — line 581-587 in `src/wp_client.py`.

### Preserve Critical Elements
Pre-LLM extract; post-LLM validate every preserved item still in new HTML. Single retry; second failure → skip + flag manual.

---

## 4. Dry-run / Staging

Three-stage review:
1. **Local preview**: HTML files in `previews/<slug>.html`, browser-openable, with diff stats header
2. **WP draft preview** (Tier A only): duplicate post as draft via `create_post_draft`, slug suffix `-regen-preview`. User clicks "Preview" in WP admin
3. **Live rollout**: per page, `update_item_content` + 30s sleep + screenshot for audit

---

## 5. Risk Mitigation

### Backup (MANDATORY before any write)
1. Save current HTML to `.ai/tasks/seo-body-regen/backups/<slug>__<post_id>__<timestamp>.html`
2. Save to `_seo_body_backup_20260417` post_meta via wp-seo-meta bridge
3. Only proceed with update if backup saved

### Rollback
```bash
.venv/bin/python src/body_regen.py --rollback --slug <slug>
```

### Per-page kill-switch
`.ai/tasks/seo-body-regen/kill_list.json` — add slug here to freeze it from regen runs.

### Quality gates (pre-write — reject if ANY fail)
- Word count outside 1,400-2,400
- Missing any preserved image tag
- Missing any preserved internal link href
- Missing or duplicate H1
- Forbidden phrases ("as an AI", "I cannot", "As of my knowledge cutoff")
- `content_generator.validate_content_quality()` returns False

### SERP safety: staged exposure
- Day 1: 2 Tier A pages → observe 48h
- If stable → remaining 4 Tier A pages
- Never >8 pages in single calendar day

---

## 6. User Gates

| Gate | After step | User action |
|------|-----------|-------------|
| G1 | 1-page sample | Review preview HTML, approve prompt quality |
| G2 | Tier A (6) previews generated | Approve batch for WP-draft preview |
| G3 | Tier A WP drafts live | Approve go-live |
| G4 | Tier A live 14 days, GSC delta reviewed | Approve Tier B start |
| G5 | Tier B live 14 days | Approve Tier C start |

---

## 7. Effort Estimate

| Phase | Engineering | Wall-clock |
|-------|-------------|-----------|
| Build `body_regen.py` | 3-4h | 1 day |
| Prompt eng + 1-page sample | 2h | 1 day |
| Tier A regen + review + live | 2h | 2 days (G2, G3) |
| Tier A 14-day observation | — | 14 days |
| Tier B regen + review + live | 2h | 2 days |
| Tier B 14-day observation | — | 14 days |
| Tier C regen + review + live | 2h | 2 days |
| Final 30-day report | 1h | 1 day |
| **Total** | **10-11h** | **~35 days** |

**LLM spend**: ~$3 total.

---

## 8. Success Measurement

### Baseline capture (before changes)
Per slug from GSC (28-day window ending 2026-04-18):
- avg position, impressions, clicks, CTR
- Save to `.ai/tasks/seo-body-regen/baseline_gsc.json`

### Primary metric
Position delta per page @ 30 days. Target: average ≥+2 across Tier A.

### Control group
5 untouched pages (similar pos/impressions). Compare delta to attribute lift.

### Reporting cadence
- Day 3: indexation check (URL inspection)
- Day 7: first position readings
- Day 14: Tier A gate decision
- Day 30: full report → rollback losers if any

---

## Top 3 Risks

1. **Rank loss on live pages** — Helpful Content volatility or losing relevancy signal we didn't identify. Mitigated by tiered rollout, full backup, 14-day gate, automated rollback.
2. **Preserve-list violations by LLM** — May drop image/link contributing to current rank. Mitigated by automated post-validation + retry + manual flag.
3. **Attribution contamination** — Title/meta rewrite for 10 pages landed 2026-04-17 today. Early CTR/rank deltas mix two interventions. Mitigated by 5-page untouched control group + waiting 14 days for title-only vs 30 days for body-regen.

---

## Critical Files for Implementation
- `src/wp_client.py` (update_item_content:581, find_post_by_slug:380, write_seo_meta_via_db:498)
- `src/content_generator.py` (validate_content_quality:1039, _build_schema_json_ld:800 for FAQPage/BreadcrumbList JSON-LD)
- `src/content_brief_engine.py` (build_content_brief, _build_internal_links — cluster link source)
- `src/gsc_client.py` (per-URL query data for regen prompt)
- `reports/pilot_gate.json` (source of truth for 25 stuck slugs + baseline)

---

## Step Breakdown (for progress.md)

```
Step 1/8 — Create task scaffold (brief, progress, context, baseline_gsc.json)
Step 2/8 — Build src/body_regen.py (fetch + preserve-extract + dry-run mode, no LLM)
Step 3/8 — Add LLM integration + prompt (sonnet-4-6 via anthropic client)
Step 4/8 — Generate 1-page sample (gluten-free-lollies-australia) → USER GATE G1
Step 5/8 — Tier A previews (6) → G2 → WP drafts → G3 → live
Step 6/8 — Wait 14d + GSC measurement → USER GATE G4
Step 7/8 — Tier B batch → G5 → Tier C batch
Step 8/8 — Final 30-day report + rollback losers
```
