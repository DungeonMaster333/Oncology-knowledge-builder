import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os
import re

FDA_RSS_URL = "https://www.fda.gov/AboutFDA/ContactFDA/StayInformed/RSSFeeds/Drugs/rss.xml"

ONCOLOGY_KEYWORDS = [
    "cancer",
    "oncology",
    "tumor",
    "tumour",
    "carcinoma",
    "lymphoma",
    "leukemia",
    "leukaemia",
    "myeloma",
    "sarcoma",
    "melanoma",
    "metastatic",
    "neoplasm",
]


def collect_fda():

    response = requests.get(
        FDA_RSS_URL,
        timeout=30,
        headers={
            "User-Agent": "OncologyKnowledgeBuilder/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.content, "xml")

    approvals = []

    for item in soup.find_all("item"):

        title = item.find("title")
        link = item.find("link")
        description = item.find("description")
        pub_date = item.find("pubDate")

        title_text = title.get_text(" ", strip=True) if title else ""
        description_text = (
            description.get_text(" ", strip=True)
            if description else ""
        )
        link_text = link.get_text(strip=True) if link else ""

        combined_text = (
            title_text + " " + description_text
        ).lower()

        # Keep only oncology/cancer-related FDA updates
        if any(
            keyword in combined_text
            for keyword in ONCOLOGY_KEYWORDS
        ):

            approvals.append({
                "title": title_text,
                "url": link_text,
                "published": (
                    pub_date.get_text(strip=True)
                    if pub_date else None
                ),
                "description": description_text
            })

    return {
        "source": "FDA",
        "source_url": FDA_RSS_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "approval_count": len(approvals),
        "approvals": approvals
    }


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

    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    ))

    save_result(result)
