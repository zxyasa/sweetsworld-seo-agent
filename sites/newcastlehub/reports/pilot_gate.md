# Pilot Gate

- Generated at: `2026-07-23T00:30:23+00:00`
- Decision: **`hold`**
- Next action: Waiting for GSC impression signal on the 60 live pilot pages. Re-run pilot_gate after 2026-07-24 to check again.
- Dashboard source: `live`

- Published pilot pages: `60`
- Approved but unpublished pages: `0`
- QA pass rate: `1.0`
- GSC impressions: `0` | clicks: `0` | avg CTR: `0.0%` | avg position: `0.0`
- Pages with impressions: `0`
- Pages stuck at positions 5-10: `0`
- Content upgrade candidates: `0`
- GA4 sessions: `0` | avg bounce: `0%` | avg duration: `0.0s`
- GA4 pages with data: `0` | high bounce: `0` | low duration: `0`
- Technical blockers: `53`
- Dashboard issue pages: `58`
- Non-blocking technical warnings: `5`

## Checks

- `published_batch_within_expected_range`: `True`
- `manual_qa_complete`: `True`
- `no_technical_blockers`: `False`
- `no_orphaned_records`: `True`
- `search_console_review_available`: `False`
- `indexation_signal_present`: `False`
- `query_intent_fit_present`: `False`
- `ctr_meets_threshold`: `True`
- `engagement_acceptable`: `True`
- `approved_queue_available`: `False`
- `no_duplicate_publishes`: `True`

## Blocking Reasons

- technical blockers remain on published pilot pages after filtering soft warnings
- GSC review is required but GSC metrics are not available
- no GSC impression signal yet on the published pilot batch
- no GSC click/query-fit signal yet on the published pilot batch

## Technical Warnings

- `missing_from_post_sitemap`: `5` page(s)

## GSC Performance Analysis

- Average CTR: `0.0%` (threshold: `1.0%`; check inactive — need more impressions)
- Average position: `0.0`
- No content upgrade candidates identified.

## GA4 Behavior Analysis

- No GA4 data available. Set `GA4_PROPERTY_ID` and `GA4_CREDENTIALS_FILE` in `.env` to enable.

## Missing Backlinks

- None — all published pages link to each other

## Approved Queue

- None
