"""FDA oncology collector using the official openFDA API (not the fda.gov website).

Why: fda.gov pages sit behind bot protection that blocks GitHub's cloud servers
(the 'abuse-detection-apology' redirect). api.fda.gov is built for scripts.

Flow: Drugs@FDA approvals in the last N days -> keep NDA/BLA originals and new-indication
(efficacy) supplements -> join to the drug label to read the indication text ->
keep only oncology -> write data/raw/fda_oncology.json.

Optional env: OPENFDA_API_KEY (free at open.fda.gov), FDA_LOOKBACK_DAYS (default 30).
"""
import datetime, json, os, pathlib, re, sys, time
import requests

API = "https://api.fda.gov"
KEY = os.environ.get("OPENFDA_API_KEY", "")
DAYS = int(os.environ.get("FDA_LOOKBACK_DAYS", "30"))
OUT = pathlib.Path("data/raw/fda_oncology.json")
HEAD = {"User-Agent": "oncology-knowledge-builder/1.0 (personal learning project)"}

ONC = re.compile(r"cancer|carcinoma|tumou?r|neoplas|malignan|lymphoma|leuk[a]?emia|myeloma|melanoma|sarcoma|"
                 r"glioma|glioblastoma|myelodysplastic|myelofibrosis|mesothelioma|blastoma|metasta", re.I)
NOT_ONC = re.compile(r"tumor necrosis|malignant hyperthermia", re.I)  # common false positives


def is_oncology(text):
    return bool(ONC.search(NOT_ONC.sub(" ", text or "")))


def get(path, params):
    params = dict(params)
    if KEY:
        params["api_key"] = KEY
    r = None
    for attempt in range(4):
        r = requests.get(API + path, params=params, headers=HEAD, timeout=60)
        if r.status_code == 404:          # openFDA uses 404 for "no matches"
            return {"results": []}
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** attempt * 2)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def recent_applications(start, end):
    q = f"submissions.submission_status:AP AND submissions.submission_status_date:[{start} TO {end}]"
    out, skip = [], 0
    while True:
        res = get("/drug/drugsfda.json", {"search": q, "limit": 100, "skip": skip}).get("results", [])
        out += res
        if len(res) < 100 or skip >= 1000:
            return out
        skip += 100


def pick(app, start, end):
    """Return one approval event for this application, or None."""
    num = app.get("application_number", "")
    if not num.startswith(("NDA", "BLA")):        # skip generics (ANDA)
        return None
    events = [s for s in app.get("submissions", [])
              if s.get("submission_status") == "AP" and start <= s.get("submission_status_date", "") <= end
              and (s.get("submission_type") == "ORIG"
                   or (s.get("submission_type") == "SUPPL" and s.get("submission_class_code") == "EFFICACY"))]
    if not events:
        return None
    s = max(events, key=lambda x: x["submission_status_date"])
    prods = app.get("products") or [{}]
    d = s["submission_status_date"]
    return {
        "application_number": num,
        "brand": (prods[0].get("brand_name") or "").title(),
        "company": app.get("sponsor_name") or "Not listed",
        "kind": "new_product" if s.get("submission_type") == "ORIG" else "new_indication_or_efficacy_supplement",
        "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
    }


def labels_for(numbers):
    """Map application number -> newest label info (indication text, generic name, drug class)."""
    found = {}
    for i in range(0, len(numbers), 20):
        chunk = numbers[i:i + 20]
        q = "openfda.application_number:(" + " OR ".join(f'"{n}"' for n in chunk) + ")"
        for lab in get("/drug/label.json", {"search": q, "limit": 100}).get("results", []):
            of = lab.get("openfda", {})
            for n in of.get("application_number", []):
                if n in chunk and lab.get("effective_time", "") >= found.get(n, {}).get("t", ""):
                    found[n] = {"t": lab.get("effective_time", ""),
                                "indication": " ".join(lab.get("indications_and_usage", []))[:900],
                                "generic": ", ".join(of.get("generic_name", [])).title(),
                                "drug_class": ", ".join(of.get("pharm_class_epc", []))}
    return found


def main():
    end_d = datetime.date.today()
    start, end = (end_d - datetime.timedelta(days=DAYS)).strftime("%Y%m%d"), end_d.strftime("%Y%m%d")
    print(f"openFDA approvals {start}..{end}")
    events = [e for e in (pick(a, start, end) for a in recent_applications(start, end)) if e]
    labels = labels_for([e["application_number"] for e in events])
    onc, unknown = [], 0
    for e in events:
        lab = labels.get(e["application_number"])
        if not lab:
            unknown += 1
            continue
        if not is_oncology(lab["indication"]):
            continue
        digits = re.sub(r"\D", "", e["application_number"])
        e.update(generic=lab["generic"], drug_class=lab["drug_class"], indication_text=lab["indication"],
                 priority="high" if e["kind"] == "new_product" else "medium",
                 source_url=f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={digits}")
        onc.append(e)
    onc.sort(key=lambda x: (x["priority"] != "high", x["date"]), reverse=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated": end, "window_days": DAYS, "items": onc}, indent=1), encoding="utf-8")
    print(f"{len(events)} approval events, {len(onc)} oncology, {unknown} without a label yet")
    if not onc:
        print("WARNING: zero oncology items - check the window or the API response")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:          # never crash the whole daily pipeline
        print("FDA collector failed:", exc)
        sys.exit(1)
