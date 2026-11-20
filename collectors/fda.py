import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os
import re

FDA_URL = "https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications"


def collect_fda():
    """
    Collect FDA oncology approval notifications.

    FDA may occasionally return an anti-bot/abuse page to automated
    requests. In that case, return a structured diagnostic result
    rather than crashing the pipeline.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; OncologyKnowledgeBuilder/1.0; "
            "+https://github.com/)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(
        FDA_URL,
        timeout=30,
        headers=headers
    )

    result = {
        "source": "FDA",
        "source_url": FDA_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": response.status_code,
        "approval_count": 0,
        "approvals": []
    }

    if response.status_code != 200:
        result["error"] = "FDA page could not be retrieved directly"
        return result

    # Detect FDA anti-abuse page
    if "abuse-detection" in response.url.lower():
        result["error"] = "FDA anti-abuse page returned"
        result["final_url"] = response.url
        return result

    soup = BeautifulSoup(response.text, "html.parser")

    approvals = []

    # FDA approval notifications are presented as links/headings.
    for link in soup.find_all("a", href=True):

        title = link.get_text(" ", strip=True)
        href = link.get("href", "").strip()

        if not title or not href:
            continue

        # Keep approval notification links
        if re.search(
            r"FDA (approves|grants|expands|withdraws)",
            title,
            re.IGNORECASE
        ):

            if href.startswith("/"):
                href = "https://www.fda.gov" + href

            approvals.append({
                "title": title,
                "url": href
            })

    # Remove duplicates
    seen = set()

    for approval in approvals:

        key = approval["url"]

        if key not in seen:
            seen.add(key)
            result["approvals"].append(approval)

    result["approval_count"] = len(result["approvals"])

    return result


def save_result(result):

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    os.makedirs("data/issues", exist_ok=True)

    filename = f"data/issues/{today}-fda.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Saved FDA data to {filename}")


if __name__ == "__main__":

    result = collect_fda()

    print(json.dumps(result, indent=2, ensure_ascii=False))

    save_result(result)
