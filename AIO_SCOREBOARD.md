# Sweetsworld AIO Scoreboard

This is a local measurement system. It does not edit WordPress, products,
schema, feeds, pages, or any other production website state.

## What it measures

- 30 Australian shopping-intent prompts across gifts, dietary needs, bulk and
  party buying, imported candy, and city/delivery intent.
- OpenAI Responses API with web search, labelled
  `responses_web_search_api`.
- Gemini API with Google Search grounding, labelled
  `gemini_grounding_api`.
- Brand mentions, recommendation heuristic, Sweetsworld domain/product
  citations, recommendation position, competitor mention share of voice,
  latency, token usage, errors, and raw evidence.

These API surfaces are not the ChatGPT consumer UI or Google AI Overviews.
Results from one surface must not be presented as results from another.

## Safe operation

The probe command defaults to a dry-run:

```bash
.venv/bin/python scripts/aio_probe.py --replicates 2
```

It prints the planned call count and writes no observations. Live provider
requests require the explicit flag:

```bash
.venv/bin/python scripts/aio_probe.py --live --replicates 2
```

Required environment variables are `OPENAI_API_KEY` and either
`GEMINI_API_KEY` or `GOOGLE_API_KEY`. The loader reads the central registry at
`~/agents/.secrets/keys.env` first, then allows project/site `.env` files and
the process environment to override it. Models can be pinned with
`AIO_OPENAI_MODEL` and `AIO_GEMINI_MODEL`.

Generate a local JSON and Markdown report after a live run:

```bash
.venv/bin/python scripts/aio_report.py
```

Add `--telegram` only when the summary should actually be sent. This requires
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

## Scheduling

`deploy/launchd/com.sweetsworld.aio-scoreboard.weekly.plist` is a prepared
weekly definition. It is intentionally not installed by this task. Its wrapper
uses two replicates by default; override with `AIO_REPLICATES` or
`AIO_PROVIDERS` before installation.

## Data and interpretation

Observations are appended to `sites/sweetsworld/data/site.db`; raw JSON evidence
is stored under `sites/sweetsworld/data/aio_raw/`. Reports are written to
`reports/aio/`.

The recommendation flag is a conservative, deterministic text-window
heuristic, so raw evidence should be reviewed for important decisions. Rates
include numerators, denominators, and 95% Wilson intervals. Comparisons are
reported only when a prior run exists.
