# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`tryka-scraper` scrapes race results from `tryka.r.mikatiming.com` (a Mikatiming-hosted results site for Tryka events) and stores them in a local SQLite database.

## Architecture

- **`scraper.py`** — entry point; orchestrates fetching, iterates events and athletes, handles pagination and retries
- **`parser.py`** — HTML parsing logic using BeautifulSoup; extracts athlete/team data from list and detail pages
- **`db.py`** — SQLite layer; connects, runs schema migrations on connect, and provides upsert/insert helpers
- **`schema.sql`** — database schema; auto-applied on every `db.connect()` call using `CREATE IF NOT EXISTS`

## Database Schema

Four tables: `events`, `results`, `raw_splits`, `refined_splits`. `members` is stored as a JSON array (solo or team). Gender is inferred from the list-page sex filter (`M`/`W`/`X`).

## Domain notes

- **Series.** Races are grouped into series, stored as `events.series`. Series 1 is the six races from Autumn 1 to Lisbon 6, now served under `/series-1/`. Series 2 started with Dublin Series 2 Race 1 and is served at the site root. Each series' base URL is in `SERIES_BASE_URLS`. To add a race, append its event IDs to that series' `SERIES_<n>_EVENT_IDS` list in `scraper.py`.

- **Division renames.** Some divisions were renamed across races but are the *same* competitive event and must be treated as one cohort in any cross-race analysis. Known aliases:
  - `TRYKA DOUBLES PRO` (Autumn 1, Winter 2) → renamed to `TRYKA PRO DOUBLES` (Spring 3 onward). Canonical name: `TRYKA PRO DOUBLES`.
  - Canonical division-alias map lives in `sled_variance.py` (`DIVISION_ALIASES`); add new aliases there so analyses stay consistent.
- **Open 500 / 800 gender restructure.** In Autumn 1 (Race 1), the women's Open 500 and Open 800 ran as their *own separate divisions* on the Sunday, distinct from the men's Saturday Open. From Winter 2 (Race 2) onward they were folded into single combined `TRYKA OPEN 500` / `TRYKA OPEN 800` divisions holding both genders (gender still recorded per athlete). The Autumn 1 women's events are `T5_5GGDDHUF16` (Open 500) and `T8_5GGDDHUF16` (Open 800) — already in `ALL_EVENT_IDS` and already stored (183 and 228 rows, gender W), and they map to division `TRYKA OPEN 500` / `TRYKA OPEN 800`. **Gotcha:** the organiser published these Sunday events with finish times and station splits but **no Overall Rank** (the source rank field is blank), so every row has `rank_overall = NULL`. Any analysis that gates finishers on `rank_overall IS NOT NULL` will silently drop all ~411 Autumn-1 Open women. `sled_variance.py` handles this via `UNRANKED_BUT_VALID_DIVISIONS`, admitting these divisions on the strength of a complete 8-station record instead.

## Running

```bash
pip3 install -r requirements.txt

python3 scraper.py                          # scrape all known events
python3 scraper.py --db custom.db           # use a different DB file
python3 scraper.py --event TD8_5GGDDHUF41  # scrape a single event
python3 scraper.py --dry-run               # list events + athlete counts only
```

## Testing & CI

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/pytest
```

- `tests/test_parser.py` and `tests/test_db.py` are unit tests. `tests/test_e2e_scrape.py` runs `scraper.main()` end to end against recorded HTML and checks the resulting DB.
- `tests/conftest.py`'s `replay_fetch` serves `scraper.fetch` from `tests/fixtures/html/` (keyed by series + params, see `tests/fixture_store.py`) and blocks real HTTP.
- **Never add CI or scheduled jobs that hit the live site.** Only re-record fixtures by hand with `tests/record_fixtures.py`, and only when the HTML changes.
- If a parser change needs new fixture pages, re-record them and update the expected values in the tests.
- `main` is protected by a ruleset: every change goes through a PR and the `ci` check must pass. **Always branch and open a PR; never push to main.**

## Dependencies

`requests`, `beautifulsoup4` — see `requirements.txt`.
