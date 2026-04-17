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

## Running

```bash
pip3 install -r requirements.txt

python3 scraper.py                          # scrape all known events
python3 scraper.py --db custom.db           # use a different DB file
python3 scraper.py --event TD8_5GGDDHUF41  # scrape a single event
python3 scraper.py --dry-run               # list events + athlete counts only
```

## Dependencies

`requests`, `beautifulsoup4` — see `requirements.txt`.
