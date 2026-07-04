import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time

# Playbill weekly grosses for Wicked Broadway (production ID: 00000150-aea6-d936-a7fd-eef6ecdd0001)
BASE_URL = "https://playbill.com/production/gross{page}?production=00000150-aea6-d936-a7fd-eef6ecdd0001"
CSV_PATH = os.path.join(os.path.dirname(__file__), "../data/wicked_broadway_weekly.csv")
STALENESS_DAYS = 7
REQUEST_DELAY = 1.5  # seconds between page requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_data_fresh():
    if not os.path.exists(CSV_PATH):
        return False
    try:
        df = pd.read_csv(CSV_PATH, parse_dates=["week_ending"])
        if df.empty:
            return False
        latest = df["week_ending"].max()
        age_days = (datetime.now() - latest).days
        print(f"Existing data found. Latest week: {latest.date()} ({age_days} days ago)")
        return age_days <= STALENESS_DAYS
    except Exception:
        return False


def parse_page(soup):
    """Extract all rows from one page's table. Returns list of dicts."""
    table = soup.find("table")
    if not table:
        return None

    rows = table.find_all("tr")
    if not rows:
        return None

    records = []
    for tr in rows:
        cells = tr.find_all("td")
        if not cells:
            continue

        record = {}
        for td in cells:
            label = td.get("data-label", "").strip()
            sort_val = td.get("data-sort-value")
            primary = td.find(class_="data-value")
            subtext = td.find(class_="subtext")

            primary_text = primary.get_text(strip=True) if primary else ""
            subtext_text = subtext.get_text(strip=True) if subtext else ""

            if label == "Week Ending":
                try:
                    record["week_ending"] = datetime.strptime(primary_text, "%b %d, %Y")
                except ValueError:
                    record["week_ending"] = None

            elif label == "Week Number":
                record["week_number"] = int(sort_val) if sort_val else None

            elif label == "This Week Gross":
                record["weekly_gross"] = float(sort_val) if sort_val else None

            elif label == "Diff $":
                record["diff_gross"] = float(sort_val) if sort_val else None

            elif label == "Avg Ticket":
                record["avg_ticket"] = float(sort_val) if sort_val else None
                record["top_ticket"] = _parse_currency(subtext_text)

            elif label == "Seats Sold":
                record["seats_sold"] = int(sort_val) if sort_val else None
                record["seats_in_theatre"] = _parse_int(subtext_text)

            elif label == "Perfs":
                record["performances"] = int(sort_val) if sort_val else None
                record["previews"] = _parse_int(subtext_text)

            elif label == "% Cap":
                record["pct_capacity"] = float(sort_val) if sort_val else None

            elif label == "Diff % cap":
                record["diff_pct_capacity"] = float(sort_val) if sort_val else None

        if record:
            records.append(record)

    return records


def _parse_currency(text):
    if not text:
        return None
    try:
        return float(text.replace("$", "").replace(",", ""))
    except ValueError:
        return None


def _parse_int(text):
    if not text:
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


def scrape_all_pages():
    all_records = []
    page_num = 1

    while True:
        page_suffix = "" if page_num == 1 else f"/p{page_num}"
        url = BASE_URL.format(page=page_suffix)
        print(f"Fetching page {page_num}: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  ERROR on page {page_num}: {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        records = parse_page(soup)

        if not records:
            print(f"  No data on page {page_num}. Stopping.")
            break

        print(f"  Got {len(records)} rows.")
        all_records.extend(records)

        # Full pages hold 52 weeks; a short page means we've hit the end
        if len(records) < 52:
            print("  Last page reached.")
            break

        page_num += 1
        time.sleep(REQUEST_DELAY)

    return all_records


def build_dataframe(records):
    df = pd.DataFrame(records)
    df = df.dropna(subset=["week_ending"])
    df = df.sort_values("week_ending").reset_index(drop=True)

    col_order = [
        "week_ending", "week_number",
        "weekly_gross", "diff_gross",
        "avg_ticket", "top_ticket",
        "seats_sold", "seats_in_theatre",
        "performances", "previews",
        "pct_capacity", "diff_pct_capacity",
    ]
    df = df[[c for c in col_order if c in df.columns]]
    return df


def main():
    if is_data_fresh():
        df = pd.read_csv(CSV_PATH)
        print(f"Data is up to date (within {STALENESS_DAYS} days). No scrape needed.")
        print(f"Dataset: {len(df)} rows, {len(df.columns)} columns.")
        return

    print("Data is stale or missing. Scraping all pages...")
    records = scrape_all_pages()

    if not records:
        print("No data collected. Exiting.")
        return

    df = build_dataframe(records)

    print(f"\nCleaned dataset: {len(df)} rows")
    print(df.head(5).to_string())
    print("...")
    print(df.tail(5).to_string())
    print(f"\nDate range: {df['week_ending'].min().date()} to {df['week_ending'].max().date()}")
    print(f"Total Broadway gross: ${df['weekly_gross'].sum():,.0f}")
    print(f"Columns: {list(df.columns)}")

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    df.to_csv(CSV_PATH, index=False)
    print(f"\nSaved to: {CSV_PATH}")


if __name__ == "__main__":
    main()
