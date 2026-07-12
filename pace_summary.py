#!/usr/bin/env python3
"""Five-number summary of running pace (min/km) for a set of Tryka divisions.

One row per (division group, gender). Pace is derived from each athlete's
'Run Total' split divided by the format's run distance (4.0 km for 500
formats, 6.4 km for 800/Pro formats — see agewinners.run_km).

Reports p10, Q1, Median, Q3, p90 pace per group.
"""

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from analysis import time_to_seconds, fmt_time, print_header, print_table
from agewinners import run_km
from station_summary import PRESETS

PERCENTILES = [10, 25, 50, 75, 90]
PERCENTILE_LABELS = ["p10", "Q1", "Median", "Q3", "p90"]


def load(db_path: str, groups: dict) -> pd.DataFrame:
    division_to_group = {div: group for group, divs in groups.items() for div in divs}
    divisions = list(division_to_group.keys())

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"""
        SELECT r.gender, e.division, rs.time AS run_total
        FROM results r
        JOIN events e ON r.event_id = e.id
        JOIN refined_splits rs ON rs.result_id = r.id AND rs.split_name = 'Run Total'
        WHERE r.rank_overall IS NOT NULL
          AND e.division IN ({",".join("?" * len(divisions))})
    """, conn, params=divisions)
    conn.close()

    df["group"] = df["division"].map(division_to_group)
    df["run_sec"] = df["run_total"].apply(time_to_seconds)
    df["km"] = df["division"].apply(lambda d: run_km(d, None))
    df["pace_sec"] = df["run_sec"] / df["km"]
    return df.dropna(subset=["pace_sec"])


def percentile_summary(paces: pd.Series) -> dict:
    values = np.percentile(paces, PERCENTILES)
    row = {"N": len(paces)}
    row.update(dict(zip(PERCENTILE_LABELS, values)))
    return row


def main():
    p = argparse.ArgumentParser(description="Tryka division run pace summary")
    p.add_argument("--db", default="tryka.db")
    p.add_argument("--preset", choices=PRESETS.keys(), default="pro")
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        return

    groups = PRESETS[args.preset]
    df = load(args.db, groups)
    if df.empty:
        print(f"No run pace data found for the '{args.preset}' divisions.")
        return

    rows = []
    for group in groups:
        grp = df[df["group"] == group]
        for gender, gg in grp.groupby("gender"):
            rows.append({"Group": group, "Gender": gender,
                         **percentile_summary(gg["pace_sec"])})

    summary = pd.DataFrame(rows)
    for label in PERCENTILE_LABELS:
        summary[label] = summary[label].apply(fmt_time)

    print_header(f"{args.preset.upper()} RUN PACE SUMMARY (min/km)")
    print_table(summary.set_index(["Group", "Gender"]), max_rows=200)


if __name__ == "__main__":
    main()
