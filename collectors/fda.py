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
    "multiple myeloma",
]


def collect_fda():

    params = {
        "limit": 99
    }

    response = requests.get(
        FDA_API_URL,
        params=params,
        timeout=30,
        headers={
            "User-Agent": "OncologyKnowledgeBuilder/1.0"
        }
    )

    response.raise_for_status()

    data = response.json()

    oncology_records = []

    for record in data.get("results", []):

        record_text = json.dumps(
            record,
            ensure_ascii=False
        ).lower()

        if any(
            term in record_text
            for term in ONCOLOGY_TERMS
        ):

            oncology_records.append({
                "application_number": record.get(
                    "application_number"
                ),
                "sponsor": record.get(
                    "sponsor_name"
                ),
                "products": record.get(
                    "products", []
                ),
                "submissions": record.get(
                    "submissions", []
                ),
                "openfda": record.get(
                    "openfda", {}
                )
            })

    return {
        "source": "FDA / openFDA Drugs@FDA",
        "source_url": FDA_API_URL,
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "records_retrieved": len(
            data.get("results", [])
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
