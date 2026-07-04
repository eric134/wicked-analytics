"""
scrape_boxoffice.py
Scrapes daily domestic box office for both Wicked films from Box Office Mojo.
Writes raw CSVs; skips a film if its data is already fresh (within STALENESS_DAYS).
"""

import os
import re
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

STALENESS_DAYS = 7
BASE = os.path.dirname(os.path.abspath(__file__))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

FILMS = [
    {
        "name":         "Wicked (2024)",
        "url":          "https://www.boxofficemojo.com/release/rl1199474177/",
        "release_date": datetime(2024, 11, 22),
        "csv":          os.path.join(BASE, "../data/wicked_domestic_daily.csv"),
    },
    {
        "name":         "Wicked: For Good (2025)",
        "url":          "https://www.boxofficemojo.com/release/rl2185003777/",
        "release_date": datetime(2025, 11, 17),
        "csv":          os.path.join(BASE, "../data/wicked2_domestic_daily.csv"),
    },
]

COLUMN_MAP = {
    "Date":     "date",
    "DOW":      "day_of_week",
    "Rank":     "rank",
    "Daily":    "daily_gross",
    "Theaters": "theaters",
    "Avg":      "avg_per_theater",
    "To Date":  "cumulative_gross",
    "Day":      "day_number",
}
PCT_YD_IDX = 4
PCT_LW_IDX = 5


def is_fresh(csv_path):
    if not os.path.exists(csv_path):
        return False
    try:
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty:
            return False
        latest = df["date"].max()
        age = (datetime.now() - latest).days
        print(f"  Existing data: latest={latest.date()}, age={age}d")
        return age <= STALENESS_DAYS
    except Exception:
        return False


def parse_currency(v):
    if not v or v.strip() in ("-", "n/a", ""):
        return None
    try:
        return float(re.sub(r"[$,]", "", v.strip()))
    except ValueError:
        return None


def parse_percent(v):
    if not v or v.strip() in ("-", "n/a", ""):
        return None
    try:
        return float(re.sub(r"[%+]", "", v.strip()))
    except ValueError:
        return None


def parse_int(v):
    if not v or v.strip() in ("-", "n/a", ""):
        return None
    try:
        return int(re.sub(r",", "", v.strip()))
    except ValueError:
        return None


def infer_date(date_str, release_date):
    """Box Office Mojo shows 'Nov 22' without a year — infer from release date."""
    for year in [release_date.year, release_date.year + 1, release_date.year + 2]:
        try:
            d = datetime.strptime(f"{date_str} {year}", "%b %d %Y")
            if d >= release_date:
                return d
        except ValueError:
            continue
    return None


def scrape_film(film):
    print(f"\n{'=' * 52}")
    print(f"  {film['name']}")

    if is_fresh(film["csv"]):
        print("  Up to date — skipping.")
        return

    print(f"  Fetching: {film['url']}")
    r = requests.get(film["url"], headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        print("  ERROR: No table found on page.")
        return

    all_rows = table.find_all("tr")
    raw_headers = [c.get_text(strip=True) for c in all_rows[0].find_all(["th", "td"])]
    raw_rows = [
        [td.get_text(strip=True) for td in tr.find_all("td")]
        for tr in all_rows[1:]
        if tr.find_all("td")
    ]
    print(f"  Scraped {len(raw_rows)} data rows.")

    n = len(raw_headers)
    records = []
    for row in raw_rows:
        row = row[:n] + [""] * (n - len(row))
        record = {}
        for i, h in enumerate(raw_headers):
            col = COLUMN_MAP.get(h)
            if col:
                record[col] = row[i]
        if PCT_YD_IDX < len(row):
            record["pct_change_yd"] = row[PCT_YD_IDX]
        if PCT_LW_IDX < len(row):
            record["pct_change_lw"] = row[PCT_LW_IDX]
        records.append(record)

    df = pd.DataFrame(records)
    df["date"] = df["date"].apply(lambda x: infer_date(x, film["release_date"]))
    df = df.dropna(subset=["date"])

    for col in ["daily_gross", "avg_per_theater", "cumulative_gross"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_currency)
    for col in ["pct_change_yd", "pct_change_lw"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_percent)
    for col in ["rank", "theaters", "day_number"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_int)

    df = df.sort_values("date").reset_index(drop=True)

    col_order = [
        "date", "day_of_week", "day_number", "rank",
        "daily_gross", "pct_change_yd", "pct_change_lw",
        "theaters", "avg_per_theater", "cumulative_gross",
    ]
    df = df[[c for c in col_order if c in df.columns]]

    os.makedirs(os.path.dirname(film["csv"]), exist_ok=True)
    df.to_csv(film["csv"], index=False)
    print(f"  Saved: {len(df)} rows -> {film['csv']}")
    print(f"  Date range: {df.date.min().date()} to {df.date.max().date()}")
    print(f"  Peak cumulative gross: ${df.cumulative_gross.max():,.0f}")


def main():
    print("=== Wicked Analytics — Box Office Scraper ===")
    for film in FILMS:
        scrape_film(film)
    print("\nDone.")


if __name__ == "__main__":
    main()
