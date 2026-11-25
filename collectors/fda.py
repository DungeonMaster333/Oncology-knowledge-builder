import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

FDA_URL = (
    "https://www.fda.gov/drugs/cancer-approvals/"
    "oncology-cancerhematologic-malignancies-approval-notifications"
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "issues"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / (
    f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-fda.json"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_date(text):
    """
    Extract a date such as:
    On November 24, 2026
    """
    match = re.search(
        r"(?:On\s+)?"
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+"
        r"(\d{1,2}),\s+(\d{4})",
        text,
        re.IGNORECASE
    )

    if not match:
        return ""

    month = match.group(1)
    day = match.group(2)
    year = match.group(3)

    try:
        dt = datetime.strptime(
            f"{month} {day} {year}",
            "%B %d %Y"
        )
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def extract_drug_and_company(title, description):
    """
    Extract useful drug/company information from FDA wording.
    Example:
    FDA approves bezuclastinib ... (Ekitna, Cogent Biosciences, Inc)
    """

    drug_name = ""
    brand_name = ""
    company = ""

    text = f"{title} {description}"

    # Generic/asset name is generally the first word after
    # approved/grants accelerated approval to.
    patterns = [
        r"(?:approves|approved|approval to|approval for|"
        r"accelerated approval to|traditional approval to)\s+"
        r"([A-Za-z0-9\-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)

        if match:
            drug_name = match.group(1)
            break

    # FDA commonly writes:
    # drug (Brand, Company)
    paren = re.search(
        r"\(([^()]+),\s*([^()]+)\)",
        description
    )

    if paren:
        brand_name = clean_text(paren.group(1))
        company = clean_text(paren.group(2))

    return drug_name, brand_name, company


def is_oncology_record(title, description):
    """
    Safety check.
    The source itself is oncology-specific, but retain a small
    validation layer so unrelated content is not accidentally
    surfaced if FDA changes page structure.
    """

    text = f"{title} {description}".lower()

    oncology_terms = [
        "cancer",
        "carcinoma",
        "tumor",
        "tumour",
        "oncolog",
        "lymphoma",
        "leukemia",
        "myeloma",
        "melanoma",
        "sarcoma",
        "glioma",
        "blastoma",
        "neoplasm",
        "nsclc",
        "small cell lung",
        "breast cancer",
        "prostate cancer",
        "bladder cancer",
        "colorectal",
        "cholangiocarcinoma",
        "hepatocellular",
        "pancreatic",
        "ovarian",
        "gastric",
        "esophageal",
        "head and neck",
        "multiple myeloma",
        "hematologic",
        "haematologic",
        "solid tumor",
        "solid tumour",
    ]

    return any(term in text for term in oncology_terms)


# ============================================================
# MAIN COLLECTION
# ============================================================

def main():

    print("Fetching FDA Oncology Approval Notifications...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; OncologyKnowledgeBuilder/1.0)"
        )
    }

    response = requests.get(
        FDA_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    records = []

    # FDA page presents approval notifications in a table.
    tables = soup.find_all("table")

    print(f"FDA tables found: {len(tables)}")

    for table in tables:

        tbody = table.find("tbody")

        if not tbody:
            continue

        rows = tbody.find_all("tr")

        for row in rows:

            cells = row.find_all(["td", "th"])

            if len(cells) < 2:
                continue

            title = clean_text(cells[0].get_text(" ", strip=True))
            description = clean_text(cells[1].get_text(" ", strip=True))

            date_text = ""

            if len(cells) >= 3:
                date_text = clean_text(
                    cells[2].get_text(" ", strip=True)
                )

            if not title:
                continue

            if not is_oncology_record(title, description):
                continue

            date = extract_date(
                f"{date_text} {description}"
            )

            drug_name, brand_name, company = (
                extract_drug_and_company(
                    title,
                    description
                )
            )

            records.append({
                "source": "FDA Oncology Approval Notifications",
                "title": title,
                "description": description,
                "date": date or date_text,
                "drug_name": drug_name,
                "brand_name": brand_name,
                "company": company,
                "url": FDA_URL
            })

    # Remove duplicates
    unique = {}

    for record in records:

        key = (
            record["title"],
            record["date"]
        )

        unique[key] = record

    records = list(unique.values())

    # Sort newest first
    records.sort(
        key=lambda x: x.get("date", ""),
        reverse=True
    )

    # Keep latest 50
    records = records[:50]

    output = {
        "source": "FDA Oncology Approval Notifications",
        "source_url": FDA_URL,
        "retrieved_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "records_retrieved": len(records),
        "records": records
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("")
    print("========================================")
    print("FDA oncology collection completed")
    print(f"Records retrieved: {len(records)}")
    print(f"Output: {OUTPUT_FILE}")
    print("========================================")

    # Print first 5 for GitHub Actions verification
    for i, record in enumerate(records[:5], 1):

        print("")
        print(f"{i}. {record['title']}")
        print(f"   Date: {record['date']}")
        print(f"   Drug: {record['drug_name']}")
        print(f"   Company: {record['company']}")


if __name__ == "__main__":
    main()
