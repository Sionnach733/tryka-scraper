"""
Tryka Race Results Scraper
Scrapes all athlete results from tryka.r.mikatiming.com and stores in SQLite.

Usage:
    python scraper.py                     # scrape everything
    python scraper.py --db custom.db      # specify database path
    python scraper.py --event TD8_5GGDDHUF41  # scrape a single event
    python scraper.py --dry-run           # list events without scraping
"""

import argparse
import re
import sys
import time
from typing import Iterator

import requests
from bs4 import BeautifulSoup

import db
from parser import gender_from_division, parse_detail_page, parse_list_page


BASE_URL = "https://tryka.r.mikatiming.com/"
MEETING_ID = "5GGDDHUF2E"

# All known event IDs. Covers all 3 races across every division.
ALL_EVENT_IDS = [
    # Autumn Race 1 – Saturday
    "T5_5GGDDHUF15",
    "T8_5GGDDHUF15",
    "TD5_5GGDDHUF15",
    "TD8_5GGDDHUF15",
    "TDP_5GGDDHUF15",
    "TP_5GGDDHUF15",
    # Autumn Race 1 – Sunday
    "T5_5GGDDHUF16",
    "T8_5GGDDHUF16",
    "TD5_5GGDDHUF16",
    "TD8_5GGDDHUF16",
    "TR_5GGDDHUF16",
    # Winter Race 2
    "T5_5GGDDHUF30",
    "T8_5GGDDHUF30",
    "TD5_5GGDDHUF30",
    "TD8_5GGDDHUF30",
    "TR_5GGDDHUF30",
    "TCF_5GGDDHUF2E",
    "TDP_5GGDDHUF2F",
    "TP_5GGDDHUF2F",
    # Spring Race 3
    "T5_5GGDDHUF40",
    "T8_5GGDDHUF40",
    "TD5_5GGDDHUF41",
    "TD8_5GGDDHUF41",
    "TR_5GGDDHUF3F",
    "TCF_5GGDDHUF3F",
    "TDP_5GGDDHUF3F",
    "TP_5GGDDHUF3F",
    # Juniors (single meeting)
    "TK8_5GGDDHUF51",
    "TK10_5GGDDHUF51",
    "TK12_5GGDDHUF51",
    "TK14_5GGDDHUF51",
    "TK16_5GGDDHUF51",
]

REQUEST_DELAY = 0.5  # seconds between requests


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; tryka-scraper/1.0; "
                "+https://github.com/Sionnach733/tryka-scraper)"
            )
        }
    )
    return session


def fetch(session: requests.Session, params: dict) -> str:
    resp = session.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY)
    return resp.text


def get_event_meta(session: requests.Session, event_id: str) -> tuple[str, str] | None:
    """Return (race_name, division) for an event_id, or None if no results."""
    html = fetch(
        session,
        {
            "content": "list",
            "fpid": "list",
            "pid": "list",
            "lang": "EN_CAP",
            "event": event_id,
            "search[sex]": "X",
            "search[age_class]": "%",
        },
    )
    soup = BeautifulSoup(html, "html.parser")
    # Title appears as "RACE NAME / DIVISION"
    title_el = soup.find(class_=re.compile(r"list-info__text.*title|headline|result-title", re.I))
    if not title_el:
        # Try h1/h2
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(strip=True)
            if "DUBLIN" in text.upper() or "TRYKA" in text.upper():
                title_el = tag
                break

    if not title_el:
        # Fallback: search raw text for the pattern
        m = re.search(r"(DUBLIN [^/\n]+) / ([^\n<]+)", html)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None

    text = title_el.get_text(strip=True)
    # Strip common prefixes added by the page ("Results: ", "Start List: ", etc.)
    text = re.sub(r"^[A-Za-z ]+:\s*", "", text)
    if "/" in text:
        parts = text.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


def iter_athlete_ids(session: requests.Session, event_id: str) -> Iterator[tuple[str, str, str, str]]:
    """
    Yield (idp, detail_event_id, search_event_id, sex) tuples for every athlete.
    Iterates all three gender filters (M, W, X) to capture the full field.
    detail_event_id and search_event_id are extracted from list page hrefs and may
    differ from event_id — both are required for detail page fetches to return data.
    """
    seen: set[str] = set()
    for sex in ("M", "W", "X"):
        page = 1
        while True:
            html = fetch(
                session,
                {
                    "content": "list",
                    "fpid": "list",
                    "pid": "list",
                    "lang": "EN_CAP",
                    "event": event_id,
                    "search[sex]": sex,
                    "search[age_class]": "%",
                    "page": page,
                },
            )
            entries, total_pages = parse_list_page(html)
            for idp, detail_event, search_event in entries:
                if idp not in seen:
                    seen.add(idp)
                    yield idp, detail_event, search_event, sex

            if page >= total_pages:
                break
            page += 1


