# Progress — SweetsWorld AIO Scoreboard

Started: 2026-07-18
Terminal: codex
Status: complete

- [x] Step 1/5 — Task record and non-website boundary
- [x] Step 2/5 — Append-only observation model
- [x] Step 3/5 — OpenAI/Gemini probes and query basket
- [x] Step 4/5 — Reports, Telegram formatting, local scheduler
- [x] Step 5/5 — Tests and offline dry-run

## Safety

No production website mutation is authorised by this task.

## Recovery notes

Completed. Full project result: 346 passed, 2 skipped. The 120-call weekly plan was dry-run only: no provider requests, no observation rows, no website changes, no scheduler installation, and no Telegram send. A future live baseline requires explicit `scripts/aio_probe.py --live` execution.

## Live smoke test — 2026-07-18

- OpenAI configuration present; Gemini/Google API key missing.
- First 2-call attempt was blocked by the local network sandbox and retained as failed run `644ebd9e-df9d-4d18-8fe9-b9fe5bd20d83`.
- Approved retry completed: run `f02ea12d-31ef-4a3f-a066-d83a9212d32a`, 2 successes, 0 errors.
- Result: 0/2 Sweetsworld mentions, 0/2 recommendations, 0/2 Sweetsworld domain citations.
- Local report: `reports/aio/20260718T122459Z_f02ea12d.md`.
- No website writes, scheduler installation, or Telegram send.
- Latest memory review found the central credential protocol at `~/agents/.secrets/`; the probe now loads that registry as its baseline. `GEMINI_API_KEY` is centrally registered.
- Central Gemini smoke run `fb103fcc-f8f7-4ef4-8723-83b638a078d6`: 2 successes, 0 errors; 1/2 brand mentions. Grounding used opaque Google redirect URLs, so source-title hostname attribution was added and unit tested.
- Post-fix Gemini run `d6b57023-d56e-43aa-bd85-1389459bac75`: 2 successes, 0 errors; 0/2 brand mentions. The variation confirms that repeated sampling is required. Competitor coverage was expanded and the basket was advanced to `2026-07-18.v2` for future runs.
- Five-cluster v2 baseline `ad279c51-57b0-400d-9efc-4cecacccb5c3`: 20/20 successful (5 prompts × 2 providers × 2 replicates). Gemini: mention/recommend/domain citation 30%/30%/30%. OpenAI: 30%/20%/60%; product citation 20%. Strongest cluster was imported American candy; Sydney local delivery produced no Sweetsworld mention or citation. Reports now compare only runs with the same basket version.
