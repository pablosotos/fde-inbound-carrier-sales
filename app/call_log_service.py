import os
import json
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")

HEADERS = [
    "timestamp",
    "carrier_name",
    "mc_number",
    "load_id",
    "origin",
    "destination",
    "loadboard_rate",
    "agreed_rate",
    "rate_delta",
    "counter_offers",
    "neg_rounds",
    "deal_reached",
    "call_outcome",
    "carrier_sentiment",
]


def _get_sheet():
    """Authenticate with Google Sheets using Service Account credentials."""
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not credentials_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
    if not SPREADSHEET_ID:
        raise ValueError("Missing GOOGLE_SHEET_ID environment variable")

    credentials_dict = json.loads(credentials_json)
    creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.sheet1


def _ensure_headers(sheet):
    """Write headers in row 1 if the sheet is empty."""
    first_row = sheet.row_values(1)
    if not first_row:
        sheet.append_row(HEADERS)


def append_call_log(data: dict):
    """Append a single call record to the Google Sheet."""
    sheet = _get_sheet()
    _ensure_headers(sheet)

    # Calculate rate_delta (agreed_rate - loadboard_rate)
    try:
        rate_delta = float(data.get("agreed_rate") or 0) - float(data.get("loadboard_rate") or 0)
    except (ValueError, TypeError):
        rate_delta = ""

    row = [
        datetime.now(timezone.utc).isoformat(),
        data.get("carrier_name", ""),
        data.get("mc_number", ""),
        data.get("load_id", ""),
        data.get("origin", ""),
        data.get("destination", ""),
        data.get("loadboard_rate", ""),
        data.get("agreed_rate", ""),
        rate_delta,
        data.get("counter_offers", ""),
        data.get("neg_rounds", ""),
        data.get("deal_reached", ""),
        data.get("call_outcome", ""),
        data.get("carrier_sentiment", ""),
    ]
    sheet.append_row(row)


def read_all_logs() -> list[dict]:
    """Return all logged calls as a list of dicts (for the /call-logs endpoint)."""
    sheet = _get_sheet()
    records = sheet.get_all_records()
    return records