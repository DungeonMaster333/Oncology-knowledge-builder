import os
import json
from pathlib import Path
from datetime import datetime, timezone

from google import genai


def load_latest_data():

    files = sorted(
        Path("data/issues").glob("*.json"),
        key=lambda x: x.stat().st_mtime
    )

    data = []

    for file in files[-10:]:

        try:
            with open(
                file,
                "r",
                encoding="utf-8"
            ) as f:

                data.append({
                    "file": file.name,
                    "data": json.load(f)
                })

        except Exception as e:

            print(
                f"Could not read {file}: {e}"
            )

    return data


def generate_digest(data):

    api_key = os.environ["GEMINI_API_KEY"]

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
You are an oncology commercial intelligence analyst
and oncology tutor.

Your task is to convert the supplied FDA,
ClinicalTrials.gov and PubMed data into a useful
daily Oncology Knowledge Digest.

IMPORTANT RULES:

1. Use ONLY the supplied source data.
2. Never invent drugs, companies, indications,
   trial results or regulatory decisions.
3. If information is unavailable, explicitly say:
   "Not specified in source data."
4. Distinguish facts from interpretation.
5. Prioritize important oncology developments.
6. Avoid repeating the same information.
7. Keep the language suitable for a pharma/life-sciences
   professional who is building oncology expertise.

Create the digest using this structure:

# Oncology Knowledge Digest

## 1. FDA / Regulatory Intelligence

For each meaningful FDA-related item:

- What happened
- Drug / asset
- Company
- Cancer indication
- Regulatory significance
- Commercial significance
- What I should learn from this

## 2. Clinical Trials / Pipeline Intelligence

For important trial or pipeline items:

- Asset
- Company / sponsor
- Cancer indication
- Trial phase
- Trial objective or status
- Why it matters
- Potential competitive implication
- What I should learn from this

## 3. Scientific / Research Intelligence

For important research:

- Topic
- Cancer indication
- Key finding
- Why it matters
- Potential pharma/commercial relevance
- What I should learn from this

## 4. Oncology Concepts to Learn

Based ONLY on today's developments, identify
3–5 oncology concepts that would be useful for me
to understand better.

For each concept explain it briefly.

## 5. Analyst Takeaways

Give 5 concise takeaways that an oncology
commercial intelligence analyst should remember.

## 6. Important Sources

List the source name and URL for each important
item.

SOURCE DATA:

{json.dumps(data, indent=2, ensure_ascii=False)}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return response.text


def save_digest(digest):

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    output_dir = Path(
        "data/digests"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = (
        output_dir /
        f"{today}-digest.md"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            f"# Oncology Knowledge Digest — {today}\n\n"
        )

        f.write(digest)

    print(
        f"Saved digest to {filename}"
    )


if __name__ == "__main__":

    data = load_latest_data()

    digest = generate_digest(
        data
    )

    save_digest(
        digest
    )
