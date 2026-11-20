import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup


FDA_ONCOLOGY_URL = (
    "https://www.fda.gov/drugs/cancer-approvals/"
    "oncology-cancerhematologic-malignancies-approval-notifications"
)

OUTPUT_DIR = Path("data/issues")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text):
    if not text:
        return ""

    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_date(text):
    match = re.search(
        r"(\d{1,2}/\d{1,2}/\d{4})",
        text
    )

    if match:
        return match.group(1)

    match = re.search(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+"
        r"\d{1,2},\s+\d{4}",
        text
    )

    if match:
        return match.group(0)

    return ""


def extract_drug_company(text):
    """
    Extracts patterns such as:

    neladalkib (Nelkarmi, Nuvalent, Inc.)
    giredestrant (Wilserdly, Genentech, Inc.)
    """

    match = re.search(
        r"\bto\s+([a-zA-Z0-9\-]+)\s+\(([^,]+),\s*([^)]+)\)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            clean_text(match.group(1)),
            clean_text(match.group(2)),
            clean_text(match.group(3)),
        )

    # Fallback: look for "drug (brand, company)"
    match = re.search(
        r"\b([a-zA-Z0-9\-]+)\s+\(([^,]+),\s*([^)]+)\)",
        text
    )

    if match:
        return (
            clean_text(match.group(1)),
            clean_text(match.group(2)),
            clean_text(match.group(3)),
        )

    return "", "", ""


def infer_event_type(title, description):
    text = f"{title} {description}".lower()

    if "accelerated approval" in text:
        return "Accelerated approval"

    if "traditional approval" in text:
        return "Traditional approval"

    if "safety labeling update" in text:
        return "Safety / labeling update"

    if "expanded indication" in text:
        return "Expanded indication"

    if "approved" in text:
        return "FDA approval"

    return "FDA oncology update"


def extract_records(html):
    soup = BeautifulSoup(html, "html.parser")

    records = []

    # FDA page uses a table containing:
    # Webpage | Description | Date
    tables = soup.find_all("table")

    for table in tables:

        rows = table.find_all("tr")

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])

            if len(cells) < 3:
                continue

            title_cell = cells[0]
            description_cell = cells[1]
            date_cell = cells[2]

            link = title_cell.find("a")

            title = clean_text(
                title_cell.get_text(" ", strip=True)
            )

            description = clean_text(
                description_cell.get_text(
                    " ",
                    strip=True
                )
            )

            date = clean_text(
                date_cell.get_text(
                    " ",
                    strip=True
                )
            )

            if not title:
                continue

            drug, brand, company = extract_drug_company(
                description
            )

            event_type = infer_event_type(
                title,
                description
            )

            # Extract date from description if table date
            # is empty.
            if not date:
                date = extract_date(description)

            source_url = FDA_ONCOLOGY_URL

            if link and link.get("href"):
                href = link["href"]

                if href.startswith("/"):
                    source_url = (
                        "https://www.fda.gov" + href
                    )
                elif href.startswith("http"):
                    source_url = href

            records.append(
                {
                    "source": "FDA",
                    "source_type": "regulatory",

                    "title": title,

                    "drug": drug,
                    "brand": brand,
                    "company": company,

                    "event_type": event_type,
                    "approval_date": date,

                    "indication": description,

                    "what_happened": description,

                    "source_url": source_url,

                    "oncology_relevance": True,
                }
            )

    return records


def main():

    print("Fetching FDA oncology approval notifications...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; OncologyKnowledgeBuilder/1.0)"
        )
    }

    response = requests.get(
        FDA_ONCOLOGY_URL,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    records = extract_records(
        response.text
    )

    # Remove duplicates.
    unique = {}

    for record in records:
        key = (
            record["title"],
            record["approval_date"],
        )

        if key not in unique:
            unique[key] = record

    records = list(unique.values())

    # Newest first.
    records.sort(
        key=lambda x: x.get(
            "approval_date",
            ""
        ),
        reverse=True,
    )

    # Keep a reasonable number for the dashboard.
    records = records[:100]

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    output_file = (
        OUTPUT_DIR /
        f"{today}-fda.json"
    )

    output = {
        "source": "FDA Oncology Approval Notifications",

        "source_url": FDA_ONCOLOGY_URL,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "records_retrieved":
            len(records),

        "oncology_records":
            len(records),

        "records":
            records,
    }

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        "FDA oncology collection complete."
    )

    print(
        f"Oncology records: {len(records)}"
    )

    print(
        f"Saved to: {output_file}"
    )

    if records:

        print()
        print("Latest FDA records:")

        for record in records[:5]:

            print(
                f"- {record['title']} "
                f"({record['approval_date']})"
            )


if __name__ == "__main__":
    main()
