# Change Log

All code, config, content, and manual WordPress operations that affect this project should be recorded here.

Recommended command:

```bash
.venv/bin/python scripts/log_change.py \
  --type manual \
  --scope "Rank Math sitemap" \
  --summary "Refreshed sitemap index" \
  --details "post-sitemap.xml lastmod updated and previously missing URLs returned"
```

Entries are appended in chronological order.

## 2026-04-05T16:07:28+10:00 | manual | Rank Math sitemap
- Actor: operator+codex
- Summary: Recovered stale post sitemap refresh
- Details: post-sitemap.xml refreshed after WordPress sitemap save/cache refresh and previously missing published URLs returned
- Verification: Live sitemap_index.xml now shows post-sitemap.xml lastmod 2026-04-05T00:30:27+00:00 and 40/40 previously missing URLs are present in post-sitemap.xml

## 2026-04-05T16:07:28+10:00 | code | change recording
- Actor: codex
- Summary: Added repository change log workflow
- Details: Added CHANGELOG.md, scripts/log_change.py, and README instructions so future changes are recorded in a consistent format
- Verification: scripts/log_change.py appended structured markdown entries to CHANGELOG.md

## 2026-04-05T16:12:13+10:00 | code | newcastlehub launchd
- Actor: codex
- Summary: Fixed broken install_launchd path resolution
- Details: Updated sites/newcastlehub/install_launchd.sh to compute REPO_DIR explicitly and chmod the real scripts/run_daily_seo_newcastlehub.sh path
- Verification: bash -n sites/newcastlehub/install_launchd.sh passed and install script completed successfully

## 2026-04-05T16:12:13+10:00 | manual | newcastlehub auto posting
- Actor: operator+codex
- Summary: Reinstalled missing daily launchd job
- Details: Installed ~/Library/LaunchAgents/com.newcastlehub.seo-agent.daily.plist and loaded com.newcastlehub.seo-agent.daily to restore scheduled daily runs
- Verification: launchctl list now includes com.newcastlehub.seo-agent.daily and the plist exists under ~/Library/LaunchAgents

## 2026-04-05T16:15:10+10:00 | config | newcastlehub auto posting
- Actor: operator+codex
- Summary: Restored auto_publish for scheduled daily runs
- Details: Changed sites/newcastlehub/site.json publish.auto_publish from false to true so the daily launchd job publishes approved content instead of stopping at draft mode
- Verification: site.json passed JSON validation after the update

## 2026-04-05T16:16:30+10:00 | manual | newcastlehub auto posting
- Actor: operator+codex
- Summary: Ran daily job manually and verified successful publish
- Details: Executed scripts/run_daily_seo_newcastlehub.sh after restoring launchd and auto_publish; the run published a new article at https://newcastlehub.info/free-business-audit-newcastle/
- Verification: newcastlehub-daily.log shows publish success, cache warm, distribution to facebook/instagram/gbp/pinterest, Telegram notification, and exit status 0

## 2026-04-05T16:20:23+10:00 | code | newcastlehub GSC
- Actor: codex
- Summary: Separated GSC credentials from Indexing API enable flag
- Details: Updated src/run_mvp.py so multi-site GSC credentials always come from SiteContext when available, while Google Indexing API submission is gated separately by indexing_api_enabled and optional indexing_credentials_file
- Verification: python3 -m py_compile src/run_mvp.py passed and a follow-up newcastlehub daily run no longer emitted the empty-path GSC warning

## 2026-04-05T16:20:23+10:00 | manual | newcastlehub GSC
- Actor: operator+codex
- Summary: Verified GSC initialization after code fix
- Details: Ran scripts/run_daily_seo_newcastlehub.sh after the fix; the job initialized Google Search Console successfully and then exited because the daily quota for 2026-04-05 had already been reached
- Verification: newcastlehub-daily.log shows 'INFO: Google Search Console enabled' followed by 'Daily quota already reached. Nothing to do.' with status 0

## 2026-04-05T16:22:30+10:00 | manual | sweetsworld pilot gate
- Actor: operator+codex
- Summary: Regenerated pilot report after sitemap recovery
- Details: Manually reran src/pilot_gate.py with --notify after the sitemap issue was fixed later in the day, because the daily monitor had already run at 10:00 and would not auto-refresh the report again until the next day
- Verification: reports/pilot_gate.json regenerated at 2026-04-05T06:06:18+00:00 with decision=expand, technical_blockers=0, impressions=10005, clicks=60

## 2026-04-05T16:23:26+10:00 | code | pilot gate notification
- Actor: codex
- Summary: Added site domain to all pilot gate Telegram headers
- Details: Updated src/telegram_notify.py so expand and generic daily-report pilot gate messages include the configured site domain suffix, matching the GSC signal header format
- Verification: python3 -m py_compile src/telegram_notify.py passed

## 2026-04-05T16:29:28+10:00 | manual | newcastlehub monitor
- Actor: operator+codex
- Summary: Installed and verified daily SEO Pilot Gate reporting for newcastlehub
- Details: Installed com.newcastlehub.seo-agent.monitor, ran scripts/run_daily_monitor_newcastlehub.sh manually, and generated site-specific reports under sites/newcastlehub/reports/
- Verification: logs/newcastlehub-monitor.log shows a successful run with pilot_gate outputs written at 2026-04-05 16:28 and no Telegram warning was emitted

## 2026-04-05T16:29:28+10:00 | code | newcastlehub monitor
- Actor: codex
- Summary: Added site-specific monitor pipeline for newcastlehub
- Details: Made analytics_engine and pilot_gate honor SiteContext environment, extended scripts/run_daily_monitor.sh to accept a site ID, and added newcastlehub monitor wrapper plus launchd plist/installer
- Verification: py_compile passed for src/site_context.py, src/analytics_engine.py, and src/pilot_gate.py; bash -n passed for the new monitor scripts

## 2026-04-05T16:33:26+10:00 | code | pilot gate logic
- Actor: codex
- Summary: Made next-action dates dynamic and normalized redirected canonical URLs in monitoring
- Details: Updated ranking_monitor to use the final canonical URL for sitemap and GSC checks after clean redirects, and updated pilot_gate to generate a next-day absolute date instead of the stale hard-coded 2026-03-24 text
- Verification: python3 -m py_compile passed for src/ranking_monitor.py and src/pilot_gate.py

## 2026-04-05T16:35:03+10:00 | manual | newcastlehub pilot monitor
- Actor: codex
- Summary: Re-ran pilot gate after stale-date and redirect handling fixes
- Details: newcastlehub daily monitor now reports 0 technical blockers; next_action uses dynamic date 2026-04-06; hold remains due to only 2 published pages and no GSC impressions/clicks yet
