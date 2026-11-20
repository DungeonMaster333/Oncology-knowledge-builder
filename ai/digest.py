import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
ISSUES_DIR = ROOT / "data" / "issues"
DIGEST_DIR = ROOT / "data" / "digests"

DIGEST_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "gemini-3.8-flash"
MAX_RETRIES = 4


# ============================================================
# HELPERS
# ============================================================

def load_latest_files():
    """
    Load the most recent FDA, ClinicalTrials.gov and PubMed JSON files.
    """
    files = sorted(ISSUES_DIR.glob("*.json"), reverse=True)

    datasets = {
        "FDA / Regulatory": [],
        "Clinical Trials": [],
        "PubMed / Scientific": []
    }

    for file in files[:20]:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            name = file.name.lower()

            if "fda" in name:
                datasets["FDA / Regulatory"].extend(
                    data if isinstance(data, list) else data.get("records", [])
                )

            elif "clinicaltrials" in name:
                datasets["Clinical Trials"].extend(
                    data if isinstance(data, list) else data.get("records", [])
                )

            elif "pubmed" in name:
                datasets["PubMed / Scientific"].extend(
                    data if isinstance(data, list) else data.get("records", [])
                )

        except Exception as e:
            print(f"Warning: could not read {file.name}: {e}")

    return datasets


def clean_records(records, limit=15):
    """
    Keep the prompt reasonably small.
    """
    cleaned = []

    for r in records[:limit]:
        if isinstance(r, dict):
            cleaned.append(r)

    return cleaned


def build_prompt(datasets):
    return f"""
You are an oncology intelligence analyst working for a pharmaceutical
commercial strategy and competitive intelligence team.

Create a concise DAILY ONCOLOGY INTELLIGENCE digest from the source
records below.

IMPORTANT:
- Only use information actually present in the supplied records.
- Do not invent approvals, indications, companies, trial results or dates.
- Clearly distinguish regulatory, clinical-trial and scientific information.
- Prefer oncology-relevant developments.
- Ignore obvious non-oncology records.
- Write for a pharma/life-sciences analyst who wants to learn oncology.
- Explain technical items in simple language.
- Highlight why each important development matters commercially or clinically.

Use exactly these sections:

# Daily Oncology Intelligence

## FDA / Regulatory Intelligence
Give the most relevant oncology regulatory developments.

## Clinical Trials / Pipeline Intelligence
Give the most relevant oncology clinical-trial developments.

## Scientific / Research Intelligence
Give the most relevant oncology research developments.

## Oncology Concepts to Learn
List 3-5 oncology concepts, biomarkers, mechanisms, modalities or disease
areas that appear useful for learning based on today's intelligence.

## Analyst Takeaways
Give 3-5 concise pharma/commercial intelligence takeaways.

## Important Sources
Mention the source type for each important item.

SOURCE DATA:

FDA / REGULATORY:
{json.dumps(clean_records(datasets["FDA / Regulatory"]), indent=2)}

CLINICAL TRIALS:
{json.dumps(clean_records(datasets["Clinical Trials"]), indent=2)}

PUBMED / SCIENTIFIC:
{json.dumps(clean_records(datasets["PubMed / Scientific"]), indent=2)}
"""


def generate_with_gemini(prompt):
    """
    Call Gemini with retries for temporary 503/high-demand errors.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Gemini attempt {attempt}/{MAX_RETRIES}...")

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            text = getattr(response, "text", None)

            if text and text.strip():
                print("Gemini digest generated successfully.")
                return text.strip()

            raise RuntimeError("Gemini returned an empty response.")

        except Exception as e:
            last_error = e
            print(f"Gemini attempt {attempt} failed: {e}")

            if attempt < MAX_RETRIES:
                wait_time = 5 * (2 ** (attempt - 1))
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

    raise RuntimeError(f"Gemini failed after {MAX_RETRIES} attempts: {last_error}")


def fallback_digest(datasets):
    """
    Generate a deterministic digest when Gemini is temporarily unavailable.
    This prevents the GitHub Action from failing just because Gemini is busy.
    """

    today = datetime.now(timezone.utc).strftime("%d %B %Y")

    lines = [
        "# Daily Oncology Intelligence",
        "",
        f"**Date:** {today}",
        "",
        "## FDA / Regulatory Intelligence",
        ""
    ]

    fda = datasets["FDA / Regulatory"]

    if fda:
        for item in fda[:5]:
            lines.append(
                f"- **{item.get('drug_name') or item.get('brand_name') or item.get('name') or 'FDA regulatory update'}** — "
                f"{item.get('indication') or item.get('description') or item.get('status') or 'Regulatory development.'}"
            )
    else:
        lines.append("- No FDA oncology records were available.")

    lines.extend([
        "",
        "## Clinical Trials / Pipeline Intelligence",
        ""
    ])

    trials = datasets["Clinical Trials"]

    if trials:
        for item in trials[:5]:
            title = (
                item.get("title")
                or item.get("brief_title")
                or item.get("name")
                or "Clinical trial"
            )

            status = item.get("status") or item.get("overall_status") or ""

            lines.append(
                f"- **{title}** — {status}"
            )
    else:
        lines.append("- No clinical-trial records were available.")

    lines.extend([
        "",
        "## Scientific / Research Intelligence",
        ""
    ])

    pubs = datasets["PubMed / Scientific"]

    if pubs:
        for item in pubs[:5]:
            title = item.get("title") or "Scientific publication"
            journal = item.get("journal") or ""

            lines.append(
                f"- **{title}** — {journal}"
            )
    else:
        lines.append("- No PubMed records were available.")

    lines.extend([
        "",
        "## Oncology Concepts to Learn",
        "",
        "- Review the mechanisms, indications and therapeutic modalities represented in today's records.",
        "- Review the clinical development stage and status of the oncology trials identified today.",
        "- Review relevant biomarkers and patient-selection concepts where applicable.",
        "",
        "## Analyst Takeaways",
        "",
        "- Today's intelligence should be interpreted together with indication, mechanism, development stage and competitive context.",
        "- Regulatory events should be validated against the underlying FDA source before making strategic conclusions.",
        "- Clinical-trial status alone does not establish efficacy or commercial success.",
        "",
        "## Important Sources",
        "",
        "- FDA / Regulatory dataset",
        "- ClinicalTrials.gov dataset",
        "- PubMed dataset",
        "",
        "_Gemini was temporarily unavailable, so this digest was generated using the collected source records without AI summarization._"
    ])

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print("Loading latest oncology intelligence records...")

    datasets = load_latest_files()

    total_records = sum(len(v) for v in datasets.values())

    print(f"FDA records: {len(datasets['FDA / Regulatory'])}")
    print(f"Clinical trial records: {len(datasets['Clinical Trials'])}")
    print(f"PubMed records: {len(datasets['PubMed / Scientific'])}")
    print(f"Total records: {total_records}")

    if total_records == 0:
        raise RuntimeError("No intelligence records were found.")

    prompt = build_prompt(datasets)

    try:
        digest = generate_with_gemini(prompt)

    except Exception as e:
        print("")
        print("WARNING: Gemini unavailable.")
        print(str(e))
        print("Generating deterministic fallback digest instead.")
        digest = fallback_digest(datasets)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    output_file = DIGEST_DIR / f"{today}-digest.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(digest)

    print("")
    print(f"Digest saved: {output_file}")
    print("Digest generation completed successfully.")


if __name__ == "__main__":
    main()
