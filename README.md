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

## Database

Results are stored in `tryka.db` (SQLite). Tables:

- `events` — race name and division per event ID
- `results` — per-athlete/team result: bib, gym affiliate, age group, gender, ranks, time, penalties
- `raw_splits` — raw checkpoint splits (time of day, elapsed, diff)
- `refined_splits` — processed splits (time, place per segment)

`members` is a JSON array to support both solo athletes and teams.
