import requests
from datetime import datetime, timezone
import json

API_URL = "https://clinicaltrials.gov/api/v2/studies"

PARAMS = {
    "query.cond": "cancer",
    "pageSize": 20,
    "format": "json"
}


def collect_clinical_trials():
    response = requests.get(
        API_URL,
        params=PARAMS,
        timeout=30,
        headers={
            "User-Agent": "OncologyKnowledgeBuilder/1.0"
        }
    )

    response.raise_for_status()

    data = response.json()

    studies = []

    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})

        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        conditions = protocol.get("conditionsModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        interventions = protocol.get("armsInterventionsModule", {})

        studies.append({
            "nct_id": identification.get("nctId"),
            "title": identification.get("briefTitle"),
            "status": status.get("overallStatus"),
            "phase": design.get("phases", []),
            "conditions": conditions.get("conditions", []),
            "interventions": [
                intervention.get("name")
                for intervention in interventions.get("interventions", [])
                if intervention.get("name")
            ],
            "sponsor": sponsor.get("leadSponsor", {}).get("name"),
            "start_date": status.get("startDateStruct", {}).get("date"),
            "completion_date": status.get("completionDateStruct", {}).get("date"),
        })

    return {
        "source": "ClinicalTrials.gov",
        "source_url": API_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "query": PARAMS,
        "study_count": len(studies),
        "studies": studies
    }


if __name__ == "__main__":
    result = collect_clinical_trials()

    print(json.dumps(result, indent=2))
