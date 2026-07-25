# Context — SweetsWorld AIO Scoreboard

## Key files

- `src/aio_visibility_monitor.py` — existing manual observation store and score API
- `tests/test_aio_visibility_monitor.py` — existing compatibility tests
- `src/site_db.py` — site-local database schema
- `agents/tg_agent/executor.py` — existing `aio_log`, `aio_report`, `aio_score` consumer (outside initial write scope)
- `apps/growth-graph/src/growth_graph/command_center.py` — reads `get_aio_score()`; remediation is disabled

## Current evidence

- `data/aio_observations.db`: 0 observations
- `sites/sweetsworld/data/site.db`: 0 AIO observations
- Existing 40 monitor tests pass under the monorepo root venv.

## Search hints

- OpenAI Responses web search exposes search sources and `url_citation` annotations.
- Gemini grounding exposes grounding chunks and support metadata.
- Provider API surfaces must not be presented as consumer-product measurements.

## Implemented files

- `src/aio_scoreboard.py` — append-only run and observation ledger
- `src/aio_probe_engines.py` — OpenAI/Gemini adapters and evidence analysis
- `src/aio_reporting.py` — Wilson intervals, surface metrics, SOV and prior-run deltas
- `scripts/aio_probe.py` — dry-run-by-default probe CLI
- `scripts/aio_report.py` — local JSON/Markdown report and explicit Telegram option
- `sites/sweetsworld/aio_query_basket.json` — versioned 30-query AU basket
- `deploy/launchd/com.sweetsworld.aio-scoreboard.weekly.plist` — prepared, not installed
- `AIO_SCOREBOARD.md` — operating and interpretation guide
