import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os
import re

FDA_RSS_URL = "https://www.fda.gov/about-fda/contact-fda/subscribe-podcasts-and-news-feeds"


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
    "oncologic",
]


def collect_fda():
    headers = {
        "User-Agent": "OncologyKnowledgeBuilder/1.0"
    }

    response = requests.get(
        FDA_RSS_URL,
        timeout=30,
        headers=headers
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    feeds = []

    for link in soup.find_all("a", href=True):

        title = link.get_text(" ", strip=True)
        href = link["href"].strip()

        if not title or not href:
            continue

        if "What's New" in title and "Drugs" in title:

            if href.startswith("/"):
                href = "https://www.fda.gov" + href

            feeds.append({
                "title": title,
                "url": href
            })

    return {
        "source": "FDA",
        "source_url": FDA_RSS_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "feed_count": len(feeds),
        "feeds": feeds
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

    print(json.dumps(result, indent=2, ensure_ascii=False))

    save_result(result)
