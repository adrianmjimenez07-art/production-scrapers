# production-scrapers

Patterns I use for **scrapers that don't break in production** — the part nobody
shows in tutorials. Built around Playwright for JS-heavy / login-walled sites,
with retries, polite rate-limiting, and structured output to SQLite.

## What's here
- `scraper.py` — a resilient base scraper: rotating user-agents, exponential-backoff
  retries, per-domain rate limiting, and idempotent upserts so re-runs never
  duplicate rows.
- Designed to run on a schedule (cron / launchd) and write into a database other
  systems read from.

## The hard parts it solves
- **JS-rendered content** → Playwright headless, wait-for-selector, not raw HTML.
- **Pagination & login walls** → session persistence + cursor tracking.
- **Getting blocked** → backoff, jitter, and UA rotation instead of hammering.
- **Dirty re-runs** → upsert on a natural key, so the same row never lands twice.

```bash
pip install -r requirements.txt
python scraper.py --url https://example.com/listings --out data.db
```

MIT licensed.
