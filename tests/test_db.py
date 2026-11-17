import json

import db


def make_result(conn, event_db_id, idp, members, gender="M", age_group="30 - 34", rank=1, rank_ag=1):
    return db.insert_result(
        conn,
        idp=idp,
        event_db_id=event_db_id,
        members=members,
        bib_number=None,
        gym_affiliate=None,
        age_group=age_group,
        gender=gender,
        rank_overall=rank,
        rank_age_group=rank_ag,
        league_points=None,
        overall_time="00:58:00",
        penalty=None,
        bonus=None,
        disqual_reason=None,
    )


def test_connect_creates_schema_and_is_idempotent(tmp_db):
    conn = db.connect(tmp_db)
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events", "results", "raw_splits", "refined_splits"} <= tables
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(events)")}
    assert "series" in cols
    conn.close()
    db.connect(tmp_db).close()  # second connect re-runs schema + migrations without error


def test_upsert_event_returns_stable_id_and_updates_series(tmp_db):
    conn = db.connect(tmp_db)
    first = db.upsert_event(conn, "TP_X", "RACE", "TRYKA PRO", 1)
    second = db.upsert_event(conn, "TP_X", "RACE", "TRYKA PRO", 2)
    assert first == second
    assert conn.execute("SELECT series FROM events WHERE id = ?", (first,)).fetchone()[0] == 2


def test_insert_result_and_splits_round_trip(tmp_db):
    conn = db.connect(tmp_db)
    event_db_id = db.upsert_event(conn, "TP_X", "RACE", "TRYKA PRO", 1)
    result_id = make_result(conn, event_db_id, "IDP1", ["Ciarán O'Shea"])
    db.insert_raw_splits(conn, result_id, [{"name": "Start", "time_of_day": "09:00:00", "time": None, "diff": None}])
    db.insert_refined_splits(conn, result_id, [{"name": "SkiErg", "time": "00:04:07", "place": 4}])

    assert db.result_exists(conn, "IDP1", event_db_id)
    row = conn.execute("SELECT members FROM results WHERE id = ?", (result_id,)).fetchone()
    assert json.loads(row["members"]) == ["Ciarán O'Shea"]
    refined = conn.execute("SELECT split_name, time, place FROM refined_splits").fetchall()
    assert [tuple(r) for r in refined] == [("SkiErg", "00:04:07", 4)]

    db.delete_result(conn, "IDP1", event_db_id)
    assert not db.result_exists(conn, "IDP1", event_db_id)
    assert conn.execute("SELECT COUNT(*) FROM raw_splits").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM refined_splits").fetchone()[0] == 0


def test_purge_placeholders_and_compact_ranks(tmp_db):
    conn = db.connect(tmp_db)
    event_db_id = db.upsert_event(conn, "TR_X", "RACE", "TRYKA RELAY", 1)
    make_result(conn, event_db_id, "A", ["Ann", "Bob"], rank=1, rank_ag=1)
    make_result(conn, event_db_id, "P", ["1", "2"], rank=2, rank_ag=2)
    make_result(conn, event_db_id, "B", ["Cat", "Dan"], rank=3, rank_ag=3)

    genders = db.purge_placeholder_results(conn, event_db_id)
    assert genders == {"M"}
    db.compact_ranks(conn, event_db_id, "M")

    ranks = conn.execute(
        "SELECT idp, rank_overall, rank_age_group FROM results ORDER BY rank_overall"
    ).fetchall()
    assert [tuple(r) for r in ranks] == [("A", 1, 1), ("B", 2, 2)]
