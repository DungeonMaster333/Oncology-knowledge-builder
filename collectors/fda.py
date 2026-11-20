import json
import os
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

API_URL = "https://api.fda.gov/drug/drugsfda.json"

# Broad oncology vocabulary.
# We use this only as one layer of filtering, not as the final decision.
ONCOLOGY_TERMS = [
    "cancer",
    "oncology",
    "tumor",
    "tumour",
    "carcinoma",
    "sarcoma",
    "lymphoma",
    "leukemia",
    "leukaemia",
    "myeloma",
    "melanoma",
    "neoplasm",
    "metastatic",
    "metastasis",
    "solid tumor",
    "solid tumour",
    "prostate cancer",
    "breast cancer",
    "lung cancer",
    "non-small cell lung",
    "small cell lung",
    "colorectal",
    "pancreatic cancer",
    "ovarian cancer",
    "gastric cancer",
    "bladder cancer",
    "renal cell",
    "hepatocellular",
    "cholangiocarcinoma",
    "multiple myeloma",
    "mantle cell",
    "hodgkin",
    "non-hodgkin",
    "acute myeloid",
    "acute lymphoblastic",
    "chronic lymphocytic",
    "chronic myeloid",
    "glioblastoma",
    "glioma",
    "head and neck cancer",
    "endometrial cancer",
    "cervical cancer",
    "thyroid cancer",
    "esophageal cancer",
    "esophageal carcinoma",
]

# Terms that strongly suggest the record is not useful as
# an oncology intelligence item by itself.
EXCLUDE_TERMS = [
    "veterinary",
    "animal",
    "cosmetic",
    "sunscreen",
    "acne",
    "common cold",
    "influenza",
    "covid",
    "antibiotic",
    "antibacterial",
    "antifungal",
    "migraine",
    "hypertension",
    "diabetes",
    "asthma",
    "arthritis",
    "cholesterol",
]


def fetch_json(url):
    request = Request(
        url,
        headers={
            "User-Agent": "Oncology-Knowledge-Builder/1.0",
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def clean(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(clean(v) for v in value if clean(v))

    if isinstance(value, dict):
        return " ".join(clean(v) for v in value.values() if clean(v))

    return str(value).strip()


def flatten_record(record):
    """
    Convert the nested Drugs@FDA record into searchable text.
    """
    chunks = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key not in {
                    "meta",
                    "openfda",
                }:
                    walk(item)

        elif isinstance(value, list):
            for item in value:
                walk(item)

        elif value is not None:
            chunks.append(str(value))

    walk(record)

    return " ".join(chunks).lower()


def get_first_product(record):
    products = record.get("products", [])

    if not products:
        return {}

    if isinstance(products, list):
        return products[0] if isinstance(products[0], dict) else {}

    return {}


def get_company(record):
    applications = record.get("applications", [])

    if not applications:
        return ""

    app = applications[0] if isinstance(applications, list) else applications

    if isinstance(app, dict):
        return clean(
            app.get("sponsor_name")
            or app.get("sponsor")
            or app.get("company_name")
        )

    return ""


def get_application_number(record):
    applications = record.get("applications", [])

    if not applications:
        return ""

    app = applications[0] if isinstance(applications, list) else applications

    if isinstance(app, dict):
        return clean(
            app.get("application_number")
            or app.get("application_no")
        )

    return ""


def extract_product_name(record):
    product = get_first_product(record)

    return clean(
        product.get("brand_name")
        or product.get("drug_name")
        or product.get("active_ingredient")
        or product.get("active_ingredient_name")
    )


def extract_active_ingredient(record):
    product = get_first_product(record)

    return clean(
        product.get("active_ingredient")
        or product.get("active_ingredient_name")
        or product.get("ingredient")
    )


def is_probably_oncology(record):
    """
    Conservative oncology filter.

    A record must contain an oncology term somewhere in the
    Drugs@FDA record and should not be dominated by clearly
    non-oncology terminology.
    """

    text = flatten_record(record)

    oncology_hits = [
        term for term in ONCOLOGY_TERMS
        if term.lower() in text
    ]

    if not oncology_hits:
        return False

    exclude_hits = [
        term for term in EXCLUDE_TERMS
        if term.lower() in text
    ]

    # If the record contains oncology terminology and only a weak
    # exclusion signal, retain it for downstream review.
    if exclude_hits and len(oncology_hits) < 2:
        return False

    return True


def build_intelligence_record(record):
    product_name = extract_product_name(record)
    active_ingredient = extract_active_ingredient(record)
    company = get_company(record)
    application_number = get_application_number(record)

    # Searchable text is retained for auditability.
    searchable_text = flatten_record(record)

    oncology_hits = [
        term for term in ONCOLOGY_TERMS
        if term.lower() in searchable_text
    ]

    return {
        "source": "FDA",
        "type": "regulatory",
        "title": (
            f"{product_name} — FDA regulatory update"
            if product_name
            else "FDA oncology regulatory update"
        ),
        "drug": product_name,
        "active_ingredient": active_ingredient,
        "company": company,
        "application_number": application_number,
        "oncology_terms_matched": oncology_hits[:10],
        "what_happened": "FDA regulatory development",
        "source_url": "https://www.fda.gov/drugs/cancer-approvals/"
        "oncology-cancerhematologic-malignancies-approval-notifications",
        "source_record": record,
    }


def main():
    print("Fetching FDA Drugs@FDA records...")

    all_records = []

    # openFDA allows a maximum of 99 records per request.
    # We fetch several pages to create a reasonable candidate pool.
    limit = 99

    for skip in range(0, 1000, limit):
        url = f"{API_URL}?limit={limit}&skip={skip}"

        try:
            payload = fetch_json(url)
        except Exception as exc:
            print(f"FDA request failed at skip={skip}: {exc}")
            break

        records = payload.get("results", [])

        if not records:
            break

        all_records.extend(records)

        print(
            f"Retrieved {len(all_records)} FDA records..."
        )

    print(f"Total FDA records retrieved: {len(all_records)}")

    oncology_records = []

    for record in all_records:
        if is_probably_oncology(record):
            intelligence = build_intelligence_record(record)
            oncology_records.append(intelligence)

    # Remove obvious duplicates using application + drug.
    unique = {}
    for item in oncology_records:
        key = (
            item.get("application_number", ""),
            item.get("drug", ""),
            item.get("company", ""),
        )

        if key == ("", "", ""):
            key = item.get("title", "")

        unique[key] = item

    oncology_records = list(unique.values())

    # Put records with stronger oncology evidence first.
    oncology_records.sort(
        key=lambda x: len(x.get("oncology_terms_matched", [])),
        reverse=True,
    )

    # Keep the feed manageable.
    oncology_records = oncology_records[:50]

    output = {
        "source": "FDA",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "records_retrieved": len(all_records),
        "oncology_records": len(oncology_records),
        "records": oncology_records,
    }

    os.makedirs("data/issues", exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = f"data/issues/{today}-fda.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Oncology records retained: {len(oncology_records)}")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
