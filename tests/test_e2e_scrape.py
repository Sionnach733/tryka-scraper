"""End-to-end: run the real scraper CLI against recorded HTML and check the database."""

import json
import sqlite3

import pytest

import scraper

LISBON_PRO = "TP_5GGDDHUF8D"
LONDON_RELAY = "TR_5GGDDHUF7A"


def run_cli(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["scraper.py", *args])
    scraper.main()


def query(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def results_for(db_path, event_id):
    return query(
        db_path,
        "SELECT r.idp, r.members, r.gender, r.age_group, r.rank_overall, r.rank_age_group, "
        "r.overall_time FROM results r JOIN events e ON e.id = r.event_id WHERE e.event_id = ? "
        "ORDER BY r.idp",
        (event_id,),
    )


@pytest.fixture
def scraped(replay_fetch, tmp_db, monkeypatch, capsys):
    for event_id in (LISBON_PRO, LONDON_RELAY):
        run_cli(monkeypatch, "--db", tmp_db, "--event", event_id)
    out = capsys.readouterr()
    # scrape_event swallows per-athlete errors as warnings; any warning is a failure here.
    assert "WARNING" not in out.err, out.err
    return tmp_db


def test_events_are_stored(scraped):
    rows = query(scraped, "SELECT event_id, race_name, division, series FROM events ORDER BY event_id")
    assert rows == [
        (LISBON_PRO, "LISBON RACE 6 GRAND FINALE", "TRYKA PRO", 1),
        (LONDON_RELAY, "LONDON RACE 5", "TRYKA RELAY", 1),
    ]


def test_solo_event_results(scraped):
    rows = results_for(scraped, LISBON_PRO)
    assert len(rows) == 18
    by_gender = {}
    for r in rows:
        by_gender[r[2]] = by_gender.get(r[2], 0) + 1
    assert by_gender == {"M": 12, "W": 6}

    winner = next(r for r in rows if r[0] == "5GGDDHUFCB1B")
    assert winner[1:] == (json.dumps(["Robert Ronan"]), "M", "25 - 29", 1, 1, "00:57:28")

    # Every finisher has the full split breakdown.
    counts = query(
        scraped,
        "SELECT r.idp, (SELECT COUNT(*) FROM raw_splits WHERE result_id = r.id), "
        "(SELECT COUNT(*) FROM refined_splits WHERE result_id = r.id) "
        "FROM results r JOIN events e ON e.id = r.event_id WHERE e.event_id = ?",
        (LISBON_PRO,),
    )
    assert all(raw > 0 and refined > 0 for _, raw, refined in counts)


def test_team_event_drops_placeholders_and_closes_rank_gaps(scraped):
    rows = results_for(scraped, LONDON_RELAY)
    assert len(rows) == 13
    for r in rows:
        members = json.loads(r[1])
        assert len(members) == 4
        assert not any(m.replace(" ", "").isdigit() for m in members)

    ranks = {}
    for r in rows:
        ranks.setdefault(r[2], []).append(r[4])
    assert {g: sorted(v) for g, v in ranks.items()} == {
        "M": [1, 2],
        "W": [1, 2],
        "X": list(range(1, 10)),
    }

    team = next(r for r in rows if r[0] == "5GGDDHUFCA13")
    assert json.loads(team[1]) == [
        "Michael Kennedy (GBR)",
        "Paul Shrives (GBR)",
        "Lucas Shawcroft (GBR)",
        "Marcus Mollisson (BUL)",
    ]


def test_rescrape_is_idempotent(scraped, monkeypatch, capsys):
    before = query(scraped, "SELECT COUNT(*) FROM results")[0][0]
    run_cli(monkeypatch, "--db", scraped, "--event", LISBON_PRO)
    assert "done: 0 stored, 18 skipped" in capsys.readouterr().out
    assert query(scraped, "SELECT COUNT(*) FROM results")[0][0] == before


def test_force_rescrape_replaces_rows(scraped, monkeypatch, capsys):
    before = results_for(scraped, LISBON_PRO)
    old_ids = {r[0] for r in query(scraped, "SELECT id FROM results")}
    run_cli(monkeypatch, "--db", scraped, "--event", LISBON_PRO, "--force")
    assert "done: 18 stored" in capsys.readouterr().out
    assert results_for(scraped, LISBON_PRO) == before
    orphans = query(
        scraped,
        "SELECT COUNT(*) FROM refined_splits WHERE result_id NOT IN (SELECT id FROM results)",
    )[0][0]
    assert orphans == 0
    assert {r[0] for r in query(scraped, "SELECT id FROM results")} != old_ids


def test_unknown_event_is_rejected(replay_fetch, tmp_db, monkeypatch):
    with pytest.raises(SystemExit):
        run_cli(monkeypatch, "--db", tmp_db, "--event", "NOT_AN_EVENT")
