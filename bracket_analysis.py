#!/usr/bin/env python3
"""Median station times and run pace for Tryka 800 races, grouped by finish-time bracket.

The 800 format is 8 run laps interleaved with 8 stations:
  SkiErg, KB Farmers Carry, Ramfit Thrusters, Sled Push,
  Sled Pull, Rowing, Lunges, Burpees.

Athletes are bucketed into finish-time brackets (default: 5-minute bins) and we
report the median time spent at each station and the median running pace within
each bracket.
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from analysis import time_to_seconds, fmt_time, print_header, print_table

# The 8 scored stations, in race order.
STATIONS = [
    "SkiErg", "KB Farmers Carry", "Ramfit Thrusters", "Sled Push",
    "Sled Pull", "Rowing", "Lunges", "Burpees",
]

# Run laps used for pace (the 8 numbered laps; the finish sprint is excluded so
# it doesn't drag the per-lap median down).
RUN_LAPS = [f"Running {i}" for i in range(1, 9)]

# Assumed distance of a single run lap, in metres. The "800" format = 8 x 800 m.
LAP_METRES = 800


def load(db_path: str, division: str, gender: str | None) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    where = "WHERE e.division LIKE ? AND r.rank_overall IS NOT NULL"
    params: list = [division]
    if gender:
        where += " AND r.gender = ?"
        params.append(gender)

    df = pd.read_sql_query(f"""
        SELECT r.id AS result_id, r.gender, r.overall_time, e.division,
               rs.split_name, rs.time AS split_time
        FROM results r
        JOIN events e ON r.event_id = e.id
        JOIN refined_splits rs ON rs.result_id = r.id
        {where}
          AND rs.split_order <= 16
    """, conn, params=params)
    conn.close()

    df["finish_sec"] = df["overall_time"].apply(time_to_seconds)
    df["split_sec"] = df["split_time"].apply(time_to_seconds)
    return df.dropna(subset=["finish_sec"])


def make_brackets(finish_min: pd.Series, width: int) -> pd.Series:
    """Bin finish time (minutes) into <width>-minute brackets with readable labels."""
    lo = int(finish_min.min() // width * width)
    hi = int(finish_min.max() // width * width) + width
    edges = list(range(lo, hi + width, width))
    labels = [f"{edges[i]}-{edges[i + 1]}" for i in range(len(edges) - 1)]
    return pd.cut(finish_min, bins=edges, labels=labels, right=False, include_lowest=True)


def main():
    p = argparse.ArgumentParser(description="Tryka 800 station & run-pace by finish bracket")
    p.add_argument("--db", default="tryka.db")
    p.add_argument("--division", default="TRYKA OPEN 800",
                   help="Division (supports SQL LIKE, e.g. '%%800%%' for all 800 formats)")
    p.add_argument("--gender", default=None, help="Filter to M / W / X")
    p.add_argument("--width", type=int, default=5, help="Bracket width in minutes")
    p.add_argument("--min-n", type=int, default=10,
                   help="Drop brackets with fewer than this many athletes")
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        return

    df = load(args.db, args.division, args.gender)
    if df.empty:
        print("No data for that division/gender.")
        return

    # One row per athlete carries finish time + bracket.
    athletes = df[["result_id", "gender", "finish_sec"]].drop_duplicates("result_id").copy()
    athletes["finish_min"] = athletes["finish_sec"] / 60
    athletes["bracket"] = make_brackets(athletes["finish_min"], args.width)
    df = df.merge(athletes[["result_id", "bracket"]], on="result_id")

    # Keep only brackets with enough athletes; order them by finish time.
    sizes = athletes.groupby("bracket", observed=True)["result_id"].count()
    keep = [b for b in sizes.index if sizes[b] >= args.min_n]
    keep = sorted(keep, key=lambda b: int(str(b).split("-")[0]))

    title = f"{args.division}" + (f" — {args.gender}" if args.gender else " — all genders")
    print_header(f"TRYKA 800 BRACKET ANALYSIS: {title}")
    print(f"\n{len(athletes)} athletes, {args.width}-min brackets "
          f"(showing brackets with >= {args.min_n}):\n")
    for b in keep:
        print(f"  {b:>8s} min : {sizes[b]:4d} athletes")

    # --- Median station times per bracket -------------------------------------
    stn = df[df["split_name"].isin(STATIONS)]
    stn_med = (stn.groupby(["split_name", "bracket"], observed=True)["split_sec"]
                  .median().unstack("bracket")
                  .reindex(index=STATIONS, columns=keep))
    print_header("MEDIAN STATION TIMES (mm:ss) by finish bracket")
    print_table(stn_med.map(lambda v: fmt_time(v) if pd.notna(v) else "-"))

    # --- Median run pace per bracket ------------------------------------------
    runs = df[df["split_name"].isin(RUN_LAPS)]
    # Median per-lap time across all 8 laps for each athlete, then median per bracket.
    lap_per_athlete = runs.groupby(["result_id", "bracket"], observed=True)["split_sec"].median()
    lap_med = lap_per_athlete.groupby("bracket", observed=True).median().reindex(keep)
    finish_med = athletes.groupby("bracket", observed=True)["finish_sec"].median().reindex(keep)

    pace = pd.DataFrame({
        "athletes": [sizes[b] for b in keep],
        "median finish": finish_med.apply(lambda v: fmt_time(v) if pd.notna(v) else "-").values,
        "median run lap": lap_med.apply(lambda v: fmt_time(v) if pd.notna(v) else "-").values,
        f"pace /km (@{LAP_METRES}m lap)": lap_med.apply(
            lambda v: fmt_time(v / LAP_METRES * 1000) if pd.notna(v) else "-").values,
    }, index=keep)
    print_header(f"MEDIAN RUN PACE by finish bracket  (per {LAP_METRES} m lap)")
    print_table(pace)


if __name__ == "__main__":
    main()
