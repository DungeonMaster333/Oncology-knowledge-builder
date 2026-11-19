import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os

FDA_URL = "https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications"


def collect_fda():
    headers = {
        "User-Agent": "OncologyKnowledgeBuilder/1.0"
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

    soup = BeautifulSoup(response.text, "html.parser")

    approvals = []

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)
        href = link.get("href")

        if not title or not href:
            continue

        if "FDA approves" in title or "FDA grants" in title:

            if href.startswith("/"):
                href = "https://www.fda.gov" + href

            approvals.append({
                "title": title,
                "url": href
            })

    seen = set()

    for approval in approvals:
        if approval["url"] not in seen:
            seen.add(approval["url"])
            result["approvals"].append(approval)

    result["approval_count"] = len(result["approvals"])

    return result


def save_result(result):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    os.makedirs("data/issues", exist_ok=True)

    filename = f"data/issues/{today}-fda.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Saved FDA data to: {filename}")


if __name__ == "__main__":
    result = collect_fda()

    print(json.dumps(result, indent=2))

    save_result(result)
