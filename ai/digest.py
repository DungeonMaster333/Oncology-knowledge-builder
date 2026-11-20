import os
import json
from pathlib import Path
from datetime import datetime, timezone

from google import genai


def load_latest_data():
    files = sorted(Path("data/issues").glob("*.json"))

    data = []

    for file in files[-3:]:
        with open(file, "r", encoding="utf-8") as f:
            data.append(json.load(f))

    return data


def generate_digest(data):
    api_key = os.environ["GEMINI_API_KEY"]

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an oncology knowledge analyst.

Using ONLY the source data provided below, create a concise
daily Oncology Knowledge Digest.

For each important development, provide:

1. What happened
2. Cancer indication
3. Drug/asset/company involved
4. Why it matters
5. Source type

Separate the digest into:

- FDA / Regulatory
- Clinical Trials / Pipeline
- Scientific Research

Do not invent information.
If the supplied data does not contain enough information,
say "Not specified in source data."

Source data:

{json.dumps(data, indent=2, ensure_ascii=False)}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return response.text


def save_digest(digest):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    output_dir = Path("data/digests")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = output_dir / f"{today}-digest.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Oncology Knowledge Digest — {today}\n\n")
        f.write(digest)

    print(f"Saved digest to: {filename}")


if __name__ == "__main__":
    data = load_latest_data()
    digest = generate_digest(data)
    save_digest(digest)