def scrape_athlete(
    session: requests.Session,
    idp: str,
    detail_event: str,
    search_event: str,
    conn,
    event_db_id: int,
    gender: str | None,
) -> bool:
    """
    Fetch and store a single athlete/team result.
    Returns True if stored, False if skipped (already exists).
    Both detail_event and search_event are required params for the detail page.
    """
    if db.result_exists(conn, idp, event_db_id):
        return False

    html = fetch(
        session,
        {
            "content": "detail",
            "fpid": "list",
            "pid": "list",
            "idp": idp,
            "lang": "EN_CAP",
            "event": detail_event,
            "search[sex]": "X",
            "search[age_class]": "%",
            "search_event": search_event,
        },
    )

    data = parse_detail_page(html)
    if not data:
        return False

    gender = gender or gender_from_division(data.get("division") or "")

    result_id = db.insert_result(
        conn,
        idp=idp,
        event_db_id=event_db_id,
        members=data["members"],
        bib_number=data.get("bib_number"),
        gym_affiliate=data.get("gym_affiliate"),
        age_group=data.get("age_group"),
        gender=gender,
        rank_overall=data.get("rank_overall"),
        rank_age_group=data.get("rank_age_group"),
        league_points=data.get("league_points"),
        overall_time=data.get("overall_time"),
        penalty=data.get("penalty"),
        bonus=data.get("bonus"),
        disqual_reason=data.get("disqual_reason"),
    )

    if data["raw_splits"]:
        db.insert_raw_splits(conn, result_id, data["raw_splits"])
    if data["refined_splits"]:
        db.insert_refined_splits(conn, result_id, data["refined_splits"])

    return True


def scrape_event(
    session: requests.Session,
    event_id: str,
    conn,
    verbose: bool = True,
) -> int:
    """Scrape all athletes for a single event. Returns count of new records stored."""
    meta = get_event_meta(session, event_id)
    if meta is None:
        if verbose:
            print(f"  [{event_id}] no results found, skipping")
        return 0

    race_name, division = meta
    if verbose:
        print(f"  [{event_id}] {race_name} / {division}")

    event_db_id = db.upsert_event(conn, event_id, race_name, division)

    stored = 0
    skipped = 0
    for idp, detail_event, search_event, sex_filter in iter_athlete_ids(session, event_id):
        # sex_filter is the authoritative gender source: it reflects which list filter
        # (M/W/X) returned this athlete. Division name is not reliable — "MENS/WOMENS"
        # means separate categories, not mixed pairs.
        gender = sex_filter
        try:
            ok = scrape_athlete(session, idp, detail_event, search_event, conn, event_db_id, gender)
            if ok:
                stored += 1
                if verbose:
                    print(f"    stored {idp} ({stored})", end="\r", flush=True)
            else:
                skipped += 1
        except requests.HTTPError as e:
            print(f"\n    WARNING: HTTP error for {idp}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"\n    WARNING: failed to parse {idp}: {e}", file=sys.stderr)

    if verbose:
        print(f"\n    done: {stored} stored, {skipped} skipped (already in DB)")
    return stored


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Tryka race results")
    parser.add_argument("--db", default="tryka.db", help="SQLite database path")
    parser.add_argument("--event", help="Scrape only this event ID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List events and their result counts without scraping details",
    )
    args = parser.parse_args()

    conn = db.connect(args.db)
    session = make_session()

    event_ids = [args.event] if args.event else ALL_EVENT_IDS

    if args.dry_run:
        print("Event discovery (dry run):")
        for eid in event_ids:
            meta = get_event_meta(session, eid)
            if meta:
                race_name, division = meta
                html = fetch(
                    session,
                    {
                        "content": "list",
                        "fpid": "list",
                        "pid": "list",
                        "lang": "EN_CAP",
                        "event": eid,
                        "search[sex]": "X",
                        "search[age_class]": "%",
                    },
                )
                m = re.search(r"(\d+)\s+Results", html)
                count = m.group(1) if m else "?"
                print(f"  {eid:30s}  {race_name} / {division}  ({count} athletes)")
            else:
                print(f"  {eid:30s}  (no results)")
        return

    total = 0
    print(f"Scraping {len(event_ids)} event(s) into {args.db}")
    for eid in event_ids:
        total += scrape_event(session, eid, conn, verbose=True)

    print(f"\nTotal new records stored: {total}")


if __name__ == "__main__":
    main()
