import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import re

FDA_URL = "https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications"


def collect_fda():
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OncologyKnowledgeBuilder/1.0)"
    }

    response = requests.get(
        FDA_URL,
        timeout=30,
        headers=headers
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    approvals = []

    # Look for links/articles on the FDA oncology approval page
    for link in soup.find_all("a", href=True):

        title = link.get_text(" ", strip=True)
        href = link["href"]

        if not title:
            continue

        # Keep likely approval-related links
        if re.search(
            r"approval|approves|approved|oncology|cancer|malign",
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
    unique_approvals = []
    seen = set()

    for item in approvals:
        key = (item["title"], item["url"])

        if key not in seen:
            seen.add(key)
            unique_approvals.append(item)

    result = {
        "source": "FDA",
        "source_url": FDA_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "approval_count": len(unique_approvals),
        "approvals": unique_approvals
    }

    return result


if __name__ == "__main__":
    result = collect_fda()

    print(json.dumps(result, indent=2))

    # Basic validation
    if result["approval_count"] == 0:
        raise RuntimeError("FDA page was reached, but no approval entries were extracted.")
