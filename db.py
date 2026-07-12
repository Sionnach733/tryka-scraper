import sqlite3
import json
from pathlib import Path

from parser import normalize_member_name


def connect(db_path: str = "tryka.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema = Path(__file__).parent / "schema.sql"
    conn.executescript(schema.read_text())
    conn.commit()
    _migrate_member_names(conn)
    return conn


def _migrate_member_names(conn: sqlite3.Connection) -> None:
    """One-time migration: reformat member names from 'Surname, Firstname (COUNTRY)'
    to 'Firstname Surname (COUNTRY)'."""
    rows = conn.execute("SELECT id, members FROM results").fetchall()
    for row in rows:
        old_members = json.loads(row["members"])
        new_members = [normalize_member_name(m) for m in old_members]
        if new_members != old_members:
            conn.execute(
                "UPDATE results SET members = ? WHERE id = ?",
                (json.dumps(new_members, ensure_ascii=False), row["id"]),
            )
    conn.commit()


def upsert_event(conn: sqlite3.Connection, event_id: str, race_name: str, division: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO events (event_id, race_name, division) VALUES (?, ?, ?)",
        (event_id, race_name, division),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM events WHERE event_id = ?", (event_id,)).fetchone()
    return row["id"]


def result_exists(conn: sqlite3.Connection, idp: str, event_db_id: int) -> bool:
    row = conn.execute(
        "SELECT id FROM results WHERE idp = ? AND event_id = ?", (idp, event_db_id)
    ).fetchone()
    return row is not None


def delete_result(conn: sqlite3.Connection, idp: str, event_db_id: int) -> None:
    """Delete a result and its splits so it can be re-scraped cleanly.

    INSERT OR REPLACE mints a new results.id, which would orphan existing split
    rows (and, with foreign keys enabled, fail on the parent delete). Force
    refreshes call this first to remove the old row and its children.
    """
    row = conn.execute(
        "SELECT id FROM results WHERE idp = ? AND event_id = ?", (idp, event_db_id)
    ).fetchone()
    if row is None:
        return
    result_id = row["id"]
    conn.execute("DELETE FROM raw_splits WHERE result_id = ?", (result_id,))
    conn.execute("DELETE FROM refined_splits WHERE result_id = ?", (result_id,))
    conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
    conn.commit()


def insert_result(
    conn: sqlite3.Connection,
    idp: str,
    event_db_id: int,
    members: list[str],
    bib_number: str | None,
    gym_affiliate: str | None,
    age_group: str | None,
    gender: str | None,
    rank_overall: int | None,
    rank_age_group: int | None,
    league_points: int | None,
    overall_time: str | None,
    penalty: str | None,
    bonus: str | None,
    disqual_reason: str | None,
) -> int:
    cur = conn.execute(
        """
        INSERT OR REPLACE INTO results
            (idp, event_id, members, bib_number, gym_affiliate, age_group, gender,
             rank_overall, rank_age_group, league_points, overall_time,
             penalty, bonus, disqual_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            idp,
            event_db_id,
            json.dumps(members, ensure_ascii=False),
            bib_number,
            gym_affiliate,
            age_group,
            gender,
            rank_overall,
            rank_age_group,
            league_points,
            overall_time,
            penalty,
            bonus,
            disqual_reason,
        ),
    )
    conn.commit()
    return cur.lastrowid


def insert_raw_splits(conn: sqlite3.Connection, result_id: int, splits: list[dict]) -> None:
    conn.execute("DELETE FROM raw_splits WHERE result_id = ?", (result_id,))
    conn.executemany(
        "INSERT INTO raw_splits (result_id, split_order, split_name, time_of_day, time, diff) "
        "VALUES (:result_id, :order, :name, :time_of_day, :time, :diff)",
        [
            {
                "result_id": result_id,
                "order": i,
                "name": s["name"],
                "time_of_day": s.get("time_of_day"),
                "time": s.get("time"),
                "diff": s.get("diff"),
            }
            for i, s in enumerate(splits)
        ],
    )
    conn.commit()


def insert_refined_splits(conn: sqlite3.Connection, result_id: int, splits: list[dict]) -> None:
    conn.execute("DELETE FROM refined_splits WHERE result_id = ?", (result_id,))
    conn.executemany(
        "INSERT INTO refined_splits (result_id, split_order, split_name, time, place) "
        "VALUES (:result_id, :order, :name, :time, :place)",
        [
            {
                "result_id": result_id,
                "order": i,
                "name": s["name"],
                "time": s.get("time"),
                "place": s.get("place"),
            }
            for i, s in enumerate(splits)
        ],
    )
    conn.commit()
