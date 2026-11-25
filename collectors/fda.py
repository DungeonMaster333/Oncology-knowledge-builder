import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


OUTPUT_DIR = Path("data/issues")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://api.fda.gov/drug/drugsfda.json"

ONCOLOGY_TERMS = [
    "cancer",
    "oncology",
    "tumor",
    "tumour",
    "carcinoma",
    "lymphoma",
    "leukemia",
    "leukaemia",
    "melanoma",
    "sarcoma",
    "myeloma",
    "glioma",
    "glioblastoma",
    "metastatic",
    "neoplasm",
    "neuroblastoma",
    "prostate",
    "breast cancer",
    "lung cancer",
    "colorectal",
    "pancreatic",
    "ovarian",
    "gastric",
    "hepatic",
    "renal cell",
    "bladder cancer",
    "multiple myeloma",
]


def is_oncology_record(record):
    text = json.dumps(record, ensure_ascii=False).lower()
    return any(term in text for term in ONCOLOGY_TERMS)


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def extract_record(record):
    products = record.get("products", [])
    applications = record.get("applications", [])

    product = products[0] if products else {}
    application = applications[0] if applications else {}

    return {
        "source": "FDA",
        "type": "REGULATORY",
        "title": clean_text(product.get("brand_name"))
                 or clean_text(product.get("active_ingredients"))
                 or "FDA oncology regulatory update",

        "asset": clean_text(product.get("brand_name"))
                 or clean_text(product.get("active_ingredients"))
                 or "Not specified",

        "company": clean_text(application.get("sponsor_name"))
                   or "Company not specified",

        "application": clean_text(record.get("application_number"))
                       or clean_text(application.get("application_number"))
                       or "Not specified",

        "action_date": clean_text(record.get("submission", [{}])[0].get("submission_status_date"))
                       if record.get("submission") else "",

        "what_happened": "FDA regulatory development",

        "oncology_related": True,
    }


def main():
    print("Fetching FDA Drugs@FDA data...")

    response = requests.get(
        API_URL,
        params={"limit": 1000},
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()
    records = data.get("results", [])

    oncology_records = [
        extract_record(record)
        for record in records
        if is_oncology_record(record)
    ]

    # Remove obvious duplicates
    unique = {}
    for item in oncology_records:
        key = (
            item["asset"],
            item["company"],
            item["application"],
        )
        unique[key] = item

    oncology_records = list(unique.values())

    output = {
        "source": "FDA / openFDA Drugs@FDA",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "records_retrieved": len(records),
        "oncology_records": len(oncology_records),
        "records": oncology_records,
    }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{today}-fda.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"FDA records retrieved: {len(records)}")
    print(f"Oncology records found: {len(oncology_records)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
