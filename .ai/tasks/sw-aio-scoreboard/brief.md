# Brief — SweetsWorld AIO Scoreboard

## Goal

Build a local, read-only AIO visibility scoreboard for SweetsWorld that probes supported AI search APIs, stores immutable evidence, and produces statistically honest reports.

## Hard boundary

- No writes to WordPress, RankMath, WooCommerce, GMC, production databases, robots.txt, schema, products, pages, posts, or site files.
- No automatic remediation or publishing.
- External calls are limited to read-only AI/search API requests and Telegram notification.
- API keys remain in environment files and are never logged.

## Acceptance criteria

- Observations are append-only and retain repeated runs over time.
- Provider, surface, model, location, prompt version, replicate, citations, mentions, recommendation position, raw evidence hash, latency, usage, and error state are recorded.
- OpenAI and Gemini adapters support offline fixture tests and live execution only when explicitly requested.
- Reports separate provider surfaces; API probes are never labelled as consumer ChatGPT or Google AI Overview.
- Reports include sample sizes, citation rate, mention rate, recommendation rate, query coverage, competitor share of voice, and deltas where prior periods exist.
- All new tests pass without touching the production website.

