#!/usr/bin/env python3
"""Podium finisher analysis for Tryka race results."""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def time_to_seconds(t: str) -> float | None:
    """Convert 'HH:MM:SS' or 'MM:SS' to total seconds."""
    if not t or not isinstance(t, str):
        return None
    parts = t.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return None
    return None


def fmt_time(seconds: float) -> str:
    """Format seconds back to MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def print_header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_subheader(title: str) -> None:
    print(f"\n--- {title} ---")


def print_table(df: pd.DataFrame, max_rows: int = 60) -> None:
    with pd.option_context("display.max_rows", max_rows, "display.width", 120,
                           "display.max_columns", 20, "display.float_format", "{:.1f}".format):
        print(df.to_string())
    print()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(db_path: str, division_filter: str | None = None):
    conn = sqlite3.connect(db_path)

    where_clause = "WHERE r.rank_overall IS NOT NULL"
    if division_filter:
        where_clause += f" AND e.division = '{division_filter}'"

    results_df = pd.read_sql_query(f"""
        SELECT r.id AS result_id, r.rank_overall, r.rank_age_group,
               r.age_group, r.gender, r.overall_time, r.gym_affiliate,
               r.penalty, e.race_name, e.division,
               CASE WHEN r.rank_overall <= 3 THEN 'podium' ELSE 'field' END AS tier
        FROM results r
        JOIN events e ON r.event_id = e.id
        {where_clause}
    """, conn)

    splits_df = pd.read_sql_query(f"""
        SELECT rs.result_id, rs.split_order, rs.split_name, rs.time, rs.place,
               r.rank_overall, r.gender, r.age_group,
               e.race_name, e.division,
               CASE WHEN r.rank_overall <= 3 THEN 'podium' ELSE 'field' END AS tier
        FROM refined_splits rs
        JOIN results r ON rs.result_id = r.id
        JOIN events e ON r.event_id = e.id
        {where_clause}
          AND rs.split_order <= 16
    """, conn)

    conn.close()

    # Convert times to seconds
    results_df["time_sec"] = results_df["overall_time"].apply(time_to_seconds)
    splits_df["time_sec"] = splits_df["time"].apply(time_to_seconds)

    # Competition group
    results_df["comp_group"] = (results_df["race_name"] + " | "
                                + results_df["division"] + " | "
                                + results_df["gender"])
    splits_df["comp_group"] = (splits_df["race_name"] + " | "
                               + splits_df["division"] + " | "
                               + splits_df["gender"])

    return results_df, splits_df


# ---------------------------------------------------------------------------
# Analysis 1: Podium Characteristics by Division
# ---------------------------------------------------------------------------

def analyze_characteristics(results_df: pd.DataFrame) -> None:
    print_header("ANALYSIS 1: Podium Finisher Characteristics by Division")

    for division, grp in results_df.groupby("division"):
        podium = grp[grp["tier"] == "podium"]
        field = grp[grp["tier"] == "field"]
        if len(podium) == 0:
            continue

        podium_time = podium["time_sec"].dropna().mean()
        field_time = field["time_sec"].dropna().mean()
        advantage = (field_time - podium_time) / field_time * 100 if field_time else 0

        print_subheader(f"{division}  ({len(podium)} podium / {len(field)} field)")
        print(f"  Avg time   podium: {fmt_time(podium_time)}   field: {fmt_time(field_time)}   advantage: {advantage:.1f}%")
        print(f"  Median     podium: {fmt_time(podium['time_sec'].dropna().median())}   field: {fmt_time(field['time_sec'].dropna().median())}")

        # Age group over-representation
        field_ag = field["age_group"].value_counts(normalize=True)
        podium_ag = podium["age_group"].value_counts(normalize=True)
        overrep = (podium_ag / field_ag).dropna().sort_values(ascending=False)
        overrep = overrep[overrep > 1.0].head(5)
        if not overrep.empty:
            print("  Age groups over-represented on podium:")
            for ag, ratio in overrep.items():
                podium_n = (podium["age_group"] == ag).sum()
                field_n = (field["age_group"] == ag).sum()
                print(f"    {ag:>12s}  {ratio:.1f}x  (podium: {podium_n}, field: {field_n})")

        # Top gym affiliates on podium
        top_gyms = podium["gym_affiliate"].dropna().value_counts().head(5)
        if not top_gyms.empty:
            print("  Top gym affiliates on podium:")
            for gym, count in top_gyms.items():
                print(f"    {gym:>30s}  {count} podium finishes")

        # Penalty rate
        podium_penalty = podium["penalty"].notna().mean() * 100
        field_penalty = field["penalty"].notna().mean() * 100
        print(f"  Penalty rate  podium: {podium_penalty:.0f}%   field: {field_penalty:.0f}%")


# ---------------------------------------------------------------------------
# Analysis 2: Station Dominance
# ---------------------------------------------------------------------------

def analyze_station_dominance(splits_df: pd.DataFrame) -> None:
    print_header("ANALYSIS 2: Station Dominance (Where Podium Finishers Win)")

    stations = splits_df[splits_df["place"].notna()].copy()

    agg = stations.groupby(["split_name", "split_order", "tier"]).agg(
        avg_time=("time_sec", "mean"),
        avg_place=("place", "mean"),
        count=("result_id", "count"),
    ).reset_index()

    pivot_time = agg.pivot_table(index=["split_order", "split_name"],
                                 columns="tier", values="avg_time")
    pivot_place = agg.pivot_table(index=["split_order", "split_name"],
                                  columns="tier", values="avg_place")

    summary = pd.DataFrame({
        "Station": pivot_time.index.get_level_values("split_name"),
        "Podium Avg": pivot_time["podium"].values,
        "Field Avg": pivot_time["field"].values,
        "Podium Place": pivot_place["podium"].values,
        "Field Place": pivot_place["field"].values,
    })
    summary["Gap %"] = (summary["Field Avg"] - summary["Podium Avg"]) / summary["Field Avg"] * 100
    summary = summary.sort_values("Gap %", ascending=False).reset_index(drop=True)

    # Format times
    summary["Podium Avg"] = summary["Podium Avg"].apply(fmt_time)
    summary["Field Avg"] = summary["Field Avg"].apply(fmt_time)
    summary["Podium Place"] = summary["Podium Place"].apply(lambda x: f"{x:.0f}")
    summary["Field Place"] = summary["Field Place"].apply(lambda x: f"{x:.0f}")

    print("\nStations ranked by podium time advantage:\n")
    print_table(summary)


# ---------------------------------------------------------------------------
# Analysis 3: Pacing Patterns
# ---------------------------------------------------------------------------

def analyze_pacing(splits_df: pd.DataFrame) -> None:
    print_header("ANALYSIS 3: Pacing Patterns")

    # 3a: Running pace trajectory
    print_subheader("Running Pace Trajectory (normalised to each athlete's average)")

    running = splits_df[
        splits_df["place"].isna() & (splits_df["split_order"] <= 14)  # exclude finish sprint
    ].copy()
    running = running.dropna(subset=["time_sec"])

    # Compute each athlete's mean running split
    athlete_avg = running.groupby("result_id")["time_sec"].mean().rename("athlete_avg")
    running = running.merge(athlete_avg, on="result_id")
    running["pace_index"] = running["time_sec"] / running["athlete_avg"]

    pace = running.groupby(["split_order", "split_name", "tier"])["pace_index"].mean().reset_index()
    pace_pivot = pace.pivot_table(index=["split_order", "split_name"],
                                  columns="tier", values="pace_index")
    pace_pivot = pace_pivot.sort_index()

    # Format for display
    display = pace_pivot.copy()
    display.columns = [f"{c} pace idx" for c in display.columns]
    print("\n(< 1.0 = faster than own average, > 1.0 = slower)\n")
    print_table(display)

    # 3b: Position progression through workstations
    print_subheader("Position Progression Through Workstations")

    stations = splits_df[splits_df["place"].notna()].copy()
    pos = stations.groupby(["split_order", "split_name", "tier"])["place"].mean().reset_index()
    pos_pivot = pos.pivot_table(index=["split_order", "split_name"],
                                columns="tier", values="place")
    pos_pivot = pos_pivot.sort_index()
    display = pos_pivot.copy()
    display.columns = [f"{c} avg rank" for c in display.columns]
    print("\n(lower = better position)\n")
    print_table(display)


# ---------------------------------------------------------------------------
# Analysis 4: Division & Age Group Breakdown
# ---------------------------------------------------------------------------

def analyze_by_division(results_df: pd.DataFrame, splits_df: pd.DataFrame) -> None:
    print_header("ANALYSIS 4: Division Breakdown")

    stations = splits_df[splits_df["place"].notna()].copy()
    running = splits_df[
        splits_df["place"].isna() & (splits_df["split_order"] <= 14)
    ].copy().dropna(subset=["time_sec"])

    for division, grp in results_df.groupby("division"):
        if len(grp) < 30:
            continue
        podium = grp[grp["tier"] == "podium"]
        if len(podium) == 0:
            continue

        print_subheader(division)

        # Top differentiating station
        div_stations = stations[stations["division"] == division]
        if not div_stations.empty:
            st_agg = div_stations.groupby(["split_name", "tier"])["time_sec"].mean().reset_index()
            st_pivot = st_agg.pivot_table(index="split_name", columns="tier", values="time_sec")
            if "podium" in st_pivot.columns and "field" in st_pivot.columns:
                st_pivot["gap_pct"] = (st_pivot["field"] - st_pivot["podium"]) / st_pivot["field"] * 100
                top_station = st_pivot["gap_pct"].idxmax()
                top_gap = st_pivot.loc[top_station, "gap_pct"]
                print(f"  Biggest podium advantage: {top_station} ({top_gap:.1f}% faster)")

        # Pacing: first half vs second half running ratio
        div_running = running[running["division"] == division]
        if not div_running.empty:
            first_half = div_running[div_running["split_order"] <= 6]
            second_half = div_running[div_running["split_order"] > 6]
            for tier in ["podium", "field"]:
                fh = first_half[first_half["tier"] == tier]["time_sec"].mean()
                sh = second_half[second_half["tier"] == tier]["time_sec"].mean()
                if fh and sh:
                    ratio = sh / fh
                    label = "even" if 0.95 <= ratio <= 1.05 else ("fades" if ratio > 1.05 else "negative split")
                    print(f"  Pacing {tier:>6s}: 2nd-half/1st-half = {ratio:.2f} ({label})")

        # Age groups punching above weight
        field = grp[grp["tier"] == "field"]
        field_ag = field["age_group"].value_counts(normalize=True)
        podium_ag = podium["age_group"].value_counts(normalize=True)
        overrep = (podium_ag / field_ag).dropna().sort_values(ascending=False)
        overrep = overrep[overrep > 1.0].head(3)
        if not overrep.empty:
            print("  Age groups over-represented on podium:")
            for ag, ratio in overrep.items():
                print(f"    {ag}: {ratio:.1f}x")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tryka podium finisher analysis")
    parser.add_argument("--db", default="tryka.db", help="Path to SQLite database")
    parser.add_argument("--division", default=None, help="Filter to a single division")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    print(f"Loading data from {db_path}...")
    results_df, splits_df = load_data(str(db_path), args.division)
    print(f"Loaded {len(results_df)} results, {len(splits_df)} split records")

    analyze_characteristics(results_df)
    analyze_station_dominance(splits_df)
    analyze_pacing(splits_df)
    analyze_by_division(results_df, splits_df)


if __name__ == "__main__":
    main()
