import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CALL_LOG_FILE = Path(__file__).resolve().parent / "call_logs.csv"

FIELDNAMES = [
    "timestamp",
    "carrier_name",
    "mc_number",
    "load_id",
    "origin",
    "destination",
    "loadboard_rate",
    "agreed_rate",
    "counter_offers",
    "neg_rounds",
    "deal_reached",
    "call_outcome",
    "carrier_sentiment",
]


def ensure_csv_exists():
    """Create the CSV with headers if it doesn't exist yet."""
    if not CALL_LOG_FILE.exists():
        with open(CALL_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_call_log(data: dict):
    """Append a single call record to call_logs.csv."""
    ensure_csv_exists()
    row = {field: data.get(field, "") for field in FIELDNAMES}
    # Always stamp the server-side UTC time
    row["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(CALL_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)


def read_all_logs() -> list[dict]:
    """Return all logged calls as a list of dicts."""
    ensure_csv_exists()
    with open(CALL_LOG_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))