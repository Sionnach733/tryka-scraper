# tryka-scraper

Scrapes race results from [tryka.r.mikatiming.com](https://tryka.r.mikatiming.com/) and stores them in a local SQLite database.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scraper.py                          # scrape all known events
python scraper.py --db custom.db           # use a different DB file
python scraper.py --event TD8_5GGDDHUF41  # scrape a single event
python scraper.py --dry-run               # list events + athlete counts, no scraping
```

## Running on production

To fetch new/updated results into the production `tryka.db`, from the repo root on the
production host:

```bash
./update_prod.sh
```

This one command:

1. `git pull` — picks up any newly-added event IDs (e.g. a new race block in `scraper.py`)
2. Backs up `tryka.db` to `tryka.db.bak-<timestamp>` before touching anything
3. Runs `scraper.py` against every known event, logging output to `logs/fetch-<timestamp>.log`
4. Prints a before/after result-count summary

If the host's system Python is externally managed (e.g. recent Ubuntu/Debian, which
refuses a plain `pip install`), create a virtualenv once and `update_prod.sh` will use it
automatically whenever `.venv/` exists:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

It's safe to re-run any time — already-stored athletes are skipped, so running it again
(or daily, while a race is still posting results) only fetches what's new.

If a run is interrupted (e.g. a network blip), it's safe to just run `./update_prod.sh`
again — nothing is lost. Note that a full re-run after an interruption has to re-page
through every already-completed event's result list before reaching new data, which can
be slow for a mature database. For a fast, targeted resume instead, scrape just the
specific event(s) still missing data:

```bash
python3 scraper.py --event <EVENT_ID>
```

To watch progress from another terminal while a fetch is running:

```bash
watch -n 5 'sqlite3 tryka.db "select count(*) from results;"'
# or
tail -f logs/fetch-<timestamp>.log
```

## Database

Results are stored in `tryka.db` (SQLite). Tables:

- `events` — race name and division per event ID
- `results` — per-athlete/team result: bib, gym affiliate, age group, gender, ranks, time, penalties
- `raw_splits` — raw checkpoint splits (time of day, elapsed, diff)
- `refined_splits` — processed splits (time, place per segment)

`members` is a JSON array to support both solo athletes and teams.
