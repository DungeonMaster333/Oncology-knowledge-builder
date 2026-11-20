import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


FDA_DRUGS_URL = "https://api.fda.gov/drug/drugsfda.json"
FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

OUTPUT_DIR = "data/issues"

MAX_RECORDS_TO_FETCH = 1000
MAX_ONCOLOGY_RECORDS = 50


# Strong oncology terms.
# These are intentionally NOT searched across the entire raw FDA record.
ONCOLOGY_TERMS = [
    "cancer",
    "oncology",
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
    "tumor",
    "tumour",
    "glioblastoma",
    "glioma",
    "prostate cancer",
    "breast cancer",
    "lung cancer",
    "colorectal cancer",
    "pancreatic cancer",
    "ovarian cancer",
    "gastric cancer",
    "bladder cancer",
    "renal cell carcinoma",
    "hepatocellular carcinoma",
    "cholangiocarcinoma",
    "multiple myeloma",
    "endometrial cancer",
    "cervical cancer",
    "thyroid cancer",
    "esophageal cancer",
    "head and neck cancer",
    "acute myeloid leukemia",
    "acute lymphoblastic leukemia",
    "chronic lymphocytic leukemia",
    "chronic myeloid leukemia",
    "non-small cell lung",
    "small cell lung",
]


# Strong pharmacologic indicators of oncology.
ONCOLOGY_CLASS_TERMS = [
    "antineoplastic",
    "antineoplastic agent",
    "antineoplastic drug",
    "antineoplastic activity",
    "cancer chemotherapy",
    "oncology",
    "tumor inhibitor",
    "tumour inhibitor",
]


