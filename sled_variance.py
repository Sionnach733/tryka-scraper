#!/usr/bin/env python3
"""Cross-race variance analysis for a single Tryka station (default: Sled Pull).

Reports of a brutally hard Sled Pull in DUBLIN SUMMER RACE 4 prompted this. Raw
station times aren't comparable across races — a weaker field or slower course
inflates every station at once. To isolate whether *this station* got harder, we
express it as a share of each athlete's own total 8-station workstation time,
which normalises away fitness, field strength, and overall race pace.

For each (division, gender) cohort it prints, per race:
  - median raw station time,
  - median station-share-of-8-stations (the normalised difficulty metric),
  - the Summer-4 delta vs the mean of the three prior races,
  - N (finishers with all 8 stations present) to flag thin cohorts.

Only divisions running the full 8-station format appear; junior/clan/relay-format
events that lack a station drop out when we require all 8 to be present.
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from analysis import time_to_seconds, fmt_time, print_header, print_table

# The 8 scored workstations, in race order.
STATIONS = [
    "SkiErg", "KB Farmers Carry", "Ramfit Thrusters", "Sled Push",
    "Sled Pull", "Rowing", "Lunges", "Burpees",
]

# Divisions renamed across races that are the same competitive event. Normalised
# to a single canonical name so cross-race cohorts merge instead of splitting.
# TRYKA DOUBLES PRO (Autumn 1, Winter 2) was renamed TRYKA PRO DOUBLES (Spring 3+).
DIVISION_ALIASES = {
    "TRYKA DOUBLES PRO": "TRYKA PRO DOUBLES",
}

# Competitive divisions whose finishers should count even when the source published
# no overall rank. The Autumn 1 women's Open 500/800 (run as separate Sunday events)
# have complete 8-station records and finish times but no Overall Rank on the source,
# so the usual rank_overall gate would wrongly drop them. See CLAUDE.md > Domain notes.
UNRANKED_BUT_VALID_DIVISIONS = ("TRYKA OPEN 500", "TRYKA OPEN 800")

# Divisions excluded from the analysis. Relay is a relay-format event, not directly
# comparable to the individual/doubles 8-station workload, so it is dropped.
EXCLUDE_DIVISIONS = ("TRYKA RELAY",)

# Races in chronological order, with short labels for compact tables.
RACE_ORDER = [
    ("DUBLIN AUTUMN RACE 1", "Autumn1"),
    ("DUBLIN WINTER RACE 2", "Winter2"),
    ("DUBLIN SPRING RACE 3", "Spring3"),
    ("DUBLIN SUMMER RACE 4", "Summer4"),
]
PRIOR_LABELS = ["Autumn1", "Winter2", "Spring3"]
TARGET_LABEL = "Summer4"


def load(db_path: str) -> pd.DataFrame:
    """One row per finisher, with a column per station (seconds). Requires all 8."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"""
        SELECT r.id AS result_id, e.race_name, e.division, r.gender,
               rs.split_name, rs.time AS split_time
        FROM results r
        JOIN events e ON r.event_id = e.id
        JOIN refined_splits rs ON rs.result_id = r.id
        WHERE (r.rank_overall IS NOT NULL OR e.division IN ({",".join("?" * len(UNRANKED_BUT_VALID_DIVISIONS))}))
          AND rs.split_name IN ({",".join("?" * len(STATIONS))})
    """, conn, params=list(UNRANKED_BUT_VALID_DIVISIONS) + STATIONS)
    conn.close()

    # Merge renamed-but-identical divisions into one canonical cohort.
    df["division"] = df["division"].replace(DIVISION_ALIASES)
    df = df[~df["division"].isin(EXCLUDE_DIVISIONS)]

    df["split_sec"] = df["split_time"].apply(time_to_seconds)
    wide = df.pivot_table(index=["result_id", "race_name", "division", "gender"],
                          columns="split_name", values="split_sec").reset_index()
    # Require every station present and positive so the share denominator is valid.
    wide = wide.dropna(subset=STATIONS)
    wide = wide[(wide[STATIONS] > 0).all(axis=1)]
    return wide


def build_summary(wide: pd.DataFrame, station: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (share table, raw-time table) indexed by (division, gender)."""
    wide = wide.copy()
    wide["total"] = wide[STATIONS].sum(axis=1)
    wide["share"] = wide[station] / wide["total"] * 100
    wide["label"] = wide["race_name"].map(dict(RACE_ORDER))

    labels = [lbl for _, lbl in RACE_ORDER]

    share = wide.pivot_table(index=["division", "gender"], columns="label",
                             values="share", aggfunc="median")
    counts = wide.pivot_table(index=["division", "gender"], columns="label",
                              values="result_id", aggfunc="count")
    raw = wide.pivot_table(index=["division", "gender"], columns="label",
                           values=station, aggfunc="median")

    share = share.reindex(columns=labels)
    counts = counts.reindex(columns=labels)
    raw = raw.reindex(columns=labels)

    # Summer-4 delta vs mean of the prior three races (share points).
    prior = share[PRIOR_LABELS].mean(axis=1)
    share["Su4-Δ"] = share[TARGET_LABEL] - prior

    # Attach N for the target race so thin cohorts are visible.
    share["N(Su4)"] = counts[TARGET_LABEL]
    return share, raw


def main():
    p = argparse.ArgumentParser(description="Cross-race station difficulty variance")
    p.add_argument("--db", default="tryka.db")
    p.add_argument("--station", default="Sled Pull", choices=STATIONS)
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        return

    wide = load(args.db)
    if wide.empty:
        print("No finishers with all 8 stations found.")
        return

    share, raw = build_summary(wide, args.station)

    print_header(f"{args.station.upper()} — SHARE OF 8-STATION WORKLOAD (median %) by race")
    print("\n(share = station time / sum of all 8 station times, per athlete."
          "\n Flat across races = station's relative difficulty unchanged;"
          "\n a jump = the station itself got harder.)\n")
    disp = share.copy()
    for c in [lbl for _, lbl in RACE_ORDER] + ["Su4-Δ"]:
        disp[c] = disp[c].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "-")
    disp["N(Su4)"] = disp["N(Su4)"].apply(lambda v: f"{int(v)}" if pd.notna(v) else "-")
    print_table(disp, max_rows=200)

    print_header(f"{args.station.upper()} — RAW MEDIAN TIME (mm:ss) by race  [confounded]")
    rawd = raw.map(lambda v: fmt_time(v) if pd.notna(v) else "-")
    print_table(rawd, max_rows=200)

    # Pooled by gender across all qualifying divisions.
    pooled_wide = wide.copy()
    pooled_wide["total"] = pooled_wide[STATIONS].sum(axis=1)
    pooled_wide["share"] = pooled_wide[args.station] / pooled_wide["total"] * 100
    pooled_wide["label"] = pooled_wide["race_name"].map(dict(RACE_ORDER))
    g = pooled_wide.pivot_table(index="gender", columns="label", values="share",
                                aggfunc="median").reindex(columns=[l for _, l in RACE_ORDER])
    g["Su4-Δ"] = g[TARGET_LABEL] - g[PRIOR_LABELS].mean(axis=1)
    print_header(f"{args.station.upper()} — SHARE POOLED BY GENDER (all qualifying divisions)")
    print_table(g.round(1))


if __name__ == "__main__":
    main()
