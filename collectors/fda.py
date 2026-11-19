import requests
from datetime import datetime, timezone
import json

FDA_URL = "https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications"


def collect_fda():
    """
    Test collector for the FDA oncology approval notifications page.
    """

    response = requests.get(
        FDA_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; OncologyKnowledgeBuilder/1.0)"
        }
    )

    result = {
        "source": "FDA",
        "url": FDA_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": response.status_code,
        "content_length": len(response.text)
    }

    return result


if __name__ == "__main__":
    try:
        result = collect_fda()
        print(json.dumps(result, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"FDA request failed: {e}")
        raise
