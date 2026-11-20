import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


FDA_URL = "https://api.fda.gov/drug/drugsfda.json"

OUTPUT_DIR = Path("data/issues")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ONCOLOGY_TERMS = [
    "cancer",
    "oncology",
    "carcinoma",
    "sarcoma",
    "lymphoma",
    "leukemia",
    "myeloma",
    "melanoma",
    "tumor",
    "tumour",
    "neoplasm",
    "neoplastic",
    "metastatic",
    "metastasis",
    "solid tumor",
    "solid tumour",
    "prostate",
    "breast cancer",
    "lung cancer",
    "colorectal",
    "colorectal cancer",
    "pancreatic",
    "ovarian",
    "gastric cancer",
    "bladder cancer",
    "renal cell",
    "kidney cancer",
    "hepatocellular",
    "liver cancer",
    "glioma",
    "glioblastoma",
    "head and neck cancer",
    "multiple myeloma",
    "acute myeloid",
    "acute lymphoblastic",
    "chronic lymphocytic",
    "chronic myeloid",
    "non-small cell",
    "small cell lung",
    "immunotherapy",
    "antineoplastic",
    "antitumor",
    "antitumour",
    "chemotherapy",
    "checkpoint inhibitor",
    "car-t",
    "bispecific",
]


def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(clean_text(x) for x in value if clean_text(x))

    if isinstance(value, dict):
        return ", ".join(
            f"{k}: {clean_text(v)}"
            for k, v in value.items()
            if clean_text(v)
        )

    return str(value).strip()


def normalize(value):
    return re.sub(r"\s+", " ", clean_text(value)).strip()


def contains_oncology_terms(value):
    text = normalize(value).lower()
    return any(term in text for term in ONCOLOGY_TERMS)


def first_non_empty(*values):
    for value in values:
        cleaned = normalize(value)
        if cleaned:
            return cleaned
    return ""


def extract_products(record):
    products = []

    for product in record.get("products", []) or []:
        products.append(
            {
                "brand_name": normalize(product.get("brand_name")),
                "active_ingredients": normalize(
                    product.get("active_ingredients")
                ),
                "dosage_form": normalize(product.get("dosage_form")),
                "route": normalize(product.get("route")),
                "marketing_status": normalize(
                    product.get("marketing_status")
                ),
                "te_code": normalize(product.get("te_code")),
            }
        )

    return products


def extract_submissions(record):
    submissions = []

    for submission in record.get("submissions", []) or []:
        submissions.append(
            {
                "submission_number": normalize(
                    submission.get("submission_number")
                ),
                "submission_type": normalize(
                    submission.get("submission_type")
                ),
                "submission_status": normalize(
                    submission.get("submission_status")
                ),
                "submission_class_code": normalize(
                    submission.get("submission_class_code")
                ),
                "submission_class_code_description": normalize(
                    submission.get("submission_class_code_description")
                ),
                "action_type": normalize(
                    submission.get("action_type")
                ),
                "submission_publication_date": normalize(
                    submission.get("submission_publication_date")
                ),
                "review_priority": normalize(
                    submission.get("review_priority")
                ),
            }
        )

    return submissions


def choose_product(products):
    if not products:
        return {}

    # Prefer products with an actual brand name.
    branded = [p for p in products if p.get("brand_name")]
    if branded:
        return branded[0]

    return products[0]


def build_event_title(record, product, submission):
    brand = product.get("brand_name", "")
    ingredient = product.get("active_ingredients", "")
    action = submission.get("action_type", "")

    asset = first_non_empty(brand, ingredient, record.get("application_number"))

    if action:
        return f"{asset} — FDA {action}"

    return f"{asset} — FDA regulatory update"


def build_event_description(record, product, submission):
    parts = []

    action = submission.get("action_type")
    submission_type = submission.get("submission_type")
    status = submission.get("submission_status")
    application = record.get("application_number")

    if action:
        parts.append(action)

    if submission_type:
        parts.append(submission_type)

    if status:
        parts.append(status)

    if application:
        parts.append(f"Application {application}")

    return " · ".join(parts) or "FDA regulatory development"


