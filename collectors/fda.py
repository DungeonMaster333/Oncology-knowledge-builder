import requests
from datetime import datetime, timezone
import json
import os

FDA_API_URL = "https://api.fda.gov/drug/drugsfda.json"

ONCOLOGY_TERMS = [
    "cancer",
    "oncology",
    "tumor",
    "tumour",
    "carcinoma",
    "lymphoma",
    "leukemia",
    "leukaemia",
    "myeloma",
    "sarcoma",
    "melanoma",
    "metastatic",
    "neoplasm",
    "non-small cell",
    "small cell",
    "breast cancer",
    "lung cancer",
    "prostate cancer",
    "colorectal cancer",
    "pancreatic cancer",
    "ovarian cancer",
    "endometrial cancer",
    "gastric cancer",
    "bladder cancer",
    "renal cell",
    "hepatocellular",
    "multiple myeloma",
]


def collect_fda():

    all_records = []

    skip = 0
    batch_size = 100

    # Retrieve several batches instead of only the first 99 records
    for _ in range(10):

        params = {
            "limit": batch_size,
            "skip": skip
        }

        response = requests.get(
            FDA_API_URL,
            params=params,
            timeout=30,
            headers={
                "User-Agent": "OncologyKnowledgeBuilder/1.0"
            }
        )

        if response.status_code == 404:
            break

        response.raise_for_status()

        data = response.json()

        records = data.get("results", [])

        if not records:
            break

        all_records.extend(records)

        skip += batch_size

    oncology_records = []

    for record in all_records:

        record_text = json.dumps(
            record,
            ensure_ascii=False
        ).lower()

        matched_terms = [
            term
            for term in ONCOLOGY_TERMS
            if term in record_text
        ]

        if matched_terms:

            products = record.get("products", [])

            submissions = record.get(
                "submissions", []
            )

            oncology_records.append({
                "application_number": record.get(
                    "application_number"
                ),
                "sponsor": record.get(
                    "sponsor_name"
                ),
                "matched_terms": matched_terms,
                "products": products,
                "submissions": submissions
            })

    return {
        "source": "FDA / openFDA Drugs@FDA",
        "source_url": FDA_API_URL,
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "records_retrieved": len(
            all_records
        ),
        "oncology_records": len(
            oncology_records
        ),
        "records": oncology_records
    }


def save_result(result):

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    os.makedirs(
        "data/issues",
        exist_ok=True
    )

    filename = (
        f"data/issues/{today}-fda.json"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Saved FDA data to {filename}"
    )


if __name__ == "__main__":

    result = collect_fda()

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    save_result(result)