# Known oncology / hematology drug signals.
# This is deliberately broader than just brand names.
ONCOLOGY_DRUG_TERMS = [
    "relugolix",
    "darolutamide",
    "apalutamide",
    "enzalutamide",
    "abiraterone",
    "leuprolide",
    "degarelix",
    "goserelin",
    "triptorelin",
    "letrozole",
    "anastrozole",
    "exemestane",
    "tamoxifen",
    "fulvestrant",
    "palbociclib",
    "ribociclib",
    "abemaciclib",
    "trastuzumab",
    "pertuzumab",
    "ado-trastuzumab",
    "fam-trastuzumab",
    "sacituzumab",
    "datopotamab",
    "pembrolizumab",
    "nivolumab",
    "ipilimumab",
    "atezolizumab",
    "durvalumab",
    "cemiplimab",
    "dostarlimab",
    "retifanlimab",
    "tislelizumab",
    "toripalimab",
    "axitinib",
    "sunitinib",
    "pazopanib",
    "cabozantinib",
    "lenvatinib",
    "sorafenib",
    "osimertinib",
    "gefitinib",
    "erlotinib",
    "afatinib",
    "lorlatinib",
    "alectinib",
    "brigatinib",
    "crizotinib",
    "dacomitinib",
    "adagrasib",
    "sotorasib",
    "encorafenib",
    "vemurafenib",
    "dabrafenib",
    "trametinib",
    "binimetinib",
    "selumetinib",
    "olaparib",
    "niraparib",
    "rucaparib",
    "talazoparib",
    "capmatinib",
    "tepotinib",
    "repotrectinib",
    "amivantamab",
    "mobocertinib",
    "zanubrutinib",
    "ibrutinib",
    "acalabrutinib",
    "pirtobrutinib",
    "venetoclax",
    "rituximab",
    "obinutuzumab",
    "mosunetuzumab",
    "glofitamab",
    "epcoritamab",
    "elranatamab",
    "teclistamab",
    "talquetamab",
    "daratumumab",
    "carfilzomib",
    "bortezomib",
    "lenalidomide",
    "pomalidomide",
    "azacitidine",
    "decitabine",
    "cytarabine",
    "daunorubicin",
    "doxorubicin",
    "etoposide",
    "cisplatin",
    "carboplatin",
    "oxaliplatin",
    "irinotecan",
    "paclitaxel",
    "docetaxel",
    "gemcitabine",
    "capecitabine",
    "fluorouracil",
    "temozolomide",
    "pemetrexed",
    "enzalutamide",
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


def safe_fetch_json(url):
    try:
        return fetch_json(url)
    except (HTTPError, URLError, TimeoutError, Exception):
        return None


def clean(value):
    if value is None:
        return ""

    if isinstance(value, list):
        values = [clean(v) for v in value]
        values = [v for v in values if v]
        return ", ".join(values)

    if isinstance(value, dict):
        return ""

    return str(value).strip()


def first(value):
    if isinstance(value, list) and value:
        return clean(value[0])

    return clean(value)


def extract_products(record):
    products = record.get("products", [])

    if isinstance(products, list):
        return products

    return []


def extract_brand_name(record):
    """
    Prefer the openFDA harmonized brand name.
    Fall back to products[].brand_name.
    """

    openfda = record.get("openfda", {})

    brand = first(openfda.get("brand_name"))

    if brand:
        return brand

    for product in extract_products(record):
        brand = clean(product.get("brand_name"))
        if brand:
            return brand

    return ""


def extract_generic_name(record):
    """
    Prefer openFDA generic name.
    Fall back to products[].active_ingredients[].name.
    """

    openfda = record.get("openfda", {})

    generic = first(openfda.get("generic_name"))

    if generic:
        return generic

    ingredients = []

    for product in extract_products(record):
        for ingredient in product.get("active_ingredients", []):
            if isinstance(ingredient, dict):
                name = clean(ingredient.get("name"))

                if name and name not in ingredients:
                    ingredients.append(name)

    return ", ".join(ingredients)


def extract_strength(record):
    strengths = []

    for product in extract_products(record):
        for ingredient in product.get("active_ingredients", []):
            if isinstance(ingredient, dict):
                name = clean(ingredient.get("name"))
                strength = clean(ingredient.get("strength"))

                if name and strength:
                    strengths.append(f"{name} {strength}")
                elif strength:
                    strengths.append(strength)

    return ", ".join(dict.fromkeys(strengths))


def extract_dosage_form(record):
    forms = []

    for product in extract_products(record):
        value = clean(product.get("dosage_form"))

        if value and value not in forms:
            forms.append(value)

    return ", ".join(forms)


def extract_route(record):
    routes = []

    for product in extract_products(record):
        value = clean(product.get("route"))

        if value and value not in routes:
            routes.append(value)

    if routes:
        return ", ".join(routes)

    openfda = record.get("openfda", {})
    return first(openfda.get("route"))


def extract_pharm_classes(record):
    openfda = record.get("openfda", {})

    classes = []

    for field in [
        "pharm_class_epc",
        "pharm_class_moa",
        "pharm_class_pe",
        "pharm_class_cs",
    ]:
        values = openfda.get(field, [])

        if isinstance(values, list):
            for value in values:
                value = clean(value)

                if value and value not in classes:
                    classes.append(value)

    return classes


def extract_sponsor(record):
    return clean(record.get("sponsor_name"))


def extract_application_number(record):
    return clean(record.get("application_number"))


def extract_latest_submission(record):
    submissions = record.get("submissions", [])

    if not isinstance(submissions, list):
        return None

    valid = []

    for submission in submissions:
        if not isinstance(submission, dict):
            continue

        date = clean(submission.get("submission_status_date"))

        if date:
            valid.append(submission)

    if not valid:
        return None

    valid.sort(
        key=lambda x: clean(x.get("submission_status_date")),
        reverse=True,
    )

    return valid[0]


def build_search_text(record):
    """
    IMPORTANT:
    Only search fields that actually describe the drug/application.
    Do NOT flatten the complete FDA JSON.
    """

    parts = [
        extract_brand_name(record),
        extract_generic_name(record),
        extract_sponsor(record),
        extract_strength(record),
    ]

    parts.extend(extract_pharm_classes(record))

    submission = extract_latest_submission(record)

    if submission:
        parts.extend(
            [
                clean(submission.get("submission_class_code_description")),
                clean(submission.get("submission_public_notes")),
                clean(submission.get("submission_type")),
            ]
        )

    return " ".join(parts).lower()


def oncology_signal(record):
    text = build_search_text(record)

    strong_drug_hits = [
        term
        for term in ONCOLOGY_DRUG_TERMS
        if term.lower() in text
    ]

    class_hits = [
        term
        for term in ONCOLOGY_CLASS_TERMS
        if term.lower() in text
    ]

    disease_hits = [
        term
        for term in ONCOLOGY_TERMS
        if term.lower() in text
    ]

    score = (
        len(strong_drug_hits) * 5
        + len(class_hits) * 4
        + len(disease_hits) * 3
    )

    return {
        "score": score,
        "drug_hits": strong_drug_hits,
        "class_hits": class_hits,
        "disease_hits": disease_hits,
    }


def is_oncology(record):
    signal = oncology_signal(record)

    # Strong known oncology drug signal
    if signal["drug_hits"]:
        return True

    # Strong pharmacologic class signal
    if signal["class_hits"]:
        return True

    # Require TWO disease/oncology signals if there is
    # no strong drug/class signal.
    if len(signal["disease_hits"]) >= 2:
        return True

    return False


def get_label_indication(record):
    """
    Optional second-stage check.

    For records that already look oncology-related, query the
    FDA label API and look specifically at indications/use text.
    """

    brand = extract_brand_name(record)

    if not brand:
        return ""

    query = quote(f'openfda.brand_name:"{brand}"')
    url = f"{FDA_LABEL_URL}?search={query}&limit=1"

    payload = safe_fetch_json(url)

    if not payload:
        return ""

    results = payload.get("results", [])

    if not results:
        return ""

    label = results[0]

    indication = label.get("indications_and_usage", [])

    return first(indication)


def extract_oncology_indication(record):
    indication = get_label_indication(record)

    if not indication:
        return ""

    lower = indication.lower()

    matches = [
        term
        for term in ONCOLOGY_TERMS
        if term.lower() in lower
    ]

    if not matches:
        return ""

    # Keep the useful indication text short.
    text = re.sub(r"\s+", " ", indication).strip()

    if len(text) > 700:
        text = text[:700].rsplit(" ", 1)[0] + "..."

    return text


def build_intelligence_record(record):
    brand = extract_brand_name(record)
    generic = extract_generic_name(record)
    sponsor = extract_sponsor(record)
    application = extract_application_number(record)

    latest = extract_latest_submission(record)

    signal = oncology_signal(record)

    indication = extract_oncology_indication(record)

    if brand and generic:
        title = f"{brand} ({generic}) — FDA regulatory update"
    elif brand:
        title = f"{brand} — FDA regulatory update"
    elif generic:
        title = f"{generic} — FDA regulatory update"
    else:
        title = "FDA oncology regulatory update"

    submission_type = ""
    submission_status = ""
    submission_date = ""
    review_priority = ""

    if latest:
        submission_type = clean(
            latest.get("submission_type")
        )
        submission_status = clean(
            latest.get("submission_status")
        )
        submission_date = clean(
            latest.get("submission_status_date")
        )
        review_priority = clean(
            latest.get("review_priority")
        )

    if indication:
        what_happened = (
            f"FDA regulatory activity for {brand or generic}. "
            f"Oncology indication context: {indication}"
        )
    else:
        what_happened = (
            f"FDA regulatory activity for {brand or generic}."
        )

    return {
        "source": "FDA",
        "type": "regulatory",

        "title": title,

        "drug": brand,
        "active_ingredient": generic,
        "strength": extract_strength(record),

        "company": sponsor,
        "application_number": application,

        "dosage_form": extract_dosage_form(record),
        "route": extract_route(record),

        "submission_type": submission_type,
        "submission_status": submission_status,
        "submission_status_date": submission_date,
        "review_priority": review_priority,

        "oncology_indication": indication,

        "oncology_signal": {
            "score": signal["score"],
            "drug_terms": signal["drug_hits"],
            "class_terms": signal["class_hits"],
            "disease_terms": signal["disease_hits"],
        },

        "what_happened": what_happened,

        "source_url": (
            "https://www.fda.gov/drugs/"
            "cancer-approvals/"
            "oncology-cancerhematologic-malignancies-"
            "approval-notifications"
        ),
    }


def main():

    print("Fetching FDA Drugs@FDA records...")

    all_records = []

    limit = 99

    for skip in range(
        0,
        MAX_RECORDS_TO_FETCH,
        limit,
    ):

        url = (
            f"{FDA_DRUGS_URL}"
            f"?limit={limit}"
            f"&skip={skip}"
        )

        payload = safe_fetch_json(url)

        if not payload:
            print(
                f"FDA request failed at skip={skip}"
            )
            break

        records = payload.get(
            "results",
            [],
        )

        if not records:
            break

        all_records.extend(records)

        print(
            f"Retrieved {len(all_records)} FDA records..."
        )

    print(
        f"Total FDA records retrieved: "
        f"{len(all_records)}"
    )

    candidates = []

    for record in all_records:

        if is_oncology(record):
            candidates.append(record)

    print(
        f"Potential oncology records identified: "
        f"{len(candidates)}"
    )

    intelligence_records = []

    for record in candidates:

        try:
            item = build_intelligence_record(record)

            intelligence_records.append(item)

        except Exception as exc:
            print(
                "Failed to process FDA record:",
                exc
            )

    # Remove duplicates.
    unique = {}

    for item in intelligence_records:

        key = (
            item.get("application_number", ""),
            item.get("drug", ""),
            item.get("active_ingredient", ""),
        )

        if not any(key):
            continue

        unique[key] = item

    intelligence_records = list(
        unique.values()
    )

    # Highest oncology signal first.
    intelligence_records.sort(
        key=lambda x: (
            x.get("oncology_signal", {})
            .get("score", 0),
            x.get("submission_status_date", ""),
        ),
        reverse=True,
    )

    intelligence_records = (
        intelligence_records[:MAX_ONCOLOGY_RECORDS]
    )

    output = {
        "source": "FDA",

        "retrieved_at": (
            datetime.now(timezone.utc)
            .isoformat()
        ),

        "records_retrieved": len(
            all_records
        ),

        "oncology_candidates": len(
            candidates
        ),

        "oncology_records": len(
            intelligence_records
        ),

        "records": intelligence_records,
    }

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    output_file = (
        f"{OUTPUT_DIR}/"
        f"{today}-fda.json"
    )

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
        "========================================"
    )
    print(
        "FDA ONCOLOGY COLLECTOR COMPLETE"
    )
    print(
        "========================================"
    )
    print(
        f"Records retrieved: "
        f"{len(all_records)}"
    )
    print(
        f"Oncology candidates: "
        f"{len(candidates)}"
    )
    print(
        f"Final oncology records: "
        f"{len(intelligence_records)}"
    )
    print(
        f"Saved: {output_file}"
    )


if __name__ == "__main__":
    main()
