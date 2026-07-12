#!/usr/bin/env python3
"""Age-group winners (by overall time) and their run pace for a Tryka division.

For each age group we take the athlete who won it on overall time (the fastest
finisher carrying rank_age_group = 1) and report their run pace, derived from
the 'Run Total' split over the format's run distance:

  500 format -> 8 x 500 m = 4.0 km
  800 / Pro  -> 8 x 800 m = 6.4 km
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

from analysis import time_to_seconds, fmt_time


def run_km(division: str, override: float | None) -> float:
    if override:
        return override
    return 4.0 if "500" in division else 6.4


def age_sortkey(ag: str) -> int:
    """Numeric age groups sort by their leading number; everything else last."""
    m = re.match(r"\d+", ag.strip())
    return int(m.group()) if m else 999


def main():
    p = argparse.ArgumentParser(description="Tryka age-group winners + run pace")
    p.add_argument("--db", default="tryka.db")
    p.add_argument("--division", default="TRYKA OPEN 800",
                   help="Exact division, e.g. 'TRYKA PRO', 'TRYKA OPEN 500'")
    p.add_argument("--gender", default="M", help="M / W / X")
    p.add_argument("--km", type=float, default=None,
                   help="Override run distance in km (else inferred from division)")
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    df = pd.read_sql_query("""
        SELECT e.race_name, r.age_group, r.members, r.overall_time,
               rs.time AS run_total
        FROM results r
        JOIN events e ON r.event_id = e.id
        JOIN refined_splits rs ON rs.result_id = r.id AND rs.split_name = 'Run Total'
        WHERE e.division = ? AND r.gender = ? AND r.rank_age_group = 1
    """, conn, params=[args.division, args.gender])
    conn.close()

    if df.empty:
        print(f"No age-group winners for {args.division} / {args.gender}.")
        return

    km = run_km(args.division, args.km)
    df["name"] = df["members"].apply(lambda m: ", ".join(json.loads(m)) if m else m)
    df["fin_sec"] = df["overall_time"].apply(time_to_seconds)
    df["run_sec"] = df["run_total"].apply(time_to_seconds)
    df["pace_sec"] = df["run_sec"] / km
    df = df.dropna(subset=["fin_sec", "age_group"])

    # Age-group winner = fastest overall time within each age group.
    df = df.loc[df.groupby("age_group")["fin_sec"].idxmin()]
    df = df.sort_values("age_group", key=lambda s: s.map(age_sortkey))

    df["Run Total"] = df["run_sec"].apply(lambda v: fmt_time(v) if pd.notna(v) else "-")
    df["Pace/km"] = df["pace_sec"].apply(lambda v: fmt_time(v) if pd.notna(v) else "-")
    df["Finish"] = df["overall_time"].str.replace("^00:", "", regex=True)

    out = df[["age_group", "name", "race_name", "Finish", "Run Total", "Pace/km"]]
    out.columns = ["Age Group", "Name", "Event", "Finish", "Run Total", "Pace/km"]
    print(f"\n{args.division} — {args.gender}   (run pace over {km:g} km)\n")
    print(out.to_string(index=False))
    print()


if __name__ == "__main__":
    main()
