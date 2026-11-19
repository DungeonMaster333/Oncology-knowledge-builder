import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json

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

    # FDA may return an anti-abuse page to automated requests.
    # We keep the response for diagnostic purposes.
    if response.status_code != 200:
        return {
            "source": "FDA",
            "url": FDA_URL,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "status": response.status_code,
            "error": "FDA page could not be retrieved directly",
            "content_preview": response.text[:500]
        }

    soup = BeautifulSoup(response.text, "html.parser")

    approvals = []

    # FDA approval notifications are represented as links on the page.
    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)
        href = link.get("href")

        if not title or not href:
            continue

        if (
            "FDA approves" in title
            or "FDA grants" in title
        ):
            if href.startswith("/"):
                href = "https://www.fda.gov" + href

            approvals.append({
                "title": title,
                "url": href
            })

    # Remove duplicates
    seen = set()
    unique_approvals = []

    for approval in approvals:
        key = approval["url"]

        if key not in seen:
            seen.add(key)
            unique_approvals.append(approval)

    return {
        "source": "FDA",
        "source_url": FDA_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": response.status_code,
        "approval_count": len(unique_approvals),
        "approvals": unique_approvals
    }


if __name__ == "__main__":
    result = collect_fda()

    print(json.dumps(result, indent=2))

    if result.get("status") == 200 and result.get("approval_count", 0) == 0:
        print("WARNING: FDA page loaded but no approval entries were detected.")
