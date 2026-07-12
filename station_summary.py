#!/usr/bin/env python3
"""Summary of station times for a set of Tryka divisions.

One row per (division group, gender, station). A "division group" can merge
multiple raw division names into one label — used for the Pro preset, where
TRYKA DOUBLES PRO and TRYKA PRO DOUBLES are inconsistently-named events for
the same doubles-pro division.

Reports p10, Q1 (p25), median, Q3 (p75), p90 for each station.
"""

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from analysis import time_to_seconds, fmt_time, print_header, print_table

# The 8 scored workstations, in race order.
STATIONS = [
    "SkiErg", "KB Farmers Carry", "Ramfit Thrusters", "Sled Push",
    "Sled Pull", "Rowing", "Lunges", "Burpees",
]

# preset name -> ordered {group label: [raw division names]}
PRESETS = {
    "pro": {
        "TRYKA PRO": ["TRYKA PRO"],
        "TRYKA PRO DOUBLES": ["TRYKA DOUBLES PRO", "TRYKA PRO DOUBLES"],
    },
    "open800": {
        "TRYKA OPEN 800": ["TRYKA OPEN 800"],
        "TRYKA DOUBLES 800": ["TRYKA DOUBLES 800"],
    },
    "open500": {
        "TRYKA OPEN 500": ["TRYKA OPEN 500"],
        "TRYKA DOUBLES 500": ["TRYKA DOUBLES 500"],
    },
}

PERCENTILES = [10, 25, 50, 75, 90]
PERCENTILE_LABELS = ["p10", "Q1", "Median", "Q3", "p90"]


def load(db_path: str, groups: dict) -> pd.DataFrame:
    division_to_group = {div: group for group, divs in groups.items() for div in divs}
    divisions = list(division_to_group.keys())

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"""
        SELECT r.gender, e.division, rs.split_name, rs.time AS split_time
        FROM results r
        JOIN events e ON r.event_id = e.id
        JOIN refined_splits rs ON rs.result_id = r.id
        WHERE r.rank_overall IS NOT NULL
          AND e.division IN ({",".join("?" * len(divisions))})
          AND rs.split_name IN ({",".join("?" * len(STATIONS))})
    """, conn, params=divisions + STATIONS)
    conn.close()

    df["group"] = df["division"].map(division_to_group)
    df["split_sec"] = df["split_time"].apply(time_to_seconds)
    return df.dropna(subset=["split_sec"])


def percentile_summary(times: pd.Series) -> dict:
    values = np.percentile(times, PERCENTILES)
    row = {"N": len(times)}
    row.update(dict(zip(PERCENTILE_LABELS, values)))
    return row


def main():
    p = argparse.ArgumentParser(description="Tryka division station time summary")
    p.add_argument("--db", default="tryka.db")
    p.add_argument("--preset", choices=PRESETS.keys(), default="pro")
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        return

    groups = PRESETS[args.preset]
    df = load(args.db, groups)
    if df.empty:
        print(f"No station data found for the '{args.preset}' divisions.")
        return

    rows = []
    for group in groups:
        grp = df[df["group"] == group]
        for gender, gg in grp.groupby("gender"):
            for station in STATIONS:
                sg = gg[gg["split_name"] == station]
                if sg.empty:
                    continue
                rows.append({"Group": group, "Gender": gender, "Station": station,
                             **percentile_summary(sg["split_sec"])})

    summary = pd.DataFrame(rows)
    for label in PERCENTILE_LABELS:
        summary[label] = summary[label].apply(fmt_time)

    print_header(f"{args.preset.upper()} STATION TIMES SUMMARY (mm:ss)")
    print_table(summary.set_index(["Group", "Gender", "Station"]), max_rows=200)


if __name__ == "__main__":
    main()