def process_record(record):
    products = extract_products(record)
    submissions = extract_submissions(record)

    # Search the entire FDA record for oncology relevance.
    searchable = json.dumps(record, ensure_ascii=False)

    if not contains_oncology_terms(searchable):
        return None

    product = choose_product(products)

    # Prefer the most recent submission with a publication date.
    dated_submissions = [
        s
        for s in submissions
        if s.get("submission_publication_date")
    ]

    if dated_submissions:
        dated_submissions.sort(
            key=lambda x: x["submission_publication_date"],
            reverse=True,
        )
        submission = dated_submissions[0]
    elif submissions:
        submission = submissions[0]
    else:
        submission = {}

    brand = product.get("brand_name", "")
    ingredient = product.get("active_ingredients", "")

    asset = first_non_empty(
        brand,
        ingredient,
        record.get("application_number"),
    )

    company = first_non_empty(
        record.get("sponsor_name"),
        record.get("sponsor"),
        "Not specified",
    )

    oncology_match = [
        term
        for term in ONCOLOGY_TERMS
        if term.lower() in searchable.lower()
    ]

    return {
        "source": "FDA",
        "source_type": "regulatory",
        "title": build_event_title(
            record,
            product,
            submission,
        ),
        "asset": asset,
        "brand_name": brand,
        "active_ingredients": ingredient,
        "company": company,
        "application_number": normalize(
            record.get("application_number")
        ),
        "application_type": normalize(
            record.get("application_type")
        ),
        "dosage_form": product.get("dosage_form", ""),
        "route": product.get("route", ""),
        "marketing_status": product.get(
            "marketing_status",
            "",
        ),
        "submission_number": submission.get(
            "submission_number",
            "",
        ),
        "submission_type": submission.get(
            "submission_type",
            "",
        ),
        "action_type": submission.get(
            "action_type",
            "",
        ),
        "submission_status": submission.get(
            "submission_status",
            "",
        ),
        "submission_date": submission.get(
            "submission_publication_date",
            "",
        ),
        "what_happened": build_event_description(
            record,
            product,
            submission,
        ),
        "oncology_relevance": True,
        "oncology_matches": oncology_match[:10],
        "source_url": (
            "https://www.accessdata.fda.gov/"
            "scripts/cder/daf/"
        ),
    }


def main():
    print("Fetching FDA Drugs@FDA data...")

    all_records = []
    limit = 100
    max_batches = 10

    for skip in range(0, limit * max_batches, limit):
        params = {
            "limit": limit,
            "skip": skip,
        }

        response = requests.get(
            FDA_URL,
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        payload = response.json()
        batch = payload.get("results", [])

        if not batch:
            break

        all_records.extend(batch)

        print(
            f"Retrieved {len(all_records)} FDA records..."
        )

        if len(batch) < limit:
            break

    processed = []

    for record in all_records:
        item = process_record(record)

        if item:
            processed.append(item)

    # Remove duplicate application/asset combinations.
    unique = {}
    for item in processed:
        key = (
            item.get("application_number", ""),
            item.get("submission_number", ""),
            item.get("asset", ""),
        )

        if key not in unique:
            unique[key] = item

    processed = list(unique.values())

    # Most recent first.
    processed.sort(
        key=lambda x: (
            x.get("submission_date", ""),
            x.get("asset", ""),
        ),
        reverse=True,
    )

    # Keep the feed manageable.
    processed = processed[:100]

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    output_file = (
        OUTPUT_DIR / f"{today}-fda.json"
    )

    output = {
        "source": "FDA",
        "source_url": FDA_URL,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "records_retrieved": len(all_records),
        "oncology_records": len(processed),
        "records": processed,
    }

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("FDA collection complete.")
    print(
        f"Records retrieved: {len(all_records)}"
    )
    print(
        f"Oncology records: {len(processed)}"
    )
    print(
        f"Saved to: {output_file}"
    )


if __name__ == "__main__":
    main()
