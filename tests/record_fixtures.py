"""Record real HTML from the live results site for the offline tests.

Run by hand only, and sparingly: it fetches roughly 50 pages from the organiser's
site, with the scraper's normal delay between requests. CI never runs this.

    .venv/bin/python tests/record_fixtures.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import scraper  # noqa: E402
from fixture_store import (  # noqa: E402
    E2E_EVENTS,
    HTML_DIR,
    MANIFEST,
    PAGINATED_LIST,
    fixture_key,
    fixture_path,
)


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    for old in HTML_DIR.glob("*.html"):
        old.unlink()
    manifest: dict = {}
    real_fetch = scraper.fetch

    def recording_fetch(session, series, params):
        html = real_fetch(session, series, params)
        fixture_path(series, params).write_text(html, encoding="utf-8")
        manifest[fixture_key(series, params)] = {"series": series, "params": params}
        return html

    scraper.fetch = recording_fetch
    session = scraper.make_session()
    with tempfile.TemporaryDirectory() as tmp:
        conn = db.connect(str(Path(tmp) / "record.db"))
        for event_id in E2E_EVENTS:
            scraper.scrape_event(session, event_id, conn, verbose=True)
        conn.close()
    recording_fetch(session, *PAGINATED_LIST)

    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    size = sum(p.stat().st_size for p in HTML_DIR.glob("*.html"))
    print(f"\nRecorded {len(manifest)} pages ({size / 1024:.0f} KB) into {HTML_DIR}")


if __name__ == "__main__":
    main()
