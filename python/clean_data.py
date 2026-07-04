"""
clean_data.py
Reads raw scraped CSVs, applies EDA fixes, and writes clean versions.

Outputs:
  data/wicked_broadway_weekly_clean.csv
  data/wicked_domestic_daily_clean.csv      (Wicked 2024)
  data/wicked2_domestic_daily_clean.csv     (Wicked: For Good 2025)
"""

import pandas as pd
import numpy as np
import os

BASE = os.path.dirname(os.path.abspath(__file__))

RAW_BROADWAY  = os.path.join(BASE, "../data/wicked_broadway_weekly.csv")
RAW_MOVIE     = os.path.join(BASE, "../data/wicked_domestic_daily.csv")
RAW_MOVIE2    = os.path.join(BASE, "../data/wicked2_domestic_daily.csv")

OUT_BROADWAY  = os.path.join(BASE, "../data/wicked_broadway_weekly_clean.csv")
OUT_MOVIE     = os.path.join(BASE, "../data/wicked_domestic_daily_clean.csv")
OUT_MOVIE2    = os.path.join(BASE, "../data/wicked2_domestic_daily_clean.csv")


# ---------------------------------------------------------------------------
# Broadway cleaning
# ---------------------------------------------------------------------------

def broadway_season(date):
    """Return Broadway season label, e.g. '2003-04'. Season runs Sep–Aug."""
    y, m = date.year, date.month
    if m >= 9:
        return f"{y}-{str(y + 1)[2:]}"
    return f"{y - 1}-{str(y)[2:]}"


def clean_broadway(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["week_ending"] = pd.to_datetime(df["week_ending"])
    df = df.sort_values("week_ending").reset_index(drop=True)

    df.drop(columns=["week_number"], inplace=True)

    # Fix first-row diff placeholders
    df.loc[0, "diff_gross"] = np.nan
    df.loc[0, "diff_pct_capacity"] = np.nan

    # Label existing rows
    df["status"] = "normal"
    strike_mask = (df["weekly_gross"] == 0) & (df["performances"] == 0) & (df["previews"] == 0)
    df.loc[strike_mask, "status"] = "dark_strike"

    # Insert placeholder rows for gaps (dark weeks)
    gap_rows = []
    for i in range(1, len(df)):
        prev = df.loc[i - 1, "week_ending"]
        curr = df.loc[i, "week_ending"]
        if (curr - prev).days > 9:
            fill = prev + pd.Timedelta(days=7)
            while fill < curr:
                if pd.Timestamp("2020-03-15") <= fill <= pd.Timestamp("2021-09-12"):
                    status = "dark_covid"
                else:
                    status = "dark_break"
                gap_rows.append({"week_ending": fill, "status": status})
                fill += pd.Timedelta(days=7)

    if gap_rows:
        df = pd.concat([df, pd.DataFrame(gap_rows)], ignore_index=True)
        df = df.sort_values("week_ending").reset_index(drop=True)

    df["week_number"] = range(1, len(df) + 1)
    df["top_ticket"] = df["top_ticket"].ffill()
    df["broadway_season"] = df["week_ending"].apply(broadway_season)

    col_order = [
        "week_ending", "week_number", "broadway_season", "status",
        "weekly_gross", "diff_gross",
        "avg_ticket", "top_ticket",
        "seats_sold", "seats_in_theatre",
        "performances", "previews",
        "pct_capacity", "diff_pct_capacity",
    ]
    return df[[c for c in col_order if c in df.columns]]


# ---------------------------------------------------------------------------
# Movie cleaning (shared logic)
# ---------------------------------------------------------------------------

MOVIE_COL_ORDER = [
    "date", "day_of_week", "day_number", "phase", "rank",
    "daily_gross", "pct_change_yd", "pct_change_lw",
    "theaters", "avg_per_theater", "cumulative_gross",
]


def _base_movie_clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def clean_movie(raw: pd.DataFrame) -> pd.DataFrame:
    """Wicked (2024) — Part 1. Splits into Initial Release vs. Re-Release."""
    df = _base_movie_clean(raw)

    initial_end     = pd.Timestamp("2025-03-13")
    rerelease_start = pd.Timestamp("2025-11-14")

    def phase(date):
        if date <= initial_end:
            return "Initial Release"
        if date >= rerelease_start:
            return "Re-Release"
        return "Off-Screen"  # safety net — no rows should land here

    df["phase"] = df["date"].apply(phase)
    return df[[c for c in MOVIE_COL_ORDER if c in df.columns]]


def clean_movie2(raw: pd.DataFrame) -> pd.DataFrame:
    """Wicked: For Good (2025) — Part 2. All rows are Initial Release."""
    df = _base_movie_clean(raw)
    df["phase"] = "Initial Release"
    return df[[c for c in MOVIE_COL_ORDER if c in df.columns]]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_broadway(df):
    print("\n  --- Broadway ---")
    print(f"  Rows: {len(df)}")
    print(f"  Date range: {df.week_ending.min().date()} -> {df.week_ending.max().date()}")
    print(f"  Status: {df.status.value_counts().to_dict()}")
    normal = df[df.status == "normal"]
    top = normal.nlargest(1, "weekly_gross").iloc[0]
    print(f"  Peak week: {top.week_ending.date()} — ${top.weekly_gross:,.0f}")


def validate_movie(label, df):
    print(f"\n  --- {label} ---")
    print(f"  Rows: {len(df)}")
    print(f"  Date range: {df.date.min().date()} -> {df.date.max().date()}")
    print(f"  Phase: {df.phase.value_counts().to_dict()}")
    print(f"  Peak cumulative: ${df.cumulative_gross.max():,.0f}")
    print(f"  Opening day gross: ${df.iloc[0].daily_gross:,.0f} ({df.iloc[0].date.date()})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Wicked Analytics — Data Cleaning ===")

    # Broadway
    b_raw = pd.read_csv(RAW_BROADWAY)
    b_clean = clean_broadway(b_raw)
    validate_broadway(b_clean)
    os.makedirs(os.path.dirname(OUT_BROADWAY), exist_ok=True)
    b_clean.to_csv(OUT_BROADWAY, index=False)
    print(f"  Saved -> {OUT_BROADWAY}")

    # Wicked (2024)
    m_raw = pd.read_csv(RAW_MOVIE)
    m_clean = clean_movie(m_raw)
    validate_movie("Wicked (2024)", m_clean)
    m_clean.to_csv(OUT_MOVIE, index=False)
    print(f"  Saved -> {OUT_MOVIE}")

    # Wicked: For Good (2025)
    if os.path.exists(RAW_MOVIE2):
        m2_raw = pd.read_csv(RAW_MOVIE2)
        m2_clean = clean_movie2(m2_raw)
        validate_movie("Wicked: For Good (2025)", m2_clean)
        m2_clean.to_csv(OUT_MOVIE2, index=False)
        print(f"  Saved -> {OUT_MOVIE2}")
    else:
        print(f"\n  Wicked: For Good raw file not found — skipping.")

    print("\nDone.")


if __name__ == "__main__":
    main()
