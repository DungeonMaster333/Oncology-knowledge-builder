import requests
from datetime import datetime, timezone
import json
import xml.etree.ElementTree as ET

SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

PARAMS = {
    "db": "pubmed",
    "term": "oncology cancer therapeutics",
    "retmax": 20,
    "retmode": "json",
}


def collect_pubmed():
    # Step 1: Search PubMed
    response = requests.get(
        SEARCH_URL,
        params=PARAMS,
        timeout=30,
        headers={
            "User-Agent": "OncologyKnowledgeBuilder/1.0"
        }
    )

    response.raise_for_status()

    search_data = response.json()

    pmids = search_data.get("esearchresult", {}).get("idlist", [])

    if not pmids:
        return {
            "source": "PubMed",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "article_count": 0,
            "articles": []
        }

    # Step 2: Fetch article details
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }

    fetch_response = requests.get(
        FETCH_URL,
        params=fetch_params,
        timeout=30,
        headers={
            "User-Agent": "OncologyKnowledgeBuilder/1.0"
        }
    )

    fetch_response.raise_for_status()

    root = ET.fromstring(fetch_response.text)

    articles = []

    for article in root.findall(".//PubmedArticle"):

        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle")

        abstract_parts = []

        for abstract in article.findall(".//AbstractText"):
            if abstract.text:
                abstract_parts.append(abstract.text)

        abstract = " ".join(abstract_parts)

        journal = article.findtext(".//Journal/Title")

        pub_date = (
            article.findtext(".//PubDate/Year")
            or article.findtext(".//PubDate/MedlineDate")
        )

        articles.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "publication_date": pub_date,
            "abstract": abstract
        })

    return {
        "source": "PubMed",
        "search_url": SEARCH_URL,
        "query": PARAMS["term"],
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "articles": articles
    }


if __name__ == "__main__":
    result = collect_pubmed()

    print(json.dumps(result, indent=2, ensure_ascii=False))
