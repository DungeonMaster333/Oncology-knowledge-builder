import json
import re
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

import requests


URL = "https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications"

OUTPUT_DIR = Path("data/issues")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class FDAParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True

        if self.in_table and tag == "tr":
            self.in_row = True
            self.current_row = []

        if self.in_row and tag in ("td", "th"):
            self.in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False

        if tag == "tr" and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_row = False

        if tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            text = " ".join(data.split())
            if text:
                self.current_row.append(text)


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_company(description):
    # FDA descriptions commonly contain:
    # drug (brand, company)
    match = re.search(
        r"\(([^(),]+),\s*([^()]+(?:Inc\.|LLC|Ltd\.|Company|Corporation|Pharma[^,)]*)?)\)",
        description,
        re.IGNORECASE,
    )

    if match:
        return clean(match.group(2))

    return "Company not specified"


def extract_asset(description):
    match = re.search(
        r"(?:approved|grants accelerated approval to|grants traditional approval to)\s+(.+?)\s+\(",
        description,
        re.IGNORECASE,
    )

    if match:
        return clean(match.group(1))

    return "Oncology asset"


def extract_date(text):
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)

    if match:
        try:
            return datetime.strptime(
                match.group(1), "%m/%d/%Y"
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def main():
    print("Fetching FDA Oncology Approval Notifications...")

    response = requests.get(
        URL,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0 Oncology-Knowledge-Builder"
        },
    )

    response.raise_for_status()

    parser = FDAParser()
    parser.feed(response.text)

    records = []

    for row in parser.rows:
        row_text = " ".join(row)

        date = extract_date(row_text)

        if not date:
            continue

        description = clean(
            row[0] if len(row) == 1 else " ".join(row)
        )

        if len(description) < 30:
            continue

        records.append({
            "source": "FDA Oncology Approval Notifications",
            "type": "REGULATORY",
            "title": description.split(".")[0][:180],
            "asset": extract_asset(description),
            "company": extract_company(description),
            "application": "Not specified",
            "action_date": date,
            "what_happened": description,
            "oncology_related": True,
        })

    # Remove duplicates
    unique = {}

    for record in records:
        key = (
            record["action_date"],
            record["title"],
        )
        unique[key] = record

    records = list(unique.values())

    # Newest first
    records.sort(
        key=lambda x: x["action_date"],
        reverse=True
    )

    # Keep latest 50 oncology approvals
    records = records[:50]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    output = {
        "source": "FDA Oncology Approval Notifications",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "records_retrieved": len(records),
        "oncology_records": len(records),
        "records": records,
    }

    output_file = OUTPUT_DIR / f"{today}-fda.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"FDA oncology records found: {len(records)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
