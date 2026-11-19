import requests
from datetime import datetime, timezone
import json
import os


FDA_URL = "https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications"

def collect_fda():
    """
    Basic FDA oncology approval collector.

    This first version checks the FDA oncology approval page
    and stores the page metadata. We will improve extraction
    after confirming the collector works in GitHub Actions.
    """

    response = requests.get(
        FDA_URL,
        timeout=30,
        headers={
            "User-Agent": "OncologyKnowledgeBuilder/1.0"
        }
    )

    response.raise_for_status()

    result = {
        "source": "FDA",
        "url": FDA_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": response.status_code,
        "content_length": len(response.text)
    }

    return result


if __name__ == "__main__":
    result = collect_fda()

    print(json.dumps(result, indent=2))
